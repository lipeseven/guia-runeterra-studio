# Prepara UMA volta do OpenF1 para o kit/gps: caminho 3D apoiado na pista + relógio s(t) monotônico.
# Saída: kit/gps/voltas/<sessao>_<piloto>_<volta>.json (lido por src/gps.js em qualquer motor).
#
# Passos (cada um resolve um defeito visto nos testes de motor):
#  1. GPS bruto (~3,7 Hz) da volta + margem de 4 s antes/depois (o carro nunca "acaba" no meio da cena);
#     remove amostras repetidas/paradas com o carro andando (causa de tranco/vai-e-vem).
#  2. x,y OpenF1 -> XZ do .glb pelo alinhamento (pista/interlagos_alinhamento.json).
#  3. Caminho geométrico: spline cúbica suavizada parametrizada pela corda (sem deslocamento lateral artificial:
#     é o traçado real do piloto); se o centro do carro sair da área pilotável (asfalto + zebra), é puxado de volta.
#  4. Relógio s(t): distância acumulada ao longo do caminho; suavização + reforço de monotonicidade (s sempre cresce)
#     -> nunca anda para trás. O JS interpola com cúbica monotônica (Fritsch–Carlson).
#  5. Altura: raio vertical na malha da pista a cada 1 m e nos pontos médios (interpolação linear nunca fura o chão);
#     inclinação (pitch) e rolagem (roll) medidas no asfalto; rumo (yaw) pela tangente suavizada.
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator, UnivariateSpline, splev, splprep
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openf1  # noqa: E402
from alinhar import aplicar, carregar_pista  # noqa: E402
from pista_glb import Superficie  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
PILOTAVEL = ("mesh2_7", "mesh2_8")            # asfalto e zebras
# superfícies para a altura: tudo da sub-árvore tracksplit_0 (asfalto, zebras, faixas pintadas, grama, escape),
# menos o terreno de fundo (mesh2, mesh2_0), que se estende por km e pode cruzar a pista.
FUNDO = ("mesh2", "mesh2_0")
MARGEM_S = 4.0       # segundos de GPS antes e depois da volta
DS = 1.0             # passo do caminho (m)
DT_RELOGIO = 0.05    # passo da tabela s(t) (s)
FOLGA_Y = 0.02       # carro 2 cm acima do asfalto medido
MEIA_BITOLA = 0.8    # m, para medir a rolagem
SIGMA_AO_LONGO = 3.0  # m, ruído do GPS ao longo da pista tolerado pela correção lenta do relógio
CORES = json.loads((AQUI / "cores.json").read_text(encoding="utf-8"))

_cache = {}


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def _pista():
    if "T" not in _cache:
        T = carregar_pista()
        _cache["T"] = T
        _cache["chao"] = Superficie(np.concatenate([v for k, v in T.items() if k not in FUNDO]))
        _cache["asf"] = Superficie(T["mesh2_7"])
        # máscara pilotável (0,25 m/px) para manter o centro do carro sobre asfalto/zebra
        tri = np.concatenate([T[k] for k in PILOTAVEL])[:, :, [0, 2]]
        lo = tri.reshape(-1, 2).min(0) - 20
        hi = tri.reshape(-1, 2).max(0) + 20
        r = 0.25
        W, H = (np.ceil((hi - lo) / r)).astype(int)
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [np.round((t - lo) / r).astype(np.int32) for t in tri], 1)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))  # fecha frestas entre triângulos
        dist, lab = cv2.distanceTransformWithLabels(1 - m, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        zy, zx = np.nonzero(m == 1)
        # rótulo -> coordenada do pixel pilotável mais próximo
        lab_xy = np.zeros((lab.max() + 1, 2))
        lab_xy[lab[zy, zx]] = np.c_[zx, zy]
        # distância até a borda por dentro (para saber quão dentro está)
        dentro = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        _cache["mask"] = dict(lo=lo, r=r, m=m, dist=dist, lab=lab, lab_xy=lab_xy, dentro=dentro)
    return _cache


def _puxar_para_pista(P, margem=0.6):
    """Desloca pontos fora da área pilotável até ficarem 'margem' m para dentro. Devolve (P2, correção em m)."""
    M = _pista()["mask"]
    ij = np.round((P - M["lo"]) / M["r"]).astype(int)
    ij[:, 0] = ij[:, 0].clip(0, M["m"].shape[1] - 1)
    ij[:, 1] = ij[:, 1].clip(0, M["m"].shape[0] - 1)
    corr = np.zeros_like(P)
    dentro = M["dentro"][ij[:, 1], ij[:, 0]] * M["r"]
    for k in range(len(P)):
        if M["m"][ij[k, 1], ij[k, 0]] == 0:
            alvo = M["lab_xy"][M["lab"][ij[k, 1], ij[k, 0]]] * M["r"] + M["lo"]
            v = alvo - P[k]
            n = np.linalg.norm(v) or 1.0
            corr[k] = v + v / n * margem
        elif dentro[k] < margem:
            pass  # sobre a zebra/asfalto perto da borda: aceito (traçado real)
    return corr


def _dedup(t, xy, vel):
    """Remove amostras quase simultâneas e posições repetidas com o carro andando."""
    ok = [0]
    for i in range(1, len(t)):
        j = ok[-1]
        if t[i] - t[j] < 0.06:
            continue
        passo = np.linalg.norm(xy[i] - xy[j])
        if passo < 0.05 and vel[i] > 20:  # GPS repetido (congelado) com o carro a >20 km/h
            continue
        ok.append(i)
    return np.array(ok)


def preparar(sessao, piloto, volta, saida=None):
    al = json.loads((AQUI / "pista" / "interlagos_alinhamento.json").read_text(encoding="utf-8"))
    lap = next(v for v in openf1.voltas(sessao, piloto) if v["lap_number"] == volta)
    t0 = _ts(lap["date_start"])
    dur = float(lap["lap_duration"])
    L = openf1.localizacao(sessao, piloto)
    tl = np.array([_ts(r["date"]) - t0 for r in L])
    sel = (tl >= -MARGEM_S - 1) & (tl <= dur + MARGEM_S + 1)
    tl = tl[sel]
    raw = np.array([[r["x"], r["y"]] for r in L], float)[sel]
    car = openf1.obter("car_data", session_key=sessao, driver_number=piloto)
    tc = np.array([_ts(r["date"]) - t0 for r in car])
    vc = np.array([r["speed"] for r in car], float)
    vel_gps = np.interp(tl, tc, vc)
    keep = _dedup(tl, raw, vel_gps)
    tl, raw = tl[keep], raw[keep]
    xz = aplicar(al, raw)
    buracos = [[round(float(a), 3), round(float(b), 3)] for a, b in zip(tl[:-1], tl[1:]) if b - a > 0.6]

    # --- 3. caminho geométrico (spline suavizada; corda como parâmetro)
    u = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])
    sig = 0.45  # m, ruído típico do GPS após alinhamento
    tck, _ = splprep([xz[:, 0], xz[:, 1]], u=u, s=len(u) * sig ** 2, k=3)
    uf = np.linspace(0, u[-1], int(u[-1] / 0.1))
    pf = np.array(splev(uf, tck)).T
    sf = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pf, axis=0), axis=1))])
    S = np.arange(0, sf[-1], DS)
    P = np.c_[np.interp(S, sf, pf[:, 0]), np.interp(S, sf, pf[:, 1])]
    # mantém o centro sobre asfalto/zebra; correção suavizada para não criar quina
    corr = _puxar_para_pista(P)
    corr = np.c_[gaussian_filter1d(corr[:, 0], 3, mode="nearest"), gaussian_filter1d(corr[:, 1], 3, mode="nearest")]
    corr_mag = np.linalg.norm(corr, axis=1)
    P = P + corr
    S_orig = S
    # reamostra em passo exato de DS após a correção
    sp = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    S = np.arange(0, sp[-1], DS)
    P = np.c_[np.interp(S, sp, P[:, 0]), np.interp(S, sp, P[:, 1])]

    # --- 4. relógio s(t): posição de cada amostra GPS ao longo do caminho
    # arco da spline no parâmetro de cada amostra (monotônico), levado ao caminho corrigido
    s_gps = np.interp(np.interp(u, uf, sf), S_orig, sp)
    # O carimbo de tempo do GPS tem ruído de ~2 m ao longo da pista (velocidade derivada dele erra ~28 km/h em média):
    # interpolar direto nele dá o tranco/vai-e-vem dos testes. Por isso o relógio é a VELOCIDADE da telemetria
    # (car_data, sensor limpo) integrada, ancorada às posições do GPS por uma correção lenta (spline bem suavizada).
    tg = np.arange(math.floor((tl[0]) / DT_RELOGIO) * DT_RELOGIO, tl[-1] + 1e-9, DT_RELOGIO)
    jan = (tc >= tg[0] - 3) & (tc <= tg[-1] + 3)
    tcj, vcj = tc[jan], vc[jan] / 3.6
    okc = np.concatenate([[True], np.diff(tcj) > 1e-3])
    tf = np.arange(tg[0], tg[-1] + 1e-9, 0.01)
    # suavização leve (σ = 0,1 s): a velocidade vem em km/h inteiros a ~4 Hz; evita pico de desaceleração irreal
    vf = gaussian_filter1d(PchipInterpolator(tcj[okc], vcj[okc])(tf), 10, mode="nearest")
    s_tel = np.concatenate([[0], np.cumsum((vf[1:] + vf[:-1]) / 2 * 0.01)])
    resid = s_gps - np.interp(tl, tf, s_tel)
    # spline robusta (pesos de Huber): o GPS tem desvios isolados de 10–15 m ao longo da pista
    w = np.ones(len(tl))
    for _ in range(4):
        corr_s = UnivariateSpline(tl, resid, w=w, k=3, s=w.sum() * SIGMA_AO_LONGO ** 2)
        w = 1.0 / np.maximum(1.0, np.abs(resid - corr_s(tl)) / (1.5 * SIGMA_AO_LONGO))
    sg = np.interp(tg, tf, s_tel) + corr_s(tg)
    erro_gps_ao_longo = s_gps - np.interp(tl, tg, sg)
    # monotonicidade estrita: velocidade mínima de 1 m/s (carro de F1 em volta rápida nunca para)
    vmin = 1.0 * DT_RELOGIO
    for i in range(1, len(sg)):
        if sg[i] < sg[i - 1] + vmin:
            sg[i] = sg[i - 1] + vmin
    # recorta o relógio ao trecho em que s cai dentro do caminho, deixando 0,5 s de folga nas pontas
    # (a correção lenta extrapola mal nos extremos; recortar evita o carro "colado" no início/fim do caminho)
    ok_s = (sg >= 1.0) & (sg <= S[-1] - 1.0) & (tg >= tl[0] + 0.5) & (tg <= tl[-1] - 0.5)
    i0, i1 = np.argmax(ok_s), len(ok_s) - np.argmax(ok_s[::-1])
    tg, sg = tg[i0:i1], sg[i0:i1]
    # a volta propriamente dita: s em t=0 e t=dur
    s_ini, s_fim = float(np.interp(0, tg, sg)), float(np.interp(dur, tg, sg))

    # --- 5. altura, inclinação, rolagem, rumo
    pista = _pista()
    chao, asf = pista["chao"], pista["asf"]
    tang = np.c_[gaussian_filter1d(np.gradient(P[:, 0]), 1.5, mode="nearest"),
                 gaussian_filter1d(np.gradient(P[:, 1]), 1.5, mode="nearest")]
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.c_[-tang[:, 1], tang[:, 0]]

    def h_em(x, z, perto):
        h = chao.altura(x, z, perto=perto, janela=1.2)
        return perto if h is None else h

    # altura de referência inicial: o asfalto sob o 1º ponto (ou o mais próximo achado)
    perto = None
    for k in range(len(P)):
        hs = asf.alturas(*P[k])
        if hs:
            perto = max(hs)
            break
    Y = np.zeros(len(P))
    Yl = np.zeros(len(P))
    Yr = np.zeros(len(P))
    for k in range(len(P)):
        Y[k] = h_em(P[k, 0], P[k, 1], perto)
        perto = Y[k]
        Yl[k] = h_em(*(P[k] + nrm[k] * MEIA_BITOLA), Y[k])
        Yr[k] = h_em(*(P[k] - nrm[k] * MEIA_BITOLA), Y[k])
    # pontos médios: a reta entre duas amostras não pode passar abaixo do chão
    for k in range(len(P) - 1):
        for f in np.arange(1, 8) / 8:
            q = P[k] * (1 - f) + P[k + 1] * f
            hm = h_em(q[0], q[1], Y[k] * (1 - f) + Y[k + 1] * f)
            lin = Y[k] * (1 - f) + Y[k + 1] * f
            if hm > lin:
                Y[k] += hm - lin
                Y[k + 1] += hm - lin
    Y += FOLGA_Y
    # rumo (three.js: rotação em Y; frente do carro = +Z local) -> yaw = atan2(dx, dz), desenrolado
    yaw = np.unwrap(np.arctan2(tang[:, 0], tang[:, 1]))
    pitch = np.arctan2(gaussian_filter1d(np.gradient(Y), 2.0, mode="nearest"), DS)
    # nrm aponta para a DIREITA do carro (frente +Z, esquerda = +X local no three.js); roll > 0 = lado esquerdo sobe
    # (rotação em Z local, regra da mão direita). Yl = altura em P + nrm (direita), Yr = em P - nrm (esquerda).
    roll = np.arctan2(gaussian_filter1d(Yr - Yl, 2.0, mode="nearest"), 2 * MEIA_BITOLA)

    # --- qualidade: velocidade do relógio x velocidade da telemetria
    tq = np.arange(0, dur, 0.1)
    v_rel = np.gradient(np.interp(tq, tg, sg), tq) * 3.6
    v_tel = np.interp(tq, tc, vc)
    eq = next((c for c in CORES["pilotos"] if c["numero"] == piloto), None)
    drv = next((d for d in openf1.pilotos(sessao) if d["driver_number"] == piloto), {})
    equipe = drv.get("team_name", eq["equipe"] if eq else "?")
    cor_eq = CORES["equipes"].get(equipe, {})
    info = openf1.sessao_info(sessao)
    out = dict(
        versao=1,
        fonte=f"OpenF1 (api.openf1.org) /v1/location e /v1/laps; {info['circuit_short_name']} {info['year']} {info['session_name']} (session_key {sessao})",
        sessao=sessao, sessao_nome=info["session_name"], piloto=piloto, sigla=drv.get("name_acronym", ""),
        nome=drv.get("full_name", ""), equipe=equipe,
        cor=cor_eq.get("cor", "#" + drv.get("team_colour", "888888")),
        cor2=cor_eq.get("cor2", "#" + drv.get("team_colour", "888888")),
        volta=volta, duracao=dur,
        setores=[lap.get("duration_sector_1"), lap.get("duration_sector_2"), lap.get("duration_sector_3")],
        pista="interlagos_sao_paulo.glb",
        coordenadas="glTF/three.js (Y para cima, metros), arquivo carregado sem transformação",
        relogio=dict(t0=round(float(tg[0]), 4), dt=DT_RELOGIO, s=np.round(sg, 3).tolist(), s_ini=round(s_ini, 3), s_fim=round(s_fim, 3)),
        caminho=dict(ds=DS, x=np.round(P[:, 0], 3).tolist(), y=np.round(Y, 3).tolist(), z=np.round(P[:, 1], 3).tolist(),
                     yaw=np.round(yaw, 4).tolist(), pitch=np.round(pitch, 4).tolist(), roll=np.round(roll, 4).tolist()),
        gps=dict(t=np.round(tl, 3).tolist(), x=np.round(xz[:, 0], 3).tolist(), z=np.round(xz[:, 1], 3).tolist()),
        qualidade=dict(
            amostras_gps=int(len(tl)), buracos_gps_maiores_0_6s=buracos,
            correcao_lateral_max_m=round(float(corr_mag.max()), 3), correcao_lateral_media_m=round(float(corr_mag.mean()), 3),
            vel_relogio_x_telemetria_kmh=dict(erro_medio=round(float(np.mean(np.abs(v_rel - v_tel))), 2),
                                              p95=round(float(np.percentile(np.abs(v_rel - v_tel), 95)), 2)),
            comprimento_volta_m=round(s_fim - s_ini, 1),
            gps_x_relogio_ao_longo_m=dict(rms=round(float(np.sqrt(np.mean(erro_gps_ao_longo ** 2))), 2),
                                          max=round(float(np.abs(erro_gps_ao_longo).max()), 2)),
        ),
    )
    saida = Path(saida) if saida else AQUI / "voltas" / f"{sessao}_{piloto}_{volta}.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out, saida


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("uso: python preparar_volta.py <session_key> <piloto> <volta|melhor> [...mais trios]")
        sys.exit(1)
    a = sys.argv[1:]
    for i in range(0, len(a), 3):
        s, p, v = int(a[i]), int(a[i + 1]), a[i + 2]
        if v == "melhor":
            v = min((x for x in openf1.voltas(s, p) if x.get("lap_duration")), key=lambda x: x["lap_duration"])["lap_number"]
        out, arq = preparar(s, p, int(v))
        print(arq.name, f"{arq.stat().st_size / 1024:.0f} KB", out["sigla"], out["volta"], out["duracao"], out["qualidade"])
