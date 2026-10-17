"""Tempos de cada palavra do roteiro numa narração (voz guia ou gravação limpa), com cache."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audio"))
from alinhar import alinhar  # noqa: E402
from limpar_gravacao import carregar, transcrever  # noqa: E402


def manter_tempos_dos_paragrafos_iguais(palavras: list[dict], roteiro: str, cache: Path) -> list[dict]:
    """Roteiro editado: os parágrafos ANTES da primeira mudança têm o mesmo áudio (voz guia em cache por parágrafo,
    mesma aceleração), então ficam com os tempos da versão anterior — o Whisper rodado de novo varia uns
    centésimos e isso obrigaria a renderizar de novo capítulos que não mudaram. Versão anterior: a última arquivada
    em direcao/anteriores/."""
    import re

    arquivadas = sorted(cache.parent.glob(f"anteriores/*/{cache.name}"))
    if not arquivadas:
        return palavras
    velhas = json.loads(arquivadas[-1].read_text(encoding="utf-8"))
    inicio, iguais = 0, 0
    for par in [p for p in re.split(r"\n\s*\n", roteiro) if p.strip()]:
        n = len(par.split())
        fim = inicio + n
        if fim > len(velhas) or [w["t"] for w in velhas[inicio:fim]] != [w["t"] for w in palavras[inicio:fim]]:
            break
        iguais, inicio = fim, fim
    if iguais:
        palavras = velhas[:iguais] + palavras[iguais:]
    return palavras


def tempos_da_narracao(audio: Path, roteiro: str, cache: Path) -> list[dict]:
    if cache.exists() and cache.stat().st_mtime > audio.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    falas = transcrever(carregar(audio))
    palavras = alinhar(roteiro, [w for f in falas for w in f["palavras"]])
    palavras = manter_tempos_dos_paragrafos_iguais(palavras, roteiro, cache)
    cache.write_text(json.dumps(palavras, ensure_ascii=False, indent=1), encoding="utf-8")
    return palavras
