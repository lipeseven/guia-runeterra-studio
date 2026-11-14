# Prepara a cena HyperFrames "melhor volta do Hamilton no mod VHE de Interlagos" (teste do kit/gps com mod do AC).
# Monta assets/ (fora do Git): links dos .glb (pista visual do mod + Ferrari), cópia de kit/gps/src e das duas voltas
# (_ideal = carro no traçado ideal do mod, lateral INFERIDA; _livre = linha do GPS do OpenF1 sem correção lateral) e
# assets/cfg.js com a decupagem: panorâmica da volta inteira + recortes das curvas (câmera de cima, carro subindo na
# tela: esquerda/direita da tela = do carro) e o S do Senna também em perseguição.
# Uso: python preparar.py   (depois: npx --yes hyperframes@0.9.20 render -o <saida.mp4>)
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parent.parent / "kit" / "gps"
sys.path.insert(0, str(KIT / "py"))
import lateral as LAT  # noqa: E402
import pista as PISTA  # noqa: E402

CIRCUITO = "Interlagos_vhe"
VOLTA = "11408_44_12_Interlagos_vhe"
FPS = 60
# grupos de curvas mostrados nos recortes (nomes de lateral.CURVAS_INTERLAGOS)
GRUPOS = [("S do Senna", ["S do Senna (1)", "S do Senna (2)"]), ("Curva do Sol", ["Curva do Sol"]),
          ("Descida do Lago", ["Descida do Lago (4)", "Descida do Lago (5)"]), ("Ferradura", ["Ferradura (6)", "Ferradura (7)"]),
          ("Laranja", ["Laranja"]), ("Pinheirinho", ["Pinheirinho"]), ("Bico de Pato", ["Bico de Pato"]),
          ("Mergulho", ["Mergulho (1)", "Mergulho (2)"]), ("Junção", ["Junção"]), ("Subida dos Boxes", ["Subida dos Boxes"])]
ANTES, DEPOIS = 1.4, 1.1        # s de volta antes do 1º ápice e depois do último
INTRO, PANORAMA = 3.5, 12.0     # s de cena: título sobre o mapa; volta inteira acelerada
LONGO, FATOR_LONGO = 4.5, 1.5   # recorte com mais de LONGO s de volta passa a 1,5x (S do Senna de cima: sempre 1x)


def tempo_em_s(v, sv):
    """t (s de volta) em que o relógio da volta passa pelo arco sv do caminho."""
    R = v["relogio"]
    tg = R["t0"] + np.arange(len(R["s"])) * R["dt"]
    return float(np.interp(sv, R["s"], tg))


def main():
    ideal = json.loads((KIT / "voltas" / f"{VOLTA}_ideal.json").read_text(encoding="utf-8"))
    livre = json.loads((KIT / "voltas" / f"{VOLTA}_livre.json").read_text(encoding="utf-8"))
    par = PISTA.parametros(CIRCUITO)
    linha = LAT.Linha.de_ai(par["linha_ideal"])
    cv = {c["nome"]: c for c in LAT.curvas(linha) if "nome" in c}
    C = ideal["caminho"]
    P = np.c_[C["x"], C["z"]]
    kd = __import__("scipy.spatial", fromlist=["cKDTree"]).cKDTree(P)
    lat = ideal["lateral"]
    seg, T = [], 0.0
    dur = ideal["duracao"]
    seg.append(dict(tipo="mapa", T0=0.0, T1=INTRO + PANORAMA, t0=-0.5, t1=dur + 0.5, titulo=True,
                    rotulo="Volta inteira · acelerada"))
    # a panorâmica: os 4 s de título seguram o carro na largada; depois a volta em PANORAMA s
    seg[-1].update(segura=INTRO)
    T = INTRO + PANORAMA
    curvas_out = []
    for nome, membros in GRUPOS:
        ks = []
        for m in membros:
            ap = linha.ponto(cv[m]["s"])
            _, k = kd.query(ap)
            ks.append(int(k))
        ta, tb = tempo_em_s(ideal, ks[0] * C["ds"]), tempo_em_s(ideal, ks[-1] * C["ds"])
        t0, t1 = ta - ANTES, tb + DEPOIS
        # enquadramento: caminho percorrido na janela; "para cima" da tela = rumo médio entre entrada e saída
        s0, s1 = np.interp([t0, t1], ideal["relogio"]["t0"] + np.arange(len(ideal["relogio"]["s"])) * ideal["relogio"]["dt"],
                           ideal["relogio"]["s"])
        i0, i1 = int(s0 / C["ds"]), int(s1 / C["ds"]) + 1
        pts = P[i0:i1]
        d = pts[-1] - pts[0]
        if np.linalg.norm(d) < 30:  # grampo: entrada e saída quase no mesmo lugar -> rumo no ápice
            k = ks[0]
            d = P[min(k + 3, len(P) - 1)] - P[max(k - 3, 0)]
        d = d / np.linalg.norm(d)
        esq = np.array([d[1], -d[0]])
        u, w = (pts - pts.mean(0)) @ d, (pts - pts.mean(0)) @ esq
        centro = pts.mean(0) + d * (u.max() + u.min()) / 2 + esq * (w.max() + w.min()) / 2
        info = []
        for m, k in zip(membros, ks):
            info.append(dict(nome=m, t=round(tempo_em_s(ideal, k * C["ds"]), 3), borda_esq=lat["borda_esq"][k],
                             borda_dir=lat["borda_dir"][k], zebra=lat["zebra"][k], fora=lat["fora_asfalto"][k]))
        curvas_out.append(dict(nome=nome, apices=info))
        base = dict(nome=nome, t0=round(t0, 3), t1=round(t1, 3), centro=centro.round(2).tolist(), dir=d.round(4).tolist(),
                    ext=[round(float(u.max() - u.min()), 1), round(float(w.max() - w.min()), 1)], apices=info)
        f = 1.0 if (nome == "S do Senna" or t1 - t0 <= LONGO) else FATOR_LONGO
        seg.append(dict(base, tipo="cima", fator=f, T0=round(T, 3), T1=round(T + (t1 - t0) / f, 3)))
        T += (t1 - t0) / f
        if nome == "S do Senna":  # o mesmo trecho de novo, câmera seguindo o carro (1,5x)
            seg.append(dict(base, tipo="perseguicao", fator=FATOR_LONGO, T0=round(T, 3), T1=round(T + (t1 - t0) / FATOR_LONGO, 3)))
            T += (t1 - t0) / FATOR_LONGO
    cfg = dict(fps=FPS, duracao=round(T, 3), quadros=int(round(T * FPS)), segmentos=seg,
               pista=par["glb"]["visual"], carro="ferrari_sf26.glb", voltas=dict(ideal=f"{VOLTA}_ideal.json", livre=f"{VOLTA}_livre.json"),
               titulo=dict(piloto=ideal["nome"], sigla=ideal["sigla"], equipe=ideal["equipe"], cor=ideal["cor"],
                           sessao=f"{ideal['sessao_nome']} · GP de São Paulo {ideal['ano']}", volta=ideal["volta"], tempo=ideal["duracao"]))
    # ---- assets
    A = AQUI / "assets"
    A.mkdir(exist_ok=True)
    modelos = next(b / "F1" / "dados" / "modelos3d" for b in AQUI.parents if (b / "F1" / "dados" / "modelos3d").exists())
    for f in (cfg["pista"], cfg["carro"]):
        de, para = modelos / f, A / f
        if para.exists() and para.stat().st_size == de.stat().st_size and para.stat().st_mtime >= de.stat().st_mtime:
            continue
        if para.exists():
            para.unlink()
        try:
            os.link(de, para)
        except OSError:
            shutil.copy2(de, para)
    shutil.rmtree(A / "kit", ignore_errors=True)
    shutil.copytree(KIT / "src", A / "kit" / "gps" / "src")
    for v in cfg["voltas"].values():
        shutil.copy2(KIT / "voltas" / v, A / v)
    (A / "cfg.js").write_text("window.__CFG = " + json.dumps(cfg, ensure_ascii=False) + ";\n", encoding="utf-8")
    html = (AQUI / "index.html").read_text(encoding="utf-8")
    import re
    html2 = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{cfg["duracao"]}"', html)
    if html2 != html:
        (AQUI / "index.html").write_text(html2, encoding="utf-8")
    print(f"duração {T:.1f} s ({cfg['quadros']} quadros)")
    for s in seg:
        print(s["tipo"], s.get("nome", ""), s["T0"], s["T1"], "volta", s["t0"], s["t1"])
    for c in curvas_out:
        print(c)


if __name__ == "__main__":
    main()
