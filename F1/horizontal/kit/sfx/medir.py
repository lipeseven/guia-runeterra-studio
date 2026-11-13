# Medidas e E/S de áudio do kit de SFX (sem dependências além de numpy/scipy e do ffmpeg do PATH).
# Loudness pela ITU-R BS.1770-4 (filtro K a 48 kHz, blocos de 400 ms): integrado (com portas -70/-10) e
# momentâneo máximo (M-máx), que é a medida usada para normalizar efeitos curtos. Pico verdadeiro com 4x de
# sobreamostragem. Tudo trabalha em float32, 48 kHz, estéreo (n, 2).
from __future__ import annotations

import subprocess
import wave

import numpy as np
from scipy.signal import lfilter, resample_poly

SR = 48000

# Coeficientes do filtro K (BS.1770-4) para 48 kHz: prateleira de agudos + passa-altas RLB.
_K1_B = [1.53512485958697, -2.69169618940638, 1.19839281085285]
_K1_A = [1.0, -1.69065929318241, 0.73248077421585]
_K2_B = [1.0, -2.0, 1.0]
_K2_A = [1.0, -1.99004745483398, 0.99007225036621]


def ler(caminho: str) -> np.ndarray:
    """Decodifica qualquer arquivo (wav/mp3/ogg) com o ffmpeg para float32 48 kHz estéreo (n, 2)."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(caminho), "-f", "f32le", "-acodec", "pcm_f32le",
           "-ac", "2", "-ar", str(SR), "-"]
    bruto = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(bruto, dtype="<f4").reshape(-1, 2).astype(np.float32).copy()


def gravar(caminho: str, x: np.ndarray, semente: int = 0) -> None:
    """Grava WAV PCM 16 bits 48 kHz estéreo, com dither TPDF determinístico."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    rng = np.random.default_rng(semente)
    lsb = 1.0 / 32768.0
    d = (rng.random(x.shape) - rng.random(x.shape)) * lsb
    q = np.clip(np.round((x + d) * 32767.0), -32767, 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(q.tobytes())


def _kfiltro(x: np.ndarray) -> np.ndarray:
    y = lfilter(_K1_B, _K1_A, x, axis=0)
    return lfilter(_K2_B, _K2_A, y, axis=0)


def _blocos(x: np.ndarray, passo_s: float = 0.1) -> np.ndarray:
    """Loudness (LUFS) de cada bloco de 400 ms. Áudio mais curto que 400 ms é completado com silêncio,
    como faria um medidor real."""
    n400 = int(0.4 * SR)
    if len(x) < n400:
        x = np.concatenate([x, np.zeros((n400 - len(x), x.shape[1]), x.dtype)])
    y = _kfiltro(x.astype(np.float64)) ** 2
    acum = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y, 0)])
    passo = max(1, int(passo_s * SR))
    ini = np.arange(0, len(y) - n400 + 1, passo)
    ms = (acum[ini + n400] - acum[ini]) / n400          # média quadrática por canal
    soma = ms.sum(1)                                      # G = 1 para L e R
    with np.errstate(divide="ignore"):
        return -0.691 + 10 * np.log10(np.maximum(soma, 1e-20))


def lufs_integrado(x: np.ndarray) -> float:
    lb = _blocos(x, 0.1)
    lb = lb[lb > -70]
    if not len(lb):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(10 ** ((lb + 0.691) / 10))) - 10
    lb = lb[lb > rel]
    return float(-0.691 + 10 * np.log10(np.mean(10 ** ((lb + 0.691) / 10))))


def lufs_m_max(x: np.ndarray) -> float:
    """Loudness momentânea máxima (janela de 400 ms, passo de 10 ms)."""
    return float(_blocos(x, 0.01).max())


def pico_verdadeiro_db(x: np.ndarray) -> float:
    up = resample_poly(x.astype(np.float64), 4, 1, axis=0)
    p = max(float(np.abs(up).max()), float(np.abs(x).max()))
    return 20 * np.log10(max(p, 1e-12))


def pico_amostra_db(x: np.ndarray) -> float:
    return 20 * np.log10(max(float(np.abs(x).max()), 1e-12))


def lufs_canais(x: np.ndarray) -> tuple[float, float]:
    """M-máx de cada canal isolado (para conferir que o estéreo não está vazio nem desequilibrado)."""
    return (lufs_m_max(np.stack([x[:, 0], np.zeros(len(x))], 1)),
            lufs_m_max(np.stack([np.zeros(len(x)), x[:, 1]], 1)))


def envelope(x: np.ndarray, janela_s: float = 0.01) -> np.ndarray:
    """Envelope RMS (mono) em janelas de 10 ms."""
    m = (x.astype(np.float64) ** 2).mean(1)
    n = max(1, int(janela_s * SR))
    k = len(m) // n
    return np.sqrt(m[: k * n].reshape(k, n).mean(1) + 1e-20)


def limitar(x: np.ndarray, teto_db: float = -1.5, antecipa_s: float = 0.003, solta_s: float = 0.06) -> np.ndarray:
    """Limitador simples com antecipação: ganho = min(1, teto/|x|) espalhado para trás pela antecipação e
    suavizado na soltura. Garante que nenhuma amostra passe do teto (o pico verdadeiro fica ~0,3 dB acima)."""
    teto = 10 ** (teto_db / 20)
    a = np.abs(x).max(1)
    g = np.minimum(1.0, teto / np.maximum(a, 1e-12))
    if g.min() >= 1.0:
        return x
    n = max(1, int(antecipa_s * SR))
    # mínimo móvel para trás (antecipação)
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(g, size=2 * n + 1, mode="nearest")
    # soltura: o ganho só volta a subir devagar
    coef = np.exp(-1.0 / (solta_s * SR))
    out = np.empty_like(g)
    cur = 1.0
    for i, v in enumerate(g):  # laço curto: efeitos têm poucos segundos
        cur = v if v < cur else v + (cur - v) * coef
        out[i] = cur
    y = x * out[:, None]
    return np.clip(y, -teto, teto)
