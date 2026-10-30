"""Pokédex do canal Pokémon (dados, sem imagens): todas as espécies da PokeAPI (GraphQL, grátis, sem chave) →
dados/pokemon/pokedex.json. É o "universo" que o roteirista, a conferência de fatos e as etiquetas do acervo
usam: nome, geração/região, tipos, evolução, lendário/mítico, categoria (genus), formas (regionais, mega…) e a
descrição da Pokédex.

Separado do Guia de Runeterra: nada aqui entra no acervo.db do LoL.

Uso:  .venv\\Scripts\\python.exe tools\\pokemon\\pokedex.py
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
PASTA = RAIZ / "dados" / "pokemon"
GRAPHQL = "https://beta.pokeapi.co/graphql/v1beta"
INGLES, ESPANHOL = 9, 7  # PokeAPI não tem pt-BR; os nomes de Pokémon no Brasil são os em inglês

REGIOES = {1: "Kanto", 2: "Johto", 3: "Hoenn", 4: "Sinnoh", 5: "Unova", 6: "Kalos", 7: "Alola", 8: "Galar", 9: "Paldea"}
TIPOS_PT = {"normal": "Normal", "fire": "Fogo", "water": "Água", "grass": "Planta", "electric": "Elétrico",
            "ice": "Gelo", "fighting": "Lutador", "poison": "Venenoso", "ground": "Terrestre", "flying": "Voador",
            "psychic": "Psíquico", "bug": "Inseto", "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão",
            "dark": "Sombrio", "steel": "Aço", "fairy": "Fada", "stellar": "Estelar"}

STATS_PT = {"hp": "PS", "attack": "Ataque", "defense": "Defesa", "special-attack": "At. Esp.",
            "special-defense": "Def. Esp.", "speed": "Velocidade"}

CONSULTA = """query {
  pokemon_v2_pokemonspecies(order_by: {id: asc}) {
    id name generation_id is_legendary is_mythical is_baby evolution_chain_id evolves_from_species_id
    nomes: pokemon_v2_pokemonspeciesnames(where: {language_id: {_in: [%d, %d]}}) { name genus language_id }
    textos: pokemon_v2_pokemonspeciesflavortexts(where: {language_id: {_eq: %d}}, order_by: {version_id: desc}, limit: 1) {
      flavor_text
    }
    formas: pokemon_v2_pokemons(order_by: {id: asc}) {
      id name is_default height weight
      tipos: pokemon_v2_pokemontypes(order_by: {slot: asc}) { tipo: pokemon_v2_type { name } }
      stats: pokemon_v2_pokemonstats(order_by: {stat_id: asc}) { base_stat stat: pokemon_v2_stat { name } }
    }
  }
}""" % (INGLES, ESPANHOL, INGLES)


def baixar() -> list[dict]:
    r = requests.post(GRAPHQL, json={"query": CONSULTA}, timeout=180)
    r.raise_for_status()
    especies = r.json()["data"]["pokemon_v2_pokemonspecies"]
    nome_de = {e["id"]: next((n["name"] for n in e["nomes"] if n["language_id"] == INGLES), e["name"]) for e in especies}
    saida = []
    for e in especies:
        en = next((n for n in e["nomes"] if n["language_id"] == INGLES), {})
        es = next((n for n in e["nomes"] if n["language_id"] == ESPANHOL), {})
        formas = []
        for f in e["formas"]:
            formas.append({"id": f["id"], "nome": f["name"], "padrao": f["is_default"],
                           "tipos": [TIPOS_PT.get(t["tipo"]["name"], t["tipo"]["name"]) for t in f["tipos"]],
                           "altura_m": f["height"] / 10, "peso_kg": f["weight"] / 10,
                           "stats": {STATS_PT.get(x["stat"]["name"], x["stat"]["name"]): x["base_stat"] for x in f["stats"]}})
        padrao = next((f for f in formas if f["padrao"]), formas[0] if formas else {})
        saida.append({
            "numero": e["id"], "nome": nome_de[e["id"]], "slug": e["name"],
            "categoria_en": en.get("genus"), "categoria_es": es.get("genus"),
            "geracao": e["generation_id"], "regiao": REGIOES.get(e["generation_id"]),
            "tipos": padrao.get("tipos", []), "stats": padrao.get("stats", {}),
            "altura_m": padrao.get("altura_m"), "peso_kg": padrao.get("peso_kg"), "lendario": e["is_legendary"], "mitico": e["is_mythical"],
            "bebe": e["is_baby"], "evolui_de": nome_de.get(e["evolves_from_species_id"]),
            "cadeia_evolutiva": e["evolution_chain_id"],
            "pokedex_en": " ".join((e["textos"][0]["flavor_text"] if e["textos"] else "").split()),
            "formas": formas,
        })
    return saida


if __name__ == "__main__":
    PASTA.mkdir(parents=True, exist_ok=True)
    dex = baixar()
    (PASTA / "pokedex.json").write_text(json.dumps(dex, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(dex)} espécies · {sum(len(d['formas']) for d in dex)} formas · "
          f"{sum(d['lendario'] for d in dex)} lendários · {sum(d['mitico'] for d in dex)} míticos")
