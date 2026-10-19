"""Conferência do roteiro, antes de aprovar (o momento em que corrigir é de graça):

1. SEMELHANÇA (local, 0 cota): cada frase do roteiro × as frases do roteiro BASE (canal gringo), por embeddings
   multilíngues (paraphrase-multilingual-MiniLM, GPU) — pega tradução quase literal mesmo em outra língua.
   Princípio do canal: inspiração, não cópia.
2. FATOS (2 chamadas pequenas ao Sonnet): o Claude tira as afirmações checáveis de lore (nomes, datas, quem fez o
   quê); para cada uma, o sistema busca LOCALMENTE trechos na wiki do LoL (fandom, API MediaWiki) e na biografia
   oficial do Universe; o Claude compara afirmação × trechos → confere / diverge / sem fonte. Cache por parágrafo:
   ajustar 1 parágrafo só reconfere ele.

Resultado em direcao/conferencia.json (o painel mostra no Roteiro).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
from pathlib import Path

from .banco import RAIZ, agora

sys.path.insert(0, str(RAIZ / "tools" / "direcao"))

CACHE_WEB = RAIZ / "dados" / "pesquisa_cache"
WIKI = "https://leagueoflegends.fandom.com/api.php"
UNIVERSE = "https://universe-meeps.leagueoflegends.com/v1/en_us/champions/{slug}/index.json"
AGENTE = {"User-Agent": "GuiaRuneterraStudio/1.0 (uso pessoal; conferencia de roteiro)"}
QUASE_IGUAL, PARECIDA = 0.78, 0.70  # cosseno entre frases (medido: tradução literal PT×EN ≈ 0,75–0,9; assunto igual ≈ 0,5)

_modelo = None
# importar transformers/accelerate em duas threads ao mesmo tempo quebra ("partially initialized module"): o CLIP é
# pré-carregado numa thread ao ligar o servidor e a conferência roda na thread do motor → um import de cada vez
IMPORTS = threading.Lock()


def _embed(textos: list[str]):
    global _modelo
    with IMPORTS:
        if _modelo is None:
            import torch
            from sentence_transformers import SentenceTransformer

            _modelo = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                                          device="cuda" if torch.cuda.is_available() else "cpu")
    return _modelo.encode(textos, normalize_embeddings=True, batch_size=64, show_progress_bar=False)


def frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?…])\s+|\n+", texto)
    return [p.strip() for p in partes if len(p.strip().split()) >= 4]


# ------------------------------------------------------------------------------------------------ semelhança
def semelhanca(roteiro: str, base: str) -> dict:
    fr, fb = frases(roteiro), frases(base)
    if not fr or not fb:
        return {"geral": 0, "frases": []}
    er, eb = _embed(fr), _embed(fb)
    sim = er @ eb.T
    marcadas = []
    for i, linha in enumerate(sim):
        j = int(linha.argmax())
        nota = float(linha[j])
        if nota >= PARECIDA:
            marcadas.append({"frase": fr[i], "base": fb[j], "nota": round(nota, 2),
                             "nivel": "quase igual" if nota >= QUASE_IGUAL else "parecida"})
    return {"geral": round(100 * len(marcadas) / len(fr)), "total": len(fr), "frases": marcadas}


# ------------------------------------------------------------------------------------------------ fontes (web)
def _baixar(url: str, params: dict | None = None) -> dict | None:
    import requests

    chave = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    arq = CACHE_WEB / f"{chave}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    try:
        r = requests.get(url, params=params, headers=AGENTE, timeout=25)
        if not r.ok:
            return None
        dados = r.json()
    except Exception:
        return None
    CACHE_WEB.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def _limpar_wikitexto(t: str) -> str:
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)  # predefinições
    t = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)  # [[alvo|texto]] → texto
    t = re.sub(r"<[^>]+>|'''?|\[https?://\S+ ([^\]]*)\]", lambda m: m.group(1) or "", t)
    return t


def _wiki(busca: str) -> list[tuple[str, str]]:
    """(fonte, texto) das 2 páginas da wiki mais relevantes para a busca."""
    r = _baixar(WIKI, {"action": "query", "list": "search", "srsearch": busca, "format": "json", "srlimit": 2})
    saida = []
    for item in ((r or {}).get("query") or {}).get("search", []):
        titulo = item["title"]
        p = _baixar(WIKI, {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                           "titles": titulo, "format": "json", "formatversion": 2})
        try:
            texto = p["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        except (KeyError, IndexError, TypeError):
            continue
        saida.append((f"wiki: {titulo}", _limpar_wikitexto(texto)))
    return saida


def _universe(nome: str) -> list[tuple[str, str]]:
    slug = re.sub(r"[^a-z]", "", nome.lower())
    r = _baixar(UNIVERSE.format(slug=slug))
    if not r:
        return []
    bio = ((r.get("champion") or {}).get("biography") or {}).get("full") or ""
    bio = re.sub(r"<[^>]+>", " ", bio)
    return [(f"Universe: {r.get('name', nome)}", bio)] if bio.strip() else []


def _trechos(fontes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    saida = []
    for fonte, texto in fontes:
        for par in re.split(r"\n\s*\n|\n(?==)", texto):
            par = re.sub(r"\s+", " ", par).strip()
            while len(par) > 40:
                saida.append((fonte, par[:700]))
                par = par[600:]
    return saida


# ------------------------------------------------------------------------------------------------ fatos
SISTEMA = ("Você confere roteiros do canal \"Guia de Runeterra\" (lore de League of Legends). Responda SOMENTE JSON.")


def fatos(roteiro: str, cache: dict, aviso=lambda m: None) -> list[dict]:
    from claude_cli import chamar_json

    pars = [p.strip() for p in re.split(r"\n\s*\n", roteiro) if p.strip()]
    chaves = [hashlib.sha1(p.encode()).hexdigest()[:16] for p in pars]
    novos = [(i, p) for i, (p, k) in enumerate(zip(pars, chaves)) if k not in cache]
    if novos:
        aviso(f"lendo {len(novos)} parágrafo(s) novo(s)")
        r = chamar_json(
            "Liste as afirmações de LORE checáveis destes parágrafos (nomes, datas, eras, quem fez o quê, parentesco, "
            "lugares). Ignore piadas, opiniões, ganchos e comentários do narrador. No máximo 4 por parágrafo, só as "
            "que importam. Para cada uma, dê termos de busca em INGLÊS para a wiki do LoL e os campeões envolvidos.\n\n"
            + "\n\n".join(f"[{i}] {p}" for i, p in novos)
            + '\n\nJSON: {"afirmacoes": [{"p": 0, "trecho": "palavras do roteiro", "afirmacao": "o fato, curto", '
              '"busca": "english search terms", "campeoes": ["Mordekaiser"]}]}',
            SISTEMA, modelo="sonnet", etiqueta="conferencia-afirmacoes")
        afirm = [a for a in r.get("afirmacoes", []) if isinstance(a.get("p"), int) and 0 <= a["p"] < len(pars)]
        aviso(f"buscando {len(afirm)} afirmação(ões) na wiki e no Universe")
        blocos = []
        for k, a in enumerate(afirm):
            fontes = _wiki(a.get("busca") or a["afirmacao"])
            for c in (a.get("campeoes") or [])[:2]:
                fontes += _universe(c)
            tr = _trechos(fontes)
            escolhidos = []
            if tr:
                e = _embed([a["afirmacao"]] + [t for _, t in tr])
                notas = e[1:] @ e[0]
                escolhidos = [tr[i] for i in notas.argsort()[::-1][:3]]
            a["trechos"] = [{"fonte": f, "texto": t} for f, t in escolhidos]
            blocos.append(f"### Afirmação {k}: {a['afirmacao']}\n" + "\n".join(
                f"[{j}] ({x['fonte']}) {x['texto']}" for j, x in enumerate(a["trechos"])) if a["trechos"] else
                f"### Afirmação {k}: {a['afirmacao']}\n(nenhum trecho encontrado)")
        vered = {}
        if afirm:
            aviso("comparando com as fontes")
            v = chamar_json(
                "Para cada afirmação do roteiro, compare com os trechos das fontes (wiki do LoL / biografia oficial):\n"
                "- confere: os trechos sustentam o essencial da afirmação (detalhe a mais sem fonte não impede);\n"
                "- diverge: os trechos CONTRADIZEM a afirmação (outra data, outro autor, outro lugar) — explique;\n"
                "- sem_fonte: os trechos não falam disso, ou só de parte (não julgue pelo seu conhecimento).\n"
                "Ausência de um detalhe NÃO é divergência.\n\n" + "\n\n".join(blocos)
                + '\n\nJSON: {"vereditos": [{"i": 0, "veredito": "confere|diverge|sem_fonte", '
                  '"explicacao": "1 frase em português", "trecho": 0}]}',
                SISTEMA, modelo="sonnet", etiqueta="conferencia-fatos")
            vered = {x["i"]: x for x in v.get("vereditos", []) if isinstance(x.get("i"), int)}
        por_par: dict[int, list] = {i: [] for i, _ in novos}
        for k, a in enumerate(afirm):
            x = vered.get(k, {})
            t = a["trechos"][x["trecho"]] if isinstance(x.get("trecho"), int) and x["trecho"] < len(a["trechos"]) else None
            por_par[a["p"]].append({"trecho": a.get("trecho"), "afirmacao": a["afirmacao"],
                                    "veredito": x.get("veredito", "sem_fonte"), "explicacao": x.get("explicacao", ""),
                                    "fonte": t})
        for i, lista in por_par.items():
            cache[chaves[i]] = lista
    saida = []
    for i, k in enumerate(chaves):
        saida += [{**a, "paragrafo": i} for a in cache.get(k, [])]
    return saida


def conferir(pasta: Path, aviso=lambda m: None) -> dict:
    dirc = pasta / "direcao"
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    arq, arq_cache = dirc / "conferencia.json", dirc / "conferencia_cache.json"
    cache = json.loads(arq_cache.read_text(encoding="utf-8")) if arq_cache.exists() else {}
    res: dict = {"quando": agora(), "roteiro": hashlib.sha1(roteiro.encode()).hexdigest()[:16]}
    base = dirc / "roteiro_base.txt"
    if base.exists() and base.read_text(encoding="utf-8").strip():
        aviso("comparando com o roteiro base")
        res["semelhanca"] = semelhanca(roteiro, base.read_text(encoding="utf-8"))
    try:
        res["fatos"] = fatos(roteiro, cache, aviso)
    except Exception as e:  # sem rede/cota: a semelhança continua valendo
        res["erro_fatos"] = str(e)[:300]
    arq_cache.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    arq.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
