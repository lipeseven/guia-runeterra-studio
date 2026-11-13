# Pastas do kit/imagens. Mídia e cache ficam em F1/dados/imagens (fora do Git: o .gitignore ignora toda pasta dados/).
# KIT_IMAGENS_DADOS muda a pasta (ex.: rodar de um worktree gravando na pasta principal).
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
F1 = AQUI.parents[2]
DADOS = Path(os.environ.get("KIT_IMAGENS_DADOS", F1 / "dados" / "imagens"))
CACHE = DADOS / "cache"
