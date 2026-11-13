# Teste do modo SEM modelo 3D (pista plana traçada pelo GPS do OpenF1).
#  1. Cada pista/<circuito>_plana.json: linha fechada (sem buraco nem salto entre pontos), passo uniforme, sem quina
#     (curvatura < 1/8 m: nenhuma curva de F1 tem raio menor), largura dentro da faixa, comprimento perto do oficial
#     (kit/graficos/pista/<circuito>.json, quando existe), GPS das voltas usadas dentro do asfalto + zebra.
#  2. Prova do MÉTODO contra a verdade: traça Interlagos pelo GPS (classificação 11408) como se não houvesse modelo
#     e mede no interlagos_sao_paulo.glb (alinhado) quanto da linha central plana cai sobre o asfalto/zebra do modelo.
#     (pula com aviso se o .glb não estiver na máquina)
# O movimento do carro nas voltas planas (monotonicidade, saltos, altura >= chão) é o testes/testar_gps.py, igual ao
# modo com modelo. Uso: python testar_plana.py   Relatório: F1/horizontal/testes/gps/relatorio_plana.json
import json
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parent
sys.path.insert(0, str(KIT / "py"))
import pista as P  # noqa: E402

SAIDA = KIT.parent.parent / "testes" / "gps"
GRAFICOS_PISTA = KIT.parent / "graficos" / "pista"
LIM_COMPRIMENTO = 0.03      # |comprimento traçado - oficial| / oficial (o traçado é o do piloto, um pouco mais curto)
LIM_CURVATURA = 1 / 8.0     # 1/m
LIM_FECHAMENTO = 1.5        # x DS entre o último e o primeiro ponto
LIM_SOBRE_MODELO = 0.90     # fração da linha central plana sobre asfalto+zebra do modelo (Interlagos)
LIM_FORA_MODELO_M = 4.0     # m: ponto da linha central plana mais longe da área pilotável do modelo


def checar_arquivo(arq):
    d = json.loads(arq.read_text(encoding="utf-8"))
    c = np.c_[d["centro"]["x"], d["centro"]["z"]]
    ds = d["centro"]["ds"]
    r, ok = {"arquivo": arq.name, "circuito": d["circuito"]}, True
    passo = np.linalg.norm(np.diff(np.r_[c, c[:1]], axis=0), axis=1)
    r["passo_min_max_m"] = [round(float(passo[:-1].min()), 3), round(float(passo[:-1].max()), 3)]
    r["fechamento_m"] = round(float(passo[-1]), 3)
    ok &= passo[:-1].max() <= ds * 1.05 and passo[:-1].min() >= ds * 0.95 and passo[-1] <= ds * LIM_FECHAMENTO
    t = np.roll(c, -1, 0) - c
    ang = np.diff(np.unwrap(np.arctan2(t[:, 1], t[:, 0])))
    curv = np.abs(ang) / ds
    r["curvatura_max_1_m"] = round(float(curv.max()), 4)
    r["raio_min_m"] = round(float(1 / max(curv.max(), 1e-9)), 1)
    ok &= curv.max() <= LIM_CURVATURA
    giro = abs(np.unwrap(np.arctan2(t[:, 1], t[:, 0]))[-1] - np.arctan2(t[0, 1], t[0, 0]))
    r["giro_total_voltas"] = round(float(giro / (2 * np.pi)), 3)   # 1 = laço simples; 0 = pista em 8 (cruzamento)
    ok &= min(abs(r["giro_total_voltas"] - 1), abs(r["giro_total_voltas"])) < 0.05
    r["largura_m"] = d["largura_m"]
    ok &= P.LARGURA_MIN <= d["largura_m"] <= P.LARGURA_MAX
    r["comprimento_m"] = d["comprimento_m"]
    of = GRAFICOS_PISTA / f"{d['circuito']}.json"
    if of.exists():
        oficial = json.loads(of.read_text(encoding="utf-8"))["comprimento_m"]
        r["comprimento_oficial_m"] = oficial
        r["erro_comprimento"] = round(abs(d["comprimento_m"] - oficial) / oficial, 4)
        ok &= r["erro_comprimento"] <= LIM_COMPRIMENTO
    r["gps_dentro_asfalto_mais_zebra"] = d["qualidade"]["fracao_dentro_asfalto_mais_zebra"]
    ok &= r["gps_dentro_asfalto_mais_zebra"] >= 0.99
    r["ok"] = bool(ok)
    return r


def prova_interlagos():
    if not P.tem_modelo("Interlagos"):
        return {"caso": "Interlagos plana x modelo", "ok": True, "pulado": "interlagos_sao_paulo.glb não encontrado"}
    tmp = KIT / "cache" / "_prova_Interlagos_plana.json"
    if not tmp.exists():
        P.tracar_plana("Interlagos", 11408, destino=tmp)
    d = json.loads(tmp.read_text(encoding="utf-8"))
    c = np.c_[d["centro"]["x"], d["centro"]["z"]]
    al = d["alinhamento"]
    xy = np.c_[(c[:, 0] - al["t"][0]) / al["escala"], -(c[:, 1] - al["t"][1]) / al["escala"]]   # volta ao OpenF1 (dm)
    g = P.carregar("Interlagos", modo="glb")
    q = g.aplicar(xy)
    M = g.mascara
    ij = np.round((q - M["lo"]) / M["r"]).astype(int)
    fora = M["dist"][ij[:, 1], ij[:, 0]] * M["r"]
    dentro = M["dentro"][ij[:, 1], ij[:, 0]] * M["r"]
    r = {"caso": "Interlagos plana (GPS 11408) x interlagos_sao_paulo.glb",
         "sobre_asfalto": round(float(np.mean([bool(g.asf.alturas(x, z)) for x, z in q])), 4),
         "sobre_asfalto_ou_zebra": round(float(np.mean([bool(g.pilot.alturas(x, z)) for x, z in q])), 4),
         "fora_max_m": round(float(fora.max()), 2),
         "dist_borda_por_dentro_p10_p50_p90_m": np.percentile(dentro, [10, 50, 90]).round(2).tolist(),
         "largura_bruta_gps_m": d["largura_bruta_m"]}
    r["ok"] = bool(r["sobre_asfalto_ou_zebra"] >= LIM_SOBRE_MODELO and r["fora_max_m"] <= LIM_FORA_MODELO_M)
    return r


def main():
    rel = {"limites": dict(comprimento=LIM_COMPRIMENTO, curvatura_1_m=LIM_CURVATURA, fechamento_x_ds=LIM_FECHAMENTO,
                           sobre_modelo=LIM_SOBRE_MODELO, fora_modelo_m=LIM_FORA_MODELO_M), "casos": []}
    for arq in sorted((KIT / "pista").glob("*_plana.json")):
        r = checar_arquivo(arq)
        rel["casos"].append(r)
        print(f"{'OK ' if r['ok'] else 'FALHOU'} {arq.name}: {json.dumps({k: v for k, v in r.items() if k not in ('arquivo', 'ok')}, ensure_ascii=False)}")
    r = prova_interlagos()
    rel["casos"].append(r)
    print(f"{'OK ' if r['ok'] else 'FALHOU'} {json.dumps(r, ensure_ascii=False)}")
    rel["ok"] = all(c["ok"] for c in rel["casos"])
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "relatorio_plana.json").write_text(json.dumps(rel, indent=1, ensure_ascii=False), encoding="utf-8")
    print("TUDO OK" if rel["ok"] else "HÁ FALHAS")
    sys.exit(0 if rel["ok"] else 1)


if __name__ == "__main__":
    main()
