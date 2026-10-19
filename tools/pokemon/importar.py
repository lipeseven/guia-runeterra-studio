r"""Primeiro material do canal Pokémon: arte oficial (Sugimori/Ken Sugimori & cia., PokeAPI/sprites) e render 3D do
Pokémon HOME de TODAS as espécies e formas (megas, regionais, Gigantamax…), PNG com fundo transparente.

    <catálogo sequencial POKEMON>/_oficial/arte/<forma>.png    (ex.: charizard-mega-x.png)
    <catálogo sequencial POKEMON>/_oficial/home/<forma>.png

Cada imagem entra no acervo DO CANAL já etiquetada pela Pokédex local (pokedex.json): espécie, tipos, geração,
região, lendário/mítico. Roda no servidor do canal Pokémon (GRS_CANAL=pokemon).

Uso:  set GRS_CANAL=pokemon && .venv\Scripts\python.exe tools\pokemon\importar.py [--simular]
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

os.environ.setdefault("GRS_CANAL", "pokemon")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acervo"))
from canal import CHAVE  # noqa: E402
from comum import PASTA_ACERVO, RAIZ, abrir_acervo  # noqa: E402

SPRITES = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/"
DESTINO = PASTA_ACERVO / "_oficial"
LICENCA = "© Nintendo / Creatures / GAME FREAK — uso de fã"
FONTES = {"arte": ("official-artwork", "arte oficial"), "home": ("home", "render 3D do Pokémon HOME")}


def listar() -> list[dict]:
    dex = json.loads((RAIZ / "dados" / "canais" / "pokemon" / "pokedex.json").read_text(encoding="utf-8"))
    itens = []
    for e in dex:
        for f in e["formas"]:
            forma = f["nome"].replace(e["slug"], "").strip("-")  # "mega-x", "alola", "" (padrão)
            for pasta, (remoto, rotulo) in FONTES.items():
                itens.append({
                    "url": f"{SPRITES}{remoto}/{f['id']}.png", "arquivo": DESTINO / pasta / f"{f['nome']}.png",
                    "especie": e["nome"], "categoria": "recorte",
                    "descricao": f"{rotulo}: {e['nome']}{f' ({forma})' if forma else ''} — {'/'.join(f['tipos'])}, "
                                 f"geração {e['geracao']} ({e['regiao']})"
                                 + (", lendário" if e["lendario"] else ", mítico" if e["mitico"] else ""),
                    "tags": [*f["tipos"], e["regiao"] or "", f"geração {e['geracao']}",
                             *(["lendário"] if e["lendario"] else []), *(["mítico"] if e["mitico"] else []),
                             *([forma] if forma else [])]})
    return itens


def baixar(itens: list[dict], aviso=print) -> list[dict]:
    for pasta in FONTES:
        (DESTINO / pasta).mkdir(parents=True, exist_ok=True)
    faltam = [i for i in itens if not i["arquivo"].exists()]
    aviso(f"{len(itens)} imagens ({len(itens) - len(faltam)} já baixadas); baixando {len(faltam)}")

    def um(i: dict) -> bool:
        r = requests.get(i["url"], timeout=60)
        if r.ok and r.content[:4] == b"\x89PNG":
            i["arquivo"].write_bytes(r.content)
        return r.ok

    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, _ in enumerate(pool.map(um, faltam), 1):
            if n % 200 == 0:
                aviso(f"{n}/{len(faltam)}")
    return [i for i in itens if i["arquivo"].exists()]


def catalogar(itens: list[dict], aviso=print) -> dict:
    from atualizar import atualizar
    from inventariar import caminho_no_banco

    atualizar(aviso)
    con = abrir_acervo()
    n = 0
    for i in itens:
        cur = con.execute("UPDATE midias SET origem='pokeapi', url=?, licenca=?, categoria=?, personagens=?, descricao=?, "
                          "tags=?, revisado=1 WHERE caminho=?",
                          (i["url"], LICENCA, i["categoria"], json.dumps([i["especie"]], ensure_ascii=False),
                           i["descricao"], json.dumps([t for t in i["tags"] if t], ensure_ascii=False),
                           caminho_no_banco(i["arquivo"])))
        n += cur.rowcount
    con.commit()
    return {"catalogadas": n}


if __name__ == "__main__":
    assert CHAVE == "pokemon", "rode com GRS_CANAL=pokemon"
    lista = listar()
    if "--simular" in sys.argv:
        print(len(lista), "imagens")
    else:
        print(json.dumps(catalogar(baixar(lista)), ensure_ascii=False))
