"""Fase C: SFX do kit/sfx (Banco, mesma escolha determinística) + trilha leve sintetizada aqui (numpy, sem licença de terceiros).
Saídas em oficina/video: _tmp/sfx.wav, _tmp/trilha.wav, _tmp/audio.wav e CREDITOS.md. Rodar com python -B (não grava __pycache__ no kit)."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[4]
sys.path.insert(0, str(RAIZ / "F1/horizontal/kit/sfx"))
import medir  # noqa: E402
from sfx import Banco, mixar  # noqa: E402

OF = RAIZ / "dados/comum/oficina_craft/biblioteca/catalogo_horizontal/video"
SR = medir.SR
plano = json.loads((AQUI / "plano.json").read_text(encoding="utf-8"))
fps = plano["fps"]
quadros = [round(t["dur"] * fps) for t in plano["trechos"]]
ini = np.concatenate([[0], np.cumsum(quadros)[:-1]]) / fps
DUR = sum(quadros) / fps

# ---------------------------------------------------------------- SFX
banco = Banco(semente=7)
ev = []
for t0, tr in zip(ini, plano["trechos"]):
    for cat, t, k in tr.get("sfx", []):
        if cat == "capitulo":
            ev += banco.capitulo(t0 + t, k)
        else:
            ev.append(banco.para(cat, t0 + t, k))
sfx = mixar(ev, DUR, limitar=False)

# ---------------------------------------------------------------- trilha (Am F C G, 96 BPM, pad + baixo + arpejo + pulso leve)
n = int(round(DUR * SR))
tt = np.arange(n) / SR
BAR = 60 / 96 * 4
ACORDES = [([57, 60, 64, 69], 45), ([53, 57, 60, 65], 41), ([55, 60, 64, 67], 48), ([55, 59, 62, 67], 43)]
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(3)
L = np.zeros(n); R = np.zeros(n)
seg = 2 * BAR
for j in range(int(DUR / seg) + 1):
    notas, baixo = ACORDES[j % 4]
    a, b = j * seg, (j + 1) * seg + 1.2
    i0, i1 = int(a * SR), min(n, int(b * SR))
    if i0 >= n:
        break
    x = tt[i0:i1] - a
    env = np.minimum(1, x / 0.9) * np.clip((b - a - x) / 1.2, 0, 1)
    for m in notas:
        for h in range(1, 7):
            amp = 0.05 / h ** 1.4
            L[i0:i1] += amp * env * np.sin(2 * np.pi * hz(m) * h * 0.9985 * x)
            R[i0:i1] += amp * env * np.sin(2 * np.pi * hz(m) * h * 1.0015 * x + 0.7)
    bx = 0.11 * env * (np.sin(2 * np.pi * hz(baixo) * x) + 0.3 * np.sin(4 * np.pi * hz(baixo) * x))
    L[i0:i1] += bx; R[i0:i1] += bx
    # arpejo em colcheias (só depois dos primeiros 10 s)
    for c in range(16):
        tc = a + c * BAR / 8
        if tc < 10 or tc > DUR - 4:
            continue
        m = notas[[0, 2, 1, 3][c % 4]] + 12
        k0, k1 = int(tc * SR), min(n, int((tc + 0.5) * SR))
        y = tt[k0:k1] - tc
        p = 0.05 * np.exp(-y / 0.16) * np.sin(2 * np.pi * hz(m) * y)
        L[k0:k1] += p * (0.6 if c % 2 else 1.0); R[k0:k1] += p * (1.0 if c % 2 else 0.6)
# pulso: bumbo macio nos tempos 1 e 3, chimbal de ruído nos contratempos
for b0 in np.arange(10, DUR - 4, BAR / 2):
    k0, k1 = int(b0 * SR), min(n, int((b0 + 0.35) * SR))
    y = tt[k0:k1] - b0
    kick = 0.16 * np.exp(-y / 0.09) * np.sin(2 * np.pi * (45 * y + 40 * 0.04 * (1 - np.exp(-y / 0.04))))
    L[k0:k1] += kick; R[k0:k1] += kick
for b0 in np.arange(10 + BAR / 8, DUR - 4, BAR / 4):
    k0, k1 = int(b0 * SR), min(n, int((b0 + 0.06) * SR))
    y = tt[k0:k1] - b0
    hat = np.diff(rng.standard_normal(k1 - k0 + 1)) * 0.012 * np.exp(-y / 0.015)
    L[k0:k1] += hat; R[k0:k1] += hat * 0.8
# reverberação curta (ruído com decaimento) e fades
ir = rng.standard_normal(int(1.6 * SR)) * np.exp(-np.arange(int(1.6 * SR)) / SR / 0.45)
ir /= np.sqrt((ir ** 2).sum())
L = L + 0.35 * fftconvolve(L, ir)[:n]
R = R + 0.35 * fftconvolve(R, ir[::-1].copy())[:n]
trilha = np.stack([L, R], 1)
trilha *= (np.minimum(1, tt / 2.5) * np.clip((DUR - tt) / 3.0, 0, 1))[:, None]
rms = np.sqrt((trilha ** 2).mean())
trilha *= 10 ** (-27 / 20) / rms  # bem abaixo dos SFX (alvo ~ -27 dBFS RMS)

mix = sfx + trilha
if medir.pico_amostra_db(mix) > -1.5:
    mix = medir.limitar(mix, -1.5)
(OF / "_tmp").mkdir(parents=True, exist_ok=True)
medir.gravar(str(OF / "_tmp/sfx.wav"), sfx)
medir.gravar(str(OF / "_tmp/trilha.wav"), trilha)
medir.gravar(str(OF / "_tmp/audio.wav"), mix)

# ---------------------------------------------------------------- créditos
usados = {}
for e in ev:
    usados.setdefault(e.id, 0)
    usados[e.id] += 1
linhas = ["# CRÉDITOS — áudio do catálogo do horizontal (fase C)", "",
          "## Trilha", "Trilha leve **própria**, sintetizada por `F1/horizontal/testes/catalogo/montagem/audio.py` (numpy: pad Lám–Fá–Dó–Sol a 96 BPM,",
          "baixo, arpejo, bumbo/chimbal leves, reverb por ruído). Sem amostras de terceiros; uso livre. Nível ~ -27 dBFS RMS sob os SFX.", "",
          f"## Efeitos sonoros ({len(ev)} eventos, {len(usados)} sons) — banco `F1/horizontal/kit/sfx` (`Banco(semente=7)`)", "",
          "| som | vezes | licença | autor | origem |", "|---|---|---|---|---|"]
for iid, k in sorted(usados.items()):
    it = banco.itens[iid]
    linhas.append(f"| `{iid}` | {k} | {it.get('licenca','?')} | {it.get('autor') or '-'} | {it.get('url') or it.get('origem','-')} |")
cred = banco.creditos(ev)
linhas += ["", "## Crédito obrigatório (CC BY)", *(["- " + c for c in cred] or ["- nenhum"])]
(OF / "CREDITOS.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"audio ok: {DUR:.2f}s, {len(ev)} eventos, pico {medir.pico_amostra_db(mix):.1f} dBFS")
