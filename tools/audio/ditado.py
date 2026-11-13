"""Ditado: transcreve um áudio curto (observação falada no painel) com o faster-whisper local, em PT-BR.

Roda num processo à parte (o servidor não carrega o modelo nem trava): imprime JSON em UTF-8 no stdout.
Mesmo modelo da limpeza da gravação (large-v3-turbo). GPU ocupada (render) ou sem CUDA → cai para a CPU (int8).

    .venv\\Scripts\\python.exe tools\\audio\\ditado.py <arquivo de áudio>   →  {"ok": true, "texto": "...", "dispositivo": "cuda"}
Aceita o que o FFmpeg decodifica (webm/opus do navegador, wav, mp3, m4a, ogg...).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MODELO = "large-v3-turbo"
_HUB = Path.home() / ".cache" / "huggingface" / "hub"
if (_HUB / "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo").exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# No Windows, as DLLs CUDA do pip (nvidia-cublas/cudnn) precisam estar no caminho (como em limpar_gravacao.py)
for _p in (Path(sys.prefix) / "Lib" / "site-packages" / "nvidia").glob("*/bin"):
    os.add_dll_directory(str(_p))
    os.environ["PATH"] = f"{_p}{os.pathsep}{os.environ['PATH']}"


def carregar_16k(arquivo: Path):
    """Áudio → float32 mono 16 kHz pelo FFmpeg (como a limpeza da gravação; o PyAV do faster-whisper não é usado)."""
    import numpy as np

    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arquivo), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode != 0:
        raise ValueError("áudio ilegível: " + r.stderr.decode("utf-8", "replace").strip()[-300:])
    a = np.frombuffer(r.stdout, np.float32).copy()
    if a.size < 1600:   # < 0,1 s
        raise ValueError("áudio vazio ou curto demais")
    return a


def transcrever(arquivo: Path) -> dict:
    from faster_whisper import WhisperModel

    audio = carregar_16k(arquivo)
    ultimo = None
    for dispositivo, tipo in (("cuda", "float16"), ("cpu", "int8")):
        try:
            modelo = WhisperModel(MODELO, device=dispositivo, compute_type=tipo)
            segs, info = modelo.transcribe(audio, language="pt", vad_filter=True, beam_size=5,
                                           condition_on_previous_text=False)
            texto = " ".join(s.text.strip() for s in segs).strip()
            return {"ok": True, "texto": texto, "dispositivo": dispositivo, "duracao": round(info.duration, 2)}
        except Exception as e:  # noqa: BLE001  (CUDA sem memória/ausente: tenta a CPU)
            ultimo = e
    raise RuntimeError(f"transcrição falhou: {type(ultimo).__name__}: {ultimo}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    try:
        r = transcrever(Path(sys.argv[1]))
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "erro": str(e)}
    sys.stdout.buffer.write(json.dumps(r, ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
