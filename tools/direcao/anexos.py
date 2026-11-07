"""Ponte entre os pedidos do Felipe e a internet, antes do diretor (que roda sem ferramentas).

- Link de imagem no pedido: baixada aqui (sem cota), reduzida e mandada ao diretor como imagem anexa.
  SVG da Wikimedia vira PNG pela miniatura da própria Wikimedia; outro SVG não é lido (aviso).
- "pesquise" no pedido (ou link de página): uma chamada curta ao Sonnet com busca na web; os fatos achados, com a
  fonte, entram no pedido como confirmados. Cache por pedido em direcao/pesquisas_pedidos.json.
Tudo que não deu certo vira nota, que o motor mostra como aviso no painel.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from claude_cli import chamar_json

LINK = re.compile(r"https?://[^\s<>\"']+")
EXT_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
MAX_IMAGENS = 4
LADO_MAX = 1568  # acima disso o Claude reduz a imagem de qualquer jeito


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GuiaRuneterraStudio/1.0 (uso pessoal)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = r.read(15_000_000 + 1)
    if len(dados) > 15_000_000:
        raise ValueError("arquivo maior que 15 MB")
    return dados


def _miniatura_wikimedia(url: str) -> str | None:
    """upload.wikimedia.org/wikipedia/commons/a/ab/X.svg → .../commons/thumb/a/ab/X.svg/1280px-X.svg.png (tamanho padrão da Wikimedia)"""
    m = re.match(r"(https://upload\.wikimedia\.org/wikipedia/[^/]+)/([0-9a-f])/([0-9a-f]{2})/([^/?#]+\.svg)$", url, re.I)
    return f"{m[1]}/thumb/{m[2]}/{m[3]}/{m[4]}/1280px-{m[4]}.png" if m else None


def _imagem(url: str, pasta: Path) -> Path:
    from PIL import Image

    limpo = url.split("?")[0].split("#")[0]
    destino = pasta / f"{hashlib.sha1(limpo.encode()).hexdigest()[:10]}.png"
    if destino.exists():
        return destino
    if limpo.lower().endswith(".svg"):
        mini = _miniatura_wikimedia(limpo)
        if not mini:
            raise ValueError("SVG fora da Wikimedia não dá para ler: mande em PNG ou JPG")
        limpo = mini
    img = Image.open(io.BytesIO(_baixar(limpo)))
    img.seek(0)
    img = img.convert("RGBA")
    fundo = Image.new("RGB", img.size, "white")  # transparência vira branco (traçados da Wikimedia vêm sem fundo)
    fundo.paste(img, mask=img.split()[3])
    fundo.thumbnail((LADO_MAX, LADO_MAX))
    pasta.mkdir(parents=True, exist_ok=True)
    fundo.save(destino)
    return destino


def _pesquisar(texto: str, fala: str, paginas: list[str], briefing: str) -> dict:
    prompt = (f"Vídeo curto de F1 (contexto do briefing, resumido):\n{briefing[:1500]}\n\n"
              f"Cena da fala: \"{fala}\"\nPedido de quem edita: \"{texto}\"\n"
              + (f"Páginas indicadas: {' '.join(paginas)}\n" if paginas else "")
              + "\nPesquise na web o que o pedido precisa saber (ex.: cores da pintura ou do macacão da época, formato de "
              "algo, ano, lugar). Use fontes confiáveis. Responda SOMENTE JSON {\"fatos\": [{\"fato\": \"curto e "
              "concreto; cores em hex quando for cor\", \"fonte\": \"url\"}], \"nao_achei\": \"o que faltou, se faltou\"}. "
              "No máximo 6 fatos.")
    r = chamar_json(prompt, "Você pesquisa fatos para um diretor de animação. Seja breve e cite a fonte de cada fato.",
                    modelo="sonnet", etiqueta="pedido-pesquisa", ferramentas="WebSearch,WebFetch", timeout=420)
    return r if isinstance(r, dict) else {"fatos": [], "nao_achei": "resposta sem formato"}


def preparar(pedidos: list[dict], falas: dict[str, str], pasta_direcao: Path, briefing: str = "",
             aviso=lambda m: None) -> tuple[list[dict], list[Path], list[str]]:
    """Devolve (pedidos com links trocados por [imagem anexa N] e fatos pesquisados, imagens, notas para o painel)."""
    imagens: list[Path] = []
    notas: list[str] = []
    cache_arq = pasta_direcao / "pesquisas_pedidos.json"
    cache = json.loads(cache_arq.read_text(encoding="utf-8")) if cache_arq.exists() else {}
    saida = []
    for p in pedidos:
        texto = p.get("texto", "")
        paginas: list[str] = []
        for url in LINK.findall(texto):
            curto = urllib.parse.unquote(url.split("?")[0].rsplit("/", 1)[-1])[:60]
            if url.split("?")[0].lower().endswith(EXT_IMAGEM):
                if len(imagens) >= MAX_IMAGENS:
                    notas.append(f"imagem não enviada (limite de {MAX_IMAGENS} por rodada): {curto}")
                    texto = texto.replace(url, f"[imagem {curto}: não enviada]")
                    continue
                try:
                    aviso(f"baixando a imagem do pedido: {curto}")
                    arq = _imagem(url, pasta_direcao / "anexos")
                    if arq not in imagens:  # mesmo link em dois pedidos = uma imagem só
                        imagens.append(arq)
                    texto = texto.replace(url, f"[imagem anexa {imagens.index(arq) + 1}: {curto}]")
                except Exception as e:  # noqa: BLE001 - qualquer falha vira aviso, o pedido segue sem a imagem
                    notas.append(f"não consegui baixar {curto}: {e}")
                    texto = texto.replace(url, f"[imagem {curto}: não baixou]")
            else:
                paginas.append(url)
        if paginas or re.search(r"pesquis", texto, re.I):
            chave = hashlib.sha1(f"{texto}|{falas.get(p.get('plano'), '')}".encode()).hexdigest()[:16]
            if cache.get(chave) is None:  # sem pesquisa ainda (ou a anterior falhou)
                aviso("pesquisando na internet o que o pedido precisa")
                try:
                    cache[chave] = _pesquisar(texto, falas.get(p.get("plano"), ""), paginas, briefing)
                except Exception as e:  # noqa: BLE001
                    notas.append(f"a pesquisa do pedido \"{texto[:50]}\" falhou: {e}")
                    cache[chave] = None
                cache_arq.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            achado = cache.get(chave) or {}
            fatos = [f"{f.get('fato')} ({f.get('fonte')})" for f in achado.get("fatos") or [] if f.get("fato")]
            if fatos:
                texto += "\n  PESQUISADO NA INTERNET (vale como fato confirmado, inclusive cores): " + "; ".join(fatos)
            elif cache.get(chave) is not None:
                notas.append(f"a pesquisa não achou o que o pedido \"{texto[:50]}\" precisa: {achado.get('nao_achei') or '?'}")
        saida.append({**p, "texto": texto})
    return saida, imagens, notas
