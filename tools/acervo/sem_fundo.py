"""Remove fundo de COR LISA (preto, branco, qualquer cor sólida) de uma imagem — local, instantâneo, sem IA.

Apaga só a cor que ENCOSTA nas bordas (preenchimento a partir das bordas): o preto em volta de um ícone redondo some,
mas o preto DENTRO do desenho fica. O resultado é um PNG com transparência, recortado, salvo à parte em
dados/acervo/derivados/ — o arquivo do acervo nunca é alterado.

Uso:  .venv\\Scripts\\python.exe tools\\acervo\\sem_fundo.py <arquivo> [saida.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import RAIZ  # noqa: E402

DERIVADOS = RAIZ / "dados" / "acervo" / "derivados"


def remover_fundo(origem: Path, destino: Path, tolerancia: float = 42.0) -> Path:
    with Image.open(origem) as im:
        im.seek(0)
        rgba = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, alfa = rgba[:, :, :3], rgba[:, :, 3]
    h, w = alfa.shape
    borda = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    cor = np.median(borda, axis=0)  # a cor do fundo é a que domina as bordas
    perto = (np.linalg.norm(rgb - cor, axis=2) < tolerancia) | (alfa < 10)
    n, rotulos = cv2.connectedComponents(perto.astype(np.uint8), connectivity=4)
    tocam = set(np.unique(np.concatenate([rotulos[0], rotulos[-1], rotulos[:, 0], rotulos[:, -1]]))) - {0}
    fundo = np.isin(rotulos, list(tocam)) & perto
    # borda suave (sem serrilhado): desfoca só a máscara
    mascara = cv2.GaussianBlur((~fundo).astype(np.float32), (0, 0), 1.2)
    novo_alfa = np.minimum(alfa, mascara * 255)
    out = Image.fromarray(np.dstack([rgb, novo_alfa]).astype(np.uint8), "RGBA")
    caixa = Image.fromarray((novo_alfa > 20).astype(np.uint8) * 255).getbbox()
    destino.parent.mkdir(parents=True, exist_ok=True)
    (out.crop(caixa) if caixa else out).save(destino)
    return destino


def sem_fundo_da_midia(midia_id: int, origem: Path) -> Path:
    """Versão sem fundo de uma mídia do acervo (cache: refaz só se o original mudou)."""
    destino = DERIVADOS / f"sem_fundo_{midia_id}.png"
    if not destino.exists() or destino.stat().st_mtime < origem.stat().st_mtime:
        remover_fundo(origem, destino)
    return destino


if __name__ == "__main__":
    o = Path(sys.argv[1])
    print(remover_fundo(o, Path(sys.argv[2]) if len(sys.argv) > 2 else DERIVADOS / f"{o.stem}_sem_fundo.png"))
