# Síntese procedural dos SFX do kit (numpy puro, determinística por semente; nada de amostras de terceiros).
# Cada função devolve float64 (n, 2) a 48 kHz, ainda sem normalização (o gerar.py normaliza por categoria).
# O riser "ruido_trilha" reproduz o riser da trilha sintetizada do teste Remotion (tools/trilha.py), elogiado
# pelo Felipe em ~16–17 s e ~47–48 s junto com o whoosh/impacto do capítulo.
from __future__ import annotations

import numpy as np

SR = 48000


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _est(m: np.ndarray, l: float = 1.0, r: float = 1.0) -> np.ndarray:
    return np.stack([m * l, m * r], 1)


def _svf(x: np.ndarray, fc: np.ndarray, q: float, modo: str = "bp") -> np.ndarray:
    """Filtro de estado variável (Chamberlin) com frequência variando por amostra."""
    y = np.empty_like(x)
    low = band = 0.0
    damp = 1.0 / q
    f = 2 * np.sin(np.pi * np.clip(fc, 20, SR / 6) / SR)
    for i in range(len(x)):
        high = x[i] - low - damp * band
        band += f[i] * high
        low += f[i] * band
        y[i] = band if modo == "bp" else (low if modo == "lp" else high)
    return y


def _fade(x: np.ndarray, ini_s: float = 0.002, fim_s: float = 0.02) -> np.ndarray:
    n = len(x)
    a, b = min(n, int(ini_s * SR)), min(n, int(fim_s * SR))
    e = np.ones(n)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if b:
        e[n - b:] *= np.linspace(1, 0, b)
    return x * (e[:, None] if x.ndim == 2 else e)


# ---------------------------------------------------------------- riser / crescendo (pico no FIM)
def riser_ruido_trilha(semente: int, dur: float = 1.5) -> np.ndarray:
    """Igual ao riser da trilha do teste Remotion: ruído suavizado (média de 6) com envelope t²."""
    rng = np.random.default_rng(semente)
    n = int(dur * SR)
    tt = np.linspace(0, 1, n)
    canais = []
    for _ in range(2):
        z = np.convolve(rng.standard_normal(n), np.ones(6) / 6, mode="same")
        canais.append(z * tt ** 2)
    return _fade(np.stack(canais, 1), 0.01, 0.006)


def riser_varredura(semente: int, dur: float = 2.4) -> np.ndarray:
    """Ruído com passa-banda subindo de 300 Hz a 7 kHz e volume em t^2.5 (crescendo de capítulo)."""
    rng = np.random.default_rng(semente)
    t = _t(dur)
    u = t / dur
    fc = 300 * (7000 / 300) ** (u ** 1.3)
    canais = [_svf(rng.standard_normal(len(t)), fc, 2.5) * u ** 2.5 for _ in range(2)]
    return _fade(np.stack(canais, 1), 0.02, 0.01)


def riser_tonal(semente: int, dur: float = 2.0) -> np.ndarray:
    """Acorde (lá menor) subindo uma oitava em glissando + ruído fino; pico no fim."""
    rng = np.random.default_rng(semente)
    t = _t(dur)
    u = t / dur
    sobe = 2 ** (u ** 2)  # uma oitava
    s = np.zeros((len(t), 2))
    for k, f in enumerate((220.0, 261.63, 329.63, 440.0)):
        for c, det in ((0, -0.004), (1, 0.004)):
            fase = 2 * np.pi * np.cumsum(f * (1 + det) * sobe) / SR + k
            s[:, c] += np.tanh(1.8 * np.sin(fase)) * 0.25
    z = np.convolve(rng.standard_normal(len(t)), np.ones(3) / 3, mode="same")
    s += _est(z * 0.15 * u ** 3)
    return _fade(s * (u ** 2)[:, None], 0.02, 0.008)


def riser_shepard(semente: int, dur: float = 3.0) -> np.ndarray:
    """Ilusão de Shepard curta: senos espaçados em oitava subindo, com volume em crescendo."""
    t = _t(dur)
    u = t / dur
    s = np.zeros((len(t), 2))
    for k in range(6):
        pos = (k / 6 + u * 0.5) % 1.0                    # posição na janela de 6 oitavas
        f = 55 * 2 ** (6 * pos)
        peso = np.sin(np.pi * pos) ** 2                   # some nas pontas
        fase = 2 * np.pi * np.cumsum(f) / SR
        s[:, 0] += np.sin(fase) * peso
        s[:, 1] += np.sin(fase + 0.6) * peso
    return _fade(s * (u ** 1.8)[:, None], 0.02, 0.008)


def riser_prato_reverso(semente: int, dur: float = 1.3) -> np.ndarray:
    """Prato invertido: ruído agudo com decaimento exponencial tocado ao contrário."""
    rng = np.random.default_rng(semente)
    t = _t(dur)
    canais = []
    for _ in range(2):
        z = rng.standard_normal(len(t))
        z = np.diff(np.concatenate([[0.0], z]))            # passa-altas simples
        z = _svf(z, np.full(len(t), 7000.0), 0.9, "bp") + z * 0.3
        canais.append((z * np.exp(-t * 3.2))[::-1])
    return _fade(np.stack(canais, 1), 0.01, 0.004)


# ---------------------------------------------------------------- impacto
def impacto_sub(semente: int, f0: float = 62.0, dur: float = 1.8) -> np.ndarray:
    """Boom grave (seno de f0 caindo para 0,55·f0) + estalo de ruído filtrado no ataque."""
    rng = np.random.default_rng(semente)
    t = _t(dur)
    f = f0 * (0.55 + 0.45 * np.exp(-t * 6))
    boom = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 2.6)
    ruido = _svf(rng.standard_normal(len(t)), np.full(len(t), 900.0), 0.8, "lp") * np.exp(-t * 18) * 0.9
    clic = rng.standard_normal(len(t)) * np.exp(-t * 300) * 0.5
    m = boom + ruido + clic
    return _fade(np.stack([m, m * 0.97 + clic * 0.1], 1), 0.0005, 0.15)


# ---------------------------------------------------------------- clique / tecla
def clique(semente: int, f: float = 3200.0) -> np.ndarray:
    """Clique seco de interface: rajada de ruído de 4 ms + ressonância curta em f."""
    rng = np.random.default_rng(semente)
    t = _t(0.12)
    z = rng.standard_normal(len(t)) * np.exp(-t * 900)
    tom = np.sin(2 * np.pi * f * t) * np.exp(-t * 180) * 0.6
    m = _svf(z, np.full(len(t), f), 3.0) + tom
    return _fade(_est(m, 1.0, 0.92), 0.0002, 0.01)


def tecla(semente: int, grave: float = 210.0, solta_ms: float = 75.0) -> np.ndarray:
    """Tecla mecânica: batida (ruído 1,5–4 kHz + 'toc' grave) e soltura mais fraca solta_ms depois."""
    rng = np.random.default_rng(semente)
    t = _t(0.22)
    m = np.zeros(len(t))
    for atraso, ganho in ((0.0, 1.0), (solta_ms / 1000, 0.45)):
        tt = np.clip(t - atraso, 0, None)
        on = (t >= atraso).astype(float)
        z = rng.standard_normal(len(t)) * np.exp(-tt * 700) * on
        m += _svf(z, np.full(len(t), 2600.0), 1.6) * ganho
        m += np.sin(2 * np.pi * grave * tt) * np.exp(-tt * 90) * on * 0.5 * ganho
    return _fade(_est(m, 0.95, 1.0), 0.0002, 0.015)


# ---------------------------------------------------------------- sino
def sino_fm(semente: int, f: float = 1760.0, razao: float = 3.5, indice: float = 2.5,
            dur: float = 2.2, decai: float = 2.2, segunda: float | None = None) -> np.ndarray:
    """Sino por FM (carrier f, modulador f·razão, índice decaindo). 'segunda' toca outra nota 120 ms depois."""
    t = _t(dur)
    def nota(fr: float, atraso: float) -> np.ndarray:
        tt = np.clip(t - atraso, 0, None)
        on = (t >= atraso).astype(float)
        idx = indice * np.exp(-tt * 4)
        s = np.sin(2 * np.pi * fr * tt + idx * np.sin(2 * np.pi * fr * razao * tt))
        return s * np.exp(-tt * decai) * on * np.minimum(1, tt / 0.002)
    m = nota(f, 0.0)
    if segunda:
        m = m * 0.8 + nota(segunda, 0.12) * 0.8
    return _fade(np.stack([m, np.roll(m, 24) * 0.95], 1), 0.0005, 0.3)


# ---------------------------------------------------------------- pop
def pop(semente: int, f_ini: float = 900.0, f_fim: float = 280.0, dur: float = 0.18) -> np.ndarray:
    """Pop de bolha: seno com queda rápida de afinação e decaimento curto."""
    t = _t(dur)
    f = f_fim + (f_ini - f_fim) * np.exp(-t * 90)
    m = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    rng = np.random.default_rng(semente)
    m += rng.standard_normal(len(t)) * np.exp(-t * 900) * 0.15
    return _fade(_est(m), 0.0005, 0.02)


# ---------------------------------------------------------------- whoosh (pico no MEIO)
def whoosh(semente: int, dur: float = 0.9, f_lo: float = 400.0, f_hi: float = 3500.0) -> np.ndarray:
    """Ruído com passa-banda subindo e descendo e envelope em sino, atravessando da esquerda para a direita."""
    rng = np.random.default_rng(semente)
    t = _t(dur)
    u = t / dur
    forma = np.sin(np.pi * u) ** 2
    fc = f_lo + (f_hi - f_lo) * forma
    m = _svf(_svf(rng.standard_normal(len(t)), fc, 2.0), fc, 2.0) * forma   # dois estágios: banda estreita, "ar"
    pan = u  # 0 = esquerda, 1 = direita
    return _fade(np.stack([m * np.cos(pan * np.pi / 2), m * np.sin(pan * np.pi / 2)], 1) * 1.4, 0.005, 0.02)


# ---------------------------------------------------------------- alerta
def bipes(semente: int, f: float = 1000.0, n: int = 2, liga_ms: float = 80, pausa_ms: float = 60,
          f2: float | None = None) -> np.ndarray:
    """Bipes de rádio/telemetria (onda quase quadrada suavizada). f2 alterna a nota (sirene curta)."""
    total = n * (liga_ms + pausa_ms) / 1000 + 0.05
    t = _t(total)
    m = np.zeros(len(t))
    for k in range(n):
        a = k * (liga_ms + pausa_ms) / 1000
        fr = f2 if (f2 and k % 2) else f
        on = ((t >= a) & (t < a + liga_ms / 1000)).astype(float)
        env = np.convolve(on, np.ones(96) / 96, mode="same")   # rampas de 2 ms
        m += np.tanh(3 * np.sin(2 * np.pi * fr * t)) * env
    return _fade(_est(m * 0.8), 0.001, 0.01)


# Receitas do banco (nome -> categoria, função, parâmetros). As sementes são fixas: regerar dá o mesmo arquivo.
RECEITAS: dict[str, tuple[str, callable, dict]] = {
    "riser_trilha_remotion": ("riser", riser_ruido_trilha, {"semente": 7, "dur": 1.5}),
    "riser_varredura": ("riser", riser_varredura, {"semente": 11}),
    "riser_tonal": ("riser", riser_tonal, {"semente": 12}),
    "riser_shepard": ("riser", riser_shepard, {"semente": 13}),
    "riser_prato_reverso": ("riser", riser_prato_reverso, {"semente": 14}),
    "impacto_sub_grave": ("impacto", impacto_sub, {"semente": 21, "f0": 58.0}),
    "impacto_sub_seco": ("impacto", impacto_sub, {"semente": 22, "f0": 75.0, "dur": 1.0}),
    "clique_sint_agudo": ("clique", clique, {"semente": 31, "f": 3600.0}),
    "clique_sint_medio": ("clique", clique, {"semente": 32, "f": 2200.0}),
    "tecla_sint_1": ("tecla", tecla, {"semente": 41, "grave": 210.0, "solta_ms": 75}),
    "tecla_sint_2": ("tecla", tecla, {"semente": 42, "grave": 180.0, "solta_ms": 95}),
    "tecla_sint_3": ("tecla", tecla, {"semente": 43, "grave": 240.0, "solta_ms": 60}),
    "sino_ping_agudo": ("sino", sino_fm, {"semente": 51, "f": 1760.0, "razao": 3.5, "indice": 2.0}),
    "sino_carrilhao_duplo": ("sino", sino_fm, {"semente": 52, "f": 1318.5, "razao": 2.0, "indice": 1.5, "segunda": 1975.5}),
    "sino_vidro": ("sino", sino_fm, {"semente": 53, "f": 2637.0, "razao": 1.41, "indice": 1.2, "dur": 1.6, "decai": 3.0}),
    "sino_suave": ("sino", sino_fm, {"semente": 54, "f": 1046.5, "razao": 2.0, "indice": 0.8, "dur": 2.5, "decai": 1.8}),
    "pop_sint_bolha": ("pop", pop, {"semente": 61}),
    "pop_sint_grave": ("pop", pop, {"semente": 62, "f_ini": 600.0, "f_fim": 160.0, "dur": 0.22}),
    "whoosh_sint_curto": ("whoosh", whoosh, {"semente": 71, "dur": 0.6}),
    "whoosh_sint_largo": ("whoosh", whoosh, {"semente": 72, "dur": 1.2, "f_lo": 250.0, "f_hi": 2400.0}),
    "alerta_radio_duplo": ("alerta", bipes, {"semente": 81, "f": 1000.0, "n": 2}),
    "alerta_triplo_grave": ("alerta", bipes, {"semente": 82, "f": 620.0, "n": 3, "liga_ms": 110, "pausa_ms": 70}),
    "alerta_dois_tons": ("alerta", bipes, {"semente": 83, "f": 880.0, "f2": 660.0, "n": 4, "liga_ms": 120, "pausa_ms": 20}),
}
