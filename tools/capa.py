"""Detecta os ícones redondos na capa do vídeo (grade de personagens feita pelo Felipe).

Uso:
    .venv\\Scripts\\python.exe tools\\capa.py <imagem-da-capa> [--nomes "A,B,C,..."] [--debug saida.jpg]

Imprime JSON com os círculos em ordem de leitura (linha a linha, da esquerda para a direita):
    [{"nome": "...", "cx": 0.12, "cy": 0.21, "r": 0.11}, ...]   (cx/cy em fração da largura/altura,
                                                                  r em fração do menor lado)
Os nomes, se não forem passados, ficam vazios — o diretor (Claude) os lê na capa.
"""
from __future__ import annotations

import argparse
import json

import cv2
import numpy as np


def detectar(caminho: str) -> tuple[list[dict], np.ndarray]:
    img = cv2.imdecode(np.fromfile(caminho, dtype=np.uint8), cv2.IMREAD_COLOR)  # aceita acentos no caminho
    h, w = img.shape[:2]
    menor = min(w, h)
    # Ícones são manchas opacas sobre fundo (quase) branco: separa o "não branco" e
    # fica com as manchas cuja área bate com a do círculo envolvente (circularidade alta).
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mascara = cv2.threshold(cinza, 235, 255, cv2.THRESH_BINARY_INV)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    circulos = []
    for c in contornos:
        (x, y), r = cv2.minEnclosingCircle(c)
        if r < menor * 0.07 or r > menor * 0.35:
            continue
        if cv2.contourArea(c) / (np.pi * r * r) > 0.85:
            circulos.append((x, y, r))
    if not circulos:
        return [], img
    # Mantém só os de raio parecido com a mediana (descarta falsos positivos).
    mediana = float(np.median([c[2] for c in circulos]))
    circulos = [c for c in circulos if abs(c[2] - mediana) < mediana * 0.15]
    # Ordem de leitura: agrupa em linhas pela altura e ordena cada linha por x.
    circulos.sort(key=lambda c: c[1])
    linhas: list[list[tuple]] = []
    for c in circulos:
        if linhas and abs(linhas[-1][0][1] - c[1]) < mediana:
            linhas[-1].append(c)
        else:
            linhas.append([c])
    ordenados = [c for linha in linhas for c in sorted(linha, key=lambda c: c[0])]
    return [{"cx": round(x / w, 4), "cy": round(y / h, 4), "r": round(r / menor, 4)} for x, y, r in ordenados], img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("capa")
    ap.add_argument("--nomes", default="")
    ap.add_argument("--debug")
    a = ap.parse_args()
    circulos, img = detectar(a.capa)
    nomes = [n.strip() for n in a.nomes.split(",")] if a.nomes else []
    for k, c in enumerate(circulos):
        c["nome"] = nomes[k] if k < len(nomes) else ""
    if a.debug:
        h, w = img.shape[:2]
        for k, c in enumerate(circulos):
            centro = (int(c["cx"] * w), int(c["cy"] * h))
            cv2.circle(img, centro, int(c["r"] * min(w, h)), (0, 0, 255), 6)
            cv2.putText(img, str(k), centro, cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 6)
        cv2.imencode(".jpg", img)[1].tofile(a.debug)
    print(json.dumps(circulos, ensure_ascii=False))


if __name__ == "__main__":
    main()
