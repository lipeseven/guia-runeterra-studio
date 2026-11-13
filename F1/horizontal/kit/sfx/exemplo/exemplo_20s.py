# Exemplo de mixagem mínima: trilho de 20 s com SFX ancorados em palavras (pedidos.json + palavras.json).
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\exemplo\exemplo_20s.py            # numpy + ffmpeg + eventos TS
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\exemplo\exemplo_20s.py --motores  # + render Remotion e HyperFrames
# Saídas em exemplo/saida/ (fora do Git): trilho_numpy.wav, trilho_ffmpeg.wav, eventos.json, eventos_ts.json,
# hyperframes/ (página + render), trilho_remotion.wav, trilho_hyperframes.wav e comparacao.json.
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

EX = Path(__file__).resolve().parent
KIT = EX.parent
sys.path.insert(0, str(KIT))
import medir  # noqa: E402
import sfx  # noqa: E402

RAIZ = KIT.parents[3]
SAIDA = EX / "saida"
DUR = 20.0
NODE_MODULES_REMOTION = RAIZ / "F1" / "video" / "node_modules"
# navegador que o F1/video já baixou (sem isso o Remotion baixa outro de ~280 MB na pasta do exemplo)
NAVEGADOR = NODE_MODULES_REMOTION / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"
HYPERFRAMES = "hyperframes@0.9.20"  # mesma versão do teste HyperFrames (via npx, nada global)


def ler_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def eventos_py(semente: int = 0) -> list[sfx.Evento]:
    return sfx.Banco(semente=semente).de_pedidos(ler_json(EX / "pedidos.json"), ler_json(EX / "palavras.json"))


def eventos_ts(semente: int = 0) -> list[dict]:
    r = subprocess.run(["node", str(EX / "eventos.ts"), str(semente)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def onsets(x: np.ndarray, limiar_db: float = 18.0) -> list[float]:
    """Instantes (s) em que o envelope de 10 ms sobe mais que limiar_db em relação aos 50 ms anteriores."""
    env = 20 * np.log10(medir.envelope(x) + 1e-9)
    out, ult = [], -1.0
    for i in range(5, len(env)):
        if env[i] > -50 and env[i] - env[i - 5:i].min() > limiar_db and i * 0.01 - ult > 0.12:
            out.append(round(i * 0.01, 2))
            ult = i * 0.01
    return out


def comparar(ref: np.ndarray, outro: np.ndarray) -> dict:
    """Atraso (ms) pela correlação dos envelopes, diferença de nível (dB RMS) e erro residual após alinhar."""
    n = min(len(ref), len(outro))
    a, b = ref[:n], outro[:n]
    ea, eb = medir.envelope(a, 0.001), medir.envelope(b, 0.001)
    lags = range(-50, 51)  # ±50 ms em passos de 1 ms
    cc = [np.dot(ea[max(0, -l):len(ea) - max(0, l)], eb[max(0, l):len(eb) - max(0, -l)]) for l in lags]
    lag = list(lags)[int(np.argmax(cc))]
    rms = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)
    s = lag * 48
    bb = np.roll(b, -s, 0)
    resid = rms(a - bb) - rms(a)
    # envelope de 10 ms em dB: p95 da diferença onde a referência tem som (insensível a desvios de fase/quadro)
    da, db = (20 * np.log10(medir.envelope(x) + 1e-9) for x in (a, b))
    m = min(len(da), len(db))
    viva = da[:m] > -45
    oa, ob = onsets(a), onsets(b)
    return {"atraso_ms": lag, "nivel_db": round(rms(b) - rms(a), 2), "residuo_onda_db": round(resid, 1),
            "envelope_dif_p95_db": round(float(np.percentile(np.abs(da[:m] - db[:m])[viva], 95)), 2),
            "onsets_iguais": len(oa) == len(ob), "onset_desvio_max_s": round(max((abs(x - y) for x, y in zip(oa, ob)), default=0), 3),
            "lufs_integrado": round(medir.lufs_integrado(b), 2)}


def remotion(evs: list[sfx.Evento]) -> Path | None:
    if not NODE_MODULES_REMOTION.is_dir():
        print("Remotion: F1/video/node_modules não existe; pulei.")
        return None
    junc = EX / "remotion" / "node_modules"
    if not junc.exists():
        subprocess.run(["cmd", "/c", "mklink", "/J", str(junc), str(NODE_MODULES_REMOTION)], check=True,
                       capture_output=True)
    publico = SAIDA / "remotion_public"          # só os WAVs usados (o bundler copia a pasta inteira)
    for e in evs:
        (publico / e.arquivo).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(KIT / e.arquivo, publico / e.arquivo)
    out = SAIDA / "trilho_remotion.wav"
    cli = NODE_MODULES_REMOTION / "@remotion" / "cli" / "remotion-cli.js"
    subprocess.run(["node", str(cli), "render", "index.tsx", "ExemploSfx", str(out), f"--public-dir={publico}",
                    f"--browser-executable={NAVEGADOR}", "--log=error"], cwd=EX / "remotion", check=True)
    return out


def hyperframes(evs: list[sfx.Evento]) -> Path | None:
    pasta = SAIDA / "hyperframes"
    (pasta / "assets" / "sfx").mkdir(parents=True, exist_ok=True)
    for e in evs:
        shutil.copy2(KIT / e.arquivo, pasta / "assets" / "sfx" / Path(e.arquivo).name)
    tags = sfx.para_hyperframes(evs)
    (pasta / "index.html").write_text(f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="UTF-8" /><meta name="viewport" content="width=320, height=180" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>html,body{{margin:0;width:320px;height:180px;background:#ecebe7}}</style></head>
<body>
<!-- Exemplo do kit de SFX: trilho de 20 s gerado por sfx.para_hyperframes() -->
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR:g}" data-fps="60" data-width="320" data-height="180">
<div id="fundo" class="clip" data-start="0" data-duration="{DUR:g}" data-track-index="1" style="position:absolute;inset:0;background:#ecebe7"></div>
{tags}
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  tl.to("#fundo", {{ opacity: 1, duration: {DUR:g} }}, 0);
  window.__timelines["main"] = tl;
</script>
</body></html>
""", encoding="utf-8")
    (pasta / "package.json").write_text(json.dumps({"name": "exemplo-sfx", "private": True, "type": "module"}), encoding="utf-8")
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    mp4 = pasta / "render.mp4"
    r = subprocess.run([npx, "--yes", HYPERFRAMES, "render", "--output", str(mp4)], cwd=pasta,
                       capture_output=True, text=True)
    if r.returncode != 0 or not mp4.exists():
        print("HyperFrames: render falhou:\n", (r.stdout + r.stderr)[-2500:])
        return None
    out = SAIDA / "trilho_hyperframes.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-vn", "-ac", "2", "-ar", "48000", str(out)], check=True)
    return out


def main() -> dict:
    SAIDA.mkdir(exist_ok=True)
    evs = eventos_py()
    (SAIDA / "eventos.json").write_text(json.dumps(sfx.para_json(evs), ensure_ascii=False, indent=1), encoding="utf-8")
    ts = eventos_ts()
    (SAIDA / "eventos_ts.json").write_text(json.dumps(ts, ensure_ascii=False, indent=1), encoding="utf-8")
    final = sfx.mixar(evs, DUR, SAIDA / "trilho_numpy.wav")
    cru = sfx.mixar(evs, DUR, None, limitar=False)
    sfx.mixar_ffmpeg(evs, DUR, SAIDA / "trilho_ffmpeg.wav")
    res = {
        "eventos": [(e.categoria, e.id, e.palavra, e.t, e.inicio) for e in evs],
        "paridade_ts": all(a["id"] == b["id"] and abs(a["inicio"] - b["inicio"]) < 1e-3 and abs(a["ganho_db"] - b["ganho_db"]) < 1e-2
                           for a, b in zip(sfx.para_json(evs), ts)) and len(ts) == len(evs),
        "numpy": {"lufs_integrado": round(medir.lufs_integrado(final), 2), "pico_dbtp": round(medir.pico_verdadeiro_db(final), 2),
                  "limitador_atuou": bool(medir.pico_amostra_db(cru) > -1.5)},
        "ffmpeg": comparar(cru, medir.ler(str(SAIDA / "trilho_ffmpeg.wav"))),
        "onsets_numpy": onsets(final),
    }
    if "--motores" in sys.argv:
        for nome, fn in (("remotion", lambda: remotion(evs)), ("hyperframes", lambda: hyperframes(evs))):
            try:
                p = fn()
            except Exception as ex:  # noqa: BLE001 - relata e segue
                print(f"{nome}: erro {ex}")
                p = None
            if p and p.exists():
                y = medir.ler(str(p))
                res[nome] = comparar(cru, y)
    (SAIDA / "comparacao.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "eventos"}, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
