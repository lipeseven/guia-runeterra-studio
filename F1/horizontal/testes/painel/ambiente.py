"""Ambiente fictício do painel do F1 para testes: canal f1 com TODAS as pastas de dados numa pasta de teste.

Nada toca o banco, os projetos ou o acervo reais: antes de importar `app.servidor`, as pastas do perfil do canal
(`canal.CANAL["pastas"]`) passam a apontar para `<esta pasta>/dados/<nome>/` (fora do Git: `dados/`). A pasta fica
dentro do repositório porque o painel monta caminhos relativos à raiz (`motor.caminho_rel`).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]                      # raiz do repositório (worktree ou pasta principal)
DIRETOR = RAIZ / "F1" / "horizontal" / "diretor"
EXEMPLO = RAIZ / "F1" / "horizontal" / "testes" / "diretor" / "exemplo"


def preparar(nome: str, limpar: bool = True) -> Path:
    """Aponta o canal f1 para dados fictícios em testes/painel/dados/<nome>. Chamar ANTES de importar app.servidor."""
    base = AQUI / "dados" / nome
    if limpar and base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)
    os.environ["GRS_CANAL"] = "f1"
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    sys.path.insert(0, str(RAIZ))
    sys.path.insert(0, str(RAIZ / "tools"))
    import canal

    assert canal.CHAVE == "f1", "GRS_CANAL precisa ser f1 antes do primeiro import de canal"
    for chave in list(canal.CANAL["pastas"]):
        if chave == "docs":   # regras e textos do canal: leitura, ficam os reais
            continue
        destino = base / chave
        canal.CANAL["pastas"][chave] = str(destino.with_suffix(".db") if chave in ("studio", "banco_acervo") else destino)
    (base / "projetos").mkdir(exist_ok=True)
    return base
