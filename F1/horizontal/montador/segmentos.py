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


def _juncao_remotion() -> Path:
    nm = node_modules()
    junc = HORIZ / "remotion" / "node_modules"
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


def renderizar(job: dict, pasta: Path, largura: int, altura: int, rascunho: bool = True, forcar: bool = False) -> dict:
    """Trecho da cena (cache por hash + resolução). Devolve {arquivo, quadros, hash, do_cache, ajuste}."""
    trechos = Path(pasta) / "trechos"
    trechos.mkdir(parents=True, exist_ok=True)
    chave = f"{job['cena']}_{job['hash']}_{largura}x{altura}"
    mp4, meta = trechos / f"{chave}.mp4", trechos / f"{chave}.json"
    if mp4.exists() and meta.exists() and not forcar:
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("quadros") == job["quadros"]:
            return {**m, "arquivo": str(mp4), "do_cache": True}
    tmp = trechos / f"_tmp_{chave}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        quadros_dir = tmp / "png"
        if job["motor"] == "remotion":
            _render_remotion(job, largura, altura, quadros_dir, tmp)
        else:
            _render_hyperframes(job, largura, altura, quadros_dir, tmp)
        pngs = sorted(quadros_dir.rglob("*.png"))
        ajuste = len(pngs) - job["quadros"]
        if ajuste < 0:
            raise FalhaRender(f"cena {job['cena']} ({job['motor']}): {len(pngs)} quadros renderizados, esperados {job['quadros']}")
        # quadro a mais de algum motor (instante final inclusivo) fica de fora e é registrado em `ajuste`
        # (medido em 2026-11-13: 0 nos dois motores com duração = quadros/60)
        pngs = pngs[: job["quadros"]]
        _codificar(pngs, largura, altura, mp4, tmp, rascunho)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = contar_quadros(mp4)
    if n != job["quadros"]:
        raise FalhaRender(f"trecho {mp4.name}: {n} quadros no MP4, esperados {job['quadros']}")
    m = {"cena": job["cena"], "motor": job["motor"], "hash": job["hash"], "quadros": n, "pre": job["pre"], "pos": job["pos"],
         "largura": largura, "altura": altura, "ajuste_quadros_motor": ajuste}
    meta.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**m, "arquivo": str(mp4), "do_cache": False}
