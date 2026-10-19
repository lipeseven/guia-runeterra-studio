"""Importa as splash arts oficiais de TODOS os campeões e skins (CommunityDragon, espelho dos arquivos do cliente do
LoL; grátis, sem chave) para o acervo — sem tocar na pasta do Felipe:

    <catálogo sequencial LOL>/_oficial_riot/splash/<campeao>_<n>.jpg   (n = skin; 0 = base) e .../universo/

Cada imagem entra no acervo.db já etiquetada: personagem, categoria ("splash" para a base, "skin" para as outras —
skins são universos alternativos, não lore, e por isso ficam atrás na busca do diretor), nome da skin em PT-BR,
origem "riot" e a URL. Imagem quase idêntica a uma que o Felipe já tem é descartada.

Uso:  .venv\\Scripts\\python.exe tools\\acervo\\importar_riot.py [--so-base] [--simular]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import PASTA_ACERVO, RAIZ, abrir_acervo  # noqa: E402

CDRAGON = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/"
UNIVERSE = "https://universe-meeps.leagueoflegends.com/v1/pt_br/champions/{slug}/index.json"
# subpasta própria DENTRO do catálogo do Felipe (pedido dele, 2026-10-19): ele vê, organiza e apaga como as dele;
# nada do que já existe na pasta é tocado
DESTINO = PASTA_ACERVO / "_oficial_riot" / "splash"
LICENCA = "Riot Games — Legal Jibber Jabber (uso de fã)"


def _url(caminho: str) -> str:
    return CDRAGON + "default/" + caminho.lower().replace("/lol-game-data/assets/", "")


def _slug(t: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", t)


def listar(so_base: bool = False) -> list[dict]:
    resumo = requests.get(CDRAGON + "pt_br/v1/champion-summary.json", timeout=30).json()
    campeoes = [c for c in resumo if c["id"] > 0]

    def skins(c: dict) -> list[dict]:
        d = requests.get(CDRAGON + f"pt_br/v1/champions/{c['id']}.json", timeout=30).json()
        saida = []
        # Universe (site oficial de lore): splash base em 1920×1080 (o cliente só tem 1215×717) + artes dos contos/HQs
        u = None
        try:
            r = requests.get(UNIVERSE.format(slug=_slug(d["alias"])), timeout=30)
            u = r.json() if r.ok else None
        except (requests.RequestException, ValueError):
            pass
        base_hd = ((u or {}).get("champion") or {}).get("image", {}).get("uri")
        vistos = set()
        for k, m in enumerate((u or {}).get("modules") or []):
            img = (m.get("featured-image") or {})
            if not img.get("uri") or img["uri"] in vistos or so_base:
                continue
            vistos.add(img["uri"])
            outros = [c.get("name") for c in m.get("featured-champions") or [] if c.get("name")]
            saida.append({"campeao": d["name"], "outros": outros, "skin": m.get("title") or img.get("title") or "arte",
                          "base": False, "categoria": "arte", "url": img["uri"],
                          "arquivo": DESTINO.parent / "universo" / f"{_slug(d['alias'])}_{k}.jpg"})
        for s in d.get("skins", []):
            if so_base and not s.get("isBase"):
                continue
            caminho = s.get("uncenteredSplashPath") or s.get("splashPath")
            if not caminho:
                continue
            num = s["id"] % 1000
            base = bool(s.get("isBase"))
            saida.append({"campeao": d["name"], "skin": s["name"], "base": base, "categoria": "splash" if base else "skin",
                          "url": base_hd if base and base_hd else _url(caminho),
                          "arquivo": DESTINO / f"{_slug(d['alias'])}_{num}.jpg"})
        return saida

    with ThreadPoolExecutor(max_workers=8) as pool:
        return [s for lista in pool.map(skins, campeoes) for s in lista]


def baixar(itens: list[dict], aviso=print) -> list[dict]:
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO.parent / "universo").mkdir(parents=True, exist_ok=True)
    faltam = [i for i in itens if not i["arquivo"].exists()]
    aviso(f"{len(itens)} splash arts ({len(itens) - len(faltam)} já baixadas); baixando {len(faltam)}")

    def um(i: dict) -> bool:
        r = requests.get(i["url"], timeout=60)
        if r.ok:
            i["arquivo"].write_bytes(r.content)
        return r.ok

    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, _ in enumerate(pool.map(um, faltam), 1):
            if n % 200 == 0:
                aviso(f"  {n}/{len(faltam)}")
    return [i for i in itens if i["arquivo"].exists()]


def catalogar(itens: list[dict], aviso=print) -> dict:
    """Inventário/CLIP/tomadas pelo atualizar do acervo; depois as etiquetas e o descarte de duplicatas."""
    import imagehash

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from atualizar import atualizar

    from inventariar import caminho_no_banco

    atualizar(aviso)
    con = abrir_acervo()
    baixados = {caminho_no_banco(i["arquivo"]) for i in itens}
    meus = [imagehash.hex_to_hash(r[1]) for r in con.execute(  # as imagens do Felipe (não as que acabaram de chegar)
        "SELECT caminho, phash FROM midias WHERE phash IS NOT NULL AND tipo='imagem' AND COALESCE(origem,'acervo')='acervo'")
        if r[0] not in baixados]
    novos, repetidos = 0, []
    for i in itens:
        r = con.execute("SELECT id, phash FROM midias WHERE caminho=?", (caminho_no_banco(i["arquivo"]),)).fetchone()
        if not r:
            continue
        if r["phash"] and any(imagehash.hex_to_hash(r["phash"]) - h <= 6 for h in meus):
            repetidos.append(r["id"])  # o Felipe já tem esta arte (talvez recortada/tratada): fica a dele
            continue
        con.execute("UPDATE midias SET origem='riot', url=?, licenca=?, categoria=?, personagens=?, descricao=?, revisado=1 "
                    "WHERE id=?", (i["url"], LICENCA, i["categoria"],
                                   json.dumps([i["campeao"], *[o for o in i.get("outros", []) if o != i["campeao"]]],
                                              ensure_ascii=False),
                                   f"arte oficial do Universe: {i['skin']}" if i["categoria"] == "arte"
                                   else f"splash art oficial: {i['skin']}", r["id"]))
        novos += 1
    for mid in repetidos:  # arquivo baixado sai do disco e do catálogo
        cam = con.execute("SELECT caminho FROM midias WHERE id=?", (mid,)).fetchone()[0]
        (PASTA_ACERVO / cam).unlink(missing_ok=True)  # só arquivos que ESTE importador baixou (subpasta _oficial_riot)
        con.execute("DELETE FROM midias WHERE id=?", (mid,))
    con.commit()
    return {"catalogadas": novos, "repetidas_descartadas": len(repetidos)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-base", action="store_true", help="só a splash base de cada campeão")
    ap.add_argument("--simular", action="store_true", help="só conta e estima o tamanho")
    a = ap.parse_args()
    lista = listar(a.so_base)
    if a.simular:
        amostra = lista[:: max(1, len(lista) // 20)]
        media = sum(int(requests.head(i["url"], timeout=30).headers.get("content-length", 0)) for i in amostra) / len(amostra)
        print(f"{len(lista)} imagens, ~{media * len(lista) / 1e6:.0f} MB")
    else:
        print(json.dumps(catalogar(baixar(lista)), ensure_ascii=False))
