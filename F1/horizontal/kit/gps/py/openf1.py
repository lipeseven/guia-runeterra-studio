# Baixa e guarda em cache (kit/gps/cache/, fora do Git) os dados do OpenF1 que o kit/gps usa.
# Uso direto: python openf1.py <session_key> <driver_number> [<driver_number> ...]
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.openf1.org/v1/"
CACHE = Path(__file__).resolve().parent.parent / "cache"


def obter(endpoint, **params):
    """GET no OpenF1 com cache em disco (cache/<sessao>/<endpoint>_<params>.json)."""
    sessao = str(params.get("session_key", "geral"))
    chave = "_".join(f"{k}-{v}" for k, v in sorted(params.items()) if k != "session_key") or "tudo"
    arq = CACHE / sessao / f"{endpoint}_{chave}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    for tentativa in range(5):
        r = requests.get(BASE + endpoint, params=params, timeout=120)
        if r.status_code == 200:
            dados = r.json()
            arq.parent.mkdir(parents=True, exist_ok=True)
            arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            return dados
        time.sleep(2 + 3 * tentativa)  # 429 (limite) ou erro temporário
    r.raise_for_status()


def voltas(sessao, piloto):
    return sorted(obter("laps", session_key=sessao, driver_number=piloto), key=lambda v: v["lap_number"])


def localizacao(sessao, piloto):
    """Todas as posições x, y, z (~3,7 Hz) do piloto na sessão, ordenadas por data."""
    return sorted(obter("location", session_key=sessao, driver_number=piloto), key=lambda r: r["date"])


def pilotos(sessao):
    return obter("drivers", session_key=sessao)


def sessao_info(sessao):
    return obter("sessions", session_key=sessao)[0]


if __name__ == "__main__":
    s = int(sys.argv[1])
    print(sessao_info(s)["session_name"], len(pilotos(s)), "pilotos")
    for p in sys.argv[2:]:
        print(p, len(voltas(s, int(p))), "voltas", len(localizacao(s, int(p))), "posições")
