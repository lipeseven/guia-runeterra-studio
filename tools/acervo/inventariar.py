"""Inventaria o acervo local: dados técnicos, miniaturas e duplicatas.

Uso:
    .venv\\Scripts\\python.exe tools\\acervo\\inventariar.py

Incremental: arquivos já inventariados e sem alteração são pulados.
Não altera nem move nada na pasta do acervo.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import imagehash
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import PASTA_ACERVO, PASTA_MINIATURAS, CONFIG, RAIZ, abrir_acervo, preparar_ffmpeg  # noqa: E402

TIPOS = {
    ".jpg": "imagem", ".jpeg": "imagem", ".jfif": "imagem", ".jpg_large": "imagem",
    ".png": "imagem", ".webp": "imagem", ".avif": "imagem", ".bmp": "imagem",
    ".gif": "gif",
    ".mp4": "video", ".webm": "video", ".mov": "video", ".mkv": "video",
    ".m4a": "audio", ".mp3": "audio", ".wav": "audio", ".ogg": "audio",
    ".pdf": "pdf",
}
LARGURA = CONFIG["acervo"]["largura_miniatura"]


def prefixo(nome: str) -> str:
    return re.sub(r"[\s_]*\d+$", "", Path(nome).stem.lower()).strip()


def sha1(caminho: Path) -> str:
    h = hashlib.sha1()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ffprobe(caminho: Path) -> dict:
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height",
         "-of", "json", str(caminho)],
        capture_output=True, text=True,
    )
    dados = json.loads(saida.stdout or "{}")
    larg = next((s.get("width") for s in dados.get("streams", []) if s.get("width")), None)
    alt = next((s.get("height") for s in dados.get("streams", []) if s.get("height")), None)
    dur = dados.get("format", {}).get("duration")
    return {"largura": larg, "altura": alt, "duracao": float(dur) if dur else None}


def quadro_video(caminho: Path, t: float) -> Image.Image:
    png = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(caminho), "-frames:v", "1",
         "-vf", f"scale={LARGURA}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True,
    ).stdout
    return Image.open(BytesIO(png)).convert("RGB")


def tem_transparencia(img: Image.Image) -> bool:
    if img.mode not in ("RGBA", "LA", "PA") and "transparency" not in img.info:
        return False
    alfa = img.convert("RGBA").getchannel("A")
    # Considera transparente se uma parte relevante da imagem é (quase) invisível.
    return sum(alfa.histogram()[:16]) / (img.width * img.height) > 0.05


def sobre_branco(img: Image.Image) -> Image.Image:
    fundo = Image.new("RGB", img.size, "white")
    fundo.paste(img, mask=img.convert("RGBA").getchannel("A"))
    return fundo


# Acervo baixado da internet (importadores, busca no storyboard): fora da pasta do Felipe, que só é lida. O caminho
# fica ABSOLUTO no banco — `PASTA_ACERVO / caminho` continua funcionando em todo o sistema.
PASTAS_EXTRA = [RAIZ / "dados" / "acervo_internet"]


def caminho_no_banco(p: Path) -> str:
    try:
        return str(p.relative_to(PASTA_ACERVO))
    except ValueError:
        return p.as_posix()


def processar(caminho: Path) -> dict:
    rel = caminho_no_banco(caminho)
    ext = caminho.suffix.lower()
    tipo = TIPOS[ext]
    info = {
        "caminho": rel, "nome": caminho.name, "ext": ext, "tipo": tipo,
        "bytes": caminho.stat().st_size, "mtime": caminho.stat().st_mtime,
        "sha1": sha1(caminho), "prefixo": prefixo(caminho.name),
        "phash": None, "largura": None, "altura": None, "duracao": None, "transparente": 0,
        "miniatura": None, "erro": None,
    }
    try:
        if tipo in ("imagem", "gif"):
            with Image.open(caminho) as img:
                info["largura"], info["altura"] = img.size
                img.seek(0)
                transp = tem_transparencia(img)
                base = sobre_branco(img) if transp else img.convert("RGB")
                info["transparente"] = int(transp)
                info["phash"] = str(imagehash.phash(base))
                if tipo == "gif":
                    total_ms = 0
                    for i in range(getattr(img, "n_frames", 1)):
                        img.seek(i)
                        total_ms += img.info.get("duration", 0)
                    info["duracao"] = total_ms / 1000 or None
                info["miniatura"] = ImageOps.contain(base, (LARGURA, LARGURA))
        elif tipo == "video":
            info.update(ffprobe(caminho))
            d = info["duracao"] or 1
            quadros = [quadro_video(caminho, d * p) for p in (0.1, 0.5, 0.9)]
            w, h = quadros[0].size
            tira = Image.new("RGB", (w, h * 3))
            for i, q in enumerate(quadros):
                tira.paste(q, (0, i * h))
            info["phash"] = str(imagehash.phash(quadros[1]))
            info["miniatura"] = ImageOps.contain(tira, (LARGURA, LARGURA))
        elif tipo == "audio":
            info.update(ffprobe(caminho))
    except Exception as e:  # um arquivo ruim não deve parar o inventário
        info["erro"] = f"{type(e).__name__}: {e}"
    return info


def main() -> None:
    preparar_ffmpeg()
    PASTA_MINIATURAS.mkdir(parents=True, exist_ok=True)
    con = abrir_acervo()
    conhecidos = {r["caminho"]: r["mtime"] for r in con.execute("SELECT caminho, mtime FROM midias")}

    raizes = [PASTA_ACERVO] + [p for p in PASTAS_EXTRA if p.exists()]
    todos = [p for r in raizes for p in r.rglob("*") if p.is_file()]
    arquivos = [p for p in todos if p.suffix.lower() in TIPOS]
    ignorados = [p.name for p in todos if p.suffix.lower() not in TIPOS]
    novos = [p for p in arquivos if conhecidos.get(caminho_no_banco(p)) != p.stat().st_mtime]
    print(f"{len(arquivos)} arquivos no acervo, {len(novos)} novos/alterados", flush=True)

    erros = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, info in enumerate(pool.map(processar, novos), 1):
            mini = info.pop("miniatura")
            erro = info.pop("erro")
            con.execute(
                """INSERT INTO midias (caminho, nome, ext, tipo, bytes, mtime, sha1, phash,
                       largura, altura, duracao, transparente, prefixo)
                   VALUES (:caminho, :nome, :ext, :tipo, :bytes, :mtime, :sha1, :phash,
                       :largura, :altura, :duracao, :transparente, :prefixo)
                   ON CONFLICT(caminho) DO UPDATE SET
                       bytes=excluded.bytes, mtime=excluded.mtime, sha1=excluded.sha1,
                       phash=excluded.phash, largura=excluded.largura, altura=excluded.altura,
                       duracao=excluded.duracao, transparente=excluded.transparente""",
                info)
            mid = con.execute("SELECT id FROM midias WHERE caminho=?", (info["caminho"],)).fetchone()[0]
            if mini is not None:
                mini.save(PASTA_MINIATURAS / f"{mid}.jpg", quality=85)
            if erro:
                erros.append(f"{info['nome']}: {erro}")
            if n % 100 == 0:
                con.commit()
                print(f"  {n}/{len(novos)}", flush=True)
    con.commit()

    # Duplicatas exatas (mesmo conteúdo) e quase-duplicatas (mesma imagem, outro formato/tamanho)
    exatas = con.execute(
        "SELECT sha1, group_concat(nome, ' = ') FROM midias GROUP BY sha1 HAVING count(*) > 1").fetchall()
    imgs = [(r["nome"], imagehash.hex_to_hash(r["phash"]))
            for r in con.execute("SELECT nome, phash FROM midias WHERE phash IS NOT NULL AND tipo='imagem'")]
    parecidas = [(a, b, ha - hb) for i, (a, ha) in enumerate(imgs) for b, hb in imgs[i + 1:] if ha - hb <= 4]

    print(f"\nDuplicatas exatas: {len(exatas)}")
    for _, nomes in exatas:
        print("  ", nomes)
    print(f"Quase-duplicatas (mesma imagem): {len(parecidas)}")
    for a, b, d in parecidas:
        print(f"   {a} ~ {b} (distância {d})")
    if ignorados:
        print(f"Ignorados (formato não suportado): {ignorados}")
    if erros:
        print(f"Erros ({len(erros)}):")
        for e in erros:
            print("  ", e)
    print("\nResumo por tipo:")
    for r in con.execute("SELECT tipo, count(*), sum(transparente) FROM midias GROUP BY tipo"):
        print(f"   {r[0]}: {r[1]} (com transparência: {r[2]})")


if __name__ == "__main__":
    main()
