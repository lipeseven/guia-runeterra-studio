"""Notas de direção do Felipe dentro do roteiro, entre colchetes: "[Texto na tela: a.N. = antes de Noxus]".

Elas NÃO são narradas: saem do texto que vai para a voz guia, o alinhamento e a limpeza da gravação, e vão para
o diretor como ordem para aquele ponto do vídeo (a frase em que aparecem).
"""
from __future__ import annotations

import re

NOTA = re.compile(r"\[([^\[\]]*)\]")


def separar(fonte: str) -> tuple[str, list[dict]]:
    """Texto com notas → (narração sem notas, [{"palavra": índice do token da narração onde a nota está,
    "texto": "..."}]). Parágrafos são preservados; uma nota sozinha numa linha não deixa linha vazia a mais."""
    narracao_pars, notas, tokens = [], [], 0
    for par in re.split(r"\n\s*\n", fonte.strip()):
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
