"""Ponte entre o painel (`app/servidor/horizontal_doc.py`) e o diretor documental, sobre o protocolo de arquivos.

O painel não importa os módulos do diretor (os nomes `comum`/`etapas` colidem com `tools/`): ele roda este arquivo
num processo à parte, manda um pedido JSON pela entrada padrão e lê a resposta JSON da saída padrão. Toda gravação do
`estado.json` passa por `etapas.py`. Nada aqui chama o modelo: as etapas que precisam dele (História, SPEC e pedido de
cena) só montam o prompt e devolvem o que o orquestrador deve rodar; a resposta entra por `aplicar`.

Pedido (stdin):  {"cmd": "resumo" | "passo" | "aprovar" | "pedir" | "retirar" | "aplicar"
                  | "storyboard" | "ajustar" | "previa" | "aprovar_cena" | "pedido_cena" | "final_checar", "pasta": "...", ...}
(storyboard do Rascunho, fase 7b: `ajustar` = ação direta na SPEC sem modelo, `pedido_cena` = pedido + prompt só da cena;
fase 7c: `final_checar` = confere se o vídeo final pode sair e devolve o comando do montador; quem roda é o motor do painel)
Resposta (stdout): {"ok": true, ...} ou {"ok": false, "erro": "..."}

Uso pelo orquestrador (a resposta do modelo é um arquivo JSON):
    python painel.py aplicar <pasta> historia resposta.json
    python painel.py aplicar <pasta> spec resposta.json [--cena <id>]
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import ativos as A
import etapas
import historia as H
import spec as S
import verificar as V
from comum import (AQUI, HORIZONTAL, cache_resposta, entradas, gravar_json, hash_dados, ler_json, limpa, observacoes,
                   palavras_do_roteiro)

PY = Path(sys.executable).name
TITULO = {"historia": "História", "spec": "SPEC", "ativos": "Ativos", "verificacao": "Verificação", "rascunho": "Rascunho"}
SEM_MONTADOR = "sem montador ainda"


class Recusa(Exception):
    """Ação que não vale no estado atual (o painel mostra a mensagem; HTTP 409)."""


def _montador_pronto() -> bool:
    return (HORIZONTAL / "montador" / "montar.py").exists()


def _calado(funcao, *args, **kw):
    """Roda uma função do diretor sem deixar o print dela sujar a resposta JSON."""
    with contextlib.redirect_stdout(io.StringIO()):
        return funcao(*args, **kw)


def _cmd_aplicar(pasta: Path, etapa: str, cena: str | None = None) -> str:
    alvo = AQUI / "painel.py"
    resposta = pasta / f"resposta_{etapa}{'_' + cena if cena else ''}.json"   # onde o orquestrador grava o JSON do modelo
    return f'{PY} "{alvo}" aplicar "{pasta}" {etapa} "{resposta}"' + (f" --cena {cena}" if cena else "")


# ---------------------------------------------------------------- entradas (roteiro e narração do card)
def sincronizar_entradas(pasta: Path, roteiro: str | None, palavras: str | None, narracao: str | None = None) -> list[str]:
    """Copia o roteiro aprovado e as palavras medidas da narração do card (voz guia ou sua gravação) para a pasta do
    horizontal. Só copia as palavras se forem do MESMO roteiro (mesma contagem); senão os tempos ficam estimados.
    Palavras novas com SPEC já feita = ressincronização (`ressincronizar`)."""
    avisos = []
    pasta.mkdir(parents=True, exist_ok=True)
    if roteiro and Path(roteiro).exists():
        texto = Path(roteiro).read_text(encoding="utf-8")
        destino = pasta / "roteiro.txt"
        if not destino.exists() or destino.read_text(encoding="utf-8") != texto:
            destino.write_text(texto, encoding="utf-8")
    if not (pasta / "roteiro.txt").exists():
        return avisos
    n_rot = len(palavras_do_roteiro((pasta / "roteiro.txt").read_text(encoding="utf-8")))
    atual = ler_json(pasta / "palavras.json")
    if isinstance(atual, list) and len(atual) != n_rot:   # tempos de um roteiro antigo: não valem mais
        (pasta / "palavras.json").unlink()
    if palavras and Path(palavras).exists():
        lista = json.loads(Path(palavras).read_text(encoding="utf-8"))
        valida = isinstance(lista, list) and all(isinstance(p, dict) and {"t", "i", "f"} <= set(p) for p in lista)
        if valida and len(lista) != n_rot:   # alinhar.py conta todo token ("—"); o diretor só palavras com letra/número
            lista = [p for p in lista if limpa(p["t"])]
        if valida and len(lista) == n_rot:
            if ler_json(pasta / "palavras.json") != lista:
                # ★ das cenas (storyboard) presos ao hash: a mesma cena só retemporizada pela narração continua aprovada
                aprov_arq = pasta / "storyboard" / "aprovacoes.json"
                antes = _hashes(pasta) if (pasta / "spec.json").exists() and ler_json(aprov_arq) else {}
                gravar_json(pasta / "palavras.json", lista)
                info = ressincronizar(pasta, narracao or "narração")
                if antes:
                    _manter_aprovacoes(pasta, antes, info)
        else:
            avisos.append(f"narração medida com {len(lista) if isinstance(lista, list) else '?'} palavras × roteiro com "
                          f"{n_rot}: tempos ficam estimados até medir de novo")
    return avisos


def ressincronizar(pasta: Path, narracao: str) -> dict | None:
    """Narração nova → SPEC retemporizada pelas palavras (`spec.retemporizar`): mesmas cenas, ids e índices; só mudam os
    tempos. Grava `ressinc.json` com as cenas afetadas (o painel mostra; a etapa Ressincronização do card usa)."""
    s = ler_json(pasta / "spec.json")
    info = {"quando": etapas.agora(), "narracao": narracao, "cenas": 0, "afetadas": []}
    if s and isinstance(s.get("cenas"), list):
        _, palavras, _, _ = entradas(pasta)
        nova = S.retemporizar(s, palavras)
        chave = lambda c: (c.get("i0"), c.get("i1"), c.get("t0"), c.get("t1"))   # noqa: E731
        info["cenas"] = len(nova["cenas"])
        info["afetadas"] = [b["id"] for a, b in zip(s["cenas"], nova["cenas"]) if chave(a) != chave(b)]
        if nova != s:
            etapas.retemporizar(pasta, nova, f"{len(info['afetadas'])} de {info['cenas']} cenas, {narracao}")
    gravar_json(pasta / "ressinc.json", info)
    return info


def _manter_aprovacoes(pasta: Path, antes: dict, info: dict | None) -> None:
    """Narração nova (voz guia → sua gravação): o hash de cada cena muda só porque os tempos mudaram. A cena que estava
    ★ NA VERSÃO VISTA continua ★ no hash novo (o Felipe aprovou o conteúdo preso às palavras, como no Runeterra a
    gravação aprovada vai direto ao render). Cena mexida depois do ★ continua sem ★."""
    arq = pasta / "storyboard" / "aprovacoes.json"
    aprov = ler_json(arq) or {}
    depois = _hashes(pasta)
    mantidas = []
    for cid, h in list(aprov.items()):
        if antes.get(cid) == h and depois.get(cid) and depois[cid] != h:
            aprov[cid] = depois[cid]
            mantidas.append(cid)
    if mantidas:
        gravar_json(arq, aprov)
    if info is not None:
        info["aprovacoes_mantidas"] = mantidas
        gravar_json(pasta / "ressinc.json", info)


def sincronizar_observacoes(pasta: Path, arquivo: str | None) -> None:
    """Observações gerais do card (`<projeto>/observacoes.json`, gravado pelo painel) → `observacoes.txt` aqui, que
    entra nos prompts da História, da SPEC e dos pedidos por cena. Sem o caminho (chamada de fora do painel), não mexe."""
    if arquivo is None:
        return
    lista = ler_json(Path(arquivo)) if Path(arquivo).exists() else None
    destino = pasta / "observacoes.txt"
    texto = "\n".join(f"- ({str(o.get('criada_em', ''))[:10]}) {str(o.get('texto', '')).strip()}"
                      for o in (lista if isinstance(lista, list) else []) if str(o.get("texto", "")).strip())
    if not texto:
        destino.unlink(missing_ok=True)
    elif not destino.exists() or destino.read_text(encoding="utf-8") != texto + "\n":
        pasta.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto + "\n", encoding="utf-8")


# ---------------------------------------------------------------- leitura
def _orquestrador(pasta: Path, estado: dict) -> list[dict]:
    """O que espera o modelo: prompt gravado e ainda sem resposta aplicada."""
    tarefas = []
    pr = pasta / "prompts"
    if estado["etapas"]["historia"]["status"] == "prompt_pronto" and (pr / "historia.prompt.txt").exists():
        tarefas.append({"etapa": "historia", "cena": None, "prompt": str(pr / "historia.prompt.txt"),
                        "comando": _cmd_aplicar(pasta, "historia")})
    if estado["etapas"]["spec"]["status"] != "prompt_pronto":
        return tarefas
    # SPEC: ou o prompt inteiro, ou um por cena (o que foi gravado por último vale)
    cheio = pr / "spec.prompt.txt"
    t_cheio = cheio.stat().st_mtime if cheio.exists() else -1
    cenas = sorted({p["cena"] for p in etapas.pedidos_abertos(estado, "spec") if p.get("cena")})
    por_cena = [(c, pr / f"pedido_{c}.prompt.txt") for c in cenas if (pr / f"pedido_{c}.prompt.txt").exists()]
    por_cena = [(c, a) for c, a in por_cena if a.stat().st_mtime >= t_cheio]
    if por_cena:
        tarefas += [{"etapa": "spec", "cena": c, "prompt": str(a), "comando": _cmd_aplicar(pasta, "spec", c)} for c, a in por_cena]
    elif cheio.exists():
        tarefas.append({"etapa": "spec", "cena": None, "prompt": str(cheio), "comando": _cmd_aplicar(pasta, "spec")})
    return tarefas


def resumo(pasta: Path, slug: str) -> dict:
    estado = etapas.ler(pasta, slug)   # só lê (sem estado.json, devolve um novo sem gravar)
    _, palavras, tempos, _ = entradas(pasta) if (pasta / "roteiro.txt").exists() else (None, [], None, None)
    ativos = ler_json(pasta / "ativos.json")
    return {"estado": estado, "titulos": TITULO, "aprovacao": etapas.APROVACAO,
            "entradas": {"roteiro": (pasta / "roteiro.txt").exists(), "palavras": len(palavras), "tempos": tempos,
                         "briefing": (pasta / "briefing.txt").exists(),
                         "observacoes": (pasta / "observacoes.txt").exists()},
            "historia": ler_json(pasta / "historia.json"), "spec": ler_json(pasta / "spec.json"),
            "ativos": ativos, "verificacao": ler_json(pasta / etapas.ARQUIVO["verificacao"]),
            "orquestrador": _orquestrador(pasta, estado),
            "montador": _montador_pronto(), "rascunho": None if _montador_pronto() else SEM_MONTADOR,
            "rascunho_info": ler_json(pasta / etapas.ARQUIVO["rascunho"]),
            "ressinc": ler_json(pasta / "ressinc.json"),   # última troca de narração (cenas retemporizadas)
            # vídeo final (fase 7c): o último render e o hash da SPEC agora (mudou depois do final = desatualizado)
            "final": ler_json(pasta / "final" / "final.json"), "final_falhou": ler_json(pasta / "final" / "falhou.json"),
            "spec_hash": hash_dados(ler_json(pasta / "spec.json")) if (pasta / "spec.json").exists() else None,
            "rascunho_video": str(pasta / "rascunho" / "rascunho.mp4") if (pasta / "rascunho" / "rascunho.mp4").exists() else None}


# ---------------------------------------------------------------- passos
def _pedidos_no_prompt(pedidos: list[dict], spec: dict | None = None) -> str:
    if not pedidos:
        return ""
    em = {c["id"]: c["em"] for c in (spec or {}).get("cenas", [])}
    linhas = [f"- {'cena ' + p['cena'] + ' (“' + em.get(p['cena'], '?') + '”): ' if p.get('cena') else ''}{p['texto']}"
              for p in pedidos]
    return "\n\n## Pedidos do Felipe para esta versão (atenda todos)\n" + "\n".join(linhas) + "\n"


def _gravar_prompt(pasta: Path, nome: str, texto: str) -> Path:
    arq = pasta / "prompts" / nome
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(texto, encoding="utf-8")
    return arq


def _exige_aprovado(estado: dict, etapa: str, para: str) -> None:
    st = estado["etapas"][etapa]["status"]
    if st != "aprovado":
        raise Recusa(f"aprove a {TITULO[etapa]} antes de {para} (está '{st}')")


def passo(pasta: Path, slug: str, nome: str) -> dict:
    estado = etapas.ler(pasta, slug)
    if nome in ("historia", "spec"):
        if not (pasta / "roteiro.txt").exists():
            raise Recusa("falta o roteiro aprovado do card (roteiro.txt)")
        reg = estado["etapas"][nome]
        abertos = etapas.pedidos_abertos(estado, nome)
        if reg["status"] in ("gerado", "aprovado") and not abertos:
            raise Recusa(f"{TITULO[nome]} já foi gerada: peça uma mudança para refazer")
        roteiro, palavras, _, briefing = entradas(pasta)
        if nome == "historia":
            spec_atual = None
        else:
            _exige_aprovado(estado, "historia", "gerar a SPEC")
            spec_atual = ler_json(pasta / "spec.json")
        # pedido só de cenas, com SPEC já existente: um prompt curto por cena (as outras ficam como estão)
        por_cena = nome == "spec" and spec_atual and abertos and all(p.get("cena") for p in abertos)
        if por_cena:
            ids = {c["id"] for c in spec_atual["cenas"]}
            cenas = sorted({p["cena"] for p in abertos if p["cena"] in ids})
            if not cenas:
                raise Recusa("os pedidos apontam para cenas que não existem mais nesta SPEC")
            arqs = [str(_gravar_prompt(pasta, f"pedido_{c}.prompt.txt", S.prompt_pedido(pasta, c))) for c in cenas]
            etapas.marcar(pasta, "spec", "prompt_pronto", f"pedido de mudança em {len(cenas)} cena(s)")
            return {"precisa_modelo": True, "prompts": arqs,
                    "comandos": [_cmd_aplicar(pasta, "spec", c) for c in cenas]}
        if nome == "historia":
            base = H.prompt(roteiro, palavras, briefing, observacoes(pasta))
        else:
            base = S.prompt(roteiro, palavras, ler_json(pasta / "historia.json"), briefing, observacoes(pasta))
        texto = base + _pedidos_no_prompt(abertos, spec_atual)
        arq = _gravar_prompt(pasta, f"{nome}.prompt.txt", texto)
        guardada = None if abertos else cache_resposta(pasta, nome, base)
        if guardada is not None:   # mesmo prompt já respondido: aplica sem gastar cota
            aplicar(pasta, nome, guardada)
            return {"precisa_modelo": False, "do_cache": True}
        etapas.marcar(pasta, nome, "prompt_pronto", "prompt pronto: aguardando o orquestrador")
        return {"precisa_modelo": True, "prompts": [str(arq)], "comandos": [_cmd_aplicar(pasta, nome)]}
    if nome == "ativos":
        _exige_aprovado(estado, "spec", "resolver os ativos")
        a = _calado(A.aplicar, pasta)
        faltas = [i for i in a["itens"] if i["status"] == "falta" and i.get("comando")]
        return {"precisa_modelo": False, "resumo": a["resumo"],
                "produzir": f'{PY} "{AQUI / "ativos.py"}" "{pasta}" --produzir' if faltas else None}
    if nome == "verificacao":
        _exige_aprovado(estado, "spec", "verificar")
        v = _calado(V.aplicar, pasta)
        return {"precisa_modelo": False, "status": v["status"], "contagem": v["contagem"]}
    if nome == "rascunho":
        if not _montador_pronto():
            raise Recusa(SEM_MONTADOR)
        return _rascunho(pasta, estado)
    raise Recusa(f"passo desconhecido: {nome}")


MONTANDO_MAX_S = 3 * 3600   # "andamento" mais velho que isto = montagem morreu (pode montar de novo)


def _rascunho(pasta: Path, estado: dict) -> dict:
    """Confere TUDO o que o montador precisa (rápido, sem render) e, se dá, dispara `montador/montar.py --registrar`
    num processo à parte (o render leva minutos). O montador grava `gerado` ou `falhou` no estado.json ao terminar."""
    import time

    reg = estado["etapas"]["rascunho"]
    if reg["status"] == "andamento":
        trava = ler_json(pasta / "rascunho" / "montando.json") or {}
        if time.time() - trava.get("inicio", 0) < MONTANDO_MAX_S:
            raise Recusa("o rascunho já está sendo montado (aguarde; o card muda sozinho ao terminar)")
    mdir = HORIZONTAL / "montador"
    sys.path.insert(0, str(mdir))
    import montar as MT   # noqa: PLC0415 (só aqui: render/numpy não carregam nas outras chamadas da ponte)

    try:
        plano = _calado(MT.planejar, pasta)
    except MT.NaoMonta as e:
        raise Recusa(str(e)) from None
    (pasta / "rascunho").mkdir(parents=True, exist_ok=True)
    log = pasta / "rascunho" / "montagem.log"
    gravar_json(pasta / "rascunho" / "montando.json", {"inicio": time.time()})
    etapas.marcar(pasta, "rascunho", "andamento", f"montando {len(plano['jobs'])} cenas…")
    fh = open(log, "w", encoding="utf-8")   # noqa: SIM115 (fica com o processo filho)
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
    subprocess.Popen([sys.executable, str(mdir / "montar.py"), str(pasta), "--registrar"], stdout=fh, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, cwd=str(mdir), creationflags=flags, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return {"precisa_modelo": False, "montando": True, "log": str(log), "avisos": plano["avisos"]}


# ---------------------------------------------------------------- aprovações e pedidos
def aprovar(pasta: Path, etapa: str) -> dict:
    if etapa == "rascunho" and not _montador_pronto():
        raise Recusa(SEM_MONTADOR)
    if not etapas.APROVACAO.get(etapa):
        raise Recusa(f"{etapa} não tem aprovação (★ só em história, SPEC e rascunho)")
    try:
        return etapas.aprovar(pasta, etapa)
    except ValueError as e:
        raise Recusa(str(e)) from None


def pedir(pasta: Path, etapa: str, texto: str, cena: str | None) -> dict:
    if etapa not in etapas.NOMES:
        raise Recusa(f"etapa desconhecida: {etapa}")
    if not texto.strip():
        raise Recusa("escreva o pedido")
    if cena:
        s = ler_json(pasta / "spec.json") or {"cenas": []}
        if etapa != "spec" or cena not in {c["id"] for c in s["cenas"]}:
            raise Recusa(f"cena {cena} não existe na SPEC")
    return etapas.pedir(pasta, etapa, texto.strip(), cena)


def retirar(pasta: Path, pid: str) -> dict:
    """O Felipe desistiu de um pedido aberto. Sem outros pedidos abertos, a etapa volta a `gerado` (aprovar de novo)."""
    estado = etapas.ler(pasta)
    p = next((x for x in estado["pedidos"] if x["id"] == pid and x["status"] == "aberto"), None)
    if not p:
        raise Recusa(f"pedido {pid} não está aberto")
    p["status"], p["resposta"] = "recusado", "retirado pelo Felipe"
    reg = estado["etapas"][p["etapa"]]
    if reg["status"] == "mudanca_pedida" and not etapas.pedidos_abertos(estado, p["etapa"]):
        reg["status"] = "gerado"
    etapas._log(estado, f"{p['etapa']}: pedido {pid} retirado")
    etapas.gravar(pasta, estado)
    return estado


def aplicar(pasta: Path, etapa: str, resposta, cena: str | None = None) -> dict:
    """Resposta do modelo (orquestrador) → arquivo da etapa; os pedidos atendidos por ela saem da lista."""
    estado = etapas.ler(pasta)
    abertos = etapas.pedidos_abertos(estado, etapa)
    if etapa == "historia":
        _calado(H.aplicar, pasta, resposta)
    elif etapa == "spec" and cena:
        roteiro, palavras, _, _ = entradas(pasta)
        historia = ler_json(pasta / "historia.json")
        nova = resposta.get("cena", resposta) if isinstance(resposta, dict) else resposta
        s = S.trocar_cena(ler_json(pasta / "spec.json"), cena, nova, palavras, historia, roteiro)
        etapas.registrar(pasta, "spec", s, base=historia, resumo=f"{len(s['cenas'])} cenas (cena {cena} refeita)")
        abertos = [p for p in abertos if p.get("cena") == cena]
    elif etapa == "spec":
        _calado(S.aplicar, pasta, resposta)
    else:
        raise Recusa(f"{etapa} não recebe resposta do modelo")
    if abertos:
        etapas.atender(pasta, [p["id"] for p in abertos], "nova versão gerada")
    if etapa == "spec" and cena:   # outras cenas com pedido e prompt pronto continuam esperando o modelo
        resto = {p["cena"] for p in etapas.pedidos_abertos(etapas.ler(pasta), "spec") if p.get("cena")}
        if any((pasta / "prompts" / f"pedido_{c}.prompt.txt").exists() for c in resto):
            etapas.marcar(pasta, "spec", "prompt_pronto", f"pedido de mudança em {len(resto)} cena(s)")
    return etapas.ler(pasta)


# ---------------------------------------------------------------- storyboard do Rascunho (fase 7b)
def _sb():
    mdir = str(HORIZONTAL / "montador")
    if mdir not in sys.path:
        sys.path.insert(0, mdir)
    import storyboard as SB   # noqa: PLC0415 (só aqui: o storyboard planeja as cenas pelo montador)
    return SB


def _hashes(pasta: Path) -> dict:
    try:
        p = _calado(_sb()._plano, pasta)
    except Exception:   # noqa: BLE001 — sem plano não há o que comparar
        return {}
    return {j["cena"]: j["hash"] for j in p["jobs"]}


def disparar_previa(pasta: Path, cenas: list[str] | None) -> dict:
    """Prévia (trecho + quadros) das cenas num processo à parte. Já gerando: as cenas entram na fila do mesmo processo."""
    import time

    SB = _sb()
    sb = SB.pasta_sb(pasta)
    sb.mkdir(parents=True, exist_ok=True)
    spec = ler_json(pasta / "spec.json") or {"cenas": []}
    ids = [c["id"] for c in spec["cenas"]] if not cenas else [c for c in cenas if c in {x["id"] for x in spec["cenas"]}]
    if not ids:
        raise Recusa("nenhuma cena para a prévia")
    g = SB._gerando(pasta)
    if g:
        fila = ler_json(sb / "fila.json") or []
        gravar_json(sb / "fila.json", sorted(set(fila) | set(ids)))
        gravar_json(sb / "gerando.json", {**g, "cenas": sorted(set(g.get("cenas", [])) | set(ids))})
        return {"na_fila": ids}
    gravar_json(sb / "gerando.json", {"inicio": time.time(), "cenas": ids})
    log = sb / "previa.log"
    fh = open(log, "a", encoding="utf-8")   # noqa: SIM115 (fica com o processo filho)
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
    subprocess.Popen([sys.executable, str(HORIZONTAL / "montador" / "storyboard.py"), str(pasta), "previa", ",".join(ids)],
                     stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=str(HORIZONTAL / "montador"),
                     creationflags=flags, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return {"gerando": ids, "log": str(log)}


def ajustar_cena(pasta: Path, cena: str, acao: dict, previa: bool = True) -> dict:
    """Ação direta do storyboard → spec.json na hora (sem modelo); Ativos e Verificação rodam de novo (offline) e só as
    cenas cujo trecho mudou (hash da receita) ganham prévia nova."""
    import ajustes

    estado = etapas.ler(pasta)
    spec_atual = ler_json(pasta / "spec.json")
    if not spec_atual:
        raise Recusa("sem SPEC ainda")
    _, palavras, _, _ = entradas(pasta)
    antes = _hashes(pasta)
    try:
        nova, desc, novo_id = ajustes.aplicar(spec_atual, cena, acao, palavras)
        etapas.ajustar(pasta, "spec", nova, f"cena {cena}: {desc}")
    except ValueError as e:
        raise Recusa(str(e)) from None
    hist = ler_json(pasta / "ajustes_diretos.json") or []
    hist.append({"em": etapas.agora(), "cena": cena, "cena_depois": novo_id, "acao": acao, "descricao": desc})
    gravar_json(pasta / "ajustes_diretos.json", hist[-500:])
    avisos = []
    for nome, mod in (("ativos", A), ("verificacao", V)):   # offline e rápidos: a SPEC nova sai já conferida
        if estado["etapas"][nome]["status"] != "pendente":
            try:
                _calado(mod.aplicar, pasta)
            except Exception as e:   # noqa: BLE001 — fica `desatualizado` (etapas.ajustar) e o motivo volta para a tela
                avisos.append(f"{TITULO[nome]} não rodou de novo ({type(e).__name__}: {str(e)[:160]}): rode pelo botão")
    depois = _hashes(pasta)
    afetadas = [c for c, h in depois.items() if antes.get(c) != h]
    disparo = disparar_previa(pasta, afetadas) if (previa and afetadas) else None
    return {"descricao": desc, "cena": novo_id, "afetadas": afetadas, "previa": disparo, "avisos": avisos}


def pedido_cena(pasta: Path, slug: str, cena: str, texto: str, origem: str = "texto") -> dict:
    """Qualquer pedido que não é ação direta (texto ou voz): pedido da cena na SPEC + o prompt SÓ dessa cena para o
    orquestrador (`spec.prompt_pedido`), na mesma chamada."""
    t = texto.strip()
    if origem == "voz":
        t = f"{t} (ditado por voz)"
    estado = pedir(pasta, "spec", t, cena)
    try:
        r = passo(pasta, slug, "spec")
    except Recusa as e:   # ex.: história não aprovada; o pedido fica aberto e o motivo volta
        return {"estado": estado, "prompt": None, "aviso": str(e)}
    return {"estado": etapas.ler(pasta), "prompt": r.get("prompts"), "comandos": r.get("comandos")}


# ---------------------------------------------------------------- vídeo final (fase 7c)
def final_checar(pasta: Path, narracao: str | None) -> dict:
    """O vídeo final só sai com: a sua narração gravada (tempos da gravação, SPEC ressincronizada), a SPEC ★, TODAS as
    cenas ★ no storyboard na versão atual e a verificação da SPEC atual sem erro. Ativos e Verificação rodam de novo
    aqui (offline), sobre a SPEC de agora. Devolve o comando do montador (o motor do painel roda
    num processo à parte, com a barra de progresso por bloco)."""
    estado = etapas.ler(pasta)
    faltas = []
    if narracao != "gravacao" or entradas(pasta)[2] != "medidos":
        faltas.append("a narração que vale ainda não é a sua gravação: grave, aprove a gravação e espere a ressincronização")
    if estado["etapas"]["spec"]["status"] != "aprovado":
        faltas.append(f"a SPEC está '{estado['etapas']['spec']['status']}': aprove ★")
    spec = ler_json(pasta / "spec.json") or {"cenas": []}
    hashes = _hashes(pasta)
    aprov = ler_json(pasta / "storyboard" / "aprovacoes.json") or {}
    sem = [f"{n + 1}" for n, c in enumerate(spec["cenas"]) if not hashes.get(c["id"]) or aprov.get(c["id"]) != hashes[c["id"]]]
    if not spec["cenas"]:
        faltas.append("sem SPEC")
    elif sem:
        faltas.append(f"aprove ★ no storyboard {len(sem)} de {len(spec['cenas'])} cena(s) na versão atual "
                      f"(cena{'s' if len(sem) > 1 else ''} {', '.join(sem[:20])}{'…' if len(sem) > 20 else ''})")
    if faltas:
        raise Recusa("vídeo final ainda não: " + " | ".join(faltas))
    for nome, mod in (("ativos", A), ("verificacao", V)):   # sempre de novo (offline, rápidos): o final confere a SPEC de agora
        try:
            _calado(mod.aplicar, pasta)
        except Exception as e:   # noqa: BLE001 — o motivo vai para a tela
            raise Recusa(f"vídeo final ainda não: {TITULO[nome]} não rodou ({type(e).__name__}: {str(e)[:200]})") from None
    v = ler_json(pasta / etapas.ARQUIVO["verificacao"]) or {}
    if v.get("status") == "reprovado":
        raise Recusa(f"vídeo final ainda não: a verificação reprovou a SPEC atual ({len(v.get('erros', []))} erro(s)); veja a aba Verificação")
    mdir = HORIZONTAL / "montador"
    sys.path.insert(0, str(mdir))
    import montar as MT   # noqa: PLC0415

    try:
        plano = _calado(MT.planejar, pasta, modo="final")
    except MT.NaoMonta as e:
        raise Recusa(str(e)) from None
    return {"cenas": len(plano["jobs"]), "avisos": plano["avisos"], "pasta_montador": str(mdir),
            "comando": [str(mdir / "montar.py"), str(pasta), "--final", "--registrar", "--progresso"]}


# ---------------------------------------------------------------- entrada
def executar(pedido: dict) -> dict:
    pasta = Path(pedido["pasta"])
    slug = pedido.get("slug") or pasta.parent.name
    cmd = pedido["cmd"]
    avisos = (sincronizar_entradas(pasta, pedido.get("roteiro"), pedido.get("palavras"), pedido.get("narracao"))
              if cmd in ("resumo", "passo") else [])
    if cmd in ("resumo", "passo"):
        sincronizar_observacoes(pasta, pedido.get("observacoes"))
    if cmd == "resumo":
        r = resumo(pasta, slug)
    elif cmd == "passo":
        r = {"passo": passo(pasta, slug, pedido["passo"])}
    elif cmd == "aprovar":
        r = {"estado": aprovar(pasta, pedido["etapa"])}
    elif cmd == "pedir":
        r = {"estado": pedir(pasta, pedido["etapa"], pedido.get("texto", ""), pedido.get("cena"))}
    elif cmd == "retirar":
        r = {"estado": retirar(pasta, pedido["id"])}
    elif cmd == "aplicar":
        r = {"estado": aplicar(pasta, pedido["etapa"], pedido["resposta"], pedido.get("cena"))}
    elif cmd == "storyboard":
        r = {"storyboard": _calado(_sb().ler, pasta, pedido.get("raiz"))}
    elif cmd == "ajustar":
        r = {"ajuste": ajustar_cena(pasta, pedido["cena"], pedido["acao"], pedido.get("previa", True))}
    elif cmd == "previa":
        r = {"previa": disparar_previa(pasta, pedido.get("cenas"))}
    elif cmd == "aprovar_cena":
        try:
            r = {"aprovacoes": _calado(_sb().aprovar, pasta, pedido["cena"])}
        except ValueError as e:
            raise Recusa(str(e)) from None
    elif cmd == "final_checar":
        r = {"final": final_checar(pasta, pedido.get("narracao"))}
    elif cmd == "pedido_cena":
        if not str(pedido.get("texto", "")).strip():
            raise Recusa("escreva (ou dite) o pedido")
        r = {"pedido": pedido_cena(pasta, slug, pedido["cena"], pedido["texto"], pedido.get("origem", "texto"))}
    else:
        raise Recusa(f"comando desconhecido: {cmd}")
    return {"ok": True, "avisos_entrada": avisos, **r}


def _saida(dados: dict) -> None:
    sys.stdout.buffer.write(json.dumps(dados, ensure_ascii=False).encode("utf-8"))


def _main(argv: list[str]) -> int:
    if argv and argv[0] == "aplicar":   # orquestrador, pela linha de comando
        sys.stdout.reconfigure(encoding="utf-8")
        if len(argv) < 4:
            print(__doc__)
            return 2
        cena = argv[argv.index("--cena") + 1] if "--cena" in argv else None
        resposta = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        e = aplicar(Path(argv[1]), argv[2], resposta, cena)
        print(f"{argv[2]}: {e['etapas'][argv[2]]['status']} ({e['etapas'][argv[2]].get('resumo', '')})")
        return 0
    try:
        _saida(executar(json.loads(sys.stdin.buffer.read().decode("utf-8"))))
    except Recusa as e:
        _saida({"ok": False, "erro": str(e)})
    except (ValueError, FileNotFoundError, KeyError) as e:
        _saida({"ok": False, "erro": f"{type(e).__name__}: {e}"})
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
