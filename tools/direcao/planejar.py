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

FORMATO = """Responda com este JSON (campos que não se aplicam = null):
{
 "secoes": [{"titulo": "Nome da seção", "frase_inicial": 0, "personagem_da_capa": "Nome exatamente como na capa ou null"}],
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
roteiro inteiro; "pecas" (mosaico/dividida/lista) entram na ordem em que as palavras são faladas — a 1ª peça
entra junto com a cena; dividida = 2 ou 3 peças, lista = 2 a 5, mosaico = 2 a 4."""


def montar_prompt(frases: list[dict], nomes_capa: list[str]) -> str:
    linhas = [f"[{f['n']}] ({f['segundos']}s){' ¶' if f['fim_de_paragrafo'] else ''} {f['texto']}" for f in frases]
    total = sum(f["segundos"] for f in frases)
    return (f"Personagens na capa (ícones disponíveis): {', '.join(nomes_capa) or 'nenhum'}.\n"
            f"Narração total: {total:.0f}s em {len(frases)} frases (¶ = fim de parágrafo). Alvo: ~{round(total / 4)} cenas.\n\n"
            "ROTEIRO:\n" + "\n".join(linhas) + "\n\n" + FORMATO)


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


def planejar(texto: str, palavras: list[dict], nomes_capa: list[str], modelo: str = "opus") -> tuple[dict, list[dict]]:
    regras = (RAIZ / "docs" / "regras_de_direcao.md").read_text(encoding="utf-8")
    frases = frases_do_roteiro(texto, palavras)
    plano = chamar_json(montar_prompt(frases, nomes_capa), SISTEMA.format(regras=regras), modelo=modelo,
                        etiqueta="direcao-plano")
    problemas = validar(plano, frases)
    if problemas:  # uma chance de corrigir, mostrando exatamente o que está errado
        plano = chamar_json(
            "Seu plano tem estes problemas:\n- " + "\n- ".join(problemas[:30]) +
            "\n\nCorrija e devolva o JSON COMPLETO.\n\nPlano anterior:\n" + json.dumps(plano, ensure_ascii=False)
            + "\n\n" + montar_prompt(frases, nomes_capa),
            SISTEMA.format(regras=regras), modelo=modelo, etiqueta="direcao-plano-correcao")
        plano["problemas_restantes"] = validar(plano, frases)
    return plano, frases
