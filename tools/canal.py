"""Perfil do CANAL deste processo. Cada canal (canais/<chave>/canal.toml) roda num servidor próprio com
GRS_CANAL=<chave>: acervo, banco, projetos, regras e textos só dele — os canais não se conhecem; só compartilham
o motor (código). Sem GRS_CANAL = "runeterra", com os caminhos de sempre."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CHAVE = os.environ.get("GRS_CANAL", "runeterra")
CANAL = tomllib.loads((RAIZ / "canais" / CHAVE / "canal.toml").read_text(encoding="utf-8"))


def caminho(chave: str) -> Path:
    """Pasta/arquivo do canal (relativo à raiz do projeto ou absoluto)."""
    p = Path(CANAL["pastas"][chave])
    return p if p.is_absolute() else RAIZ / p


def todos() -> list[dict]:
    """Canais existentes (para o seletor do painel): chave, nome e porta — nada além disso."""
    saida = []
    for arq in sorted((RAIZ / "canais").glob("*/canal.toml")):
        c = tomllib.loads(arq.read_text(encoding="utf-8"))
        saida.append({"chave": c["chave"], "nome": c["nome"], "porta": c["porta"]})
    return saida
