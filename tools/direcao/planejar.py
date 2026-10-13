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
TIPOS = ("capa", "cartao", "telacheia", "recorte", "mosaico", "clipe", "dialogo")


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
  cartao    — fundo branco, imagem emoldurada no centro e LEGENDA curta embaixo (o "feijão com arroz").
  telacheia — arte ocupando a tela toda (impacto, atmosfera, transição). Sem legenda.
  recorte   — personagem recortado sobre fundo branco + legenda (apresentar/descrever um personagem).
  mosaico   — fundo em tela cheia + 2 a 4 imagens que entram quando cada item é falado. SÓ enumeração rápida
              de itens do mesmo assunto. Nunca dois mosaicos seguidos.
  clipe     — trecho de animação/cinemática (ação, revelação, emoção) quando faz sentido existir tomada disso.
  dialogo   — dois ícones e a fala entre aspas: fala atribuída a um personagem dirigida a outro.
- Legendas: curtas (1 a 5 palavras), em português. Podem ser descritivas ("Noxus invadiu Ionia") ou,
  com moderação, ter humor/gíria brasileira no tom do canal ("Swain é zika", "gg") — o Felipe revisa.
- Seções: cada personagem/tema principal é uma seção (o nome dele fica no topo dos cartões, com o ícone da capa).

=== COMO DESCREVER A BUSCA ===
"busca.o_que" é a descrição VISUAL, em inglês, do que a imagem deve mostrar segundo o SENTIDO da frase
(metáforas não são literais). "busca.personagens" são nomes de LoL que devem aparecer (pode ser vazio).
"busca.categorias" prefere entre: splash, arte, recorte, icone, meme, foto, mapa, hq, cinematica, carta.
Para "clipe", a busca descreve a ação da tomada.
"""

FORMATO = """Responda com este JSON:
{
 "secoes": [{"titulo": "Nome da seção", "frase_inicial": 0, "personagem_da_capa": "Nome exatamente como na capa ou null"}],
 "cenas": [
  {"frase": 0, "comeca_na_palavra": null, "tipo": "capa", "legenda": null, "legenda_na_palavra": null,
   "destaques": [], "busca": null, "mosaico": null, "dialogo": null},
  {"frase": 1, "comeca_na_palavra": null, "tipo": "cartao", "legenda": "um conto infantil", "legenda_na_palavra": "conto",
   "destaques": [], "busca": {"o_que": "...", "personagens": ["..."], "categorias": ["arte"]}, "mosaico": null, "dialogo": null},
  {"frase": 7, "comeca_na_palavra": "Volibear", "tipo": "mosaico", "legenda": null, "legenda_na_palavra": null, "destaques": [],
   "busca": {"o_que": "fundo...", "personagens": [], "categorias": ["arte"]},
   "mosaico": [{"palavra": "Volibear", "busca": {"o_que": "...", "personagens": ["Volibear"], "categorias": ["splash"]}}],
   "dialogo": null}
 ],
 "observacoes": "1 a 3 frases sobre escolhas que o Felipe deve conferir"
}
Regras do JSON: "frase" é o número [n] da frase; "comeca_na_palavra" e "legenda_na_palavra" são palavras que
EXISTEM naquela frase (copie exatamente); as cenas estão em ordem e cobrem o roteiro inteiro;
"dialogo" = {"esquerda": "Personagem que fala", "direita": "Personagem ouvinte", "destaques": ["palavra"]}."""


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
        for campo in ("comeca_na_palavra", "legenda_na_palavra"):
            w = c.get(campo)
            if w and re.sub(r"[^\wÀ-ú-]", "", w).lower() not in palavras:
                problemas.append(f"cena {k}: {campo} {w!r} não está na frase {n}")
    return problemas


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
