"""Perfil do CANAL deste processo. Cada canal tem uma pasta na raiz (<Canal>/canal.toml) e roda num servidor próprio com
GRS_CANAL=<chave>: acervo, banco, projetos, regras e textos só dele — os canais não se conhecem; só compartilham
o motor (código). Sem GRS_CANAL = "runeterra", com os caminhos de sempre."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CHAVE = os.environ.get("GRS_CANAL", "runeterra")

def _perfis() -> list[dict]:
    return [tomllib.loads(arq.read_text(encoding="utf-8")) for arq in sorted(RAIZ.glob("*/canal.toml"))]


CANAL = next(c for c in _perfis() if c["chave"] == CHAVE)
# Dados do MOTOR, iguais para todos os canais (modelos, cache de voz, efeitos sonoros, trava, consumo do Claude).
DADOS_COMUM = RAIZ / "dados" / "comum"


def caminho(chave: str) -> Path:
    """Pasta/arquivo do canal (relativo à raiz do projeto ou absoluto)."""
    p = Path(CANAL["pastas"][chave])
    return p if p.is_absolute() else RAIZ / p


def todos() -> list[dict]:
    """Canais existentes (para o seletor do painel): chave, nome e porta — nada além disso."""
    return [{"chave": c["chave"], "nome": c["nome"], "porta": c["porta"]} for c in _perfis()]
