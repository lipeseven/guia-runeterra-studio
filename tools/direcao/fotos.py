"""Fotos de pessoas reais para o cartão de pessoa do horizontal (F1).

O direito de imagem é decisão do Felipe (2026-11-07): a busca pega a MELHOR foto de qualquer fonte (DuckDuckGo
imagens + Wikimedia Commons), em alta resolução, recente, de preferência retrato, e ela já entra no vídeo. No painel
(bloco "Fotos das pessoas") dá para trocar por outra candidata ou deixar sem foto.
  1. `preparar(projeto, nomes, contexto)` busca as candidatas e escolhe a melhor (direcao/fotos_pessoas.json);
  2. `na_pasta(projeto, trabalho)` baixa a escolhida (se o download falhar, a próxima) para
     <dados do canal>/acervo_internet/pessoas/ e põe um link na pasta pública do render;
  3. `creditos(projeto)` dá as linhas de crédito conhecidas para a descrição.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

# a Wikimedia pede um agente identificado (sem ele, e com a imagem original, responde 429)
AGENTE = {"User-Agent": "GuiaRuneterraStudio/1.0 (uso pessoal; https://github.com/lipeseven) python-requests"}
ARQ = "fotos_pessoas.json"


def _limpa(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def _pontuar(c: dict, nome: str, contexto: str, ano_atual: int) -> float:
    texto = f"{c['titulo']} {c.get('descricao', '')}".lower()
    larg, alt = c["largura"], c["altura"]
    pontos = 3.0 if alt >= larg * 0.9 else 0.0  # retrato cabe no cartão
    pontos += min(3.0, min(larg, alt) / 600)  # resolução
    ano = c.get("ano") or 0
    pontos += max(0, 5 - (ano_atual - ano)) if ano else 0  # recente pesa mais
    pontos += sum(2 for w in re.findall(r"\w+", contexto.lower()) if len(w) > 3 and w in texto)  # ex.: "ferrari"
    pontos -= 3 if re.search(r"\b(car|carro|helmet|capacete|crowd|grid|podium|onboard|livery|wallpaper)\b", texto) else 0
    pontos += 2 if re.search(r"\b(portrait|retrato|headshot|press conference|media day|interview)\b", texto) else 0
    return round(pontos, 1)


# bancos de imagem que entregam a foto com marca d'água
MARCA_DAGUA = re.compile(r"alamy|gettyimages|shutterstock|dreamstime|istockphoto|depositphotos|123rf|agefotostock|"
                         r"imago-images|sportsphoto|motorsportimages|lat\.?images|zimbio|pixelz", re.I)


def _ddg(nome: str, ano: int, n: int = 30) -> list[dict]:
    from ddgs import DDGS

    for _ in range(3):  # o ddgs às vezes sorteia um "navegador" que falha
        try:
            saida = []
            for r in DDGS().images(f"{nome} F1 {ano} portrait", max_results=n, size="Large"):
                if MARCA_DAGUA.search(f"{r.get('image', '')} {r.get('url', '')} {r.get('source', '')}"):
                    continue
                titulo = r.get("title") or ""
                m = re.search(r"(20\d\d)", f"{titulo} {r.get('url', '')}")
                saida.append({"titulo": titulo, "pagina": r.get("url") or "", "miniatura": r.get("thumbnail") or r["image"],
                              "imagem": r["image"], "largura": int(r.get("width") or 0), "altura": int(r.get("height") or 0),
                              "ano": int(m.group(1)) if m else None, "licenca": "", "autor": r.get("source") or "",
                              "fonte": "web"})
            return saida
        except Exception as e:
            print(f"[fotos] DuckDuckGo falhou: {e}")
    return []


def _commons(nome: str) -> list[dict]:
    import requests

    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=AGENTE, timeout=25, params={
            "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": f'"{nome}" filetype:bitmap',
            "gsrlimit": 40, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 360, "format": "json"}).json()
    except Exception as e:
        print(f"[fotos] Commons falhou: {e}")
        return []
    saida = []
    for p in ((r.get("query") or {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("url"):
            continue
        meta = ii.get("extmetadata") or {}
        data = _limpa((meta.get("DateTimeOriginal") or {}).get("value", ""))
        m = re.search(r"(19|20)\d\d", data or p.get("title", ""))
        saida.append({"titulo": p.get("title", ""), "pagina": ii.get("descriptionurl", ""), "miniatura": ii.get("thumburl") or ii["url"],
                      "imagem": ii["url"], "largura": ii.get("width", 0), "altura": ii.get("height", 0),
                      "ano": int(m.group(0)) if m else None, "descricao": _limpa((meta.get("ImageDescription") or {}).get("value", "")),
                      "licenca": _limpa((meta.get("LicenseShortName") or {}).get("value", "")),
                      "autor": _limpa((meta.get("Artist") or {}).get("value", ""))[:120], "fonte": "commons"})
    return saida


def candidatas(nome: str, contexto: str = "", n: int = 8) -> list[dict]:
    """As melhores fotos da pessoa (web + Commons): retrato, grande, recente, com o contexto no título."""
    ano_atual = datetime.now().year
    sobrenome = nome.split()[-1].lower()
    vistas, saida = set(), []
    for c in _ddg(nome, ano_atual) + _commons(nome):
        texto = f"{c['titulo']} {c.get('descricao', '')} {c['pagina']}".lower()
        if sobrenome not in texto or min(c["largura"], c["altura"]) < 700 or c["imagem"] in vistas:
            continue
        vistas.add(c["imagem"])
        c["pontos"] = _pontuar(c, nome, contexto, ano_atual)
        saida.append(c)
    saida.sort(key=lambda c: -c["pontos"])
    return saida[:n]


def ler(projeto: Path) -> dict:
    arq = projeto / "direcao" / ARQ
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


def gravar(projeto: Path, dados: dict) -> None:
    (projeto / "direcao" / ARQ).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def preparar(projeto: Path, nomes: list[str], contexto: str = "") -> list[str]:
    """Busca as candidatas das pessoas novas (quem já está no arquivo fica como está). Devolve quem falta aprovar."""
    dados = ler(projeto)
    for nome in dict.fromkeys(n.strip() for n in nomes if n and n.strip()):
        if nome in dados:
            continue
        try:
            cands = candidatas(nome, contexto)
        except Exception as e:  # sem internet: o cartão sai com a silhueta
            print(f"[fotos] busca de {nome} falhou: {e}")
            cands = []
        # a melhor já entra (o Felipe troca no painel se quiser)
        dados[nome] = {"candidatas": cands, "escolhida": 0 if cands else None, "aprovada": True}
    gravar(projeto, dados)
    return []


def _pasta_pessoas() -> Path:
    from comum import PASTA_INTERNET

    p = PASTA_INTERNET / "pessoas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _baixar(nome: str, c: dict) -> Path | None:
    import requests

    if c.get("fonte") == "commons" and "/thumb/" in c["miniatura"]:
        url = re.sub(r"/\d+px-", "/1280px-", c["miniatura"].split("?")[0])  # tamanho padrão do Commons (a original é limitada)
    else:
        url = c["imagem"]
    ext = Path(url.split("?")[0]).suffix.lower()
    ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"
    base = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    arq = _pasta_pessoas() / f"{base}-{hashlib.sha1(url.encode()).hexdigest()[:8]}{ext}"
    if arq.exists():
        return arq
    try:
        r = requests.get(url, headers={**AGENTE, "User-Agent": "Mozilla/5.0", "Referer": c.get("pagina") or url}, timeout=40)
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image/") or len(r.content) < 20000:
            raise ValueError("não é uma imagem (ou é pequena demais)")
    except Exception as e:
        print(f"[fotos] não baixei {url[:80]}: {e}")
        return None
    arq.write_bytes(r.content)
    return arq


def rosto(arq: Path) -> tuple[float, float] | None:
    """Centro do maior rosto de frente (fração da largura e da altura), se ele ocupar pelo menos 7% da largura.
    Foto sem rosto (carro, pôster, capacete) não serve para o cartão de pessoa."""
    import cv2
    import numpy as np
    from canal import DADOS_COMUM

    img = cv2.imdecode(np.fromfile(str(arq), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    esc = 900 / max(img.shape[:2])
    if esc < 1:
        img = cv2.resize(img, None, fx=esc, fy=esc)
    # YuNet (opencv_zoo): o OpenCV 5 não traz mais os detectores Haar
    det = cv2.FaceDetectorYN.create(str(DADOS_COMUM / "modelos" / "face_detection_yunet_2023mar.onnx"), "",
                                    (img.shape[1], img.shape[0]), 0.8)
    _, caras = det.detect(img)
    if caras is None or not len(caras):
        return None
    x, y, w, h = max(caras, key=lambda r: r[2] * r[3])[:4]
    if w < img.shape[1] * 0.07:
        return None
    return round(float((x + w / 2) / img.shape[1]), 3), round(float((y + h / 2) / img.shape[0]), 3)


def na_pasta(projeto: Path, trabalho: Path) -> dict[str, str]:
    """Baixa a escolhida de cada pessoa (se falhar ou não tiver rosto, a próxima da lista) e põe na pasta pública do
    render. Devolve {nome: {foto, foco}} (foco = centro do rosto, para enquadrar o cartão)."""
    dados, saida = ler(projeto), {}
    for nome, d in dados.items():
        if d.get("escolhida") is None:
            continue
        ordem = list(range(d["escolhida"], len(d["candidatas"])))
        arq = None
        for i in ordem:
            arq = _baixar(nome, d["candidatas"][i])
            foco = rosto(arq) if arq else None
            if arq and (foco or d.get("manual")):  # escolha manual do Felipe vale mesmo sem rosto detectado
                if i != d["escolhida"] or d.get("foco") != foco:
                    d["escolhida"], d["foco"] = i, foco
                    gravar(projeto, dados)
                break
            arq = None
        if not arq:
            continue
        destino = trabalho / f"pessoa_{arq.name}"
        if not destino.exists():
            try:
                os.link(arq, destino)
            except OSError:
                shutil.copy2(arq, destino)
        saida[nome] = {"foto": destino.name, "foco": d.get("foco")}
    return saida


def creditos(projeto: Path) -> list[str]:
    """Linhas de crédito das fotos aprovadas (CC BY/BY-SA exigem autor, fonte e licença)."""
    linhas = []
    for nome, d in ler(projeto).items():
        if d.get("escolhida") is not None:
            c = d["candidatas"][d["escolhida"]]
            licenca = f" ({c['licenca']})" if c.get("licenca") else ""
            linhas.append(f"Foto de {nome}: {c['autor'] or 'autor desconhecido'} — {c['pagina']}{licenca}")
    return linhas


def credito_modelo(glb: Path) -> str | None:
    """Crédito do modelo 3D (Sketchfab grava autor, licença e fonte dentro do .glb)."""
    import struct

    try:
        with open(glb, "rb") as f:
            f.read(12)
            n, _ = struct.unpack("<II", f.read(8))
            ex = (json.loads(f.read(n)).get("asset") or {}).get("extras") or {}
    except (OSError, ValueError):
        return None
    if not ex.get("author"):
        return None
    return f"Modelo 3D \"{ex.get('title', glb.stem)}\": {ex['author']} — {ex.get('source', '')} ({ex.get('license', '').split(' (')[0]})"
