"""Transcreve a narração dos vídeos de referência com faster-whisper (GPU).

Uso:
    .venv\\Scripts\\python.exe tools\\analise_referencias\\transcrever.py

Para cada vídeo, cria em dados/runeterra/analise_referencias/<slug>/:
    transcricao.json -> segmentos com o tempo de cada palavra
    transcricao.txt  -> texto corrido com marcação de tempo por segmento
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# No Windows, as DLLs CUDA instaladas pelo pip (nvidia-cublas/cudnn) precisam
# entrar no caminho de busca antes de carregar o ctranslate2.
for pacote in (Path(sys.prefix) / "Lib" / "site-packages" / "nvidia").glob("*/bin"):
    os.add_dll_directory(str(pacote))
    os.environ["PATH"] = f"{pacote}{os.pathsep}{os.environ['PATH']}"

import subprocess  # noqa: E402

import numpy as np  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from detectar_cortes import PASTA_SAIDA, PASTA_VIDEOS, slug, tempo  # noqa: E402


def carregar_audio(video: Path) -> np.ndarray:
    """Decodifica o áudio com FFmpeg (16 kHz mono), sem depender do PyAV."""
    bruto = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(bruto, np.int16).astype(np.float32) / 32768.0


def main() -> None:
    modelo = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    for video in sorted(PASTA_VIDEOS.glob("*.mp4")):
        destino = PASTA_SAIDA / slug(video.stem)
        destino.mkdir(parents=True, exist_ok=True)
        if (destino / "transcricao.json").exists():
            print(f"{video.name}: já transcrito, pulando", flush=True)
            continue

        t0 = time.time()
        segmentos, info = modelo.transcribe(
            carregar_audio(video), word_timestamps=True, vad_filter=True)  # idioma detectado
        dados, linhas = [], []
        for s in segmentos:
            dados.append({
                "inicio": round(s.start, 3), "fim": round(s.end, 3), "texto": s.text.strip(),
                "palavras": [{"p": w.word.strip(), "i": round(w.start, 3), "f": round(w.end, 3)}
                             for w in (s.words or [])],
            })
            linhas.append(f"[{tempo(s.start)}] {s.text.strip()}")

        (destino / "transcricao.json").write_text(
            json.dumps({"video": video.name, "segmentos": dados}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        (destino / "transcricao.txt").write_text("\n".join(linhas), encoding="utf-8")
        print(f"{video.name}: {len(dados)} segmentos em {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
