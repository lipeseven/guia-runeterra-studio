"""Briefing do vídeo: roteiro e instruções num arquivo só, em seções separadas por linhas de "=".

    ============
    1. ROTEIRO (texto falado)
    ============
    ...

Só a seção cujo título começa com ROTEIRO é narrada; o resto fica em direcao/briefing.json. O diretor lê o briefing
inteiro menos o roteiro, as fontes e os pontos para o Felipe decidir; a conferência usa as linhas dos fatos e do
"evitar" como anotação verificada deste vídeo. Roteiro sem seções = roteiro normal, sem briefing.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

TITULO = re.compile(r"^=+[ \t]*\n[ \t]*(?:\d+\.[ \t]*)?([^\n]+?)[ \t]*\n=+[ \t]*$", re.M)


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()


def separar(texto: str) -> tuple[str, dict | None]:
    """Texto recebido → (roteiro, briefing ou None). O briefing traz cabeçalho, seções e as linhas de fatos."""
    partes = TITULO.split(texto.replace("\r\n", "\n"))
    if len(partes) < 3:
        return texto, None
    secoes = [{"titulo": t.strip(), "texto": c.strip()} for t, c in zip(partes[1::2], partes[2::2])]
    roteiro = next((s for s in secoes if _norm(s["titulo"]).startswith("ROTEIRO")), None)
    if not roteiro or not roteiro["texto"]:
        return texto, None
    outras = [s for s in secoes if s is not roteiro]
    fatos = []
    for s in outras:
        tit = _norm(s["titulo"])
        if "FATOS" in tit or "EVITAR" in tit:
            prefixo = "Evitar: " if "EVITAR" in tit else ""
            fatos += [prefixo + x.strip()[2:].strip() for x in s["texto"].splitlines() if x.strip().startswith("- ")]
    return roteiro["texto"] + "\n", {"cabecalho": partes[0].strip(), "secoes": outras, "fatos": fatos}


def ler(dirc: Path) -> dict | None:
    arq = dirc / "briefing.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def para_o_diretor(dirc: Path) -> str:
    """Texto do briefing para o prompt do diretor ("" se o vídeo não tem briefing)."""
    b = ler(dirc)
    if not b:
        return ""
    fora = ("FONTES", "PONTOS")
    partes = [b["cabecalho"]] + [f"## {s['titulo']}\n{s['texto']}" for s in b["secoes"]
                                 if not _norm(s["titulo"]).startswith(fora)]
    return "\n\n".join(p for p in partes if p)
