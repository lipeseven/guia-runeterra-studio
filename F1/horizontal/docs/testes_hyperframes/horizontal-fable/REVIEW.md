# REVIEW — Ferrari SF-26, "O caminho do ar" (HyperFrames 0.9.20)

Data: 2026-11-12. Composição: `comp\index.html` + `comp\filme.js` (uma linha do tempo GSAP; tudo é função do quadro, ancorado nos quadros da SPEC). Saída: `video\ferrari_fable.mp4` (1920x1080, 30 fps, 1260 quadros, 42,0 s, H.264 + AAC, 31 MB).

## O que foi conferido

| Verificação | Resultado |
|---|---|
| `hyperframes check` | 0 erros (lint, runtime, layout, movimento, contraste, áudio). Avisos aceitos: 2 trilhas densas e 3 "estrutura aninhada" (o filme é um arquivo só, sem subcomposições); 1 de ofício: `DOWNFORCE` fica 1,1 s na tela (a fala acaba ali). 22 notas informativas de palavra gigante saindo do quadro ou atrás do vídeo com alfa (é o estilo) |
| `snapshot --review` | rodado; folhas em `comp\.hyperframes\artifacts\snapshots\` |
| Erro silencioso de vídeo/import | página aberta em servidor local (127.0.0.1:48731, já encerrado): os 9 vídeos com `readyState 4` e 1920 px, 2 fotos carregadas, áudio pronto, GSAP e dados presentes, console sem erro |
| Render de verdade | folhas tiradas do próprio MP4 (`assets\testes\final_1..5.jpg`, um quadro a cada 16): todos os planos 3D aparecem, com alfa correto e palavra atrás do carro |
| Áudio no MP4 | trilha AAC de 42 s; volume médio -21,3 dB, pico -4,1 dB (medido; não ouvido) |
| Tempo de render | 1 min 0 s (qualidade `delivery`, GPU, 5 workers) |

## O que entrou (pedido do BRIEF)

- Palavra gigante com decodificação atrás do carro: `2026`, `GIRA`, `AR`, `VELOCIDADE`, `DETALHES` (atrás do vídeo com alfa); `BRANCO`, `AGRESSIVO`, `DOWNFORCE`, `INTERLAGOS`, `TÍTULO` (na frente ou fora do carro, porque o plano não tem área livre atrás).
- Números colados ao objeto e contador: `16`/`44` ao lado dos cartões; contador de km/h subindo com os valores reais de `dados\telemetria_interlagos.json` (para em 334 e 331) e marcador vermelho correndo na reta.
- Gráfico de velocidade da volta (425 pontos reais, OpenF1, classificação 2025, Leclerc) com as duas retas em vermelho e selo de fonte.
- Tipografia condensada (League Gothic), rótulos em caixa com linha-guia presa à peça (pontos exportados do Blender), anotações à mão (Caveat) com traço desenhado.
- Transições medidas: 3 empurrões com borrão e esticão, mergulho em vermelho, cortina, glitch de 5 quadros, cortes.
- Cor de destaque única `#ED1131`.

## O que a revisão pegou e foi consertado

- Gráfico de velocidade não aparecia: uma regra de CSS esticava o SVG para fora da tela (o `check` passava). Consertado.
- Rótulo cortado na borda direita, palavras resolvendo tarde, `TÍTULO` e números escondidos atrás das fotos, anotação branca ilegível sobre logo, riscos de ar grossos demais, carro cortado no plano final (H09 refeito), riscos de ar vazando para o plano final (H09 refeito de novo).

## O que ficou fraco (ver PLACAR.md, rodada 3: vídeo 82/100; só C05 aprovada)

- Acabamento abaixo da Formula Addict: luz plana, carro pequeno nos planos gerais (C01, C12), só estúdio claro.
- Trechos parados de 1 a 2 s: maquete de Interlagos (câmera fixa), escapamento (q1070–1102), C04.
- C04 mostra a comparação só com duas linhas (cinza `ANTES`, vermelha `2026`); não há modelo da asa antiga. A linha cinza é ilustrativa, não medida.
- C08: fotos chapadas e ~0,5 s de vermelho quase vazio no começo.
- `BRANCO` fica na frente do carro; `AR` lê mal com o R tapado; `AGRESSIVO` ainda aparece embaralhado em q256.
- Borda serrilhada da pintura branca vem da textura do modelo.

## Decisões que cabem ao Felipe

- Os números 334 e 331 km/h são do carro de 2025 (a fala é sobre 2026) e a fala não os diz; ficam com selo de fonte.
- A mini asa do escapamento foi modelada (o .glb não tem), com forma aproximada.

## Não verificado

- Não ouvi o áudio nem assisti ao vídeo rodando: sincronia fala × tela foi conferida só pelos quadros da transcrição; fluidez das transições e do contador, só por quadros parados.

## Rodada 4 (2026-11-12) — `videoerrari_fable_v2.mp4` (42,0 s, 1260 quadros, ~35 MB; captura ~1 min). A versão anterior continua em `videoerrari_fable.mp4`.

| Pedido do Felipe | O que foi feito | Conferido |
|---|---|---|
| 1 Círculos à mão | oval liso (Catmull-Rom) que passa pouco do início ("perninha"), desenhado com ease-out, preso à caixa 2D da peça projetada do 3D (C02 tampa branca: cantos por raio na superfície; C05 aba; C11 mini asa) | script quadro a quadro + sequências; avaliador: parcial (C05 pega a aba inteira e o "44") |
| 2 Texto picotado | causa: letra à mão revelada com `clip-path` em % da caixa, sem folga para o contorno e a inclinação da Caveat, e que ficava ligado depois da entrada (cortava o "!"); trocado por máscara de borda suave + padding, removida no fim. Palavras gigantes: a decodificação com letras-isca saiu; entram letra a letra e saem inteiras | `txt_piscar.jpg`, `txt_voa.jpg`, CHKTXT; avaliador: atendido |
| 3 Asa Macarena | pivô movido para o bordo de ataque; giro de +170° em X (sobe, passa pela vertical, fica invertida) em q386–398; aberta em H05/H09 | `seq_h04aba.jpg`; avaliador: atendido |
| 4 Seta sem alvo | removida; setas restantes presas a pontos da peça, com halo | avaliador: atendido |
| 5 Mini asa | H04 e H07 misturavam quadros de duas versões da peça (renders 01:38/01:47 e 09:09/08:34); re-render completo de H04, H05, H07, H09; mini asa presa ao carro | `mini_cont.jpg`; avaliador: atendido |
| 6 Blur do começo | H01 de f/2,8 para f/6,3 | avaliador: parcial (agora quase não se vê profundidade) |
| 7 Ritmo | textos com tempo mínimo de leitura; câmera da asa dianteira re-temporizada (subida de 1,2 s para 1,9 s); BRANCO/2026/GIRA/DOWNFORCE/"num piscar!"/"voa!" mais longos; "novo!" e "NAS RETAS" cortados; 1 troca de plano por frase | avaliador: parcial |
| 8 Dados 2026 + carro na pista | OpenF1 GP de São Paulo 2026, corrida, Leclerc, volta 51 (1:14,170, a mais rápida): velocidade/freio/marcha e GPS interpolados a 30 fps. Gráfico de velocidade × distância com cursor do carro, contador com a velocidade real do quadro e selo "OPENF1 · GP DE SÃO PAULO 2026 · CORRIDA · LECLERC · VOLTA 51". H06 novo: carro 3D (10x maior que a escala real) andando na maquete pela trajetória GPS em lapso de tempo ~9x; câmera sai do geral, persegue o carro nas duas retas e volta ao geral | alinhamento: erro médio 3,9 m (máx. 9,7 m) OpenF1→linha central; carro encaixado na linha central (desvio médio 2,5 m); avaliador: parcial (carro pequeno, câmera rola, rótulo de reta oposta longo) |

Verificação: `check` 0 erros (avisos antigos: 2 trilhas densas, 3 aninhadas, 1 de movimento); página no servidor local 127.0.0.1:47913 (encerrado): 9 vídeos `readyState 4` a 1920 px, console sem erro; folhas de sequência do MP4 em `assets	estes4\`.

Não verificado: áudio não ouvido e vídeo não assistido rodando (só sequências de quadros); o lapso de tempo do carro no H06 não é tempo real; a 2ª passagem pela reta dos boxes usa o fim da própria volta 51 (antes da linha) emendado no começo dela.
