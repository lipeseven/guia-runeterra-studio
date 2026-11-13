"""Gera exemplo/cena.json: a cena de teste do kit de anotação (1920x1080, 60 q/s, 7 s), igual para os dois motores.

- Textos da cena (Arial/Arial Black do Windows, desenhados como <text> SVG pela linha de base): a caixa de cada um é a
  caixa de TINTA medida com Pillow + 4 px; o teste de render confere que nenhum pixel escuro sai dela.
- Peça "asa": retângulo 360x110 que anda (pan) e gira ±12° (como uma peça 3D girando). A caixa do alvo é a caixa
  ESTÁVEL (envelope do giro inteiro em volta do pivô), não a caixa projetada de cada quadro.

Rodar: .venv\\Scripts\\python.exe F1\\horizontal\\kit\\anotacao\\exemplo\\gerar_cena.py
"""
import json
import math
from pathlib import Path

from PIL import ImageFont

AQUI = Path(__file__).resolve().parent
FONTES = {"Arial Black": r"C:\Windows\Fonts\ariblk.ttf", "Arial": r"C:\Windows\Fonts\arialbd.ttf"}
FPS, DUR = 60, 7.0


def texto(t: str, fonte: str, tam: int, x: float, y: float) -> dict:
    f = ImageFont.truetype(FONTES[fonte], tam)
    x0, y0, x1, y1 = f.getbbox(t, anchor="ls")
    pad = 4
    return {"caixa": {"x": x + x0 - pad, "y": y + y0 - pad, "w": x1 - x0 + 2 * pad, "h": y1 - y0 + 2 * pad}, "texto": True,
            "render": {"texto": t, "fonte": fonte, "peso": 900 if fonte == "Arial Black" else 700, "tamanho": tam, "x": x, "y": y}}


def peca() -> dict:
    w, h, amp, per = 360, 110, 12.0, 2.4
    cx0, cy0 = 560.0, 560.0

    def desl(t: float) -> tuple[float, float]:
        u = min(1.0, t / DUR)
        s = u * u * (3 - 2 * u)
        return 150 * s, -36 * math.sin(math.pi * u)

    # envelope do giro: maior meio-tamanho em volta do pivô (amostrado a cada quadro)
    hw = hh = 0.0
    for q in range(int(DUR * FPS) + 1):
        g = math.radians(amp * math.sin(2 * math.pi * (q / FPS) / per))
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            x, y = sx * w / 2, sy * h / 2
            hw = max(hw, abs(x * math.cos(g) - y * math.sin(g)))
            hh = max(hh, abs(x * math.sin(g) + y * math.cos(g)))
    mov = []
    for i in range(int(DUR / 0.25) + 1):
        t = i * 0.25
        dx, dy = desl(t)
        mov.append({"t": t, "dx": round(dx, 3), "dy": round(dy, 3)})
    return {"caixa": {"x": round(cx0 - hw, 3), "y": round(cy0 - hh, 3), "w": round(2 * hw, 3), "h": round(2 * hh, 3)},
            "movimento": mov, "peca": {"w": w, "h": h, "giroAmp": amp, "giroPeriodo": per, "cx": cx0, "cy": cy0}}


def main() -> None:
    alvos = {
        "asa": peca(),
        "titulo": texto("ASA TRASEIRA", "Arial Black", 64, 120, 150),
        "valor": texto("323", "Arial Black", 120, 1180, 450),
        "rotulo": texto("VELOCIDADE MÁXIMA · SF-26", "Arial", 30, 1180, 510),
        "s1": texto("SETOR 1   +0,412", "Arial Black", 44, 1180, 720),
        "s2": texto("SETOR 2   +1,155", "Arial Black", 44, 1180, 790),
        "s3": texto("SETOR 3   −0,086", "Arial Black", 44, 1180, 860),
    }
    v = alvos["valor"]["caixa"]
    alvos["unidade"] = texto("km/h", "Arial Black", 56, v["x"] + v["w"] + 22, 450)
    anot = [
        {"id": "oval-asa", "tipo": "oval", "alvo": "asa", "em": 0.4, "folga": 26},
        {"id": "nota-gira", "tipo": "nota", "texto": "gira ±12°", "em": 1.15, "perto": {"alvo": "oval-asa", "lado": "auto", "distancia": 60, "desloc": [230, 0]}},
        {"id": "seta-gira", "tipo": "seta", "de": "nota-gira", "para": "oval-asa", "em": 2.25, "curva": -0.18},
        {"id": "sub-titulo", "tipo": "sublinhado", "alvo": "titulo", "em": 2.75},
        {"id": "corr-valor", "tipo": "corrigido", "alvo": "valor", "texto": "326", "em": 3.3},
        {"id": "chave-s12", "tipo": "chave", "alvos": ["s1", "s2"], "lado": "direita", "em": 4.6},
        {"id": "nota-78", "tipo": "nota", "texto": "78% aqui", "em": 5.05, "perto": {"alvo": "chave-s12", "lado": "direita", "distancia": 20}},
    ]
    cena = {"largura": 1920, "altura": 1080, "fps": FPS, "duracao": DUR, "fundo": "#f2f1ec", "tinta": "#141414",
            "alvos": alvos, "anotacoes": anot}
    (AQUI / "cena.json").write_text(json.dumps(cena, ensure_ascii=False, indent=1), encoding="utf-8")
    print("cena.json:", {k: a["caixa"] for k, a in alvos.items()})


if __name__ == "__main__":
    main()
