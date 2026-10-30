"""Detecta os cortes de cena dos vídeos de referência e gera folhas de contato.

Uso:
    .venv\\Scripts\\python.exe tools\\analise_referencias\\detectar_cortes.py

Para cada vídeo em dados/runeterra/referencias, cria em
dados/runeterra/analise_referencias/<slug>/:
    cortes.json      -> lista de cenas (início, fim, duração)
    quadros/         -> primeiro quadro de cada cena (miniatura)
    folhas/          -> grades de miniaturas com o tempo de cada cena
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tools"))
from canal import caminho  # noqa: E402  (pasta de referências DO CANAL: GRS_CANAL)

PASTA_VIDEOS = caminho("referencias")
PASTA_SAIDA = caminho("analise")

LIMIAR_CENA = 0.30          # sensibilidade do detector de corte (0-1)
LARGURA_MINIATURA = 320
COLUNAS, LINHAS = 8, 6      # 48 miniaturas por folha de contato


def slug(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")[:120]


def duracao(video: Path) -> float:
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    )
    return float(saida.stdout.strip())


def detectar(video: Path) -> dict:
    destino = PASTA_SAIDA / slug(video.stem)
    if (destino / "cortes.json").exists():
        return json.loads((destino / "cortes.json").read_text(encoding="utf-8"))
    quadros = destino / "quadros"
    quadros.mkdir(parents=True, exist_ok=True)
    for antigo in quadros.glob("*.jpg"):
        antigo.unlink()

    # Uma única passada: detecta o corte e já salva o primeiro quadro da cena.
    # O quadro 0 entra sempre (eq(n,0)) para a primeira cena ter miniatura.
    filtro = (
        f"fps=30,scale={LARGURA_MINIATURA}:-2,"
        f"select='eq(n\\,0)+gt(scene\\,{LIMIAR_CENA})',showinfo"
    )
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-hwaccel", "cuda", "-i", str(video),
         "-an", "-vf", filtro, "-fps_mode", "vfr", "-q:v", "4",
         str(quadros / "%05d.jpg")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou em {video.name}:\n{proc.stderr[-2000:]}")

    inicios = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
    total = duracao(video)
    cenas = []
    for i, inicio in enumerate(inicios):
        fim = inicios[i + 1] if i + 1 < len(inicios) else total
        cenas.append({
            "n": i + 1,
            "inicio": round(inicio, 3),
            "fim": round(fim, 3),
            "duracao": round(fim - inicio, 3),
            "quadro": f"quadros/{i + 1:05d}.jpg",
        })

    resultado = {"video": video.name, "duracao_total": round(total, 3), "cenas": cenas}
    (destino / "cortes.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    montar_folhas(destino, cenas)
    return resultado


def tempo(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m:02d}:{s:02d}"


def montar_folhas(destino: Path, cenas: list[dict]) -> None:
    folhas = destino / "folhas"
    folhas.mkdir(exist_ok=True)
    for antiga in folhas.glob("*.jpg"):
        antiga.unlink()
    if not cenas:
        return

    fonte = ImageFont.truetype("arial.ttf", 16)
    w = LARGURA_MINIATURA
    h = Image.open(destino / cenas[0]["quadro"]).height
    por_folha = COLUNAS * LINHAS
    for f in range(0, len(cenas), por_folha):
        lote = cenas[f:f + por_folha]
        folha = Image.new("RGB", (COLUNAS * w, LINHAS * h), "black")
        desenho = ImageDraw.Draw(folha)
        for i, cena in enumerate(lote):
            x, y = (i % COLUNAS) * w, (i // COLUNAS) * h
            caminho = destino / cena["quadro"]
            if caminho.exists():
                folha.paste(Image.open(caminho), (x, y))
            rotulo = f"#{cena['n']} {tempo(cena['inicio'])} ({cena['duracao']:.1f}s)"
            desenho.rectangle([x, y, x + 175, y + 20], fill="black")
            desenho.text((x + 3, y + 1), rotulo, fill="yellow", font=fonte)
        folha.save(folhas / f"folha_{f // por_folha + 1:03d}.jpg", quality=85)


def main() -> None:
    videos = sorted(PASTA_VIDEOS.glob("*.mp4"))
    if not videos:
        sys.exit(f"Nenhum vídeo encontrado em {PASTA_VIDEOS}")
    with ThreadPoolExecutor(max_workers=3) as pool:
        for r in pool.map(detectar, videos):
            duracoes = [c["duracao"] for c in r["cenas"]]
            media = sum(duracoes) / len(duracoes)
            print(f"{r['video']}: {len(duracoes)} cenas, média {media:.2f}s", flush=True)


if __name__ == "__main__":
    main()
