"""Folhas por cena: 8 quadros (início+2, 6 no meio, fim-3) e 12 consecutivos no meio; nas cenas com movimento
(GPS, gráficos, barras) 2ª folha de 12 consecutivos a 80 %. Quadros extras em resolução cheia: python quadros.py 469 1848 ..."""
import os, sys, cv2, numpy as np
from comum import VIDEO, OUT, FIN, NUMS, GPS, GRAF

MOV = set(GPS) | set(GRAF)
sheets = {}
for n, c in zip(NUMS, FIN["cenas"]):
    q0, q1 = c["Q0"], c["Q1"]; L = q1 - q0
    sheets[f"c{n}_{c['id']}_8q"] = [q0 + 2] + [int(q0 + L * k / 7) for k in range(1, 7)] + [q1 - 3]
    sheets[f"c{n}_{c['id']}_seq12"] = list(range(q0 + L // 2 - 6, q0 + L // 2 + 6))
    if c["id"] in MOV:
        s = q0 + int(L * 0.8) - 6
        sheets[f"c{n}_{c['id']}_seq12b"] = list(range(s, s + 12))
extra = [int(a) for a in sys.argv[1:]]
so_extra = bool(extra)
need = {}
if not so_extra:
    for nm, idx in sheets.items():
        for i in idx: need.setdefault(i, []).append(nm)
for i in extra: need.setdefault(i, []).append("X")
got = {}
cap = cv2.VideoCapture(VIDEO); i = 0; mx = max(need)
while i <= mx:
    ok, f = cap.read()
    if not ok: break
    if i in need:
        for nm in need[i]:
            if nm == "X": cv2.imwrite(os.path.join(OUT, f"q{i}_cheio.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 85])
            else: got[(nm, i)] = f
    i += 1
if not so_extra:
    W, H = 480, 270
    for nm, idx in sheets.items():
        tiles = []
        for i in idx:
            t = cv2.resize(got[(nm, i)], (W, H), interpolation=cv2.INTER_AREA)
            cv2.putText(t, f"q{i} {i/60:.2f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            tiles.append(t)
        rows = [np.hstack(tiles[r * 4:(r + 1) * 4]) for r in range(len(tiles) // 4)]
        cv2.imwrite(os.path.join(OUT, nm + ".jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print("ok", 0 if so_extra else len(sheets), "folhas;", len(extra), "extras")
