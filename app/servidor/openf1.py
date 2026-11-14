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
    "setor": "tempo do setor (1, 2 ou 3) na volta pedida (s); com piloto2 = diferença entre os dois nesse setor",
    "speed_trap": "velocidade no speed trap (km/h, st_speed do /laps) na volta pedida",
}
SESSOES = ("Race", "Qualifying", "Sprint", "Sprint Qualifying", "Sprint Shootout", "Practice 1", "Practice 2", "Practice 3")
PRIMEIRO_ANO = 2023   # o OpenF1 começa em 2023: antes disso, sem dados (a conferência cai na Wikipedia)

# GP / país / cidade / circuito como o roteiro (PT) e o modelo (EN) costumam escrever → circuit_short_name do OpenF1.
# Uso real (2026-11-14): "classificação do GP do México de 2026" não achava a sessão (o modelo pode mandar "México",
# "Hermanos Rodríguez", "Classificação"...). Chaves já normalizadas por `_normal` (sem acento/espaço, minúsculas).
# País com mais de um GP (Itália: Monza/Imola; Espanha: Barcelona/Madri; EUA: Austin/Miami/Las Vegas) NÃO entra:
# fica ambíguo de propósito (sem dados), e o prompt pede o session_key ao orquestrador.
LOCAIS = {
    "mexico": "Mexico City", "cidadedomexico": "Mexico City", "mexicocity": "Mexico City", "hermanosrodriguez": "Mexico City",
    "brasil": "Interlagos", "brazil": "Interlagos", "saopaulo": "Interlagos", "interlagos": "Interlagos",
    "monza": "Monza", "emiliaromagna": "Imola", "imola": "Imola",
    "monaco": "Monte Carlo", "montecarlo": "Monte Carlo", "barcelona": "Catalunya", "catalunha": "Catalunya", "catalunya": "Catalunya", "madri": "Madring", "madrid": "Madring",
    "belgica": "Spa-Francorchamps", "belgium": "Spa-Francorchamps", "spa": "Spa-Francorchamps",
    "japao": "Suzuka", "japan": "Suzuka", "suzuka": "Suzuka", "holanda": "Zandvoort", "paisesbaixos": "Zandvoort",
    "netherlands": "Zandvoort", "zandvoort": "Zandvoort", "hungria": "Hungaroring", "hungary": "Hungaroring",
    "hungaroring": "Hungaroring", "austria": "Spielberg", "spielberg": "Spielberg", "redbullring": "Spielberg",
    "grabretanha": "Silverstone", "inglaterra": "Silverstone", "reinounido": "Silverstone", "britain": "Silverstone",
    "silverstone": "Silverstone", "canada": "Montreal", "montreal": "Montreal",
    "austin": "Austin",
    "lasvegas": "Las Vegas", "miami": "Miami", "arabiasaudita": "Jeddah", "saudiarabia": "Jeddah", "jeddah": "Jeddah",
    "bahrein": "Sakhir", "barein": "Sakhir", "bahrain": "Sakhir", "sakhir": "Sakhir",
    "australia": "Melbourne", "melbourne": "Melbourne", "china": "Shanghai", "xangai": "Shanghai", "shanghai": "Shanghai",
    "azerbaijao": "Baku", "azerbaijan": "Baku", "baku": "Baku", "singapura": "Singapore", "singapore": "Singapore",
    "catar": "Lusail", "qatar": "Lusail", "lusail": "Lusail", "abudhabi": "Yas Marina Circuit", "yasmarina": "Yas Marina Circuit",
}
# nome da sessão em PT/EN → session_name do OpenF1 (a classificação da sprint chamava "Sprint Shootout" em 2023)
NOMES_SESSAO = {"classificacao": "Qualifying", "quali": "Qualifying", "qualifying": "Qualifying",
                "corrida": "Race", "race": "Race", "sprint": "Sprint",
                "classificacaosprint": "Sprint Qualifying", "classificacaodasprint": "Sprint Qualifying",
                "sprintqualifying": "Sprint Qualifying", "sprintshootout": "Sprint Qualifying",
                "treinolivre1": "Practice 1", "tl1": "Practice 1", "fp1": "Practice 1", "practice1": "Practice 1",
                "treinolivre2": "Practice 2", "tl2": "Practice 2", "fp2": "Practice 2", "practice2": "Practice 2",
                "treinolivre3": "Practice 3", "tl3": "Practice 3", "fp3": "Practice 3", "practice3": "Practice 3"}

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


def nome_sessao(nome) -> str:
    """"Classificação", "quali", "Qualifying" → "Qualifying" (o que não reconhece volta como veio)."""
    return NOMES_SESSAO.get(_normal(nome), str(nome or ""))


def _mesma_sessao(pedida, do_openf1) -> bool:
    alvo = {_normal(nome_sessao(pedida))}
    if alvo & {"sprintqualifying", "sprintshootout"}:
        alvo = {"sprintqualifying", "sprintshootout"}
    return _normal(do_openf1) in alvo


def sessao_do_texto(texto: str) -> dict:
    """Ano, local (circuit_short_name) e sessão citados no texto ("na classificação do GP do México de 2026" →
    {"ano": 2026, "local": "Mexico City", "sessao": "Qualifying"}). Só o que achar: pode vir parcial ou vazio.
    Regra: o 1º GP/país/circuito citado; ano e sessão da mesma frase (senão os primeiros do texto)."""
    import re

    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    achado: dict = {}
    frase = t
    for f in re.split(r"(?<=[.!?])\s+|\n+", t):
        ws = re.findall(r"[a-z]+", f)
        # 1 a 3 palavras seguidas formam a chave ("cidade do mexico", "las vegas", "gra bretanha")
        local = next((LOCAIS["".join(ws[k:k + n])] for k in range(len(ws)) for n in (3, 2, 1)
                      if "".join(ws[k:k + n]) in LOCAIS), None)
        if local:
            achado["local"], frase = local, f
            break
    ano = re.search(r"\b(20[2-4]\d)\b", frase) or re.search(r"\b(20[2-4]\d)\b", t)
    if ano:
        achado["ano"] = int(ano.group(1))
    for rx, nome in ((r"classificacao (?:da |de )?sprint|sprint shootout|sprint qualifying", "Sprint Qualifying"),
                     (r"treino livre ?([123])|\b(?:tl|fp)([123])\b", "Practice"),
                     (r"classificacao|\bquali\b|qualifying|\bpole\b", "Qualifying"),
                     (r"\bsprint\b", "Sprint"), (r"\bcorrida\b|\brace\b", "Race")):
        m = re.search(rx, frase) or re.search(rx, t)
        if m:
            achado["sessao"] = f"Practice {next(g for g in m.groups() if g)}" if nome == "Practice" else nome
            break
    return achado


def sessao(pedido: dict, contexto: dict | None = None) -> dict:
    """Sessão do OpenF1 pelo session_key ou por ano + local (circuito/cidade/país, em PT ou EN) + nome da sessão.
    `contexto` = a sessão citada no roteiro (`sessao_do_texto`): preenche SÓ o que o pedido não traz (o trecho
    conferido raramente repete "classificação do GP de X de 2026"); ano/local/sessão ditos no pedido valem."""
    if pedido.get("session_key") or not contexto:
        return _sessao(pedido)
    return _sessao({**pedido, **{k: v for k, v in contexto.items() if pedido.get(k) in (None, "")}})


def _sessao(pedido: dict) -> dict:
    if pedido.get("session_key"):
        s = _obter("sessions", session_key=int(pedido["session_key"]))
        if not s:
            raise SemDados(f"sessão {pedido['session_key']} não existe no OpenF1")
        return s[0]
    ano = pedido.get("ano")
    if not isinstance(ano, int) or ano < PRIMEIRO_ANO:
        raise SemDados(f"o OpenF1 só tem dados a partir de {PRIMEIRO_ANO} (ano: {ano})")
    nome = nome_sessao(pedido.get("sessao") or "Race")
    alvo = _normal(pedido.get("local"))
    if not alvo:
        raise SemDados("falta o local (circuito ou cidade) da sessão")
    todas = [s for s in _obter("sessions", year=ano) if _mesma_sessao(nome, s.get("session_name"))]

    def no_local(a: str) -> list[dict]:
        return [s for s in todas if any(a in _normal(s.get(k)) or (_normal(s.get(k)) and _normal(s.get(k)) in a)
                                        for k in ("circuit_short_name", "location"))]

    achadas = no_local(alvo)
    if not achadas:
        achadas = [s for s in todas if alvo == _normal(s.get("country_name"))]
    if len(achadas) != 1 and alvo in LOCAIS:   # "México", "Hermanos Rodríguez", "Grã-Bretanha" → circuito do OpenF1
        achadas = no_local(_normal(LOCAIS[alvo])) or achadas
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


def _volta(sk: int, num: int, volta) -> dict:
    vs = _voltas(sk, num)
    if not vs:
        raise SemDados(f"sem voltas cronometradas do carro {num} na sessão {sk}")
    if volta in (None, "", "melhor", "best"):
        return min(vs, key=lambda x: x["lap_duration"])
    v = next((x for x in vs if x["lap_number"] == int(volta)), None)
    if v is None:
        raise SemDados(f"carro {num} sem tempo na volta {volta} da sessão {sk}")
    return v


def _tempo(sk: int, num: int, volta) -> tuple[float, str]:
    v = _volta(sk, num, volta)
    return float(v["lap_duration"]), f"volta {v['lap_number']}"


def _setor(sk: int, num: int, volta, setor: int) -> tuple[float, str]:
    v = _volta(sk, num, volta)
    t = v.get(f"duration_sector_{setor}")
    if not isinstance(t, (int, float)):
        raise SemDados(f"carro {num} sem o setor {setor} na volta {v['lap_number']}")
    return float(t), f"volta {v['lap_number']} setor {setor}"


def _resultado(sk: int, num: int | None = None) -> list[dict]:
    return _obter("session_result", session_key=sk, **({"driver_number": num} if num is not None else {}))


def calcular(pedido: dict, contexto: dict | None = None) -> tuple[float, str, str]:
    """(valor, unidade, de onde veio) recalculado do OpenF1 para o pedido."""
    tipo = pedido.get("tipo")
    if tipo not in TIPOS:
        raise SemDados(f"tipo '{tipo}' não é conferido pelo OpenF1")
    s = sessao(pedido, contexto)
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
    if tipo == "setor":
        if num is None or str(pedido.get("setor")) not in ("1", "2", "3"):
            raise SemDados("setor precisa de piloto e setor (1, 2 ou 3)")
        st = int(pedido["setor"])
        t1, q1 = _setor(sk, num, pedido.get("volta"), st)
        if pedido.get("piloto2") in (None, ""):
            return round(t1, 3), "s", f"{rot} /laps carro {num} {q1}"
        n2 = _piloto(sk, pedido["piloto2"])
        t2, q2 = _setor(sk, n2, pedido.get("volta2", pedido.get("volta")), st)
        return round(abs(t1 - t2), 3), "s", f"{rot} /laps carro {num} {q1} × carro {n2} {q2}"
    if tipo == "speed_trap":   # rodada 1 do "Nove milésimos": 350 × 347 é o st_speed, não a máxima da telemetria
        if num is None:
            raise SemDados("falta o piloto")
        v = _volta(sk, num, pedido.get("volta"))
        if not isinstance(v.get("st_speed"), (int, float)):
            raise SemDados(f"carro {num} sem speed trap na volta {v['lap_number']}")
        return float(v["st_speed"]), "km/h", f"{rot} /laps carro {num} volta {v['lap_number']} st_speed"
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


def conferir(pedido: dict, contexto: dict | None = None) -> dict:
    """Valor dito no roteiro × valor recalculado do OpenF1. `contexto` = sessão citada no roteiro (ver `sessao`)."""
    try:
        certo, unidade, fonte = calcular(pedido, contexto)
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


def fatos_da_sessao(pedido: dict, contexto: dict | None = None) -> list[tuple[str, str]]:
    """(fonte, texto) com os números da sessão para a pesquisa: resultado (top 10 + pilotos pedidos), melhor volta e
    pit stops dos pilotos pedidos. Sem dados (ano < 2023, sessão não achada): lista vazia. `contexto` = ver `sessao`."""
    try:
        s = sessao(pedido, contexto)
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
