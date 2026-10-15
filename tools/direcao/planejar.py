"""Diretor — 1ª passada (só texto): roteiro + tempos -> plano de cenas.

O Claude decide, frase a frase: tipo de cena, legenda, destaques e O QUE PROCURAR (pelo sentido,
não pela palavra). Nenhuma imagem é escolhida aqui — isso é a 2ª passada, com os candidatos à vista.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from claude_cli import chamar_json

RAIZ = Path(__file__).resolve().parents[2]
TIPOS = ("capa", "hub", "cartao", "telacheia", "recorte", "mosaico", "clipe", "dialogo",
         "dividida", "lista", "meio", "texto", "citacao")
COM_PECAS = ("mosaico", "dividida", "lista")  # tipos que usam "pecas" (uma imagem por item falado)


def frases_do_roteiro(texto: str, palavras: list[dict]) -> list[dict]:
    """Frases com o índice da 1ª/última palavra (mesmos índices de alinhar.palavras_do_roteiro)
    e a duração na narração (voz guia ou gravação)."""
    toks = texto.split()
    # fim de parágrafo: o último token antes de uma linha em branco
    fins_par, k = set(), -1
    for par in re.split(r"\n\s*\n", texto):
        k += len(par.split())
        fins_par.add(k)
    frases, ini = [], 0
    for i, t in enumerate(toks):
        if t.endswith((".", "!", "?", ":", "…")) or i in fins_par or i == len(toks) - 1:
            frases.append({"n": len(frases), "de": ini, "ate": i, "texto": " ".join(toks[ini:i + 1]),
                           "segundos": round(palavras[i]["f"] - palavras[ini]["i"], 1),
                           "fim_de_paragrafo": i in fins_par})
            ini = i + 1
    return frases


SISTEMA = """Você é o diretor visual do canal brasileiro "Guia de Runeterra" (lore de League of Legends).
Transforma o roteiro narrado em uma lista de cenas para um editor automático. Responda SOMENTE com JSON.

{regras}

=== ESTILO DO CANAL (resumo) ===
- Ritmo rápido: uma cena nova a cada ~3–5 s em média. Frases longas (> ~6 s) podem ser divididas
  numa palavra de ênfase (campo "comeca_na_palavra"). Cortes caem no início de frases ou em palavras de ênfase.
- Tipos de cena disponíveis:
  capa      — abertura: a capa do vídeo com zoom no personagem da 1ª seção. SÓ a primeira cena.
  hub       — transição de seção: os ícones da capa voltam e a câmera fecha no personagem da seção que COMEÇA.
              Use na frase inicial de cada seção a partir da 2ª (é onde o roteiro fala só o nome: "Nocturne."),
              quando o personagem da seção está na capa. Sem busca.
  cartao    — fundo branco, imagem emoldurada no centro e LEGENDA curta embaixo (o "feijão com arroz").
  telacheia — arte ocupando a tela toda (impacto, atmosfera). Pode ter "rotulo" (nome grande) e "subrotulo"
              (descrição curta) sobre a arte, para APRESENTAR um personagem/lugar ("Raum" / "o demônio dos segredos").
  recorte   — personagem recortado sobre fundo branco + legenda (apresentar/descrever um personagem).
  meio      — meio a meio: arte numa metade da tela e uma FRASE curta (campo "legenda", até ~6 palavras) na outra.
              Para ideias/conceitos fortes ("o poder de criar", "amaldiçoou a família real").
  texto     — só texto, sem imagem (campo "legenda" + "fundo": "claro" — padrão — ou "escuro" só em ocasião especial).
              Para conceitos abstratos, viradas e pausas dramáticas ("A Clareza", "Outra história"). Curto e raro.
  dividida  — tela dividida: 2 ou 3 imagens em altura total lado a lado, com nome embaixo de cada ("pecas").
              Para comparar/confrontar ou apresentar um par/trio ("Tryndamere e Ashe", "Darkin contra Ascendidos").
  lista     — lista acumulada: 2 a 5 painéis com rótulo entrando um ao lado do outro conforme a frase enumera
              ("pecas", cada uma com "rotulo"). Para enumerações de CONCEITOS (torturas, poderes, motivos).
  mosaico   — fundo em tela cheia + 2 a 4 imagens que entram quando cada item é falado ("pecas"). Enumeração
              rápida de itens do mesmo assunto, mais visual que a lista. Nunca dois mosaicos seguidos.
  clipe     — trecho de animação/cinemática (ação, revelação, emoção) quando faz sentido existir tomada disso.
  dialogo   — dois ícones e a fala entre aspas: fala atribuída a um personagem dirigida a outro.
  citacao   — fala/trecho CITADO de um personagem ou conto, sobre uma arte, com "autor" e "destaques"
              (palavras que acendem em vermelho). A cena deve cobrir exatamente a frase citada.
- Legendas/rótulos: curtos (1 a 5 palavras), em português. Podem ser descritivos ("Noxus invadiu Ionia"),
  frases narrativas ("e aí deu ruim") ou, com moderação, ter humor/gíria brasileira no tom do canal
  ("Swain é zika", "gg") — o Felipe revisa.
- Seções: cada personagem/tema principal é uma seção (o nome dele fica no topo dos cartões, com o ícone da capa).
- O FUNDO BRANCO é a assinatura do canal: cartões, recortes, listas, meio a meio e diálogos são sempre no branco.
  O escuro só aparece nas cenas de tela cheia (arte, clipe, citação, tela dividida) e, em ocasiões especiais,
  num "texto" com "fundo": "escuro" (virada dramática, pausa pesada). O padrão do "texto" é "claro".
- Variedade é obrigatória: um vídeo com só cartão parece automático. Misture os tipos com sentido; nenhum tipo
  "especial" (hub não conta) mais de 2 vezes seguidas ou dominando o vídeo.

=== NOTAS DO FELIPE ===
- Linhas "↳ NOTA DO FELIPE: ..." são ordens de direção que ele escreveu no roteiro para aquela frase (não são
  narradas). Têm prioridade sobre o seu gosto: siga-as. Ex.: "Texto na tela: X" → cena "texto" (ou a legenda da
  cena) com exatamente X; "mostrar o mapa de Ionia" → a busca é o mapa; "meme do gato aqui" → meme de gato.

=== EFEITOS SONOROS (campo opcional "som") ===
- O padrão do canal é VOZ PURA (medido nos vídeos de referência). Efeito sonoro é tempero raro e com sentido:
  em média no máximo 1 a cada ~40 s, só em momentos marcantes — revelação, golpe/batalha, magia, criatura,
  morte, explosão, sino/presságio. Na grande maioria das cenas: "som": null.
- "som": {{"o_que": "descrição do som em inglês (ex.: 'deep cinematic boom', 'crows cawing', 'sword clash')",
  "palavra": "palavra da frase em que o som bate"}}.
- Nunca em cenas seguidas, nunca o mesmo tipo de som duas vezes seguidas, nada de whoosh em corte. Metáforas
  não viram som literal ("devorar nações" não leva som de mastigar).

=== COMO DESCREVER A BUSCA ===
"busca.o_que" é a descrição VISUAL, em inglês, do que a imagem deve mostrar segundo o SENTIDO da frase
(metáforas não são literais). "busca.personagens" são nomes de LoL que devem aparecer (pode ser vazio).
"busca.categorias" prefere entre: splash, arte, recorte, icone, meme, foto, mapa, hq, cinematica, carta.
Para "clipe", a busca descreve a ação da tomada.
"""

FORMATO = """Responda com este JSON. OMITA os campos que não se aplicam (nada de null, [] ou "" à toa: JSON enxuto).
{
 "cenas": [
  {"frase": 0, "tipo": "capa"},
  {"frase": 1, "tipo": "cartao", "legenda": "um conto infantil", "legenda_na_palavra": "conto",
   "busca": {"o_que": "...", "personagens": ["..."], "categorias": ["arte"]}},
  {"frase": 3, "comeca_na_palavra": "Raum", "tipo": "telacheia", "rotulo": "Raum", "subrotulo": "o demônio dos segredos",
   "legenda_na_palavra": "Raum", "busca": {"o_que": "...", "personagens": ["Raum"], "categorias": ["splash"]}},
  {"frase": 5, "tipo": "meio", "legenda": "o poder de criar", "legenda_na_palavra": "criar", "busca": {...}},
  {"frase": 6, "tipo": "texto", "legenda": "Outra história", "fundo": "claro"},
  {"frase": 7, "comeca_na_palavra": "Volibear", "tipo": "mosaico", "busca": {"o_que": "fundo...", "personagens": [], "categorias": ["arte"]},
   "pecas": [{"palavra": "Volibear", "busca": {"o_que": "...", "personagens": ["Volibear"], "categorias": ["splash"]}}]},
  {"frase": 9, "tipo": "dividida", "pecas": [{"palavra": "Ashe", "rotulo": "Ashe", "busca": {...}},
                                            {"palavra": "Tryndamere", "rotulo": "Tryndamere", "busca": {...}}]},
  {"frase": 11, "tipo": "lista", "pecas": [{"palavra": "nervos", "rotulo": "nervos cutucados", "busca": {...}}, ...]},
  {"frase": 12, "tipo": "hub"},
  {"frase": 13, "tipo": "telacheia", "busca": {...}, "som": {"o_que": "deep cinematic boom", "palavra": "explodiu"}},
  {"frase": 14, "tipo": "citacao", "autor": "Sion, na Mente da Loucura", "destaques": ["sangue"], "busca": {...}},
  {"frase": 15, "tipo": "dialogo", "dialogo": {"esquerda": "Quem fala", "direita": "Quem ouve", "destaques": ["palavra"]}}
 ],
 "observacoes": "1 a 3 frases sobre escolhas que o Felipe deve conferir"
}
Regras do JSON: "frase" é o número [n] da frase; "comeca_na_palavra", "legenda_na_palavra", "destaques" e
"pecas[].palavra" e "som.palavra" são palavras que EXISTEM naquela frase (copie exatamente); as cenas estão em ordem e cobrem o
trecho inteiro; "pecas" (mosaico/dividida/lista) entram na ordem em que as palavras são faladas — a 1ª peça
entra junto com a cena; dividida = 2 ou 3 peças, lista = 2 a 5, mosaico = 2 a 4."""


def montar_prompt(frases: list[dict], nomes_capa: list[str], contexto: str = "") -> str:
    """`frases` numeradas a partir de 0 (o trecho que está sendo planejado)."""
    linhas = []
    for i, f in enumerate(frases):
        linhas.append(f"[{i}] ({f['segundos']}s){' ¶' if f['fim_de_paragrafo'] else ''} {f['texto']}")
        linhas += [f"     ↳ NOTA DO FELIPE: {nota}" for nota in f.get("notas", [])]
    total = sum(f["segundos"] for f in frases)
    return (f"Personagens na capa (ícones disponíveis): {', '.join(nomes_capa) or 'nenhum'}.\n" + contexto +
            f"Narração deste trecho: {total:.0f}s em {len(frases)} frases (¶ = fim de parágrafo). "
            f"Alvo: ~{max(1, round(total / 4))} cenas.\n\nTRECHO DO ROTEIRO:\n" + "\n".join(linhas) + "\n\n" + FORMATO)


def validar(plano: dict, frases: list[dict]) -> list[str]:
    """Confere o que o Claude devolveu; devolve a lista de problemas (vazia = ok)."""
    problemas = []
    ultima = -1
    for k, c in enumerate(plano.get("cenas", [])):
        if c.get("tipo") not in TIPOS:
            problemas.append(f"cena {k}: tipo inválido {c.get('tipo')!r}")
        n = c.get("frase")
        if not isinstance(n, int) or not 0 <= n < len(frases):
            problemas.append(f"cena {k}: frase inválida {n!r}")
            continue
        if n < ultima:
            problemas.append(f"cena {k}: fora de ordem")
        ultima = n
        palavras = [re.sub(r"[^\wÀ-ú-]", "", w).lower() for w in frases[n]["texto"].split()]
        existe = lambda w: re.sub(r"[^\wÀ-ú-]", "", w).lower() in palavras  # noqa: E731
        for campo in ("comeca_na_palavra", "legenda_na_palavra"):
            w = c.get(campo)
            if w and not existe(w):
                problemas.append(f"cena {k}: {campo} {w!r} não está na frase {n}")
        tipo = c.get("tipo")
        if tipo in COM_PECAS:
            pecas = pecas_da_cena(c)
            minimo, maximo = {"dividida": (2, 3), "lista": (2, 5), "mosaico": (2, 4)}[tipo]
            if not minimo <= len(pecas) <= maximo:
                problemas.append(f"cena {k}: {tipo} precisa de {minimo} a {maximo} peças (tem {len(pecas)})")
            for p in pecas:
                if p.get("palavra") and not existe(p["palavra"]):
                    problemas.append(f"cena {k}: peça com palavra {p['palavra']!r} que não está na frase {n}")
                if not p.get("busca"):
                    problemas.append(f"cena {k}: peça sem busca")
        som = c.get("som")
        if som and som.get("palavra") and not existe(som["palavra"]):
            problemas.append(f"cena {k}: som com palavra {som['palavra']!r} que não está na frase {n}")
        if tipo in ("meio", "texto") and not c.get("legenda"):
            problemas.append(f"cena {k}: {tipo} precisa de \"legenda\" (o texto da cena)")
        if tipo in ("cartao", "telacheia", "recorte", "meio", "citacao", "clipe", "mosaico") and not c.get("busca"):
            problemas.append(f"cena {k}: {tipo} precisa de \"busca\"")
    return problemas


def pecas_da_cena(c: dict) -> list[dict]:
    """Peças de mosaico/dividida/lista. Planos antigos usavam o campo "mosaico"."""
    return c.get("pecas") or c.get("mosaico") or []


# ===================================================================== direção por blocos (com reaproveitamento)
# O roteiro é dividido em BLOCOS (introdução + uma seção por personagem/tema). Cada bloco é planejado à parte e
# guardado em direcao/plano_secoes/<hash do texto>.json. Quando o roteiro muda:
#   bloco igual             → reaproveita (0 cota)
#   mudança pequena         → reaproveita as cenas e marca as frases alteradas para conferir (0 cota)
#   bloco novo/reescrito    → só ele volta para o Claude
# Cada cena tem um "id" estável: escolhas de imagem, candidatos e ajustes do storyboard são guardados por id.

SISTEMA_SEGMENTAR = """Você divide roteiros do canal "Guia de Runeterra" em seções. Responda SOMENTE com JSON."""


def _norm_frase(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())


def _parece_titulo(f: dict) -> bool:
    """Seção do canal começa com o nome sozinho no início do parágrafo ("Nocturne.", "A Criação de Runeterra.")."""
    return len(f["texto"].split()) <= 6 and f["texto"].rstrip().endswith((".", "!", "?", ":"))


def titulos_possiveis(frases: list[dict]) -> list[int]:
    """Frases curtas no início de parágrafo: candidatas a título de seção."""
    inicio_par = {0} | {i + 1 for i, f in enumerate(frases[:-1]) if f["fim_de_paragrafo"]}
    return [i for i in sorted(inicio_par) if i < len(frases) and _parece_titulo(frases[i])]


def segmentar(frases: list[dict], nomes_capa: list[str], anterior: dict | None) -> list[dict]:
    """Seções: [{"titulo", "frase_inicial", "personagem_da_capa"}]. Tenta reaproveitar as fronteiras do plano
    anterior (sem cota); só pergunta ao Claude (Sonnet, barato) se apareceu uma frase com cara de título nova."""
    candidatos = titulos_possiveis(frases)
    if anterior and anterior.get("secoes"):
        textos = [_norm_frase(f["texto"]) for f in frases]
        achadas, ini = [], 0
        for s in anterior["secoes"]:
            alvo = _norm_frase(s.get("frase_texto", ""))
            i = next((j for j in range(ini, len(textos)) if textos[j] == alvo), None) if alvo else None
            if i is None:
                achadas = None
                break
            achadas.append({**s, "frase_inicial": i})
            ini = i + 1
        # todas as seções antigas continuam lá e não apareceu nenhuma frase com cara de título que já não
        # existisse antes (as que o Claude já julgou "não é seção" ficam em titulos_vistos): mesmas fronteiras
        vistos = set(anterior.get("titulos_vistos", []))
        novos = {_norm_frase(frases[i]["texto"]) for i in candidatos} - vistos
        if achadas and not novos:
            return achadas
    linhas = "\n".join(f"[{i}] {f['texto']}" for i, f in enumerate(frases))
    r = chamar_json(
        f"Personagens na capa (ícones): {', '.join(nomes_capa) or 'nenhum'}.\n\nROTEIRO (frases numeradas):\n{linhas}\n\n"
        "Divida em seções: cada personagem/tema/evento principal é uma seção, e no estilo do canal ela começa com o "
        "NOME SOZINHO numa frase própria. O que vem antes da 1ª seção é a introdução (não é seção). Responda: "
        '{"secoes": [{"titulo": "Nome da seção", "frase_inicial": 3, '
        '"personagem_da_capa": "nome exatamente como na capa, ou null"}]}',
        SISTEMA_SEGMENTAR, modelo="sonnet", etiqueta="direcao-secoes")
    secoes, ultima = [], -1
    for s in r.get("secoes", []):
        i = s.get("frase_inicial")
        if isinstance(i, int) and ultima < i < len(frases):
            pc = s.get("personagem_da_capa")
            secoes.append({"titulo": s.get("titulo") or frases[i]["texto"].strip(" ."), "frase_inicial": i,
                           "personagem_da_capa": pc if pc in nomes_capa else None})
            ultima = i
    return secoes


def _slug(t: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "secao"


def blocos_do_roteiro(frases: list[dict], secoes: list[dict], nomes_capa: list[str]) -> list[dict]:
    import hashlib

    inicios = [s["frase_inicial"] for s in secoes]
    blocos = []
    if not inicios or inicios[0] > 0:
        blocos.append({"id": "intro", "titulo": None, "personagem_da_capa": None, "de": 0,
                       "ate": (inicios[0] - 1) if inicios else len(frases) - 1, "tipo": "intro"})
    usados: set[str] = set()
    for k, s in enumerate(secoes):
        bid = _slug(s["titulo"])
        while bid in usados or bid == "intro":
            bid += "-2"
        usados.add(bid)
        ate = (inicios[k + 1] - 1) if k + 1 < len(inicios) else len(frases) - 1
        blocos.append({"id": bid, "titulo": s["titulo"], "personagem_da_capa": s.get("personagem_da_capa"),
                       "de": s["frase_inicial"], "ate": ate, "tipo": "primeira" if k == 0 else "secao"})
    for b in blocos:
        b["frases"] = [frases[i]["texto"] for i in range(b["de"], b["ate"] + 1)]
        notas = [frases[i].get("notas", []) for i in range(b["de"], b["ate"] + 1)]
        chave = json.dumps([b["frases"], b["tipo"], b["personagem_da_capa"], sorted(nomes_capa)]
                           + ([notas] if any(notas) else []), ensure_ascii=False)
        b["hash"] = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:16]
    return blocos


def mudanca_pequena(velhas: list[str], novas: list[str]) -> list[int] | None:
    """Mesmas frases com palavras trocadas (correção de nome, erro de digitação): devolve os índices que mudaram.
    None = mudança estrutural (frases novas/removidas/reescritas) → replanejar o bloco."""
    import difflib

    if len(velhas) != len(novas):
        return None
    mudadas = []
    for i, (a, b) in enumerate(zip(velhas, novas)):
        if a == b:
            continue
        # por caracteres: "no sono" → "durante o sono" ou "rúnicas" → "Rúnicas" são retoques, não reescrita
        if difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() < 0.6:
            return None
        mudadas.append(i)
    return mudadas if len(mudadas) <= max(1, len(novas) // 3) else None


def _contexto_bloco(b: dict, blocos: list[dict], tipos_antes: dict[str, int]) -> str:
    titulos = [x["titulo"] for x in blocos if x["titulo"]]
    linhas = [f"Seções do vídeo: {', '.join(titulos) or 'uma só'}."]
    if b["tipo"] == "intro":
        linhas.append("Você planeja a INTRODUÇÃO (antes da 1ª seção). A primeira cena é obrigatoriamente \"capa\".")
    else:
        linhas.append(f"Você planeja a seção \"{b['titulo']}\". Personagem desta seção na capa: "
                      f"{b['personagem_da_capa'] or 'nenhum'}.")
        if b["tipo"] == "secao" and b["personagem_da_capa"]:
            linhas.append("A primeira cena (frase [0], onde o roteiro fala o nome) é \"hub\".")
        elif b["tipo"] == "primeira":
            linhas.append("É a 1ª seção: a capa da abertura já apresentou o personagem — não use \"hub\" aqui.")
    if tipos_antes:
        uso = ", ".join(f"{t} {n}" for t, n in sorted(tipos_antes.items(), key=lambda x: -x[1]))
        linhas.append(f"Tipos já usados nas seções anteriores: {uso}. Varie: não repita os mesmos especiais.")
    return "\n".join(linhas) + "\n"


def planejar_bloco(b: dict, frases_bloco: list[dict], nomes_capa: list[str], contexto: str,
                   modelo: str = "opus") -> dict:
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    sistema = SISTEMA.format(regras=regras)
    prompt = montar_prompt(frases_bloco, nomes_capa, contexto)
    plano = chamar_json(prompt, sistema, modelo=modelo, etiqueta=f"direcao-plano:{b['id']}")
    problemas = validar(plano, frases_bloco)
    if problemas:  # uma chance de corrigir, mostrando exatamente o que está errado
        plano = chamar_json(
            "Seu plano tem estes problemas:\n- " + "\n- ".join(problemas[:30]) +
            "\n\nCorrija e devolva o JSON COMPLETO.\n\nPlano anterior:\n" + json.dumps(plano, ensure_ascii=False)
            + "\n\n" + prompt, sistema, modelo=modelo, etiqueta=f"direcao-plano-correcao:{b['id']}")
    return plano


def planejar(texto: str, palavras: list[dict], nomes_capa: list[str], dirc: Path,
             aviso=lambda msg: None, modelo: str = "opus") -> tuple[dict, list[dict], dict]:
    """Plano do vídeo inteiro, bloco a bloco, reaproveitando o que não mudou. Devolve (plano, frases, relatório)."""
    import uuid

    from notas import notas_por_frase

    frases = frases_do_roteiro(texto, palavras)
    arq_notas = dirc / "notas.json"
    if arq_notas.exists():  # [notas de direção] do roteiro, presas na frase em que aparecem
        for n, textos in notas_por_frase(json.loads(arq_notas.read_text(encoding="utf-8")), frases).items():
            frases[n]["notas"] = textos
    arq_plano, cache = dirc / "plano.json", dirc / "plano_secoes"
    cache.mkdir(exist_ok=True)
    anterior = json.loads(arq_plano.read_text(encoding="utf-8")) if arq_plano.exists() else None
    if anterior and anterior.get("formato") != 2:
        anterior = None  # plano antigo (vídeo inteiro numa chamada): não dá para reaproveitar por bloco
    secoes = segmentar(frases, nomes_capa, anterior)
    blocos = blocos_do_roteiro(frases, secoes, nomes_capa)
    velhos = {b["id"]: b for b in (anterior or {}).get("blocos", [])}
    cenas, observacoes, relatorio = [], [], {"iguais": [], "ajustados": [], "novos": []}
    tipos_antes: dict[str, int] = {}
    for n, b in enumerate(blocos, 1):
        nome = b["titulo"] or "introdução"
        arq = cache / f"{b['hash']}.json"
        if arq.exists():
            local = json.loads(arq.read_text(encoding="utf-8"))
            relatorio["iguais"].append(nome)
        else:
            v = velhos.get(b["id"])
            mudadas = mudanca_pequena(v["frases"], b["frases"]) if v and (cache / f"{v['hash']}.json").exists() else None
            # mudadas == [] = frases idênticas mas o bloco mudou (nota de direção, personagem da capa): replaneja
            if mudadas:
                local = json.loads((cache / f"{v['hash']}.json").read_text(encoding="utf-8"))
                # cena que cobre uma frase alterada: o Felipe confere no storyboard (marcas de antes continuam
                # até ele clicar "está ok")
                for i, c in enumerate(local["cenas"]):
                    fim = local["cenas"][i + 1]["frase"] if i + 1 < len(local["cenas"]) else len(b["frases"])
                    if any(c["frase"] <= m < max(fim, c["frase"] + 1) for m in mudadas):
                        c["conferir"] = True
                relatorio["ajustados"].append(nome)
            else:
                aviso(f"planejando “{nome}” ({n}/{len(blocos)}) com o Claude")
                local = planejar_bloco(b, frases[b["de"]:b["ate"] + 1], nomes_capa,
                                       _contexto_bloco(b, blocos, tipos_antes), modelo)
                relatorio["novos"].append(nome)
            for c in local.get("cenas", []):
                c.setdefault("id", f"{b['id']}-{uuid.uuid4().hex[:6]}")
            arq.write_text(json.dumps(local, ensure_ascii=False, indent=1), encoding="utf-8")
        for c in local.get("cenas", []):
            if isinstance(c.get("frase"), int) and 0 <= c["frase"] <= b["ate"] - b["de"]:
                cenas.append({**c, "frase": c["frase"] + b["de"], "secao": b["id"]})
                tipos_antes[c["tipo"]] = tipos_antes.get(c["tipo"], 0) + 1
        if local.get("observacoes"):
            observacoes.append(f"{nome}: {local['observacoes']}")
    plano = {
        "formato": 2,
        "titulos_vistos": [_norm_frase(frases[i]["texto"]) for i in titulos_possiveis(frases)],
        "blocos": [{k: b[k] for k in ("id", "titulo", "personagem_da_capa", "de", "ate", "tipo", "frases", "hash")}
                   for b in blocos],
        "secoes": [{"id": b["id"], "titulo": b["titulo"], "frase_inicial": b["de"],
                    "personagem_da_capa": b["personagem_da_capa"], "frase_texto": b["frases"][0]}
                   for b in blocos if b["tipo"] != "intro"],
        "cenas": cenas,
        "observacoes": " ".join(observacoes),
        "reaproveitamento": relatorio,
    }
    return plano, frases, relatorio


def guardar_blocos(plano: dict, dirc: Path) -> None:
    """Depois de uma revisão (pedido ao diretor), grava as cenas novas no cache do bloco — senão o próximo
    planejamento devolveria as cenas antigas."""
    cache = dirc / "plano_secoes"
    cache.mkdir(exist_ok=True)
    for b in plano.get("blocos", []):
        arq = cache / f"{b['hash']}.json"
        anterior = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
        local = [{**{k: v for k, v in c.items() if k != "secao"}, "frase": c["frase"] - b["de"]}
                 for c in plano["cenas"] if c.get("secao") == b["id"]]
        arq.write_text(json.dumps({**anterior, "cenas": local}, ensure_ascii=False, indent=1), encoding="utf-8")
