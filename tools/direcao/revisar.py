"""Diretor — revisão: refaz SÓ as cenas em que o Felipe deixou um pedido no storyboard."""
from __future__ import annotations

import json
from pathlib import Path

from candidatos import Acervo, abrir_acervo, buscar, folhas, id_da_cena, necessidades
from claude_cli import chamar_json
from escolher import escolher
from planejar import FORMATO, SISTEMA

RAIZ = Path(__file__).resolve().parents[2]


def revisar(plano: dict, frases: list[dict], necs: list[dict], escolhas: dict, ajustes: dict,
            ids: list[str], pasta_trabalho: Path, nomes_capa: list[str]) -> None:
    """Atualiza plano/necs/escolhas/ajustes NO LUGAR para as cenas `ids` (ids estáveis das cenas)."""
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    por_id = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    ids = [i for i in ids if i in por_id]
    pedidos = []
    for cid in ids:
        c = plano["cenas"][por_id[cid]]
        cena = {k: v for k, v in c.items() if k not in ("id", "secao", "conferir")}
        pedidos.append({"cena": cid, "frase": frases[c["frase"]]["texto"], "cena_atual": {**cena, "frase": 0},
                        "pedido_do_felipe": ajustes[cid]["comentario"]})
    prompt = ("O Felipe revisou o rascunho e fez pedidos para algumas cenas. Refaça SÓ essas cenas atendendo ao pedido "
              "(a cena cobre a frase indicada, que é a frase [0]; ajuste tipo, legenda, destaques e principalmente a busca).\n"
              f"Personagens na capa: {', '.join(nomes_capa)}.\n\n"
              f"PEDIDOS:\n{json.dumps(pedidos, ensure_ascii=False, indent=1)}\n\n"
              'Responda: {"cenas": {"<id da cena>": { ...cena no mesmo formato, com "frase": 0... }}}\n\n'
              "Formato de cada cena (referência):\n" + FORMATO)
    novas = chamar_json(prompt, SISTEMA.format(regras=regras), modelo="opus", etiqueta="direcao-revisao")["cenas"]
    for cid, cena in novas.items():
        if cid not in por_id:
            continue
        velha = plano["cenas"][por_id[cid]]
        # mesma posição no roteiro e mesmo id (o storyboard continua apontando para ela)
        plano["cenas"][por_id[cid]] = {**cena, "frase": velha["frase"], "id": cid, "secao": velha.get("secao")}
        aj = ajustes[cid]
        aj["comentario_aplicado"] = True
        for campo in ("candidato", "tipo", "legenda"):  # o diretor refez a cena: valem as escolhas novas dele
            aj.pop(campo, None)

    # novos candidatos e nova escolha, só para as necessidades dessas cenas
    ac = Acervo(abrir_acervo())
    alvo = [n for n in necessidades(plano, frases) if n["cena"] in ids]
    for n in alvo:
        n["candidatos"] = buscar(ac, n)
    if alvo:
        escolhas.update(escolher(alvo, folhas(alvo, pasta_trabalho / "candidatos_revisao")))
    necs[:] = [n for n in necs if n["cena"] not in ids] + alvo
    ordem = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    necs.sort(key=lambda n: (ordem.get(n["cena"], 1e9), n.get("peca", -1)))
