# Teste automático da posição lateral e da pista vinda de mod do Assetto Corsa (Interlagos_vhe). Complementa
# testar_gps.py (movimento, altura, monotonicidade — que roda também nas voltas _livre/_ideal) sem mudar os critérios dele.
#  1. bordas(): pista sintética (asfalto reto de 12 m + zebra de 1 m à esquerda): distâncias e frações exatas.
#  2. Linha: projeção (s, d) e ponto(s, d) são inversos; d > 0 = esquerda.
#  3. Alinhamento Interlagos_vhe: 0% do GPS fora de asfalto+zebra; escala a < 1% de 0,1 (dm -> m).
#  4. .ai do mod: lado_esq da linha ideal bate com a borda esquerda da malha 1road (convenção de lado), comprimento.
#  5. Volta _livre: correção lateral 0 e caminho a <= 0,6 m (mediana) do GPS bruto (traçado preservado).
#  6. Volta _ideal: caminho sobre a linha ideal (|d| <= 0,05 m) e marcada como lateral NÃO medida.
#  7. Lateral por metro: presente, finita em >= 98% dos pontos, largura do asfalto em [6, 25] m em >= 95%;
#     ápices: S do Senna (1) com zebra e borda esquerda < 1,5 m (o que o traçado ideal do mod faz).
#  8. (KN5) se o mod estiver na máquina: assetto.py exporta as superfícies idênticas (±1 mm) às do Blender.
# Uso: python testar_lateral.py   (sai com 1 se algo falhar; relatório em F1/horizontal/testes/gps/relatorio_lateral.json)
import json
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parent
sys.path.insert(0, str(KIT / "py"))
import lateral as LAT  # noqa: E402
import pista as PISTA  # noqa: E402

SAIDA = KIT.parent.parent / "testes" / "gps"
CIRC = "Interlagos_vhe"
VOLTA = "11408_44_12_Interlagos_vhe"
res, falhas = {}, []


def checa(nome, ok, valor):
    res[nome] = dict(ok=bool(ok), valor=valor)
    print(("OK     " if ok else "FALHOU ") + nome, valor)
    if not ok:
        falhas.append(nome)


def fita(x0, x1, z0, z1):
    """retângulo no plano y = 0 como 2 triângulos (n, 3, 3)"""
    a, b, c, d = [x0, 0, z0], [x1, 0, z0], [x1, 0, z1], [x0, 0, z1]
    return np.array([[a, b, c], [a, c, d]], float)


class PistaFalsa:
    circuito, modo = "sintetica", "teste"

    def __init__(self):
        # carro andando em +z; esquerda = (fz, -fx) = (1, 0)*... -> para frente (0, 1): esquerda = (1, 0) = +x
        self._T_asf = fita(-6, 6, -200, 200)
        self._T_zebra = fita(6, 7, -200, 200)


def t1_bordas():
    p = PistaFalsa()
    P = np.array([[0.0, 0.0], [5.5, 10.0], [-6.5, 20.0]])
    esq = LAT.esquerda(np.array([[0.0, 1.0]] * 3))
    B = LAT.bordas(p, P, esq)
    ok = (abs(B["borda_esq"][0] - 6) <= 0.15 and abs(B["borda_dir"][0] - 6) <= 0.15 and B["zebra"][0] == 0
          and B["fora_asfalto"][0] == 0 and abs(B["borda_esq"][1] - 0.5) <= 0.15 and 0.15 <= B["zebra"][1] <= 0.35
          and abs(B["borda_dir"][2] + 0.5) <= 0.15 and 0.6 <= B["fora_asfalto"][2] <= 0.85)
    checa("1 bordas() em pista sintética", ok, {k: np.round(v, 2).tolist() for k, v in B.items()})


def t2_linha():
    th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    L = LAT.Linha(np.c_[100 * np.cos(th), 100 * np.sin(th)])
    s = np.array([10.0, 200.0, 500.0]); d = np.array([2.0, -3.0, 0.5])
    s2, d2 = L.projetar(L.ponto(s, d))
    checa("2 Linha.projetar(ponto(s, d)) = (s, d)", np.abs(s2 - s).max() < 0.05 and np.abs(d2 - d).max() < 0.05,
          dict(s=np.round(s2, 3).tolist(), d=np.round(d2, 3).tolist()))


def t3_alinhamento():
    al = PISTA.parametros(CIRC)["alinhamento"]
    checa("3 alinhamento: GPS fora de asfalto+zebra <= 0,1%; escala ~0,1",
          al.get("fracao_fora_pilotavel", 1) <= 0.001 and abs(al["escala"] / 0.1 - 1) < 0.01,
          dict(fora=al.get("fracao_fora_pilotavel"), escala=round(al["escala"], 5), folga=al.get("folga_translacao_m")))


def t4_ai():
    par = PISTA.parametros(CIRC)
    if not Path(par["linha_ideal"]).exists():
        checa("4 .ai do mod (pulado: mod fora da máquina)", True, None)
        return
    L = LAT.Linha.de_ai(par["linha_ideal"])
    p = PISTA.carregar(CIRC, modo="glb")
    B = LAT.bordas(p, L.L[::5], L.esq[::5])
    de = np.nanmedian(np.abs(B["borda_esq"] - L.extra["lado_esq"][::5]))
    troca = np.nanmedian(np.abs(B["borda_esq"] - L.extra["lado_dir"][::5]))
    checa("4 .ai: lado_esq = borda esquerda da malha (e não a direita); comprimento ~4223 m",
          de < 1.5 and troca > 4 and abs(L.comprimento - 4223) < 10,
          dict(dif_mediana_m=round(float(de), 2), se_trocado_m=round(float(troca), 2), comprimento=round(L.comprimento, 1)))


def t5_livre():
    v = json.loads((KIT / "voltas" / f"{VOLTA}_livre.json").read_text(encoding="utf-8"))
    P = np.c_[v["caminho"]["x"], v["caminho"]["z"]]
    G = np.c_[v["gps"]["x"], v["gps"]["z"]]
    from scipy.spatial import cKDTree
    d, _ = cKDTree(P).query(G)
    checa("5 volta _livre: sem correção lateral e caminho sobre o GPS",
          v["qualidade"]["correcao_lateral_max_m"] == 0 and np.median(d) <= 0.6 and v["lateral"]["medida"],
          dict(correcao_max=v["qualidade"]["correcao_lateral_max_m"], gps_caminho_p50=round(float(np.median(d)), 3),
               p95=round(float(np.percentile(d, 95)), 3)))


def t6_ideal():
    v = json.loads((KIT / "voltas" / f"{VOLTA}_ideal.json").read_text(encoding="utf-8"))
    par = PISTA.parametros(CIRC)
    if not Path(par["linha_ideal"]).exists():
        checa("6 volta _ideal (pulado: mod fora da máquina)", True, None)
        return v
    L = LAT.Linha.de_ai(par["linha_ideal"])
    _, d = L.projetar(np.c_[v["caminho"]["x"], v["caminho"]["z"]])
    checa("6 volta _ideal: caminho na linha ideal; lateral marcada como inferida",
          np.abs(d).max() <= 0.05 and v["lateral"]["medida"] is False,
          dict(d_max=round(float(np.abs(d).max()), 4), fonte=v["lateral"]["fonte"]))
    return v


def t7_lateral(v):
    lt = v["lateral"]
    be = np.array(lt["borda_esq"], float); bd = np.array(lt["borda_dir"], float)
    fin = np.isfinite(be) & np.isfinite(bd)
    w = (be + bd)[fin]
    par = PISTA.parametros(CIRC)
    ok = len(be) == len(v["caminho"]["x"]) and fin.mean() >= 0.98 and np.mean((w >= 6) & (w <= 25)) >= 0.95
    val = dict(finitos=round(float(fin.mean()), 4), largura_p5_p50_p95=np.round(np.percentile(w, [5, 50, 95]), 1).tolist())
    if Path(par["linha_ideal"]).exists():
        L = LAT.Linha.de_ai(par["linha_ideal"])
        c = next(c for c in LAT.curvas(L) if c.get("nome") == "S do Senna (1)")
        from scipy.spatial import cKDTree
        _, k = cKDTree(np.c_[v["caminho"]["x"], v["caminho"]["z"]]).query(L.ponto(c["s"]))
        val["senna1"] = dict(borda_esq=lt["borda_esq"][k], zebra=lt["zebra"][k])
        ok &= lt["zebra"][k] > 0 and lt["borda_esq"][k] < 1.5
        val["lados_das_curvas_ok"] = all(c["lado_curva"] == c.get("lado_esperado") for c in LAT.curvas(L))
        ok &= val["lados_das_curvas_ok"]
    checa("7 lateral por metro (bordas, zebra) e ápice do S do Senna", ok, val)


def t8_kn5():
    import assetto
    mod = Path(PISTA.parametros(CIRC)["linha_ideal"]).parents[2]
    ref = PISTA._achar_glb(PISTA.parametros(CIRC)["glb"]["arquivo"])
    if not (mod / "vhe_interlagos.kn5").exists() or ref is None:
        checa("8 KN5 -> GLB (pulado: mod ou .glb fora da máquina)", True, None)
        return
    from pista_glb import triangulos
    tmp = KIT / "cache" / "_teste_superficies.glb"
    assetto.superficies(mod, tmp, ["vhe_interlagos.kn5"])
    A = triangulos(tmp, agrupar="no")
    B = triangulos(ref, agrupar="no")
    difs = {}
    for k in ("1road001", "1kerb001", "1curb001"):
        kb = next(x for x in B if x.replace("_", "") == k)
        a, b = A[k].reshape(-1, 3), B[kb].reshape(-1, 3)
        difs[k] = float(np.abs(np.sort(a, 0) - np.sort(b, 0)).max()) if a.shape == b.shape else 99.0
    tmp.unlink()
    checa("8 KN5 -> GLB (assetto.py) = exportação do Blender (±1 mm)", max(difs.values()) <= 1e-3,
          {k: round(v, 6) for k, v in difs.items()})


if __name__ == "__main__":
    t1_bordas(); t2_linha(); t3_alinhamento(); t4_ai(); t5_livre(); t7_lateral(t6_ideal()); t8_kn5()
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "relatorio_lateral.json").write_text(json.dumps(dict(ok=not falhas, casos=res), ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    print("TUDO OK" if not falhas else f"FALHAS: {falhas}")
    sys.exit(1 if falhas else 0)
