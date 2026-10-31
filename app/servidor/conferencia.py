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

CACHE_WEB = caminho("dados_acervo").parent / "pesquisa_cache"  # Runeterra: dados/runeterra/pesquisa_cache
# A wiki do LoL saiu do Fandom (o fandom.com ficou parado em 2023): wiki.leagueoflegends.com, namespace Universe
# (3006) = lore, com o resumo dos contos e HQs oficiais. ns_extra = eventos (0), Legends of Runeterra (3002) e Riftbound (3008).
WIKI = "https://wiki.leagueoflegends.com/en-us/api.php"
POKEWIKI = "https://pokemon.fandom.com/api.php"  # a Bulbapedia bloqueia acesso automático (Cloudflare)
# fontes por canal (canal.toml: fatos): o que buscar e como chamar quem aparece na afirmação
FONTES = {"lol": {"wiki": WIKI, "ns": "3006", "ns_extra": "0|3002|3008",
                  "nome": "wiki do LoL (lore, eventos, Legends of Runeterra, Riftbound) / biografia e contos oficiais da Riot",
                  "quem": "campeões envolvidos"},
          "pokemon": {"wiki": POKEWIKI, "ns": "0", "nome": "Pokémon Wiki / Pokédex oficial", "quem": "Pokémon e personagens envolvidos"}}
FONTE = FONTES[CANAL.get("fatos", "lol")]
UNIVERSE = "https://universe-meeps.leagueoflegends.com/v1/en_us/champions/{slug}/index.json"
CONTO = "https://universe-meeps.leagueoflegends.com/v1/en_us/story/{slug}/index.json"
ARQ_FATOS = caminho("dados_acervo").parent / "fatos_do_canal.txt"  # anotações do Felipe, uma por linha (# = comentário)
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
    """(fonte, texto) das 4 páginas da wiki do canal mais relevantes para a busca (LoL: só páginas de lore)."""
    r = _baixar(FONTE["wiki"], {"action": "query", "list": "search", "srsearch": busca, "format": "json", "srlimit": 4,
                                "srnamespace": FONTE["ns"]})
    titulos = [item["title"] for item in ((r or {}).get("query") or {}).get("search", [])]
    if FONTE.get("ns_extra"):
        r = _baixar(FONTE["wiki"], {"action": "query", "list": "search", "srsearch": busca, "format": "json", "srlimit": 6,
                                    "srnamespace": FONTE["ns_extra"]})
        extras = [item["title"] for item in ((r or {}).get("query") or {}).get("search", [])]
        titulos += [t for t in extras if "/" not in t and not re.match(r"V\d", t)][:2]  # sem skins/áudio/notas de versão
    return [x for t in titulos for x in _wiki_pagina(t)]


def _wiki_pagina(titulo: str) -> list[tuple[str, str]]:
    """Uma página da wiki pelo título (vazio se não existir)."""
    p = _baixar(FONTE["wiki"], {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                                "titles": titulo, "format": "json", "formatversion": 2, "redirects": 1})
    try:
        texto = p["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
    except (KeyError, IndexError, TypeError):
        return []
    return [(f"wiki: {p['query']['pages'][0].get('title', titulo)}", _limpar_wikitexto(texto))]


def _pagina_do_personagem(nome: str) -> list[tuple[str, str]]:
    """A página de lore do personagem citado (LoL: Universe:<nome>) — a busca por termos às vezes erra o alvo."""
    return _wiki_pagina(f"Universe:{nome}" if FONTE["ns"] == "3006" else nome)


def _universe(nome: str) -> list[tuple[str, str]]:
    slug = re.sub(r"[^a-z]", "", nome.lower())
    r = _baixar(UNIVERSE.format(slug=slug))
    if not r:
        return []
    bio = ((r.get("champion") or {}).get("biography") or {}).get("full") or ""
    bio = re.sub(r"<[^>]+>", " ", bio)
    saida = [(f"Riot (biografia): {r.get('name', nome)}", bio)] if bio.strip() else []
    for m in r.get("modules") or []:  # conto oficial do campeão (texto completo)
        if m.get("type") == "story-preview" and m.get("story-slug"):
            c = _baixar(CONTO.format(slug=m["story-slug"])) or {}
            secoes = ((c.get("story") or {}).get("story-sections") or [])
            texto = " ".join(sub.get("content") or "" for sec in secoes for sub in sec.get("story-subsections") or [])
            texto = re.sub(r"<[^>]+>", " ", texto)
            if texto.strip():
                saida.append((f"Riot (conto): {(c.get('story') or {}).get('title') or m.get('title')}", texto))
    return saida


def _trechos(fontes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    saida = []
    for fonte, texto in fontes:
        for par in re.split(r"\n\s*\n|\n(?==)", texto):
            par = re.sub(r"\s+", " ", par).strip()
            while len(par) > 40:
                saida.append((fonte, par[:700]))
                par = par[600:]
    return saida


def fatos_relevantes(consulta: str, n: int = 3) -> list[tuple[str, str]]:
    """Anotações do Felipe ligadas a esta consulta (o que não está escrito em lugar nenhum, ex.: cinemática)."""
    if not ARQ_FATOS.exists():
        return []
    linhas = [x.strip() for x in ARQ_FATOS.read_text(encoding="utf-8-sig").splitlines() if x.strip() and not x.strip().startswith("#")]
    if not linhas:
        return []
    e = _embed([consulta] + linhas)
    notas = e[1:] @ e[0]
    return [("fato do canal", linhas[i]) for i in notas.argsort()[::-1][:n] if notas[i] >= 0.4]


# ------------------------------------------------------------------------------------------------ fatos
# Como pesar as fontes (conferência, dossiê e crivo). O que vale é o ponto mais recente da história, não quem publicou.
REGRA_DAS_FONTES = ("Trecho marcado \"fato do canal\" é anotação verificada pelo dono do canal e vale acima de todas as fontes."
                    + (" A biografia da Riot é um retrato antigo e costuma parar no tempo; eventos, cinemáticas, contos e "
                       "linha do tempo trazem o que aconteceu depois. Biografia que não cita um fato NÃO contradiz esse "
                       "fato. Se duas fontes se contradizem, vale a mais recente na história, mesmo que seja a wiki (ex.: a "
                       "biografia o mostra servindo o rei e a linha do tempo conta que ele morreu depois: vale a morte). Se "
                       "não der para saber qual é a mais recente, não decida: diga isso."
                       if CANAL.get("fatos", "lol") == "lol" else ""))
SISTEMA = f"Você confere roteiros do canal \"{CANAL['nome']}\" ({CANAL['assunto']}). Responda SOMENTE JSON."


def _pokedex(nome: str) -> list[tuple[str, str]]:
    """Ficha da Pokédex local (PokeAPI) do Pokémon citado — dados oficiais de tipo, geração, evolução."""
    arq = RAIZ / "dados" / "pokemon" / "pokedex.json"
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


# Versão das regras da checagem: mudou a regra (fontes, prompt) → todo parágrafo é conferido de novo uma vez.
REGRAS = "4"  # 4 = obra mais recente vale mais, eventos/LoR/Riftbound na busca, fatos do canal (2026-10-31)


LOTE = 8  # trechos por chamada ao Claude: o progresso fica guardado a cada lote


def _cortar(paragrafo: str) -> list[str]:
    """Trechos de ~60-90 palavras. O corte depende só da própria frase: editar uma frase não desloca os trechos
    seguintes, então só o trecho dela volta a ser conferido."""
    saida, atual, n = [], [], 0
    for frase in re.split(r"(?<=[.!?…])\s+", paragrafo):
        ws = frase.split()
        partes = [" ".join(ws[k:k + 60]) for k in range(0, len(ws), 60)] if len(ws) > 90 else [frase]  # sem pontuação
        for parte in partes:
            atual.append(parte)
            n += len(parte.split())
            if n >= 90 or (n >= 40 and int(hashlib.sha1(parte.encode()).hexdigest(), 16) % 3 == 0):
                saida.append(" ".join(atual))
                atual, n = [], 0
    if atual:
        if saida and n < 15:  # sobra curta no fim do parágrafo
            saida[-1] += " " + " ".join(atual)
        else:
            saida.append(" ".join(atual))
    return saida


def _chave(texto: str) -> str:
    return f"{REGRAS}:{hashlib.sha1(texto.encode()).hexdigest()[:16]}"


def _migrar(pars: list[str], cache: dict) -> None:
    """Conferência antiga era por parágrafo: reparte o resultado pelos trechos em vez de gastar cota de novo."""
    def normal(t: str) -> set[str]:
        return set(re.findall(r"\w+", t.lower()))

    for p in pars:
        velho = hashlib.sha1((REGRAS + p).encode()).hexdigest()[:16]
        if velho not in cache:
            continue
        trechos = _cortar(p)
        lista: dict[str, list] = {_chave(t): [] for t in trechos}
        for a in cache[velho]:
            palavras = normal(a.get("trecho") or a.get("afirmacao") or "")
            melhor = max(trechos, key=lambda t: len(palavras & normal(t)))
            lista[_chave(melhor)].append(a)
        for k, v in lista.items():
            cache.setdefault(k, v)


def _checar(pars: list[str], chaves: list[str], novos: list[tuple[int, str]], cache: dict, aviso) -> None:
    from claude_cli import chamar_json

    if novos:
        r = chamar_json(
            "Liste as afirmações de LORE checáveis destes trechos (nomes, datas, eras, quem fez o quê, parentesco, "
            "lugares). Ignore piadas, opiniões, ganchos, comentários do narrador e o que o próprio roteiro já chama de "
            "teoria/especulação. Cada afirmação = UM fato só: frase com vários fatos vira várias afirmações curtas. "
            "Liste todas, no máximo 6 por trecho. Para cada uma, dê termos de busca em INGLÊS para a wiki "
            f"({FONTE['nome']}), começando pelo nome de quem aparece, e os {FONTE['quem']}.\n\n"
            + "\n\n".join(f"[{i}] {p}" for i, p in novos)
            + '\n\nJSON: {"afirmacoes": [{"p": 0, "trecho": "palavras do roteiro", "afirmacao": "o fato, curto", '
              '"busca": "english search terms", "campeoes": ["Mordekaiser"]}]}',
            SISTEMA, modelo="sonnet", etiqueta="conferencia-afirmacoes")
        pedidos = {i for i, _ in novos}
        afirm = [a for a in r.get("afirmacoes", []) if a.get("p") in pedidos]
        aviso(f"buscando {len(afirm)} afirmação(ões) na wiki e no Universe")
        blocos = []
        for k, a in enumerate(afirm):
            fontes = _wiki(a.get("busca") or a["afirmacao"])
            vistas = {f for f, _ in fontes}
            for c in (a.get("campeoes") or [])[:2]:
                fontes += [x for x in _pagina_do_personagem(c) if x[0] not in vistas]  # sempre a página de quem aparece
                fontes += _universe(c) if CANAL.get("fatos", "lol") == "lol" else _pokedex(c)
            tr = _trechos(fontes)
            escolhidos = []
            if tr:
                e = _embed([a["afirmacao"]] + [t for _, t in tr])
                notas = e[1:] @ e[0]
                ordem = [tr[i] for i in notas.argsort()[::-1]]
                # 3 melhores da wiki + 2 melhores da Riot (biografia/conto): dá para cruzar as fontes
                escolhidos = ([x for x in ordem if x[0].startswith("wiki")][:3]
                              + [x for x in ordem if not x[0].startswith("wiki")][:2]) or ordem[:3]
            escolhidos += fatos_relevantes(a["afirmacao"])
            a["trechos"] = [{"fonte": f, "texto": t} for f, t in escolhidos]
            blocos.append(f"### Afirmação {k}: {a['afirmacao']}\n" + "\n".join(
                f"[{j}] ({x['fonte']}) {x['texto']}" for j, x in enumerate(a["trechos"])) if a["trechos"] else
                f"### Afirmação {k}: {a['afirmacao']}\n(nenhum trecho encontrado)")
        vered = {}
        if afirm:
            aviso("comparando com as fontes")
            v = chamar_json(
                f"Para cada afirmação do roteiro, compare com os trechos das fontes ({FONTE['nome']}):\n"
                "- confere: os trechos sustentam a afirmação;\n"
                "- parcial: os trechos sustentam o principal, mas um pedaço não aparece neles — diga QUAL pedaço;\n"
                "- diverge: os trechos CONTRADIZEM a afirmação (outra data, outro autor, outro lugar) — explique;\n"
                "- sem_fonte: os trechos não falam disso (não julgue pelo seu conhecimento).\n"
                "Ausência de um detalhe NÃO é divergência.\n"
                "Cruze as fontes: `fontes` = quantas fontes DIFERENTES (wiki, biografia Riot, conto Riot) sustentam a "
                "afirmação; `fontes_divergem` = true se as próprias fontes se contradizem entre si (diga na explicação "
                "qual valeu e por quê).\n" + REGRA_DAS_FONTES + "\n\n" + "\n\n".join(blocos)
                + '\n\nJSON: {"vereditos": [{"i": 0, "veredito": "confere|parcial|diverge|sem_fonte", '
                  '"explicacao": "1 frase em português", "trecho": 0, "fontes": 1, "fontes_divergem": false}]}',
                SISTEMA, modelo="sonnet", etiqueta="conferencia-fatos")
            vered = {x["i"]: x for x in v.get("vereditos", []) if isinstance(x.get("i"), int)}
        por_par: dict[int, list] = {i: [] for i, _ in novos}
        for k, a in enumerate(afirm):
            x = vered.get(k, {})
            t = a["trechos"][x["trecho"]] if isinstance(x.get("trecho"), int) and x["trecho"] < len(a["trechos"]) else None
            por_par[a["p"]].append({"trecho": a.get("trecho"), "afirmacao": a["afirmacao"],
                                    "veredito": x.get("veredito", "sem_fonte"), "explicacao": x.get("explicacao", ""),
                                    "fonte": t, "fontes": x.get("fontes") if isinstance(x.get("fontes"), int) else None,
                                    "fontes_divergem": bool(x.get("fontes_divergem"))})
        for i, lista in por_par.items():
            cache[chaves[i]] = lista


def fatos(roteiro: str, cache: dict, aviso=lambda m: None, info: dict | None = None) -> list[dict]:
    pars = [p.strip() for p in re.split(r"\n\s*\n", roteiro) if p.strip()]
    itens = [(i, t) for i, p in enumerate(pars) for t in _cortar(p)]
    textos, chaves = [t for _, t in itens], [_chave(t) for _, t in itens]
    _migrar(pars, cache)
    novos = [(k, t) for k, (t, c) in enumerate(zip(textos, chaves)) if c not in cache]
    if info is not None:
        info.update(refeitos=len(novos), total=len(chaves))
    for ini in range(0, len(novos), LOTE):
        aviso(f"conferindo trechos {ini + 1} a {min(ini + LOTE, len(novos))} de {len(novos)}")
        _checar(textos, chaves, novos[ini:ini + LOTE], cache, aviso)
    # trecho de outra versão fica guardado: voltar uma versão ou desfazer uma alteração não confere de novo
    for k in [k for k in cache if not k.startswith(f"{REGRAS}:")]:
        del cache[k]
    return [{**a, "paragrafo": i, "bloco": c} for (i, _), c in zip(itens, chaves) for a in cache.get(c, [])]


def _rodada(anteriores: list[dict], atuais: list[dict], info: dict) -> dict:
    """O que esta rodada mudou: só trechos alterados entram aqui; o resto da lista é o mesmo de antes."""
    if not all(a.get("bloco") for a in anteriores):  # conferência antiga, sem trechos
        return {**info, "novas": [], "resolvidas": []}
    blocos_antes, blocos_agora = {a["bloco"] for a in anteriores}, {a["bloco"] for a in atuais}
    pendente = lambda a: a.get("veredito") != "confere"  # noqa: E731
    return {**info,
            "novas": [a["afirmacao"] for a in atuais if pendente(a) and anteriores and a["bloco"] not in blocos_antes],
            "resolvidas": [a["afirmacao"] for a in anteriores if pendente(a) and a["bloco"] not in blocos_agora]}


def conferir(pasta: Path, aviso=lambda m: None) -> dict:
    dirc = pasta / "direcao"
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    arq, arq_cache = dirc / "conferencia.json", dirc / "conferencia_cache.json"
    cache = json.loads(arq_cache.read_text(encoding="utf-8")) if arq_cache.exists() else {}
    anteriores = (json.loads(arq.read_text(encoding="utf-8")).get("fatos") or []) if arq.exists() else []
    info: dict = {}
    res: dict = {"quando": agora(), "roteiro": hashlib.sha1(roteiro.encode()).hexdigest()[:16]}
    base = dirc / "roteiro_base.txt"
    if base.exists() and base.read_text(encoding="utf-8").strip():
        aviso("comparando com o roteiro base")
        res["semelhanca"] = semelhanca(roteiro, base.read_text(encoding="utf-8"))
    try:
        res["fatos"] = fatos(roteiro, cache, aviso, info)
        res["rodada"] = _rodada(anteriores, res["fatos"], info)
    except Exception as e:  # sem rede/cota: a semelhança continua valendo
        res["erro_fatos"] = str(e)[:300]
    arq_cache.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    arq.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
