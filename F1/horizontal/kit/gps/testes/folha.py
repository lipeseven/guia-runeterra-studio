# Folha de sequência (contact sheet) a 60 q/s de um render com câmera FIXA, e medida do movimento do carro NA IMAGEM.
#  - folha_sequencia_<nome>.jpg: N quadros CONSECUTIVOS (1/60 s entre eles), mesmo recorte, numerados.
#  - folha_cebola_<nome>.jpg: "casca de cebola": o carro de cada quadro de um trecho sobre o fundo + gráfico do
#    deslocamento na tela por quadro (px/q) e do 2º diferencial (tranco). Passos iguais/suaves = sem tranco; sinal
#    negativo do produto escalar entre passos = vai-e-vem.
# Uso: python folha.py <video.mp4> <nome> [quadro_inicial] [n_quadros]   (para a cebola: render sem rastro e sem HUD)
import json
import sys
from pathlib import Path

import cv2
import numpy as np

SAIDA = Path(__file__).resolve().parents[3] / "testes" / "gps"


def ler(video):
    cap = cv2.VideoCapture(str(video))
    q = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        q.append(f)
    return q


def centroides(quadros):
    fundo = np.median(np.stack(quadros[::4]), axis=0).astype(np.uint8)
    cs, caixas = [], []
    for f in quadros:
        d = cv2.cvtColor(cv2.absdiff(f, fundo), cv2.COLOR_BGR2GRAY)
        m = (d > 28).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m)
        if n <= 1:
            cs.append(None); caixas.append(None); continue
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        if st[k, cv2.CC_STAT_AREA] < 30:
            cs.append(None); caixas.append(None); continue
        cs.append(cen[k]); caixas.append(st[k, :4])
    return fundo, cs, caixas


def main():
    video, nome = Path(sys.argv[1]), sys.argv[2]
    q = ler(video)
    fundo, cs, caixas = centroides(q)
    vis = [i for i, c in enumerate(cs) if c is not None]
    i0 = int(sys.argv[3]) if len(sys.argv) > 3 else vis[len(vis) // 3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    trecho = [i for i in range(i0, min(len(q), i0 + n))]
    # recorte comum: caixa que contém o carro em todos os quadros do trecho
    bx = [caixas[i] for i in trecho if caixas[i] is not None]
    x0 = max(0, min(b[0] for b in bx) - 40); y0 = max(0, min(b[1] for b in bx) - 30)
    x1 = min(q[0].shape[1], max(b[0] + b[2] for b in bx) + 40); y1 = min(q[0].shape[0], max(b[1] + b[3] for b in bx) + 30)
    w = 320
    cel = []
    for i in trecho:
        c = cv2.resize(q[i][y0:y1, x0:x1], (w, int(w * (y1 - y0) / (x1 - x0))))
        cv2.putText(c, f"q{i}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(c, f"q{i}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cel.append(c)
    col = 6
    while len(cel) % col:
        cel.append(np.full_like(cel[0], 255))
    folha = np.vstack([np.hstack(cel[r * col:(r + 1) * col]) for r in range(len(cel) // col)])
    cab = np.full((40, folha.shape[1], 3), 255, np.uint8)
    cv2.putText(cab, f"{nome}: quadros consecutivos {trecho[0]}-{trecho[-1]} a 60 q/s (1/60 s entre celulas), recorte fixo",
                (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    SAIDA.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(SAIDA / f"folha_sequencia_{nome}.jpg"), np.vstack([cab, folha]))

    # movimento na tela (todos os quadros com carro visível e longe das bordas)
    H, W = q[0].shape[:2]
    ok = [i for i in vis if caixas[i][0] > 2 and caixas[i][1] > 2 and caixas[i][0] + caixas[i][2] < W - 2 and caixas[i][1] + caixas[i][3] < H - 2]
    seq = [i for i in ok if i - 1 in ok]
    passos = {i: np.array(cs[i]) - np.array(cs[i - 1]) for i in seq}
    idx = sorted(passos)
    mod = np.array([np.linalg.norm(passos[i]) for i in idx])
    dots = np.array([passos[i] @ passos[i - 1] for i in idx if i - 1 in passos])
    d2 = np.abs(np.diff(mod))
    met = dict(video=video.name, quadros=len(q), quadros_com_carro=len(vis), passos_medidos=len(idx),
               passo_px_med=round(float(np.median(mod)), 2), passo_px_min=round(float(mod.min()), 2), passo_px_max=round(float(mod.max()), 2),
               variacao_passo_p95_px=round(float(np.percentile(d2, 95)), 3), variacao_passo_max_px=round(float(d2.max()), 3),
               recuos_na_tela=int((dots < 0).sum()),
               nota="centroide da diferença para o fundo (mediana); passo = deslocamento do carro na imagem entre quadros")

    # casca de cebola: carro de cada 3º quadro do trecho visível sobre o fundo
    ceb = fundo.copy()
    alvo = [i for i in ok][::3]
    for i in alvo:
        d = cv2.cvtColor(cv2.absdiff(q[i], fundo), cv2.COLOR_BGR2GRAY) > 28
        ceb[d] = q[i][d]
    # gráfico
    gh, gw = 260, ceb.shape[1]
    g = np.full((gh, gw, 3), 255, np.uint8)
    if len(idx) > 1:
        xs = np.interp(idx, [idx[0], idx[-1]], [50, gw - 20])
        top = max(1.0, mod.max() * 1.15)
        ys = gh - 30 - mod / top * (gh - 60)
        for k in range(len(xs) - 1):
            cv2.line(g, (int(xs[k]), int(ys[k])), (int(xs[k + 1]), int(ys[k + 1])), (40, 40, 200), 2)
        for k in range(len(xs)):
            cv2.circle(g, (int(xs[k]), int(ys[k])), 2, (0, 0, 0), -1)
        cv2.line(g, (50, gh - 30), (gw - 20, gh - 30), (0, 0, 0), 1)
        cv2.putText(g, f"deslocamento do carro na tela por quadro (px/q), quadros {idx[0]}-{idx[-1]}; max {top / 1.15:.1f} px; "
                       f"recuos {met['recuos_na_tela']}; variacao p95 {met['variacao_passo_p95_px']:.2f} px",
                    (50, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.imwrite(str(SAIDA / f"folha_cebola_{nome}.jpg"), np.vstack([ceb, g]))
    (SAIDA / f"folha_metricas_{nome}.json").write_text(json.dumps(met, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False))


if __name__ == "__main__":
    main()
