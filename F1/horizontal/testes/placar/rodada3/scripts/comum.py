"""Caminhos comuns do placar da rodada 3 (rodar com o .venv do projeto a partir de qualquer pasta)."""
import json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(AQUI)                      # F1/horizontal/testes/placar/rodada3
REPO = os.path.abspath(os.path.join(OUT, *[".."] * 5))  # raiz do repositório (pasta principal ou worktree)
# dados ficam fora do Git: sempre na pasta principal
PRINCIPAL = r"C:\Users\Felipe\Downloads\exclusive Claude"
PROJ = PRINCIPAL + r"\F1\dados\projetos\nove-milesimos-teste-do-fluxo-completo"
VIDEO = PROJ + r"\saida\final_v4.mp4"
KIT = PRINCIPAL + r"\F1\horizontal\kit"
TMP = os.path.join(REPO, "_aval")                # intermediários (não versionados)
os.makedirs(TMP, exist_ok=True)

FIN = json.load(open(PROJ + r"\horizontal\final\final.json", encoding="utf-8"))
NUMS = ["01", "02", "03", "04", "05", "06", "07", "08", "09a", "09b", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19"]
C = {c["id"]: (c["Q0"], c["Q1"]) for c in FIN["cenas"]}
NUM = {c["id"]: n for n, c in zip(NUMS, FIN["cenas"])}
GPS = ["447ab02a", "e0df513b", "a37e2524", "d5a93934", "76c5a688"]
GRAF = ["747ede00", "dd4ffd33", "528c1e00", "a68a79fb", "760ea8f0"]
