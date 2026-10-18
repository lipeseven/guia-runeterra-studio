"""Diretor — revisão: refaz SÓ as cenas em que o Felipe deixou um pedido no storyboard.

O diretor vê o TRECHO inteiro que a cena cobre (todas as frases até a próxima cena) e pode devolver uma cena ou
uma LISTA de cenas (dividir o trecho em várias imagens). Arquivo do acervo citado pelo nome ("illaoi2.gif") entra
direto, sem passar pela escolha do Claude.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from candidatos import Acervo, abrir_acervo, buscar, escolha_fixa, folhas, id_da_cena, necessidades
from claude_cli import chamar_json
from escolher import escolher
from planejar import FORMATO, SISTEMA, TIPOS

RAIZ = Path(__file__).resolve().parents[2]


def _trecho(plano: dict, k: int, frases: list[dict], montadas: dict) -> list[dict]:
    """Frases que a cena k cobre NO RASCUNHO que o Felipe viu (cenas seguintes sem imagem ficam de fora do vídeo,
    e esta cena continua na tela até a próxima montada). Sem rascunho: até a próxima cena do plano."""
    c = plano["cenas"][k]
    m = montadas.get(id_da_cena(c, k))
    if m:
        return [f for f in frases if f["de"] <= m["ate"] and f["ate"] >= m["de"]] or frases[c["frase"]:c["frase"] + 1]
    ini = c["frase"]
    prox = next((x["frase"] for x in plano["cenas"][k + 1:] if x["frase"] > ini), len(frases))
    return frases[ini:max(prox, ini + 1)]


def _ordenar(plano: dict, frases: list[dict]) -> None:
    """Cenas em ordem de fala: frase e, dentro dela, a palavra em que começam."""
    def chave(c):
        f = frases[c["frase"]]
        w = (c.get("comeca_na_palavra") or "").strip().lower()
        pos = next((i for i, t in enumerate(f["texto"].split()) if w and t.strip(".,;:!?…").lower() == w.strip(".,;:!?…")), 0)
        return (c["frase"], pos)
    plano["cenas"].sort(key=chave)


def revisar(plano: dict, frases: list[dict], necs: list[dict], escolhas: dict, ajustes: dict,
            ids: list[str], pasta_trabalho: Path, nomes_capa: list[str], montadas: dict | None = None) -> None:
    """Atualiza plano/necs/escolhas/ajustes NO LUGAR para as cenas `ids` (ids estáveis das cenas).
    `montadas` = cenas do rascunho atual por id ({"de", "ate"} em palavras): define o trecho que o Felipe viu."""
    montadas = montadas or {}
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    por_id = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    ids = [i for i in ids if i in por_id]
    pedidos, trechos = [], {}
    for cid in ids:
        k = por_id[cid]
        c = plano["cenas"][k]
        trechos[cid] = _trecho(plano, k, frases, montadas)
        cena = {kk: v for kk, v in c.items() if kk not in ("id", "secao", "conferir")}
        pedidos.append({"cena": cid,
                        "trecho": [f"[{i}] {f['texto']}" + "".join(f"  ↳ NOTA: {n}" for n in f.get("notas", []))
                                   for i, f in enumerate(trechos[cid])],
                        "cena_atual": {**cena, "frase": 0}, "pedido_do_felipe": ajustes[cid]["comentario"],
                        # o que o Felipe já montou à mão (tipo, itens): o diretor atende o pedido SEM desmanchar
                        **({"montado_pelo_felipe": {x: ajustes[cid][x] for x in ("tipo", "pecas_def", "juntar") if x in ajustes[cid]}}
                           if any(x in ajustes[cid] for x in ("tipo", "pecas_def", "juntar")) else {})})
    prompt = ("O Felipe revisou o rascunho e fez pedidos para algumas cenas. Refaça SÓ essas cenas atendendo ao pedido.\n"
              "Cada cena cobre um TRECHO (frases numeradas a partir de [0]). Você pode devolver UMA cena ou uma LISTA de "
              "cenas para dividir o trecho em várias imagens (ex.: \"a partir de 'Se você já jogou' outra imagem\"): "
              "cada cena com \"frase\" (número no trecho) e, se começar no meio da frase, \"comeca_na_palavra\" "
              "(palavra exata). A 1ª cena começa na frase [0].\n"
              "SÓ divida a cena se o Felipe PEDIR para dividir/separar (\"a partir de...\", \"outra cena\", \"outra imagem\" "
              "num trecho). Pedido de ajuste fino (centralizar, zoom, foco, texto junto) NÃO é motivo para dividir nem "
              "para mudar o tipo da cena; se a cena tem \"montado_pelo_felipe\", mantenha o tipo e a estrutura dele.\n"
              "Se o Felipe citar um arquivo do acervo pelo nome (ex.: illaoi2.gif), ponha o nome em \"busca.arquivo\".\n"
              f"Personagens na capa: {', '.join(nomes_capa)}.\n\n"
              f"PEDIDOS:\n{json.dumps(pedidos, ensure_ascii=False, indent=1)}\n\n"
              'Responda: {"cenas": {"<id da cena>": {cena} ou [{cena}, {cena}, ...]}}\n\n'
              "Formato de cada cena (referência):\n" + FORMATO)
    novas = chamar_json(prompt, SISTEMA.format(regras=regras), modelo="opus", etiqueta="direcao-revisao")["cenas"]

    afetados: list[str] = []
    trocas: dict[str, list[dict]] = {}
    sumir: set[str] = set()
    for cid in (c for c in novas if c in por_id):
        velha = plano["cenas"][por_id[cid]]
        lista = novas[cid] if isinstance(novas[cid], list) else [novas[cid]]
        pediu_dividir = re.search(r"\b(divid\w*|separ\w*|a partir d[eo]|outra cena|nova cena|duas cenas|outra imagem)\b",
                                  ajustes[cid].get("comentario", "").lower())
        if len(lista) > 1 and not pediu_dividir:  # o diretor quis dividir sem o Felipe pedir: fica só a 1ª
            lista = lista[:1]
        trecho = trechos[cid]
        validas = [c for c in lista if isinstance(c, dict) and c.get("tipo") in TIPOS]
        if not validas:
            continue  # resposta inútil para esta cena: mantém a atual
        substitutas = []
        for j, c in enumerate(sorted(validas, key=lambda c: int(c.get("frase") or 0))):
            rel = min(max(int(c.get("frase") or 0), 0), len(trecho) - 1)
            substitutas.append({**c, "frase": trecho[rel]["n"], "secao": velha.get("secao"),
                                "id": cid if j == 0 else f"{cid}-{uuid.uuid4().hex[:4]}"})
        trocas[cid] = substitutas
        # cenas do plano que caem nesse trecho e NÃO apareciam no rascunho (sem imagem): o diretor acabou de
        # replanejar o trecho inteiro, então elas saem (senão disputariam o mesmo pedaço do vídeo)
        nums = {f["n"] for f in trecho}
        sumir |= {id_da_cena(x, i) for i, x in enumerate(plano["cenas"])
                  if x["frase"] in nums and id_da_cena(x, i) != cid and montadas and id_da_cena(x, i) not in montadas}
        afetados += [s["id"] for s in substitutas]
        aj = ajustes[cid]
        aj["comentario_aplicado"] = True
        # o que o Felipe fez À MÃO continua valendo, a não ser que o pedido seja justamente sobre aquilo
        # (antes o diretor apagava tipo/imagem/legenda escolhidos por ele a cada pedido)
        texto = ajustes[cid].get("comentario", "").lower()
        sobre = {
            # palavras INTEIRAS ("parte direita" não é "arte"; "zoom na imagem que já estava" pede outra coisa)
            "candidato": r"\b(outra imagem|nova imagem|troc\w*|troq\w*|substitu\w*|foto|arquivo|clipe|v[ií]deo)\b|\.(png|jpe?g|webp|gif|avif)\b",
            "tipo": r"\b(tela cheia|cart[aã]o|recorte|meio a meio|lista|dividid\w*|mosaico|clipe|tipo de cena|formato|cita[cç][aã]o)\b",
            "legenda": r"\b(legenda|texto|escrit\w*|letreiro)\b",
        }
        for campo, padrao in sobre.items():
            if re.search(padrao, texto) or (len(lista) > 1 and campo != "tipo"):  # dividida a pedido: imagem/legenda novas
                aj.pop(campo, None)
                if campo == "candidato":
                    aj.pop("midia", None)
    nova_lista = []
    for i, x in enumerate(plano["cenas"]):
        xid = id_da_cena(x, i)
        if xid in trocas:
            nova_lista += trocas[xid]
        elif xid not in sumir:
            nova_lista.append(x)
    plano["cenas"] = nova_lista
    _ordenar(plano, frases)

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
    # necessidades criadas pelo Felipe (itens buscados à mão, outra metade, junção) continuam
    manuais = [n for n in necs if n["cena"] in afetados and n["id"] not in {a["id"] for a in alvo}
               and any(c.get("manual") or (c.get("tipo") == "midia" and c.get("nota") == 1.0) for c in n.get("candidatos", []))]
    necs[:] = [n for n in necs if n["cena"] not in afetados and n["cena"] not in sumir] + alvo + manuais
    ordem = {id_da_cena(c, k): k for k, c in enumerate(plano["cenas"])}
    necs.sort(key=lambda n: (ordem.get(n["cena"], 1e9), n.get("peca", -1)))
