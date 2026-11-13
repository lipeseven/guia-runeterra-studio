"""Gera exemplo/cena.json do kit/foco: cena de teste 1920x1080, 60 q/s, 6 s, usada pelos dois motores e pelos testes.

Fundo claro (assinatura do canal) com grade, textos e listras finas (para o desfoque ser visível e mensurável), um carro
estilizado de perfil que anda devagar (trilha `movimento`) e dois focos:
  - "asa": retângulo arredondado na asa traseira, 0,6–3,2 s;
  - "roda": elipse na roda dianteira, 3,5–5,7 s.
As caixas são ESTÁVEIS (pose de referência do carro); o kit as desloca pela mesma trilha do carro.

  .venv\\Scripts\\python.exe F1\\horizontal\\kit\\foco\\exemplo\\gerar_cena.py
"""
from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
W, H = 1920, 1080


def fundo_svg() -> str:
    p = []
    p.append(f'<rect width="{W}" height="{H}" fill="#f3f1ec"/>')
    for x in range(0, W + 1, 80):
        p.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#d9d5cc" stroke-width="2"/>')
    for y in range(0, H + 1, 80):
        p.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#d9d5cc" stroke-width="2"/>')
    # listras finas (alta frequência) em duas faixas: o desfoque apaga as listras
    for x in range(120, 640, 8):
        p.append(f'<rect x="{x}" y="96" width="4" height="120" fill="#2b2b2b"/>')
    for x in range(1300, 1820, 8):
        p.append(f'<rect x="{x}" y="880" width="4" height="110" fill="#2b2b2b"/>')
    p.append('<text x="700" y="190" font-family="Bahnschrift" font-weight="700" font-size="96" fill="#1c1c1c">INTERLAGOS</text>')
    p.append('<text x="128" y="980" font-family="Bahnschrift" font-size="44" fill="#3a3a3a">setor 2 · curva 8 · 326 km/h</text>')
    return "".join(p)


def carro_svg() -> str:
    """Carro de perfil (nariz à esquerda), pose de referência. Retorna o SVG e as caixas da asa e da roda dianteira."""
    p = []
    # sombra
    p.append('<ellipse cx="960" cy="742" rx="560" ry="18" fill="#00000022"/>')
    # assoalho e corpo
    p.append('<path d="M420 690 L1500 690 L1500 712 L420 712 Z" fill="#26262a"/>')
    p.append('<path d="M440 690 C520 650 640 640 760 632 L900 600 C960 560 1040 556 1100 586 L1360 600 L1470 612 L1480 690 Z" fill="#c8102e"/>')
    p.append('<path d="M900 600 C940 575 1000 570 1040 586 L1000 612 L910 616 Z" fill="#1d1d1f"/>')  # cockpit
    p.append('<path d="M930 590 C980 548 1050 548 1080 584" fill="none" stroke="#1d1d1f" stroke-width="10"/>')  # halo
    p.append('<path d="M780 640 L1380 640" stroke="#ffffff" stroke-width="6"/>')
    p.append('<text x="1110" y="672" font-family="Bahnschrift" font-weight="700" font-size="34" fill="#ffffff">16</text>')
    # asa dianteira
    p.append('<path d="M330 700 L560 700 L560 716 L330 716 Z" fill="#1d1d1f"/>')
    p.append('<path d="M340 684 L470 684 L470 694 L340 694 Z" fill="#c8102e"/>')
    # asa traseira (alvo 1): pilar + dois elementos + placa lateral
    p.append('<rect x="1440" y="520" width="18" height="110" fill="#1d1d1f"/>')
    p.append('<rect x="1392" y="496" width="150" height="26" rx="4" fill="#1d1d1f"/>')
    p.append('<rect x="1396" y="530" width="142" height="16" rx="4" fill="#c8102e"/>')
    p.append('<rect x="1526" y="486" width="16" height="96" rx="3" fill="#2b2b2b"/>')
    for x in range(1400, 1526, 9):
        p.append(f'<rect x="{x}" y="502" width="3" height="14" fill="#55565a"/>')
    # rodas
    for cx in (560, 1360):
        p.append(f'<circle cx="{cx}" cy="690" r="78" fill="#151517"/>')
        p.append(f'<circle cx="{cx}" cy="690" r="46" fill="#3a3b3f"/>')
        for k in range(8):
            import math
            a = k * math.pi / 4
            p.append(f'<line x1="{cx}" y1="690" x2="{cx + 44 * math.cos(a):.1f}" y2="{690 + 44 * math.sin(a):.1f}" stroke="#8a8b90" stroke-width="5"/>')
        p.append(f'<circle cx="{cx}" cy="690" r="10" fill="#d6d6d6"/>')
    return "".join(p)


def main() -> None:
    cena = {
        "largura": W, "altura": H, "fps": 60, "duracao": 6,
        "fundo_svg": fundo_svg(),
        "carro_svg": carro_svg(),
        # trilha do carro (e da âncora dos focos): anda 90 px para a esquerda e sobe 10 px
        "movimento": [{"t": 0, "dx": 0, "dy": 0}, {"t": 2, "dx": -30, "dy": -4}, {"t": 4, "dx": -62, "dy": -10}, {"t": 6, "dx": -90, "dy": -10}],
        "focos": [
            {"id": "asa", "em": 0.6, "ate": 3.2,
             "alvo": {"caixa": {"x": 1390, "y": 484, "w": 154, "h": 148}}},
            {"id": "roda", "em": 3.5, "ate": 5.7, "forma": "elipse", "folga": 10,
             "alvo": {"caixa": {"x": 482, "y": 612, "w": 156, "h": 156}}},
        ],
    }
    for f in cena["focos"]:
        f["alvo"]["movimento"] = cena["movimento"]
    (AQUI / "cena.json").write_text(json.dumps(cena, ensure_ascii=False), encoding="utf-8")
    print("cena.json gravada")


if __name__ == "__main__":
    main()
