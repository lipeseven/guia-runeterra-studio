"""Mídias da internet (sem chave, sem cota): busca de imagens no DuckDuckGo + Wikimedia Commons para o storyboard.

A imagem escolhida é baixada para dados/acervo_internet/busca/ (fora da pasta do Felipe) e entra no acervo.db na
hora — com origem, página e título guardados para os créditos. Daí em diante é uma mídia como outra qualquer.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from .banco import RAIZ

AGENTE = {"User-Agent": "Mozilla/5.0 (GuiaRuneterraStudio; uso pessoal)"}
EXTS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def buscar(consulta: str, n: int = 24) -> list[dict]:
    """[{imagem, miniatura, titulo, pagina, fonte, largura, altura}] — DuckDuckGo primeiro, Commons para completar."""
    saida: list[dict] = []
    from ddgs import DDGS

    for tentativa in range(3):  # o ddgs sorteia um "navegador" por sessão e às vezes sai um que falha: tenta de novo
        try:
            for r in DDGS().images(consulta, max_results=n):
                saida.append({"imagem": r["image"], "miniatura": r.get("thumbnail") or r["image"], "titulo": r.get("title") or "",
                              "pagina": r.get("url") or "", "fonte": r.get("source") or "",
                              "largura": int(r.get("width") or 0), "altura": int(r.get("height") or 0)})
            break
        except Exception as e:  # DuckDuckGo limita rajadas: o Commons segura a busca
            print(f"[internet] DuckDuckGo falhou ({tentativa + 1}/3): {e}")
    if len(saida) < n:
        saida += _commons(consulta, n - len(saida))
    return saida[:n]


def _commons(consulta: str, n: int) -> list[dict]:
    import requests

    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=AGENTE, timeout=20, params={
            "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": consulta, "gsrlimit": n,
            "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 320, "format": "json"}).json()
    except Exception:
        return []
    saida = []
    for p in ((r.get("query") or {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("url"):
            continue
        meta = ii.get("extmetadata") or {}
        saida.append({"imagem": ii["url"], "miniatura": ii.get("thumburl") or ii["url"], "titulo": p.get("title", ""),
                      "pagina": ii.get("descriptionurl", ""), "fonte": "Wikimedia Commons",
                      "largura": ii.get("width", 0), "altura": ii.get("height", 0),
                      "licenca": re.sub(r"<[^>]+>", "", (meta.get("LicenseShortName") or {}).get("value", "")),
                      "autor": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:120]})
    return saida


def baixar(url: str, titulo: str = "", pagina: str = "", fonte: str = "", licenca: str = "", autor: str = "") -> dict:
    """Baixa a imagem e cataloga no acervo. Devolve {midia_id, nome, miniatura} (o mesmo formato da busca do acervo)."""
    import requests

    r = requests.get(url, headers={**AGENTE, "Referer": pagina or url}, timeout=60)
    r.raise_for_status()
    tipo = r.headers.get("content-type", "").split(";")[0].strip().lower()
    ext = EXTS.get(tipo) or Path(url.split("?")[0]).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise ValueError("o link não é uma imagem (jpg, png, webp ou gif)")
    base = re.sub(r"[^a-z0-9]+", "-", (titulo or Path(url).stem).lower())[:40].strip("-") or "imagem"
    sys.path.insert(0, str(RAIZ / "tools"))
    from comum import PASTA_INTERNET

    pasta = PASTA_INTERNET / "busca"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{base}-{hashlib.sha1(url.encode()).hexdigest()[:8]}{ext}"
    arq.write_bytes(r.content)

    sys.path.insert(0, str(RAIZ / "tools"))
    sys.path.insert(0, str(RAIZ / "tools" / "acervo"))
    from comum import PASTA_MINIATURAS, abrir_acervo
    from inventariar import processar

    info = processar(arq)
    if info.get("erro"):
        arq.unlink(missing_ok=True)
        raise ValueError(f"imagem inválida: {info['erro']}")
    mini = info.pop("miniatura")
    info.pop("erro")
    con = abrir_acervo()
    con.execute(
        """INSERT INTO midias (caminho, nome, ext, tipo, bytes, mtime, sha1, phash, largura, altura, duracao,
               transparente, prefixo, origem, url, descricao, licenca, autor, categoria, revisado)
           VALUES (:caminho, :nome, :ext, :tipo, :bytes, :mtime, :sha1, :phash, :largura, :altura, :duracao,
               :transparente, :prefixo, 'internet', :url, :descricao, :licenca, :autor, 'arte', 1)
           ON CONFLICT(caminho) DO UPDATE SET mtime=excluded.mtime""",
        {**info, "url": pagina or url, "descricao": f"{titulo} ({fonte})".strip(), "licenca": licenca or None,
         "autor": autor or None})
    mid = con.execute("SELECT id FROM midias WHERE caminho=?", (info["caminho"],)).fetchone()[0]
    con.commit()
    PASTA_MINIATURAS.mkdir(parents=True, exist_ok=True)
    if mini is not None:
        mini.save(PASTA_MINIATURAS / f"{mid}.jpg", quality=85)
    return {"midia_id": mid, "nome": arq.name,
            "miniatura": (PASTA_MINIATURAS / f"{mid}.jpg").relative_to(RAIZ).as_posix()}
