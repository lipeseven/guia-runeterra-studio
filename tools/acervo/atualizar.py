"""Atualiza o catálogo do acervo com o que entrou na pasta (incremental, local, sem cota).

Uso:
    .venv\\Scripts\\python.exe tools\\acervo\\atualizar.py

Passos: inventário (dados + miniaturas) → busca por semelhança (CLIP) das imagens → tomadas dos vídeos novos →
etiquetas pelo NOME (arquivo novo herda as etiquetas dos irmãos de mesmo prefixo: "azir18.jpg" ← "azir…").
O que não dá para etiquetar pelo nome fica listado (etiquetar com o Claude gasta cota: decisão do Felipe).
Nunca altera nem move nada na pasta do acervo.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import RAIZ, abrir_acervo  # noqa: E402

PY = sys.executable
AQUI = Path(__file__).resolve().parent


def _rodar(script: str, *args: str) -> None:
    subprocess.run([PY, str(AQUI / script), *args], cwd=str(RAIZ), check=True)


def etiquetar_pelo_nome(con) -> tuple[int, list[str]]:
    """Mídias sem etiqueta herdam categoria e personagens dos irmãos de mesmo prefixo já etiquetados."""
    sem = con.execute("SELECT id, nome, prefixo FROM midias WHERE categoria IS NULL "
                      "AND tipo IN ('imagem','gif','video')").fetchall()
    feitas, faltam = 0, []
    for r in sem:
        irmaos = con.execute("SELECT categoria, personagens FROM midias WHERE prefixo=? AND categoria IS NOT NULL",
                             (r["prefixo"],)).fetchall()
        if not r["prefixo"] or not irmaos:
            faltam.append(r["nome"])
            continue
        categoria = Counter(i["categoria"] for i in irmaos).most_common(1)[0][0]
        personagens = Counter(i["personagens"] or "[]" for i in irmaos).most_common(1)[0][0]
        con.execute("UPDATE midias SET categoria=?, personagens=?, descricao=?, uso=NULL WHERE id=?",
                    (categoria, personagens, f"(pelo nome do arquivo, como os outros '{r['prefixo']}')", r["id"]))
        feitas += 1
    con.commit()
    return feitas, faltam


def atualizar(aviso=print) -> dict:
    con = abrir_acervo()
    antes = {r[0] for r in con.execute("SELECT caminho FROM midias")}
    aviso("procurando arquivos novos")
    _rodar("inventariar.py")
    novos = [r["nome"] for r in con.execute("SELECT caminho, nome FROM midias") if r["caminho"] not in antes]
    if novos:
        aviso(f"{len(novos)} arquivo(s) novo(s): busca por semelhança")
        _rodar("busca_semantica.py", "indexar")
        aviso("tomadas dos vídeos novos")
        _rodar("indexar_clipes.py", "indexar")
    feitas, faltam = etiquetar_pelo_nome(con)
    return {"novos": novos, "etiquetadas_pelo_nome": feitas, "sem_etiqueta": faltam}


if __name__ == "__main__":
    print(json.dumps(atualizar(), ensure_ascii=False, indent=1))
