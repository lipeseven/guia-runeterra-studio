# Regras de direção — Explicando F1

Este arquivo entra no prompt do diretor. Todo ajuste fino do Felipe entra aqui.

## Pedido do Felipe vence as regras (2026-11-14)
- **Pedido explícito do Felipe SEMPRE é cumprido**, mesmo contra uma regra deste arquivo, da folha de estilos ou da API
  (número fora da fala, teto de efeitos, estilo de legenda, cor). Regra pré-setada nunca é motivo de recusa. Só vai para
  `nao_feitos` o que falta de verdade no motor (modelo que não existe, arquivo de logo/som que não está na pasta,
  informação que ninguém deu), e o motivo diz exatamente o que falta (ex.: "falta o arquivo F1/comum/arte/logos/fia.png").
- **Pedido pesado (2026-11-21)**: cada item de `nao_feitos` leva `"capacidade": true` quando o que falta é CAPACIDADE
  NOVA no motor — função/peça/efeito que a API das cenas não tem, ou julgamento visual que só olhando os quadros se
  resolve — e `false` quando falta só um arquivo ou uma informação do Felipe. Com `true` o pedido vai sozinho para o
  ORQUESTRADOR (o chat, que edita a biblioteca): não tente "quase fazer" nem ignore; diga no `motivo`, em uma frase,
  qual capacidade falta (ex.: "a API não tem partículas de faísca saindo do assoalho").
- **Número na tela fora da fala**: liberado só quando o Felipe pede. Ele declara na seção do briefing
  `NÚMEROS NA TELA (pedido do Felipe)` (uma linha por texto, ex.: `- 6,201 km`) ou escreve o número num pedido do card
  (inclusive respondendo a um "pedido não feito"). O texto vai para a tela exatamente como ele escreveu; os outros números
  continuam presos à fala (a checagem avisa "número fora da fala" no card).
- **Som específico**: som pedido pelo Felipe por nome de arquivo usa `som.arquivo` (com `obrigatorio: true`).
- **Logo**: só de arquivo em `F1/comum/arte/logos/` (`logo:chave`); nunca logo desenhado à mão.

## Ajustes do Felipe (GP do Brasil, 2026-11-04)
- **Cartões empilhados (`etapas`) cansam.** No máximo 1 por vídeo, e de preferência com `foco` (fundo escuro e desfocado).
  `foco` também é tempero: 1 ou 2 por vídeo. Para o resto, gráfico que interage com a cena: `linhatempo`, `minimapa`,
  `perfil`, `torre`, `relogio`, `ano`, `sentido`, ou a lista falada em cortes rápidos com `palavra`.
- **A abertura pode ser a própria pergunta escrita na tela** (`frase`, com `sem_legenda`), não precisa ser carro na pista.
- **O gráfico pertence à cena.** Falou de um trecho do circuito: o carro PASSA por ele, com o `minimapa` mostrando onde
  está. Falou de um vencedor: o carro na pintura dele, na vista panorâmica.
- **Vista de um circuito real usa `criarCircuito(nome, { cenario: true })`**, nunca a reta genérica (`set: "pista"`).
- **Carro parado fora do box parece acidente.** "Parada" é sempre no set `pit`, na marca, com a equipe em volta.
- **Plano só no carro, sem nada acontecendo, é fraco.** Toda cena mostra o que a fala diz.
- **Som:** nada de barulho de carro. Swoosh em troca forte de cena, pop quando algo aparece, alerta quando algo dá errado.
  **Efeito só em momento-chave, ligado a algo que muda na tela naquela palavra** (a cor do carro troca, um número aparece, o
  alerta da perda de posições). Sem isso, não leva som: efeito em toda cena vira "goteira" e não destaca nada. O efeito bate numa
  palavra-chave falada, nunca numa pausa. No máximo uma lista por vídeo com um efeito por item; ~9 efeitos em 2 min 20 s é a medida.
- **O autódromo fica na cidade**, não numa floresta nem numa rodovia: muros, arquibancadas e prédios em volta da pista, poucas árvores só no miolo.
- **Câmera transita.** Plano com carro usa `filmar` com 2 ou 3 posições, nunca uma posição só do começo ao fim (exceção:
  `drone`, `grua` e `passagem`, que já se movem sozinhas no trecho; `filmarVariado` cuida disso).
- **Velocidade do carro é constante no plano e parecida entre planos** (~0,015 da volta por segundo; reta rápida ~0,021).
- **O próprio cenário é o infográfico (aprovado, "Por que a chuva vira um problema em Interlagos?", 2026-11-08).** Em vez de
  cartão/seletor `etapas` por cima da imagem, cada palavra da lista marca algo DENTRO da cena, entrando seca na palavra:
  "curvas" = placa 3D da curva no traçado (`numerarCurvas`/`nomearTrechos`); "pontos de frenagem" = zona de frenagem acesa
  em vermelho no asfalto (`destacarTrecho`); "outros carros" = brilho âmbar nos carros (`brilho`). Só numerar a curva que
  aparece no quadro. Cuidado com o halo do brilho (forte demais) e com a placa colada na legenda.
- **Carro seguindo outro carro com spray: câmera panorâmica alta e de longe, acompanhando os dois.** Referência aprovada:
  `filmar` com 3 posições, ~70 m atrás, 31–35 m de altura, lente 30, mirando ~30 m à frente do ponto entre os carros;
  carros a ~19 m um do outro e spray curto (~12 m) para não cobrir o de trás. Câmera baixa/grudada atrás do carro foi
  reprovada: "levantar um pouco e ficar panorâmica, acompanhando de longe". Mundo tem só 140 partículas (`w.parts`):
  `solta` acima disso quebra a cena e cai na cena de reserva.
- **Circuito do PRÓXIMO GP (pedido do Felipe, 2026-11-10; vale mais que as regras pré-setadas).** Cena de pista que não
  depende de um circuito específico (tema geral: aerodinâmica, pneus, curvas, freios...) usa o circuito do próximo GP, agora
  **Las Vegas (GP 2026)**: `criarCircuito("lasvegas", { cenario: true })`, chave `"circ:lv"` (dia, padrão) ou `"circ:lvn"`
  (noite, só quando a fala/o clima pedir; desde 2026-11-21 a noite é em NEON por padrão, com bloom e luzes traseiras nos
  carros: ver `api_cenas.md`, "Las Vegas"). Nunca o do GP que já passou (Interlagos). Interlagos só quando a fala for sobre ele
  ou o tema exigir. Escolha a curva real que mostra a fala (curva rápida, grampo, Strip para reta). Rua estreita com muro:
  `filmar` com "lado"/"ladoesq" pode bater no muro; prefira "rasante", "curva", "alto", "heli", "atras" e confira o quadro.

## Velocidade, tráfego e câmeras (Felipe, GP de Las Vegas, 2026-11-21)
- **Carro de F1 tem que PARECER a 300 km/h em toda cena de pista** ("reclamo há muitos vídeos"). O sistema de velocidade da
  biblioteca liga sozinho (postes e painéis passando, asfalto com juntas, borrão de movimento, lente e tremor): não desligue sem
  motivo. Para parecer rápido: câmera BAIXA e PERTO (rasante, roda, rodaFrente, travelling, nariz, halo, passagem); câmera alta
  e longe (alto, heli, helicoptero) mostra o pelotão e o lugar, mas não velocidade: use-a só quando a fala pede o lugar/a corrida
  inteira. Velocidade de pista sempre a real (~0,014 da volta/s em Las Vegas = 87 m/s).
- **Carro só freia, e o freio só acende (`aquecer`), quando a fala é sobre frenagem/freio/curva lenta.** Fala genérica sobre a
  corrida ("correr aqui não é tão simples", "corrida", "pista") = carro a toda, sem freio incandescente. (Aos 5 s do GP de Las Vegas
  o carro desacelerava com luz saindo da roda: "é corrida de F1, tem que estar correndo".)
- **Mais carro na pista: a F1 tem 22.** Cena de corrida usa `pelotao` com 6 a 12 carros (22 na largada/visão do pelotão inteiro);
  carro sozinho só quando a fala é sobre UM piloto/carro (volta rápida, explicação de peça). Duelo = `forma: "duelo"`.
- **Câmera variada: no máximo 2 cenas seguidas com a mesma família de câmera** (`TIPO_CAMERA`: atras, baixa, lateral, frente,
  alto, heli, roda, onboard, orbita, grua, fixa) e nunca o vai-e-vem alto → atrás → alto → atrás. Padrão das cenas de pista sem
  enquadramento pedido pela fala: `filmarVariado(w, circ, f, c.k, c.n, { dur: c.fim })` (nunca repete a família no plano seguinte).
  Repertório (linguagem de TV de F1 e de jogo): câmera fixa de beira de pista que gira com o carro passando (`passagem`), roda e
  asfalto (`rodaFrente`), 3/4 frontal baixa, travelling lateral, nariz, sobre o ombro (`halo`), drone orbitando, grua subindo,
  helicóptero seguindo o pelotão.

## Ajustes do Felipe (GP de Las Vegas, 2026-11-21)
- **Mapa dos EUA: `criarMapaEUA` + `zoomNoMapa`, nunca chapa lisa** ("uma chapa azul sem detalhe. Cadê os estados? Se der
  zoom, cadê o mapa?"). Nunca `criarMapaRegiao`/`criarMapa("USA")` para falar de uma cidade ou estado americano: o país vira
  uma mancha só. O zoom vai do país ao estado e à cidade com `zoomNoMapa(w, mapa, k)`; o alfinete escala com a largura que a
  função devolve. Brasil: `criarMapaBrasil` (mesma ideia).
- **Rótulo 3D de um lugar ou objeto: `rotuloEm(w, chave, texto, alvo, { em })`, nunca `rotulo(...)` com `position.set` à
  mão.** O rótulo "ESTACIONAMENTO" saiu "totalmente descentralizado" porque a posição foi escrita no mundo e o objeto estava
  num grupo escalado; `rotuloEm` ancora no centro do alvo (já com a escala do grupo) e confere sozinho, a cada quadro, que o
  centro projetado do rótulo está a menos de 6% da largura do centro do alvo (senão `ERRO_ROTULO` nos quadros de conferência).
- **Prédio famoso é modelo com a cara dele, nunca bloco bege.** Caesars Palace: `criarCaesarsPalace({ epoca })` ("1981" =
  torre curva original; "atual" = torres com frontão, colunata, fontes e letreiro). O circuito de 1981/82 no estacionamento:
  `criarEstacionamentoCaesars()`. Outro prédio citado pela fala sem modelo: vai para `nao_feitos` pedindo a referência.
- **Posição numa corrida: `classificacao` (tabela com os nomes reais do 1º ao Nº e a linha do piloto acesa), sem seta.** "Não
  precisa de seta: é só a tabela e o nome na posição." Os nomes vêm do resultado oficial (briefing/conferência); sem o
  resultado conferido, não invente nomes. `torre` (com seta e troca de lugar) só quando a fala é sobre GANHAR ou PERDER posições.

## Aprendizados aprovados pelo Felipe (retrospectivas automáticas)
- Lista de nomes de lugares (curvas, trechos) na abertura vira tipografia grande sobre o mapa da pista, com o lugar citado aceso na palavra; nunca carro de perto, que não mostra onde o lugar fica. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Toda cena sobre uma curva ou trecho de circuito leva o minimapa com o trecho aceso (e o ponto do carro), para o espectador se localizar. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- A mesma linguagem de câmera não se repete em sequência: aproximar/afastar no carro no máximo 1 ou 2 vezes no vídeo; cada curva ganha um enquadramento próprio (câmera fixa na beira, visão do piloto, de cima, lateral, contra a luz). Câmera em movimento sempre por interpolação suave, nunca seguindo pontos com tranco. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Fala sobre o passado de um lugar mostra como ele era (traçado antigo desenhado sobre o atual, trechos que sumiram em vermelho) e traz informação concreta (ano, motivo); número de distância é contador com o traçado sendo desenhado, nunca barras de velocidade. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Fala com pessoas fazendo algo (tomar café, comemorar, trabalhar) mostra bonecos fazendo a ação no lugar citado; objeto sozinho parado na tela não serve. Câmera "no carro" mostra parte do carro no quadro para se entender onde ela está. _(vídeo: História das Curvas no Autódromo de Interlagos)_
- Quando o tema for o pneu (compostos, degradação, pressão, desgaste), o pneu é o protagonista: usar o pneu em destaque (close, vista explodida ou lado a lado por composto), nunca o carro inteiro como ilustração. O carro só aparece quando a fala é sobre a pista ou a corrida. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Todo objeto desenhado deve estar completo e com detalhe característico: pneu com aro/roda visível, banda lateral e cor do composto, nunca o miolo preto liso. Rodas giram sempre que o carro está em movimento na pista. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Câmera nunca fica travada nem entra no chão ou perto demais: usar movimento suave e contínuo entre 2-3 posições, com distância mínima que mantenha o objeto inteiro e sem cortar o solo. Para explicar partes do carro, usar visão panorâmica e destacar (brilho) a parte relacionada à fala. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Curvas do carro devem ser suaves, com trajetória em arco e velocidade angular contínua, sem pausa nem 'travadas' na entrada ou saída da curva. _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Caixas de texto não podem se sobrepor: antes de fechar a cena, checar que blocos simultâneos têm áreas separadas, com no máximo 2 textos ao mesmo tempo, ou escalonar a entrada e saída de cada um. Frases curtas de destaque podem ser quebradas em duas linhas hierárquicas (ex.: 'pneu mais' em cima, 'rápido' embaixo). _(vídeo: POR QUE A ESTRATÉGIA DE PNEUS É TÃO IMPORTANTE EM INTERLAGOS?)_
- Carro, capacete, macacão e boné de um piloto real seguem a identidade da época citada na fala (equipe, ano, modelo, cores). O diretor pesquisa antes de desenhar, e a cor correta vale para todas as cenas do mesmo ano. Não usar cor genérica nem de outra temporada. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Fala sobre chuva leva pneu de chuva (sulcado, cor correta), pista molhada e respingos. Condição do tempo citada na fala precisa aparecer no carro e no cenário. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Quando a fala cita um GP/circuito com data, usar o traçado real do circuito da época (da biblioteca/Wikimedia, nunca desenhado de memória) com a data em texto na tela, em vez de mapa-múndi ou mapa genérico. Mapa de país só quando o país é o lugar físico do evento, não quando é a nação como tema. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Números de estatísticas de carreira (títulos, vitórias, poles) viram infográfico próprio (cartão com número grande, troféu, bandeira ou ícone), nunca contador que parece gráfico de velocidade nem carro rodando como ilustração. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Texto em tela fica sempre alinhado (centralizado ou na mesma margem), com tamanho que caiba no take. Frase longa se divide em vários takes ou linhas, e o texto sobre cena de fundo ganha destaque com o fundo desfocado. _(vídeo: Ayrton Senna: por que ele era tão especial?)_
- Objetos fixos do cenário (indicador/farol, poste, placa, luz) ficam sempre ancorados a uma estrutura real da cena (parede do box, chão, teto), nunca flutuando solto no espaço. Antes de fechar a cena, checar que cada objeto tem apoio físico visível. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Evitar cores piscando (z-fighting): nunca sobrepor superfícies coplanares (cor de macacão, faixa, marcação, decalque); dar deslocamento mínimo entre camadas ou usar um único material. Vale para todos os personagens e objetos coloridos. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Quando a fala citar uma função ou pessoa específica dentre várias (ex.: um mecânico), destacar só ela: os demais ficam translúcidos ou saem da cena. Em cenas com poucos personagens para o que a fala descreve (ex.: 'segurança'), completar o elenco da equipe. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Cena de ação (troca de pneus, pitstop, trabalho em equipe) nunca fica com personagens parados: a ação descrita deve acontecer em todas as cenas, desde o primeiro quadro. Pitstop completo = carro chega, é atendido e sai; ao repetir uma ação, variar o ângulo. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Sentido de giro das rodas deve corresponder ao sentido de movimento do carro, na chegada e na saída (rotação para frente, sem parecer marcha à ré). Verificar o sinal da rotação na biblioteca, não com inversão manual por plano. _(vídeo: Como uma equipe troca quatro pneus em dois segundos?)_
- Todas as 4 rodas giram e as dianteiras esterçam em carro em movimento; roda inteira (pneu, aro, calota) gira como uma peça só. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Cor e vida (pedido do Felipe, vale mais que a regra do fundo branco): nunca cena quase toda cinza/branca. Cada ambiente tem identidade (céu em degradê, mar, box e pátio com piso/parede coloridos, marcações, neon em Las Vegas) e algo se movendo ao mesmo tempo (veículos, guindaste, poeira, câmera ativa). Cartão cinza de legenda repetido em todo plano não serve. _(vídeo: Como funciona o transporte dos carros na Fórmula 1?)_
- Mapa com país: sempre `criarMapaRegiao` (países coloridos, fronteira, oceano azul), nunca continente em mancha cinza única; ícones de veículo grandes o bastante para ler. _(vídeo: Como funciona o transporte dos carros na Fórmula 1?)_
- Pessoas usam os movimentos articulados de `boneco.ts` (andar, carregar, agachar, apontar, acenar); nunca deslizar parado ou em pose de "pau". _(vídeo: Como funciona o transporte dos carros na Fórmula 1?)_
- Gancho de abertura: escurecer a tela INTEIRA de modo uniforme (mesma opacidade em todos os pixels), nunca faixa ou degradê pela metade, para o texto ganhar destaque. _(vídeo: Como funciona o transporte dos carros na Fórmula 1?)_
- Texto em cartão/placa sempre centralizado, com margem igual dos dois lados e numa linha quando couber. Logo redondo (Sphere de Las Vegas) é recortado em círculo perfeito, sem cantos do JPEG. Número que rola até o valor falado nunca mostra valor errado no meio (ano 2026 fica 2026). _(vídeo: Como funciona o transporte dos carros na Fórmula 1?)_
- Cena com carro em pista: o pneu fica sempre apoiado no chão, sem atravessar o asfalto. Efeitos luminosos (brilho, rastro, linhas de vento) ficam contidos acima do solo e não cruzam chão, pneu ou carro; conferir o quadro antes de fechar. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Quando a fala fala de uma parte do carro (assoalho, asa, difusor), a câmera é escolhida para que essa parte apareça visível no quadro (ângulo baixo/lateral para o assoalho, vista que mostre o perfil da asa). Conferir que a parte citada não fica escondida pelo corpo do carro. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Plano com carro em movimento não pode parecer parado: zoom próximo e sem variação faz a cena parecer estática. Mantenha distância média/aberta e troque de take ou enquadramento quando a cena durar mais que alguns segundos. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Tags e rótulos de texto: devem ficar inteiramente dentro do quadro (respeitando margens da tela vertical), ter fundo com contraste/legibilidade (caixas não muito escuras, texto bem visível) e ficar na parte alta quando o carro ilustra o que é dito embaixo. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Destaques de listas faladas acompanham a palavra, um por vez, com o efeito que combina com o conceito (pneus = brilho nos pneus, asfalto = destaque no chão, temperatura = termômetro subindo). Ultrapassagem ou comparação entre carros usa pinturas diferentes para cada carro, e desenhos de comparação (ex.: asa de avião × asa de F1) usam o perfil real e correto, conferido antes de fechar. _(vídeo: Como um carro de F1 consegue fazer curvas tão rápido?)_
- Fala que descreve um efeito sobre o piloto (perder visibilidade, se perder, errar a curva) mostra a causa e o resultado juntos num enquadramento aberto: o carro dentro do contexto (atrás de outro, no spray, na curva) e visivelmente em dificuldade, como saindo da linha ou corrigindo. Nunca um plano fechado ou só o carro isolado. _(vídeo: Por que a chuva vira um problema em Interlagos?)_

- Vertical rende a 60 fps (horizontal segue em 30 até decisão); tempos de cena em segundos (`c.t`, `c.s`, `c.k`, marcas), nunca quadros fixos de 30.
- Pulo/travada: animação de carro na pista nunca pode andar em degraus. Giro, esterço e distância ao muro são interpolados entre os pontos do traçado; o giro visto da roda acima de 2,5 m/s vem do tempo do vídeo. Ao ver "imagem pulando", medir (quadros duplicados, fluxo ótico entre quadros consecutivos) antes de culpar o render. _(vídeo: Por que os freios de um F1 ficam incandescentes?)_
- Gancho em UM take contínuo e o que vem logo depois na mesma câmera/mundo, sem 3 tomadas curtas coladas nem teleporte; cortes só com sentido (mesma direção/eixo) ou troca de mundo. _(vídeo: Por que os freios de um F1 ficam incandescentes?)_
- Pedais do F1 atual: só freio (esquerda, mais largo, pé esquerdo) e acelerador (direita); sem embreagem de pé. Raio-X do piloto usa perna por IK com o joelho dobrando de forma crível. _(vídeo: Por que os freios de um F1 ficam incandescentes?)_
- Freio na biblioteca (`freio.ts`, `freio_cena.ts`): disco de carbono ventilado (Brembo, 328/280 mm), pinça de 6 pistões, brilho a partir de ~450 °C; todo carro já tem os 4 freios no aro. Para mostrar calor, cor do disco por temperatura, nunca creme pálido (parece frio). _(vídeo: Por que os freios de um F1 ficam incandescentes?)_
- Peça em close (freio, medidor, termômetro) com TAMANHO CONSTANTE no plano: `enquadrar` com `de`/`folga`/`lente` fixos; nada de órbita ou zoom animado que faça a peça "aumentar e diminuir". Close de peça sempre a mostra inteira e legível (nada de câmera colada num pedaço). Fala de frenagem ("reduzir a velocidade") = o freio funcionando de lado (pinça apertando, disco girando e esquentando), não o pneu. Fantasma (`isolar`/`raioX`) só em peça parada: em roda/disco girando ele pisca. Rótulos de zona (FRIO/ADEQUADA/QUENTE) aparecem um por vez, na palavra. _(vídeo: Por que os freios de um F1 ficam incandescentes?)_
- Peça com furos, parafusos ou padrão radial (disco, roda, calota) deve ter o padrão completo em 360° e fixo, sem elementos sumindo e aparecendo. Conferir o quadro antes de fechar. _(vídeo: pq os freios de um F1 ficam incandescentes?)_
- Ordem de camadas de peças encaixadas deve ser fisicamente correta (disco atrás da calota/roda, pinça sobre o disco). Em vista lateral, conferir profundidade de cada peça para que nada atravesse ou apareça na frente do que deveria cobrir. _(vídeo: pq os freios de um F1 ficam incandescentes?)_
- Trechos de fala longos ou explicativos não podem ficar com um único quadro parado. Alternar enquadramentos informativos (corte, detalhe, diagrama, infográfico) a cada poucos segundos, e usar o mesmo critério em trechos parados. _(vídeo: pq os freios de um F1 ficam incandescentes?)_
- Fala sobre sistema interno (híbrido, motor, bateria) mostra a câmera de lado ou em corte/raio-X com cada componente visível e rotulado. Nunca a traseira do carro, que esconde as partes. _(vídeo: pq os freios de um F1 ficam incandescentes?)_
- Quando um pedido de correção citar problema de movimento ou tamanho em uma cena, aplicar o mesmo critério a todas as cenas do vídeo com peça em close antes de entregar, e não só à cena citada. _(vídeo: pq os freios de um F1 ficam incandescentes?)_
- Escurecer o take nunca é solução para legibilidade: manter o fundo claro e vivo e dar legibilidade ao texto com uma plaquinha/fundo próprio na legenda. Antes de fechar, conferir que nenhum take ficou escuro demais e, quando o fundo da imagem for branco, usar fundo na legenda. _(vídeo: Como é calculado o número de voltas numa corrida de Fórmula 1?)_
- Circuitos, logos e modelos que já existem na biblioteca/pastas do projeto (mapas de 2026, traçados, logos como o da FIA) devem ser procurados e usados antes de desenhar ou usar genérico. Citar circuito pelo nome (Mônaco, Silverstone, Interlagos) = usar o traçado real da pasta de mapas; objeto simbólico (livro de regras, troféu) leva o logo oficial na capa. _(vídeo: Como é calculado o número de voltas numa corrida de Fórmula 1?)_
- Em cenas com mapa/traçado, o zoom da câmera deve manter todas as tags de nome legíveis e dentro do quadro durante todo o take: não aproximar a ponto de cortar ou fazer sumir rótulos, e etiquetas nunca saem da tela. Conferir o quadro mais fechado do movimento de câmera. _(vídeo: Como é calculado o número de voltas numa corrida de Fórmula 1?)_
- Texto em tela nunca cobre o elemento ilustrativo da cena (mapa, exemplo, imagem): reservar uma área própria para o texto e outra para a imagem e reorganizar a cena se houver conflito. Se a fala é sobre a imagem, o texto fica em faixa separada, fora dela. _(vídeo: Como é calculado o número de voltas numa corrida de Fórmula 1?)_
- Números e cálculos falados viram texto em tela com valor e unidade juntos, em formato curto de infográfico em caixa alta (ex.: "56 VOLTAS", "LIMITE 3H", "~305 KM = X VOLTAS"), com o termo-chave presente. Para números sorteados ou escolhidos, usar animação de número girando e travando no valor; medidas de pista (comprimento) aparecem dentro/sobre o traçado para ser didático. _(vídeo: Como é calculado o número de voltas numa corrida de Fórmula 1?)_
- Veículos em pista devem ficar sempre dentro do traçado: antes de fechar a cena, conferir em todos os planos (entrada, saída, câmera de fundo) que nenhum carro (incluindo safety car e carro líder) atravessa muro, parede ou contenção, e que o carro principal está inteiro dentro do enquadramento. Entradas na pista (pit lane, safety car) seguem uma trajetória real pela abertura, nunca em linha reta através de barreiras. _(vídeo: como funciona o safety car?)_
- Grupos de bonecos conversando ou reagindo (ex.: pilotos/engenheiros em reunião, em frente a uma tela) ficam virados um para o outro ou para a tela, nunca de costas para ela, com gestos de diálogo (cabeça, braços) e mobília coerente (cadeiras). Não usar 'levantar a mão' como gesto padrão de conversa. _(vídeo: como funciona o safety car?)_
- Equipe e mecânicos em cenas de box/pitstop usam o uniforme com as cores da equipe do tema (ou do exemplo mostrado), consistente em todas as cenas do vídeo, não macacão genérico. _(vídeo: como funciona o safety car?)_
- Quando a fala citar um local/GP específico com condição de horário (corrida noturna como Las Vegas), todas as cenas do vídeo ambientadas nesse local usam céu noturno, iluminação e neon, sem trechos de dia misturados. Conferir o horário do evento antes de escolher o céu de cada cena. _(vídeo: como funciona o safety car?)_
- Quando a fala citar elementos de uma lista ordenada (pneus macio/médio/duro, posições, estágios), dispô-los lado a lado, de frente para a câmera, em ordem lógica (macio à esquerda, médio no meio, duro à direita) e com as cores do composto visíveis, sem sobreposição nem câmera dentro de um objeto. Infográficos de corrida podem incluir contador de voltas (ex.: 48/62) quando a fala citar voltas restantes. _(vídeo: como funciona o safety car?)_
- Processo (o mais importante): antes de mostrar qualquer versão ao Felipe, o motor confere TODO plano em quadros de tamanho original (1080x1920: primeiro quadro, meio e o momento antes de efeitos entrarem) contra uma lista fixa: peça flutuando ou sem função, argola/bola/disco estranho, malha rasgada, mão ou personagem deformado, texto cortado, peça atravessando outra. O Felipe só deve receber erros de gosto, nunca erros que o motor consegue ver. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Objeto novo e complexo (mão, volante, cockpit, piloto, peça de carro) nunca entra direto no vídeo: primeiro uma prova isolada em 3 ângulos, tamanho original, com medidas reais e comparada à referência (foto real ou imagem que o Felipe mandou). Só depois de parecer o real vai para a direção. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Medidas reais para tudo que é humano ou do carro: mão adulta com luva (palma ~0,09x0,10 m, dedos 0,06-0,09 m com falanges 4:2,5:2, polegar ~0,055 m e menor que o indicador). Nada de proporção inventada nem 'pau', 'bola' ou 'bastão'. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Pegada no volante: cada mão fechada na empunhadura lateral (palma no lado de fora, dedos contornando a haste por trás e por dentro, pontas aparecendo na frente, polegar por cima do indicador), presa ao volante (gira com ele). Nunca dedo abrindo para fora, nada cobrindo tela ou botões. Verificar com o volante reto e girado (~90°). _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Entrada de ar (sidepod, airbox) é um buraco escuro escavado na própria carenagem. Nunca moldura, argola, anel, disco ou peça flutuando; peça que o carro real não tem não se inventa. Se houver dúvida, olhar foto real antes de modelar. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Pedido de remoção vira lista de proibidos do vídeo (bola preta, seletor final de cartões, brilho que não faz sentido, peça duplicada) e é conferida em todos os planos antes de cada entrega. Pedido já feito não pode voltar. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- POV é a visão dos DOIS olhos: câmera centrada no eixo do carro, abaixo do arco do halo, sem inclinar, também nas transições de e para câmera externa. Volante na altura do peito/queixo, face reta; cinto em faixas largas e claras sobre os ombros; sem almofada no pescoço. Toda fala sobre o que o piloto vê usa POV real, com as mãos no volante e sem faixa vazia embaixo; retrovisor citado = cabeça vira e o retrovisor real entra no quadro com reflexo. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Carro andando com piloto: o volante gira junto com o esterço das rodas, a tela mostra marcha e velocidade coerentes (reta 7ª/8ª, curva lenta 2ª-4ª, nunca 'N' em movimento) e as rodas ficam em borrão de movimento, nunca lentas ou para trás. Use `cockpitNaPista`. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Mostrar o piloto por dentro do carro usa corte limpo (`cortar`, plano entrando do lado da câmera), nunca raio-X/vidro translúcido do carro inteiro: as faces internas sujam o quadro. Destaque de peça = a própria peça emite brilho; nada de peça duplicada nem bolinhas. _(vídeo: como é a visão de um piloto de dentro do carro?)_
- Iteração em blocos: cada rodada muda SÓ o que o Felipe pediu; mudança de biblioteca só aditiva (opt-in) e provada por diferença de pixels nos planos não pedidos. Se o pedido citar um problema, procurar o mesmo problema em todos os planos do vídeo na mesma rodada. _(vídeo: como é a visão de um piloto de dentro do carro?)_
