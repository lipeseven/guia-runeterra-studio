# Posição LATERAL do carro na pista (distância às bordas do asfalto, zebra sob o carro) e a medição honesta de quanto
# o GPS do OpenF1 diz sobre ela.
#
#  - bordas(pista, P, esq): para cada ponto do caminho (XZ) e a direção "esquerda" do carro, a distância (m) do centro
#    do carro até a borda esquerda/direita do ASFALTO (positivo = a borda está do lado indicado; negativo = o centro já
#    passou dela), a fração da largura do carro (2,0 m) fora do asfalto e se o carro cobre zebra. Raster de 0,2 m das
#    malhas 'asfalto' e 'zebra' de pista/<circuito>.json.
#  - Linha: traçado de referência (ex.: a linha ideal .ai de um mod do Assetto Corsa) com projeção s, d (d > 0 = esquerda).
#  - medir(...): o relatório de fidelidade lateral (testes/gps/<circuito>_lateral.json): espalhamento lateral entre
#    voltas/pilotos do OpenF1, linha do OpenF1 x linha ideal do mod, posição nas curvas principais.
#
# Uso: python lateral.py <circuito> <session_key> <piloto> [--pilotos 63 16 1 30 12 6 81]
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openf1  # noqa: E402
import pista as PISTA  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
RES = 0.2              # m/px do raster das superfícies
MEIA_LARGURA = 1.0     # m: carro de F1 tem 2,0 m de largura
ALCANCE = 30.0         # m de busca lateral de cada lado


def esquerda(tangente):
    """Direção 'esquerda' no plano XZ para a tangente (tx, tz) no sistema do modelo (three.js, Y para cima).
    Conferido no mod VHE: a borda que a linha .ai chama de esquerda fica neste lado (diferença mediana 1,1 m)."""
    t = np.asarray(tangente, float)
    t = t / np.linalg.norm(t, axis=-1, keepdims=True)
    return np.stack([t[..., 1], -t[..., 0]], -1)


class Raster:
    """Máscaras 0/1 de asfalto e zebra num raster de RES m (cv2.fillPoly dos triângulos projetados em XZ)."""

    def __init__(self, T_asf, T_zebra=None, res=RES):
        tudo = T_asf if T_zebra is None else np.concatenate([T_asf, T_zebra])
        self.lo = tudo[:, :, [0, 2]].reshape(-1, 2).min(0) - 40
        hi = tudo[:, :, [0, 2]].reshape(-1, 2).max(0) + 40
        self.r = res
        self.W, self.H = np.ceil((hi - self.lo) / res).astype(int)
        self.asf = self._m(T_asf)
        self.zeb = self._m(T_zebra) if T_zebra is not None else np.zeros_like(self.asf)

    def _m(self, T):
        m = np.zeros((self.H, self.W), np.uint8)
        cv2.fillPoly(m, [np.round((t - self.lo) / self.r).astype(np.int32) for t in T[:, :, [0, 2]]], 1)
        return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    def em(self, m, Q):
        ij = np.round((Q - self.lo) / self.r).astype(int)
        ok = (ij[..., 0] >= 0) & (ij[..., 0] < self.W) & (ij[..., 1] >= 0) & (ij[..., 1] < self.H)
        out = np.zeros(Q.shape[:-1], np.uint8)
        out[ok] = m[ij[..., 1][ok], ij[..., 0][ok]]
        return out


_rasters = {}


def raster(pista):
    k = (pista.circuito, pista.modo)
    if k not in _rasters:
        _rasters[k] = Raster(pista._T_asf, pista._T_zebra)
    return _rasters[k]


def bordas(pista, P, esq, meia=MEIA_LARGURA):
    """P (n, 2) XZ, esq (n, 2) unitário. Devolve dict de arrays (n,): borda_esq, borda_dir (m do centro até a borda do
    asfalto; o trecho de asfalto contínuo mais perto do centro), fora_asfalto (0..1 da largura do carro sem asfalto
    embaixo), zebra (0..1 da largura do carro sobre zebra)."""
    R = raster(pista)
    off = np.arange(-ALCANCE, ALCANCE + 1e-9, R.r / 2)
    i0 = int(np.argmin(np.abs(off)))
    be, bd = np.full(len(P), np.nan), np.full(len(P), np.nan)
    for a in range(0, len(P), 2000):
        Q = P[a:a + 2000, None, :] + off[None, :, None] * esq[a:a + 2000, None, :]
        A = R.em(R.asf, Q).astype(bool)
        for k in range(len(Q)):
            lin = A[k]
            if not lin.any():
                continue
            if lin[i0]:
                c = i0
            else:  # centro fora do asfalto: o trecho de asfalto mais perto
                idx = np.nonzero(lin)[0]
                c = idx[np.argmin(np.abs(idx - i0))]
            e = c
            while e + 1 < len(off) and lin[e + 1]:
                e += 1
            d = c
            while d - 1 >= 0 and lin[d - 1]:
                d -= 1
            be[a + k], bd[a + k] = off[e], -off[d]
    largura = np.linspace(-meia, meia, 21)
    Qc = P[:, None, :] + largura[None, :, None] * esq[:, None, :]
    fora = 1.0 - R.em(R.asf, Qc).mean(1)
    zeb = R.em(R.zeb, Qc).mean(1)
    return dict(borda_esq=be, borda_dir=bd, fora_asfalto=fora, zebra=zeb)


class Linha:
    """Linha de referência fechada (n, 2) com distância s; projeção de pontos (s, d) com d > 0 à esquerda."""

    def __init__(self, xz, s=None, extra=None):
        self.L = np.asarray(xz, float)
        self.s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.L, axis=0), axis=1))] if s is None else np.asarray(s, float)
        fecho = np.linalg.norm(self.L[0] - self.L[-1])
        self.comprimento = self.s[-1] + fecho
        tg = np.roll(self.L, -1, 0) - np.roll(self.L, 1, 0)
        self.esq = esquerda(tg)
        self.kd = cKDTree(self.L)
        self.extra = extra or {}

    @classmethod
    def de_ai(cls, caminho):
        import assetto
        d = assetto.ler_ai(caminho)
        return cls(d["pontos"][:, [0, 2]], d["s"], dict(y=d["pontos"][:, 1], lado_esq=d["lado_esq"],
                                                        lado_dir=d["lado_dir"], velocidade=d["velocidade"]))

    def projetar(self, q):
        q = np.asarray(q, float)
        _, j = self.kd.query(q)
        n = len(self.L)
        melhor_d2 = np.full(len(q), np.inf)
        s_out, d_out = np.zeros(len(q)), np.zeros(len(q))
        for jj in ((j - 1) % n, j):
            a, b = self.L[jj], self.L[(jj + 1) % n]
            ab = b - a
            t = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
            pp = a + ab * t[:, None]
            d2 = ((q - pp) ** 2).sum(1)
            m = d2 < melhor_d2
            s_out[m] = (self.s[jj] + t * np.linalg.norm(ab, axis=1))[m]
            e = self.esq[jj] * (1 - t[:, None]) + self.esq[(jj + 1) % n] * t[:, None]
            d_out[m] = np.einsum("ij,ij->i", q - pp, e)[m]
            melhor_d2 = np.minimum(melhor_d2, d2)
        return s_out, d_out

    def ponto(self, s, d=0.0):
        """XZ no arco s (com volta: s módulo comprimento) deslocado d m à esquerda."""
        s = np.mod(np.asarray(s, float), self.comprimento)
        ss = np.r_[self.s, self.comprimento]
        LL = np.r_[self.L, self.L[:1]]
        EE = np.r_[self.esq, self.esq[:1]]
        x = np.interp(s, ss, LL[:, 0]) + d * np.interp(s, ss, EE[:, 0])
        z = np.interp(s, ss, LL[:, 1]) + d * np.interp(s, ss, EE[:, 1])
        return np.stack([x, z], -1)


# ------------------------------------------------------------------------------------------------ curvas
# Curvas de Interlagos na ordem da volta (sentido anti-horário). Posição achada pela curvatura da linha ideal do mod
# (picos de |curvatura| em ordem), conferida pela direção (E/D) esperada de cada uma.
CURVAS_INTERLAGOS = [("S do Senna (1)", "E"), ("S do Senna (2)", "D"), ("Curva do Sol", "E"), ("Descida do Lago (4)", "E"),
                     ("Descida do Lago (5)", "E"), ("Ferradura (6)", "D"), ("Ferradura (7)", "D"), ("Laranja", "D"),
                     ("Pinheirinho", "E"), ("Bico de Pato", "D"), ("Mergulho (1)", "E"), ("Mergulho (2)", "E"),
                     ("Junção", "E"), ("Subida dos Boxes", "E")]


def curvas(linha, nomes=CURVAS_INTERLAGOS, raio_max=180.0):
    """Ápices (s, lado) das curvas: mínimos locais de raio < raio_max separados por > 90 m, na ordem da volta.
    Devolve [{nome, s, lado_curva ('E'|'D'), raio}] só se o número de ápices achados bater com 'nomes' (senão, sem nome)."""
    L = linha.L
    tg = np.gradient(L, axis=0)
    ang = np.unwrap(np.arctan2(tg[:, 1], tg[:, 0]))
    ds = np.gradient(linha.s)
    k = gaussian_filter1d(np.gradient(ang) / np.maximum(ds, 1e-6), 6, mode="wrap")
    raio = 1 / np.maximum(np.abs(k), 1e-6)
    cand = [i for i in range(1, len(L) - 1) if raio[i] < raio_max and raio[i] <= raio[i - 1] and raio[i] <= raio[i + 1]]
    cand.sort(key=lambda i: raio[i])
    esc = []
    for i in cand:
        if all(abs(linha.s[i] - linha.s[j]) > 90 for j in esc):
            esc.append(i)
    esc.sort(key=lambda i: linha.s[i])
    # sinal: curvatura > 0 com a esquerda (fz, -fx) = curva para a ESQUERDA? verificado abaixo pela 1ª curva (S do Senna
    # é à esquerda); o lado vem do sinal do produto vetorial tangente x d(tangente) no sistema do modelo
    out = []
    for n, i in enumerate(esc):
        t0, t1 = tg[i - 1], tg[i + 1]
        giro = np.dot(t1 - t0, linha.esq[i])  # > 0: a tangente gira para a esquerda
        out.append(dict(s=float(linha.s[i]), lado_curva="E" if giro > 0 else "D", raio=float(raio[i])))
    if len(out) == len(nomes):
        for c, (nome, lado) in zip(out, nomes):
            c["nome"], c["lado_esperado"] = nome, lado
    return out


# ------------------------------------------------------------------------------------------------ medição
def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def voltas_projetadas(pista, linha, sessao, pilotos, tol=1.07):
    """Projeção (t, s, d) de cada volta rápida (≤ tol × melhor da sessão) dos pilotos na linha de referência."""
    laps = [v for v in openf1.obter("laps", session_key=sessao)
            if v.get("lap_duration") and v.get("date_start") and not v.get("is_pit_out_lap")]
    melhor = min(v["lap_duration"] for v in laps)
    res = []
    for p in pilotos:
        L = openf1.localizacao(sessao, p)
        t = np.array([_ts(r["date"]) for r in L])
        xy = np.array([[r["x"], r["y"]] for r in L], float)
        for v in laps:
            if v["driver_number"] != p or v["lap_duration"] > melhor * tol:
                continue
            t0 = _ts(v["date_start"])
            sel = (t >= t0) & (t < t0 + v["lap_duration"]) & (np.abs(xy).sum(1) > 0)
            q = pista.aplicar(xy[sel])
            s, d = linha.projetar(q)
            res.append(dict(piloto=p, volta=v["lap_number"], duracao=v["lap_duration"], t=t[sel] - t0, s=s, d=d, xz=q))
    return res


def medir(circuito, sessao, piloto, outros, saida=None, passo=10.0):
    par = PISTA.parametros(circuito)
    pista = PISTA.carregar(circuito, modo="glb")
    linha = Linha.de_ai(par["linha_ideal"])
    V = voltas_projetadas(pista, linha, sessao, [piloto] + [p for p in outros if p != piloto])
    nb = int(linha.comprimento // passo) + 1
    M = np.full((len(V), nb), np.nan)
    for i, v in enumerate(V):
        b = (v["s"] // passo).astype(int)
        ok = np.abs(v["d"]) < 25
        for k in np.unique(b[ok]):
            M[i, k] = np.mean(v["d"][ok][b[ok] == k])
    med = np.nanmedian(M, 0)
    sb = np.arange(nb) * passo + passo / 2
    okb = ~np.isnan(med)
    med_i = np.interp(sb, sb[okb], med[okb])
    bruto = np.concatenate([v["d"] - np.interp(v["s"], sb, med_i) for v in V])
    bruto = bruto[np.abs(bruto) < 25]
    # bordas do asfalto pela malha, ao longo da linha ideal (centro = linha ideal; d = deslocamento para a esquerda)
    B = bordas(pista, linha.L, linha.esq)
    be, bd = np.interp(sb, linha.s, B["borda_esq"]), np.interp(sb, linha.s, B["borda_dir"])
    ham = [v for v in V if v["piloto"] == piloto]
    melhor = min(ham, key=lambda v: v["duracao"])
    # comparação por curva (no ápice da linha ideal, ±15 m)
    cv = []
    for c in curvas(linha):
        j = np.abs(((sb - c["s"] + linha.comprimento / 2) % linha.comprimento) - linha.comprimento / 2) <= 15
        jb = np.abs(((melhor["s"] - c["s"] + linha.comprimento / 2) % linha.comprimento) - linha.comprimento / 2) <= 15
        k = int(np.argmin(np.abs(linha.s - c["s"])))
        w = B["borda_esq"][k] + B["borda_dir"][k]
        item = dict(c, largura_asfalto_m=round(float(w), 1),
                    ideal=dict(borda_esq_m=round(float(B["borda_esq"][k]), 2), borda_dir_m=round(float(B["borda_dir"][k]), 2),
                               zebra=round(float(B["zebra"][k]), 2), fora_asfalto=round(float(B["fora_asfalto"][k]), 2)))
        if jb.any():
            d_h = float(np.mean(melhor["d"][jb]))
            item["openf1_melhor_volta"] = dict(desloc_vs_ideal_m=round(d_h, 2),
                                               borda_esq_m=round(float(B["borda_esq"][k] - d_h), 2),
                                               borda_dir_m=round(float(B["borda_dir"][k] + d_h), 2))
        if j.any():
            item["espalhamento_entre_voltas_m"] = round(float(np.nanmean(np.nanpercentile(M[:, j], 95, 0) - np.nanpercentile(M[:, j], 5, 0))), 2)
        cv.append(item)
    dev = np.abs(M - med)
    rel = dict(
        circuito=circuito, sessao=sessao, piloto=piloto, pilotos=sorted({v["piloto"] for v in V}), voltas=len(V),
        melhor_volta=dict(volta=melhor["volta"], duracao=melhor["duracao"], amostras=int(len(melhor["s"])),
                          intervalo_mediano_s=round(float(np.median(np.diff(melhor["t"]))), 3)),
        linha_ideal=dict(arquivo=Path(par["linha_ideal"]).name, comprimento_m=round(float(linha.comprimento), 1)),
        openf1_espalhamento=dict(
            nota="desvio lateral de cada volta (média por trecho de 10 m) em relação à mediana de TODAS as voltas/pilotos",
            volta_x_mediana_m=dict(p50=round(float(np.nanpercentile(dev, 50)), 3), p90=round(float(np.nanpercentile(dev, 90)), 3),
                                   p99=round(float(np.nanpercentile(dev, 99)), 3)),
            ponto_bruto_x_mediana_m=dict(p50=round(float(np.percentile(np.abs(bruto), 50)), 3),
                                         p90=round(float(np.percentile(np.abs(bruto), 90)), 3),
                                         p99=round(float(np.percentile(np.abs(bruto), 99)), 3))),
        openf1_x_linha_ideal_m=dict(p50=round(float(np.nanpercentile(np.abs(med), 50)), 2),
                                    p90=round(float(np.nanpercentile(np.abs(med), 90)), 2),
                                    max=round(float(np.nanmax(np.abs(med))), 2)),
        openf1_fora_do_asfalto=dict(
            nota="linha mediana do OpenF1 além da borda do asfalto (m), ao longo da volta",
            fracao=round(float(np.mean((med_i > be) | (med_i < -bd))), 3),
            max_m=round(float(np.max(np.maximum(med_i - be, -bd - med_i))), 2)),
        curvas=cv,
        perfil=dict(passo=passo, s=sb.round(1).tolist(), openf1_mediana=np.round(med, 3).tolist(),
                    melhor_volta=[None if np.isnan(x) else round(float(x), 3) for x in M[V.index(melhor)]],
                    borda_esq=np.round(be, 2).tolist(), borda_dir=np.round(bd, 2).tolist()),
    )
    saida = Path(saida) if saida else AQUI.parent.parent / "testes" / "gps" / f"{circuito}_lateral.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    return rel, saida


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="fidelidade lateral do GPS do OpenF1 contra a linha ideal de um mod")
    ap.add_argument("circuito"); ap.add_argument("sessao", type=int); ap.add_argument("piloto", type=int)
    ap.add_argument("--pilotos", type=int, nargs="*", default=[63, 16, 1, 30, 12, 6, 81])
    a = ap.parse_args()
    rel, arq = medir(a.circuito, a.sessao, a.piloto, a.pilotos)
    print(arq)
    print(json.dumps({k: rel[k] for k in ("voltas", "pilotos", "melhor_volta", "openf1_espalhamento", "openf1_x_linha_ideal_m",
                                           "openf1_fora_do_asfalto")}, ensure_ascii=False))
    for c in rel["curvas"]:
        print(c.get("nome", "?"), round(c["s"]), c["lado_curva"], c.get("lado_esperado"), round(c["raio"]), c["ideal"],
              c.get("openf1_melhor_volta"), c.get("espalhamento_entre_voltas_m"))
