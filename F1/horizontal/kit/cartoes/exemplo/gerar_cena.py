"""Gera a cena de teste do kit/cartoes (exemplo/cena.json) e a foto de exemplo (exemplo/foto_exemplo.jpg).

1920x1080, 60 q/s, 7 s, fundo claro com um traçado de pista estilizado:
  - tag "curva 8" ancorada num ponto fixo da pista (0,4–3,6 s);
  - tag "Leclerc 318 km/h" presa a um carro que anda pela pista até perto da borda direita (0,8–3,6 s): força o
    kit a escolher o lado que cabe o tempo todo;
  - cartão de pessoa (foto P&B + nome + função), 1,2–3,6 s;
  - cartão de capítulo "PARTE 02" com o traçado se desenhando, 4,0–6,9 s.
A foto é um RETRATO SINTÉTICO (formas desenhadas aqui), não é foto de pessoa real.

  .venv\\Scripts\\python.exe F1\\horizontal\\kit\\cartoes\\exemplo\\gerar_cena.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 60


def pista(u: float) -> tuple[float, float]:
    """curva fechada estilizada (u em 0..1) ocupando o meio/alto do quadro"""
    a = 2 * math.pi * u
    x = 960 + 760 * math.cos(a) + 90 * math.cos(3 * a)
    y = 470 + 300 * math.sin(a) - 70 * math.sin(2 * a)
    return x, y


def foto() -> None:
    im = Image.new("RGB", (480, 600), (150, 160, 175))
    d = ImageDraw.Draw(im)
    for y in range(600):
        c = int(120 + 80 * y / 600)
        d.line([(0, y), (480, y)], fill=(c, c - 10, c - 25))
    d.ellipse([150, 120, 330, 330], fill=(205, 170, 140))  # rosto
    d.ellipse([140, 90, 340, 210], fill=(60, 45, 35))  # cabelo
    d.rectangle([205, 310, 275, 380], fill=(190, 155, 125))  # pescoço
    d.ellipse([60, 360, 420, 760], fill=(200, 20, 30))  # macacão
    d.ellipse([190, 210, 215, 228], fill=(40, 30, 30)); d.ellipse([265, 210, 290, 228], fill=(40, 30, 30))
    d.arc([205, 250, 275, 295], 20, 160, fill=(120, 60, 50), width=5)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(AQUI / "foto_exemplo.jpg", quality=88)


def main() -> None:
    foto()
    pts = [pista(i / 400) for i in range(401)]
    d_pista = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    fundo = (f'<rect width="{W}" height="{H}" fill="#f3f1ec"/>'
             f'<path d="{d_pista}" fill="none" stroke="#2a2a2a" stroke-width="30" stroke-linejoin="round"/>'
             f'<path d="{d_pista}" fill="none" stroke="#9a9a9a" stroke-width="3" stroke-dasharray="18 16"/>')
    # carro anda de u=0,80 a u=1,04 (passa perto da borda direita: x ≈ 1810)
    t0, t1 = 0.8, 3.6
    trilha = []
    for q in range(round(t0 * FPS), round(t1 * FPS) + 1):
        t = q / FPS
        u = 0.80 + 0.24 * (t - t0) / (t1 - t0)
        x, y = pista(u % 1)
        trilha.append({"t": round(t, 5), "x": round(x, 2), "y": round(y, 2)})
    curva8 = pista(0.62)
    # traçado do capítulo: a mesma pista, normalizada para 0..1000
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = min(xs), min(ys)
    s = 1000 / (max(xs) - x0)
    d_tr = "M" + " L".join(f"{(x - x0) * s:.1f} {(y - y0) * s:.1f}" for x, y in pts) + " Z"
    cena = {
        "largura": W, "altura": H, "fps": FPS, "duracao": 7,
        "fundo_svg": fundo,
        "carro": trilha,
        "cartoes": [
            {"tipo": "tag", "id": "curva8", "em": 0.4, "ate": 3.6, "texto": "Curva 8 · Laranjinha", "ancora": [round(curva8[0], 2), round(curva8[1], 2)]},
            {"tipo": "tag", "id": "leclerc", "em": 0.8, "ate": 3.6, "texto": "Leclerc · 318 km/h", "ancora": trilha},
            {"tipo": "pessoa", "id": "pessoa", "em": 1.2, "ate": 3.6, "nome": "Charles Leclerc", "funcao": "Piloto da Ferrari",
             "foto": "foto_exemplo.jpg", "fotoTam": [480, 600], "fotoFoco": [0.5, 0.36], "cor": "#e10600"},
            {"tipo": "capitulo", "id": "parte2", "em": 4.0, "ate": 6.9, "numero": 2, "titulo": "Onde a Ferrari perdeu tempo",
             "tracado": {"d": d_tr, "largura": 1000, "altura": round((max(ys) - y0) * s, 1)}},
        ],
    }
    (AQUI / "cena.json").write_text(json.dumps(cena, ensure_ascii=False), encoding="utf-8")
    print("cena.json e foto_exemplo.jpg gravadas")


if __name__ == "__main__":
    main()
