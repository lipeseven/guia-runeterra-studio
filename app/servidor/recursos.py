"""Estado real do PC e dos serviços, para o painel "Recursos"."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from .banco import RAIZ

_cache: dict[str, tuple[float, object]] = {}


def _memo(chave: str, segundos: float, fn):
    t, v = _cache.get(chave, (0.0, None))
    if time.time() - t > segundos:
        v = fn()
        _cache[chave] = (time.time(), v)
    return v


def gpu() -> dict:
    try:
        s = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
        nome, uso, usada, total, temp = [x.strip() for x in s.strip().split(",")]
        uso = int(uso)
        return {"ok": True, "nome": nome, "uso": uso, "vram_usada": int(usada), "vram_total": int(total),
                "temperatura": int(temp), "estado": "ocupada" if uso > 30 else "ociosa"}
    except Exception as e:  # sem driver / sem nvidia-smi
        return {"ok": False, "erro": str(e)}


def _tamanho(p: Path) -> int:
    total = 0
    for raiz, _, arquivos in os.walk(p):
        for a in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, a))
            except OSError:
                pass
    return total


def disco() -> dict:
    uso = shutil.disk_usage(RAIZ.anchor)
    def medir():
        return {"dados": _tamanho(RAIZ / "dados"), "projetos": _tamanho(RAIZ / "projetos") if (RAIZ / "projetos").exists() else 0}
    pastas = _memo("pastas", 60, medir)
    return {"livre": uso.free, "total": uso.total, **pastas}


def porta_aberta(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def servicos() -> list[dict]:
    from dotenv import dotenv_values

    env = dotenv_values(RAIZ / ".env")
    piper = RAIZ / "dados/modelos/piper/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx"
    whisper = Path.home() / ".cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo"
    return [
        {"nome": "Fish Audio", "papel": "voz guia", "estado": "pronto" if env.get("FISH_API_KEY") else "sem chave",
         "detalhe": "s2.1-pro-free · uso justo"},
        {"nome": "Piper", "papel": "voz guia (reserva local)", "estado": "pronto" if piper.exists() else "não instalado",
         "detalhe": "pt_BR-faber"},
        {"nome": "Whisper", "papel": "transcrição", "estado": "pronto" if whisper.exists() else "não baixado",
         "detalhe": "large-v3-turbo · GPU"},
        {"nome": "ComfyUI", "papel": "imagens por IA", "estado": "ligado" if porta_aberta(8188) else "não instalado",
         "detalhe": "Z-Image-Turbo"},
        {"nome": "Claude", "papel": "diretor", "estado": "via chat", "detalhe": "plano Pro · cota não medida ainda"},
    ]


def resumo() -> dict:
    return {"gpu": _memo("gpu", 3, gpu), "disco": disco(), "servicos": _memo("servicos", 10, servicos)}
