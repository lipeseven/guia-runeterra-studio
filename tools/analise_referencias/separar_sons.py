"""Separa a narração do resto do áudio dos vídeos de referência (Demucs htdemucs, GPU, local).

O que sobra sem a voz (bateria/graves/outros) é onde estão os efeitos sonoros e a música de fundo.
Saída por vídeo: dados/runeterra/analise_referencias/<slug>/som/{drums,bass,other,vocals}.flac (mono 44,1 kHz).

    .venv\\Scripts\\python.exe tools\\analise_referencias\\separar_sons.py [trecho-do-nome]
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import RAIZ, preparar_ffmpeg  # noqa: E402

from detectar_cortes import slug  # noqa: E402

sys.path.insert(0, str(RAIZ / "tools"))
from canal import caminho  # noqa: E402  (pasta de referências DO CANAL: GRS_CANAL)

PASTA_VIDEOS = caminho("referencias")
PASTA_SAIDA = caminho("analise")
SR = 44100
BLOCO = 300  # segundos por vez (cabe folgado em 16 GB de RAM)


def decodificar(video: Path) -> np.ndarray:
    """Áudio estéreo float32 [2, n] a 44,1 kHz via FFmpeg."""
    preparar_ffmpeg()
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(bruto, dtype=np.float32).reshape(-1, 2).T.copy()


def separar(video: Path, modelo) -> Path:
    from demucs.apply import apply_model

    destino = PASTA_SAIDA / slug(video.stem) / "som"
    if (destino / "vocals.flac").exists():
        print("  já separado")
        return destino
    destino.mkdir(parents=True, exist_ok=True)
    audio = decodificar(video)
    nomes = modelo.sources  # ['drums', 'bass', 'other', 'vocals']
    saidas = {n: [] for n in nomes}  # vocals também: serve de referência de volume (efeito X dB abaixo da voz)
    for ini in range(0, audio.shape[1], BLOCO * SR):
        x = torch.from_numpy(audio[:, ini:ini + BLOCO * SR])
        ref = x.mean(0)
        media, desvio = ref.mean(), ref.std() + 1e-8
        with torch.no_grad():
            y = apply_model(modelo, ((x - media) / desvio)[None], device="cuda", shifts=0, overlap=0.25, progress=False)[0]
        y = y * desvio + media
        for k, n in enumerate(nomes):
            if n in saidas:
                saidas[n].append(y[k].mean(0).cpu().numpy())
    for n, partes in saidas.items():
        sf.write(destino / f"{n}.flac", np.concatenate(partes), SR)
    return destino


def main() -> None:
    from demucs.pretrained import get_model

    filtro = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    modelo = get_model("htdemucs").cuda().eval()
    videos = sorted(v for v in PASTA_VIDEOS.glob("*.mp4") if "teste_audio" not in v.name and filtro in v.name.lower())
    for n, v in enumerate(videos, 1):
        t = time.time()
        print(f"[{n}/{len(videos)}] {v.name}", flush=True)
        separar(v, modelo)
        print(f"  {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
