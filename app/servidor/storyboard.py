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


def _arq_pendentes(pasta: Path) -> Path:
    return pasta / "direcao" / "ajustes_pendentes.json"


def _arq_foto(pasta: Path) -> Path:
    return pasta / "direcao" / "ajustes_no_rascunho.json"


def pendentes(pasta: Path) -> list[str]:
    """Cenas cujos ajustes estão DIFERENTES dos que o último rascunho usou (comparação com a foto tirada quando o
    motor leu os ajustes). Mexer e desfazer volta a ficar igual → deixa de ser pendente."""
    foto = _ler(_arq_foto(pasta), None)
    if foto is None:  # projetos de antes da foto: lista de cenas mexidas
        return _ler(_arq_pendentes(pasta), [])
    atuais = _ler(pasta / "direcao" / "ajustes.json", {})
    return [cid for cid in sorted(set(atuais) | set(foto)) if atuais.get(cid) != foto.get(cid)]


def marcar_pendente(pasta: Path, cid: str) -> None:
    lista = pendentes(pasta)
    if cid not in lista:
        _arq_pendentes(pasta).write_text(json.dumps(lista + [cid], ensure_ascii=False), encoding="utf-8")


def limpar_pendentes(pasta: Path) -> None:
    """O motor leu os ajustes para montar um rascunho: tudo o que estava pendente entrou nessa fila (foto dos
    ajustes usados, para comparar depois)."""
    _arq_foto(pasta).write_text(json.dumps(_ler(pasta / "direcao" / "ajustes.json", {}), ensure_ascii=False),
                                encoding="utf-8")
    _arq_pendentes(pasta).unlink(missing_ok=True)


def cenas(pasta: Path) -> list[dict]:
    """Lista para a tela: uma entrada por cena do PLANO (inclusive recusadas/removidas)."""
    import sys

    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from candidatos import numeros_das_cenas
    sys.path.insert(0, str(RAIZ / "tools"))
    from comum import abrir_acervo

    acervo = abrir_acervo()
    pend = set(pendentes(pasta))
    d = carregar(pasta)
    numeros = numeros_das_cenas(d["plano"], pasta / "direcao")
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
        if aj.get("midia") and nec:  # pela identidade (a posição muda se a busca for refeita)
            escolhido = next((cands[i] for i, x in enumerate(nec["candidatos"]) if [x["tipo"], x["id"]] == list(aj["midia"])), None)
            if escolhido is None and aj["midia"][0] == "midia":  # escolha sua que saiu da lista (busca refeita)
                escolhido = {"idx": -1, "nome": "(sua escolha)", "tipo": "midia",
                             "miniatura": f"dados/acervo/miniaturas/{aj['midia'][1]}.jpg"}
        elif "candidato" in aj and cands:
            escolhido = cands[aj["candidato"]] if aj["candidato"] < len(cands) else None
        elif esc.get("escolha") and cands:
            escolhido = cands[esc["escolha"] - 1] if esc["escolha"] - 1 < len(cands) else None
        clipe = None
        if escolhido and escolhido["tipo"] == "tomada":  # para o Felipe escolher o momento do clipe no vídeo original
            t = acervo.execute("SELECT t.midia_id, t.inicio, m.duracao FROM tomadas t JOIN midias m ON m.id=t.midia_id "
                               "WHERE t.id=?", (nec["candidatos"][escolhido["idx"]]["id"],)).fetchone()
            if t:
                clipe = {"midia_id": t[0], "inicio": aj.get("clipe_inicio", t[1]), "duracao": t[2]}
        # itens de lista / tela dividida / mosaico: cada um com a própria imagem (necessidade "<cid>p<j>")
        pecas = []
        for j, peca in enumerate((aj.get("juntar") or {}).get("pecas") or c.get("pecas") or c.get("mosaico") or []):
            pn = necs.get(f"{cid}p{j}")
            pe = d["escolhas"].get(f"{cid}p{j}") or {}
            pcands = [{"idx": i, "nome": x["nome"], "tipo": x["tipo"], "miniatura": _rel(x["miniatura"])}
                      for i, x in enumerate(pn["candidatos"])] if pn else []
            paj = (aj.get("pecas") or {}).get(str(j), {})
            pesc = None
            if "candidato" in paj and paj["candidato"] < len(pcands):
                pesc = pcands[paj["candidato"]]
            elif pe.get("escolha") and pcands:
                pesc = pcands[pe["escolha"] - 1]
            pecas.append({"j": j, "rotulo": peca.get("rotulo") or peca.get("palavra") or "",
                          "busca": (peca.get("busca") or {}).get("o_que"), "escolhido": pesc, "candidatos": pcands,
                          "ajustada": bool(paj)})
        metade2 = None
        if aj.get("metade2") and necs.get(f"{cid}m2"):
            x = necs[f"{cid}m2"]["candidatos"][aj["metade2"]["candidato"]]
            metade2 = {"nome": x["nome"], "miniatura": _rel(x["miniatura"])}
        m = montadas.get(cid)
        inicio = palavras[m["de"]]["i"] if m and palavras else None
        inicios.append(inicio)
        frase = ""
        if m and toks:
            frase = " ".join(toks[m["de"]:m["ate"] + 1])
        saida.append({
            "k": k, "numero": numeros.get(cid, str(k)), "id": cid, "secao": c.get("secao"), "conferir": bool(c.get("conferir")) and not aj.get("conferido"),
            "tipo": aj.get("tipo", c["tipo"]), "legenda": aj.get("legenda", c.get("legenda")),
            "frase": frase, "inicio": inicio, "busca": (c.get("busca") or {}).get("o_que"),
            "escolhido": escolhido, "metade2": metade2, "clipe": clipe, "candidatos": cands, "pecas": pecas, "recusada": nec is not None and not esc.get("escolha"),
            "no_rascunho": m is not None, "removida": bool(aj.get("removida")),
            "comentario": aj.get("comentario"), "comentario_aplicado": bool(aj.get("comentario_aplicado")),
            "motivo": esc.get("motivo"), "ajustada": bool(aj), "pendente": cid in pend,
            "som": None if aj.get("sem_som") else (c.get("som") or {}).get("o_que"),
            "som_no_rascunho": cid in sons,
            "lado": aj.get("lado") or (m or {}).get("lado"), "fundo": (m or {}).get("fundo") if isinstance((m or {}).get("fundo"), str) else None,
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
        n_ = next((n for n in d["necs"] if n["id"] == cid), None)
        if n_ and aj["candidato"] < len(n_["candidatos"]):
            aj["midia"] = [n_["candidatos"][aj["candidato"]]["tipo"], n_["candidatos"][aj["candidato"]]["id"]]
    elif tipo == "usar_midia":  # resultado de uma busca manual no acervo: vira um candidato novo
        necs = d["necs"]
        nec = next((n for n in necs if n["id"] == cid), None)
        if nec is None:  # cena que nasceu sem imagem (ex.: "só texto"): passa a ter uma
            cena = next(c for k, c in enumerate(d["plano"]["cenas"]) if _id(c, k) == cid)
            tipo_atual = aj.get("tipo", cena["tipo"])
            if tipo_atual in ("capa", "hub", "dialogo", "mosaico", "dividida", "lista"):
                raise ValueError("este tipo de cena não usa uma imagem só")
            if tipo_atual == "texto":
                aj["tipo"] = "cartao"  # o texto continua como legenda do cartão
            nec = {"id": cid, "cena": cid, "tipo": aj.get("tipo", tipo_atual), "frase": "",
                   "busca": {"o_que": cena.get("legenda") or ""}, "legenda": cena.get("legenda"), "candidatos": []}
            necs.append(nec)
        cand = {"tipo": "midia", "id": int(acao["midia_id"]), "nome": acao["nome"], "nota": 1.0, "manual": True,
                "miniatura": str(RAIZ / acao["miniatura"])}
        nec["candidatos"].append(cand)
        aj["candidato"] = len(nec["candidatos"]) - 1
        aj["midia"] = [cand["tipo"], cand["id"]]
        (pasta / "direcao" / "candidatos.json").write_text(json.dumps(necs, ensure_ascii=False, indent=1), encoding="utf-8")
    elif tipo in ("peca_candidato", "peca_usar_midia"):  # imagem de UM item da lista/dividida/mosaico
        j = int(acao["j"])
        pid = f"{cid}p{j}"
        if tipo == "peca_candidato":
            idx = int(acao["idx"])
        else:
            necs = d["necs"]
            pn = next((n for n in necs if n["id"] == pid), None)
            if pn is None:  # item que o diretor não conseguiu buscar: passa a ter uma necessidade
                cena = next(c for k, c in enumerate(d["plano"]["cenas"]) if _id(c, k) == cid)
                peca = (cena.get("pecas") or cena.get("mosaico") or [])[j]
                pn = {"id": pid, "cena": cid, "peca": j, "tipo": "peca", "busca": peca.get("busca") or {},
                      "frase": "", "legenda": peca.get("rotulo") or peca.get("palavra"), "candidatos": []}
                necs.append(pn)
            pn["candidatos"].append({"tipo": "midia", "id": int(acao["midia_id"]), "nome": acao["nome"], "nota": 1.0, "manual": True,
                                     "miniatura": str(RAIZ / acao["miniatura"])})
            idx = len(pn["candidatos"]) - 1
            (pasta / "direcao" / "candidatos.json").write_text(json.dumps(necs, ensure_ascii=False, indent=1),
                                                               encoding="utf-8")
        pn_ = next((n for n in d["necs"] if n["id"] == pid), None)
        cand_ = pn_["candidatos"][idx] if pn_ and idx < len(pn_["candidatos"]) else None
        aj.setdefault("pecas", {})[str(j)] = {"candidato": idx, **({"midia": [cand_["tipo"], cand_["id"]]} if cand_ else {})}
    elif tipo == "juntar_proxima":  # esta cena + a próxima viram uma tela dividida; a próxima sai do vídeo
        _juntar_com_a_proxima(pasta, d, cid, aj)
    elif tipo == "metade_usar_midia":  # meio a meio: IMAGEM na outra metade (no lugar do texto)
        necs = d["necs"]
        mid = f"{cid}m2"
        n2 = next((n for n in necs if n["id"] == mid), None)
        if n2 is None:
            n2 = {"id": mid, "cena": cid, "tipo": "metade", "busca": {}, "frase": "", "legenda": "", "candidatos": []}
            necs.append(n2)
        n2["candidatos"].append({"tipo": "midia", "id": int(acao["midia_id"]), "nome": acao["nome"], "nota": 1.0, "manual": True,
                                 "miniatura": str(RAIZ / acao["miniatura"])})
        aj["metade2"] = {"candidato": len(n2["candidatos"]) - 1}
        (pasta / "direcao" / "candidatos.json").write_text(json.dumps(necs, ensure_ascii=False, indent=1), encoding="utf-8")
    elif tipo == "metade_texto":  # meio a meio: a outra metade volta a ser o texto
        aj.pop("metade2", None)
    elif tipo == "lado":  # meio a meio / citação: de que lado fica a imagem
        if acao["lado"] not in ("esq", "dir", "centro"):
            raise ValueError("lado inválido")
        aj["lado"] = acao["lado"]
    elif tipo == "clipe_inicio":
        aj["clipe_inicio"] = round(max(0.0, float(acao["segundos"])), 2)
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
        velho = d["ajustes"].pop(cid, None) or {}
        outra = (velho.get("juntar") or {}).get("com")
        if outra and outra in d["ajustes"]:  # desfaz a junção: a cena que tinha sido absorvida volta
            oa = d["ajustes"][outra]
            if oa.get("juntada_em") == cid:
                oa.pop("juntada_em", None)
                oa.pop("removida", None)
                if not oa:
                    d["ajustes"].pop(outra)
                marcar_pendente(pasta, outra)
    elif tipo == "comentario":
        aj["comentario"] = acao["texto"].strip()
        aj["comentario_aplicado"] = False
    else:
        raise ValueError(f"ação desconhecida: {tipo}")
    if cid in d["ajustes"] and not d["ajustes"][cid]:
        d["ajustes"].pop(cid)
    salvar_ajustes(pasta, d["ajustes"])
    marcar_pendente(pasta, cid)
    return d["ajustes"].get(cid, {})


def _juntar_com_a_proxima(pasta: Path, d: dict, cid: str, aj: dict) -> None:
    """A cena vira TELA DIVIDIDA: item 1 = a imagem dela, item 2 = a imagem da próxima cena, entrando na palavra em
    que a próxima começava (o efeito de entrada o editor de variedade escolhe). A próxima cena sai do vídeo (a
    narração dela continua, agora sobre a tela dividida)."""
    cenas_plano = d["plano"]["cenas"]
    ids = [_id(c, k) for k, c in enumerate(cenas_plano)]
    i = ids.index(cid)
    prox = next((k for k in range(i + 1, len(ids)) if not cenas_plano[k].get("removida")
                 and not d["ajustes"].get(ids[k], {}).get("removida")), None)
    if prox is None:
        raise ValueError("não há próxima cena para juntar")
    necs = {n["id"]: n for n in d["necs"]}

    def imagem(x: str) -> dict:
        n, a, e = necs.get(x), d["ajustes"].get(x, {}), d["escolhas"].get(x) or {}
        idx = a.get("candidato", (e.get("escolha") or 0) - 1)
        if not n or idx < 0 or idx >= len(n["candidatos"]) or n["candidatos"][idx]["tipo"] != "midia":
            raise ValueError("as duas cenas precisam ter uma imagem escolhida (escolha a imagem antes de juntar)")
        return n["candidatos"][idx]

    nid = ids[prox]
    c, pc = cenas_plano[i], cenas_plano[prox]
    pecas = [{"rotulo": aj.get("legenda", c.get("legenda")) or "", "busca": c.get("busca") or {}},
             {"rotulo": d["ajustes"].get(nid, {}).get("legenda", pc.get("legenda")) or "", "busca": pc.get("busca") or {},
              "frase": pc["frase"], "palavra": pc.get("comeca_na_palavra")}]
    for j, img in enumerate((imagem(cid), imagem(nid))):
        pid = f"{cid}p{j}"
        d["necs"][:] = [n for n in d["necs"] if n["id"] != pid]
        d["necs"].append({"id": pid, "cena": cid, "peca": j, "tipo": "peca", "busca": pecas[j]["busca"], "frase": "",
                          "legenda": pecas[j]["rotulo"], "candidatos": [img]})
    (pasta / "direcao" / "candidatos.json").write_text(json.dumps(d["necs"], ensure_ascii=False, indent=1), encoding="utf-8")
    aj["tipo"] = "dividida"
    aj["juntar"] = {"com": nid, "pecas": pecas}
    aj["pecas"] = {"0": {"candidato": 0}, "1": {"candidato": 0}}
    d["ajustes"].setdefault(nid, {}).update(removida=True, juntada_em=cid)
    marcar_pendente(pasta, nid)


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
        if aj.get("lado"):
            c["lado_felipe"] = aj["lado"]
        if aj.get("metade2"):  # meio a meio com imagem nas duas metades
            c["metade2"] = True
            escolhas[f"{cid}m2"] = {"escolha": aj["metade2"]["candidato"] + 1, "fixa": True, "foco": [0.5, 0.45]}
        if aj.get("juntar"):  # tela dividida montada pelo Felipe com a cena seguinte
            c["pecas"] = aj["juntar"]["pecas"]
        if "tipo" in aj:
            c["tipo"] = aj["tipo"]
        if "candidato" in aj:
            escolhas[k] = {**(escolhas.get(k) or {}), "escolha": aj["candidato"] + 1, "fixa": True,
                           **({"midia": aj["midia"]} if aj.get("midia") else {})}
        for j, pa in (aj.get("pecas") or {}).items():  # imagem escolhida pelo Felipe para um item da lista
            if "candidato" in pa:
                pid = f"{k}p{j}"
                escolhas[pid] = {**(escolhas.get(pid) or {}), "escolha": pa["candidato"] + 1, "fixa": True,
                                 **({"midia": pa["midia"]} if pa.get("midia") else {})}
        if "clipe_inicio" in aj:  # momento do clipe escolhido pelo Felipe (segundo do vídeo original)
            escolhas[k] = {**(escolhas.get(k) or {}), "inicio": aj["clipe_inicio"]}
    return plano, escolhas


def pendentes_para_o_diretor(ajustes: dict) -> list[str]:
    return [cid for cid, a in ajustes.items() if a.get("comentario") and not a.get("comentario_aplicado")]


def _sem_acento(t: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode().strip()


def preaquecer_busca() -> None:
    """Carrega o modelo CLIP antes da primeira busca (chamado ao ligar o servidor)."""
    import sys

    sys.path.insert(0, str(RAIZ / "tools" / "acervo"))
    try:
        from busca_semantica import modelo

        modelo()
    except Exception as e:  # sem GPU/modelo: a busca por nome continua funcionando, só a 1ª fica lenta
        print(f"[busca] não consegui pré-carregar o CLIP: {e}")


def buscar_no_acervo(consulta: str, n: int = 16) -> list[dict]:
    """Busca MANUAL do Felipe no storyboard. Ordem: nome exato (com ou sem extensão) → nome que começa com o
    termo → nome que contém → etiquetas (personagens, descrição, uso) → semelhança (CLIP) para completar.
    Mostra tudo, inclusive a categoria "canal" (o diretor automático é que não usa logos/thumbs), e esconde
    arquivos que não existem mais na pasta do acervo."""
    import re
    import sys

    sys.path.insert(0, str(RAIZ / "tools"))
    sys.path.insert(0, str(RAIZ / "tools" / "acervo"))
    from busca_semantica import buscar
    from comum import PASTA_ACERVO, abrir_acervo

    con = abrir_acervo()
    q = _sem_acento(consulta)
    q_base = re.sub(r"\.(jpe?g|png|webp|gif|avif|jfif)$", "", q)
    termos = [t for t in re.split(r"[^a-z0-9]+", q_base) if len(t) >= 2]
    pontos: dict[int, float] = {}
    info: dict[int, dict] = {}
    for r in con.execute("SELECT id, caminho, nome, categoria, personagens, descricao, uso FROM midias "
                         "WHERE tipo IN ('imagem','gif')"):
        if not (PASTA_ACERVO / r["caminho"]).exists():
            continue
        info[r["id"]] = {"nome": r["nome"], "categoria": r["categoria"]}
        nome = _sem_acento(r["nome"])
        base = nome.rsplit(".", 1)[0]
        nota = 0.0
        if q_base and (nome == q or base == q_base):
            nota = 100
        elif q_base and base.startswith(q_base):
            nota = 50 + 10 * len(q_base) / max(1, len(base))
        elif q_base and q_base in base:
            nota = 30
        if termos:
            etiquetas = " " + re.sub(r"[^a-z0-9]+", " ", _sem_acento(" ".join(
                str(r[x] or "") for x in ("personagens", "descricao", "uso", "categoria")))) + " "
            acertos = sum(1 for t in termos if t in base or f" {t} " in etiquetas)
            nota += 10 * acertos / len(termos)
        if nota:
            pontos[r["id"]] = nota
    # semelhança (CLIP): completa com o que nome e etiquetas não dizem; pesa pouco perto de um acerto de nome
    for mid, nota in buscar(consulta, max(80, 2 * n)):
        if mid in info:
            pontos[mid] = pontos.get(mid, 0) + 5 * nota
    melhores = sorted(pontos.items(), key=lambda x: -x[1])[:n]
    return [{"midia_id": mid, "nome": info[mid]["nome"], "nota": round(nota, 2), "categoria": info[mid]["categoria"],
             "miniatura": f"dados/acervo/miniaturas/{mid}.jpg"} for mid, nota in melhores]
