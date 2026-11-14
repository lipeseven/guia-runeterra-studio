"""Diagnóstico de saltos: diferença média entre quadros consecutivos (480p, cinza) nas cenas de GPS — lista quadros com
diferença > 15 (troca brusca da imagem) e a correlação de fase em volta do maior salto da cena 14; folha de 12 quadros
consecutivos em volta de cada quadro pedido. Uso: python diag.py 3666 295"""
import json, os, sys, cv2, numpy as np
from comum import VIDEO, OUT, C, NUM, GPS, TMP

alvo = [int(a) for a in sys.argv[1:]]
cap = cv2.VideoCapture(VIDEO); i = 0; prev = None; res = {NUM[g]: [] for g in GPS}; dist = {NUM[g]: [] for g in GPS}; pc = []
seqs = {a: [] for a in alvo}
hw = cv2.createHanningWindow((480, 270), cv2.CV_32F)
while True:
    ok, f = cap.read()
    if not ok: break
    g = cv2.cvtColor(cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    for a in alvo:
        if a - 6 <= i < a + 6: seqs[a].append((i, cv2.resize(f, (640, 360), interpolation=cv2.INTER_AREA)))
    if prev is not None:
        for gid in GPS:
            q0, q1 = C[gid]
            if q0 + 2 <= i < q1 - 2:
                d = float(np.abs(g - prev).mean()); dist[NUM[gid]].append(d)
                if d > 15: res[NUM[gid]].append((i, round(d, 1)))
        if 3640 <= i < 3700:
            (dx, dy), r = cv2.phaseCorrelate(prev, g, hw); pc.append((i, round(dx, 2), round(dy, 2), round(r, 2)))
    prev = g; i += 1
out = {"quadros_dif>15": {k: v for k, v in res.items()}, "dif_mediana": {k: round(float(np.median(v)), 2) for k, v in dist.items()},
       "dif_p99": {k: round(float(np.percentile(v, 99)), 2) for k, v in dist.items()}, "fase_14_q3640_3700": pc}
json.dump(out, open(os.path.join(TMP, "diag.json"), "w"), indent=1)
for k, v in res.items(): print(k, len(v), v[:40])
print(out["dif_mediana"], out["dif_p99"])
print([p for p in pc if abs(p[1]) > 2 or abs(p[2]) > 2])
for a, lst in seqs.items():
    tiles = []
    for q, t in lst:
        cv2.putText(t, f"q{q}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2); tiles.append(t)
    rows = [np.hstack(tiles[r * 4:(r + 1) * 4]) for r in range(len(tiles) // 4)]
    cv2.imwrite(os.path.join(OUT, f"diag_q{a}_seq12.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
