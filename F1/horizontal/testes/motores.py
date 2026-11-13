"""Funções comuns dos testes de render do kit nos DOIS motores (foco, cartões, transições).

- `construir_global(ts, nome)`: esbuild do núcleo TS em IIFE (`window.<nome>`) para o HyperFrames;
- `render_remotion(pasta_exemplo, composicao, destino, props)`: PNG quadro a quadro (Remotion 4.0.539 do F1/video);
- `render_hyperframes(index_html, assets, destino)`: PNG quadro a quadro (npx hyperframes@0.9.20, nada global);
- `quadros`, `folha` (folha de sequência JPG), `comparar` (diferença média entre os motores).
O padrão é o de `testes/anotacao/rodar.py` (junção LOCAL de node_modules ao lado do exemplo, nunca em remotion/node_modules).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HORIZ = Path(__file__).resolve().parents[1]
RAIZ = HORIZ.parents[1]
HF_VERSAO = "hyperframes@0.9.20"


def node_modules() -> Path:
    """F1/video/node_modules deste checkout ou, numa worktree, o da pasta principal do repositório."""
    for base in [RAIZ, *RAIZ.parents]:
        p = base / "F1" / "video" / "node_modules"
        if (p / "@remotion" / "cli").is_dir():
            return p
    raise SystemExit("F1/video/node_modules não encontrado (rode npm install em F1/video na pasta principal)")


NM = node_modules()
NAVEGADOR = NM / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print((r.stdout or "")[-3000:], (r.stderr or "")[-3000:])
        raise SystemExit(f"falhou: {' '.join(map(str, cmd[:4]))}")
    return r


def construir_global(ts: Path, nome: str) -> Path:
    """kit/<x>/<x>.ts → kit/<x>/<x>.global.js (IIFE window.<nome>). Gerado: não editar à mão."""
    esbuild = NM / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    out = ts.with_name(ts.stem + ".global.js")
    rel = ts.relative_to(RAIZ).as_posix()
    sh([esbuild, ts.name, "--bundle", "--format=iife", f"--global-name={nome}", "--target=es2019", "--charset=utf8",
        f"--banner:js=// GERADO por esbuild de {rel} (F1/horizontal/testes/motores.py). Não editar à mão.",
        f"--outfile={out.name}", "--log-level=warning"], cwd=ts.parent)
    return out


def kit_json(cli: Path, *args: str):
    return json.loads(sh(["node", cli, *args]).stdout)


def render_remotion(pasta_exemplo: Path, composicao: str, destino: Path, props: dict | None = None) -> None:
    """pasta_exemplo = F1/horizontal/remotion/<modulo>/exemplo (com index.tsx que chama registerRoot)."""
    if not (HORIZ / "remotion" / "node_modules" / "remotion").is_dir():
        junc = pasta_exemplo.parent / "node_modules"
        if not junc.exists():
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junc), str(NM)], check=True, capture_output=True)
    if destino.exists():
        shutil.rmtree(destino)
    cli = NM / "@remotion" / "cli" / "remotion-cli.js"
    cmd = ["node", cli, "render", "index.tsx", composicao, destino, "--sequence", "--image-format=png",
           f"--browser-executable={NAVEGADOR}", "--log=error"]
    if props:
        cmd.append("--props=" + json.dumps(props))
    sh(cmd, cwd=pasta_exemplo)


def render_hyperframes(index_html: Path, assets: dict[str, str | Path], destino: Path, projeto: Path) -> None:
    """Monta a pasta do projeto (index.html + assets/<nome> = conteúdo ou arquivo) e renderiza PNG quadro a quadro."""
    if projeto.exists():
        shutil.rmtree(projeto)
    (projeto / "assets").mkdir(parents=True)
    shutil.copy2(index_html, projeto / "index.html")
    for nome, v in assets.items():
        alvo = projeto / "assets" / nome
        if isinstance(v, Path):
            shutil.copy2(v, alvo)
        else:
            alvo.write_text(v, encoding="utf-8")
    (projeto / "package.json").write_text(json.dumps({"name": "exemplo-kit", "private": True, "type": "module"}), encoding="utf-8")
    if destino.exists():
        shutil.rmtree(destino)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    sh([npx, "--yes", HF_VERSAO, "render", "--format", "png-sequence", "--output", destino, "--quiet"], cwd=projeto)


def quadros(pasta: Path) -> list[Path]:
    return sorted(pasta.rglob("*.png"))


def img(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)


def comparar(a: list[Path], b: list[Path], passo: int = 5) -> dict:
    """Diferença média por quadro entre os dois motores (0–255) e o pior quadro."""
    difs = []
    for q in range(0, min(len(a), len(b)), passo):
        difs.append((float(np.abs(img(a[q]) - img(b[q])).mean()), q))
    return {"media": round(sum(d for d, _ in difs) / len(difs), 3), "pior": {"q": max(difs)[1], "dif": round(max(difs)[0], 3)}}


FONTE_ROT = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)


def folha(arquivos: list[Path], idx: list[int], corte, larg: int, cols: int, titulo: str, out: Path, fps: int = 60) -> None:
    ims = []
    for q in idx:
        im = Image.open(arquivos[q]).convert("RGB")
        if corte:
            im = im.crop(corte)
        h = round(im.height * larg / im.width)
        im = im.resize((larg, h), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 118, 30], fill=(20, 20, 20))
        d.text((6, 3), f"q{q} {q / fps:.3f}s", font=FONTE_ROT, fill=(255, 255, 255))
        ims.append(im)
    rows = math.ceil(len(ims) / cols)
    W, H = ims[0].size
    sheet = Image.new("RGB", (cols * W + (cols + 1) * 4, rows * H + (rows + 1) * 4 + 44), (90, 90, 90))
    ImageDraw.Draw(sheet).text((8, 8), titulo, font=FONTE_ROT, fill=(255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, (4 + (i % cols) * (W + 4), 48 + (i // cols) * (H + 4)))
    sheet.save(out, quality=86)
