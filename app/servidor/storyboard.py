"""Storyboard: revisão cena a cena do rascunho. Os ajustes do Felipe ficam em direcao/ajustes.json
e são aplicados por cima do plano e das escolhas do diretor na próxima montagem."""
from __future__ import annotations

import json
from pathlib import Path

from .banco import RAIZ

TIPOS = ["cartao", "telacheia", "recorte", "meio", "texto", "citacao", "mosaico", "dividida", "lista", "clipe",
         "dialogo", "hub", "capa"]


def _ler(p: Path, padrao):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else padrao


def _rel(caminho: str) -> str:
    """Miniaturas ficam em dados/ (acervo e tomadas): caminho relativo para /api/arquivo."""
    try:
        return Path(caminho).resolve().relative_to(RAIZ.resolve()).as_posix()
    except ValueError:
        return caminho


def carregar(pasta: Path) -> dict:
    dirc = pasta / "direcao"
    return {"plano": _ler(dirc / "plano.json", {"cenas": []}), "necs": _ler(dirc / "candidatos.json", []),
            "escolhas": _ler(dirc / "escolhas.json", {}), "ajustes": _ler(dirc / "ajustes.json", {}),
            "direcao": _ler(dirc / "direcao.json", {"cenas": [], "palavras": []}),
            "roteiro": (dirc / "roteiro.txt").read_text(encoding="utf-8") if (dirc / "roteiro.txt").exists() else ""}


def salvar_ajustes(pasta: Path, ajustes: dict) -> None:
    (pasta / "direcao" / "ajustes.json").write_text(json.dumps(ajustes, ensure_ascii=False, indent=1), encoding="utf-8")


def cenas(pasta: Path) -> list[dict]:
    """Lista para a tela: uma entrada por cena do PLANO (inclusive recusadas/removidas)."""
    d = carregar(pasta)
    toks = d["roteiro"].split()
    palavras = d["direcao"].get("palavras") or []
    montadas = {c.get("id") or f"C{c.get('k')}": c for c in d["direcao"].get("cenas", [])}
    sons = {s.get("id") or f"C{s.get('k')}" for s in d["direcao"].get("sons", [])}
    necs = {n["id"]: n for n in d["necs"]}
    inicios = []
    saida = []
    for k, c in enumerate(d["plano"].get("cenas", [])):
        cid = _id(c, k)
        aj = d["ajustes"].get(cid, {})
        nec = necs.get(cid)
        esc = d["escolhas"].get(cid) or {}
        cands = [{"idx": i, "nome": x["nome"], "tipo": x["tipo"], "miniatura": _rel(x["miniatura"])}
                 for i, x in enumerate(nec["candidatos"])] if nec else []
        escolhido = None
        if "candidato" in aj and cands:
            escolhido = cands[aj["candidato"]] if aj["candidato"] < len(cands) else None
        elif esc.get("escolha") and cands:
            escolhido = cands[esc["escolha"] - 1]
        m = montadas.get(cid)
        inicio = palavras[m["de"]]["i"] if m and palavras else None
        inicios.append(inicio)
        frase = ""
        if m and toks:
            frase = " ".join(toks[m["de"]:m["ate"] + 1])
        saida.append({
            "k": k, "id": cid, "secao": c.get("secao"), "conferir": bool(c.get("conferir")) and not aj.get("conferido"),
            "tipo": aj.get("tipo", c["tipo"]), "legenda": aj.get("legenda", c.get("legenda")),
            "frase": frase, "inicio": inicio, "busca": (c.get("busca") or {}).get("o_que"),
            "escolhido": escolhido, "candidatos": cands, "recusada": nec is not None and not esc.get("escolha"),
            "no_rascunho": m is not None, "removida": bool(aj.get("removida")),
            "comentario": aj.get("comentario"), "comentario_aplicado": bool(aj.get("comentario_aplicado")),
            "motivo": esc.get("motivo"), "ajustada": bool(aj),
            "som": None if aj.get("sem_som") else (c.get("som") or {}).get("o_que"),
            "som_no_rascunho": cid in sons,
        })
    # fim de cada cena = início da próxima montada
    for i, s in enumerate(saida):
        prox = next((x["inicio"] for x in saida[i + 1:] if x["inicio"] is not None), None)
        s["fim"] = prox if prox is not None else (palavras[-1]["f"] if palavras else None)
    return saida


def _id(c: dict, k: int) -> str:
    """Id estável da cena (planos por bloco); planos antigos usavam a posição."""
    return c.get("id") or f"C{k}"


def ajustar(pasta: Path, cid: str, acao: dict) -> dict:
    """Aplica um ajuste do Felipe a uma cena (pelo id estável). Ações: candidato, usar_midia, legenda, tipo,
    remover, sem_som, conferido, restaurar, comentario."""
    d = carregar(pasta)
    if cid not in {_id(c, k) for k, c in enumerate(d["plano"].get("cenas", []))}:
        raise ValueError("cena não encontrada (o plano mudou? recarregue o storyboard)")
    aj = d["ajustes"].setdefault(cid, {})
    tipo = acao["acao"]
    if tipo == "candidato":
        aj["candidato"] = int(acao["idx"])
    elif tipo == "usar_midia":  # resultado de uma busca manual no acervo: vira um candidato novo
        necs = d["necs"]
        nec = next((n for n in necs if n["id"] == cid), None)
        if nec is None:
            raise ValueError("esta cena não usa imagem")
        cand = {"tipo": "midia", "id": int(acao["midia_id"]), "nome": acao["nome"], "nota": 1.0,
                "miniatura": str(RAIZ / acao["miniatura"])}
        nec["candidatos"].append(cand)
        aj["candidato"] = len(nec["candidatos"]) - 1
        (pasta / "direcao" / "candidatos.json").write_text(json.dumps(necs, ensure_ascii=False, indent=1), encoding="utf-8")
    elif tipo == "legenda":
        aj["legenda"] = acao["texto"].strip()
    elif tipo == "tipo":
        if acao["tipo"] not in TIPOS:
            raise ValueError("tipo inválido")
        aj["tipo"] = acao["tipo"]
    elif tipo == "remover":
        aj["removida"] = True
    elif tipo == "sem_som":
        aj["sem_som"] = True
    elif tipo == "conferido":  # o Felipe olhou a cena cuja frase mudou no roteiro e está ok
        aj["conferido"] = True
    elif tipo == "restaurar":
        d["ajustes"].pop(cid, None)
    elif tipo == "comentario":
        aj["comentario"] = acao["texto"].strip()
        aj["comentario_aplicado"] = False
    else:
        raise ValueError(f"ação desconhecida: {tipo}")
    if cid in d["ajustes"] and not d["ajustes"][cid]:
        d["ajustes"].pop(cid)
    salvar_ajustes(pasta, d["ajustes"])
    return d["ajustes"].get(cid, {})


def aplicar(plano: dict, escolhas: dict, ajustes: dict) -> tuple[dict, dict]:
    """Ajustes por cima do plano/escolhas do diretor (usado antes de montar). Ajustes de cenas que não existem
    mais (bloco replanejado) são ignorados."""
    plano = json.loads(json.dumps(plano))
    escolhas = dict(escolhas)
    por_id = {_id(c, k): c for k, c in enumerate(plano["cenas"])}
    for cid, aj in ajustes.items():
        c = por_id.get(cid)
        if c is None:
            continue
        k = cid
        if aj.get("removida"):
            c["removida"] = True
        if aj.get("sem_som"):
            c["som"] = None
        if "legenda" in aj:
            c["legenda"] = aj["legenda"] or None
        if "tipo" in aj:
            c["tipo"] = aj["tipo"]
        if "candidato" in aj:
            escolhas[k] = {**(escolhas.get(k) or {}), "escolha": aj["candidato"] + 1, "fixa": True}
    return plano, escolhas


def pendentes_para_o_diretor(ajustes: dict) -> list[str]:
    return [cid for cid, a in ajustes.items() if a.get("comentario") and not a.get("comentario_aplicado")]


def buscar_no_acervo(consulta: str, n: int = 12) -> list[dict]:
    import sys

    sys.path.insert(0, str(RAIZ / "tools"))
    sys.path.insert(0, str(RAIZ / "tools" / "acervo"))
    from busca_semantica import buscar
    from comum import abrir_acervo

    con = abrir_acervo()
    # 1) etiquetas em português (nome do arquivo, personagens, descrição, uso) — acerta nomes e termos exatos
    termos = [t for t in consulta.lower().split() if len(t) > 2]
    pontos: dict[int, float] = {}
    for r in con.execute("SELECT id, nome, personagens, descricao, uso FROM midias WHERE tipo IN ('imagem','gif') "
                         "AND IFNULL(categoria,'') != 'canal'"):
        texto = " ".join(str(r[x] or "") for x in ("nome", "personagens", "descricao", "uso")).lower()
        acertos = sum(1 for t in termos if t in texto)
        if acertos:
            pontos[r["id"]] = acertos / len(termos)
    # 2) significado (CLIP) — completa com o que as etiquetas não descrevem
    for mid, nota in buscar(consulta, 60):
        pontos[mid] = pontos.get(mid, 0) + nota
    saida = []
    for mid, nota in sorted(pontos.items(), key=lambda x: -x[1]):
        r = con.execute("SELECT nome, tipo, categoria FROM midias WHERE id=?", (mid,)).fetchone()
        if r["tipo"] not in ("imagem", "gif") or r["categoria"] == "canal":
            continue
        saida.append({"midia_id": mid, "nome": r["nome"], "nota": round(nota, 3),
                      "miniatura": f"dados/acervo/miniaturas/{mid}.jpg"})
        if len(saida) >= n:
            break
    return saida
