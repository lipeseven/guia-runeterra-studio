# A pista de QUALQUER circuito para o kit/gps, em dois modos com a mesma interface:
#  "glb"   — modelo 3D (F1/dados/modelos3d/<arquivo>, fora do Git) alinhado ao OpenF1. Parâmetros por circuito em
#            pista/<circuito>.json ("glb": arquivo, nó, materiais; "alinhamento": saída do alinhar.py).
#  "plana" — sem modelo 3D: o traçado é tirado do próprio /v1/location do OpenF1 (voltas rápidas de vários pilotos),
#            superfície plana (y = 0) com largura estimada pelo espalhamento lateral do GPS. Gravado em
#            pista/<circuito>_plana.json (vai para o Git; o adaptador three.js desenha a pista a partir dele).
# <circuito> = circuit_short_name do OpenF1 (ex.: "Interlagos", "Monza").
#
# Interface: p = carregar(circuito, sessao=..., modo=None|"glb"|"plana")
#   p.aplicar(xy_openf1_dm) -> XZ (m) no sistema da pista; p.chao / p.asf / p.pilot (Superficie: altura por raio
#   vertical); p.mascara (área pilotável, para puxar o centro do carro de volta); p.render (o que o motor carrega).
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scipy.interpolate import splev, splprep
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

import openf1
from pista_glb import Superficie, triangulos

AQUI = Path(__file__).resolve().parent.parent
PASTA = AQUI / "pista"

# modo plano
DS_CENTRO = 2.0          # m entre pontos da linha central gravada
LARGURA_MIN, LARGURA_MAX = 12.0, 16.0   # m: 12 = mínimo da FIA para pista nova; a estimativa é presa nesta faixa
ZEBRA = 1.0              # m de zebra de cada lado (área pilotável = asfalto + zebra)
ESCAPE = 8.0             # m de chão (área de escape) de cada lado, para a altura nunca faltar
N_PILOTOS_PLANA = 6      # pilotos usados para traçar a pista plana (os das voltas mais rápidas)
TOL_VOLTA_RAPIDA = 1.07  # volta "rápida" = até 107% da melhor da sessão (fora: volta lenta, de saída/entrada)


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def _achar_glb(nome):
    """F1/dados/modelos3d fica fora do Git: procura subindo as pastas (funciona também numa worktree)."""
    for base in AQUI.parents:
        c = base / "F1" / "dados" / "modelos3d" / nome
        if c.exists():
            return c
    return None


def aplicar(al, xy):
    """x,y do OpenF1 (dm) -> XZ (m) pela similaridade 2D gravada (escala, R, t, refletir)."""
    xy = np.asarray(xy, float) * np.array([1.0, -1.0 if al["refletir"] else 1.0])
    return al["escala"] * (np.array(al["R"]) @ xy.T).T + np.array(al["t"])


def parametros(circuito):
    arq = PASTA / f"{circuito}.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


def tem_modelo(circuito):
    g = parametros(circuito).get("glb")
    return bool(g and _achar_glb(g["arquivo"]))


def triangulos_glb(circuito):
    """Triângulos do .glb do circuito (sub-árvore g['no'] se houver), com cache em npz."""
    g = parametros(circuito)["glb"]
    glb = _achar_glb(g["arquivo"])
    if glb is None:
        raise FileNotFoundError(f"não achei F1/dados/modelos3d/{g['arquivo']}")
    arq = AQUI / "cache" / f"pista_{Path(g['arquivo']).stem}_{g.get('no') or 'tudo'}.npz"
    if not arq.exists():
        T = triangulos(glb, g.get("no"))
        arq.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(arq, **{str(k): v.astype(np.float32) for k, v in T.items()})
    z = np.load(arq)
    return {k: z[k].astype(float) for k in z.files}


def _mascara(tri_pilotavel):
    """Máscara pilotável (0,25 m/px) + transformadas de distância para puxar pontos de fora para dentro."""
    tri = tri_pilotavel[:, :, [0, 2]]
    lo = tri.reshape(-1, 2).min(0) - 20
    hi = tri.reshape(-1, 2).max(0) + 20
    r = 0.25
    W, H = (np.ceil((hi - lo) / r)).astype(int)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round((t - lo) / r).astype(np.int32) for t in tri], 1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))  # fecha frestas entre triângulos
    dist, lab = cv2.distanceTransformWithLabels(1 - m, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(m == 1)
    lab_xy = np.zeros((lab.max() + 1, 2))
    lab_xy[lab[zy, zx]] = np.c_[zx, zy]
    dentro = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    return dict(lo=lo, r=r, m=m, dist=dist, lab=lab, lab_xy=lab_xy, dentro=dentro)


class Pista:
    def __init__(self, circuito, modo, al, T_chao, T_asf, T_pilot, render, info):
        self.circuito, self.modo, self.al, self.render, self.info = circuito, modo, al, render, info
        self.chao = Superficie(T_chao)
        self.asf = Superficie(T_asf)
        self.pilot = Superficie(T_pilot)
        self._T_pilot = T_pilot
        self._mask = None

    def aplicar(self, xy):
        return aplicar(self.al, xy)

    @property
    def mascara(self):
        if self._mask is None:
            self._mask = _mascara(self._T_pilot)
        return self._mask


# ------------------------------------------------------------------------------------------------ modo GLB
def _carregar_glb(circuito):
    p = parametros(circuito)
    g, al = p["glb"], p.get("alinhamento")
    if not al:
        raise ValueError(f"pista/{circuito}.json sem 'alinhamento': rode py/alinhar.py {circuito} <sessao> <pilotos>")
    T = triangulos_glb(circuito)
    fundo = set(g.get("fundo", []))
    chao = np.concatenate([v for k, v in T.items() if k not in fundo])
    pil = np.concatenate([T[k] for k in g["pilotavel"]])
    return Pista(circuito, "glb", al, chao, T[g["asfalto"]], pil, g["arquivo"],
                 dict(arquivo=g["arquivo"], erro_mediano_m=al.get("erro_mediano_m")))


# ------------------------------------------------------------------------------------------------ modo plano
def _fita(c, largura, fechada=True):
    """Triângulos (n, 3, 3) de uma fita plana (y = 0) de 'largura' m em torno da linha central c (n, 2)."""
    cc = np.r_[c, c[:1]] if fechada else c
    tg = np.gradient(cc, axis=0)
    if fechada:
        tg[0] = tg[-1] = cc[1] - cc[-2]
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    nr = np.c_[-tg[:, 1], tg[:, 0]]
    e, d = cc + nr * largura / 2, cc - nr * largura / 2
    E = np.c_[e[:, 0], np.zeros(len(e)), e[:, 1]]
    D = np.c_[d[:, 0], np.zeros(len(d)), d[:, 1]]
    t1 = np.stack([E[:-1], D[:-1], E[1:]], 1)
    t2 = np.stack([D[:-1], D[1:], E[1:]], 1)
    return np.concatenate([t1, t2])


def _voltas_rapidas(sessao):
    V = [v for v in openf1.obter("laps", session_key=sessao)
         if v.get("lap_duration") and v.get("date_start") and not v.get("is_pit_out_lap")]
    melhor = min(v["lap_duration"] for v in V)
    return sorted([v for v in V if v["lap_duration"] <= melhor * TOL_VOLTA_RAPIDA], key=lambda v: v["lap_duration"])


def _pontos_volta(L, t, v):
    t0 = _ts(v["date_start"])
    sel = (t >= t0) & (t < t0 + v["lap_duration"])
    return L[sel]


def tracar_plana(circuito, sessao, pilotos=None, destino=None):
    """Traça a pista pelo GPS do OpenF1 e grava pista/<circuito>_plana.json (ou 'destino'). Devolve o dicionário."""
    rapidas = _voltas_rapidas(sessao)
    if pilotos is None:
        pilotos = []
        for v in rapidas:
            if v["driver_number"] not in pilotos:
                pilotos.append(v["driver_number"])
            if len(pilotos) >= N_PILOTOS_PLANA:
                break
    por_piloto = {}
    for p in pilotos:
        L = openf1.localizacao(sessao, p)
        t = np.array([_ts(r["date"]) for r in L])
        xy = np.array([[r["x"], r["y"]] for r in L], float) / 10.0   # dm -> m
        por_piloto[p] = (t, xy)
    # referência: a volta mais rápida entre os pilotos escolhidos
    ref = next(v for v in rapidas if v["driver_number"] in por_piloto)
    t, xy = por_piloto[ref["driver_number"]]
    r = _pontos_volta(xy, t, ref)
    r = r[np.r_[True, np.linalg.norm(np.diff(r, axis=0), axis=1) > 0.3]]
    tck, _ = splprep([r[:, 0], r[:, 1]], s=len(r) * 1.0 ** 2, per=1)
    uf = np.linspace(0, 1, 20000, endpoint=False)
    pf = np.array(splev(uf, tck)).T
    # todas as voltas rápidas dos pilotos escolhidos (o traçado de cada um cobre um lado da pista)
    todos = np.concatenate([_pontos_volta(xy, t, v) for v in rapidas if v["driver_number"] in por_piloto
                            for t, xy in [por_piloto[v["driver_number"]]]])
    n_voltas = sum(1 for v in rapidas if v["driver_number"] in por_piloto)

    def reamostrar(p):
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[p, p[:1]], axis=0), axis=1))]
        S = np.arange(0, s[-1], DS_CENTRO)
        pp = np.r_[p, p[:1]]
        return np.c_[np.interp(S, s, pp[:, 0]), np.interp(S, s, pp[:, 1])], s[-1]

    c, comp = reamostrar(pf)
    for _ in range(3):  # a linha central vai para a mediana lateral de todas as passagens
        tg = np.roll(c, -1, 0) - np.roll(c, 1, 0)
        tg /= np.linalg.norm(tg, axis=1, keepdims=True)
        nr = np.c_[-tg[:, 1], tg[:, 0]]
        d, j = cKDTree(c).query(todos)
        off = np.einsum("ij,ij->i", todos - c[j], nr[j])
        ok = np.abs(off) < 25          # fora disso: entrada/saída de box ou erro do GPS
        med = np.zeros(len(c))
        # mediana por ponto (janela de ±3 pontos = ±6 m), robusta
        ordem = np.argsort(j[ok])
        jj, oo = j[ok][ordem], off[ok][ordem]
        ini = np.searchsorted(jj, np.arange(len(c)))
        fim = np.searchsorted(jj, np.arange(len(c)), side="right")
        for k in range(len(c)):
            vals = np.concatenate([oo[ini[(k + q) % len(c)]:fim[(k + q) % len(c)]] for q in range(-3, 4)])
            med[k] = np.median(vals) if len(vals) >= 3 else 0.0
        med = gaussian_filter1d(med, 4, mode="wrap")
        c, comp = reamostrar(c + nr * med[:, None])
    # largura: espalhamento lateral (p1..p99) das passagens em cada trecho de ~40 m, presa a [MIN, MAX]
    tg = np.roll(c, -1, 0) - np.roll(c, 1, 0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    nr = np.c_[-tg[:, 1], tg[:, 0]]
    d, j = cKDTree(c).query(todos)
    off = np.einsum("ij,ij->i", todos - c[j], nr[j])
    ok = np.abs(off) < 25
    blocos = (j[ok] * DS_CENTRO // 40).astype(int)
    esp = []
    for b in np.unique(blocos):
        o = off[ok][blocos == b]
        if len(o) >= 20:
            esp.append(np.percentile(o, 99) - np.percentile(o, 1))
    esp = np.array(esp)
    # +1 m: o centro do carro fica ~1 m dentro da borda. Medido em Monza/Interlagos: espalhamento ~0,1–0,2 m (o GPS do
    # OpenF1 parece projetado numa linha de referência), então a largura cai no mínimo da faixa (LARGURA_MIN).
    bruta = float(np.percentile(esp, 90)) + 1.0
    largura = float(np.clip(bruta, LARGURA_MIN, LARGURA_MAX))
    dentro = float(np.mean(np.abs(off[ok]) <= largura / 2 + ZEBRA))
    # sistema de coordenadas da pista plana: x = leste, z = -norte (vista de cima sem espelhar), origem no centro
    cx, cy = (c.min(0) + c.max(0)) / 2
    al = dict(escala=0.1, R=[[1.0, 0.0], [0.0, 1.0]], t=[float(-cx), float(cy)], refletir=True)
    cen = np.c_[c[:, 0] - cx, -(c[:, 1] - cy)]
    info = openf1.sessao_info(sessao)
    out = dict(
        circuito=circuito, modo="plana",
        fonte=f"traçado pelo OpenF1 /v1/location: {n_voltas} voltas rápidas (≤ {TOL_VOLTA_RAPIDA:.0%} da melhor) de "
              f"{len(por_piloto)} pilotos, {info.get('year')} {info.get('session_name')} (session_key {sessao})",
        sessao_usada=sessao, pilotos_usados=[int(p) for p in por_piloto],
        convencao="x, z = escala * R @ (x_openf1, -y_openf1) + t  (x,y do OpenF1 em dm; x = leste, z = -norte, m); y = 0",
        alinhamento=al,
        largura_m=round(largura, 2), largura_bruta_m=round(bruta, 2),
        largura_metodo="p90 do espalhamento lateral (p1–p99) das passagens por trecho de 40 m, +1 m, presa a "
                       f"[{LARGURA_MIN:g}, {LARGURA_MAX:g}] m",
        zebra_m=ZEBRA, escape_m=ESCAPE,
        comprimento_m=round(float(comp), 1),
        qualidade=dict(pontos_gps=int(ok.sum()), fracao_dentro_asfalto_mais_zebra=round(dentro, 4),
                       desvio_lateral_p50_m=round(float(np.median(np.abs(off[ok]))), 2)),
        centro=dict(ds=DS_CENTRO, fechada=True, x=np.round(cen[:, 0], 3).tolist(), z=np.round(cen[:, 1], 3).tolist()),
    )
    destino = Path(destino) if destino else PASTA / f"{circuito}_plana.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def _carregar_plana(circuito, sessao=None):
    arq = PASTA / f"{circuito}_plana.json"
    if not arq.exists():
        if sessao is None:
            raise FileNotFoundError(f"não há pista/{arq.name}: passe a sessão para traçar a pista pelo GPS")
        tracar_plana(circuito, sessao)
    d = json.loads(arq.read_text(encoding="utf-8"))
    c = np.c_[d["centro"]["x"], d["centro"]["z"]]
    w = d["largura_m"]
    asf = _fita(c, w)
    pil = _fita(c, w + 2 * d["zebra_m"])
    chao = _fita(c, w + 2 * d["escape_m"])
    return Pista(circuito, "plana", d["alinhamento"], chao, asf, pil, arq.name,
                 dict(arquivo=arq.name, largura_m=w, comprimento_m=d["comprimento_m"]))


_cache = {}


def carregar(circuito, sessao=None, modo=None):
    """modo None = 'glb' se o circuito tem modelo 3D alinhado e o arquivo existe; senão 'plana'."""
    if modo is None:
        modo = "glb" if tem_modelo(circuito) and parametros(circuito).get("alinhamento") else "plana"
    k = (circuito, modo)
    if k not in _cache:
        _cache[k] = _carregar_glb(circuito) if modo == "glb" else _carregar_plana(circuito, sessao)
    return _cache[k]
