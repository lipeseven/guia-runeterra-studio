# Guia de estilo — Guia de Runeterra (v1.0)

Extraído dos 10 vídeos de referência + 1 do Felipe em `recursos de vídeo para aprender/`.
Dados brutos: `dados/analise_referencias/` (cortes, transcrições, folhas de contato, `estatisticas.json`,
som separado, `leitura_visual.md` com as anotações brutas por vídeo).
Ferramentas: `tools/analise_referencias/`.

> v1.0 (2026-10-14): estatísticas, transcrição, som e **leitura visual dos 11 vídeos** (todas as folhas de
> contato). Seções 3–4 da v0.1 continuam valendo; a seção 10 traz o que a leitura completa acrescentou.

## 1. Formato geral

| Item | Valor |
|---|---|
| Duração | 10–34 min (média ~20 min) |
| Resolução de referência | 1920×1040 @ 60 fps → **nós: 1920×1080 @ 60 fps** |
| Narração | ocupa ~96% do vídeo — praticamente sem respiros longos |
| Velocidade da fala (inglês) | ~167 palavras/min |
| Música de fundo | nenhuma (alinhado com a decisão do canal) |

## 2. Ritmo de cortes

Dois "modos" aparecem nas referências:

| Modo | Cena média | Quando |
|---|---|---|
| **Rápido** | 3–4 s | Vídeos de narrativa/lista com muita arte em tela cheia (Darkin, Demons, Major Events, Most Powerful) |
| **Construído** | 7–9 s | Vídeos mais "explicativos", em que a cena é um quadro branco que vai sendo montado aos poucos (Terrifying, Couples, Biggest Threat, Suffered) |

- Os cortes caem **no início de frases** em ~64% das vezes (acaso seria bem menos). Regra: **cortar na fronteira de frase**; dentro da frase, só elementos novos entram.
- Primeiro minuto um pouco mais acelerado (~15 cortes/min contra ~12 no resto).
- 10% das cenas têm menos de ~1 s (flashes de cinemática, impactos).
- Cenas acima de 15 s só existem no modo "construído", com elementos entrando ao longo da cena.

## 3. Tipos de cena (vocabulário do diretor)

1. **Grade de ícones** — retratos redondos com borda escura + nome embaixo, fundo branco. Usado na **abertura** (apresenta todos os personagens do vídeo) e em retomadas. Leve zoom lento.
2. **Cartão emoldurado** — fundo branco, imagem centralizada com legenda curta embaixo ("Shurima", "The Sun Disc", "Blood Magic", "Xolaani vs Zaahen"). A imagem pode ser trocada dentro do mesmo cartão enquanto a legenda muda ("sealed in their weapons").
3. **Arte em tela cheia** — splash art / arte do Universe ocupando tudo, com **zoom lento** (Ken Burns sutil).
4. **Citação sobre arte** — arte em tela cheia + citação em serifa itálica na parte de baixo, com **palavras-chave em vermelho** e a fonte em letra pequena ("Jhin, Voice lines", "Tahm Kench, Biography").
5. **Diálogo** — fundo branco, dois ícones redondos lado a lado, fala entre aspas embaixo; as palavras-chave **ficam vermelhas em sincronia com a narração**.
6. **Cartão de título/conceito** — fundo branco, texto central ("The Kinkou Order") e personagens recortados (sem fundo) entrando um a um embaixo.
7. **Trecho de cinemática** — clipe oficial em tela cheia, às vezes com o nome do personagem sobreposto ou o título da cinemática.
8. **Colagem** — 2 a 4 imagens lado a lado/em grade ilustrando uma enumeração.
9. **Explicação de gameplay** — ícones de habilidade (Q/W/E/R), item ou teclado + texto curto em vermelho ("4 bounces", "4th bullet crits", "J-H-I-N / 1 2 3 4").
10. **Meme / quebra** — meme entrando por cima da cena (ex.: o ganso do Untitled Goose Game), prints de YouTube/estatísticas, piadas visuais. Curto.
11. **Conto/fonte** — capa do conto citado com título e autor ("The Gambler's Woe, by Anthony Reynolds").

## 4. Elementos fixos

- **Marcador de seção**: no modo cartão branco, o nome do personagem/tema da seção aparece no topo central, com um ícone pequeno no canto superior esquerdo. Fica fixo durante toda a seção.
- **Construção progressiva**: elementos (ícones, personagens, textos, palavras em vermelho) entram **no momento em que são falados** — isso exige o tempo de cada palavra (Whisper).
- **Paleta**: fundo branco puro nos cartões; texto preto; destaque **vermelho**.
- **Tipografia**: fonte arredondada/manuscrita para rótulos e títulos; serifa itálica para citações.

## 5. Estrutura do roteiro

- **Abertura a frio**: começa direto no assunto, com um gancho atual ("Na última cinemática… o Xin Zhao se torna hospedeiro do Zaahen") e perguntas ("Quem é? Quão poderoso? De onde veio?"). Sem "olá, bem-vindos".
- **Formato lista**: uma seção por personagem/evento. Cada seção começa **falando só o nome** ("Xolaani.") seguido da definição ("Xolaani é a Darkin Bloodletter."), depois origem → acontecimentos → situação atual.
- **Fontes citadas** no próprio vídeo (biografia, falas, contos, quadrinhos).
- **Final seco**: termina no último item, sem encerramento longo.

## 6. Implicações para o sistema

- **Remotion é peça central**, não acessória: os tipos 1, 2, 4, 5, 6, 8, 9 e 11 são modelos de layout animados, sincronizados palavra a palavra. O FFmpeg cuida dos tipos 3 e 7, da mixagem e da codificação final.
- O **diretor (Claude)** escolhe, para cada frase, um tipo de cena do vocabulário acima e preenche os dados (imagens, legenda, palavras-chave em vermelho, quando cada elemento entra).
- **Glossário de nomes é obrigatório**: o Whisper errou "Zaahen" (→ Zahen), "Xolaani" (→ Zolani), "Kinkou" (→ Kinku), "Jhin" (→ Jin), "Rhaast" (→ Rast).
- **Ícones redondos e personagens recortados** precisam ser gerados automaticamente (recorte circular das splash arts; remoção de fundo local, por exemplo rembg).

## 7. O estilo próprio do Guia de Runeterra

Analisado em "Todos os DEMÔNIOS de League of Legends Explicados em 22 minutos" (22 min,
327 cenas, média 4,0 s, ~162 palavras/min em PT-BR). **O canal já segue o vocabulário
acima**: grade de ícones na abertura, cartões brancos com legenda, ícone da seção no canto
superior esquerdo + nome da seção no topo, citações em serifa itálica sobre arte, recortes,
cinemáticas. O que é **próprio do canal** e deve prevalecer sobre as referências:

- **Modo rápido** como padrão (3–4 s por cena).
- **Legendas com humor e gíria brasileira** nos cartões ("se não fizer o mewing", "Swain é zika",
  "gg panth", "Soraka, é você?") misturadas a legendas descritivas ("Noxus invadiu Ionia").
- **Mais memes e imagens do mundo real** (fotos de banco: terapia, pessoa triste, fita de luto;
  memes brasileiros e internacionais: Tom, M&M, Chaves etc.) para ilustrar sentimentos e piadas.
- **Narração mais literária/dramática**, com **ganchos que ligam uma seção à próxima**
  ("E o verdadeiro perigo é quando essas entidades… / Se os Azakanas precisam…").
- **Seção começa com o nome sozinho** ("Nocturne."), igual às referências.
- **Encerramento com chamada para ação** ("É isso rapaziada… deixem um like, se inscrevam…
  deixem sugestões… Valeu, falou e um abraço") — diferente das referências, que terminam seco.
- Whisper em PT também erra nomes: "Asacanas" (Azakanas), "Ione" (Yone), "guerras rônicas" (rúnicas).

## 8. Som (efeitos e trilha) — analisado nos 11 vídeos

Como foi medido: Demucs separa a narração do resto (`tools/analise_referencias/separar_sons.py`); no que sobra,
`analisar_sons.py` detecta picos acima do fundo, classifica com CLAP (local) e mede volume vs. voz.
Dados: `dados/analise_referencias/sons_resumo.json`, `<vídeo>/som/eventos.json`; exemplos em `sons_exemplos/`.
Cuidado: o Demucs deixa vazar consoantes da voz como "pops" (~100% em cima da fala, até no vídeo do Felipe) —
o analisador descarta esses vazamentos.

- **O padrão é voz pura.** Em 8 dos 11 vídeos (incluindo o do Felipe) não há trilha audível (fundo ≈ -40 dB
  da voz = resíduo da separação) e quase nenhum efeito: **0 a 0,4 efeito por minuto**.
- **Transições são cortes secos**, sem whoosh: só 2–15% dos sons coincidem com um corte de cena.
- Os poucos sons dos vídeos "secos" são pontuais e temáticos (vidro quebrando, espada, sino, magia), quase
  sempre de clipes do jogo ou de um momento marcante — não decoração.
- **Exceções:**
  - "The Demons…" (10 min): trilha tensa contínua a ~-19 dB da voz + ~3,7 efeitos/min (explosões, batidas,
    criaturas) fortes (~-7 dB da voz).
  - "Aatrox vs Mordekaiser": trilha com batida só nos primeiros 7 minutos (-24 a -33 dB), depois silêncio.
- **Implicação para o Guia de Runeterra** (que já é sem trilha, por escolha do Felipe): efeito sonoro é tempero
  raro e com sentido — no máximo ~1–2 por minuto, ancorado em palavra/momento marcante (revelação, golpe, magia,
  criatura, nome que abre seção), volume bem abaixo da voz (-12 a -18 dB), nunca em todo corte. Variar sempre.

## 9. Em aberto

- Nada pendente de análise. Próximo passo é construir os recursos da seção 10 que o Felipe escolher.

## 10. Leitura visual completa (v1.0)

### 10.1 Cada vídeo tem um "modo" — e o modo muda o visual inteiro

| Modo | Vídeos | Visual |
|---|---|---|
| **Branco/explicativo** | Demons, Most Powerful 1 e 2, Major Events, Suffered | cartões brancos, recortes, legendas, memes |
| **Escuro/cinematográfico** | Biggest Threat, Aatrox vs Mordekaiser | quase sem branco; título da seção no topo sobre a arte, telas divididas, citações no preto |
| **Narrativo longo** | Every Couple | cenas de 10–40 s, quadrinhos percorridos, cinemáticas (Arcane) |
| **Versus** | Aatrox vs Mordekaiser | placar por categoria ("Power", "Feats", "Battle IQ"), arte gráfica alto contraste |

→ O diretor deve escolher um modo **por vídeo** (pelo tema) e variar entre vídeos: um canal que faz todo vídeo
igual parece automatizado.

### 10.2 Recursos encontrados que ainda NÃO temos no Remotion

| Recurso | Como é | Onde apareceu |
|---|---|---|
| **Hub de seção** | a grade/esteira de ícones volta entre TODAS as seções e dá zoom (ou desliza) até o ícone da próxima — é a transição de seção | todos os vídeos com lista |
| **Tela dividida** | 2 (ou 3) imagens em altura total lado a lado, nome de cada lado; às vezes um círculo no meio com um detalhe | Couples, Aatrox, Suffered, Threat |
| **Meio a meio** | arte em metade da tela + frase curta no branco da outra metade | Most Powerful 2, Demons ("10 Kings") |
| **Texto sozinho** | frase/conceito no branco ou no preto, sem imagem ("Another story", "The Clarity", "Being") | quase todos |
| **Lista acumulada** | painéis com legenda entrando lado a lado conforme a narração enumera | Suffered, Most Powerful 2 |
| **Comparação construída** | 2 imagens rotuladas entram uma por vez ("villain" → "savior") | Most Powerful |
| **Linha do tempo** | ícones sobre uma linha com datas; cartão só com a data grande; nome do evento + intervalo | Major Events, Aatrox |
| **Mapa** | mapa com zoom na região e rótulo; regiões coloridas com nomes | Major Events |
| **Diagrama** | ícones ligados por linhas (triângulo do Trifarix, pares de casais com tipo de relação) | Major Events, Couples |
| **Nome sobre arte** | nome grande + subtítulo pequeno colado no personagem ("Raum / the demon of secrets") | Threat, Aatrox, Suffered |
| **Título da seção no topo da arte escura** | variação do marcador de seção para o modo escuro | Threat, Suffered |
| **Quadrinho percorrido** | página de HQ com pan/zoom de painel em painel | Couples |
| **Clarão branco** | 2–6 quadros brancos como impacto/transição dentro de cinemática | Most Powerful 2, Couples |
| **Montagem relâmpago** | cortes de 0,1–0,5 s (clímax de cinemática ou piada com o fundo trocando) | Aatrox, Threat |
| **Anotação com seta** | seta desenhada apontando um detalhe ("wings ←", "→ Avarosa") | Aatrox, Major Events |
| **Personagem + reação** | ícone do personagem com nome e, ao lado, meme/emoji com fala ("Rell" + "I'm in") | Suffered, Most Powerful |
| **Crédito de fan art na cena** | linha pequena embaixo da imagem com o nome do artista | Couples |
| **Fonte na cena** | "in-game voice lines", "The Call Cinematic" em letra pequena | Most Powerful, Aatrox |
| **Aviso de spoiler** | cartão "spoilers warning" com recorte do personagem | Couples |

### 10.3 Padrões confirmados nos 11
- Legendas curtas em minúsculas, descritivas OU frases narrativas ("two realms emerged",
  "maybe this wasn't a good idea") OU piada — misturadas.
- Memes e fotos reais em todos os vídeos (a cada 1–3 min), sempre ligados ao sentido da frase.
- Final: metade termina seco, metade com CTA ("have I missed anything?", "thanks for watching").
  O Guia de Runeterra mantém o CTA próprio dele (seção 7).

### 10.4 Marcas registradas da referência — NÃO copiar
- O **emoji amarelo apontando** e o **boneco-bolha desenhado** que reaparecem dezenas de vezes, o Poro do
  final, "if you've made it this far…", a abertura "A long time ago in a galaxy far, far away…".
- São a identidade do @explainedbynavi. Copiar isso é o que faria o Guia de Runeterra parecer cópia.
  Se o Felipe quiser um mascote/bordão recorrente, que seja **dele** (ex.: um meme brasileiro fixo).
