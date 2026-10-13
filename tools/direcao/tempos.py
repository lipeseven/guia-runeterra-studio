"""Tempos de cada palavra do roteiro numa narração (voz guia ou gravação limpa), com cache."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audio"))
from alinhar import alinhar  # noqa: E402
from limpar_gravacao import carregar, transcrever  # noqa: E402


def tempos_da_narracao(audio: Path, roteiro: str, cache: Path) -> list[dict]:
    if cache.exists() and cache.stat().st_mtime > audio.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    falas = transcrever(carregar(audio))
    palavras = alinhar(roteiro, [w for f in falas for w in f["palavras"]])
    cache.write_text(json.dumps(palavras, ensure_ascii=False, indent=1), encoding="utf-8")
    return palavras
