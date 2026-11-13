# Alinha o sistema x,y do OpenF1 (decímetros) ao plano XZ do interlagos_sao_paulo.glb (metros, Y para cima).
# Método: similaridade 2D (escala, rotação, translação, com reflexão testada) por ICP contra o asfalto (material mesh2_7),
# usando as posições de várias voltas limpas. Grava pista/interlagos_alinhamento.json (pequeno, vai para o Git).
# Uso: python alinhar.py [session_key] [piloto ...]
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openf1  # noqa: E402
from pista_glb import Superficie  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent


def _achar_glb(nome="interlagos_sao_paulo.glb"):
    """F1/dados/modelos3d fica fora do Git: procura subindo as pastas (funciona também numa worktree)."""
    for base in AQUI.parents:
        c = base / "F1" / "dados" / "modelos3d" / nome
        if c.exists():
            return c
    raise FileNotFoundError(f"não achei F1/dados/modelos3d/{nome}")


GLB = _achar_glb()
MATERIAL_ASFALTO = "mesh2_7"


def carregar_pista():
    """Triângulos da pista (sub-árvore tracksplit_0), com cache em npz."""
    arq = AQUI / "cache" / "pista_tracksplit.npz"
    if not arq.exists():
        from pista_glb import triangulos
        T = triangulos(GLB, "tracksplit_0")
        arq.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(arq, **{str(k): v.astype(np.float32) for k, v in T.items()})
    z = np.load(arq)
    return {k: z[k].astype(float) for k in z.files}


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


def aplicar(al, xy):
    xy = np.asarray(xy, float) * np.array([1.0, -1.0 if al["refletir"] else 1.0])
    return al["escala"] * (np.array(al["R"]) @ xy.T).T + np.array(al["t"])


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


def alinhar(sessao=11412, pilotos=(16, 12)):
    T = carregar_pista()
    asf = T[MATERIAL_ASFALTO]
    alvo = np.concatenate([asf.mean(1), asf.reshape(-1, 3)])[:, [0, 2]]
    gps = np.concatenate([pontos_gps(sessao, p) for p in pilotos])
    melhor = None
    for refletir in (False, True):
        for ang in np.radians([0, 90, 180, 270]):
            al, med = icp(gps, alvo, refletir, ang)
            if melhor is None or med < melhor[1]:
                melhor = (al, med)
    al, med = melhor
    # quantos pontos GPS caem sobre o asfalto (raio vertical)
    sup = Superficie(asf)
    q = aplicar(al, gps)
    dentro = np.mean([bool(sup.alturas(x, z)) for x, z in q])
    al.update(
        fonte="interlagos_sao_paulo.glb (asfalto, material mesh2_7) alinhado ao OpenF1 por ICP de similaridade 2D",
        sessao_usada=sessao, pilotos_usados=list(pilotos),
        convencao="glb_x, glb_z = escala * R @ (x_openf1, ±y_openf1) + t   (x,y do OpenF1 em decímetros; refletir = inverter y antes)",
        erro_mediano_m=round(med, 3), fracao_sobre_asfalto=round(float(dentro), 4), n_pontos=int(len(gps)),
    )
    saida = AQUI / "pista" / "interlagos_alinhamento.json"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(json.dumps(al, indent=1, ensure_ascii=False), encoding="utf-8")
    return al


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 11412
    ps = tuple(int(p) for p in sys.argv[2:]) or (16, 12)
    al = alinhar(s, ps)
    print({k: al[k] for k in ("escala", "refletir", "erro_mediano_m", "fracao_sobre_asfalto", "n_pontos")})
