"""Prepara os dados dos gráficos de comparação de duas voltas (kit/graficos), direto do OpenF1.

Entrada: cache do OpenF1 do kit/gps (`kit/gps/cache/<sessao>/`, baixa se faltar, via kit/gps/py/openf1.py):
  `laps` (tempo de volta e de setor), `car_data` (velocidade, acelerador, freio, marcha, ~3,7 Hz), `drivers`, `sessions`.
  Traçado do minimapa: a volta já preparada do kit/gps (`kit/gps/voltas/<sessao>_<piloto>_<volta>.json`), se existir.
Saída: `kit/graficos/comparacoes/<sessao>_<pA>-<voltaA>_<pB>-<voltaB>.json` (vai para o Git), lida igual pelos dois motores.

Como a distância é feita (igual ao teste HyperFrames elogiado): integral da velocidade da telemetria no tempo da volta
(trapézio), de `date_start` a `date_start + lap_duration`, normalizada para o comprimento oficial (Interlagos 4.309 m).
Cada piloto é normalizado sozinho; por isso o delta acumulado termina EXATAMENTE na diferença oficial dos tempos de volta.
Também guarda as amostras BRUTAS da volta (para a verificação comparar o que foi plotado com a fonte).

Uso: python preparar.py 11408 16 17 12 22          (sessão, piloto A, volta A, piloto B, volta B; volta "melhor" vale)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parent
GPS = KIT.parent / "gps"
sys.path.insert(0, str(GPS / "py"))
import openf1  # noqa: E402  (kit/gps/py/openf1.py: cache em kit/gps/cache)

COMPRIMENTO = {"Interlagos": 4309.0}  # m, comprimento oficial
PASSO = 5.0  # m entre pontos da grade de distância


def ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def volta_de(sessao: int, piloto: int, volta: str) -> dict:
    vs = [v for v in openf1.voltas(sessao, piloto) if v.get("lap_duration")]
    if volta == "melhor":
        return min(vs, key=lambda v: v["lap_duration"])
    return next(v for v in vs if v["lap_number"] == int(volta))


def amostras(sessao: int, piloto: int, lap: dict) -> dict:
    """Amostras brutas do car_data da volta (+1 amostra de cada lado para interpolar as pontas)."""
    t0, dur = ts(lap["date_start"]), lap["lap_duration"]
    cd = sorted(openf1.obter("car_data", session_key=sessao, driver_number=piloto), key=lambda r: r["date"])
    t = np.array([ts(r["date"]) - t0 for r in cd])
    i0 = max(0, int(np.searchsorted(t, 0.0)) - 1)
    i1 = min(len(cd), int(np.searchsorted(t, dur)) + 1)
    sel = cd[i0:i1]
    return {
        "t": [round(float(x), 6) for x in t[i0:i1]],
        "vel": [r["speed"] for r in sel],
        "acel": [r["throttle"] for r in sel],
        "freio": [r["brake"] for r in sel],
        "marcha": [r["n_gear"] for r in sel],
        "date": [r["date"] for r in sel],
    }


def distancia(b: dict, dur: float, L: float) -> np.ndarray:
    """Distância (m) de cada amostra bruta: integral trapezoidal da velocidade, 0 em t=0 e L em t=dur."""
    t, v = np.array(b["t"]), np.array(b["vel"], float) / 3.6
    acc = np.concatenate([[0.0], np.cumsum(np.diff(t) * (v[1:] + v[:-1]) / 2)])
    d0, d1 = np.interp(0.0, t, acc), np.interp(dur, t, acc)
    return (acc - d0) / (d1 - d0) * L, float(d1 - d0)


def serie(b: dict, dist: np.ndarray, grade: np.ndarray, dur: float) -> dict:
    t = np.array(b["t"])
    if np.any(np.diff(dist) <= 0):
        raise SystemExit("distância não cresce (carro parado dentro da volta?)")
    tempo = np.interp(grade, dist, t)
    tempo[0], tempo[-1] = 0.0, dur
    acel = np.clip(np.array(b["acel"], float), 0, 100)  # o OpenF1 usa 104 como valor inválido (carro parado)
    freio = (np.array(b["freio"], float) > 0).astype(float)
    # marcha e freio são degraus: valor da amostra mais recente (não interpola entre marchas)
    idx = np.clip(np.searchsorted(dist, grade, side="right") - 1, 0, len(dist) - 1)
    return {
        "t": np.round(tempo, 4).tolist(),
        "vel": np.round(np.interp(grade, dist, np.array(b["vel"], float)), 2).tolist(),
        "acel": np.round(np.interp(grade, dist, acel), 1).tolist(),
        "freio": freio[idx].astype(int).tolist(),
        "marcha": np.array(b["marcha"])[idx].astype(int).tolist(),
    }


def tracado(sessao: int, piloto: int, volta: int, L: float) -> dict | None:
    """Traçado 2D (x, z do .glb da pista, m) da volta preparada no kit/gps, com a distância normalizada de cada ponto."""
    arq = GPS / "voltas" / f"{sessao}_{piloto}_{volta}.json"
    if not arq.exists():
        return None
    v = json.loads(arq.read_text(encoding="utf-8"))
    r, c = v["relogio"], v["caminho"]
    s = np.array(r["s"])
    ts_ = r["t0"] + np.arange(len(s)) * r["dt"]
    sa, sb = np.interp(0.0, ts_, s), np.interp(v["duracao"], ts_, s)
    sc = np.arange(len(c["x"])) * c["ds"]
    m = (sc >= sa) & (sc <= sb)
    x, z, sp = np.array(c["x"])[m], np.array(c["z"])[m], sc[m]
    passo = max(1, len(x) // 500)
    return {"fonte": f"kit/gps/voltas/{arq.name} (GPS do OpenF1 alinhado ao .glb)",
            "x": np.round(x[::passo], 2).tolist(), "z": np.round(z[::passo], 2).tolist(),
            "d": np.round((sp[::passo] - sa) / (sb - sa) * L, 1).tolist()}


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    sessao, pa, va, pb, vb = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
    info = openf1.sessao_info(sessao)
    circuito = info.get("circuit_short_name", "")
    L = COMPRIMENTO.get(circuito)
    if not L:
        raise SystemExit(f"sem comprimento oficial para {circuito!r} (acrescente em COMPRIMENTO)")
    dr = {d["driver_number"]: d for d in openf1.pilotos(sessao)}
    cores = json.loads((GPS / "cores.json").read_text(encoding="utf-8"))
    grade = np.arange(0.0, L + 1e-6, PASSO)
    if grade[-1] < L:
        grade = np.append(grade, L)
    out_p, equipes_vistas = [], {}
    for p, v in ((pa, va), (pb, vb)):
        lap = volta_de(sessao, p, v)
        b = amostras(sessao, p, lap)
        dist, bruto_m = distancia(b, lap["lap_duration"], L)
        equipe = dr[p]["team_name"]
        ce = cores["equipes"].get(equipe, {"cor": "#" + dr[p]["team_colour"], "cor2": "#555555"})
        cor = ce["cor2"] if equipes_vistas.get(equipe) else ce["cor"]
        equipes_vistas[equipe] = True
        b["d"] = np.round(dist, 4).tolist()
        out_p.append({
            "numero": p, "sigla": dr[p]["name_acronym"], "nome": dr[p]["full_name"], "equipe": equipe, "cor": cor,
            "volta": lap["lap_number"], "tempo": lap["lap_duration"],
            "setores": [lap["duration_sector_1"], lap["duration_sector_2"], lap["duration_sector_3"]],
            "inicio": lap["date_start"], "distancia_integrada_m": round(bruto_m, 1),
            **serie(b, dist, grade, lap["lap_duration"]),
            "bruto": b,
        })
    A, B = out_p
    delta = np.round(np.array(A["t"]) - np.array(B["t"]), 4)
    # fronteiras de setor em distância: onde cada piloto estava ao fechar o setor (média dos dois)
    fr = []
    for k in (1, 2):
        ds = [float(np.interp(sum(P["setores"][:k]), P["t"], grade)) for P in out_p]
        fr.append({"d": round(sum(ds) / 2, 1), "por_piloto": [round(x, 1) for x in ds]})
    curvas = json.loads((KIT / "pista" / "interlagos_curvas.json").read_text(encoding="utf-8")) if circuito == "Interlagos" else None
    out = {
        "versao": 1,
        "fonte": f"OpenF1 (api.openf1.org) /v1/car_data e /v1/laps; {info.get('location', '')} {info.get('year', '')} "
                 f"{info.get('session_name', '')} (session_key {sessao})",
        "fonte_curta": f"Dados: OpenF1 · {info.get('session_name', '')} {info.get('location', '')} {info.get('year', '')}",
        "sessao": sessao, "sessao_nome": info.get("session_name"), "circuito": circuito,
        "comprimento_m": L, "passo_m": PASSO,
        "metodo_distancia": "integral da velocidade do car_data no tempo da volta, normalizada ao comprimento oficial (por piloto)",
        "grade_d": np.round(grade, 2).tolist(),
        "pilotos": out_p,
        "delta": delta.tolist(),
        "delta_def": "delta = tempo de A − tempo de B no mesmo ponto da pista (negativo: A à frente)",
        "setores_d": fr,
        "curvas": curvas["curvas"] if curvas else [],
        "tracado": tracado(sessao, pa, A["volta"], L),
    }
    nome = f"{sessao}_{pa}-{A['volta']}_{pb}-{B['volta']}.json"
    dest = KIT / "comparacoes" / nome
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dest.name, f"{dest.stat().st_size / 1024:.0f} KB", A["sigla"], A["tempo"], B["sigla"], B["tempo"],
          "delta final", delta[-1], "dist. integrada", A["distancia_integrada_m"], B["distancia_integrada_m"])


if __name__ == "__main__":
    main()
