"""Gera uma tira de quadros ao longo de cenas específicas, para ver o movimento interno.

Uso:
    .venv\\Scripts\\python.exe tools\\analise_referencias\\amostrar_cenas.py <slug-do-video> <n> [<n> ...]

Cada cena vira uma linha com 5 quadros (0%, 25%, 50%, 75%, 95% da duração).
Saída: dados/runeterra/analise_referencias/<slug>/amostras/cenas_<n1>_<n2>....jpg
"""
from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from detectar_cortes import PASTA_SAIDA, PASTA_VIDEOS, slug, tempo  # noqa: E402

POSICOES = (0.0, 0.25, 0.5, 0.75, 0.95)
LARGURA = 400


def quadro(video: Path, t: float) -> Image.Image:
    png = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={LARGURA}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True,
    ).stdout
    return Image.open(BytesIO(png)).convert("RGB")


def main() -> None:
    nome, numeros = sys.argv[1], [int(n) for n in sys.argv[2:]]
    video = next(v for v in PASTA_VIDEOS.glob("*.mp4") if slug(v.stem) == nome)
    cenas = json.loads((PASTA_SAIDA / nome / "cortes.json").read_text(encoding="utf-8"))["cenas"]
    fonte = ImageFont.truetype("arial.ttf", 16)

    linhas = []
    for n in numeros:
        c = cenas[n - 1]
        imgs = [quadro(video, c["inicio"] + p * c["duracao"]) for p in POSICOES]
        w, h = imgs[0].size
        linha = Image.new("RGB", (w * len(imgs), h), "black")
        d = ImageDraw.Draw(linha)
        for i, img in enumerate(imgs):
            linha.paste(img, (i * w, 0))
            d.rectangle([i * w, 0, i * w + 150, 20], fill="black")
            d.text((i * w + 3, 1), f"#{n} {tempo(c['inicio'] + POSICOES[i] * c['duracao'])} {int(POSICOES[i] * 100)}%",
                   fill="yellow", font=fonte)
        linhas.append(linha)

    folha = Image.new("RGB", (linhas[0].width, sum(l.height for l in linhas)))
    y = 0
    for l in linhas:
        folha.paste(l, (0, y))
        y += l.height
    destino = PASTA_SAIDA / nome / "amostras"
    destino.mkdir(exist_ok=True)
    arquivo = destino / f"cenas_{'_'.join(map(str, numeros))}.jpg"
    folha.save(arquivo, quality=85)
    print(arquivo)


if __name__ == "__main__":
    main()
