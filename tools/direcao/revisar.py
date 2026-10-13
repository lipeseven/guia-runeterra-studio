"""Diretor — revisão: refaz SÓ as cenas em que o Felipe deixou um pedido no storyboard."""
from __future__ import annotations

import json
from pathlib import Path

from candidatos import abrir_acervo, buscar, folhas, necessidades
from claude_cli import chamar_json
from escolher import escolher
from planejar import FORMATO, SISTEMA

RAIZ = Path(__file__).resolve().parents[2]


def revisar(plano: dict, frases: list[dict], necs: list[dict], escolhas: dict, ajustes: dict,
            ks: list[int], pasta_trabalho: Path, nomes_capa: list[str]) -> None:
    """Atualiza plano/necs/escolhas/ajustes NO LUGAR para as cenas `ks`."""
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    pedidos = []
    for k in ks:
        c = plano["cenas"][k]
        pedidos.append({"cena": k, "frase": frases[c["frase"]]["texto"], "cena_atual": c,
                        "pedido_do_felipe": ajustes[str(k)]["comentario"]})
    prompt = ("O Felipe revisou o rascunho e fez pedidos para algumas cenas. Refaça SÓ essas cenas atendendo ao pedido "
              "(mantenha o campo \"frase\"; ajuste tipo, legenda, destaques e principalmente a busca).\n"
              f"Personagens na capa: {', '.join(nomes_capa)}.\n\n"
              f"PEDIDOS:\n{json.dumps(pedidos, ensure_ascii=False, indent=1)}\n\n"
              'Responda: {"cenas": {"<numero da cena>": { ...cena no mesmo formato... }}}\n\n'
              "Formato de cada cena (referência):\n" + FORMATO)
    novas = chamar_json(prompt, SISTEMA.format(regras=regras), modelo="opus", etiqueta="direcao-revisao")["cenas"]
    for k_str, cena in novas.items():
        k = int(k_str)
        cena["frase"] = plano["cenas"][k]["frase"]
        plano["cenas"][k] = cena
        aj = ajustes[str(k)]
        aj["comentario_aplicado"] = True
        for campo in ("candidato", "tipo", "legenda"):  # o diretor refez a cena: valem as escolhas novas dele
            aj.pop(campo, None)

    # novos candidatos e nova escolha, só para as necessidades dessas cenas
    con = abrir_acervo()
    todas = necessidades(plano, frases)
    alvo = [n for n in todas if n["cena"] in ks]
    for n in alvo:
        n["candidatos"] = buscar(con, n)
    if alvo:
        novas_escolhas = escolher(alvo, folhas(alvo, pasta_trabalho / "candidatos_revisao"))
        escolhas.update(novas_escolhas)
    ids = {n["id"] for n in alvo}
    necs[:] = [n for n in necs if n["id"] not in ids and n["cena"] not in ks] + alvo
    necs.sort(key=lambda n: (n["cena"], n.get("peca", -1)))
