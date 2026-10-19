r"""Análise completa das referências DO CANAL (GRS_CANAL), sem cota: cortes → transcrição → estatísticas →
separação de sons (Demucs) → classificação dos sons (CLAP). Cada etapa pula o que já foi feito.
A leitura visual e o guia de estilo vêm depois, com o Claude, a partir destes resultados.

Uso:  set GRS_CANAL=pokemon && .venv\Scripts\python.exe tools\analise_referencias\rodar_tudo.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ETAPAS = ["detectar_cortes.py", "transcrever.py", "estatisticas.py", "separar_sons.py", "analisar_sons.py"]

if __name__ == "__main__":
    for etapa in ETAPAS:
        print(f"=== {etapa}", flush=True)
        r = subprocess.run([sys.executable, str(PASTA / etapa)], cwd=PASTA.parents[1])
        if r.returncode != 0:
            print(f"!!! {etapa} falhou (código {r.returncode}); seguindo para a próxima", flush=True)
    print("=== análise das referências concluída", flush=True)
