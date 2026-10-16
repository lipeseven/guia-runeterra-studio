"""Diretor — revisão: refaz SÓ as cenas em que o Felipe deixou um pedido no storyboard.

O diretor vê o TRECHO inteiro que a cena cobre (todas as frases até a próxima cena) e pode devolver uma cena ou
uma LISTA de cenas (dividir o trecho em várias imagens). Arquivo do acervo citado pelo nome ("illaoi2.gif") entra
direto, sem passar pela escolha do Claude.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from candidatos import Acervo, abrir_acervo, buscar, escolha_fixa, folhas, id_da_cena, necessidades
from claude_cli import chamar_json
from escolher import escolher
from planejar import FORMATO, SISTEMA, TIPOS

RAIZ = Path(__file__).resolve().parents[2]


def _trecho(plano: dict, k: int, frases: list[dict]) -> list[dict]:
    """Frases que a cena k cobre: da frase dela até antes da próxima cena."""
    ini = plano["cenas"][k]["frase"]
    prox = next((c["frase"] for c in plano["cenas"][k + 1:] if c["frase"] > ini), len(frases))
    return frases[ini:max(prox, ini + 1)]


def revisar(plano: dict, frases: list[dict], necs: list[dict], escolhas: dict, ajustes: dict,
            ids: list[str], pasta_trabalho: Path, nomes_capa: list[str]) -> None:
    """Atualiza plano/necs/escolhas/ajustes NO LUGAR para as cenas `ids` (ids estáveis das cenas)."""
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    por_id = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    ids = [i for i in ids if i in por_id]
    pedidos, trechos = [], {}
    for cid in ids:
        k = por_id[cid]
        c = plano["cenas"][k]
        trechos[cid] = _trecho(plano, k, frases)
        cena = {kk: v for kk, v in c.items() if kk not in ("id", "secao", "conferir")}
        pedidos.append({"cena": cid,
                        "trecho": [f"[{i}] {f['texto']}" + "".join(f"  ↳ NOTA: {n}" for n in f.get("notas", []))
                                   for i, f in enumerate(trechos[cid])],
                        "cena_atual": {**cena, "frase": 0}, "pedido_do_felipe": ajustes[cid]["comentario"]})
    prompt = ("O Felipe revisou o rascunho e fez pedidos para algumas cenas. Refaça SÓ essas cenas atendendo ao pedido.\n"
              "Cada cena cobre um TRECHO (frases numeradas a partir de [0]). Você pode devolver UMA cena ou uma LISTA de "
              "cenas para dividir o trecho em várias imagens (ex.: \"a partir de 'Se você já jogou' outra imagem\"): "
              "cada cena com \"frase\" (número no trecho) e, se começar no meio da frase, \"comeca_na_palavra\" "
              "(palavra exata). A 1ª cena começa na frase [0].\n"
              "Se o Felipe citar um arquivo do acervo pelo nome (ex.: illaoi2.gif), ponha o nome em \"busca.arquivo\".\n"
              f"Personagens na capa: {', '.join(nomes_capa)}.\n\n"
              f"PEDIDOS:\n{json.dumps(pedidos, ensure_ascii=False, indent=1)}\n\n"
              'Responda: {"cenas": {"<id da cena>": {cena} ou [{cena}, {cena}, ...]}}\n\n'
              "Formato de cada cena (referência):\n" + FORMATO)
    novas = chamar_json(prompt, SISTEMA.format(regras=regras), modelo="opus", etiqueta="direcao-revisao")["cenas"]

    afetados: list[str] = []
    # de trás para frente: inserir cenas não muda a posição das que ainda vão ser trocadas
    for cid in sorted((c for c in novas if c in por_id), key=lambda c: -por_id[c]):
        k = por_id[cid]
        velha = plano["cenas"][k]
        lista = novas[cid] if isinstance(novas[cid], list) else [novas[cid]]
        trecho = trechos[cid]
        validas = [c for c in lista if isinstance(c, dict) and c.get("tipo") in TIPOS]
        if not validas:
            continue  # resposta inútil para esta cena: mantém a atual
        substitutas = []
        for j, c in enumerate(sorted(validas, key=lambda c: int(c.get("frase") or 0))):
            rel = min(max(int(c.get("frase") or 0), 0), len(trecho) - 1)
            substitutas.append({**c, "frase": velha["frase"] + rel, "secao": velha.get("secao"),
                                "id": cid if j == 0 else f"{cid}-{uuid.uuid4().hex[:4]}"})
        plano["cenas"][k:k + 1] = substitutas
        afetados += [s["id"] for s in substitutas]
        aj = ajustes[cid]
        aj["comentario_aplicado"] = True
        for campo in ("candidato", "tipo", "legenda"):  # o diretor refez a cena: valem as escolhas novas dele
            aj.pop(campo, None)

    # novos candidatos e nova escolha, só para as necessidades dessas cenas
    ac = Acervo(abrir_acervo())
    alvo = [n for n in necessidades(plano, frases) if n["cena"] in afetados]
    para_o_claude = []
    for n in alvo:
        n["candidatos"] = buscar(ac, n)
        fixa = escolha_fixa(n)
        if fixa:
            escolhas[n["id"]] = fixa  # arquivo pedido pelo Felipe: sem escolha do Claude
        else:
            para_o_claude.append(n)
    if para_o_claude:
        escolhas.update(escolher(para_o_claude, folhas(para_o_claude, pasta_trabalho / "candidatos_revisao")))
    necs[:] = [n for n in necs if n["cena"] not in afetados] + alvo
    ordem = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    necs.sort(key=lambda n: (ordem.get(n["cena"], 1e9), n.get("peca", -1)))
