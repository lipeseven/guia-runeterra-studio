"""Fotos de pessoas reais para o cartão de pessoa do horizontal (F1).

Só fotos com licença livre para uso comercial (Wikimedia Commons: CC0, domínio público, CC BY, CC BY-SA); nunca
NC/ND nem foto de agência. O diretor só pede o nome; aqui:
  1. `preparar(projeto, nomes, contexto)` busca as candidatas de cada pessoa (miniaturas remotas, nada baixado) e
     guarda em direcao/fotos_pessoas.json, com a melhor já indicada mas NÃO aprovada;
  2. o Felipe aprova (ou troca, ou deixa sem foto) no painel — só foto aprovada entra no vídeo;
  3. `na_pasta(projeto, trabalho)` baixa as aprovadas (uma vez, para <dados do canal>/acervo_internet/pessoas/) e põe
     um link na pasta pública do render; `foto_de(nome)` diz o arquivo para o cartão;
  4. `creditos(projeto)` dá as linhas de crédito para a descrição do vídeo (autor, página, licença).
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
LIVRE = re.compile(r"^(cc0|public domain|pd\b|cc by(-sa)?( \d\.\d)?( [a-z]{2,})?$|cc-by(-sa)?-\d\.\d)", re.I)
ARQ = "fotos_pessoas.json"


def _limpa(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def livre(licenca: str) -> bool:
    l = (licenca or "").strip().lower()
    return bool(l) and "nc" not in re.split(r"[\s-]", l) and "nd" not in re.split(r"[\s-]", l) and bool(LIVRE.match(l))


def candidatas(nome: str, contexto: str = "", n: int = 6) -> list[dict]:
    """Fotos do Commons com licença livre, as mais prováveis primeiro: retrato, recente, com o contexto no título."""
    import requests

    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=AGENTE, timeout=25, params={
        "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": f'"{nome}" filetype:bitmap',
        "gsrlimit": 40, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 360, "format": "json"}).json()
    ano_atual = datetime.now().year
    saida = []
    for p in ((r.get("query") or {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        licenca = _limpa((meta.get("LicenseShortName") or {}).get("value", ""))
        larg, alt = ii.get("width", 0), ii.get("height", 0)
        if not ii.get("url") or not livre(licenca) or min(larg, alt) < 500:
            continue
        titulo = p.get("title", "")
        texto = f"{titulo} {_limpa((meta.get('ImageDescription') or {}).get('value', ''))}".lower()
        sobrenome = nome.split()[-1].lower()
        if sobrenome not in texto:
            continue
        data = _limpa((meta.get("DateTimeOriginal") or {}).get("value", ""))
        ano = int(m.group(0)) if (m := re.search(r"(19|20)\d\d", data or titulo)) else 0
        pontos = 0.0
        pontos += 3 if alt >= larg * 0.9 else 0  # retrato cabe no cartão
        pontos += max(0, 5 - (ano_atual - ano)) if ano else 0  # recente pesa mais
        pontos += sum(2 for w in re.findall(r"\w+", contexto.lower()) if len(w) > 3 and w in texto)  # ex.: "ferrari"
        pontos -= 2 if re.search(r"\b(car|helmet|crowd|grid|podium)\b", texto) else 0  # carro/capacete: rosto pequeno
        saida.append({"titulo": titulo, "pagina": ii.get("descriptionurl", ""), "miniatura": ii.get("thumburl") or ii["url"],
                      "imagem": ii["url"], "largura": larg, "altura": alt, "ano": ano or None, "licenca": licenca,
                      "autor": _limpa((meta.get("Artist") or {}).get("value", ""))[:120], "pontos": round(pontos, 1)})
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
        dados[nome] = {"candidatas": cands, "escolhida": 0 if cands else None, "aprovada": False}
    gravar(projeto, dados)
    return [n for n, d in dados.items() if not d.get("aprovada") and d.get("candidatas")]


def _pasta_pessoas() -> Path:
    from comum import PASTA_INTERNET

    p = PASTA_INTERNET / "pessoas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def na_pasta(projeto: Path, trabalho: Path) -> dict[str, str]:
    """Baixa as aprovadas (uma vez) e põe na pasta pública do render. Devolve {nome: arquivo na pasta pública}."""
    import requests

    dados, saida = ler(projeto), {}
    for nome, d in dados.items():
        if not d.get("aprovada") or d.get("escolhida") is None:
            continue
        c = d["candidatas"][d["escolhida"]]
        # a versão de 1280 px (tamanho padrão do Commons) vem do servidor de miniaturas (a original é limitada e pesada demais para um cartão)
        url = re.sub(r"/\d+px-", "/1280px-", c["miniatura"].split("?")[0]) if "/thumb/" in c["miniatura"] else c["imagem"]
        ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
        base = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
        arq = _pasta_pessoas() / f"{base}-{hashlib.sha1(url.encode()).hexdigest()[:8]}{ext}"
        if not arq.exists():
            try:
                r = requests.get(url, headers=AGENTE, timeout=60)
                r.raise_for_status()
            except Exception as e:  # sem a foto, o cartão sai com a silhueta; o render não para
                print(f"[fotos] não baixei a foto de {nome}: {e}")
                continue
            arq.write_bytes(r.content)
        destino = trabalho / f"pessoa_{arq.name}"
        if not destino.exists():
            try:
                os.link(arq, destino)
            except OSError:
                shutil.copy2(arq, destino)
        saida[nome] = destino.name
    return saida


def creditos(projeto: Path) -> list[str]:
    """Linhas de crédito das fotos aprovadas (CC BY/BY-SA exigem autor, fonte e licença)."""
    linhas = []
    for nome, d in ler(projeto).items():
        if d.get("aprovada") and d.get("escolhida") is not None:
            c = d["candidatas"][d["escolhida"]]
            linhas.append(f"Foto de {nome}: {c['autor'] or 'autor desconhecido'} — {c['pagina']} ({c['licenca']})")
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
