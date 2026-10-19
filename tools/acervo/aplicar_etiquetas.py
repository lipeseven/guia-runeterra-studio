"""Aplica etiquetas (escritas pelo Claude ou por você) ao banco do acervo.

Uso:
    .venv\\Scripts\\python.exe tools\\acervo\\aplicar_etiquetas.py

Lê todos os arquivos dados/acervo/etiquetas/*.json no formato:
    {"<id>": ["categoria", ["Personagem", ...], "descrição curta", "uso (opcional)"], ...}

Categorias: splash, arte, icone, recorte, meme, foto, mapa, hq, cinematica,
gameplay, carta, texto, canal, fundo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import DADOS_ACERVO, RAIZ, abrir_acervo  # noqa: E402

PASTA = DADOS_ACERVO / "etiquetas"
CATEGORIAS = {"splash", "arte", "icone", "recorte", "meme", "foto", "mapa", "hq", "cinematica",
              "gameplay", "carta", "texto", "canal", "fundo"}


def main() -> None:
    con = abrir_acervo()
    total, problemas = 0, []
    for arq in sorted(PASTA.glob("*.json")):
        for mid, valor in json.loads(arq.read_text(encoding="utf-8")).items():
            cat, pers, desc, *resto = valor
            if cat not in CATEGORIAS:
                problemas.append(f"{arq.name} #{mid}: categoria desconhecida '{cat}'")
                continue
            n = con.execute(
                "UPDATE midias SET categoria=?, personagens=?, descricao=?, uso=? WHERE id=?",
                (cat, json.dumps(pers, ensure_ascii=False), desc, resto[0] if resto else None, int(mid)),
            ).rowcount
            if n == 0:
                problemas.append(f"{arq.name} #{mid}: id inexistente")
            total += n
    con.commit()
    print(f"{total} mídias etiquetadas")
    for p in problemas:
        print("  !", p)
    faltam = con.execute(
        "SELECT count(*) FROM midias WHERE categoria IS NULL AND tipo IN ('imagem','gif','video')").fetchone()[0]
    print(f"Sem etiqueta: {faltam}")


if __name__ == "__main__":
    main()
