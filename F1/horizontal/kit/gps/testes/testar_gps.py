# Teste automático do kit/gps. Amostra o gps.js (via Node, o mesmo código dos motores) a 60 q/s numa volta completa
# e prova: (1) monotonicidade de s(t); (2) nenhum salto acima do limite (posição, velocidade, rumo);
# (3) altura >= asfalto em TODOS os quadros (raio vertical na malha da pista); (4) cobertura: pose finita em todo o
# intervalo, inclusive além das margens (carro nunca some). Também roda o modo comparação (2,2x).
# Uso: python testar_gps.py [volta.json ...]   (padrão: todas em ../voltas/). Sai com código 1 se algo falhar.
# Relatório: F1/horizontal/testes/gps/relatorio_teste.json
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parent
sys.path.insert(0, str(KIT / "py"))
import pista as PISTA  # noqa: E402

SAIDA = KIT.parent.parent / "testes" / "gps"
FPS = 60
LIM_SALTO_M_POR_S = 100.0     # nenhum F1 passa de ~95 m/s: |Δpos| por quadro <= 100/60 m (x fator)
LIM_ACEL = 70.0               # m/s² (~7 g; frenagem de F1 chega a ~5–6 g)
LIM_YAW_RAD_S = 3.0           # rad/s (hairpin a 80 km/h, raio 15 m ≈ 1,5 rad/s)
LIM_EXCESSO_POS = 0.05        # m: |Δpos| x vel·dt (salto que a velocidade não explica)


def amostrar(volta, fator, t_ini=None, t_fim=None):
    tmp = SAIDA / f"_amostra_{volta.stem}_{fator}.json"
    cmd = ["node", str(AQUI / "amostrar.mjs"), str(volta), str(FPS), str(fator), str(tmp)]
    if t_ini is not None:
        cmd += [str(t_ini), str(t_fim)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    d = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.unlink()
    return d


def checar(d, chao, pilot):
    q = np.array(d["q"], float)
    t, s, x, y, z, yaw, pit, rol, v, com = q.T
    fator = d["fator"]
    dtq = 1.0 / FPS
    r = {}
    ok = True
    r["quadros"] = int(len(q))
    r["finitos"] = bool(np.isfinite(q).all())
    ok &= r["finitos"]
    # (1) monotonicidade: dentro do trecho com dados, s cresce sempre
    ds = np.diff(s)
    dentro = (com[1:] > 0) & (com[:-1] > 0)
    r["monotonico"] = bool((ds[dentro] > 0).all())
    r["ds_min_m"] = round(float(ds[dentro].min()), 5)
    r["recuos"] = int((ds < 0).sum())
    ok &= r["monotonico"] and r["recuos"] == 0
    # (2) saltos
    dp = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)
    lim = LIM_SALTO_M_POR_S * dtq * fator
    r["salto_max_m"] = round(float(dp.max()), 4)
    r["limite_salto_m"] = round(lim, 4)
    ok &= r["salto_max_m"] <= lim
    vm = (v[1:] + v[:-1]) / 2
    exc = np.abs(dp - vm * dtq * fator)
    r["excesso_pos_max_m"] = round(float(exc[dentro].max()), 4)
    ok &= r["excesso_pos_max_m"] <= LIM_EXCESSO_POS * fator
    acel = np.diff(v) / (dtq * fator)
    r["acel_max_ms2"] = round(float(np.abs(acel[dentro]).max()), 2)
    ok &= r["acel_max_ms2"] <= LIM_ACEL
    jerk = np.diff(acel) / (dtq * fator)
    r["jerk_p99_ms3"] = round(float(np.percentile(np.abs(jerk), 99)), 1)
    yr = np.abs(np.diff(yaw)) / (dtq * fator)
    r["yaw_max_rad_s"] = round(float(yr.max()), 3)
    ok &= r["yaw_max_rad_s"] <= LIM_YAW_RAD_S
    # (3) altura >= chão em todos os quadros (centro do carro) — raio vertical na malha
    folga = []
    sem_chao = 0
    for xi, yi, zi in zip(x, y, z):
        h = chao.altura(xi, zi, perto=yi, janela=1.5)
        if h is None:
            sem_chao += 1
            continue
        folga.append(yi - h)
    folga = np.array(folga)
    r["altura_folga_min_m"] = round(float(folga.min()), 4)
    r["altura_folga_max_m"] = round(float(folga.max()), 4)
    r["quadros_abaixo_do_chao"] = int((folga < 0).sum())
    r["quadros_sem_chao_medido"] = sem_chao
    ok &= r["quadros_abaixo_do_chao"] == 0 and sem_chao == 0
    # rodas (informativo): 4 contatos (±0,8 m lateral, +1,8/-1,8 m) com a pose; folga em relação ao chão
    fr = np.c_[np.sin(yaw) * np.cos(pit), np.sin(pit), np.cos(yaw) * np.cos(pit)]
    esq = np.c_[np.cos(yaw) * np.cos(rol), np.sin(rol), -np.sin(yaw) * np.cos(rol)]  # +X local (esquerda), com rolagem
    rodas = []
    for k in range(0, len(q), 3):
        for a, b in ((1.8, 0.8), (1.8, -0.8), (-1.8, 0.8), (-1.8, -0.8)):
            p = np.array([x[k], y[k], z[k]]) + fr[k] * a + esq[k] * b
            h = chao.altura(p[0], p[2], perto=p[1], janela=1.5)
            if h is not None:
                rodas.append(p[1] - h)
    rodas = np.array(rodas)
    r["rodas_folga_p01_m"] = round(float(np.percentile(rodas, 1)), 3)
    r["rodas_folga_min_m"] = round(float(rodas.min()), 3)
    # sobre asfalto/zebra (informativo)
    r["centro_sobre_asfalto_ou_zebra"] = round(float(np.mean([bool(pilot.alturas(a, b)) for a, b in zip(x, z)])), 4)
    r["ok"] = bool(ok)
    return r


def main():
    voltas = [Path(a) for a in sys.argv[1:]] or sorted((KIT / "voltas").glob("*.json"))
    SAIDA.mkdir(parents=True, exist_ok=True)
    rel = {"fps": FPS, "limites": dict(salto_m_por_s=LIM_SALTO_M_POR_S, acel_ms2=LIM_ACEL, yaw_rad_s=LIM_YAW_RAD_S,
                                       excesso_pos_m=LIM_EXCESSO_POS), "casos": []}
    tudo_ok = True
    for v in voltas:
        meta = json.loads(v.read_text(encoding="utf-8"))
        # a malha contra a qual a altura é medida é a da pista da própria volta (modelo 3D ou plana)
        # (voltas antigas, sem 'circuito'/'modo_pista', são de Interlagos com o modelo 3D)
        p = PISTA.carregar(meta.get("circuito", "Interlagos"), modo=meta.get("modo_pista", "glb"))
        chao, pilot = p.chao, p.pilot
        casos = [("volta completa 1x", 1.0, None, None),
                 ("comparação 2,2x", 2.2, None, None),
                 ("além das margens (-8 s a dur+8 s)", 1.0, -8.0, meta["duracao"] + 8.0)]
        for nome, fator, a, b in casos:
            d = amostrar(v, fator, a, b)
            r = checar(d, chao, pilot)
            r.update(volta=v.name, caso=nome, circuito=p.circuito, modo_pista=p.modo)
            rel["casos"].append(r)
            tudo_ok &= r["ok"]
            print(f"{'OK ' if r['ok'] else 'FALHOU'} {v.name:20s} {nome:34s} quadros={r['quadros']:5d} "
                  f"ds_min={r['ds_min_m']:.4f} salto={r['salto_max_m']:.3f}/{r['limite_salto_m']:.3f} "
                  f"acel={r['acel_max_ms2']:.1f} yaw={r['yaw_max_rad_s']:.2f} folga_min={r['altura_folga_min_m']:.3f} "
                  f"abaixo={r['quadros_abaixo_do_chao']} rodas_p01={r['rodas_folga_p01_m']:.3f}")
    rel["ok"] = bool(tudo_ok)
    (SAIDA / "relatorio_teste.json").write_text(json.dumps(rel, indent=1, ensure_ascii=False), encoding="utf-8")
    print("TUDO OK" if tudo_ok else "HÁ FALHAS")
    sys.exit(0 if tudo_ok else 1)


if __name__ == "__main__":
    main()
