# Leitura do OpenF1 (https://api.openf1.org/v1) com cache em disco (F1/dados/imagens/cache/openf1).
# Só o que o kit/imagens precisa: sessão, encontro (meeting), pilotos, voltas, race_control, pit, ultrapassagens.
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from caminhos import CACHE

BASE = "https://api.openf1.org/v1/"


def _get(rota: str, **params) -> list[dict]:
    q = urllib.parse.urlencode(params, safe="<>=")
    chave = (rota + "_" + q).replace("&", "_").replace("=", "-").replace("<", "lt").replace(">", "gt")
    arq = CACHE / "openf1" / (chave[:180] + ".json")
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    url = BASE + rota + ("?" + q if q else "")
    ultimo = None
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kit-imagens/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # limite de taxa (429) ou rede: espera e tenta de novo
            ultimo = e
            time.sleep(2 + 3 * tentativa)
    else:
        raise RuntimeError(f"OpenF1 falhou em {url}: {ultimo}")
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def sessao(session_key: int) -> dict:
    s = _get("sessions", session_key=session_key)
    if not s:
        raise ValueError(f"sessão {session_key} não existe no OpenF1")
    s = dict(s[0])
    m = _get("meetings", meeting_key=s["meeting_key"])
    if m:
        s["meeting_name"] = m[0].get("meeting_name")
        s["meeting_official_name"] = m[0].get("meeting_official_name")
    return s


def pilotos(session_key: int) -> dict[int, dict]:
    return {d["driver_number"]: d for d in _get("drivers", session_key=session_key)}


def voltas(session_key: int) -> list[dict]:
    return _get("laps", session_key=session_key)


def race_control(session_key: int) -> list[dict]:
    return _get("race_control", session_key=session_key)


def pit(session_key: int) -> list[dict]:
    return _get("pit", session_key=session_key)


def ultrapassagens(session_key: int) -> list[dict]:
    try:
        return _get("overtakes", session_key=session_key)
    except RuntimeError:
        return []


def pacote(session_key: int) -> dict:
    """Tudo que a validação usa, num dicionário só (é o mesmo formato da fixture dos testes)."""
    return {
        "sessao": sessao(session_key),
        "pilotos": {str(k): v for k, v in pilotos(session_key).items()},
        "voltas": [
            {k: v[k] for k in ("driver_number", "lap_number", "date_start", "lap_duration")}
            for v in voltas(session_key)
        ],
        "race_control": race_control(session_key),
        "pit": pit(session_key),
        "ultrapassagens": ultrapassagens(session_key),
    }
