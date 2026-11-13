"""Gera kit/cartoes/larguras.ts: avanço de cada caractere (unidades de 1/1000 do tamanho da fonte), subida e descida
das três variações da Bahnschrift usadas nos cartões. Com isso o kit sabe a largura do texto SEM navegador (o layout
e o teste "a tag não sai do quadro" rodam em Node puro). Os motores desenham com `font-kerning: none`, então a
largura no Chrome é a soma dos avanços (o teste de render confere nos pixels).

  .venv\\Scripts\\python.exe F1\\horizontal\\kit\\cartoes\\gerar_larguras.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

AQUI = Path(__file__).resolve().parent
FONTE = r"C:\Windows\Fonts\bahnschrift.ttf"
# estilo → (wght, wdth)
ESTILOS = {"forte": (700, 87.5), "medio": (600, 100), "normal": (400, 100)}
CHARS = "".join(chr(c) for c in range(32, 127)) + "ÀÁÂÃÄÇÈÉÊËÍÎÏÑÓÔÕÖÚÛÜàáâãäçèéêëíîïñóôõöúûüºª°·–—…×±’‘“”«»€"


def main() -> None:
    tab = {}
    for nome, (wg, wd) in ESTILOS.items():
        f = ImageFont.truetype(FONTE, 1000)
        f.set_variation_by_axes([wg, wd])
        asc, desc = f.getmetrics()
        # caixa de tinta das maiúsculas/acentos (para a caixa do texto não cortar acento)
        b = f.getbbox("ÁÇÉÍÓÚÃÕÊÔgjpqy", anchor="ls")
        tab[nome] = {"wght": wg, "wdth": wd, "asc": asc, "desc": desc, "tinta_cima": -b[1], "tinta_baixo": b[3],
                     "av": {c: round(f.getlength(c), 1) for c in CHARS}}
    src = ("// GERADO por gerar_larguras.py (Bahnschrift do Windows, PIL). Não editar à mão.\n"
           "// av = avanço por caractere em 1/1000 do tamanho; asc/desc = métricas da fonte; tinta_* = maior tinta de acento/descendente.\n"
           "export type Estilo = \"forte\" | \"medio\" | \"normal\";\n"
           "export type TabelaFonte = { wght: number; wdth: number; asc: number; desc: number; tinta_cima: number; tinta_baixo: number; av: Record<string, number> };\n"
           f"export const LARGURAS: Record<Estilo, TabelaFonte> = {json.dumps(tab, ensure_ascii=False)};\n")
    (AQUI / "larguras.ts").write_text(src, encoding="utf-8")
    print({k: (v["asc"], v["desc"], v["tinta_cima"], v["tinta_baixo"], v["av"]["M"]) for k, v in tab.items()})


if __name__ == "__main__":
    main()
