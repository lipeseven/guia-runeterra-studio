"""Busca por significado no acervo com CLIP (local, GPU).

Indexar (incremental):
    .venv\\Scripts\\python.exe tools\\acervo\\busca_semantica.py indexar
Buscar (termos em inglês funcionam melhor):
    .venv\\Scripts\\python.exe tools\\acervo\\busca_semantica.py buscar "warrior with flaming sword" [-n 10]

Os vetores ficam em dados/acervo/clip.npz (ids + vetores normalizados).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import PASTA_MINIATURAS, RAIZ, abrir_acervo  # noqa: E402

MODELO, PESOS = "ViT-L-14", "laion2b_s32b_b82k"
ARQUIVO = RAIZ / "dados" / "acervo" / "clip.npz"
DISPOSITIVO = "cuda" if torch.cuda.is_available() else "cpu"

_cache: dict = {}


def modelo():
    if not _cache:
        import open_clip
        m, _, prep = open_clip.create_model_and_transforms(MODELO, pretrained=PESOS, device=DISPOSITIVO)
        m.eval()
        _cache.update(m=m, prep=prep, tok=open_clip.get_tokenizer(MODELO))
    return _cache["m"], _cache["prep"], _cache["tok"]


def carregar() -> tuple[np.ndarray, np.ndarray]:
    if ARQUIVO.exists():
        d = np.load(ARQUIVO)
        return d["ids"], d["vetores"]
    return np.zeros(0, dtype=np.int64), np.zeros((0, 768), dtype=np.float32)


def partes(mid: int, tipo: str) -> list[Image.Image]:
    """Imagens que representam a mídia. Vídeos: a miniatura é uma tira de 3 quadros."""
    img = Image.open(PASTA_MINIATURAS / f"{mid}.jpg").convert("RGB")
    if tipo != "video":
        return [img]
    h = img.height // 3
    return [img.crop((0, i * h, img.width, (i + 1) * h)) for i in range(3)]


@torch.no_grad()
def indexar() -> None:
    con = abrir_acervo()
    ids, vetores = carregar()
    feitos = set(ids.tolist())
    pendentes = [r for r in con.execute("SELECT id, tipo FROM midias WHERE tipo IN ('imagem','gif','video')")
                 if r["id"] not in feitos and (PASTA_MINIATURAS / f"{r['id']}.jpg").exists()]
    print(f"{len(feitos)} já indexadas, {len(pendentes)} novas", flush=True)
    if not pendentes:
        return
    m, prep, _ = modelo()
    novos_ids, novos_vet = [], []
    for i in range(0, len(pendentes), 32):
        lote = pendentes[i:i + 32]
        imagens, dono = [], []
        for r in lote:
            for p in partes(r["id"], r["tipo"]):
                imagens.append(prep(p))
                dono.append(r["id"])
        with torch.autocast(DISPOSITIVO, enabled=DISPOSITIVO == "cuda"):
            v = m.encode_image(torch.stack(imagens).to(DISPOSITIVO)).float()
        v = (v / v.norm(dim=-1, keepdim=True)).cpu().numpy()
        for r in lote:  # média dos quadros para vídeos
            sel = [k for k, d in enumerate(dono) if d == r["id"]]
            media = v[sel].mean(axis=0)
            novos_ids.append(r["id"])
            novos_vet.append(media / np.linalg.norm(media))
        print(f"  {min(i + 32, len(pendentes))}/{len(pendentes)}", flush=True)
    ids = np.concatenate([ids, np.array(novos_ids, dtype=np.int64)])
    vetores = np.concatenate([vetores, np.array(novos_vet, dtype=np.float32)])
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ARQUIVO, ids=ids, vetores=vetores)
    print(f"Índice salvo: {len(ids)} mídias")


@torch.no_grad()
def buscar(texto: str, n: int = 10) -> list[tuple[int, float]]:
    ids, vetores = carregar()
    m, _, tok = modelo()
    with torch.autocast(DISPOSITIVO, enabled=DISPOSITIVO == "cuda"):
        t = m.encode_text(tok([texto]).to(DISPOSITIVO)).float()
    t = (t / t.norm(dim=-1, keepdim=True)).cpu().numpy()[0]
    notas = vetores @ t
    melhores = np.argsort(-notas)[:n]
    return [(int(ids[i]), float(notas[i])) for i in melhores]


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("indexar")
    b = sub.add_parser("buscar")
    b.add_argument("texto")
    b.add_argument("-n", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "indexar":
        indexar()
    else:
        con = abrir_acervo()
        for mid, nota in buscar(a.texto, a.n):
            nome = con.execute("SELECT nome FROM midias WHERE id=?", (mid,)).fetchone()[0]
            print(f"{nota:.3f}  #{mid}  {nome}")


if __name__ == "__main__":
    main()
