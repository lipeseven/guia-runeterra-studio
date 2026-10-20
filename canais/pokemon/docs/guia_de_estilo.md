# Guia de estilo — canal Pokémon (v0.1, 2026-10-20)

> Fonte: análise de 10 vídeos de referência (Pokemon Explainer ×3, RealLifePokemon ×3, Uproar Media ×4) —
> números em `dados/canais/pokemon/analise_referencias/estatisticas.json` e `sons_resumo.json`, anotações visuais
> em `leitura_visual.md`. Nome e identidade visual (cores, fonte, capa) ainda serão decididos pelo Felipe: este guia
> diz O QUE o nicho faz e O QUE vamos fazer; a "pele" fica para depois.

## 1. O formato que funciona no nicho
- **Catálogo "Every X Explained in N Minutes"**: um item (Pokémon, Poké Ball, região, tipo) = uma seção, em ordem
  lógica (Pokédex, geração, cronologia). É o mesmo formato do Guia de Runeterra — o motor já faz isso.
- Dois produtos diferentes nas referências:
  - **Explainer / RealLife** (13–25 min): ritmo rápido, cena média **1,5–5 s** (mediana ~2,4 s), 12–40 cortes/min.
  - **Uproar** (52–98 min): "documentário" lento, cena média 6–16 s, clipes longos. **Não é o nosso modelo.**
- **Nosso alvo**: 15–25 min, ritmo Explainer (cena média ~3 s), narração do Felipe (~165–185 palavras/min).

## 2. Recursos recorrentes (e como o nosso motor responde)
| No nicho | Como fazemos |
|---|---|
| **Mosaico-índice de todos os itens** na abertura e **entre seções** (o item atual destacado, "checklist de progresso") — presente em TODOS os canais rápidos | Nosso **hub** (grade de ícones da capa com zoom no próximo) — já existe; a capa vira a grade dos itens do vídeo |
| **Selo no canto superior esquerdo** com ícone circular + nome do item da seção, fixo a seção inteira | Nosso **cabeçalho de seção** (ícone da capa + título) — já existe |
| **Recorte da arte oficial sem fundo sobre branco** (Explainer: 60–70% das cenas) | Tipo `recorte`/`cartao` sobre o branco + acervo `_oficial/arte` e `_oficial/home` (2.584 PNGs transparentes) |
| **Clipe do anime/jogo** (RealLife 65–80%, Explainer 25–50%) | Tipo `clipe` — **curto (≤ 6 s), mudo, poucos** (regra de direitos §6 das regras de direção); preferir screenshot |
| **Ficha de stats / Pokédex** (print da Bulbapedia, tela do Game Boy) — 1 por item | **NOVO (a fazer):** cena "ficha" desenhada pelo motor com os dados da Pokédex local (tipos, categoria, altura/peso, base stats) — limpa, legível e nossa, em vez de print |
| **Telas retrô** (Game Boy, sprites pixelados, "X is evolving!") para nostalgia | Acervo: importar sprites das gerações antigas (PokeAPI/sprites) — **a fazer** |
| **Rajadas de 0,1–0,5 s** (flashes de evolução, golpes, zoom em detalhes) como pontuação | **NOVO (a fazer):** efeito "rajada" (3–6 quadros-relâmpago) no sorteio de efeitos |
| Rótulo curto em barra (nome de lugar/personagem) | Nossa legenda/rótulo — já existe |
| Capas de jogos lado a lado, tela dividida para comparar | `dividida` — já existe |
| Mapas das regiões | `telacheia` com mapa do acervo (importar mapas oficiais — a fazer) |
| Memes/piada visual curta (Jesus como Arceus, Knuckles) | Igual ao LoL: com moderação, humor do Felipe |

## 3. Fundo, paleta e texto
- **Explainer: fundo branco quase 100%**, cor só no conteúdo → coerente com o motor (fundo branco já é o padrão).
- RealLife/Uproar: o fundo é o próprio clipe (muito footage). Uproar tem fundo-marca turquesa com bolinhas —
  **identidade deles: não copiar**.
- Cada seção "se pinta" com a cor do tipo do Pokémon (azul água, laranja fogo, roxo fantasma) — dá para usar a cor
  do tipo no selo/rótulo da seção (dado já existe na Pokédex).
- **Pouquíssimo texto na tela** em todos: a narração carrega. Texto = nome no selo, rótulo curto, ficha de stats.
  Isso bate com a retrospectiva do Felipe no LoL (legendas enxutas, nome próprio).

## 4. Som (medido)
- **Voz pura é o padrão** (8 de 10 vídeos: leito a −40 dB da voz, praticamente inaudível; ≤ 1 efeito/min).
- Exceção: Pokeball (música contínua a −24 dB + "pop" a cada item, 11/min) — estilo "lista de produtos".
- Nosso padrão: igual ao LoL (voz pura, efeito raro). Sem música do anime/jogos.

## 5. Estrutura de um vídeo
1. **Abertura**: mosaico/grade de todos os itens (índice) → gancho.
2. **Seção por item**: nome (selo) → apresentação (arte oficial no branco) → ficha (tipo/stats) → história/anime/jogo
   (clipes curtos e screenshots) → curiosidade/piada.
3. **Entre seções**: volta ao mosaico com o próximo item destacado (hub).
4. **Fechamento**: curto; CTA do Felipe (sem botão "subscribe" animado copiado).

## 6. O que nos diferencia (para não parecer cópia)
- Voz real do Felipe em PT-BR (o nicho em português é menor), humor brasileiro.
- Ficha de dados **desenhada** e legível (os outros colam prints ilegíveis da Bulbapedia).
- Visual limpo no branco com arte oficial em alta (acervo oficial completo, não prints de baixa).
- Menos dependência de clipe do anime (mais seguro para direitos e mais "autoral").
