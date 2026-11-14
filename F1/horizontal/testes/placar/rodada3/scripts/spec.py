"""Lista as cenas da SPEC (id + parâmetros) para o avaliador. Uso: python spec.py"""
import json
from comum import PROJ
s = json.load(open(PROJ + r"\horizontal\spec.json", encoding="utf-8"))
for c in s.get("cenas", s):
    d = {k: v for k, v in c.items() if k != "id"}
    print(c.get("id"), json.dumps(d, ensure_ascii=False)[:700]); print()
