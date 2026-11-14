"""Notas de direção do Felipe dentro do roteiro, entre colchetes: "[Texto na tela: a.N. = antes de Noxus]".

Elas NÃO são narradas: saem do texto que vai para a voz guia, o alinhamento e a limpeza da gravação, e vão para
o diretor como ordem para aquele ponto do vídeo (a frase em que aparecem).
"""
from __future__ import annotations

import re

NOTA = re.compile(r"\[([^\[\]]*)\]")
# Marcas simples de Markdown (roteiro escrito/colado de um editor ou do chat): nunca são faladas. Saem da narração
# (roteiro.txt → voz guia, alinhamento, limpeza, diretor, âncoras); o roteiro_fonte.txt guarda como veio.
_MD_LINHA = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|>[ \t]?)", re.M)         # título "## …" e citação "> …"
_MD_ENFASE = (re.compile(r"\*\*(.+?)\*\*", re.S), re.compile(r"__(.+?)__", re.S),
              re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", re.S),
              re.compile(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", re.S))
_MD_SOLTO = re.compile(r"(?:(?<=\s)|^)\*+|\*+(?=\s|$)", re.M)   # asterisco que sobrou na borda de palavra (2*3 fica)


def limpar_markdown(texto: str) -> str:
    """Tira negrito/itálico (`**x**`, `__x__`, `*x*`, `_x_`), título (`# `), citação (`> `), código (`) e asterisco
    solto na borda de uma palavra. Mantém o resto como está (palavras com _ no meio, como nome_de_arquivo, não mudam)."""
    t = _MD_LINHA.sub("", texto)
    for rx in _MD_ENFASE:
        t = rx.sub(lambda m: m.group(1), t)
    return _MD_SOLTO.sub("", t).replace("`", "")


def separar(fonte: str) -> tuple[str, list[dict]]:
    """Texto com notas → (narração sem notas e sem marcas de Markdown, [{"palavra": índice do token da narração onde
    a nota está, "texto": "..."}]). Parágrafos são preservados; uma nota sozinha numa linha não deixa linha vazia a mais."""
    narracao_pars, notas, tokens = [], [], 0
    for par in re.split(r"\n\s*\n", limpar_markdown(fonte).strip()):
        pedacos, ultimo = [], 0
        for m in NOTA.finditer(par):
            antes = par[ultimo:m.start()]
            pedacos.append(antes)
            tokens += len(antes.split())
            if m.group(1).strip():
                notas.append({"palavra": tokens, "texto": m.group(1).strip()})
            ultimo = m.end()
        pedacos.append(par[ultimo:])
        tokens += len(par[ultimo:].split())
        texto = re.sub(r"[ \t]+", " ", " ".join(p.strip() for p in pedacos if p.strip())).strip()
        if texto:
            narracao_pars.append(texto)
    narracao = "\n\n".join(narracao_pars) + "\n"
    total = len(narracao.split())
    for n in notas:  # nota no fim do roteiro: prende na última palavra
        n["palavra"] = min(n["palavra"], max(0, total - 1))
    return narracao, notas


def notas_por_frase(notas: list[dict], frases: list[dict]) -> dict[int, list[str]]:
    """Índice da frase (de frases_do_roteiro) → textos das notas que caem nela."""
    saida: dict[int, list[str]] = {}
    for n in notas:
        f = next((f for f in frases if f["de"] <= n["palavra"] <= f["ate"]), None)
        if f is not None:
            saida.setdefault(f["n"], []).append(n["texto"])
    return saida
