"""Medidas de vídeo da rodada 3 (uma passada pelo MP4):
- GPS: correlação de fase do quadro inteiro (480p) -> velocidade, reversões, salto p99/máx (tranco);
- etiquetas HAM/RUS nas 5 cenas de GPS: caixa vermelha/verde com texto branco; sobreposição e TROCA de lado entre quadros;
- ovais/traços das anotações (caixa do traço vermelho) depois de desenhados;
- diferença média por quadro (para achar quando algo entra na tela) nas cenas 9b, 11, 15, 16;
- igualdade com o final_v3 nas cenas que não mudaram (PSNR em 3 quadros por cena, mesmos tempos).
Saída: _aval/video.json"""
import json, os, cv2, numpy as np
from comum import VIDEO, PROJ, C, NUM, GPS, TMP

ANOT = {"c8b897f1": (60, 97), "abbcf455": (1020, 1052), "791bf924": (1150, 1215), "408641ec": (4800, 4840), "e9aa5677": (5220, 5420)}
DIFF = ["09e13e9a", "528c1e00", "fe9cb062", "760ea8f0", "d5a93934", "a37e2524", "447ab02a", "e0df513b", "76c5a688"]
V3 = PROJ + r"\saida\final_v3.mp4"


def rotulos(f):
    """caixas das etiquetas: componente vermelho (HAM) ou verde-água (RUS) 30-160 px de largura com texto branco dentro"""
    b, g, r = [f[:, :, k].astype(np.int16) for k in range(3)]
    out = {}
    masks = {"HAM": (r > 180) & (g < 70) & (b < 100), "RUS": (g > 160) & (b > 130) & (r < 90)}
    white = (r > 230) & (g > 230) & (b > 230)
    for nome, m in masks.items():
        m = m.copy(); m[:330, :450] = False; m[:330, 1480:] = False; m[960:, :] = False  # sem HUD, minimapa, rodapé
        # abertura 7x7: corta a perninha (2-3 px) que liga a etiqueta ao rastro/ponto do carro
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        best = None
        for k in range(1, n):
            x, y, w, h, a = st[k]
            if 30 <= w <= 170 and 16 <= h <= 60 and w > h:
                wt = white[y:y + h, x:x + w].mean()
                if wt > 0.06 and (best is None or a > best[4]): best = (int(x), int(y), int(w), int(h), int(a))
        out[nome] = best
    return out


res = {"gps": {}, "rotulos": {}, "anot": {}, "diff": {}, "igual_v3": {}}
cap = cv2.VideoCapture(VIDEO); cap3 = cv2.VideoCapture(V3)
n3 = int(cap3.get(cv2.CAP_PROP_FRAME_COUNT))
prev = None; prevfull = None; i = 0
mot = {g: [] for g in GPS}; rot = {g: [] for g in GPS}; bb = {a: [] for a in ANOT}; df = {d: [] for d in DIFF}
cmp_q = set()
for cid, (q0, q1) in C.items():
    for fr in (0.25, 0.5, 0.75): cmp_q.add(int(q0 + (q1 - q0) * fr))
f3cache = {}
# lê o v3 só nos quadros de comparação (mesmo índice)
j = 0
while j <= max(cmp_q) and j < n3:
    ok, f3 = cap3.read()
    if not ok: break
    if j in cmp_q: f3cache[j] = cv2.resize(f3, (480, 270), interpolation=cv2.INTER_AREA)
    j += 1
while True:
    ok, f = cap.read()
    if not ok: break
    small = cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
    for gid in GPS:
        q0, q1 = C[gid]
        if q0 + 20 <= i < q1 - 20 and prev is not None:
            # cópias: phaseCorrelate com janela altera os arrays no lugar (falsearia a medida seguinte)
            (dx, dy), r = cv2.phaseCorrelate(prev.copy(), g.copy(), cv2.createHanningWindow((480, 270), cv2.CV_32F))
            mot[gid].append((i, dx, dy, r))
        if q0 + 25 <= i < q1 - 20:
            rot[gid].append((i, rotulos(f)))
    for a, (s, e) in ANOT.items():
        if s <= i < e:
            b_, g_, r_ = f[:, :, 0].astype(int), f[:, :, 1].astype(int), f[:, :, 2].astype(int)
            m = (r_ > 150) & (g_ < 90) & (b_ < 90); ys, xs = np.nonzero(m)
            bb[a].append((i, int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()), int(m.sum())) if len(xs) else (i, None))
    for d in DIFF:
        q0, q1 = C[d]
        if q0 < i < q1 and prev is not None: df[d].append((i, round(float(np.abs(g - prev).mean()), 2)))
    if i in f3cache:
        a3 = f3cache[i]; mse = float(((small.astype(np.float32) - a3.astype(np.float32)) ** 2).mean())
        res["igual_v3"].setdefault(NUM[[k for k, (x0, x1) in C.items() if x0 <= i < x1][0]], []).append(round(10 * np.log10(255 ** 2 / max(mse, 1e-6)), 1))
    prev = g; i += 1

for gid, v in mot.items():
    a = np.array([[x[1], x[2]] for x in v]); n = np.hypot(a[:, 0], a[:, 1]); jj = np.hypot(*(np.diff(a, axis=0).T))
    rr = np.array([x[3] for x in v])
    rev = sum(1 for k in range(1, len(a)) if n[k] > 0.3 and n[k - 1] > 0.3 and (a[k] @ a[k - 1]) < 0)
    baixa = [int(v[k][0]) for k in range(len(v)) if rr[k] < 0.1]  # correlação sem pico (resposta < 0,1): medida não confiável
    res["gps"][NUM[gid] + "_" + gid] = {"quadros": len(a), "vel_med_px480": round(float(np.median(n)), 3), "vel_p95": round(float(np.percentile(n, 95)), 3),
        "salto_p99_px": round(float(np.percentile(jj, 99)), 3), "salto_max_px": round(float(jj.max()), 3), "q_salto_max": int(v[int(jj.argmax()) + 1][0]),
        "reversoes": rev, "resposta_mediana": round(float(np.median(rr)), 3), "quadros_resposta_<0.1": baixa[:20]}
for gid, v in rot.items():
    ambos = [(q, d) for q, d in v if d["HAM"] and d["RUS"]]
    sobre = []; lado = []; trocas = []; lado_prev = None; dist = []
    for q, d in ambos:
        h, r = d["HAM"], d["RUS"]
        ix = max(0, min(h[0] + h[2], r[0] + r[2]) - max(h[0], r[0])); iy = max(0, min(h[1] + h[3], r[1] + r[3]) - max(h[1], r[1]))
        if ix * iy > 0: sobre.append(q)
        dxc = (h[0] + h[2] / 2) - (r[0] + r[2] / 2); dyc = (h[1] + h[3] / 2) - (r[1] + r[3] / 2)
        # lado só conta quando estão lado a lado (|dy| < altura) e afastados
        if abs(dyc) < h[3] and abs(dxc) > 10:
            s = 1 if dxc > 0 else -1
            if lado_prev is not None and s != lado_prev[0] and q - lado_prev[1] <= 3: trocas.append(q)
            lado_prev = (s, q)
        elif abs(dxc) < h[2] / 2 and abs(dyc) > 10:  # empilhadas: troca de cima/baixo
            s = 2 if dyc > 0 else -2
            if lado_prev is not None and s != lado_prev[0] and abs(s) == abs(lado_prev[0]) and q - lado_prev[1] <= 3: trocas.append(q)
            lado_prev = (s, q)
        # salto do centro da etiqueta HAM entre quadros consecutivos
    pulos = []
    for (q0_, d0), (q1_, d1) in zip(v, v[1:]):
        for nome in ("HAM", "RUS"):
            if d0[nome] and d1[nome] and q1_ == q0_ + 1:
                pulos.append(abs((d1[nome][0] + d1[nome][2] / 2) - (d0[nome][0] + d0[nome][2] / 2)))
    pulos = np.array(pulos) if pulos else np.zeros(1)
    res["rotulos"][NUM[gid] + "_" + gid] = {"quadros": len(v), "com_as_duas": len(ambos), "so_uma_ou_nenhuma": len(v) - len(ambos),
        "quadros_sobrepostas": len(sobre), "q_sobrepostas": sobre[:15], "trocas_de_lado": len(trocas), "q_trocas": trocas[:30],
        "salto_x_etiqueta_p99_px": round(float(np.percentile(pulos, 99)), 1), "salto_x_max_px": round(float(pulos.max()), 1)}
for a, v in bb.items():
    vv = [x for x in v if x[1] is not None]; arr = np.array([x[1:5] for x in vv])
    res["anot"][NUM[a] + "_" + a] = {"janela": ANOT[a], "quadros": len(v), "com_traco": len(vv),
        "var_bbox_px[x0,x1,y0,y1]": [int(arr[:, k].max() - arr[:, k].min()) for k in range(4)] if len(vv) else None}
for d, v in df.items():
    pk = sorted(v, key=lambda x: -x[1])[:6]
    res["diff"][NUM[d] + "_" + d] = {"picos(q,dif)": sorted(pk), "pct_quadros_parados(<0.05)": round(100 * np.mean([x[1] < 0.05 for x in v]), 1),
                                     "maior_trecho_parado_s": 0}
    run = best = 0
    for _, x in v:
        run = run + 1 if x < 0.05 else 0; best = max(best, run)
    res["diff"][NUM[d] + "_" + d]["maior_trecho_parado_s"] = round(best / 60, 2)
json.dump(res, open(os.path.join(TMP, "video.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, indent=0)[:9000])
