"""Junção dos trechos com as transições do kit/transicoes, num relógio único de 60 q/s.

Linha do tempo: a cena k ocupa os quadros globais [Q0k, Q1k), Q = round(t * 60) das palavras (contíguas: Q1k = Q0k+1).
A transição de entrada da cena k (n quadros) fica CENTRADA no corte, como no kit: quadros [Q0k - n//2, Q0k - n//2 + n).
Por isso o trecho da cena k é renderizado com `pre = n_k // 2` quadros antes de Q0k e `pos = n_{k+1} - n_{k+1} // 2`
depois de Q1k (sobreposição dos dois lados; ARQUITETURA §6).

Os quadros intermediários são compostos aqui, em numpy, com o MESMO `estadoTransicao` que os motores aplicam em CSS
(opacidade, escala em torno do centro, desfoque gaussiano com desvio = blur px, recorte inset em %, barra do wipe),
lido pelo `transicoes.mjs`. O resto do vídeo é o próprio trecho (trim por quadro, sem recompor).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FPS = 60
AQUI = Path(__file__).resolve().parent


def estados(transicoes: list[dict], largura: int, altura: int, tmp: Path) -> list[dict]:
    """[{tipo, em, quadros}] → estados por quadro do kit (node transicoes.mjs)."""
    if not transicoes:
        return []
    ped = tmp / "transicoes_pedido.json"
    ped.write_text(json.dumps({"fps": FPS, "largura": largura, "altura": altura, "transicoes": transicoes}), encoding="utf-8")
    r = subprocess.run(["node", str(AQUI / "transicoes.mjs"), str(ped)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"transicoes.mjs falhou: {r.stderr[-1500:]}")
    return json.loads(r.stdout)


def ler_quadros(mp4: Path, inicio: int, n: int, largura: int, altura: int) -> np.ndarray:
    """Quadros [inicio, inicio+n) do MP4 em RGB uint8 (n, H, W, 3)."""
    if n <= 0:
        return np.zeros((0, altura, largura, 3), np.uint8)
    cmd = ["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"trim=start_frame={inicio}:end_frame={inicio + n},setpts=PTS-STARTPTS",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-800:])
    arr = np.frombuffer(r.stdout, np.uint8)
    k = arr.size // (altura * largura * 3)
    if k != n:
        raise RuntimeError(f"{Path(mp4).name}: pedi {n} quadros a partir de {inicio}, vieram {k}")
    return arr.reshape(n, altura, largura, 3)


def _cobertura(n: int, a: float, b: float) -> np.ndarray:
    """Fração de cada pixel [i, i+1) dentro de [a, b) (borda com antisserrilhado, como o Chrome)."""
    i = np.arange(n, dtype=np.float64)
    return np.clip(np.minimum(i + 1, b) - np.maximum(i, a), 0, 1)


def _camada(img: np.ndarray, c: dict, largura: int) -> tuple[np.ndarray, np.ndarray]:
    """Uma camada CSS do kit → (rgb float, alfa float H×W)."""
    H, W = img.shape[:2]
    im = Image.fromarray(img)
    if c["blur"] > 0.01:
        im = im.filter(ImageFilter.GaussianBlur(c["blur"] * largura / 1920))
    s = c["escala"]
    if abs(s - 1) > 1e-6 or c["tx"] or c["ty"]:
        cx, cy = W / 2 + c["tx"], H / 2 + c["ty"]
        im = im.transform((W, H), Image.AFFINE, (1 / s, 0, W / 2 - cx / s, 0, 1 / s, H / 2 - cy / s), Image.BICUBIC)
    rgb = np.asarray(im, np.float64)
    alfa = np.full((H, W), float(c["opacidade"]))
    if c.get("recorte"):
        cima, dir_, baixo, esq = c["recorte"]
        alfa *= np.outer(_cobertura(H, cima / 100 * H, H - baixo / 100 * H), _cobertura(W, esq / 100 * W, W - dir_ / 100 * W))
    return rgb, alfa


def compor(a: np.ndarray, b: np.ndarray, estado: dict, largura: int) -> np.ndarray:
    """Quadro intermediário: A por baixo, B por cima, barra do wipe no topo."""
    H, W = a.shape[:2]
    out = np.zeros((H, W, 3), np.float64)
    for img, c in ((a, estado["a"]), (b, estado["b"])):
        if c is None:
            continue
        rgb, al = _camada(img, c, largura)
        out = out * (1 - al[..., None]) + rgb * al[..., None]
    br = estado.get("barra")
    if br:
        cor = np.array([int(br["cor"][k:k + 2], 16) for k in (1, 3, 5)], np.float64)
        al = np.outer(_cobertura(H, br["y"], br["y"] + br["h"]), _cobertura(W, br["x"], br["x"] + br["w"]))
        out = out * (1 - al[..., None]) + cor * al[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def pecas(cenas: list[dict], trechos: list[dict], est: list[dict | None], largura: int, altura: int, tmp: Path) -> list[dict]:
    """Lista ordenada de peças do vídeo final: {tipo: 'trecho', arquivo, de, ate} ou {tipo: 'transicao', pasta, n}.
    est[k] = estados da transição de ENTRADA da cena k (None = corte/1ª cena)."""
    out = []
    for k, (cena, tr) in enumerate(zip(cenas, trechos)):
        n_in = est[k]["n"] if est[k] else 0
        n_out = est[k + 1]["n"] if k + 1 < len(cenas) and est[k + 1] else 0
        L = int(round(cena["t1"] * FPS)) - int(round(cena["t0"] * FPS))
        pre = n_in // 2
        de, ate = n_in, pre + L - n_out // 2            # quadros puros da cena k no trecho dela
        if ate < de:
            raise ValueError(f"cena {cena['id']}: transições de entrada ({n_in} q) e saída ({n_out} q) maiores que a cena ({L} q)")
        if est[k] and n_in:
            prev, ptr = cenas[k - 1], trechos[k - 1]
            Lp = int(round(prev["t1"] * FPS)) - int(round(prev["t0"] * FPS))
            pre_p = (est[k - 1]["n"] // 2) if est[k - 1] else 0
            ini_a = pre_p + Lp - n_in // 2               # 1º quadro de A usado na transição (no trecho de A)
            qa = ler_quadros(Path(ptr["arquivo"]), ini_a, n_in, largura, altura)
            qb = ler_quadros(Path(tr["arquivo"]), 0, n_in, largura, altura)
            pasta = tmp / f"transicao_{k:02d}"
            pasta.mkdir(parents=True, exist_ok=True)
            for m, e in enumerate(est[k]["quadros"]):
                Image.fromarray(compor(qa[m], qb[m], e, largura)).save(pasta / f"q{m:06d}.png", compress_level=1)
            out.append({"tipo": "transicao", "pasta": str(pasta), "n": n_in, "cena": cena["id"], "q0": est[k]["q0"]})
        if ate > de:
            out.append({"tipo": "trecho", "arquivo": tr["arquivo"], "de": de, "ate": ate, "cena": cena["id"]})
    return out


def parametros_codec(cod: str, rascunho: bool) -> list[str]:
    """Parâmetros fixos por codificador: todos os blocos de um vídeo saem iguais (concat sem recodificar). Sem quadros B
    (`-bf 0`): cada bloco começa e termina limpo no relógio de 60 q/s."""
    if cod == "h264_nvenc":
        if os.environ.get("F1_SEM_NVENC"):   # testes: máquina "sem NVENC" (preset inexistente = o ffmpeg recusa de verdade)
            return ["h264_nvenc", "-preset", "sem_nvenc", "-bf", "0"]
        return ["h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19" if rascunho else "16", "-b:v", "0", "-bf", "0"]
    return ["libx264", "-preset", "veryfast" if rascunho else "slow", "-crf", "18" if rascunho else "15", "-bf", "0"]


def encodar_final(pcs: list[dict], audio: Path | None, saida: Path, largura: int, altura: int, rascunho: bool, tmp: Path,
                  codec: str | None = None) -> str:
    """UMA passada do ffmpeg: trims dos trechos + quadros das transições → concat → setpts por quadro (60 q/s CFR) +
    o áudio da mixagem. Filtro longo vai por arquivo (`-/filter_complex`). Devolve o codificador usado.
    `codec` fixa o codificador (blocos: todos iguais); sem ele, NVENC e x264 se falhar."""
    entradas, filtros, rot = [], [], []
    for k, p in enumerate(pcs):
        if p["tipo"] == "trecho":
            entradas += ["-i", p["arquivo"]]
            filtros.append(f"[{k}:v]trim=start_frame={p['de']}:end_frame={p['ate']},setpts=PTS-STARTPTS,"
                           f"scale={largura}:{altura},setsar=1,format=yuv420p[v{k}]")
        else:
            entradas += ["-framerate", str(FPS), "-start_number", "0", "-i", str(Path(p["pasta"]) / "q%06d.png")]
            filtros.append(f"[{k}:v]setpts=PTS-STARTPTS,scale={largura}:{altura},setsar=1,format=yuv420p[v{k}]")
        rot.append(f"[v{k}]")
    filtros.append(f"{''.join(rot)}concat=n={len(pcs)}:v=1:a=0,setpts=N/({FPS}*TB)[v]")
    script = tmp / "filtro_video.txt"
    script.write_text(";\n".join(filtros), encoding="utf-8")
    mapa = ["-map", "[v]"]
    if audio:
        entradas += ["-i", str(audio)]
        mapa += ["-map", f"{len(pcs)}:a", "-c:a", "aac", "-b:a", "256k" if rascunho else "320k", "-ar", "48000"]
    opcoes = [codec] if codec else ["h264_nvenc", "libx264"]
    for cod in [parametros_codec(c, rascunho) for c in opcoes]:
        cmd = ["ffmpeg", "-y", "-v", "error", *entradas, "-/filter_complex", str(script), *mapa, "-c:v", *cod,
               "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr", "-g", "120", "-movflags", "+faststart", str(saida)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return cod[0]
        erro = r.stderr[-1500:]
    raise RuntimeError(f"ffmpeg (vídeo final) falhou: {erro}")
