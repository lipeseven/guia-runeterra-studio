# Placar independente — "Nove milésimos" (rodada 1, 2026-11-14)

Avaliador independente (não produziu o vídeo). Vídeo: `F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v2.mp4`
(1920×1080, 60 q/s, 5.429 quadros, 90,5 s, 19 cenas, **voz Fish provisória**). Dados por cena em `placar_rodada1.json`.

## Como foi avaliado
- Por cena: folha de 8 quadros (início+2, 6 no meio, fim−2) e folha de 12 quadros **consecutivos** a 60 q/s no meio da
  cena; extras de 12 consecutivos na curva da cena 8, no estádio da cena 14 e ampliados (carros, ovais). Tudo em
  `F1/horizontal/testes/placar/rodada1/` (`cNN_<id>_8q.jpg`, `cNN_<id>_seq12*.jpg`, mais 5 quadros de evidência em resolução cheia).
- Medido por script (não só olho): caixa do traço vermelho dos ovais/sublinhados em 30 quadros seguidos (cenas 4, 13, 19:
  **0 px de variação**, não pulam); movimento global entre quadros por correlação de fase nas 5 cenas de GPS (nenhum
  tranco nem vai-e-volta: 0–1 reversão, p99 do salto ≤ 0,6 px a 480p); HUD da cena 8 lido a cada 8 quadros; nível RMS/pico
  de cada SFX (`sfx.wav`) contra a voz (`limpa.wav`) na janela do evento.
- Rubrica: (a) dados 25 · (b) sincronia/ritmo 15 · (c) clareza 20 · (d) movimento 15 · (e) estética/vida 15 · (f) SFX/transição 10.

## O que NÃO deu para avaliar
- **Não ouvi o vídeo.** O critério (f) e parte do (b) saíram de medidas (tempo de cada evento × palavra, RMS/pico × voz),
  não do ouvido: timbre, gosto e equilíbrio real ficam para o Felipe. A voz é a guia Fish; com a voz dele os tempos mudam.
- Não assisti corrido em tempo real; a suavidade vem de quadros consecutivos + medida de movimento global.
- Dados: conferi o que está na tela contra o roteiro, o relatório e a soma dos setores (fecha ao milésimo). Não reconsultei
  o OpenF1 (velocidades do HUD ponto a ponto não foram reconferidas na API).

## Placar
| # | cena (id) | s | a 25 | b 15 | c 20 | d 15 | e 15 | f 10 | **nota** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | "Nove milésimos" sublinhado (c8b897f1) | 1,6 | 24 | 13 | 18 | 14 | 7 | 8 | **84** |
| 2 | GPS fim da volta (447ab02a) | 6,2 | 20 | 10 | 12 | 13 | 5 | 6 | **66** |
| 3 | velocidade volta inteira (747ede00) | 5,1 | 23 | 12 | 15 | 14 | 11 | 7 | **82** |
| 4 | 1:16.514 oval (abbcf455) | 4,7 | 25 | 14 | 17 | 14 | 7 | 8 | **85** |
| 5 | +0,009 s sublinhado (791bf924) | 2,8 | 24 | 14 | 18 | 14 | 6 | 6 | **82** |
| 6 | capítulo 1 (f7de54d4) | 3,3 | 24 | 13 | 19 | 14 | 11 | 6 | **87** |
| 7 | setores (a68a79fb) | 3,4 | 25 | 9 | 17 | 14 | 12 | 5 | **82** |
| 8 | GPS reta → Curva 1 (e0df513b) | 7,8 | 21 | 7 | 11 | 10 | 5 | 7 | **61** |
| 9 | telemetria 850–1450 m (dd4ffd33) | 8,7 | 19 | 13 | 16 | 14 | 12 | 7 | **81** |
| 10 | capítulo 2 (c247ab85) | 2,5 | 24 | 13 | 19 | 14 | 10 | 6 | **86** |
| 11 | velocidade S2 + minimapa (528c1e00) | 5,2 | 17 | 12 | 12 | 14 | 10 | 6 | **71** |
| 12 | GPS saída do grampo (a37e2524) | 5,4 | 19 | 10 | 12 | 13 | 5 | 6 | **65** |
| 13 | 30.008 oval (d96a46d3) | 2,5 | 23 | 13 | 15 | 14 | 6 | 8 | **79** |
| 14 | GPS setor 3 2× (d5a93934) | 4,6 | 19 | 9 | 12 | 13 | 5 | 6 | **64** |
| 15 | foco 1:16.514 (f6d5a7f0) | 6,3 | 25 | 7 | 14 | 13 | 6 | 6 | **71** |
| 16 | velocidade "speed trap" (760ea8f0) | 8,1 | 12 | 10 | 13 | 14 | 10 | 6 | **65** |
| 17 | "Velocidade de reta" riscado (408641ec) | 2,9 | 24 | 14 | 18 | 14 | 6 | 7 | **83** |
| 18 | GPS perseguição câmera lenta (76c5a688) | 5,0 | 22 | 11 | 11 | 13 | 6 | 7 | **70** |
| 19 | fecho "Nove milésimos." (e9aa5677) | 4,5 | 24 | 14 | 18 | 14 | 7 | 3 | **80** |

**Nota global (média ponderada pela duração): 73,8 / 100.**
Por critério (% do máximo, ponderado): dados 84 · sincronia 73 · clareza 72 · movimento 89 · **estética/vida 52** · **SFX 63**.

Leitura: o que o Felipe já reclamou antes foi resolvido (carros não vão e voltam, não somem, não entram no chão; ovais
não pulam; GPS real com rastro por equipe). O vídeo perde pontos em outras coisas: o mundo do GPS é vazio e parado,
duas afirmações do roteiro aparecem na tela com dados que não batem com o que é dito ou que não estão lá, e o som
tem dois buracos (sino inaudível e longos trechos sem nenhum SFX).

## Os 5 maiores problemas
1. **Cena 16: o gráfico contradiz a fala (dados).** A fala diz "Russell 350, Hamilton 347 no speed trap"; o gráfico
   (car_data) mostra as duas linhas em ~350 km/h e nenhuma marca do speed trap (q4590, `c16_speedtrap_q4590.jpg`).
   "RUS sempre um pouco acima" (objetivo da SPEC) também não aparece: as linhas se cruzam. Causa: o kit de gráficos não
   tem o `st_speed` do `/laps` (lacuna já citada em `app/servidor/openf1.py:20`) e a SPEC escolheu "velocidade" para um fato
   que não está na série. Correção: tipo/elemento "speed trap" em `kit/graficos` (dois números ou barras com o `st_speed`
   e a posição da armadilha marcada no eixo), ou trocar a cena por texto/anotação com 350 × 347.
2. **Cenas de GPS (2, 8, 12, 14, 18 = 29 s, 32 % do vídeo) sem vida e sem sensação de velocidade.** Plano cinza, pista
   cinza lisa, nada em volta; na reta a 349 km/h o fundo anda ~0,1 px por quadro (medido) e o carro parece parado
   (cena 8, q1694–q1855). Contra `F1/docs/regras_de_direcao.md` (autódromo na cidade, arquibancadas, câmera transita) e a
   memória de fundo claro com cor. A cena 14 promete "o estádio" e não há estádio. Causa: `montador/hyperframes/gps.html`
   (mundo plano sem textura) e câmera `alta` fixa no carro. Correção: zebras/linhas tracejadas/marcas de distância na pista
   (dão velocidade), contorno do estádio e arquibancadas como formas simples, número de curva, minimapa com o ponto.
3. **Carros fundidos um no outro (cenas 2, 8, 12, 14, 18).** Com o GPS real os dois modelos se interpenetram (asa da
   Ferrari dentro da Mercedes, `c02_carros_sobrepostos_q311.jpg`; cena 18 q5002–q5013): vira um borrão vermelho-preto e não
   dá para ver quem está na frente nem o "freou 22 m depois". O Felipe aceita um carro sobre o outro, mas precisa ler.
   Correção em `kit/gps`: o carro de trás como fantasma (transparência ~50 %) ou contorno na cor da equipe, e uma
   etiqueta HAM/RUS presa a cada carro.
4. **Números ditos que não ficam na tela no tempo da fala (sincronia).** Cena 8: o par 349 × 345 aparece no HUD só por
   ~10 quadros (q1834), 0,2 s antes do "349"; quando a fala diz "345" (32,9 s) o HUD já está em ~150 (`c08_hud_q1770-1922.jpg`).
   Cena 9: "104 contra 100" não aparece (gráfico sem velocidade) e os "22 metros" não são marcados. Cena 15: o desfoque
   cobre "contra 1:16.523" em 66,4 s, quase 1 s ANTES de a fala dizer esse número (67,34 s). Correção: HUD com "segurar
   valor" na palavra-âncora (`montador/receitas.py` `_gps`/`_nota_gps` → parâmetro `marcar: [{i, rotulo}]`); na
   telemetria, cota "22 m" entre o início dos freios e os mínimos 104/100 na Curva 1; no foco (`receitas.py:222`), entrar
   depois da última palavra do texto que vai ser desfocado (ou a SPEC usar i=184).
5. **SFX: sino final inaudível e cortado; fecho e capítulos competem com a voz; 7 cenas seguidas sem som.** O sino
   (`sino_suave`, 2,48 s) começa em 89,88 s e o vídeo acaba em 90,48 s: toca 0,6 s, pico −39 dBFS — na prática não existe
   (`montador/mixagem.py:125` corta em `end_sample=n`). O impacto do fecho (85,96 s) fica 1,7 dB ACIMA da voz em RMS na
   janela (−15,1 × −16,8 dB) e os capítulos empilham whoosh + riser + impacto a 2–3 dB da voz enquanto ela fala ("setores",
   "segundo"). O riser do capítulo 2 começa em 41,3 s, embaixo de "contra 100 de Russell". Entre 44 s e 56 s e entre
   66 s e 79 s não há nenhum SFX; o gráfico de setores (o mais elogiável) entra sem clique. Correção: estender o vídeo/
   cauda até o fim do sino ou ancorar o sino 2 s antes; ducking da voz no `mixagem.py` (sidechain já existe:
   `[vozsc]` vai para `anullsink`, não é usado); cliques/pops nos gráficos quando cada barra/linha entra.

## Defeitos por cena (resumo; detalhe no JSON)
- **1** (84): só texto em fundo claro, sem vida (e). Ok no resto; impacto no "Nove".
- **2** (66): narração fala de nomes/GP e a cena mostra o fim da volta sem chegar à linha (objetivo "chegando juntos à linha"
  não cumprido); carros fundidos; mundo vazio; rodapé mistura "Mexico City … classificação".
- **3** (82): correto e limpo, mas as duas linhas se sobrepõem a volta toda: "como a diferença foi construída" não se vê;
  subtítulo "76,514" (formato diferente do "1:16.514" das outras cenas); rodapé em inglês "Qualifying Mexico City 2026".
- **4** (85): oval no "514" no tempo certo, estável; o começo do traço passa por cima do "1:" (q1053).
- **5** (82): bom; layout idêntico ao da cena 4 logo em seguida (monótono); "+0,009 s" com vírgula × "1:16.514" com ponto.
- **6** (87): melhor cena de texto (traçado desenhado, PARTE 01). Três sons empilhados sob a fala.
- **7** (82): números todos certos (somas fecham), mas 3,4 s para um gráfico denso: S2, S3 e Volta entram antes de serem
  ditos e o gráfico completo fica ~1 s na tela antes do zoom; eixo ±0,06 s deixa as barras pequenas; sem clique.
- **8** (61): pior cena. Reta parada (sem sensação de 349 km/h), 349 × 345 só por um instante, carros fundidos, mundo vazio,
  a frenagem 22 m depois não é mostrada aqui.
- **9** (81): telemetria correta (freio RUS ~1.050 m × HAM ~1.070 m ≈ 20 m) e bem ritmada; falta a velocidade 104 × 100 e a
  cota de 22 m; a distância vem da integral da velocidade (erro conhecido, `kit/graficos/py/preparar.py:191`).
- **10** (86): igual à 6; riser começa 2,8 s antes, ainda na cena 9.
- **11** (71): "Russell recuperou 22 milésimos nas curvas rápidas" sem nada que mostre onde; minimapa cinza SEM destaque do
  setor 2 nem ponto (`c11_minimapa_sem_destaque_q3054.jpg`); linhas sobrepostas.
- **12** (65): HUD mostra HAM saindo mais rápido (107 × 101), mas "acelerar a 100 %" não aparece (sem acelerador) e
  "Russell foi mais rápido no setor" também não. Mundo vazio, carros fundidos.
- **13** (79): "30.008 contra 30.030" sem dizer quem é quem (falta "Russell"/"Hamilton"); traço do oval sobre o "3".
- **14** (64): "o estádio" não existe na cena; 6 ms não aparece; faixa fina da pista ao fundo no topo do quadro parece
  defeito (q3744); de resto suave a 2×.
- **15** (71): desfoca o número no momento em que é dito; caixa clara recortada em volta do "1:16.514" sobre véu cinza
  (`c15_veu_e_borrao_q4110.jpg`); 6,3 s parados; só um clique de 45 ms para "o resultado final".
- **16** (65): ver problema 1. Além disso é o 3º gráfico de velocidade igual (cenas 3, 11, 16) e fica 3,5 s parado depois de
  desenhado. Curiosamente mostra bem o 349 × 344 da cena 8 (RUS ~350 × HAM ~345 em 960–1.020 m).
- **17** (83): riscado no "não", certo; só texto.
- **18** (70): HUD confirma RUS freando antes (HAM 309 × RUS 284 em q5002): boa escolha; mas a Ferrari "atravessa" a
  Mercedes, a borda do plano aparece no horizonte e o mundo é vazio.
- **19** (80): visual certo; o impacto passa a voz e o sino não se ouve (ver problema 5).

## Observações para quem for corrigir
- O que o Felipe tinha reprovado nos testes de motores e que **está resolvido** aqui (não mexer): vai-e-volta, carro sumindo,
  carro no chão, oval pulando (0 px), texto picotado/cortado, transições.
- Quatro cenas só de texto (1, 4, 5, 13) + 17 e 19 = 6 de 19 no mesmo layout (texto preto centralizado em fundo claro).
  Variar (número dentro de cartão com foto/cor da equipe, comparação lado a lado HAM × RUS) ajuda (e) e a regra de
  não parecer produção em massa.
- Nenhuma imagem real e nenhuma trilha (o relatório já diz); o vídeo depende só de gráfico, texto e GPS cinza.
