"""Etapa SPEC: história aprovada → cenas presas às palavras do roteiro, cada uma com motor, kits e parâmetros.

O modelo escreve a SPEC (prompt em `prompts/spec.txt`) citando TRECHOS literais; aqui cada trecho vira índice de
palavra (`i0`/`i1` da cena, `i` de cada SFX e de cada âncora dentro dos parâmetros, como `ritmo[].em` do gráfico).
Os tempos (`t0`/`t1`) são derivados das palavras: trocar a narração só recalcula os tempos (`retemporizar`).

    python spec.py prompt  <pasta_do_projeto>                  # grava prompts/spec.prompt.txt
    python spec.py aplicar <pasta_do_projeto> <resposta.json>  # resposta do modelo → spec.json + estado
    python spec.py pedido  <pasta_do_projeto> <id_cena>        # prompt de mudança de UMA cena (pedido do Felipe)
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import etapas
from comum import (FPS, KITS, MOTORES, TRANSICOES, cache_resposta, entradas, extrair_json, frases, hash_dados, hash_texto, ler_json,
                   localizar, observacoes, preencher, prompt_arquivo, regras_de_direcao, resumo_kits)
from esquema import validar

CAUDA = 0.6   # s depois da última palavra (respiro final)


def prompt(roteiro: str, palavras: list[dict], historia: dict, briefing: str = "", obs: str = "") -> str:
    h = {k: historia[k] for k in ("titulo", "tese", "capitulos", "afirmacoes")}
    return preencher(prompt_arquivo("spec.txt"), roteiro_com_tempos=frases(palavras), duracao=f"{palavras[-1]['f']:.0f}",
                     historia=json.dumps(h, ensure_ascii=False, indent=1), kits=resumo_kits(),
                     briefing=briefing.strip() or "(sem briefing)", regras=regras_de_direcao(), fps=FPS,
                     observacoes=obs.strip() or "(nenhuma observação geral)")


def _ancoras(no, palavras: list[dict], i0: int, i1: int, avisos: list[str], onde: str):
    """Toda chave "em" (texto) dentro dos parâmetros ganha "i" (índice a partir do início da cena; None = não achou)."""
    if isinstance(no, dict):
        if isinstance(no.get("em"), str):
            j = localizar(palavras, no["em"], i0)
            no["i"] = j
            if j is None:
                avisos.append(f"{onde}: âncora \"{no['em']}\" não encontrada a partir da cena")
        for k, v in no.items():
            if k != "em":
                _ancoras(v, palavras, i0, i1, avisos, onde)
    elif isinstance(no, list):
        for v in no:
            _ancoras(v, palavras, i0, i1, avisos, onde)


def _id(em: str, usados: set) -> str:
    pid = hashlib.sha1(em.encode()).hexdigest()[:8]
    while pid in usados:
        pid = hashlib.sha1(pid.encode()).hexdigest()[:8]
    usados.add(pid)
    return pid


def tempos_das_cenas(cenas: list[dict], palavras: list[dict]) -> None:
    """i1 = início da próxima; t0/t1 pelas palavras. Primeira cena começa em 0."""
    for k, c in enumerate(cenas):
        c["i1"] = cenas[k + 1]["i0"] if k + 1 < len(cenas) else len(palavras)
        c["t0"] = 0.0 if k == 0 else round(palavras[c["i0"]]["i"], 3)
    for k, c in enumerate(cenas):
        c["t1"] = cenas[k + 1]["t0"] if k + 1 < len(cenas) else round(palavras[-1]["f"] + CAUDA, 3)


def normalizar(bruto, palavras: list[dict], historia: dict, roteiro: str, tempos: str = "medidos") -> dict:
    bruto = extrair_json(bruto)
    brutos = bruto["cenas"] if isinstance(bruto, dict) else bruto
    avisos, cenas, ult, usados = [], [], -1, set()
    caps = historia["capitulos"]
    for n, b in enumerate(brutos):
        i = localizar(palavras, b.get("em"), ult + 1)
        if i is None and not cenas:
            i = 0
            avisos.append(f"cena {n + 1}: trecho \"{b.get('em')}\" não encontrado; a 1ª cena começa na 1ª palavra")
            b = {**b, "em": " ".join(p["t"] for p in palavras[:4])}
        if i is None:
            avisos.append(f"cena {n + 1}: trecho não encontrado no roteiro: \"{b.get('em')}\" (saiu)")
            continue
        if not cenas and i != 0:
            avisos.append("a 1ª cena não começava na 1ª palavra: passou a começar")
            i = 0
        ult = i
        tr = b.get("transicao") or ("corte" if not cenas else "corte")
        if isinstance(tr, str):
            tr = {"tipo": tr}
        tr = {"tipo": tr.get("tipo", "corte"), "quadros": int(tr.get("quadros", TRANSICOES.get(tr.get("tipo"), 0)))}
        cap = b.get("capitulo") or next((c["id"] for c in reversed(caps) if c["i"] <= i), caps[0]["id"])
        c = {"id": _id(b["em"], usados), "em": b["em"], "i0": i, "i1": i + 1, "t0": 0.0, "t1": 0.001, "capitulo": cap,
             "objetivo": str(b.get("objetivo") or ""), "motor": b.get("motor"),
             "kits": copy.deepcopy(b.get("kits") or []), "afirmacoes": [str(x) for x in b.get("afirmacoes") or []],
             "texto": [str(x) for x in b.get("texto") or []], "sfx": [], "transicao": tr}
        if c["motor"] not in MOTORES:
            pref = [KITS[u.get("kit")].get("prefere") for u in c["kits"] if u.get("kit") in KITS]
            c["motor"] = "hyperframes" if "hyperframes" in pref else "remotion"
            avisos.append(f"cena {c['id']}: motor '{b.get('motor')}' inválido/ausente, ficou {c['motor']} (pelos kits)")
        for k in ("camera", "movimento", "aceitar_nao_validado", "notas"):
            if b.get(k):
                c[k] = b[k]
        for s in b.get("sfx") or []:
            j = localizar(palavras, s.get("em"), i)
            if j is None:
                avisos.append(f"cena {c['id']}: SFX {s.get('categoria')} em \"{s.get('em')}\" não encontrado (saiu)")
                continue
            e = {"categoria": s.get("categoria"), "em": s["em"], "i": j}
            for k in ("ponto", "intensidade"):
                if s.get(k) is not None:
                    e[k] = s[k]
            c["sfx"].append(e)
        cenas.append(c)
    if not cenas:
        raise ValueError("a SPEC não tem nenhuma cena achada no roteiro")
    tempos_das_cenas(cenas, palavras)
    for c in cenas:
        for uso in c["kits"]:
            _ancoras(uso.get("params"), palavras, c["i0"], c["i1"], avisos, f"cena {c['id']} kit {uso.get('kit')}")
    spec = {"versao": 1, "fps": FPS, "largura": 1920, "altura": 1080, "roteiro_hash": hash_texto(roteiro),
            "historia_hash": hash_dados(historia), "tempos": tempos, "cenas": cenas,
            "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "avisos": avisos}
    erros = validar(spec, "spec")
    if erros:
        raise ValueError("SPEC inválida:\n  " + "\n  ".join(erros[:30]))
    return spec


def retemporizar(spec: dict, palavras: list[dict]) -> dict:
    """Narração nova (mesmo roteiro): mesmos índices, tempos novos. Cena cujo trecho mudou de lugar = re-localizada."""
    s = copy.deepcopy(spec)
    ult = -1
    for c in s["cenas"]:
        j = localizar(palavras, c["em"], ult + 1)
        if j is not None:
            c["i0"] = j if ult >= 0 else 0
        ult = c["i0"]
    tempos_das_cenas(s["cenas"], palavras)
    s["tempos"] = "medidos"
    return s


def aplicar(pasta: Path, resposta) -> dict:
    pasta = Path(pasta)
    roteiro, palavras, tempos, briefing = entradas(pasta)
    historia = ler_json(pasta / "historia.json")
    if historia is None:
        raise FileNotFoundError("falta historia.json (etapa anterior)")
    estado = etapas.ler(pasta)
    if estado["etapas"]["historia"]["status"] != "aprovado":
        print("aviso: a história ainda não foi aprovada pelo Felipe (★)", file=sys.stderr)
    cache_resposta(pasta, "spec", prompt(roteiro, palavras, historia, briefing, observacoes(pasta)), resposta)
    s = normalizar(resposta, palavras, historia, roteiro, tempos)
    etapas.registrar(pasta, "spec", s, base=historia, resumo=f"{len(s['cenas'])} cenas"
                     + (f", {len(s['avisos'])} avisos" if s["avisos"] else ""))
    return s


def prompt_pedido(pasta: Path, id_cena: str) -> str:
    """Prompt para refazer UMA cena a partir dos pedidos abertos dela (as outras ficam como estão)."""
    pasta = Path(pasta)
    roteiro, palavras, _, _ = entradas(pasta)
    s = ler_json(pasta / "spec.json")
    c = next(x for x in s["cenas"] if x["id"] == id_cena)
    pedidos = [p["texto"] for p in etapas.pedidos_abertos(etapas.ler(pasta), "spec") if p.get("cena") == id_cena]
    trecho = " ".join(p["t"] for p in palavras[c["i0"]:c["i1"]])
    return preencher(prompt_arquivo("pedido_cena.txt"), cena=json.dumps(c, ensure_ascii=False, indent=1), trecho=trecho,
                     pedidos="\n".join(f"- {p}" for p in pedidos) or "(nenhum pedido aberto)", kits=resumo_kits(),
                     observacoes=observacoes(pasta))


def trocar_cena(spec: dict, id_cena: str, nova: dict, palavras: list[dict], historia: dict, roteiro: str) -> dict:
    """Resposta do pedido de cena → SPEC com a cena trocada (re-normalizada inteira; ids das outras não mudam)."""
    brutos = []
    for c in spec["cenas"]:
        base = nova if c["id"] == id_cena else c
        b = {k: v for k, v in base.items() if k not in ("id", "i0", "i1", "t0", "t1")}
        b.setdefault("em", c["em"])
        brutos.append(b)
    return normalizar({"cenas": brutos}, palavras, historia, roteiro, spec["tempos"])


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("prompt", "aplicar", "pedido"):
        print(__doc__)
        return 2
    pasta = Path(argv[1])
    if argv[0] == "prompt":
        roteiro, palavras, tempos, briefing = entradas(pasta)
        p = prompt(roteiro, palavras, ler_json(pasta / "historia.json"), briefing, observacoes(pasta))
        saida = pasta / "prompts" / "spec.prompt.txt"
    elif argv[0] == "pedido":
        p = prompt_pedido(pasta, argv[2])
        saida = pasta / "prompts" / f"pedido_{argv[2]}.prompt.txt"
    else:
        s = aplicar(pasta, json.loads(Path(argv[2]).read_text(encoding="utf-8")))
        print(f"spec.json: {len(s['cenas'])} cenas")
        for a in s["avisos"]:
            print("  aviso:", a)
        return 0
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(p, encoding="utf-8")
    print(f"{saida} ({len(p)} caracteres)")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
