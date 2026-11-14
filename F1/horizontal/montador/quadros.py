"""Verificação do vídeo montado, por QUADRO e por amostra de áudio (não por foto solta).

1. Formato: 60 q/s CFR, resolução, nº de quadros = soma das cenas (Q1 - Q0 de cada uma), áudio com a duração do vídeo.
2. Duração por cena: o 1º, o do meio e o último quadro PURO de cada cena no vídeo final são o quadro certo do trecho
   dela (o mais parecido entre os deslocamentos -2..+2; deslocamento 0 = nenhum quadro a mais/a menos antes dele).
3. Junções: de 2 quadros antes a 2 depois de cada transição, cada quadro final = o esperado (puro do trecho A, quadro
   composto da transição, puro do trecho B), sem quadro preto e sem quadro repetido onde o esperado muda.
4. Sincronia: no `sfx.wav` (mesma linha do tempo da mixagem), o pico (RMS 10 ms) de cada SFX isolado cai na âncora;
   o áudio do MP4 final está alinhado ao `master.wav` (correlação cruzada); loudness do MP4 medida.
Folhas de quadros (JPG) de cada junção e das cenas, para olhar.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import juncao as J
import mixagem as M

FPS = 60
SR = 48000
PSNR_MIN = 32.0           # dB entre o quadro final e o esperado (duas codificações H.264 de alta qualidade)
TOL_SFX_MS = {"impacto": 12, "pop": 12, "clique": 12, "tecla": 12, "alerta": 15, "sino": 15, "whoosh": 150, "riser": 150}


def _probe(mp4: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,duration,sample_rate,channels",
                        "-of", "json", str(mp4)], capture_output=True, text=True)
    return {s["codec_type"]: s for s in json.loads(r.stdout)["streams"]}


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 99.0 if mse < 1e-9 else 10 * np.log10(255 ** 2 / mse)


def _audio_mono(arq: Path) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def _envelope(x: np.ndarray, janela_s: float = 0.01) -> np.ndarray:
    w = max(1, int(janela_s * SR))
    c = np.concatenate([[0.0], np.cumsum(x * x)])
    e = np.sqrt(np.maximum(0, (c[w:] - c[:-w]) / w))
    return np.concatenate([np.zeros(w // 2), e, np.zeros(len(x) - len(e) - w // 2)])


def _atraso_ms(a: np.ndarray, b: np.ndarray, max_ms: float = 50) -> float:
    """Atraso de b em relação a a (ms) pela correlação cruzada (FFT), limitado a ±max_ms."""
    n = min(len(a), len(b), SR * 20)
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    m = 1 << int(np.ceil(np.log2(2 * n)))
    cc = np.fft.irfft(np.fft.rfft(b, m) * np.conj(np.fft.rfft(a, m)), m)
    L = int(max_ms / 1000 * SR)
    lags = np.concatenate([np.arange(0, L + 1), np.arange(-L, 0)])
    vals = np.concatenate([cc[:L + 1], cc[-L:]])
    return float(lags[int(np.argmax(vals))] / SR * 1000)


FONTE = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 16)


def folha(quadros: list[tuple[str, np.ndarray]], titulo: str, saida: Path, larg: int = 320, cols: int = 6) -> None:
    ims = []
    for rot, q in quadros:
        im = Image.fromarray(q)
        im = im.resize((larg, round(im.height * larg / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 8 + 9 * len(rot), 22], fill=(20, 20, 20))
        d.text((4, 2), rot, font=FONTE, fill=(255, 255, 255))
        ims.append(im)
    W, H = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W + (cols + 1) * 4, rows * H + (rows + 1) * 4 + 30), (90, 90, 90))
    ImageDraw.Draw(sheet).text((8, 6), titulo, font=FONTE, fill=(255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, (4 + (i % cols) * (W + 4), 34 + (i // cols) * (H + 4)))
    sheet.save(saida, quality=88)


def verificar(rel: dict, saida_dir: Path) -> dict:
    """rel = relatório do montador (cenas com Q0/Q1/trecho, peças, transições, mixagem). Devolve erros/avisos/medidas."""
    saida_dir = Path(saida_dir)
    saida_dir.mkdir(parents=True, exist_ok=True)
    W, H = rel["largura"], rel["altura"]
    mp4 = Path(rel["arquivo"])
    erros, avisos, med = [], [], {}
    # 1. formato
    pr = _probe(mp4)
    v, a = pr.get("video", {}), pr.get("audio")
    total = rel["quadros"]
    med["formato"] = {"quadros": int(v.get("nb_read_frames", -1)), "esperado": total, "fps": v.get("r_frame_rate"),
                      "fps_medio": v.get("avg_frame_rate"), "resolucao": f"{v.get('width')}x{v.get('height')}"}
    if int(v.get("nb_read_frames", -1)) != total:
        erros.append(f"FORMATO: {v.get('nb_read_frames')} quadros no MP4, esperados {total}")
    if v.get("r_frame_rate") != "60/1" or v.get("avg_frame_rate") != "60/1":
        erros.append(f"FORMATO: taxa {v.get('r_frame_rate')} / média {v.get('avg_frame_rate')} (esperado 60/1 CFR)")
    if (v.get("width"), v.get("height")) != (W, H):
        erros.append(f"FORMATO: resolução {v.get('width')}x{v.get('height')}, esperada {W}x{H}")
    soma = sum(c["Q1"] - c["Q0"] for c in rel["cenas"])
    if soma != total:
        erros.append(f"FORMATO: soma das cenas {soma} quadros × vídeo {total}")
    if rel.get("audio"):
        if not a:
            erros.append("AUDIO: MP4 sem áudio")
        else:
            dif = abs(float(a.get("duration", 0)) - total / FPS) * 1000
            med["formato"]["audio_ms_de_diferenca"] = round(dif, 1)
            if dif > 25:
                erros.append(f"AUDIO: duração do áudio difere {dif:.0f} ms do vídeo")

    trechos = {c["id"]: c for c in rel["cenas"]}
    # 2. duração por cena (quadros puros no lugar certo)
    med["cenas"] = []
    folha_cenas = []
    for p in rel["pecas"]:
        if p["tipo"] != "trecho":
            continue
        c = trechos[p["cena"]]
        g0 = c["Q0"] - c["pre"]                       # quadro global do índice 0 do trecho
        res = {"cena": c["id"], "quadros": c["Q1"] - c["Q0"], "amostras": []}
        for j in sorted({p["de"], (p["de"] + p["ate"] - 1) // 2, p["ate"] - 1}):
            g = g0 + j
            fin = J.ler_quadros(mp4, g, 1, W, H)[0]
            lo, hi = max(0, j - 2), min(c["trecho_quadros"], j + 3)
            fonte = J.ler_quadros(Path(c["trecho"]), lo, hi - lo, W, H)
            ps = {d: psnr(fin, fonte[j + d - lo]) for d in range(lo - j, hi - j)}
            melhor = max(ps, key=ps.get)
            vizinhos_iguais = all(psnr(fonte[j - lo], fonte[k]) > 45 for k in range(len(fonte)) if k != j - lo)
            ok = ps[0] >= PSNR_MIN and (melhor == 0 or ps[melhor] - ps[0] < 0.05)
            res["amostras"].append({"quadro": g, "local": j, "psnr": round(ps[0], 2), "melhor_desloc": melhor,
                                    "parado": vizinhos_iguais})
            if not ok:
                erros.append(f"CENA {c['id']}: quadro global {g} não é o quadro {j} do trecho (PSNR {ps[0]:.1f} dB; "
                             f"melhor deslocamento {melhor:+d})")
            if j == (p["de"] + p["ate"] - 1) // 2:
                folha_cenas.append((f"{c['id']} q{g} {c['motor']}", fin))
        med["cenas"].append(res)
    if folha_cenas:
        folha(folha_cenas, "meio de cada cena (vídeo final)", saida_dir / "folha_cenas.jpg", larg=480, cols=3)

    # 3. junções
    med["juncoes"] = []
    cen = rel["cenas"]
    for k in range(1, len(cen)):
        A, B = cen[k - 1], cen[k]
        n = B["n_entrada"]
        q0 = B["Q0"] - n // 2
        g_ini, g_fim = q0 - 2, q0 + n + 2
        fin = J.ler_quadros(mp4, g_ini, g_fim - g_ini, W, H)
        trans_dir = next((Path(p["pasta"]) for p in rel["pecas"] if p["tipo"] == "transicao" and p["cena"] == B["id"]), None)
        pior, pretos, repetidos, vistos = 99.0, [], [], []
        esperado_ant = None
        for m, g in enumerate(range(g_ini, g_fim)):
            if g < q0:
                esp = J.ler_quadros(Path(A["trecho"]), g - (A["Q0"] - A["pre"]), 1, W, H)[0]
                rot = "A"
            elif g < q0 + n:
                esp = np.asarray(Image.open(trans_dir / f"q{g - q0:06d}.png").convert("RGB"))
                rot = f"T{g - q0}"
            else:
                esp = J.ler_quadros(Path(B["trecho"]), g - (B["Q0"] - B["pre"]), 1, W, H)[0]
                rot = "B"
            p_ = psnr(fin[m], esp)
            pior = min(pior, p_)
            if p_ < PSNR_MIN:
                erros.append(f"JUNCAO {A['id']}→{B['id']}: quadro {g} ({rot}) difere do esperado (PSNR {p_:.1f} dB)")
            if fin[m].mean() < 8 and esp.mean() > 30:
                pretos.append(g)
            if m and esperado_ant is not None and np.abs(fin[m].astype(int) - fin[m - 1]).mean() < 0.3 \
                    and np.abs(esp.astype(int) - esperado_ant).mean() > 1.0:
                repetidos.append(g)
            esperado_ant = esp
            vistos.append((f"q{g} {rot} {p_:.0f}dB", fin[m]))
        if pretos:
            erros.append(f"JUNCAO {A['id']}→{B['id']}: quadro preto em {pretos}")
        if repetidos:
            erros.append(f"JUNCAO {A['id']}→{B['id']}: quadro repetido em {repetidos}")
        med["juncoes"].append({"de": A["id"], "para": B["id"], "tipo": B["transicao"], "n": n, "q0": q0, "corte": B["Q0"],
                               "pior_psnr": round(pior, 2), "pretos": pretos, "repetidos": repetidos})
        folha(vistos, f"junção {A['id']} → {B['id']}: {B['transicao']} {n} q (q{q0}..q{q0 + n - 1}), 60 q/s",
              saida_dir / f"folha_juncao_{k:02d}_{B['transicao']}.jpg", larg=320, cols=6)

    # 4. sincronia e loudness
    mix = rel.get("audio")
    if mix:
        stem = _audio_mono(Path(mix["arquivos"]["sfx"]))
        env = _envelope(stem)
        evs = mix["eventos"]
        med["sfx"] = []
        for e in evs:
            outros = [o["t"] for o in evs if o is not e]
            isolado = all(abs(o - e["t"]) > 0.35 for o in outros)
            i0, i1 = int(max(0, e["t"] - 0.25) * SR), int(min(len(env) / SR, e["t"] + 0.25) * SR)
            pico = (i0 + int(np.argmax(env[i0:i1]))) / SR if i1 > i0 else float("nan")
            tol = TOL_SFX_MS.get(e["categoria"], 15)
            # referência: o pico do PRÓPRIO som (mesmo envelope deslizante) onde a mixagem o colocou. O `pico_s` do
            # catálogo (blocos de 10 ms) erra em som com dois golpes parecidos (uso real, 2026-11-14: alerta_hf_erro
            # 0,05 × 0,14 s): isso vira AVISO do catálogo; ERRO fica para som fora do lugar na mixagem.
            ref, d_cat = e["t"], None
            if e.get("arquivo") and Path(e["arquivo"]).exists() and e.get("inicio") is not None:
                s = _audio_mono(Path(e["arquivo"]))
                a0 = int(round(float(e.get("corte_ini") or 0) * SR))
                seg = s[a0:a0 + int(round(float(e["dur"]) * SR))] if e.get("dur") else s[a0:]
                if len(seg) > SR // 100:
                    ref = float(e["inicio"]) + int(np.argmax(_envelope(seg))) / SR
                    d_cat = (ref - e["t"]) * 1000
            d = (pico - ref) * 1000
            med["sfx"].append({"categoria": e["categoria"], "id": e["id"], "t": e["t"], "pico_medido": round(pico, 4),
                               "erro_ms": round(d, 1), "pico_catalogo_ms": None if d_cat is None else round(d_cat, 1),
                               "isolado": isolado, "palavra": e.get("palavra")})
            if isolado and abs(d) > tol:
                (erros if tol <= 15 else avisos).append(
                    f"SFX {e['categoria']} ({e['id']}) em {e['t']:.3f} s: pico medido {d:+.1f} ms do pico do som (tolerância {tol} ms)")
            if d_cat is not None and abs(d_cat) > tol and tol <= 15:
                avisos.append(f"SFX {e['categoria']} ({e['id']}): o pico do som fica {d_cat:+.1f} ms da palavra "
                              f"(pico_s do catálogo do kit/sfx diferente do envelope de 10 ms; refazer o catálogo)")
        master = _audio_mono(Path(mix["arquivos"]["master"]))
        final = _audio_mono(mp4)
        atraso = _atraso_ms(master, final)
        med["audio_alinhamento_ms"] = round(atraso, 3)
        if abs(atraso) > 1.0:
            erros.append(f"AUDIO: áudio do MP4 deslocado {atraso:+.2f} ms em relação ao master")
        lf = M.medir(mp4)
        med["loudness_mp4"] = lf
        if mix.get("alvo_lufs") is not None and abs(lf["lufs"] - mix["alvo_lufs"]) > 0.7:
            erros.append(f"LOUDNESS: {lf['lufs']:.1f} LUFS no MP4, alvo {mix['alvo_lufs']}")
        if lf["pico_dbtp"] > -1.0:
            erros.append(f"LOUDNESS: pico verdadeiro {lf['pico_dbtp']:.1f} dBTP (> -1)")
    out = {"status": "reprovado" if erros else "aprovado", "erros": erros, "avisos": avisos, "medidas": med}
    (saida_dir / "verificacao_montagem.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
