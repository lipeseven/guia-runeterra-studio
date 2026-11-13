"""Gera exemplo/cena.json do kit/transicoes: 5 cenas paradas (fundo claro, letra grande, listras e grade) ligadas por
corte (com impacto) em 1 s, fade em 2 s, wipe em 3 s e zoom-through em 4 s; 5 s a 60 q/s.
As cenas são PARADAS de propósito: assim o teste de pixels mede só a transição (quadros que não são nem A nem B).

  .venv\\Scripts\\python.exe F1\\horizontal\\kit\\transicoes\\exemplo\\gerar_cena.py
"""
from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
W, H = 1920, 1080
CENAS = [("A", "#f3f1ec", "#e10600", "Corte"), ("B", "#eef2f4", "#1e5bc6", "Fade"), ("C", "#f4efe6", "#00875a", "Wipe"),
         ("D", "#f1eef4", "#7a2bb8", "Zoom"), ("E", "#f3f1ec", "#141414", "Fim")]


def cena_svg(i: int, letra: str, fundo: str, cor: str, nome: str) -> str:
    p = [f'<rect width="{W}" height="{H}" fill="{fundo}"/>']
    for x in range(0, W + 1, 120):
        p.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#d6d2c8" stroke-width="2"/>')
    # listras numa posição diferente por cena (contraste forte entre cenas em boa parte do quadro)
    y0 = 120 + 160 * i
    for k in range(14):
        p.append(f'<rect x="{80 + 120 * k}" y="{y0}" width="60" height="120" fill="{cor}" opacity="0.85"/>')
    x = 260 + 300 * i
    p.append(f'<text x="{x}" y="900" font-family="Bahnschrift" font-weight="700" font-size="520" fill="#141414">{letra}</text>')
    p.append(f'<text x="{(x + 520) % 1500 + 200}" y="980" font-family="Bahnschrift" font-size="64" fill="{cor}">{nome}</text>')
    return "".join(p)


def main() -> None:
    cena = {
        "largura": W, "altura": H, "fps": 60, "duracao": 5,
        "cenas": [cena_svg(i, *c) for i, c in enumerate(CENAS)],
        "transicoes": [
            {"tipo": "corte", "em": 1.0, "sfx": "impacto"},
            {"tipo": "fade", "em": 2.0},
            {"tipo": "wipe", "em": 3.0, "direcao": "direita"},
            {"tipo": "zoom", "em": 4.0},
        ],
    }
    (AQUI / "cena.json").write_text(json.dumps(cena, ensure_ascii=False), encoding="utf-8")
    print("cena.json gravada")


if __name__ == "__main__":
    main()
