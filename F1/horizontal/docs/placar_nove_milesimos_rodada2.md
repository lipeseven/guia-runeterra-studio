# Placar independente — "Nove milésimos" (rodada 2, 2026-11-14)

Avaliador independente (não produziu o vídeo). Vídeo: `F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v3.mp4`
(1920×1080, 60 q/s, 5.429 quadros, 90,5 s, 20 cenas, **voz Fish provisória**, trilha local nova). Dados por cena e todas as
medidas em `placar_rodada2.json`. Mesma rubrica da rodada 1: (a) dados 25 · (b) sincronia/ritmo 15 · (c) clareza 20 ·
(d) movimento 15 · (e) estética/vida 15 · (f) SFX/transição 10.

## Como foi avaliado
- Por cena: folha de 8 quadros (início+2, 6 no meio, fim−3) e folha de 12 quadros **consecutivos** no meio; nas 9 cenas com
  movimento (GPS e gráficos) uma 2ª folha de 12 consecutivos a 80 % da cena; extra de 12 consecutivos na cena 14 (q3602,
  2×) e 9 quadros em resolução cheia (`qNNNN_cheio.jpg`). Tudo em `F1/horizontal/testes/placar/rodada2/`. Olhei as folhas.
- Medido por script (`testes/placar/rodada2/scripts/`):
  - **Ovais/traços**: caixa do traço vermelho em 30–200 quadros seguidos depois de desenhado (cenas 1, 4, 17, 19): **0 px**
    de variação (não pulam). Na 5 a janela pega o traço ainda crescendo (só a ponta direita anda; y fixo).
  - **Tranco no GPS**: correlação de fase do quadro inteiro (480p) nas 5 cenas: 0 reversões e salto p99 ≤ 0,17 px nas
    cenas 2, 8, 12, 18; cena 14 (2×) 3 reversões, p99 1,3 px, máx 2,2 px — na folha q3602–q3613 o movimento é contínuo,
    sem tranco visível. O chão agora anda: 2,5–8,5 px/quadro (960p, mediana num recorte sem HUD/carro) contra ~0,1 px
    na rodada 1 (medida de recorte é ruidosa por causa dos ladrilhos repetidos: serve para "anda", não para precisão).
  - **HUD × OpenF1**: 43 leituras (86 valores) do HUD nas 5 cenas de GPS contra o `car_data` bruto interpolado no mesmo
    tempo da volta: **erro médio 0,8 km/h, p90 2, máximo 6** (q5155, frenagem a 0,5× — amostragem de 4 Hz). Bate.
  - **Rótulos e duelos × palavra** (aparição por quadro): todos entre +0,1 e +0,2 s da palavra (ex.: 104 em 41,15 s × fala
    41,02; 1:16.514 em 65,78 × 65,66; 347 em 75,82 × 75,70).
  - **Áudio**: refiz só a trilha com o mesmo filtro (`filtro_audio.txt`, sidechain) e separei SFX = mix − voz − trilha
    (a voz entra a −3 dB por canal; conferido por mínimos quadrados, resíduo −166 dB). RMS/pico de cada SFX × voz na
    janela do evento e pico × palavra-âncora.

## O que NÃO deu para avaliar
- **Não ouvi nada.** (f) e parte de (b) vêm de números: timbre, gosto da trilha, se um clique a −25 dB da voz "aparece"
  ou não, isso é do Felipe. A voz é a Fish provisória; com a voz dele os tempos e o mascaramento mudam.
- Não assisti corrido em tempo real; suavidade = quadros consecutivos + correlação de fase.
- Não reconsultei a API do OpenF1 online: comparei com o `car_data` bruto que o próprio kit baixou
  (`kit/graficos/comparacoes/11400_44-19_63-21.json`). O speed trap 350 × 347 e os setores conferi contra o relatório/roteiro, não na API.

## Placar (comparado com a rodada 1)
| # | cena (id) | s | a 25 | b 15 | c 20 | d 15 | e 15 | f 10 | **nota** | r1 | Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | "Nove milésimos" (c8b897f1) | 1,6 | 24 | 13 | 18 | 14 | 7 | 8 | **84** | 84 | 0 |
| 2 | GPS fim da volta (447ab02a) | 6,2 | 23 | 12 | 15 | 13 | 10 | 6 | **79** | 66 | +13 |
| 3 | velocidade volta inteira (747ede00) | 5,1 | 23 | 12 | 15 | 14 | 11 | 7 | **82** | 82 | 0 |
| 4 | 1:16.514 oval (abbcf455) | 4,7 | 25 | 14 | 17 | 14 | 7 | 7 | **84** | 85 | −1 |
| 5 | +0.009 s (791bf924) | 2,8 | 25 | 14 | 18 | 14 | 6 | 6 | **83** | 82 | +1 |
| 6 | capítulo 1 (f7de54d4) | 3,3 | 24 | 13 | 19 | 14 | 11 | 7 | **88** | 87 | +1 |
| 7 | setores (a68a79fb) | 3,4 | 25 | 9 | 17 | 14 | 12 | 6 | **83** | 82 | +1 |
| 8 | GPS reta → Curva 1 (e0df513b) | 7,8 | 23 | 12 | 15 | 13 | 10 | 7 | **80** | 61 | +19 |
| 9a | frenagem 900–1350 m (dd4ffd33) | 4,2 | 21 | 13 | 16 | 14 | 11 | 5 | **80** | 81* | −1 |
| 9b | duelo mínima 104 × 100 (712d73a7, nova) | 4,6 | 24 | 13 | 18 | 12 | 8 | 5 | **80** | 81* | −1 |
| 10 | capítulo 2 (c247ab85) | 2,5 | 24 | 13 | 19 | 14 | 10 | 7 | **87** | 86 | +1 |
| 11 | velocidade S2 + faixa (528c1e00) | 5,2 | 19 | 13 | 15 | 14 | 11 | 5 | **77** | 71 | +6 |
| 12 | GPS saída do grampo (a37e2524) | 5,4 | 22 | 13 | 13 | 13 | 10 | 4 | **75** | 65 | +10 |
| 13 | duelo S2 30.008 × 30.030 (d96a46d3) | 2,5 | 25 | 14 | 19 | 13 | 8 | 5 | **84** | 79 | +5 |
| 14 | GPS setor 3 2× (d5a93934) | 4,6 | 23 | 13 | 14 | 13 | 10 | 4 | **77** | 64 | +13 |
| 15 | duelo resultado (f6d5a7f0) | 6,3 | 25 | 13 | 18 | 12 | 7 | 5 | **80** | 71 | +9 |
| 16 | duelo speed trap (760ea8f0) | 8,1 | 24 | 12 | 18 | 11 | 6 | 5 | **76** | 65 | +11 |
| 17 | "Velocidade de reta" riscado (408641ec) | 2,9 | 24 | 14 | 18 | 14 | 6 | 7 | **83** | 83 | 0 |
| 18 | GPS perseguição câmera lenta (76c5a688) | 5,0 | 18 | 13 | 9 | 13 | 11 | 7 | **71** | 70 | +1 |
| 19 | fecho "Nove milésimos." (e9aa5677) | 4,5 | 24 | 14 | 18 | 14 | 7 | 5 | **82** | 80 | +2 |

\* a antiga cena 9 (81, 8,7 s) virou 9a + 9b; comparo as duas com o 81 dela.

**Nota global (ponderada pela duração): 79,8 / 100** (rodada 1: 73,8; +6,0).
Por critério (% do máximo, ponderado): dados 92 (84) · sincronia 85 (73) · clareza 81 (72) · movimento 88 (89) ·
**estética/vida 60** (52) · **SFX 58** (63).

**Meta (toda cena ≥ 80 e global ≥ 80): NÃO atingida.** Global 0,2 abaixo; 6 cenas abaixo de 80: 2 (79), 11 (77), 12 (75),
14 (77), 16 (76), 18 (71).

Leitura: as correções de dados e sincronia funcionaram (speed trap certo, números ditos aparecem na palavra, HUD bate com o
OpenF1, o GPS ganhou mundo, minimapa e placa da Curva 1, e o chão anda). O que segura a nota agora é: **as etiquetas
HAM/RUS** (novas) que se cobrem ou apontam o carro errado; **SFX baixos demais** depois do sidechain (o problema virou o
contrário da rodada 1); e **quatro duelos iguais** que deixam o meio-fim do vídeo parado.

## Os 5 maiores problemas restantes
1. **Etiqueta no carro errado na perseguição (cena 18) e etiquetas sobrepostas nas cenas 2, 8, 12, 14.** Em q4945
   (`q4945_cheio.jpg`) a etiqueta "HAM" está em cima da Mercedes e "RUS" flutua sobre pista vazia; o espectador lê o
   contrário do que a fala diz ("Hamilton freia depois"). Em q3355/q3398 a "RUS" cobre a "HAM"; em q2093 só se vê a Ferrari.
   Causa: `montador/hyperframes/gps.html:161` ancora a etiqueta 2,2 m acima do carro (na câmera baixa de perseguição esse
   ponto cai sobre o carro da frente) e `:166` só sobe a 2ª etiqueta 46 px fixos, sem olhar quem está à frente na tela.
   Correção: na perseguição, etiqueta ao lado/abaixo do próprio carro (ou só a cor do rastro); na alta, ordenar por
   profundidade e afastar até não haver interseção, com perninha até o carro.
2. **SFX enterrados sob a voz.** Com o sidechain do SFX (`montador/mixagem.py:30`, `DUCK_SFX` ratio 3) os cliques/pops
   novos ficam 23–28 dB abaixo da voz em RMS: tecla "22" −28, clique "30.008" −28, pop "350" −26, clique "1:16.514" −23.
   O **sino do fecho continua inaudível**: agora cabe inteiro, mas cai sob "E uma diferença praticamente invisível" e fica
   em −51 dBFS RMS / −38,8 dBFS pico, 33 dB abaixo da voz. Buracos sem SFX > 6 s: 2,2–15,9, 31,0–41,3, 47,2–56,7,
   57,1–65,6, 65,9–72,1, 72,3–79,1 s (na prática os SFX entre 47 e 79 s não contam). Correção: cliques/pops fora do
   sidechain (ou ratio menor) e alvo "pico do SFX ≈ pico da voz −6 dB"; sino depois de "cronômetro." com cauda de 2,5 s.
3. **Quatro duelos iguais em 35 s (9b, 13, 15, 16 = 21,4 s) com tempo vazio.** Cartões entram vazios e o número só
   aparece na palavra: 1,6 s vazio na 9b, 2 s na 15, 1,2 s + cartão HAM vazio 3,5 s na 16 (8,1 s quase parados).
   Correto e legível, mas (d) e (e) caem e repete o layout (regra de não parecer produção em massa). Causa: SPEC escolheu
   `cartoes/duelo` 4× e `montador/receitas.py:219` (`_duelo`) mostra o cartão desde o início. Correção: variar (speed trap
   na pista/minimapa, barras crescendo, um duelo com foto/cor cheia), cartão entrar com o número.
4. **Cena 11: a faixa "curvas rápidas do setor 2" não mostra nada.** As duas linhas ficam iguais dentro de 2.520–3.020 m,
   os "22 milésimos" não aparecem, e o trecho não tem fonte (escolhido na SPEC). O espectador vê "destaque" sem diferença.
   Correção: mostrar o número (30.030 × 30.008 / −0,022 s) na faixa, ou ampliar a escala no trecho; delta só depois de
   resolver a distância (`kit/graficos/py/preparar.py:191`).
5. **GPS ainda pouco vivo e sem som (cenas 2, 12, 14).** Melhorou muito (ladrilhos, zebras, prédios, céu na perseguição),
   mas a câmera alta mostra quase só chão bege com 1–3 caixas; nada de arquibancada/estádio; e as três cenas não têm nenhum
   SFX. Carros continuam fundidos quando colados (o "translúcido" deixa o rastro ciano aparecer através do carro, q4945).
   Correção: arquibancadas/estádio como formas na reta final e no setor 3, passagem de som leve (whoosh baixo) nas trocas
   de câmera.

## Defeitos por cena < 80 (quadro/tempo · causa · correção)
- **2 (79)**: carros fundidos e etiquetas coladas (q311, q418); 6,2 s sem SFX. · `gps.html:166`. · etiquetas por
  profundidade; som de passagem na linha. (Linha de chegada e rótulo "Classificação · GP do México 2026" agora certos.)
- **11 (77)**: faixa em q2991 (49,85 s, na palavra "curvas") sem diferença visível; tecla do "22" a −28 dB. · SPEC
  (destaque sem fonte) + `preparar.py:191`. · número na faixa, escala local.
- **12 (75)**: "RUS" cobre "HAM" (q3355, q3398); "100% de acelerador" só como texto; sem SFX. · `gps.html:161-166`. ·
  etiquetas separadas; HUD com acelerador marcado (`marcar`, já implementado e não usado).
- **14 (77)**: etiquetas sobrepostas e carro da RUS escondido (q3602–q3613, q3744); sem SFX; ainda sem estádio. ·
  `gps.html:161-166`, `kit/gps` (mundo). · idem 1 e 5.
- **16 (76)**: 8,1 s com cartões vazios/parados (q4203–q4549); mesmo layout da 15; pop do "350" a −26 dB. ·
  `receitas.py:219` + SPEC. · variar a forma, cortar o vazio.
- **18 (71)**: etiqueta HAM no carro da RUS, RUS sobre pista vazia (q4945–q5155); carro translúcido com rastro atravessando. ·
  `gps.html:161` (+2,2 m na perseguição) e `:166`. · etiqueta presa ao carro na câmera baixa.

## Cenas que passaram (≥ 80), notas curtas
- 8 (80, +19): agora a melhor GPS: rótulo "Antes da frenagem da Curva 1" em 28,68 s ("logo"), "RUS 349 · HAM 345" na
  palavra, HUD igual ao OpenF1, placa "1"; perde por carros fundidos na curva e placa "1" cobrindo o rodapé (q2093).
- 9a (80): faixa "HAM freia ~22 m depois" 0,36 s depois do "22"; distância integrada (±15 m) sem aviso; sem SFX.
- 9b (80): 104 e 100 na palavra; cartões vazios 1,6 s; riser do capítulo 2 começa sob "104 contra 100" (41,33 s).
- 13 (84) e 15 (80): quem é quem resolvido; 15 tem 2 s vazios no início.
- 19 (82): impacto agora 3,4 dB abaixo da voz (era 1,7 acima); sino inaudível (problema 2).
- 1, 3, 4, 5, 6, 7, 10, 17: praticamente iguais à rodada 1 (texto em fundo claro; 3 ainda com "76,514" e rodapé em inglês).

## Trilha × voz (RMS, janelas de 400 ms com fala)
Trilha (depois do sidechain) −36,3 dBFS RMS; voz −17,8. Margem voz − trilha: mediana **22 dB**, p10 9,3 dB; só 6 % das
janelas de fala com margem < 6 dB, todas em finais/começos de frase (1,2; 7,6; 10,0; 12,8; 17,2; 20,0; 26,8; 34,8; 36,4;
38,8; 63,2; 74,4; 78,0; 85,6 s), onde a voz já está caindo. **A trilha não cobre a voz.** Se ela é audível/agradável a
−36 dBFS só o ouvido diz. Último som da trilha em 89,8 s (vídeo 90,5 s). Loudness do MP4 −14,0 LUFS / −2,3 dBTP (do relatório).

## O que está resolvido e não deve ser mexido
Ovais/traços estáveis (0 px), GPS sem vai-e-volta nem tranco, HUD fiel ao OpenF1, rótulos e duelos na palavra, speed trap
correto, fecho com impacto abaixo da voz, trilha sob a voz, chão que dá sensação de velocidade, minimapa com ponto.
