# Placar independente — "Nove milésimos" (rodada 3, final, 2026-11-14)

Avaliador independente (não produziu o vídeo). Vídeo: `F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v4.mp4`
(1920×1080, 60 q/s, 5.429 quadros, 90,5 s, 20 cenas, **voz IA provisória de teste**, trilha local). Medidas e notas por cena
em `placar_rodada3.json`. Mesma rubrica das rodadas 1 e 2: (a) dados 25 · (b) sincronia/ritmo 15 · (c) clareza 20 ·
(d) movimento 15 · (e) estética/vida 15 · (f) SFX/transição 10. IDs novos: 9b = `09e13e9a`, 15 = `fe9cb062`.

## Como foi avaliado
- Folhas por cena (8 quadros + 12 consecutivos no meio; nas 10 cenas com movimento, mais 12 consecutivos a 80 %), 17 quadros
  em resolução cheia e 2 folhas de diagnóstico (`diag_q3672_seq12.jpg`, `diag_q295_seq12.jpg`). Tudo em
  `F1/horizontal/testes/placar/rodada3/`. Olhei as folhas.
- Scripts em `testes/placar/rodada3/scripts/` (caminhos pela pasta do script; dados na pasta principal; intermediários em `_aval/`):
  `quadros.py` (folhas), `video.py` (GPS, etiquetas, ovais, quadros parados, igualdade com o v3), `audio.py`, `hud.py` (+ `hud.json`
  com as leituras feitas olhando os quadros), `diag.py`, `placar.py`.
- **Correção de método:** `cv2.phaseCorrelate` com janela altera os arrays no lugar; os scripts da rodada 2 passavam o mesmo
  array para a medida seguinte. Agora vão cópias. As conclusões da rodada 2 sobre o GPS (sem vai-e-volta) continuam valendo.

## Medidas
- **Ovais/traços** (cenas 1, 4, 17, 19, 30–200 quadros depois de desenhados): **0 px** de variação. Na 5 a janela pega o traço
  ainda crescendo (igual à rodada 2).
- **Tranco no GPS** (correlação de fase, quadro inteiro, 480p): 0 reversões nas 5 cenas; salto p99 0,07–0,19 px nas cenas 2, 8,
  12, 18; cena 14 (3×) p99 0,43 px, máx 2,3 px em q3593 (o único quadro com correlação sem pico). **Câmera lisa.**
- **Etiquetas HAM/RUS** (caixa vermelha/verde-água com texto branco, quadro a quadro):

  | cena | quadros com as duas | encostadas/sobrepostas | **trocas de lado** (salto de ~94 px em 1 quadro) |
  |---|---|---|---|
  | 2 | 314/329 | 0 | 0 |
  | 8 | 409/424 | 3 (q2028, 2029, 2045) | 3 (q1915, 2005, 2073) |
  | 12 | 252/276 | 9 (encostam 1–2 px, q3187) | 2 (q3167, 3255) |
  | 14 | 326/347 | 9 (q3686–3710) | **7** (q3593, 3655, 3672, 3745, 3768, 3785, 3797) |
  | 18 | 253/253 | 0 | 1 (q5108, ao entrar na curva) |

  Na perseguição (18) o erro da rodada 2 foi corrigido: "HAM" sobre o carro de trás (Ferrari), "RUS" sobre o da frente
  (`q4945_cheio.jpg`). Mas quando os carros andam lado a lado as etiquetas **pulam de um lado para o outro** de um quadro para
  o seguinte (`diag_q3672_seq12.jpg`: q3671 RUS à esquerda, q3672 HAM à esquerda) — é o "pulo" que o Felipe reprova.
- **HUD × OpenF1** (84 valores, 42 quadros, as 5 cenas; t = início + (q − Q0)/60 × fator da SPEC, contra o `car_data` bruto do
  kit): erro médio **0,9 km/h**, p90 2,7, máx 7 — o máx é q3937, já no fade final da cena 14, com a volta de HAM terminada
  (76,95 s > 76,514): o HUD mostra 282 × 275 extrapolado. Fora isso ≤ 6 (frenagem, amostragem de 4 Hz). Bate.
- **Duelos/barras × palavra:** 104 e 1:16.514 entram com o número (sem cartão vazio). Barras da 16 começam a crescer em
  72,13 s ("350" falado em 72,12) e 75,72 s ("347" em 75,70); terminam exatamente em 350,0 e 347,0 na escala.
- **Quadros parados** (diferença média < 0,05): 9b 80 %, 11 82 % (3,6 s seguidos), 15 93 % (2,0 s), 16 87 % (3,1 s).
- **Igual ao v3** (PSNR 108 dB = idêntico): cenas 1, 4, 5, 7, 17 e quase todo o 3, 6, 9a, 19.

### Áudio
Cada SFX foi recriado sozinho com a **mesma linha do filtro** do montador (`filtro_audio.txt`) e posto no tempo dele; os do
barramento sem sidechain (clique/tecla/pop/alerta/sino) conferem com o resíduo mix − voz − trilha (diferença 0,0–0,1 dB).
"Banda" = melhor banda de oitava em que o SFX passa voz+trilha em ±80 ms do pico (> 0 dB: provavelmente audível).

| SFX (palavra) | pico − palavra | SFX − voz RMS | pico SFX − pico voz | banda |
|---|---|---|---|---|
| clique "classificação" | +1 ms | −1,6 dB | +1,8 | +17,5 (11–20 kHz) |
| pop "514" | −38 ms | −0,3 | −6,1 | +4,2 |
| clique "25" | +9 | −10,3 | +6,2 | +18,4 |
| pop "349" | −35 | −2,0 | −3,8 | +10,7 |
| tecla "22" | +1 | −9,2 | +0,8 | +19,0 |
| clique "rápidas" | +8 | −11,2 | +2,0 | +5,3 |
| pop "100%" | 0 | −7,4 | +3,9 | +23,4 |
| clique "30.008" | +3 | −8,4 | +2,4 | +40,8 |
| tecla "6" | +2 | −14,5 | −1,3 | +17,0 |
| cliques "1:16.514" / "1:16.523" | +1 / −1 | (voz parada) / −10,7 | +2,5 / +2,0 | +55,7 / +14,0 |
| pops "350" / "347" | +1 / −2 | −4,3 / −10,1 | −0,8 / +1,4 | +19,1 / +8,3 |
| alerta "não" | −2 | −2,5 | −8,4 | +6,2 |
| clique "frenagens" | −2 | −4,0 | +4,5 | +48,5 |
| impacto fecho "Nove" | −38 | −3,2 | +14,3 | +25,7 |
| **sino "Uma"** | −8 | **−17,5** | **−12,3** | **+13,9 (710–1420 Hz)** |

- **Sino remedido:** pico −16,8 dBFS, RMS −35,7 dBFS; 17,5 dB abaixo da voz em RMS (rodada 2: 33 dB) e o ataque 12 dB abaixo do
  pico da voz, mas 14 dB acima de voz+trilha na banda de 1 kHz. Deve ser **audível, fraco**, por baixo de "Uma pole." (ainda não
  está depois da frase). O "+14 ainda ficava 19 dB abaixo" do produtor é coerente com o −17,5 de agora.
- Cliques/teclas/pops: todos com pico na palavra (−38 a +9 ms) e agora 0–15 dB abaixo da voz em RMS, picos no nível da voz:
  **saíram do enterrado** (eram −23 a −28).
- Impactos/riser/whoosh (com sidechain): o hit do capítulo 1 cai ~0,6 s depois de "setores" (igual às rodadas anteriores).
- **Trilha × voz:** trilha −36,3 dBFS RMS, voz −17,8; margem mediana 22 dB, p10 9,3 dB; 6 % das janelas de fala com margem < 6 dB
  (finais de frase). A trilha não cobre a voz. Último som da trilha 90,0 s. **Loudness do MP4: −14,0 LUFS, −1,4 dBTP, LRA 4,6 LU.**

## Placar (comparado com as rodadas 1 e 2)
| # | cena (id) | s | a 25 | b 15 | c 20 | d 15 | e 15 | f 10 | **nota** | r1 | r2 | Δ r2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | "Nove milésimos" (c8b897f1) | 1,6 | 24 | 13 | 18 | 14 | 7 | 8 | **84** | 84 | 84 | 0 |
| 2 | GPS fim da volta (447ab02a) | 6,2 | 23 | 13 | 17 | 13 | 11 | 7 | **84** | 66 | 79 | +5 |
| 3 | velocidade volta inteira (747ede00) | 5,1 | 23 | 12 | 15 | 14 | 11 | 7 | **82** | 82 | 82 | 0 |
| 4 | 1:16.514 oval (abbcf455) | 4,7 | 25 | 14 | 17 | 14 | 7 | 8 | **85** | 85 | 84 | +1 |
| 5 | +0.009 s (791bf924) | 2,8 | 25 | 14 | 18 | 14 | 6 | 6 | **83** | 82 | 83 | 0 |
| 6 | capítulo 1 (f7de54d4) | 3,3 | 24 | 13 | 19 | 14 | 11 | 7 | **88** | 87 | 88 | 0 |
| 7 | setores (a68a79fb) | 3,4 | 25 | 9 | 17 | 14 | 12 | 7 | **84** | 82 | 83 | +1 |
| 8 | GPS reta → Curva 1 (e0df513b) | 7,8 | 23 | 12 | 16 | 13 | 10 | 8 | **82** | 61 | 80 | +2 |
| 9a | frenagem 900–1350 m (dd4ffd33) | 6,1 | 21 | 13 | 16 | 14 | 11 | 5 | **80** | 81 | 80 | 0 |
| 9b | mínima 104 × 100 (09e13e9a) | 2,7 | 24 | 14 | 18 | 13 | 8 | 5 | **82** | 81 | 80 | +2 |
| 10 | capítulo 2 (c247ab85) | 2,5 | 24 | 13 | 19 | 14 | 10 | 7 | **87** | 86 | 87 | 0 |
| 11 | velocidade S2 (528c1e00) | 5,2 | 22 | 13 | 17 | 13 | 10 | 7 | **82** | 71 | 77 | +5 |
| 12 | GPS saída do grampo (a37e2524) | 5,4 | 22 | 13 | 16 | 13 | 10 | 7 | **81** | 65 | 75 | +6 |
| 13 | duelo S2 (d96a46d3) | 2,5 | 25 | 14 | 19 | 13 | 8 | 7 | **86** | 79 | 84 | +2 |
| 14 | GPS setor 3 3× (d5a93934) | 6,5 | 23 | 14 | 14 | 12 | 12 | 7 | **82** | 64 | 77 | +5 |
| 15 | resultado (fe9cb062) | 4,4 | 25 | 14 | 18 | 13 | 7 | 7 | **84** | 71 | 80 | +4 |
| 16 | speed trap em barras (760ea8f0) | 8,1 | 23 | 14 | 18 | 12 | 9 | 7 | **83** | 65 | 76 | +7 |
| 17 | "Velocidade de reta" (408641ec) | 2,9 | 24 | 14 | 18 | 14 | 6 | 7 | **83** | 83 | 83 | 0 |
| 18 | GPS perseguição (76c5a688) | 5,0 | 23 | 13 | 16 | 13 | 11 | 8 | **84** | 70 | 71 | +13 |
| 19 | fecho (e9aa5677) | 4,5 | 24 | 14 | 18 | 14 | 7 | 6 | **83** | 80 | 82 | +1 |

**Nota global (ponderada pela duração): 83,1 / 100** (rodada 1: 73,8; rodada 2: 79,8; **+3,3**).
Por critério (% do máximo): dados 93 (r2 92) · sincronia 88 (85) · clareza 84 (81) · movimento 88 (88) · **estética/vida 64** (60) ·
**SFX 69** (58).

**Meta (toda cena ≥ 80 e global ≥ 80): ATINGIDA**, mas no limite: 9a com 80 e 12 com 81. Nenhuma cena passou de 88; o teto agora
é estética/vida (64 %) e SFX (69 %).

## O que ainda segura a nota (para a próxima versão, não bloqueia a meta)
1. **Etiquetas que trocam de lado** (cenas 8, 12, 14, 18; 13 trocas, 7 só na 14). Causa provável: `gps.html` decide o lado de
   cada etiqueta quadro a quadro pela posição projetada; com os carros quase lado a lado o sinal inverte e elas saltam ~94 px.
   Correção: lado fixo por cena (ou histerese: só trocar se a outra posição ficar livre por ≥ 0,5 s) e deslizar em vez de saltar.
2. **Três duelos com o mesmo cartão** (9b, 13, 15) e cartões/barras parados 80–93 % do tempo, metade de baixo da tela vazia.
   A troca da 16 por barras foi boa; falta variar mais um (ex.: o resultado final como placar grande ou sobre a pista).
3. **Cena 11:** o rosa cobre o gráfico inteiro, então não destaca nada; as linhas continuam iguais. O número escrito salva a cena.
   Correção: sem faixa (é o setor inteiro) e o número maior; ou mostrar o delta acumulado no setor.
4. **GPS:** carros fundidos quando colados (q418, q3187); Ferrari quase preta na perseguição; placa "1" sobre o rodapé (q2093);
   HUD extrapolado depois da bandeirada (q3937). Mundo ainda ralo nas cenas 8 e 12 (sem arquibancada).
5. **SFX demais (ver abaixo).**

## Regras do Felipe
- **Fundo claro:** todas as cenas em fundo claro (bege/cinza claro, pista cinza), sem tela escura. ✔
- **Texto sem animação exagerada:** cartões entram com fade curto, números não rolam, rótulos secos. ✔
- **Variedade de SFX:** 26 eventos, cada um com um arquivo diferente (7 cliques, 2 teclas, 5 pops, 1 alerta, 4 impactos, 2 risers,
  4 whooshes, 1 sino): variados. ✔
- **"Goteira" / ~9 efeitos em 2 min 20 s:** **contra a regra.** Agrupando eventos a menos de 1,5 s, são 17 momentos em 90,5 s —
  equivale a ~26 em 2 min 20 s (a regra dá ~6 para 90 s). Entre 47 e 76 s há 9 sons curtos em 29 s (um a cada ~3 s:
  22, rápidas, 100%, 30.008, 6, 1:16.514, 1:16.523, 350, 347) — exatamente a goteira que a regra descreve. Todos estão numa
  palavra-chave com algo mudando na tela (bom), mas o conjunto não destaca mais nada. Minha opinião: manter ~9–10 momentos
  (impacto de abertura, capítulos 1 e 2, "349", "22", "30.008", "350", "não", fecho) e cortar "classificação", "rápidas",
  "100%", "6", "1:16.523", "347", "frenagens" e o whoosh do zoom em 81 s. Não tirei pontos de (f) além do que já estava,
  porque a rodada pediu audibilidade; mas é o que eu mudaria antes de publicar.

## O que um ouvido humano precisa checar
1. **Sino do fecho** (86,97 s): se aparece sob "Uma pole." ou some; se o timbre combina.
2. **Goteira entre 47 e 76 s:** se os 9 cliques/pops seguidos cansam.
3. **Cliques/pops agora no nível da voz** (pico SFX ≈ pico voz): se algum ficou alto demais ou "seco" (ex.: "1:16.514", +2,5 dB
   sobre a voz, num silêncio; "clique classificação" com energia em 11–20 kHz pode soar agudo/estalado).
4. **Hit do capítulo 1** ~0,6 s depois de "setores": se parece atrasado.
5. **Trilha a −36 dBFS RMS** sob a voz: se é audível/agradável ou só ruído de fundo.
6. Tudo isso com a **voz definitiva** (a provisória muda tempos e mascaramento).

## O que está resolvido e não deve ser mexido
Ovais estáveis (0 px), câmera de GPS sem vai-e-volta nem tranco, HUD fiel ao OpenF1 (0,9 km/h), etiqueta da perseguição no carro
certo, números e barras na palavra, cartões sem tempo vazio no início, cliques/pops audíveis, trilha sob a voz, −14 LUFS.
