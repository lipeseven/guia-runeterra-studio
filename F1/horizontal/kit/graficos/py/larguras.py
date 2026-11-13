"""Gera fonte/segoe_larguras.json: avanço de cada caractere da Segoe UI (Windows) em milésimos de em, por peso.

O kit calcula o layout (onde cabe cada rótulo, sem sobreposição) sem navegador; para isso precisa da largura do texto.
A verificação (testes/graficos/rodar.py) mede depois as caixas REAIS no Chrome e reprova se a estimativa errar.
Uso: python larguras.py
"""
import json
from pathlib import Path

from PIL import ImageFont

ARQ = {400: "segoeui.ttf", 600: "seguisb.ttf", 700: "segoeuib.ttf"}
CHARS = [chr(c) for c in range(32, 127)] + list("ÀÁÂÃÇÉÊÍÓÔÕÚàáâãçéêíóôõú·×−–—→←↑↓Δ≈±°%‰…“”‘’")
out = {"_nota": "Segoe UI (C:/Windows/Fonts), avanço em 1/1000 em, sem kerning. Gerado por py/larguras.py.",
       "ascendente": 0.74, "descendente": 0.24, "pesos": {}}
for peso, arq in ARQ.items():
    f = ImageFont.truetype(f"C:/Windows/Fonts/{arq}", 1000)
    out["pesos"][str(peso)] = {c: round(f.getlength(c)) for c in CHARS}
dest = Path(__file__).resolve().parent.parent / "fonte" / "segoe_larguras.json"
dest.parent.mkdir(exist_ok=True)
dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(dest, len(CHARS))
