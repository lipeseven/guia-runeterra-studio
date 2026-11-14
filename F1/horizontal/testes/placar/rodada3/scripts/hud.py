"""HUD x OpenF1: leituras do HUD feitas OLHANDO os quadros (hud.json: cena -> [quadro, HAM, RUS]) contra o car_data bruto
do kit interpolado no mesmo tempo da volta (t = inicio + (q - Q0)/60 * fator, parâmetros da SPEC). Saída: _aval/hud.json"""
import json, os, numpy as np
from comum import KIT, PROJ, C, NUM, TMP, AQUI

cmp = json.load(open(KIT + r"\graficos\comparacoes\11400_44-19_63-21.json", encoding="utf-8"))
bruto = {p["sigla"]: p["bruto"] for p in cmp["pilotos"]}
spec = json.load(open(PROJ + r"\horizontal\spec.json", encoding="utf-8"))
par = {}
for c in spec["cenas"]:
    for k in c["kits"]:
        if k["kit"] == "gps": par[c["id"]] = (k["params"]["inicio"], k["params"]["fator"])
hud = json.load(open(os.path.join(AQUI, "hud.json")))
out = []
for gid, lst in hud.items():
    ini, fat = par[gid]; q0 = C[gid][0]
    for q, h, r in lst:
        t = ini + (q - q0) / 60 * fat
        vh = float(np.interp(t, bruto["HAM"]["t"], bruto["HAM"]["vel"])); vr = float(np.interp(t, bruto["RUS"]["t"], bruto["RUS"]["vel"]))
        out.append({"cena": NUM[gid], "q": q, "t_volta": round(t, 2), "HAM_hud": h, "HAM_openf1": round(vh), "RUS_hud": r, "RUS_openf1": round(vr),
                    "dH": h - round(vh), "dR": r - round(vr)})
d = np.array([[o["dH"], o["dR"]] for o in out]).ravel()
res = {"leituras": out, "resumo": {"n_valores": len(d), "erro_abs_med": round(float(np.mean(np.abs(d))), 1), "p90": round(float(np.percentile(np.abs(d), 90)), 1),
       "max": int(np.abs(d).max())}}
json.dump(res, open(os.path.join(TMP, "hud.json"), "w"), indent=1)
for o in out: print(o)
print(res["resumo"])
