"""Indexa os clipes de vídeo do acervo por TOMADAS (trechos entre cortes) e permite buscar por significado.

Indexar (incremental):
    .venv\\Scripts\\python.exe tools\\acervo\\indexar_clipes.py indexar
Buscar uma tomada (termos em inglês funcionam melhor):
    .venv\\Scripts\\python.exe tools\\acervo\\indexar_clipes.py buscar "masked swordsman fighting a demon" [-n 8]

Cada tomada guarda início/fim (s) dentro do clipe e uma miniatura do quadro do meio.
Vetores CLIP em dados/acervo/clip_tomadas.npz.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import DADOS_ACERVO, PASTA_ACERVO, RAIZ, abrir_acervo, preparar_ffmpeg  # noqa: E402

PASTA_TOMADAS = DADOS_ACERVO / "tomadas"
ARQUIVO = DADOS_ACERVO / "clip_tomadas.npz"
LIMIAR = 0.30
MINIMA = 0.6  # tomadas mais curtas que isso (flashes, transições) não entram

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tomadas (
    id        INTEGER PRIMARY KEY,
    midia_id  INTEGER NOT NULL REFERENCES midias(id),
    n         INTEGER NOT NULL,
    inicio    REAL NOT NULL,
    fim       REAL NOT NULL,
    UNIQUE (midia_id, n)
);
"""


def cortes(caminho: Path) -> list[float]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-hwaccel", "cuda", "-i", str(caminho), "-an",
         "-vf", f"fps=15,scale=320:-2,select='gt(scene\\,{LIMIAR})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]


def miniatura(caminho: Path, t: float, destino: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(caminho), "-frames:v", "1",
                    "-vf", "scale=384:-2", "-q:v", "4", str(destino)], check=True)


def processar(item: tuple[int, str, float]) -> tuple[int, list[tuple[float, float]]]:
    mid, rel, duracao = item
    caminho = PASTA_ACERVO / rel
    limites = [0.0] + cortes(caminho) + [duracao]
    tomadas = [(a, b) for a, b in zip(limites, limites[1:]) if b - a >= MINIMA]
    for n, (a, b) in enumerate(tomadas):
        miniatura(caminho, (a + b) / 2, PASTA_TOMADAS / f"{mid}_{n}.jpg")
    return mid, tomadas


def indexar() -> None:
    preparar_ffmpeg()
    PASTA_TOMADAS.mkdir(parents=True, exist_ok=True)
    con = abrir_acervo()
    con.executescript(ESQUEMA)
    feitos = {r[0] for r in con.execute("SELECT DISTINCT midia_id FROM tomadas")}
    pendentes = [(r["id"], r["caminho"], r["duracao"]) for r in con.execute(
        "SELECT id, caminho, duracao FROM midias WHERE tipo='video' AND duracao IS NOT NULL")
        if r["id"] not in feitos]
    print(f"{len(pendentes)} clipes para indexar", flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for mid, tomadas in pool.map(processar, pendentes):
            con.executemany("INSERT OR REPLACE INTO tomadas (midia_id, n, inicio, fim) VALUES (?,?,?,?)",
                            [(mid, n, round(a, 3), round(b, 3)) for n, (a, b) in enumerate(tomadas)])
            con.commit()
            print(f"  #{mid}: {len(tomadas)} tomadas", flush=True)
    vetorizar(con)


def vetorizar(con) -> None:
    import torch
    from PIL import Image
    from busca_semantica import DISPOSITIVO, modelo

    ids_antigos = np.load(ARQUIVO)["ids"] if ARQUIVO.exists() else np.zeros(0, dtype=np.int64)
    vet_antigos = np.load(ARQUIVO)["vetores"] if ARQUIVO.exists() else np.zeros((0, 768), dtype=np.float32)
    feitos = set(ids_antigos.tolist())
    linhas = [r for r in con.execute("SELECT id, midia_id, n FROM tomadas") if r["id"] not in feitos]
    if not linhas:
        return
    m, prep, _ = modelo()
    novos_ids, novos_vet = [], []
    with torch.no_grad():
        for i in range(0, len(linhas), 64):
            lote = linhas[i:i + 64]
            imgs = torch.stack([prep(Image.open(PASTA_TOMADAS / f"{r['midia_id']}_{r['n']}.jpg").convert("RGB"))
                                for r in lote]).to(DISPOSITIVO)
            with torch.autocast(DISPOSITIVO, enabled=DISPOSITIVO == "cuda"):
                v = m.encode_image(imgs).float()
            novos_vet.append((v / v.norm(dim=-1, keepdim=True)).cpu().numpy())
            novos_ids += [r["id"] for r in lote]
    np.savez(ARQUIVO, ids=np.concatenate([ids_antigos, np.array(novos_ids, dtype=np.int64)]),
             vetores=np.concatenate([vet_antigos] + novos_vet))
    print(f"Vetores de tomadas: {len(feitos) + len(novos_ids)}")


def buscar(texto: str, n: int = 8) -> list[dict]:
    import torch
    from busca_semantica import DISPOSITIVO, modelo

    d = np.load(ARQUIVO)
    m, _, tok = modelo()
    with torch.no_grad(), torch.autocast(DISPOSITIVO, enabled=DISPOSITIVO == "cuda"):
        t = m.encode_text(tok([texto]).to(DISPOSITIVO)).float()
    t = (t / t.norm(dim=-1, keepdim=True)).cpu().numpy()[0]
    notas = d["vetores"] @ t
    con = abrir_acervo()
    saida = []
    for i in np.argsort(-notas)[:n]:
        r = con.execute("SELECT t.id, t.midia_id, t.n, t.inicio, t.fim, m.nome FROM tomadas t "
                        "JOIN midias m ON m.id = t.midia_id WHERE t.id=?", (int(d["ids"][i]),)).fetchone()
        saida.append({**dict(r), "nota": float(notas[i])})
    return saida


def main() -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("indexar")
    b = sub.add_parser("buscar")
    b.add_argument("texto")
    b.add_argument("-n", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "indexar":
        indexar()
    else:
        for r in buscar(a.texto, a.n):
            print(f"{r['nota']:.3f}  tomada #{r['id']}  {r['nome']}  {r['inicio']:.1f}-{r['fim']:.1f}s  "
                  f"(miniatura: dados/acervo/tomadas/{r['midia_id']}_{r['n']}.jpg)")


if __name__ == "__main__":
    main()
