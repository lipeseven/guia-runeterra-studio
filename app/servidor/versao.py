"""Que código o painel está rodando (uso real, 2026-11-14).

O 1º card documental de verdade saiu com as etapas antigas (Narração `voz_ia`, sem voz guia) porque a pasta principal
estava parada no PR #108 (antes da fase 7a), com os PRs #109–#111 já mesclados no GitHub, e o servidor tinha subido
desse código. Nada no painel avisava. Aqui: ao subir, o servidor guarda o commit que carregou e compara com o
`origin/main` conhecido localmente (sem rede: vale o último fetch/pull); `/api/canal` devolve o aviso e o quadro mostra.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .banco import RAIZ


def _git(raiz: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, encoding="utf-8", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def estado(raiz: Path = RAIZ, carregado: str | None = None) -> dict:
    """{"commit", "ramo", "atras" (commits do origin/main que a pasta não tem; só no ramo main), "ultimo" (assunto do
    commit mais novo do origin/main), "reiniciar" (a pasta mudou depois que o servidor subiu), "aviso"}."""
    commit = _git(raiz, "rev-parse", "HEAD")
    ramo = _git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
    if commit is None:
        return {"commit": None, "ramo": None, "atras": 0, "reiniciar": False, "aviso": None}
    atras, ultimo = 0, None
    if ramo == "main" and _git(raiz, "rev-parse", "--verify", "--quiet", "origin/main"):
        atras = int(_git(raiz, "rev-list", "--count", "HEAD..origin/main") or 0)
        ultimo = _git(raiz, "log", "-1", "--format=%s", "origin/main") if atras else None
    reiniciar = bool(carregado and carregado != commit)
    avisos = []
    if atras:
        avisos.append(f"A pasta do sistema está {atras} commit(s) atrás do GitHub (origin/main: “{ultimo}”): "
                      "atualize (git pull) e reinicie o painel, senão cards novos saem no fluxo antigo.")
    if reiniciar:
        avisos.append("O código mudou depois que o painel subiu: reinicie o painel para usar a versão nova.")
    return {"commit": commit[:7], "ramo": ramo, "atras": atras, "ultimo": ultimo, "reiniciar": reiniciar,
            "aviso": " ".join(avisos) or None}


CARREGADO = _git(RAIZ, "rev-parse", "HEAD")   # o commit de quando este processo importou o código
_cache: dict = {"t": 0.0, "v": None}


def atual() -> dict:
    """`estado` do servidor em execução, guardado por 60 s (o quadro chama a cada abertura)."""
    if _cache["v"] is None or time.monotonic() - _cache["t"] > 60:
        _cache.update(t=time.monotonic(), v=estado(RAIZ, CARREGADO))
    return _cache["v"]
