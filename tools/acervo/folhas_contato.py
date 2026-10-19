"""Gera folhas de contato do acervo (para revisão visual / etiquetagem pelo Claude).

Uso:
    .venv\\Scripts\\python.exe tools\\acervo\\folhas_contato.py [--so-sem-etiqueta]

Saída: dados/acervo/folhas/folha_NNN.jpg — cada miniatura com "#id nome".
Transparentes aparecem sobre xadrez; vídeos têm borda azul; GIFs borda verde.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import DADOS_ACERVO, PASTA_ACERVO, PASTA_MINIATURAS, RAIZ, abrir_acervo  # noqa: E402

COLUNAS, LINHAS = 8, 5
CEL_W, CEL_H, ROTULO = 300, 230, 22
SAIDA = DADOS_ACERVO / "folhas"
BORDA = {"video": "#2f6fff", "gif": "#20b050"}


def xadrez(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), "#ddd")
    d = ImageDraw.Draw(img)
    for y in range(0, h, 16):
        for x in range((y // 16) % 2 * 16, w, 32):
            d.rectangle([x, y, x + 15, y + 15], fill="#aaa")
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-sem-etiqueta", action="store_true")
    a = ap.parse_args()

    con = abrir_acervo()
    filtro = "AND categoria IS NULL" if a.so_sem_etiqueta else ""
    itens = con.execute(
        f"SELECT id, nome, caminho, tipo, transparente FROM midias "
        f"WHERE tipo IN ('imagem','gif','video') {filtro} ORDER BY prefixo, nome").fetchall()

    SAIDA.mkdir(parents=True, exist_ok=True)
    for antiga in SAIDA.glob("*.jpg"):
        antiga.unlink()
    fonte = ImageFont.truetype("arialbd.ttf", 15)
    por_folha = COLUNAS * LINHAS
    for f in range(0, len(itens), por_folha):
        folha = Image.new("RGB", (COLUNAS * CEL_W, LINHAS * (CEL_H + ROTULO)), "#222")
        d = ImageDraw.Draw(folha)
        for i, r in enumerate(itens[f:f + por_folha]):
            x, y = (i % COLUNAS) * CEL_W, (i // COLUNAS) * (CEL_H + ROTULO)
            if r["transparente"]:
                # usa o original para mostrar a transparência real
                with Image.open(PASTA_ACERVO / r["caminho"]) as orig:
                    orig.seek(0)
                    mini = ImageOps.contain(orig.convert("RGBA"), (CEL_W - 6, CEL_H - 6))
                fundo = xadrez(*mini.size)
                fundo.paste(mini, mask=mini.getchannel("A"))
                mini = fundo
            else:
                mini = ImageOps.contain(Image.open(PASTA_MINIATURAS / f"{r['id']}.jpg"), (CEL_W - 6, CEL_H - 6))
            if r["tipo"] in BORDA:
                d.rectangle([x, y, x + CEL_W - 1, y + CEL_H - 1], outline=BORDA[r["tipo"]], width=3)
            folha.paste(mini, (x + (CEL_W - mini.width) // 2, y + (CEL_H - mini.height) // 2))
            d.text((x + 4, y + CEL_H + 2), f"#{r['id']} {r['nome']}"[:34], fill="white", font=fonte)
        folha.save(SAIDA / f"folha_{f // por_folha + 1:03d}.jpg", quality=82)
    print(f"{len(itens)} itens em {(len(itens) + por_folha - 1) // por_folha} folhas -> {SAIDA}")


if __name__ == "__main__":
    main()
