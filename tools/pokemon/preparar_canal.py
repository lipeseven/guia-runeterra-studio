r"""Prepara as pastas e o banco do canal Pokémon (roda uma vez; pode repetir sem estragar nada).

O catálogo de EFEITOS SONOROS (tabela `sons`, arquivos em dados/comum/sfx/) é ferramenta de edição do motor: é copiado
do catálogo base. A memória de uso (`uso_som`, `uso_midia`) começa vazia — cada canal tem a sua.

Uso:  set GRS_CANAL=pokemon && .venv\Scripts\python.exe tools\pokemon\preparar_canal.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

os.environ.setdefault("GRS_CANAL", "pokemon")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canal import CHAVE, caminho  # noqa: E402
from comum import RAIZ, abrir_acervo  # noqa: E402

assert CHAVE == "pokemon", "rode com GRS_CANAL=pokemon"
for chave in ("acervo", "dados_acervo", "internet", "projetos"):
    caminho(chave).mkdir(parents=True, exist_ok=True)
con = abrir_acervo()
if not con.execute("SELECT count(*) FROM sons").fetchone()[0]:
    base = sqlite3.connect(RAIZ / "dados" / "runeterra" / "acervo.db")
    colunas = [r[1] for r in base.execute("PRAGMA table_info(sons)")]
    linhas = base.execute(f"SELECT {', '.join(colunas)} FROM sons").fetchall()
    con.executemany(f"INSERT INTO sons ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})", linhas)
    con.commit()
    print(f"{len(linhas)} efeitos sonoros no catálogo do canal")
print("canal pokemon pronto:", caminho("dados_acervo").parent)
