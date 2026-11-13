"""Etapa HISTÓRIA: roteiro (+ briefing) → estrutura documental (capítulos e afirmações verificáveis).

Quem escreve a história é o modelo (prompt em `prompts/historia.txt`, executado pelo orquestrador ou pelo painel);
este módulo monta o prompt e transforma a resposta em `historia.json` conferido: cada capítulo e cada afirmação
apontam para um TRECHO LITERAL do roteiro, resolvido em índice de palavra (direção presa à palavra). Afirmação
verificável = diz qual sessão (OpenF1 session_key), qual carro e qual volta; é isso que `ativos.py` e `verificar.py` usam.

    python historia.py prompt  <pasta_do_projeto>                 # grava prompts/historia.prompt.txt
    python historia.py aplicar <pasta_do_projeto> <resposta.json> # resposta do modelo → historia.json + estado
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import etapas
from comum import (cache_resposta, entradas, extrair_json, frases, hash_texto, localizar, preencher, prompt_arquivo,
                   regras_de_direcao)
from esquema import validar

FUNCOES = ["gancho", "contexto", "evidencia", "tensao", "virada", "desfecho"]


def prompt(roteiro: str, palavras: list[dict], briefing: str = "") -> str:
    return preencher(prompt_arquivo("historia.txt"), roteiro_com_tempos=frases(palavras),
                     duracao=f"{palavras[-1]['f']:.0f}", briefing=briefing.strip() or "(sem briefing)",
                     regras=regras_de_direcao())


def normalizar(bruto: dict, palavras: list[dict], roteiro: str, tempos: str = "medidos") -> dict:
    """Resposta do modelo → historia.json. Trecho que não existe no roteiro sai (vira aviso); nada é inventado aqui."""
    bruto = extrair_json(bruto)
    avisos: list[str] = []
    caps, ult = [], -1
    for n, c in enumerate(bruto.get("capitulos") or []):
        i = localizar(palavras, c.get("em"), ult + 1)
        if i is None and not caps:
            avisos.append(f"capítulo {n + 1} ({c.get('titulo')}): trecho não encontrado; vira o início do roteiro")
            c = {**c, "em": " ".join(p["t"] for p in palavras[:4])}
            i = 0
        if i is None:
            avisos.append(f"capítulo {n + 1} ({c.get('titulo')}): trecho não encontrado no roteiro: \"{c.get('em')}\"")
            continue
        ult = i
        caps.append({"id": f"c{len(caps) + 1}", "titulo": str(c.get("titulo") or f"Parte {len(caps) + 1}"),
                     "funcao": c.get("funcao") if c.get("funcao") in FUNCOES else "contexto",
                     "ritmo": "respiro" if c.get("ritmo") == "respiro" else "denso", "em": c.get("em") or palavras[0]["t"], "i": i})
        if c.get("funcao") not in FUNCOES:
            avisos.append(f"capítulo {caps[-1]['id']}: função '{c.get('funcao')}' desconhecida, ficou 'contexto'")
    if caps:
        if caps[0]["i"] != 0:
            avisos.append("o 1º capítulo não começava na 1ª palavra: passou a começar")
        caps[0]["i"] = 0
        for a, b in zip(caps, caps[1:] + [None]):
            a["i1"] = b["i"] if b else len(palavras)
    afs = []
    for n, a in enumerate(bruto.get("afirmacoes") or []):
        i = localizar(palavras, a.get("em"))
        if i is None:
            avisos.append(f"afirmação {n + 1}: trecho não encontrado no roteiro: \"{a.get('em')}\" (saiu)")
            continue
        cap = next((c["id"] for c in reversed(caps) if c["i"] <= i), "c1")
        novo = {"id": f"a{len(afs) + 1}", "texto": str(a.get("texto") or a.get("em")), "em": a["em"], "i": i,
                "capitulo": cap, "tipo": a.get("tipo", "contexto"), "verificavel": bool(a.get("verificavel"))}
        for k in ("sessao", "setor", "evento", "valor", "unidade", "fonte"):
            if a.get(k) is not None:
                novo[k] = a[k]
        if a.get("carros"):
            novo["carros"] = [{"piloto": int(x["piloto"]), "volta": x["volta"] if x.get("volta") == "melhor" else int(x["volta"])}
                              for x in a["carros"]]
        if novo["verificavel"] and not (novo.get("sessao") and novo.get("carros")):
            avisos.append(f"afirmação {novo['id']} marcada verificável sem sessão/carro: virou não verificável")
            novo["verificavel"] = False
        if novo["verificavel"] and not novo.get("fonte"):
            novo["fonte"] = "OpenF1"
        afs.append(novo)
    afs.sort(key=lambda x: x["i"])
    for k, a in enumerate(afs):          # ids em ordem de fala; a SPEC recebe esta história e cita estes ids
        a["id"] = f"a{k + 1}"
    h = {"versao": 1, "titulo": str(bruto.get("titulo") or "sem título"), "tese": str(bruto.get("tese") or ""),
         "roteiro_hash": hash_texto(roteiro), "tempos": tempos, "capitulos": caps, "afirmacoes": afs,
         "fontes": [str(x) for x in bruto.get("fontes") or []], "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "avisos": avisos}
    erros = validar(h, "historia")
    if erros:
        raise ValueError("história inválida:\n  " + "\n  ".join(erros))
    return h


def aplicar(pasta: Path, resposta) -> dict:
    pasta = Path(pasta)
    roteiro, palavras, tempos, briefing = entradas(pasta)
    cache_resposta(pasta, "historia", prompt(roteiro, palavras, briefing), resposta)
    h = normalizar(resposta, palavras, roteiro, tempos)
    etapas.registrar(pasta, "historia", h, resumo=f"{len(h['capitulos'])} capítulos, {len(h['afirmacoes'])} afirmações"
                     + (f", {len(h['avisos'])} avisos" if h["avisos"] else ""))
    return h


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("prompt", "aplicar"):
        print(__doc__)
        return 2
    pasta = Path(argv[1])
    if argv[0] == "prompt":
        roteiro, palavras, tempos, briefing = entradas(pasta)
        p = prompt(roteiro, palavras, briefing)
        saida = pasta / "prompts" / "historia.prompt.txt"
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(p, encoding="utf-8")
        etapas.marcar(pasta, "historia", "prompt_pronto")
        em_cache = cache_resposta(pasta, "historia", p) is not None
        print(f"{saida} ({len(p)} caracteres; tempos {tempos}{'; resposta já em cache' if em_cache else ''})")
        return 0
    import json
    h = aplicar(pasta, json.loads(Path(argv[2]).read_text(encoding="utf-8")))
    print(f"historia.json: {len(h['capitulos'])} capítulos, {len(h['afirmacoes'])} afirmações")
    for a in h["avisos"]:
        print("  aviso:", a)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
