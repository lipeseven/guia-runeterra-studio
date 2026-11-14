"""Render de UMA cena no motor dela → trecho MP4 a 60 q/s com o número EXATO de quadros (sem áudio).

Cache por hash da receita (`receitas.receita`): `<pasta>/trechos/<cena>_<hash>.mp4` + `.json`. Mesmo hash = não
renderiza de novo; cena mudada (texto, dados, tempos, transição vizinha, código do kit/adaptador) = hash novo.
Os motores renderizam PNG quadro a quadro (o mesmo caminho medido nos testes dos kits) e o ffmpeg codifica o trecho.

Remotion 4.0.539 (o `node_modules` do F1/video, por junção LOCAL em F1/horizontal/remotion/node_modules, fora do Git)
e HyperFrames 0.9.20 (`npx --yes hyperframes@0.9.20`, nada global). A cena HyperFrames carrega gsap e three.js do CDN
(como os exemplos dos kits): sem internet, o render dela falha com a mensagem do motor.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import receitas as R

HORIZ = R.HORIZ
FPS = R.FPS
HF_VERSAO = "hyperframes@0.9.20"


class FalhaRender(Exception):
    pass


def _sh(cmd: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise FalhaRender(f"falhou: {' '.join(map(str, cmd[:5]))}\n{(r.stdout or '')[-1500:]}\n{(r.stderr or '')[-2500:]}")
    return r


def node_modules() -> Path:
    for base in [HORIZ.parents[1], *HORIZ.parents[1].parents]:
        p = base / "F1" / "video" / "node_modules"
        if (p / "@remotion" / "cli").is_dir():
            return p
    raise FalhaRender("F1/video/node_modules não encontrado (rode npm install em F1/video na pasta principal)")


_TRAVA_JUNCAO = threading.Lock()   # montar._renderizar_paralelo chama de várias threads


def _juncao_remotion() -> Path:
    nm = node_modules()
    junc = HORIZ / "remotion" / "node_modules"
    with _TRAVA_JUNCAO:
        if not junc.exists():
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junc), str(nm)], check=True, capture_output=True)
    return nm


def _render_remotion(job: dict, largura: int, altura: int, destino: Path, tmp: Path) -> None:
    nm = _juncao_remotion()
    navegador = nm / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"
    props = tmp / "props.json"
    props.write_text(json.dumps({**job["props"], "largura": largura, "altura": altura}, ensure_ascii=False), encoding="utf-8")
    cmd = ["node", nm / "@remotion" / "cli" / "remotion-cli.js", "render", "index.tsx", "CenaDoc", destino, "--sequence",
           "--image-format=png", f"--props={props}", "--log=error", "--concurrency=4"]
    if navegador.exists():
        cmd.append(f"--browser-executable={navegador}")
    _sh(cmd, cwd=HORIZ / "remotion" / "cena")


def _render_hyperframes(job: dict, largura: int, altura: int, destino: Path, tmp: Path) -> None:
    proj = tmp / "hf"
    (proj / "assets").mkdir(parents=True)
    html = (R.AQUI / "hyperframes" / "gps.html").read_text(encoding="utf-8")
    dur = f"{job['quadros'] / FPS:.7f}"
    html = html.replace("__W__", str(largura)).replace("__H__", str(altura)).replace("__DUR__", dur)
    (proj / "index.html").write_text(html, encoding="utf-8")
    (proj / "assets" / "cfg.js").write_text("window.__CFG = " + json.dumps(job["cfg"], ensure_ascii=False) + ";\n", encoding="utf-8")
    for d in ("src", "exemplo"):
        shutil.copytree(R.KIT / "gps" / d, proj / "assets" / "kit" / "gps" / d)
    shutil.copy2(R.AQUI / "movimento.js", proj / "assets" / "movimento.js")
    for rel, origem in job["assets"].items():
        alvo = proj / "assets" / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(origem, alvo)       # modelos 3D grandes: link físico, sem copiar
        except OSError:
            shutil.copy2(origem, alvo)
    (proj / "package.json").write_text(json.dumps({"name": "cena-montador", "private": True, "type": "module"}), encoding="utf-8")
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    _sh([npx, "--yes", HF_VERSAO, "render", "--format", "png-sequence", "--output", destino, "--quiet"], cwd=proj)


def _codificar(pngs: list[Path], largura: int, altura: int, saida: Path, tmp: Path, rascunho: bool) -> None:
    seq = tmp / "seq"
    seq.mkdir()
    for k, p in enumerate(pngs):
        os.replace(p, seq / f"q{k:06d}.png")
    vf = f"scale={largura}:{altura}:flags=lanczos,setsar=1,format=yuv420p"
    _sh(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-start_number", "0", "-i", seq / "q%06d.png", "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast" if rascunho else "medium", "-crf", "14" if rascunho else "10",
         "-g", "60", "-r", str(FPS), "-an", saida])


def contar_quadros(mp4: Path) -> int:
    r = _sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
             "-of", "csv=p=0", mp4])
    return int(r.stdout.strip().split(",")[0])


TETO_LOTE_S = 45.0   # s de vídeo por invocação do Remotion no lote (medido em medir_motores.py; ver README.md)


def _chave(job: dict, largura: int, altura: int) -> str:
    return f"{job['cena']}_{job['hash']}_{largura}x{altura}"


def _do_cache(job: dict, trechos: Path, largura: int, altura: int) -> dict | None:
    chave = _chave(job, largura, altura)
    mp4, meta = trechos / f"{chave}.mp4", trechos / f"{chave}.json"
    if mp4.exists() and meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("quadros") == job["quadros"]:
            return {**m, "arquivo": str(mp4), "do_cache": True}
    return None


def _finalizar(job: dict, pngs: list[Path], trechos: Path, largura: int, altura: int, tmp: Path, rascunho: bool) -> dict:
    chave = _chave(job, largura, altura)
    mp4, meta = trechos / f"{chave}.mp4", trechos / f"{chave}.json"
    ajuste = len(pngs) - job["quadros"]
    if ajuste < 0:
        raise FalhaRender(f"cena {job['cena']} ({job['motor']}): {len(pngs)} quadros renderizados, esperados {job['quadros']}")
    # quadro a mais de algum motor (instante final inclusivo) fica de fora e é registrado em `ajuste`
    # (medido em 2026-11-13: 0 nos dois motores com duração = quadros/60)
    _codificar(pngs[: job["quadros"]], largura, altura, mp4, tmp, rascunho)
    n = contar_quadros(mp4)
    if n != job["quadros"]:
        raise FalhaRender(f"trecho {mp4.name}: {n} quadros no MP4, esperados {job['quadros']}")
    m = {"cena": job["cena"], "motor": job["motor"], "hash": job["hash"], "quadros": n, "pre": job["pre"], "pos": job["pos"],
         "largura": largura, "altura": altura, "ajuste_quadros_motor": ajuste}
    meta.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**m, "arquivo": str(mp4), "do_cache": False}


def renderizar(job: dict, pasta: Path, largura: int, altura: int, rascunho: bool = True, forcar: bool = False) -> dict:
    """Trecho da cena (cache por hash + resolução). Devolve {arquivo, quadros, hash, do_cache, ajuste}."""
    trechos = Path(pasta) / "trechos"
    trechos.mkdir(parents=True, exist_ok=True)
    if not forcar and (c := _do_cache(job, trechos, largura, altura)):
        return c
    tmp = trechos / f"_tmp_{_chave(job, largura, altura)}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        quadros_dir = tmp / "png"
        if job["motor"] == "remotion":
            _render_remotion(job, largura, altura, quadros_dir, tmp)
        else:
            _render_hyperframes(job, largura, altura, quadros_dir, tmp)
        return _finalizar(job, sorted(quadros_dir.rglob("*.png")), trechos, largura, altura, tmp, rascunho)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def lotes(jobs: list[dict], teto_s: float = TETO_LOTE_S) -> list[list[dict]]:
    """Cenas Remotion a renderizar, em lotes de até `teto_s` segundos de vídeo (cena maior que o teto = lote sozinha)."""
    out, atual, soma = [], [], 0.0
    for j in jobs:
        d = j["quadros"] / FPS
        if atual and soma + d > teto_s:
            out.append(atual)
            atual, soma = [], 0.0
        atual.append(j)
        soma += d
    if atual:
        out.append(atual)
    return out


def renderizar_lote(jobs: list[dict], pasta: Path, largura: int, altura: int, rascunho: bool = True, forcar: bool = False,
                    teto_s: float = TETO_LOTE_S) -> dict:
    """Várias cenas REMOTION numa invocação só do motor (bundle + navegador uma vez por lote, como o render por blocos
    do Runeterra): composição `LoteDoc` com as cenas em sequência; os PNGs são repartidos por cena e cada cena vira o
    PRÓPRIO trecho (mesmo cache por hash de `renderizar`). Cenas já no cache não entram no lote. {cena: resultado}."""
    trechos = Path(pasta) / "trechos"
    trechos.mkdir(parents=True, exist_ok=True)
    out, falta = {}, []
    for j in jobs:
        if j["motor"] != "remotion":
            raise FalhaRender(f"renderizar_lote é só do Remotion (cena {j['cena']} é {j['motor']})")
        c = None if forcar else _do_cache(j, trechos, largura, altura)
        if c:
            out[j["cena"]] = c
        else:
            falta.append(j)
    for k, lote in enumerate(lotes(falta, teto_s)):
        if len(lote) == 1:
            out[lote[0]["cena"]] = renderizar(lote[0], pasta, largura, altura, rascunho, forcar=True)
            continue
        tmp = trechos / f"_tmp_lote_{lote[0]['hash']}_{k}"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        try:
            nm = _juncao_remotion()
            navegador = nm / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"
            props = tmp / "props.json"
            props.write_text(json.dumps({"largura": largura, "altura": altura, "cenas": [{**j["props"], "largura": largura,
                                         "altura": altura} for j in lote]}, ensure_ascii=False), encoding="utf-8")
            cmd = ["node", nm / "@remotion" / "cli" / "remotion-cli.js", "render", "index.tsx", "LoteDoc", tmp / "png", "--sequence",
                   "--image-format=png", f"--props={props}", "--log=error", "--concurrency=4"]
            if navegador.exists():
                cmd.append(f"--browser-executable={navegador}")
            _sh(cmd, cwd=HORIZ / "remotion" / "cena")
            pngs = sorted((tmp / "png").rglob("*.png"))
            total = sum(j["quadros"] for j in lote)
            if len(pngs) < total:
                raise FalhaRender(f"lote Remotion: {len(pngs)} quadros, esperados {total}")
            ini = 0
            for j in lote:
                sub = tmp / f"cena_{j['cena']}"
                sub.mkdir()
                out[j["cena"]] = _finalizar(j, pngs[ini:ini + j["quadros"]], trechos, largura, altura, sub, rascunho)
                ini += j["quadros"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return out
