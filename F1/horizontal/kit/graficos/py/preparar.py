"""Prepara os dados dos gráficos de comparação de duas voltas (kit/graficos), direto do OpenF1. Serve para QUALQUER
sessão/pista/piloto: tudo entra por parâmetro; nada é fixo de um GP.

Entrada (cache do OpenF1 do kit/gps, `kit/gps/cache/<sessao>/`; baixa se faltar, via kit/gps/py/openf1.py):
  `sessions` (circuito, ano), `drivers` (sigla, nome, equipe, cor), `laps` (tempo de volta e de setores),
  `car_data` (velocidade, acelerador, freio, marcha, ~3,7 Hz) e `location` (x, y: traçado do minimapa).
Dados da pista (opcional): `kit/graficos/pista/<circuit_short_name>.json` = comprimento oficial, sentido e curvas com nome.
Saída: `kit/graficos/comparacoes/<sessao>_<pA>-<voltaA>_<pB>-<voltaB>.json` (vai para o Git), lida igual pelos dois motores.

Distância (método do teste HyperFrames elogiado): integral da velocidade da telemetria no tempo da volta (trapézio), de
`date_start` a `date_start + lap_duration`, normalizada ao comprimento da pista, cada piloto sozinho; por isso o delta
acumulado termina EXATAMENTE na diferença oficial dos tempos de volta. Comprimento: `--comprimento` > arquivo da pista >
média das distâncias integradas dos dois (avisado no JSON). Também guarda as amostras BRUTAS (para a verificação).
Setores: quantos o `/laps` trouxer (`duration_sector_1..N`).

Uso: python preparar.py <sessao> <pilotoA> <voltaA> <pilotoB> <voltaB> [--comprimento M]     (volta: número ou "melhor")
  ex.: python preparar.py 11408 16 17 12 22          (classificação SP 2026, LEC × ANT)
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

PASSO = 5.0  # m entre pontos da grade de distância


def ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def volta_de(sessao: int, piloto: int, volta: str) -> dict:
    vs = [v for v in openf1.voltas(sessao, piloto) if v.get("lap_duration")]
    if not vs:
        raise SystemExit(f"piloto {piloto} sem volta cronometrada na sessão {sessao}")
    if volta == "melhor":
        return min(vs, key=lambda v: v["lap_duration"])
    lap = next((v for v in vs if v["lap_number"] == int(volta)), None)
    if not lap:
        raise SystemExit(f"piloto {piloto}: volta {volta} sem tempo na sessão {sessao}")
    return lap


def setores_de(lap: dict) -> list[float]:
    s, k = [], 1
    while f"duration_sector_{k}" in lap:
        s.append(lap[f"duration_sector_{k}"])
        k += 1
    if not s or any(x is None for x in s):
        raise SystemExit(f"volta {lap['lap_number']} sem tempo de algum setor: {s}")
    return s


def amostras(sessao: int, piloto: int, lap: dict) -> dict:
    """Amostras brutas do car_data da volta (+1 amostra de cada lado para interpolar as pontas)."""
    t0, dur = ts(lap["date_start"]), lap["lap_duration"]
    cd = sorted(openf1.obter("car_data", session_key=sessao, driver_number=piloto), key=lambda r: r["date"])
    t = np.array([ts(r["date"]) - t0 for r in cd])
    i0 = max(0, int(np.searchsorted(t, 0.0)) - 1)
    i1 = min(len(cd), int(np.searchsorted(t, dur)) + 1)
    sel = cd[i0:i1]
    if len(sel) < 20 or t[i0] > 0.5 or t[i1 - 1] < dur - 0.5:
        raise SystemExit(f"piloto {piloto}: car_data não cobre a volta {lap['lap_number']} ({len(sel)} amostras)")
    return {
        "t": [round(float(x), 6) for x in t[i0:i1]],
        "vel": [r["speed"] for r in sel],
        "acel": [r["throttle"] for r in sel],
        "freio": [r["brake"] for r in sel],
        "marcha": [r["n_gear"] for r in sel],
        "date": [r["date"] for r in sel],
    }


def integrar(b: dict, dur: float) -> tuple[np.ndarray, float]:
    """Distância integrada (m) de cada amostra, 0 em t=0, e o total da volta."""
    t, v = np.array(b["t"]), np.array(b["vel"], float) / 3.6
    acc = np.concatenate([[0.0], np.cumsum(np.diff(t) * (v[1:] + v[:-1]) / 2)])
    d0, d1 = np.interp(0.0, t, acc), np.interp(dur, t, acc)
    return acc - d0, float(d1 - d0)


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


def tracado(sessao: int, piloto: int, lap: dict, t_grade: list[float], grade: np.ndarray) -> dict | None:
    """Traçado 2D do minimapa direto do /location do OpenF1 (x, y em dm → m; tela: x à direita, z = −y para baixo),
    com a distância de cada ponto pelo relógio da volta do piloto (t → d da grade)."""
    loc = sorted(openf1.localizacao(sessao, piloto), key=lambda r: r["date"])
    t0, dur = ts(lap["date_start"]), lap["lap_duration"]
    pts = [(ts(r["date"]) - t0, r["x"] / 10, -r["y"] / 10) for r in loc]
    pts = [p for p in pts if 0 <= p[0] <= dur]
    if len(pts) < 50:
        return None
    t = np.array([p[0] for p in pts])
    d = np.interp(t, t_grade, grade)
    return {"fonte": f"OpenF1 /v1/location (piloto {piloto}, volta {lap['lap_number']})",
            "x": [round(p[1], 1) for p in pts], "z": [round(p[2], 1) for p in pts], "d": np.round(d, 1).tolist()}


def main() -> None:
    args = sys.argv[1:]
    comp_arg = None
    if "--comprimento" in args:
        i = args.index("--comprimento")
        comp_arg = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 5:
        raise SystemExit(__doc__)
    sessao, pa, va, pb, vb = int(args[0]), int(args[1]), args[2], int(args[3]), args[4]
    info = openf1.sessao_info(sessao)
    circuito = info.get("circuit_short_name", "")
    arq_pista = KIT / "pista" / f"{circuito}.json"
    pista = json.loads(arq_pista.read_text(encoding="utf-8")) if arq_pista.exists() else {}
    dr = {d["driver_number"]: d for d in openf1.pilotos(sessao)}
    cores = json.loads((GPS / "cores.json").read_text(encoding="utf-8"))
    brutos = []
    for p, v in ((pa, va), (pb, vb)):
        if p not in dr:
            raise SystemExit(f"piloto {p} não está na sessão {sessao}")
        lap = volta_de(sessao, p, v)
        b = amostras(sessao, p, lap)
        acc, tot = integrar(b, lap["lap_duration"])
        brutos.append((p, lap, b, acc, tot))
    if comp_arg:
        L, origem = comp_arg, "parâmetro --comprimento"
    elif pista.get("comprimento_m"):
        L, origem = float(pista["comprimento_m"]), f"pista/{arq_pista.name}"
    else:
        L, origem = round((brutos[0][4] + brutos[1][4]) / 2, 1), "média das distâncias integradas (sem comprimento oficial)"
    grade = np.arange(0.0, L + 1e-6, PASSO)
    if grade[-1] < L:
        grade = np.append(grade, L)
    out_p, equipes_vistas = [], {}
    for p, lap, b, acc, tot in brutos:
        dist = acc / tot * L
        equipe = dr[p]["team_name"]
        # cor: kit/gps/cores.json pela equipe; senão a team_colour do OpenF1. 2º piloto da mesma equipe: cor2
        ce = cores["equipes"].get(equipe) or {"cor": "#" + (dr[p].get("team_colour") or "777777"), "cor2": "#555555"}
        cor = ce["cor2"] if equipes_vistas.get(equipe) else ce["cor"]
        equipes_vistas[equipe] = True
        b["d"] = np.round(dist, 4).tolist()
        out_p.append({
            "numero": p, "sigla": dr[p]["name_acronym"], "nome": dr[p]["full_name"], "equipe": equipe, "cor": cor,
            "volta": lap["lap_number"], "tempo": lap["lap_duration"], "setores": setores_de(lap),
            "inicio": lap["date_start"], "distancia_integrada_m": round(tot, 1),
            **serie(b, dist, grade, lap["lap_duration"]),
            "bruto": b,
        })
    A, B = out_p
    if len(A["setores"]) != len(B["setores"]):
        raise SystemExit("os dois pilotos têm números de setores diferentes")
    delta = np.round(np.array(A["t"]) - np.array(B["t"]), 4)
    # fronteiras de setor em distância: onde cada piloto estava ao fechar o setor (média dos dois)
    fr = []
    for k in range(1, len(A["setores"])):
        ds = [float(np.interp(sum(P["setores"][:k]), P["t"], grade)) for P in out_p]
        fr.append({"d": round(sum(ds) / 2, 1), "por_piloto": [round(x, 1) for x in ds]})
    nome_s = info.get("session_name", "")
    out = {
        "versao": 2,
        "fonte": f"OpenF1 (api.openf1.org) /v1/car_data, /v1/laps e /v1/location; {info.get('location', '')} {info.get('year', '')} "
                 f"{nome_s} (session_key {sessao})",
        "fonte_curta": f"Dados: OpenF1 · {nome_s} {info.get('location', '')} {info.get('year', '')}",
        "sessao": sessao, "sessao_nome": nome_s, "circuito": circuito, "local": info.get("location"), "ano": info.get("year"),
        "comprimento_m": L, "comprimento_origem": origem, "passo_m": PASSO,
        "metodo_distancia": "integral da velocidade do car_data no tempo da volta, normalizada ao comprimento (por piloto)",
        "grade_d": np.round(grade, 2).tolist(),
        "pilotos": out_p,
        "delta": delta.tolist(),
        "delta_def": "delta = tempo de A − tempo de B no mesmo ponto da pista (negativo: A à frente)",
        "setores_d": fr,
        "curvas": pista.get("curvas", []),
        "sentido": pista.get("sentido"),
        "tracado": tracado(sessao, pa, volta_de(sessao, pa, str(A["volta"])), A["t"], grade),
    }
    nome = f"{sessao}_{pa}-{A['volta']}_{pb}-{B['volta']}.json"
    dest = KIT / "comparacoes" / nome
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dest.name, f"{dest.stat().st_size / 1024:.0f} KB", circuito, f"L={L} ({origem})", A["sigla"], A["tempo"], A["cor"],
          B["sigla"], B["tempo"], B["cor"], "delta final", delta[-1], "setores", len(A["setores"]),
          "dist. integrada", A["distancia_integrada_m"], B["distancia_integrada_m"])


if __name__ == "__main__":
    main()
