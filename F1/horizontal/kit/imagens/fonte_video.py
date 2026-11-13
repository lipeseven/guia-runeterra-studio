# Acesso ao vídeo da fonte sem baixar o vídeo inteiro: metadados (yt-dlp -J), quadros soltos por busca HTTP
# (ffmpeg -ss na URL do fluxo), legendas automáticas (texto pequeno) e recorte só do trecho escolhido.
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from caminhos import CACHE

_FLUXOS: dict[tuple[str, int], str] = {}


def _ytdlp(*args: str, texto=True) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "yt_dlp", "--no-warnings", "--encoding", "utf-8", *args],
                          capture_output=True, text=texto, encoding="utf-8" if texto else None,
                          errors="replace" if texto else None)


def _ffmpeg() -> str:
    f = shutil.which("ffmpeg")
    if not f:
        raise RuntimeError("ffmpeg não está no PATH")
    return f


def id_video(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url)
    return m.group(1) if m else re.sub(r"\W", "_", url)[-40:]


def info(url: str) -> dict:
    arq = CACHE / "videos" / f"{id_video(url)}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    p = _ytdlp("-J", "--skip-download", url)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp não leu {url}: {p.stderr[-400:]}")
    d = json.loads(p.stdout)
    meta = {k: d.get(k) for k in ("id", "title", "channel", "uploader", "upload_date", "duration",
                                  "webpage_url", "license", "channel_url")}
    meta["description"] = (d.get("description") or "")[:3000]
    meta["chapters"] = d.get("chapters")
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def buscar(consulta: str, n: int = 10) -> list[dict]:
    """Busca no YouTube (só a lista: id, título, canal, duração)."""
    p = _ytdlp("--flat-playlist", "--print", "%(id)s\t%(duration)s\t%(channel)s\t%(title)s", f"ytsearch{n}:{consulta}")
    saida = []
    for linha in p.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) == 4:
            vid, dur, canal, titulo = partes
            saida.append({"id": vid, "duration": float(dur) if dur not in ("NA", "None", "") else None,
                          "channel": canal, "title": titulo, "webpage_url": f"https://www.youtube.com/watch?v={vid}"})
    return saida


def fluxo(url: str, altura: int = 1080) -> str:
    """URL direta do fluxo de vídeo (H.264, sem áudio). Expira em algumas horas: fica só em memória."""
    chave = (url, altura)
    if chave not in _FLUXOS:
        p = _ytdlp("-f", f"bv*[height<={altura}][vcodec^=avc1]/bv*[height<={altura}]", "-g", url)
        if p.returncode != 0 or not p.stdout.strip():
            raise RuntimeError(f"yt-dlp não deu o fluxo de {url}: {p.stderr[-400:]}")
        _FLUXOS[chave] = p.stdout.strip().splitlines()[0]
    return _FLUXOS[chave]


def quadro(fonte: str, t: float):
    """Um quadro no instante t (s) de uma URL de fluxo ou arquivo local. None se não leu."""
    import cv2
    p = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{t:.3f}", "-i", fonte, "-frames:v", "1",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if not p.stdout:
        return None
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


def recortar(url: str, ini: float, dur: float, destino: Path, altura: int = 1080) -> Path:
    """Baixa SÓ o trecho [ini, ini+dur] (vídeo, sem áudio), H.264 CRF 18."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-ss", f"{ini:.3f}", "-i", fluxo(url, altura), "-t", f"{dur:.3f}",
                        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(destino)], capture_output=True, text=True)
    if p.returncode != 0 or not destino.exists():
        raise RuntimeError(f"ffmpeg não recortou {url} {ini}+{dur}: {p.stderr[-400:]}")
    return destino


def duracao_arquivo(caminho: Path) -> float:
    p = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(caminho)], capture_output=True, text=True)
    return float(p.stdout.strip() or 0)


def quadros_arquivo(caminho: Path, passo: float = 0.5) -> list[tuple[float, object]]:
    """Quadros de um arquivo local a cada `passo` s (para validar o trecho já recortado)."""
    import cv2
    cap = cv2.VideoCapture(str(caminho))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    saida, t = [], 0.0
    while True:
        i = int(round(t * fps))
        if n and i >= n:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, img = cap.read()
        if not ok:
            break
        saida.append((round(t, 3), img))
        t += passo
    cap.release()
    return saida


def legendas(url: str, idioma: str = "en") -> list[dict]:
    """Legendas (manuais ou automáticas) como [{"i", "f", "texto"}]. Lista vazia se não houver."""
    vid = id_video(url)
    pasta = CACHE / "legendas"
    pronto = pasta / f"{vid}.{idioma}.json"
    if pronto.exists():
        return json.loads(pronto.read_text(encoding="utf-8"))
    pasta.mkdir(parents=True, exist_ok=True)
    _ytdlp("--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", idioma, "--sub-format", "vtt",
           "-o", str(pasta / f"{vid}.%(ext)s"), url)
    vtts = sorted(pasta.glob(f"{vid}*.vtt"))
    itens: list[dict] = []
    if vtts:
        itens = _ler_vtt(vtts[0].read_text(encoding="utf-8", errors="replace"))
    pronto.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    return itens


def _seg(h: str) -> float:
    p = h.replace(",", ".").split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))


def _ler_vtt(txt: str) -> list[dict]:
    itens, vistos = [], set()
    for bloco in re.split(r"\n\s*\n", txt):
        m = re.search(r"([\d:.]+)\s*-->\s*([\d:.]+)", bloco)
        if not m:
            continue
        linhas = [re.sub(r"<[^>]+>", "", l).strip() for l in bloco.splitlines()[1:] if "-->" not in l]
        texto = " ".join(l for l in linhas if l)
        if texto and (m.group(1), texto) not in vistos:
            vistos.add((m.group(1), texto))
            itens.append({"i": _seg(m.group(1)), "f": _seg(m.group(2)), "texto": texto})
    return itens
