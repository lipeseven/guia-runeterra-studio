"""Diretor — 2ª passada (com imagens): o Claude olha as folhas de candidatos e escolhe.

Em LOTES: com dezenas de imagens numa mensagem só, as primeiras deixam de chegar ao modelo (aconteceu com 55
folhas: 161 respostas "folha não recebida"). Cada lote leva poucas folhas; o que voltar sem resposta ou com
"não recebi" é reenviado uma vez.
"""
from __future__ import annotations

import re
from pathlib import Path

from claude_cli import chamar_json

SISTEMA = """Você é o diretor visual do canal "Guia de Runeterra" (lore de League of Legends) escolhendo imagens.
Cada linha das folhas é uma necessidade (id em amarelo, a frase narrada e a legenda) com até 4 candidatos numerados.
Critérios, em ordem:
1. A imagem ilustra o SENTIDO da frase no contexto (metáforas não são literais).
2. O personagem certo: nunca use a imagem de outro personagem fingindo ser o citado.
3. Não repetir a mesma imagem em necessidades diferentes, a menos que não haja alternativa.
4. Para "recorte": personagem isolado (fundo transparente/branco). Para "clipe": a tomada mostra a ação narrada.
5. Se NENHUM candidato serve de verdade, recuse (escolha null) — melhor buscar outra imagem depois do que errar.
"foco" = ponto de interesse da imagem escolhida (x, y de 0 a 1, ex.: o rosto), usado para enquadrar.
Se alguma folha não chegou ou está ilegível, diga isso no motivo ("folha não recebida") em vez de recusar.
Responda SOMENTE com JSON."""

POR_FOLHA = 7  # igual a candidatos.folhas(por_folha=7): a ordem das necessidades segue a ordem das folhas
FOLHAS_POR_LOTE = 6
NAO_VIU = re.compile(r"n[ãa]o (recebid|cheg|vej|consig|carreg)|ileg[íi]vel|sem folha|folha ausente", re.I)


def _chamar(necs: list[dict], folhas: list[Path], modelo: str, etiqueta: str) -> dict:
    lista = "\n".join(f"{n['id']} ({n['tipo']}): {n['frase'][:160]}" + (f" | legenda: {n['legenda']}" if n.get("legenda") else "")
                      for n in necs)
    prompt = (f"Folhas anexadas: {len(folhas)}. Necessidades:\n{lista}\n\n"
              'Responda: {"<id>": {"escolha": 1-4 ou null, "foco": [x, y], "motivo": "até 10 palavras"}, ...} '
              "com TODAS as necessidades.")
    return chamar_json(prompt, SISTEMA, modelo=modelo, imagens=folhas, etiqueta=etiqueta)


def _faltando(necs: list[dict], r: dict) -> list[dict]:
    return [n for n in necs if n["id"] not in r or (not (r[n["id"]] or {}).get("escolha")
                                                    and NAO_VIU.search((r[n["id"]] or {}).get("motivo") or ""))]


def escolher(necs: list[dict], folhas: list[Path], modelo: str = "opus", aviso=lambda msg: None) -> dict:
    """`folhas` foram geradas de `necs` na mesma ordem, POR_FOLHA necessidades por folha."""
    escolhas: dict = {}
    passo = POR_FOLHA * FOLHAS_POR_LOTE
    lotes = [(necs[i:i + passo], folhas[i // POR_FOLHA:(i + passo) // POR_FOLHA]) for i in range(0, len(necs), passo)]
    for k, (lote, fl) in enumerate(lotes, 1):
        aviso(f"escolhendo imagens (Claude) — lote {k}/{len(lotes)}")
        r = _chamar(lote, fl, modelo, f"direcao-escolha:{k}/{len(lotes)}")
        faltam = _faltando(lote, r)
        if faltam:  # o modelo não viu parte das folhas: reenvia o lote só com as necessidades que faltaram
            from candidatos import folhas as gerar_folhas

            refeitas = gerar_folhas(faltam, fl[0].parent / f"reenvio_{k}") if fl else []
            r.update(_chamar(faltam, refeitas, modelo, f"direcao-escolha-reenvio:{k}"))
        escolhas.update({n["id"]: r[n["id"]] for n in lote if n["id"] in r})
    return escolhas
