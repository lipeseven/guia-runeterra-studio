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

from .banco import CANAL, RAIZ, agora, caminho

sys.path.insert(0, str(RAIZ / "tools" / "direcao"))

CACHE_WEB = caminho("dados_acervo").parent / "pesquisa_cache"  # Runeterra: dados/pesquisa_cache
WIKI = "https://leagueoflegends.fandom.com/api.php"
POKEWIKI = "https://pokemon.fandom.com/api.php"  # a Bulbapedia bloqueia acesso automático (Cloudflare)
# fontes por canal (canal.toml: fatos): o que buscar e como chamar quem aparece na afirmação
FONTES = {"lol": {"wiki": WIKI, "nome": "wiki do LoL / biografia oficial", "quem": "campeões envolvidos"},
          "pokemon": {"wiki": POKEWIKI, "nome": "Pokémon Wiki / Pokédex oficial", "quem": "Pokémon e personagens envolvidos"}}
FONTE = FONTES[CANAL.get("fatos", "lol")]
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


def limpar_base(texto: str) -> str:
    """Transcrição do YouTube colada como roteiro base: tira marcações de tempo ("0:12", "1:02:33") e de som
    ("[Música]", "(aplausos)") e junta as linhas quebradas pela legenda."""
    t = texto.replace("\r\n", "\n")
    t = re.sub(r"\[[^\]\n]{1,30}\]|\((?:m[uú]sica|music|aplausos|applause|risos|laughter)\)", " ", t, flags=re.I)
    t = re.sub(r"(?<![\w:])\d{1,2}(?::\d{2}){1,2}(?![\w:])", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    if len(re.findall(r"[.!?…]", t)) < len(t.split()) / 60:  # quase sem pontuação = legenda: linhas são pedaços
        t = re.sub(r"\s*\n\s*", " ", t)
    return re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", t).strip()


def frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?…])\s+|\n+", texto)
    saida = []
    for p in partes:  # sem pontuação (transcrição automática): "frase" enorme vira trechos de ~20 palavras
        ws = p.split()
        n = max(1, round(len(ws) / 20)) if len(ws) > 35 else 1
        saida += [" ".join(ws[len(ws) * k // n:len(ws) * (k + 1) // n]) for k in range(n)]
    return [p.strip() for p in saida if len(p.strip().split()) >= 4]


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


def _predefinicao(m: re.Match) -> str:
    """Predefinição em linha que mostra um nome ({{cbi|Kayn}}, {{ci|Jun|image=…}}) vira o nome; o resto some."""
    corpo = m.group(0)[2:-2]
    if "\n" in corpo:
        return ""
    nome, *args = corpo.split("|")
    if nome.strip().lower().startswith("sm"):  # falas/áudio
        return ""
    pos = [a for a in args if "=" not in a]
    return pos[0].strip() if pos else ""


def _limpar_wikitexto(t: str) -> str:
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", _predefinicao, t)
    t = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)  # [[alvo|texto]] → texto
    t = re.sub(r"<[^>]+>|'''?|\[https?://\S+ ([^\]]*)\]", lambda m: m.group(1) or "", t)
    return t


def _wiki(busca: str) -> list[tuple[str, str]]:
    """(fonte, texto) das 2 páginas da wiki do canal mais relevantes para a busca."""
    r = _baixar(FONTE["wiki"], {"action": "query", "list": "search", "srsearch": busca, "format": "json", "srlimit": 2})
    saida = []
    for item in ((r or {}).get("query") or {}).get("search", []):
        titulo = item["title"]
        p = _baixar(FONTE["wiki"], {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
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
SISTEMA = f"Você confere roteiros do canal \"{CANAL['nome']}\" ({CANAL['assunto']}). Responda SOMENTE JSON."


def _pokedex(nome: str) -> list[tuple[str, str]]:
    """Ficha da Pokédex local (PokeAPI) do Pokémon citado — dados oficiais de tipo, geração, evolução."""
    arq = RAIZ / "dados" / "canais" / "pokemon" / "pokedex.json"
    if not arq.exists():
        return []
    alvo = re.sub(r"[^a-z0-9]", "", nome.lower())
    for e in json.loads(arq.read_text(encoding="utf-8")):
        if re.sub(r"[^a-z0-9]", "", e["nome"].lower()) == alvo:
            texto = (f"{e['nome']} (#{e['numero']}), {e['categoria_en']}, tipos {'/'.join(e['tipos'])}, "
                     f"geração {e['geracao']} ({e['regiao']}), "
                     f"{'lendário' if e['lendario'] else 'mítico' if e['mitico'] else 'comum'}"
                     + (f", evolui de {e['evolui_de']}" if e['evolui_de'] else "") + f". Pokédex: {e['pokedex_en']}")
            return [(f"Pokédex: {e['nome']}", texto)]
    return []


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
            f"que importam. Para cada uma, dê termos de busca em INGLÊS para a wiki ({FONTE['nome']}) e os {FONTE['quem']}.\n\n"
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
                fontes += _universe(c) if CANAL.get("fatos", "lol") == "lol" else _pokedex(c)
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
                f"Para cada afirmação do roteiro, compare com os trechos das fontes ({FONTE['nome']}):\n"
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
