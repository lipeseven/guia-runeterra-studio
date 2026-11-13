# Relógio da sessão (OpenF1) x contador de voltas da transmissão.
#
# A transmissão mostra "LAP C/71" = volta do LÍDER, não a do piloto da afirmação. Por isso a volta do piloto vira uma
# JANELA no relógio da sessão (date_start .. date_start + lap_duration) e cada valor C do contador vira outra janela
# (primeiro carro a abrir a volta C .. primeiro a abrir a C+1). A imagem só bate se as janelas se cruzam.
from __future__ import annotations

from datetime import datetime, timezone


def ts(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()


def hora(t: float) -> str:
    """Hora UTC legível (HH:MM:SS) para a evidência."""
    return datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M:%S")


def inicios_lider(voltas: list[dict]) -> dict[int, float]:
    """Volta C -> instante em que o primeiro carro abriu a volta C (= quando o contador da TV passa a C)."""
    ini: dict[int, float] = {}
    for v in voltas:
        if v.get("date_start") and v.get("lap_number"):
            t = ts(v["date_start"])
            n = v["lap_number"]
            if n not in ini or t < ini[n]:
                ini[n] = t
    return ini


def fim_corrida(voltas: list[dict]) -> float | None:
    """Fim da última volta do líder (primeira bandeirada)."""
    ultimo = max((v["lap_number"] for v in voltas if v.get("lap_number")), default=None)
    fins = [ts(v["date_start"]) + v["lap_duration"] for v in voltas
            if v.get("lap_number") == ultimo and v.get("date_start") and v.get("lap_duration")]
    return min(fins) if fins else None


def total_voltas(voltas: list[dict]) -> int:
    return max((v["lap_number"] for v in voltas if v.get("lap_number")), default=0)


def janela_contador(c: int, voltas: list[dict]) -> tuple[float, float] | None:
    ini = inicios_lider(voltas)
    if c not in ini:
        return None
    fim = ini.get(c + 1) or fim_corrida(voltas) or ini[c] + 150.0
    return ini[c], fim


def contador_em(t: float, voltas: list[dict]) -> int:
    """Valor do contador da TV no instante t (0 antes da largada)."""
    ini = inicios_lider(voltas)
    return max((c for c, t0 in ini.items() if t0 <= t), default=0)


def janela_volta(voltas: list[dict], piloto: int, volta: int) -> tuple[float, float] | None:
    """Volta `volta` do piloto no relógio da sessão. None se o OpenF1 não tem essa volta."""
    por_n = {v["lap_number"]: v for v in voltas if v.get("driver_number") == piloto}
    v = por_n.get(volta)
    if not v or not v.get("date_start"):
        return None
    t0 = ts(v["date_start"])
    if v.get("lap_duration"):
        return t0, t0 + v["lap_duration"]
    prox = por_n.get(volta + 1)
    if prox and prox.get("date_start"):
        return t0, ts(prox["date_start"])
    return None


def cruzamento(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def contadores_esperados(janela: tuple[float, float], voltas: list[dict]) -> list[int]:
    """Valores do contador da TV que aparecem em algum momento da janela."""
    tot = total_voltas(voltas)
    return [c for c in range(1, tot + 1)
            if (jc := janela_contador(c, voltas)) and cruzamento(jc, janela) > 0]
