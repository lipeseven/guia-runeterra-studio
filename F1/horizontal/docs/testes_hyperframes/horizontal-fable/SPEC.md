# SPEC — Ferrari SF-26, "O caminho do ar" (Explicando F1, horizontal)

Etapa 2 do BRIEF. Escrito em 2026-11-12. Serve de contrato para a etapa 3 (Blender) e a etapa 4 (HyperFrames).

## 1. Resumo técnico

| Item | Valor |
|---|---|
| Saída | 1920x1080, 30 fps, `video\ferrari_fable.mp4` |
| Duração | 1260 quadros = 42,0 s. Narração `narracao.mp3` = 40,05 s (última palavra termina em 39,70 s). De 39,70 a 42,0 s: 3D em movimento, sem texto, com a direita livre para a tela final |
| Âncora | Tudo é ancorado em **palavra** de `transcricao_palavras.json` (116 palavras, índices w0 a w115). Quadro = `round(inicio × 30)`. Os quadros desta SPEC são derivados; se a narração mudar, recalcular pelos índices |
| Notação | `w39 "gira"` = início da palavra 39. `w39f` = fim da palavra. `+6q` = 6 quadros depois |
| Trilha | Nenhuma foi fornecida. Sem som de motor (regra do canal) |

## 2. Linha de história escolhida

**"O caminho do ar".** A câmera percorre o carro da frente para trás, na mesma ordem em que o ar passa por ele: bate na asa dianteira, atravessa a asa traseira aberta e sai junto ao escapamento, onde a mini asa ainda tira downforce. No meio, a consequência: velocidade final, os dois pilotos e as duas retas de Interlagos.

Por que esta e não as outras:
- A fala já vem nessa ordem (frente, traseira, reta, pilotos, pista, escapamento). A câmera só precisa seguir.
- Dá um fio visual único: **uma linha vermelha de ar** que aparece na asa traseira (C06), vira o traço das retas no mapa (C09) e fecha nas setas de downforce (C11).
- Descartadas: "lista de 4 novidades" (vira catálogo, sem tensão) e "o carro feito para Interlagos" (a pista só aparece em 1 das 8 frases).

O que o espectador leva: sabe apontar no carro as 4 peças citadas e entende por que a Ferrari anda nas duas retas de Interlagos.

## 3. Visual

| Elemento | Definição |
|---|---|
| Fundo base (modo claro) | papel `#EDEAE6`, grade de pontos `#141414` a 6% (passo 48 px). Fundo claro é a base do canal |
| Tinta | `#141414`. Cinza de apoio `#8C8A86` |
| **Cor de destaque (única)** | **vermelho Ferrari `#ED1131`** (é o `cor_equipe` do JSON de telemetria). Nenhuma outra cor entra no vídeo |
| Regra do vermelho | No modo claro, **um único elemento vermelho por tela** (traço à mão, linha de ar, reta acesa, número). A palavra gigante é em tinta preta, porque vermelho atrás de carro vermelho some |
| Modo cor cheia | fundo `#ED1131` liso, palavra gigante branca, fotos P&B. Só na cena dos pilotos (C08), como "virada" |
| Palavra gigante | League Gothic (ou Anton), caixa-alta, corpo de 440 px (41% da altura), tracking 0, **atrás do carro** (camada entre o fundo e o plano herói com alfa). 1 a 3 palavras, nunca a frase |
| Decodificação | 0,52 letra por quadro, ordem sorteada com semente fixa, 2 a 4 letras-isca em cinza trocadas em 2 a 4 q. Sai ao contrário em 12 q. Entra 0 a 1 s depois da palavra falada |
| Microlegenda e rótulo | Inter 800, 30 px, caixa-alta, tracking +4%, **seca** (entra num quadro). Linha-guia de 2 px com ponto quadrado de 10 px na peça |
| Anotação à mão | Caveat 700, 64 px. Traço de 6 px a 105 px por quadro; letra a 52 px por quadro. Comenta a fala, não repete |
| Números | League Gothic 260 px colados no objeto. Contador troca seco a cada 2 q |
| Pessoas | foto P&B em cartão de papel inclinado, com sombra. Nunca rosto em 3D |
| Fontes | copiar de `comparacao\video\assets\fonts\` para `assets\fonts\` (não baixar em tempo de render) |

## 4. Transições (medidas em quadros, 30 fps)

| Tipo | Medida |
|---|---|
| `corte` | 0 q. A cena nova já começa com a câmera em movimento (deriva de 2 a 6% em 25 q) |
| `empurrar` | a antiga sai em 10 q (ease-in cúbico), borrão horizontal até 8% da largura, texto esticado 1,2x em X. A nova começa 9 q depois do início da saída e entra em 15 q (ease-out), sem rebote. Fundo parado |
| `contínua` | mesmo clipe do Blender, sem corte. A câmera viaja de uma peça à outra |
| `cor` | 8 q enchendo de vermelho + 6 q vazios + 8 q de entrada do conteúdo novo |
| `cortina` | de baixo para cima, 15 q, ease-out, borda reta com feather de 3% da altura |
| `glitch` | 5 q, só fatias horizontais, sem cor: q1-2 fatias deslocadas ±7% da largura, q3 ruído no quadro todo, q5 limpo |

Mistura do vídeo (11 trocas de cena): 3 cortes, 3 empurrões, 3 contínuas, 1 cor, 1 cortina, 1 glitch (o glitch conta junto com um corte). Mais 9 entradas de palavra por decodificação. Bate com a receita "em 16 momentos".

## 5. Tabela de cenas

Colunas: âncora de início e fim (palavra e quadro), o que aparece, camada (H = plano herói do Blender; MG = motion graphics no HyperFrames), transição de entrada.

| id | Início | Fim | Fala | Herói 3D | Motion graphics (com âncora) | Entrada |
|---|---|---|---|---|---|---|
| **C01** gancho | w0 "O" · q0 | w10 "mais" · q98 | "O novo carro da Ferrari de 2026 está um pouco" | **H01**: frente 3/4 baixa, push-in com órbita | w4 "Ferrari" q24: rótulo seco `FERRARI` com linha-guia no bico. w6 "2026" q43: palavra gigante **`2026`** decodifica (8 q) atrás do carro. w8 "um" q82: `2026` sai ao contrário (12 q) | abre direto, câmera já andando |
| **C02** branco | w10 "mais" · q98 | w15f "costume." · q141 | "mais branco do que de costume." | **H02**: macro lateral na área branca, brilho varrendo | w11 "branco" q107: palavra gigante **`BRANCO`** (contorno preto de 6 px, miolo branco) decodifica em 12 q, ocupando a metade de baixo. w14 "de" q128: círculo vermelho à mão na área branca + letra à mão `novo!` (único vermelho da tela) | `corte` em q98 |
| **C03** asa dianteira | w16 "A" · q156 | w24f "agressivo" · q253 | "A asa dianteira também apresenta um perfil mais agressivo" | **H03** (1ª parte): rasante ao chão, deslize lateral na asa | w17 "asa" q161: rótulo seco `ASA DIANTEIRA` com linha-guia. w22 "perfil" q215: traço vermelho à mão contorna o perfil do flap de cima (traçado 2D da peça). w24 "agressivo" q233: palavra gigante **`AGRESSIVO`** decodifica (17 q) atrás da asa | `empurrar` para a esquerda: saída q141 a q151, entrada q150 a q165 |
| **C04** comparação | w25 "em" · q253 | w30f "anteriores." · q310 | "em comparação com os carros anteriores." | **H03** (2ª parte): a câmera sobe para vista alta de frente; surge o "fantasma" cinza da asa antiga | w25 q253: `AGRESSIVO` sai ao contrário (12 q). w26 "comparação" q257: tela divide com fio vertical de 2 px (desenhado em 10 q); etiquetas secas `ANTES` (cinza) e `2026` (tinta). w29 "carros" q283: seta dupla vermelha à mão entre os dois perfis + letra à mão `olha o ângulo` | `contínua` (mesmo clipe H03) |
| **C05** asa traseira | w31 "A" · q319 | w41f "rapidamente." · q428 | "A asa traseira dispõe de um mecanismo que gira ela rapidamente." | **H04** (1ª parte): traseira 3/4 alta, push-in na asa; **a aba de cima gira e abre em q384 a q392** (8 q) | w32 "asa" q324: rótulo seco `ASA TRASEIRA`. w37 "mecanismo" q363: círculo à mão no pivô + seta curva vermelha no sentido do giro. w39 "gira" q384: palavra gigante **`GIRA`** decodifica (8 q) atrás da asa; etiqueta de estado troca seca `FECHADA` → `ABERTA` em q392. w41 "rapidamente" q404: a aba fecha e abre de novo (2x em 20 q) para mostrar a rapidez | `corte` em q319 |
| **C06** ar | w42 "deixando" · q435 | w48f "retas," · q506 | "deixando passar muito ar durante as retas," | **H04** (2ª parte): a câmera desce para trás do carro, no eixo; **linhas de ar vermelhas** atravessam a fenda aberta (feitas no Blender, para o carro tapar as linhas) | w42 q435: `GIRA` sai (12 q). w44 "muito" q456: palavra gigante **`AR`** entra seca atrás do carro, no mesmo quadro em que a 1ª linha cruza a asa. w46 "durante" q478: letra à mão preta `passa direto` + seta. w48 "retas" q493: rótulo seco `NAS RETAS` | `contínua` (mesmo clipe H04) |
| **C07** velocidade | w49 "dando" · q511 | w54f "considerável." · q579 | "dando uma velocidade final bem considerável." | **H05**: tracking lateral em velocidade (chão borrado, rodas girando, asa aberta); em q566 o carro acelera e **sai do quadro pela direita** | w51 "velocidade" q521: palavra gigante **`VELOCIDADE`** decodifica (19 q) atrás do carro. w52 "final" q533: `FINAL` entra seco abaixo, em vermelho, sublinhado à mão. w54 "considerável" q557: `VELOCIDADE FINAL` estica 1,2x e borra junto com a saída do carro (q566 a q579) | `empurrar` para a direita: saída q503 a q513, entrada q512 a q527 |
| **C08** pilotos | w55 "Vamos" · q589 | w71f "escuderia." · q745 | "Vamos ver como Charles Leclerc vai trabalhar com Lewis Hamilton para levar o título para a escuderia." | nenhum (respiro do 3D; modo cor cheia) | w58 "Charles" q610: cartão P&B do Leclerc entra da esquerda (15 q, ease-out, giro de -12° a -4°); w59 "Leclerc" q620: tarja de pincel preta com `CHARLES LECLERC` seco. w61 "trabalhar" q644: `+` à mão, preto, entre os cartões. w63 "Lewis" q662: cartão do Hamilton entra da direita (+4°); w64 "Hamilton" q671: tarja `LEWIS HAMILTON`. w68 "título" q709: palavra gigante branca **`TÍTULO`** decodifica (12 q) atrás dos cartões. w71 "escuderia" q730: os cartões encostam um no outro (8 q) e um traço à mão sublinha os dois nomes | `cor`: vermelho enche em q575 a q583, vazio q583 a q589 |
| **C09** Interlagos | w72 "Em" · q754 | w90f "final." · q934 | "Em Interlagos, a Ferrari terá vantagem na reta dos boxes e na reta oposta, por conta da velocidade final." | **H06**: maquete clara de Interlagos vista de cima em diagonal, com foco seletivo; as duas retas acendem em vermelho | w73 "Interlagos" q761: palavra gigante **`INTERLAGOS`** decodifica (19 q) no alto. w77 "vantagem" q806: `INTERLAGOS` sai (12 q). w79 "reta" q826: 1ª reta acende (traço cresce em 20 q) + rótulo `RETA DOS BOXES`; **contador** sobe de 156 até **334 km/h** em q826 a q853. w84 "reta" q865: 2ª reta acende + rótulo `RETA OPOSTA`; contador recomeça em 188 e vai a **331 km/h** em q865 a q889. w89 "velocidade" q908: **gráfico de velocidade da volta** se desenha na faixa de baixo (20 q), com os dois picos em vermelho | `cortina` de baixo para cima, q741 a q756, cor papel |
| **C10** escapamento | w91 "Agora," · q945 | w105f "carro." · q1095 | "Agora, vamos ver os detalhes incríveis que a Ferrari deixou próximo ao escapamento do carro." | **H07**: viagem contínua pelo flanco, da lateral até o escapamento, com troca de foco | w95 "detalhes" q983: palavra gigante **`DETALHES`** decodifica (15 q) atrás do carro. w96 "incríveis" q998: letra à mão vermelha `olha isso` + seta na direção da viagem. w99 "Ferrari" q1025: `DETALHES` sai (12 q). w103 "escapamento" q1064: rótulo seco `ESCAPAMENTO` com linha-guia presa à peça (posição vinda de `h07_pontos.json`) | `glitch` de 5 q, q942 a q947 |
| **C11** mini asa | w106 "Tem" · q1103 | w115f "carro" · q1191 | "Tem uma mini asa que ajuda no downforce do carro" | **H08**: macro no escapamento; o foco passa do escapamento para a mini asa em q1114 a q1127 | w108 "mini" q1114: círculo à mão preto em volta da mini asa (acompanha o foco). w109 "asa" q1127: rótulo seco `MINI ASA`. w113 "downforce" q1160: palavra gigante **`DOWNFORCE`** decodifica (17 q) atrás da peça; em q1166, 3 setas vermelhas à mão apontam para baixo sobre a mini asa (uma a cada 4 q) | `corte` em q1103 |
| **C12** fecho | w115f · q1191 | q1260 | (sem fala) | **H09**: traseira 3/4, câmera recua em órbita lenta; carro no terço esquerdo | q1191: `DOWNFORCE` e setas somem no empurrão. Nenhum texto. Retângulo livre à direita (x de 1080 a 1840, y de 180 a 900) | `empurrar` para a direita: saída q1183 a q1193, entrada q1192 a q1207 |

### Mudanças de tela por frase

| Frase | Palavras | Mudanças (o que entra de novo) | Total |
|---|---|---|---|
| 1 | w0–w15 | plano H01, rótulo, `2026`, corte para H02, `BRANCO`, círculo à mão | 6 |
| 2 | w16–w30 | empurrão para H03, rótulo, contorno vermelho, `AGRESSIVO`, subida com fantasma, divisão `ANTES`/`2026`, seta à mão | 7 |
| 3 | w31–w41 | corte para H04, rótulo, círculo e seta, giro da aba com `GIRA`, abre e fecha 2x | 5 |
| 4 | w42–w54 | linhas de ar com `AR`, letra à mão, empurrão para H05, `VELOCIDADE`, `FINAL`, saída do carro | 6 |
| 5 | w55–w71 | mergulho em vermelho, cartão 1 com nome, `+`, cartão 2 com nome, `TÍTULO`, encosto dos cartões | 6 |
| 6 | w72–w90 | cortina para a maquete, `INTERLAGOS`, reta 1 com contador, reta 2 com contador, gráfico | 5 |
| 7 | w91–w105 | glitch para H07, `DETALHES`, letra à mão, rótulo do escapamento | 4 |
| 8 | w106–w115 | corte para H08, troca de foco com círculo, rótulo, `DOWNFORCE` com setas | 4 |

Intervalo médio entre mudanças: cerca de 0,95 s (43 mudanças em 40 s). A meta da Formula Addict é algo novo a cada 2 a 3 s; aqui ficamos mais densos de propósito, por ser um vídeo curto.

## 6. Dados reais usados (cena C09)

Fonte: `dados\telemetria_interlagos.json` (API OpenF1, classificação do GP de São Paulo de 2025, volta 15 do Leclerc, 1:09.801; 425 pontos, um a cada 10 m). Valores conferidos no JSON nesta etapa:

| Trecho | Distância no JSON | Velocidade do Leclerc | Tempo no trecho | Hamilton (mesmo trecho) |
|---|---|---|---|---|
| Reta dos boxes (saída da Junção até a freada do S do Senna) | 3260 m → 4240 m, e segue de 0 a 220 m | 155,8 → **334,0 km/h** na linha (pico de 335,9 aos 200 m; radar 334) | 12,71 s até a linha | pico de 339,8 km/h (radar 338) |
| Reta oposta (saída da curva 3 até a freada da curva 4) | 490 m → 1260 m | 187,9 → **330,7 km/h** aos 1250 m | 9,88 s | pico de 329,0 km/h |

Como usar na tela:
- **Contador 1:** segue os valores de `vel[326..424]` comprimidos em 27 q; para em `334 KM/H`.
- **Contador 2:** segue `vel[49..125]` comprimidos em 24 q; para em `331 KM/H` (330,7 arredondado).
- **Gráfico:** velocidade por distância da volta inteira (425 pontos), em faixa de 1680x230 px na base. O eixo começa em 3260 m e dá a volta (`x = (dist − 3260) mod 4245`), para a reta dos boxes ficar inteira à esquerda e a reta oposta logo depois. Linha cinza de 3 px; os dois trechos acima em vermelho com área preenchida a 20%. Sem eixos numerados; só duas marcas secas `334` e `331` nos picos.
- **Mapa:** no plano H06 as retas são as do `alinhamento_interlagos.json` (`linha`, um ponto a cada ~3,6 m). Converter por fração da volta: boxes = frações 0,768 → 1,0 e 0 → 0,052; oposta = frações 0,115 → 0,297. Conferir a olho contra `tracado.x/y` do JSON (giro de 258°).
- **Selo de fonte** obrigatório, seco, 22 px, canto inferior direito: `CLASSIFICAÇÃO 2025 · LECLERC · DADOS OPENF1`.

Avisos sobre estes números:
1. São do carro de **2025** (SF-25). A fala é sobre o carro de 2026. O selo de fonte deixa isso claro na tela. O arquivo de 2026 (`telemetria_interlagos_2026.json`) não foi usado: os tempos são ~18 s mais lentos (parece chuva) e o clima não foi conferido.
2. A regra do canal diz "números na tela só os que a fala diz". Aqui o BRIEF pede gráfico e contador com dado real quando a fala cita velocidade; vale o BRIEF. Se o Felipe preferir a regra antiga, o contador sai e ficam só o traço das retas e o gráfico sem número.
3. Os dados mostram **onde** se atinge a velocidade final, não provam vantagem da Ferrari sobre outras equipes. Nenhum texto na tela afirma isso.

## 7. Planos herói do Blender (9 clipes)

Comum a todos: 1920x1080, 30 fps, EEVEE (Cycles baixo só se o reflexo ficar pobre), motion blur ligado, estúdio claro `#EDEAE6` com piso levemente reflexivo, softbox grande de cima à esquerda (chave), contorno frio por trás, sem HDRI visível. 6 q de sobra antes e depois de cada clipe para as transições. Coleção `FABLE_HORIZONTAL`; modelos derivados em `assets\modelos\`.

Planos "alfa": a palavra gigante passa **atrás** do carro, então o carro sai com fundo transparente (sombra de contato no alfa e reflexo falso: carro espelhado sob o piso, 15% de opacidade, borrado). Entregar `.webm` (VP9 com alfa) e guardar a sequência PNG em `assets\seq\hNN\`; a etapa 4 testa qual dos dois o HyperFrames toca sem pular quadro.

| id | Cena | Quadros (duração) | Câmera | Luz | Profundidade de campo | Peça em destaque | Arquivo em `assets\` |
|---|---|---|---|---|---|---|---|
| **H01** | C01 | q0–q104 (105 q + 6) | 85 mm, altura de 0,45 m, frente 3/4. Push-in de 12% com órbita de 12° para a direita, ease-out | chave suave + contorno marcando o bico e o halo | f/4, foco no bico; o fundo do carro cai levemente | carro inteiro, pintura | `h01_abertura.webm` (alfa) |
| **H02** | C02 | q98–q147 (50 q + 12) | 100 mm macro, deslize lateral de 0,15 da largura | faixa de luz (softbox estreito) varrendo a superfície ao longo do plano | f/2,8, foco na área branca | **partes brancas** (material `sf25_carbon1_white` e o branco de `sf25_paints`; conferir no modelo onde ficam) | `h02_branco.mp4` |
| **H03** | C03 + C04 | q150–q316 (167 q + 12) | 35 mm. 1ª parte (até q253): rasante a 0,12 m do chão, deslize da direita para a esquerda ao longo da asa. 2ª parte (q253–q290): sobe em arco para vista alta de frente e segura com deriva de 3% | chave rasante para desenhar cada elemento da asa; reflexo no piso | f/2,0 na 1ª parte (foco na aleta da ponta); f/5,6 na 2ª | **asa dianteira**. Na 2ª parte, "fantasma" cinza fosco semitransparente da asa antiga ao lado (peça `FRONT_WING` do `ferrari_sf26_v2.glb`, que é um SF90 de 2019), entrando em q257–q272 | `h03_asa_dianteira.webm` (alfa) |
| **H04** | C05 + C06 | q313–q511 (199 q + 12) | 70 mm. 1ª parte: traseira 3/4 alta, push-in de 15% na asa. 2ª parte (q435–q470): desce e gira até o eixo do carro, por trás, na altura da asa | contorno forte na borda da aba; fundo limpo para o recorte ler bem | f/2,8, foco na aba de cima | **asa traseira**: aba de cima gira no eixo do bordo de fuga, fechada → aberta em q384–q392 (ease-out, sem rebote), fecha e abre 2x em q404–q424, fica aberta. **Linhas de ar**: 7 curvas finas emissivas `#ED1131`, correndo de frente para trás de q446 a q511, passando pela fenda | `h04_asa_traseira.webm` (alfa) |
| **H05** | C07 | q506–q585 (80 q + 6) | 50 mm, tracking lateral colado no carro. Em q566 o carro acelera e sai pela direita em 13 q | luz de estúdio com faixas no piso para dar leitura de velocidade | f/4; motion blur forte no piso (8 a 10% da largura) e rodas girando | carro inteiro de lado, asa traseira aberta | `h05_velocidade.webm` (alfa) |
| **H06** | C09 | q741–q940 (200 q + 6) | 60 mm, vista de cima em diagonal (cerca de 55° de inclinação) sobre a pista inteira, deriva de 4% e giro de 6° no plano todo | luz lateral baixa para o relevo da pista fazer sombra; material tipo maquete, papel claro | foco seletivo (tipo maquete): nítido na faixa central, bordas borradas | **Interlagos** (`interlagos_sao_paulo.glb`). Faixa vermelha emissiva sobre a reta dos boxes crescendo em q826–q846 e sobre a reta oposta em q865–q885. Reservar a faixa de baixo (230 px) e o canto superior direito para o gráfico e o contador | `h06_interlagos.mp4` + `h06_pontos.json` (posição na tela, quadro a quadro, do começo e do fim de cada reta, para prender os rótulos) |
| **H07** | C10 | q942–q1109 (168 q + 6) | 50 mm. Viagem contínua: começa na lateral (entrada de ar), corre pela tampa do motor e chega em close no escapamento em q1064; ease-in-out | brilho correndo pela carenagem durante a viagem | f/2,0; o foco acompanha a peça mais próxima e trava no escapamento em q1064 | flanco, tampa do motor e **escapamento** | `h07_viagem.webm` (alfa) + `h07_pontos.json` (posição do escapamento na tela) |
| **H08** | C11 | q1103–q1197 (95 q + 6) | 100 mm macro, traseira baixa, órbita de 6° | chave rasante para destacar a espessura da mini asa; contorno no bocal do escapamento | f/1,8. **Troca de foco** do escapamento para a mini asa em q1114–q1127 | **mini asa junto ao escapamento** | `h08_mini_asa.webm` (alfa) + `h08_pontos.json` (posição da mini asa na tela) |
| **H09** | C12 | q1186–q1260 (75 q) | 50 mm, traseira 3/4. Recuo de 20% com órbita lenta de 10°; carro no terço esquerdo do quadro | luz mais aberta, reflexo completo no piso | f/4 | carro inteiro por trás, asa aberta | `h09_fecho.mp4` |

Total: cerca de 1.210 quadros de render.

Preparação do modelo (etapa 3), a partir do que o cabeçalho do `ferrari_sf26.glb` mostra (33 malhas, uma por material):
- Eixos no arquivo: comprimento em Y (traseira em Y negativo, luz traseira em y = -2,74; frente em y = +2,79). Altura em Z negativo.
- A aba de cima da asa traseira está fundida em `sf25_carbon1` (56 mil vértices) e `sf25_paints`. Separar por seleção de região (y abaixo de -2,2 e z acima do plano principal da asa), definir a origem no bordo de fuga e salvar como `assets\modelos\sf26_pecas.blend` e `.glb`.
- Rodas: `tyre_tread`, `tyre_sides`, `sf25_wheel_hub` e `discs.008` estão fundidas nas 4 rodas; separar por roda para girar no H05.
- Mini asa do escapamento: **conferir se existe no modelo** (procurar em `sf25_carbon1`, perto de y = -2,3 a -2,7, baixo). Se não existir, modelar com base em foto real do SF-26 (pesquisar antes) e salvar como peça derivada.

## 8. Camadas de motion graphics (HyperFrames)

Ordem de baixo para cima:

1. **Fundo**: papel `#EDEAE6` + grade de pontos. No C08, vermelho liso `#ED1131`.
2. **Palavra gigante** com decodificação: `2026`, `BRANCO`, `AGRESSIVO`, `GIRA`, `AR`, `VELOCIDADE` + `FINAL`, `TÍTULO`, `INTERLAGOS`, `DETALHES`, `DOWNFORCE`. Fica atrás do plano herói (exceto `INTERLAGOS`, que fica sobre a maquete com mistura "multiplicar").
3. **Plano herói** (vídeo do Blender, com alfa quando indicado).
4. **Rótulos com linha-guia** (secos): `FERRARI`, `ASA DIANTEIRA`, `ASA TRASEIRA`, `NAS RETAS`, `RETA DOS BOXES`, `RETA OPOSTA`, `ESCAPAMENTO`, `MINI ASA`. Posição presa à peça pelos arquivos `hNN_pontos.json`; onde a câmera quase não mexe, posição fixa.
5. **Etiquetas de estado e comparação**: `FECHADA` → `ABERTA`; `ANTES` / `2026` com fio divisor.
6. **Anotações à mão** (SVG com traço desenhado): círculos, seta curva do giro, contorno do perfil da asa, seta dupla, `novo!`, `olha o ângulo`, `passa direto`, `olha isso`, `+`, sublinhados, 3 setas de downforce.
7. **Números e dados** (C09): contador de km/h, gráfico de velocidade, selo de fonte.
8. **Cartões de pessoa** (C08): fotos P&B de `charles-leclerc.jpg` e `lewis-hamilton.jpg`, cartão de papel com sombra, tarja de pincel com o nome.
9. **Transições**: empurrão com borrão e esticamento, mergulho em cor, cortina, glitch.
10. **Áudio**: `narracao.mp3` a partir do quadro 0.

Textos na tela: só palavras que a fala diz ou rótulos da peça citada. Exceções assumidas: os números do C09 (ver seção 6) e as anotações à mão, que comentam em vez de repetir.

## 9. Riscos e plano B

| Risco | Plano B |
|---|---|
| A aba da asa traseira não separa limpa da malha fundida | girar o conjunto de cima inteiro (aba + suporte) ou cortar a malha com um plano; no pior caso, mostrar o giro em close mais fechado para esconder a emenda |
| O modelo não tem a mini asa do escapamento | modelar a peça com foto de referência; se não houver referência confiável, H08 vira close do escapamento e a mini asa entra como contorno à mão |
| O fantasma do SF90 não alinha com a asa do SF-26 (regras de 2019, largura diferente) | tirar o fantasma; C04 fica com a vista alta, o fio divisor e o contorno à mão do perfil |
| `.webm` com alfa pula quadro no HyperFrames | usar a sequência PNG, ou render sem alfa com a palavra gigante embutida no Blender (texto 3D atrás do carro) |
| Rótulos escorregam da peça nos planos com câmera viva | exportar os `hNN_pontos.json` do Blender (projeção do ponto 3D na tela, por quadro) |
| Carro vermelho contra fundo vermelho | já evitado: o modo cor cheia só aparece no C08, sem carro |
| Maquete de Interlagos pesada ou feia de cima | mapa 2D em SVG com `tracado.x/y` do JSON (giro de 258°), mesmos destaques e dados |

## 10. Pontos para o placar (etapa 5)

Cada cena C01 a C12 e cada plano H01 a H09 recebe nota em `PLACAR.md`. Pontos que o avaliador deve olhar de perto:
- H04: a aba gira no eixo certo, sem buraco na malha, e as linhas de ar passam pela fenda (não por dentro da peça).
- H02, H07, H08: profundidade de campo visível e brilho varrendo a superfície (é a lacuna principal contra a Formula Addict).
- C09: os picos do gráfico coincidem com as retas acesas, e o contador para exatamente em 334 e 331.
- Todas: palavra gigante entra entre 0 e 1 s depois da palavra falada; só um elemento vermelho por tela no modo claro.
