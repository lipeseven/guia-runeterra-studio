"""Números de F1 conferidos contra o OpenF1 (canal com `fatos = "f1"`; fase 7a do documentário horizontal).

Fatos de F1 precisam ser precisos: o que o roteiro afirma com número (tempo de volta, diferença, posição, voltas,
pit stops, velocidade) é recalculado a partir dos dados brutos do OpenF1 (api.openf1.org, temporadas 2023+), sem modelo.
O modelo (pela conferência/pesquisa) só diz QUAL dado conferir: `pedido` = {"tipo", "ano", "local", "sessao", "piloto",
"piloto2", "volta", "valor", "casas"} (ou "session_key" no lugar de ano/local/sessao). A leitura HTTP e o cache em disco
são os do `kit/gps` (`F1/horizontal/kit/gps/py/openf1.py`, cache fora do Git).

`conferir(pedido)` → {"status": "confere" | "diverge" | "sem_dados", "valor_openf1", "explicacao", "fonte"}.
`fatos_da_sessao(pedido)` → fatos com número para o dossiê da pesquisa (resultado, melhor volta, pit stops).
"""
from __future__ import annotations

import importlib.util
import unicodedata
from pathlib import Path

from .banco import CANAL, RAIZ

TIPOS = {
    "tempo_volta": "tempo de uma volta (s); volta = número ou \"melhor\"",
    "diferenca": "diferença entre os tempos de volta de piloto e piloto2 (s); volta = número ou \"melhor\"",
    "posicao_final": "posição final na sessão (resultado oficial)",
    "posicao_largada": "posição de largada (1ª posição registrada na corrida)",
    "voltas_total": "número de voltas completadas pelo piloto (ou do vencedor, sem piloto)",
    "pit_stops": "quantos pit stops o piloto fez",
    "pit_tempo": "tempo parado no box (s) no pit stop da volta pedida (ou o mais rápido, sem volta)",
    "velocidade_max": "velocidade máxima do piloto na sessão (km/h) pela telemetria",
}
SESSOES = ("Race", "Qualifying", "Sprint", "Sprint Qualifying", "Sprint Shootout", "Practice 1", "Practice 2", "Practice 3")
PRIMEIRO_ANO = 2023   # o OpenF1 começa em 2023: antes disso, sem dados (a conferência cai na Wikipedia)

_cliente = None


def _obter(endpoint: str, **params):
    """GET com cache em disco (cliente do kit/gps). Trocável nos testes (dados fictícios, sem rede)."""
    global _cliente
    if _cliente is None:
        cfg = CANAL.get("horizontal_doc") or {}
        arq = RAIZ / Path(cfg.get("diretor", "F1/horizontal/diretor")).parent / "kit" / "gps" / "py" / "openf1.py"
        spec = importlib.util.spec_from_file_location("kit_gps_openf1", arq)
        _cliente = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_cliente)
    return _cliente.obter(endpoint, **params)


def _normal(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in t if ch.isalnum())


class SemDados(Exception):
    pass


def sessao(pedido: dict) -> dict:
    """Sessão do OpenF1 pelo session_key ou por ano + local (circuito/cidade/país) + nome da sessão."""
    if pedido.get("session_key"):
        s = _obter("sessions", session_key=int(pedido["session_key"]))
        if not s:
            raise SemDados(f"sessão {pedido['session_key']} não existe no OpenF1")
        return s[0]
    ano = pedido.get("ano")
    if not isinstance(ano, int) or ano < PRIMEIRO_ANO:
        raise SemDados(f"o OpenF1 só tem dados a partir de {PRIMEIRO_ANO} (ano: {ano})")
    nome = pedido.get("sessao") or "Race"
    alvo = _normal(pedido.get("local"))
    if not alvo:
        raise SemDados("falta o local (circuito ou cidade) da sessão")
    todas = [s for s in _obter("sessions", year=ano) if _normal(s.get("session_name")) == _normal(nome)]
    achadas = [s for s in todas if any(alvo in _normal(s.get(k)) or (_normal(s.get(k)) and _normal(s.get(k)) in alvo)
                                       for k in ("circuit_short_name", "location"))]
    if not achadas:
        achadas = [s for s in todas if alvo == _normal(s.get("country_name"))]
    if len(achadas) != 1:
        raise SemDados(f"{'nenhuma' if not achadas else f'{len(achadas)} sessões'} '{nome}' em '{pedido.get('local')}' {ano} no OpenF1")
    return achadas[0]


def _piloto(sk: int, quem) -> int:
    if isinstance(quem, int) or (isinstance(quem, str) and quem.isdigit()):
        return int(quem)
    alvo = _normal(quem)
    for d in _obter("drivers", session_key=sk):
        if alvo in (_normal(d.get("name_acronym")), _normal(d.get("last_name")), _normal(d.get("full_name")),
                    _normal(d.get("broadcast_name"))):
            return d["driver_number"]
    raise SemDados(f"piloto '{quem}' não está na sessão {sk}")


def _voltas(sk: int, num: int) -> list[dict]:
    return [v for v in _obter("laps", session_key=sk, driver_number=num) if v.get("lap_duration")]


def _tempo(sk: int, num: int, volta) -> tuple[float, str]:
    vs = _voltas(sk, num)
    if not vs:
        raise SemDados(f"sem voltas cronometradas do carro {num} na sessão {sk}")
    if volta in (None, "melhor", "best"):
        v = min(vs, key=lambda x: x["lap_duration"])
    else:
        v = next((x for x in vs if x["lap_number"] == int(volta)), None)
        if v is None:
            raise SemDados(f"carro {num} sem tempo na volta {volta} da sessão {sk}")
    return float(v["lap_duration"]), f"volta {v['lap_number']}"


def _resultado(sk: int, num: int | None = None) -> list[dict]:
    return _obter("session_result", session_key=sk, **({"driver_number": num} if num is not None else {}))


def calcular(pedido: dict) -> tuple[float, str, str]:
    """(valor, unidade, de onde veio) recalculado do OpenF1 para o pedido."""
    tipo = pedido.get("tipo")
    if tipo not in TIPOS:
        raise SemDados(f"tipo '{tipo}' não é conferido pelo OpenF1")
    s = sessao(pedido)
    sk = s["session_key"]
    rot = f"OpenF1 · {s.get('circuit_short_name')} {s.get('year')} {s.get('session_name')} (session_key {sk})"
    num = _piloto(sk, pedido["piloto"]) if pedido.get("piloto") not in (None, "") else None
    if tipo in ("tempo_volta", "diferenca"):
        if num is None:
            raise SemDados("falta o piloto")
        t1, q1 = _tempo(sk, num, pedido.get("volta"))
        if tipo == "tempo_volta":
            return round(t1, 3), "s", f"{rot} /laps carro {num} {q1}"
        if pedido.get("piloto2") in (None, ""):
            raise SemDados("diferença precisa de piloto2")
        n2 = _piloto(sk, pedido["piloto2"])
        t2, q2 = _tempo(sk, n2, pedido.get("volta2", pedido.get("volta")))
        return round(abs(t1 - t2), 3), "s", f"{rot} /laps carro {num} {q1} × carro {n2} {q2}"
    if tipo == "posicao_final":
        r = _resultado(sk, num)
        if not r or r[0].get("position") is None:
            raise SemDados(f"sem resultado oficial do carro {num}")
        return float(r[0]["position"]), "posição", f"{rot} /session_result carro {num}"
    if tipo == "posicao_largada":
        pos = sorted(_obter("position", session_key=sk, driver_number=num), key=lambda p: p["date"])
        if not pos:
            raise SemDados(f"sem posições do carro {num}")
        return float(pos[0]["position"]), "posição", f"{rot} /position (1º registro) carro {num}"
    if tipo == "voltas_total":
        if num is None:
            r = [x for x in _resultado(sk) if x.get("position") == 1]
            if not r:
                raise SemDados("sem resultado oficial da sessão")
            return float(r[0]["number_of_laps"]), "voltas", f"{rot} /session_result vencedor"
        r = _resultado(sk, num)
        if r and r[0].get("number_of_laps") is not None:
            return float(r[0]["number_of_laps"]), "voltas", f"{rot} /session_result carro {num}"
        vs = _obter("laps", session_key=sk, driver_number=num)
        return float(max((v["lap_number"] for v in vs), default=0)), "voltas", f"{rot} /laps carro {num}"
    if num is None:
        raise SemDados("falta o piloto")
    if tipo == "pit_stops":
        return float(len(_obter("pit", session_key=sk, driver_number=num))), "paradas", f"{rot} /pit carro {num}"
    if tipo == "pit_tempo":
        ps = [p for p in _obter("pit", session_key=sk, driver_number=num) if p.get("stop_duration") is not None]
        if pedido.get("volta") not in (None, "", "melhor"):
            ps = [p for p in ps if p.get("lap_number") == int(pedido["volta"])]
        if not ps:
            raise SemDados(f"sem tempo de parada do carro {num}")
        p = min(ps, key=lambda x: x["stop_duration"])
        return round(float(p["stop_duration"]), 2), "s", f"{rot} /pit carro {num} volta {p.get('lap_number')}"
    # velocidade_max
    vel = [c["speed"] for c in _obter("car_data", session_key=sk, driver_number=num) if isinstance(c.get("speed"), (int, float))]
    if not vel:
        raise SemDados(f"sem telemetria do carro {num}")
    return float(max(vel)), "km/h", f"{rot} /car_data carro {num}"


def _tolerancia(pedido: dict, unidade: str) -> float:
    """Meia unidade da última casa dita no roteiro ("0,117 s" → 0,0005; "um décimo" = 0,1 → 0,05)."""
    if unidade in ("posição", "voltas", "paradas"):
        return 0.0
    casas = pedido.get("casas")
    if not isinstance(casas, int):
        txt = str(pedido.get("valor"))
        casas = len(txt.split(".")[1]) if "." in txt else 0
    return 0.5 * 10 ** -casas + 1e-9 if unidade == "s" else max(1.0, 0.5 * 10 ** -casas)


def _fmt(v: float, unidade: str) -> str:
    if unidade == "posição":
        return f"{int(v)}º"
    if unidade == "s" and v >= 60:
        m, s = divmod(v, 60)
        return f"{int(m)}:{s:06.3f}".replace(".", ",")
    return (f"{v:.3f}".rstrip("0").rstrip(".") if unidade == "s" else f"{v:g}").replace(".", ",") + f" {unidade}"


def conferir(pedido: dict) -> dict:
    """Valor dito no roteiro × valor recalculado do OpenF1."""
    try:
        certo, unidade, fonte = calcular(pedido)
    except SemDados as e:
        return {"status": "sem_dados", "explicacao": f"OpenF1: {e}", "fonte": None, "valor_openf1": None}
    except Exception as e:   # rede/limite do OpenF1: não decide nada
        return {"status": "sem_dados", "explicacao": f"OpenF1 indisponível ({type(e).__name__}: {str(e)[:120]})",
                "fonte": None, "valor_openf1": None}
    dito = pedido.get("valor")
    if not isinstance(dito, (int, float)):
        return {"status": "sem_dados", "explicacao": f"OpenF1 dá {_fmt(certo, unidade)}, mas o roteiro não diz o valor",
                "fonte": fonte, "valor_openf1": certo}
    ok = abs(float(dito) - certo) <= _tolerancia(pedido, unidade)
    return {"status": "confere" if ok else "diverge", "valor_openf1": certo, "unidade": unidade, "fonte": fonte,
            "explicacao": f"OpenF1: {_fmt(certo, unidade)}" + ("" if ok else f" (o roteiro diz {_fmt(float(dito), unidade)})")}


def fatos_da_sessao(pedido: dict) -> list[tuple[str, str]]:
    """(fonte, texto) com os números da sessão para a pesquisa: resultado (top 10 + pilotos pedidos), melhor volta e
    pit stops dos pilotos pedidos. Sem dados (ano < 2023, sessão não achada): lista vazia."""
    try:
        s = sessao(pedido)
    except SemDados:
        return []
    except Exception:
        return []
    sk = s["session_key"]
    rot = f"OpenF1 · {s.get('circuit_short_name')} {s.get('year')} {s.get('session_name')} (session_key {sk})"
    try:
        nomes = {d["driver_number"]: d.get("name_acronym") or str(d["driver_number"]) for d in _obter("drivers", session_key=sk)}
        res = sorted((r for r in _resultado(sk) if isinstance(r.get("position"), int)), key=lambda r: r["position"])
    except Exception:
        return []
    pedidos = []
    for p in pedido.get("pilotos") or []:
        try:
            pedidos.append(_piloto(sk, p))
        except SemDados:
            continue
    linhas = [f"{r['position']}º {nomes.get(r['driver_number'], r['driver_number'])} (carro {r['driver_number']}, "
              f"{r.get('number_of_laps')} voltas{', DNF' if r.get('dnf') else ''})"
              for r in res if r["position"] <= 10 or r["driver_number"] in pedidos]
    saida = [(rot, "Resultado: " + "; ".join(linhas))] if linhas else []
    for num in pedidos:
        try:
            t, q = _tempo(sk, num, "melhor")
            saida.append((rot, f"{nomes.get(num, num)} (carro {num}): melhor volta {_fmt(t, 's')} na {q}"))
            n_pit = len(_obter("pit", session_key=sk, driver_number=num))
            if s.get("session_name") in ("Race", "Sprint"):
                saida.append((rot, f"{nomes.get(num, num)} (carro {num}): {n_pit} pit stop(s)"))
        except Exception:
            continue
    return saida
