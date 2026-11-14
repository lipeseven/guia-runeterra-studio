"""Medidas de áudio da rodada 3.
Recria cada SFX sozinho com a MESMA linha do filtro do montador (horizontal/final/audio/filtro_audio.txt: corte, fade e
ganho, sem o adelay) e o põe no tempo 'inicio' do relatorio.json. Os SFX do barramento SEM sidechain (clique, tecla, pop,
alerta, sino) entram no mix exatamente assim; os do barramento COM sidechain (impacto, riser, whoosh) são medidos pelo
resíduo mix - voz - trilha (voz mono a -3 dB por canal; trilha refeita com tri_filtro.txt -> _aval/tri_duck.wav).
Por evento: RMS/pico do SFX e da voz na janela, pico SFX - pico voz em +-150 ms, a MELHOR banda de oitava em que o SFX
passa voz+trilha (+-80 ms em volta do pico do SFX; > 0 dB = provavelmente audível, < -10 dB = provavelmente mascarado),
e pico do SFX - tempo da palavra-âncora. Também trilha x voz e buracos sem SFX. Saída: _aval/audio.json"""
import json, os, re, subprocess, numpy as np, soundfile as sf
from comum import PROJ, TMP

A = PROJ + r"\horizontal\final\audio"
rel = json.load(open(PROJ + r"\horizontal\final\relatorio.json", encoding="utf-8"))["audio"]
ev = rel["eventos"]
linhas = open(A + r"\filtro_audio.txt", encoding="utf-8").read().splitlines()
duck = set(re.findall(r"\[t(\d+)\]", [l for l in linhas if "[busd]" in l and "amix" in l][0]))
SR = 48000
rd = lambda p: sf.read(p, always_2d=True)[0].mean(1)
voz = rd(PROJ + r"\trabalho\gravacao\limpa.wav") * 0.70710678
tri = rd(os.path.join(TMP, "tri_duck.wav")); mix = rd(A + r"\mix_bruta.wav")
N = len(mix); fit = lambda x: np.pad(x, (0, max(0, N - len(x))))[:N]
voz, tri = fit(voz), fit(tri)
resid = mix - voz - tri
db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
pk = lambda x: 20 * np.log10(np.max(np.abs(x)) + 1e-12)
pal = json.load(open(PROJ + r"\direcao\tempos_gravacao.json", encoding="utf-8"))
BANDAS = [(88, 177), (177, 355), (355, 710), (710, 1420), (1420, 2840), (2840, 5680), (5680, 11360), (11360, 20000)]


def isolado(k, e):
    """renderiza o SFX k (entrada [k+2:a]) com a linha do filtro, sem adelay"""
    ln = [l for l in linhas if l.startswith(f"[{k + 2}:a]")][0]
    corpo = ln.split("]", 1)[1]
    corpo = re.sub(r",adelay=[^,]+,asplit=2\[s\d+\]\[t\d+\];?$", "", corpo)
    saida = os.path.join(TMP, f"sfx_{k:02d}.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", e["arquivo"], "-af", corpo, "-c:a", "pcm_f32le", saida], check=True)
    x = rd(saida); s = np.zeros(N); a = int(round(e["inicio"] * SR)); b = min(N, a + len(x)); s[a:b] = x[:b - a]
    return s


def banda_snr(s, ruido, c):
    a, b = max(0, c - int(0.08 * SR)), min(N, c + int(0.08 * SR))
    w = np.hanning(b - a); S = np.abs(np.fft.rfft(s[a:b] * w)) ** 2; R = np.abs(np.fft.rfft(ruido[a:b] * w)) ** 2
    f = np.fft.rfftfreq(b - a, 1 / SR); out = []
    for lo, hi in BANDAS:
        m = (f >= lo) & (f < hi); out.append(10 * np.log10((S[m].sum() + 1e-15) / (R[m].sum() + 1e-15)))
    k = int(np.argmax(out)); return round(out[k], 1), f"{BANDAS[k][0]}-{BANDAS[k][1]} Hz"


E = []; stems = {}
for k, e in enumerate(ev):
    s = isolado(k, e); stems[k] = s
    sidechain = str(k + 2) in duck
    a = int(e["inicio"] * SR); b = min(N, int((e["inicio"] + e["dur"]) * SR))
    no_mix = resid if sidechain else s   # o que de fato está no mix
    seg = no_mix[a:b]; pi = int(np.argmax(np.abs(seg))); c = a + pi
    cc, dd = max(0, c - 7200), min(N, c + 7200)
    snr, banda = banda_snr(no_mix, voz + tri, c)
    p = min(pal, key=lambda w: abs(w["i"] - e["t"]))
    E.append({"n": k + 1, "categoria": e["categoria"], "id": e["id"], "palavra": e["palavra"], "t_palavra": round(e["t"], 2),
              "palavra_mais_proxima": f"{p['t']}@{p['i']:.2f}", "sidechain": sidechain,
              "pico_s": round(c / SR, 3), "pico_menos_palavra_ms": int(round(1000 * (c / SR - e["t"]))),
              "sfx_rms_db": round(db(seg), 1), "sfx_pico_db": round(pk(seg), 1), "voz_rms_db": round(db(voz[a:b]), 1),
              "sfx_menos_voz_rms_db": round(db(seg) - db(voz[a:b]), 1), "pico_sfx_menos_pico_voz_150ms_db": round(pk(no_mix[cc:dd]) - pk(voz[cc:dd]), 1),
              "melhor_banda_sfx_sobre_voz_trilha_db": snr, "banda": banda,
              "obs": "resíduo (inclui outros SFX com sidechain sobrepostos)" if sidechain else "isolado exato"})
# momentos de SFX (eventos a menos de 1,5 s viram um momento)
mom = []
for e in sorted(ev, key=lambda x: x["inicio"]):
    if mom and e["inicio"] - mom[-1]["fim"] < 1.5: mom[-1]["fim"] = max(mom[-1]["fim"], e["inicio"] + e["dur"]); mom[-1]["n"] += 1; mom[-1]["cats"].append(e["categoria"])
    else: mom.append({"ini": round(e["inicio"], 2), "fim": e["inicio"] + e["dur"], "n": 1, "cats": [e["categoria"]]})
for m in mom: m["fim"] = round(m["fim"], 2)
buracos = [(mom[k]["fim"], mom[k + 1]["ini"]) for k in range(len(mom) - 1) if mom[k + 1]["ini"] - mom[k]["fim"] > 6]
# trilha x voz (janelas de 400 ms com fala)
win = int(0.4 * SR); M = [(k / SR, db(voz[k:k + win]), db(tri[k:k + win])) for k in range(0, N - win, win)]
fala = [m for m in M if m[1] > -38]; mg = np.array([v - t for _, v, t in fala]); nz = np.nonzero(np.abs(tri) > 1e-4)[0]
sil = [m for m in M if m[1] <= -50]
trilha = {"trilha_rms_db": round(db(tri), 1), "voz_rms_db": round(db(voz), 1), "janelas_fala": len(fala),
          "margem_voz_sobre_trilha_mediana_db": round(float(np.median(mg)), 1), "margem_p10_db": round(float(np.percentile(mg, 10)), 1),
          "pct_fala_margem_<6dB": round(100 * float((mg < 6).mean()), 1), "trilha_nas_pausas_mediana_db": round(float(np.median([t for _, _, t in sil])), 1) if sil else None,
          "trilha_ultimo_som_s": round(nz[-1] / SR, 2), "residuo_sem_sfx_db": None}
# conferência do resíduo: num trecho sem SFX, mix - voz - trilha deve ser ~0
ativo = np.zeros(N, bool)
for e in ev: ativo[int(e["inicio"] * SR):int((e["inicio"] + e["dur"] + 0.5) * SR)] = True
trilha["residuo_sem_sfx_db"] = round(db(resid[~ativo]), 1)
# estatística dos isolados exatos (sem sidechain) x resíduo: confere que entram sem redução
chk = [round(db(resid[int(e["inicio"] * SR):int((e["inicio"] + e["dur"]) * SR)]) - db(stems[k][int(e["inicio"] * SR):int((e["inicio"] + e["dur"]) * SR)]), 2)
       for k, e in enumerate(ev) if str(k + 2) not in duck]
out = {"sfx": E, "n_eventos": len(ev), "momentos": mom, "n_momentos": len(mom), "buracos_sem_sfx_>6s": buracos, "trilha": trilha,
       "conferencia_residuo_menos_isolado_db": chk, "mix_rms_db": round(db(mix), 1)}
json.dump(out, open(os.path.join(TMP, "audio.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for e in E: print(e["n"], e["categoria"], e["palavra"], e["t_palavra"], e["palavra_mais_proxima"], "dt", e["pico_menos_palavra_ms"], "sfx", e["sfx_rms_db"], "pk", e["sfx_pico_db"], "s-v", e["sfx_menos_voz_rms_db"], "pk-pk", e["pico_sfx_menos_pico_voz_150ms_db"], "banda", e["melhor_banda_sfx_sobre_voz_trilha_db"], e["banda"], "SC" if e["sidechain"] else "")
print(json.dumps({k: v for k, v in out.items() if k != "sfx"}, ensure_ascii=False))
