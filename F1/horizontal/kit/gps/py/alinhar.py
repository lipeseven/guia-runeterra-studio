# Alinhador genérico: x,y do OpenF1 (decímetros) -> plano XZ do .glb de QUALQUER circuito (metros, Y para cima).
# Método: similaridade 2D (escala, rotação, translação, com reflexão testada) por ICP contra o asfalto do modelo,
# usando as posições de várias voltas limpas. Parâmetros do modelo (arquivo, nó, material do asfalto) e o resultado
# ficam em pista/<circuito>.json (pequeno, vai para o Git). <circuito> = circuit_short_name do OpenF1.
# Uso: python alinhar.py <circuito> <session_key> <piloto> [<piloto> ...]
#      (circuito novo: crie antes pista/<circuito>.json com o bloco "glb", como em pista/Interlagos.json)
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openf1  # noqa: E402
import pista as P  # noqa: E402
from pista import aplicar  # noqa: E402,F401  (reexportado: alinhar.aplicar continua valendo)
from pista_glb import Superficie  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def pontos_gps(sessao, piloto, n_voltas=6):
    """x,y (dm) das voltas mais rápidas e limpas (sem saída de box)."""
    V = [v for v in openf1.voltas(sessao, piloto) if v.get("lap_duration") and not v.get("is_pit_out_lap")]
    V = sorted(V, key=lambda v: v["lap_duration"])[:n_voltas]
    L = openf1.localizacao(sessao, piloto)
    t = np.array([_ts(r["date"]) for r in L])
    xy = np.array([[r["x"], r["y"]] for r in L], float)
    sel = np.zeros(len(L), bool)
    for v in V:
        t0 = _ts(v["date_start"])
        sel |= (t >= t0) & (t <= t0 + v["lap_duration"])
    return xy[sel]


def umeyama(a, b, refletir):
    """s, R tal que b ≈ s R a' + t, com a' = a com y invertido se refletir."""
    a = a * np.array([1.0, -1.0 if refletir else 1.0])
    ma, mb = a.mean(0), b.mean(0)
    A, B = a - ma, b - mb
    U, S, Vt = np.linalg.svd(B.T @ A / len(a))
    D = np.eye(2)
    if np.linalg.det(U @ Vt) < 0:
        D[1, 1] = -1
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (A ** 2).sum(1).mean()
    return s, R, mb - s * R @ ma


def icp(gps, alvo, refletir, ang0):
    kd = cKDTree(alvo)
    c = np.array([[np.cos(ang0), -np.sin(ang0)], [np.sin(ang0), np.cos(ang0)]])
    g = gps * np.array([1.0, -1.0 if refletir else 1.0])
    s = np.sqrt(np.ptp(alvo, 0).prod() / max(np.ptp((c @ g.T).T, 0).prod(), 1e-9))
    R = c
    t = alvo.mean(0) - s * (R @ g.mean(0))
    al = None
    for it in range(80):
        al = dict(escala=float(s), R=R.tolist(), t=t.tolist(), refletir=refletir)
        q = aplicar(al, gps)
        d, j = kd.query(q)
        lim = np.percentile(d, 90 if it > 10 else 100)
        ok = d <= lim
        s, R, t = umeyama(gps[ok], alvo[j[ok]], refletir)
    al = dict(escala=float(s), R=R.tolist(), t=t.tolist(), refletir=refletir)
    d, _ = kd.query(aplicar(al, gps))
    return al, float(np.median(d))


def alinhar(circuito, sessao, pilotos, gravar=True):
    par = P.parametros(circuito)
    if not par.get("glb"):
        raise ValueError(f"pista/{circuito}.json sem bloco 'glb' (arquivo, no, asfalto, pilotavel, fundo)")
    T = P.triangulos_glb(circuito)
    asf = T[par["glb"]["asfalto"]]
    alvo = np.concatenate([asf.mean(1), asf.reshape(-1, 3)])[:, [0, 2]]
    gps = np.concatenate([pontos_gps(sessao, p) for p in pilotos])
    melhor = None
    for refletir in (False, True):
        for ang in np.radians([0, 90, 180, 270]):
            al, med = icp(gps, alvo, refletir, ang)
            if melhor is None or med < melhor[1]:
                melhor = (al, med)
    al, med = melhor
    sup = Superficie(asf)  # quantos pontos GPS caem sobre o asfalto (raio vertical)
    q = aplicar(al, gps)
    dentro = np.mean([bool(sup.alturas(x, z)) for x, z in q])
    al.update(
        fonte=f"{par['glb']['arquivo']} (asfalto, material {par['glb']['asfalto']}) alinhado ao OpenF1 por ICP de similaridade 2D",
        sessao_usada=sessao, pilotos_usados=list(pilotos),
        convencao="glb_x, glb_z = escala * R @ (x_openf1, ±y_openf1) + t   (x,y do OpenF1 em decímetros; refletir = inverter y antes)",
        erro_mediano_m=round(med, 3), fracao_sobre_asfalto=round(float(dentro), 4), n_pontos=int(len(gps)),
    )
    if gravar:
        par["alinhamento"] = al
        (P.PASTA / f"{circuito}.json").write_text(json.dumps(par, indent=1, ensure_ascii=False), encoding="utf-8")
    return al


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("uso: python alinhar.py <circuito> <session_key> <piloto> [<piloto> ...]")
        sys.exit(1)
    al = alinhar(sys.argv[1], int(sys.argv[2]), tuple(int(p) for p in sys.argv[3:]))
    print({k: al[k] for k in ("escala", "refletir", "erro_mediano_m", "fracao_sobre_asfalto", "n_pontos")})
