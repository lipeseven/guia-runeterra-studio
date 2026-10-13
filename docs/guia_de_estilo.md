# Guia de estilo — Guia de Runeterra (v0.1)

Extraído dos 10 vídeos de referência em `recursos de vídeo para aprender/`.
Dados brutos: `dados/analise_referencias/` (cortes, transcrições, folhas de contato, `estatisticas.json`).
Ferramentas: `tools/analise_referencias/`.

> Versão 0.1: estatísticas cobrem os 10 vídeos; a leitura visual detalhada foi feita em
> 2 deles ("The Darkin…" e "The Most Terrifying Characters…"). Ampliar conforme necessário.

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

## 8. Em aberto

- Efeitos sonoros: ainda não analisados (quais sons, em que momentos).
- Transições: aparentemente cortes secos; confirmar se há whoosh/flash.
