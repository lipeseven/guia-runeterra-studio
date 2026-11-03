"""Música de fundo gerada no PC (Stable Audio Open, o mesmo dos efeitos; licença Stability Community: uso comercial ok
abaixo de US$ 1 mi/ano de receita). O modelo gera até ~47 s: um trecho de 44 s vira laço com emenda suave (cross-fade
de potência constante) até cobrir o vídeo. A mixagem (volume baixo e "ducking" sob a voz) fica em vertical.py.

    .venv\\Scripts\\python.exe tools\\audio\\trilha.py "calm electronic, soft pads" 95 saida.wav
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TRECHO = 44.0  # segundos gerados de uma vez (o limite do modelo é ~47 s)
EMENDA = 3.0  # segundos de cross-fade em cada volta do laço


def _laco(trecho: np.ndarray, sr: int, segundos: float) -> np.ndarray:
    """Repete o trecho com cross-fade de potência constante até passar de `segundos`."""
    cf = int(EMENDA * sr)
    t = np.linspace(0, np.pi / 2, cf)[:, None]
    sai, entra = np.cos(t), np.sin(t)
    saida = trecho.copy()
    while len(saida) < segundos * sr:
        saida = np.concatenate([saida[:-cf], saida[-cf:] * sai + trecho[:cf] * entra, trecho[cf:]])
    return saida[: int(segundos * sr)]


def gerar(descricao: str, segundos: float, destino: Path, semente: int = 7) -> Path:
    """Gera a trilha (instrumental, sem voz) com pelo menos `segundos` e grava em `destino` (.wav estéreo)."""
    from sfx import Gerador

    g = Gerador()
    try:
        prompt = f"{descricao}, background music, instrumental, smooth and pleasant, steady, warm mix, soft percussion, no hi-hats, no vocals, high quality"
        a = g.pipe(prompt, negative_prompt="vocals, voice, speech, singing, hi-hats, cymbals, harsh treble, hiss, distorted, noise, low quality",
                   num_inference_steps=100, audio_end_in_s=TRECHO,
                   generator=g.torch.Generator("cuda").manual_seed(semente)).audios[0]
        sr = g.pipe.vae.sampling_rate
        trecho = a.float().cpu().numpy().T  # (amostras, 2)
    finally:
        g.liberar()
    trecho = trecho[int(0.2 * sr):]  # o começo do modelo costuma vir com um "ataque"; tira um pedacinho
    pico = float(np.abs(trecho).max()) or 1.0
    trecho = trecho * (10 ** (-3 / 20) / pico)
    musica = _laco(trecho, sr, segundos)
    destino.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destino, musica.astype(np.float32), sr)
    return destino


if __name__ == "__main__":
    print(gerar(sys.argv[1], float(sys.argv[2]), Path(sys.argv[3])))
