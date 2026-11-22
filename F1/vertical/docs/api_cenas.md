# API das cenas (lida pelo diretor)

Cada vídeo é um projeto novo: escreva as cenas DESTE texto. Cada plano traz um `codigo`: o corpo de uma função em
JavaScript puro (sem tipos, sem import, sem `return` de valor), executada a CADA quadro. Monte o quadro do zero a partir do
tempo: o mundo é zerado antes (só aparece o que o código puser). Nada aleatório: use `seed(i)` (0 a 1, fixo por i).

## Campos do plano (JSON)
- `em`: trecho exato do roteiro (2 a 5 palavras) onde o plano começa.
- `set`: cenário fixo que fica visível: `pista` (reta longa com grama, zebras, arquibancadas; carros andam para -z),
  `circuito` (circuito inteiro visto do alto), `estudio` (chão liso infinito; cor em `w.chao.color.set(...)`),
  `pit` (box), `livre` (nenhum cenário, só o céu: use para mapa, escada e pódio próprios).
- `clima`: luz e céu: tarde, manha, sol, noite, brasa, chumbo, vazio (estúdio escuro), claro (estúdio claro).
- `codigo`: a cena (abaixo). Ou `tipo`: uma cena pronta do catálogo, sem código, quando ela já diz exatamente a fala.
- `marcas`: {nome: "trecho exato"}: momentos dentro do plano; no código, `c.m("nome")` dá o segundo da palavra.
- `som` (opcional): {"o_que": "descrição curta EM INGLÊS do som", "em": "trecho exato"}; `sons`: lista igual, para mais de
  um efeito no plano. Só com sentido na fala: whoosh em troca forte ("fast cinematic whoosh"), pop quando algo aparece ("short
  soft bubble pop"), alerta quando algo dá errado ("short clean two tone alert beep"), clique de botão ou seletor ("single
  button click", "rotary knob clicks"), bipe de rádio ("radio beep static"). Barulho de carro: nunca. Só em momento-chave, em
  que algo muda na tela naquela palavra; a maioria dos planos fica sem efeito. O efeito bate na palavra citada e dura pouco (pop 0,3 s). Teto de 1 a cada 12 s no vídeo (o motor corta o excesso por igual). Efeito pedido pelo Felipe: `"obrigatorio": true` no
  som (passa por fora do teto e do intervalo; os outros continuam no teto); mantenha a marca nas revisões. A trilha não é daqui: é ligada no painel.
  **Som por arquivo** (2026-11-14): `{"arquivo": "freesound_cache/104026.ogg", "em": "trecho", "volume"?: 0.26, "duracao"?:
  0.8, "o_que"?: "nota", "obrigatorio"?}` toca AQUELE arquivo (sem busca). Caminho absoluto ou relativo a, nesta ordem:
  `dados/comum/`, a pasta do projeto do vídeo, a raiz do repositório, `dados/comum/freesound_cache/`,
  `F1/horizontal/kit/sfx/banco/` (ex.: `"alerta/alerta_dois_tons.wav"`) e `dados/comum/sfx/`. Áudio .wav/.mp3/.ogg/.flac/.m4a,
  normalizado como o catálogo (sem silêncio no início, até 6 s, pico -3 dBFS); `volume` 0,02 a 1 (padrão 0,26 ≈ os do
  catálogo), `duracao` em segundos (padrão: o som inteiro). Arquivo que não existe vira aviso no card e o render segue sem ele.
  Use quando o Felipe pedir um som específico ou quando nenhuma descrição acha o som certo; vale o mesmo teto dos outros.
- `sem_legenda`: true tira a legenda do plano (quando a frase já está em letra grande com o gráfico `frase`).
- `legenda` (2026-11-14): estilo da legenda. `{"fundo": "#0e1118", "opacidade": 0.72, "raio": 22, "margem": 18, "branca":
  true}`: `fundo` = caixa atrás do texto (cor hex ou CSS; sem `fundo` = sem caixa), `opacidade` 0 a 1, `raio` e `margem` em px;
  `branca: true` = todas as palavras já faladas em branco e negrito (legenda branca de destaque, sem o cinza das anteriores).
  No plano vale só para ele; na RAIZ da resposta (`"legenda": {...}` ao lado de `"planos"`) vale para o vídeo inteiro (o do
  plano se soma por cima). Use em cena clara ou movimentada onde a legenda se perde, ou quando o Felipe pedir.
- Números na tela: só os que a fala diz, **exceto os liberados pelo Felipe**: a seção `NÚMEROS NA TELA (pedido do Felipe)`
  do briefing (uma linha por texto/número, ex.: `- 6,201 km`) e todo número que ele escrever num pedido do card (inclusive
  a resposta a um "pedido não feito"). Esses vão para a tela exatamente como escritos; a checagem automática (aviso
  "número fora da fala") só libera aqueles números, nunca os outros.
- Gráficos informativos (campos do plano, 2D por cima da cena; UM por plano, só quando reforçam a fala):
  - `titulo`: {"texto": "RÁDIO — COMUNICAÇÃO", "sub": "COM A EQUIPE", "em": "trecho"}: só na troca de assunto.
  - `grafico`: {"tipo", "em": "trecho" (entra), "ate_em": "trecho" (fim do movimento), ...}:
    `icone` {icone: radio | raio | engrenagem | bateria | freio | diferencial | alerta | volante | pneu | seletor |
    cronometro | motor | nuvem | chuva | calendario | bandeira | trofeu | pista, texto?}: ícone grande num círculo com brilho.
    `regua` {esquerda: "FRENTE", direita: "TRÁS", de: 0.5, ate: 0.3}: marcador andando entre os dois lados (0 a 1).
    `bateria` {de: 1, ate: 0.3, segmentos: 5, texto?}: bateria por segmentos (abaixo de 25% fica vermelha).
    `seletor` {cliques: 3, de: 0, ate: 2, texto?}: seletor 2D girando em cliques ("1 de 3 cliques").
    `numero` {valor: 311, de: 0, unidade: "KM/H", max?}: número contando com barras.
    `etapas` {itens: ["ENTRADA", "MEIO", "SAÍDA"], itens_em: ["trecho", ...]}: cada etapa acende na sua palavra.
    `alerta` {texto: "ENERGIA LIMITADA"}.
    `frase` {palavras: [{t: "Brasil?", em: "Brasil?", brasil: true}, ...]}: a frase em letra grande, palavra por palavra; `brasil` = verde e amarelo com traço.
    `palavra` {texto: "HISTÓRIA", em}: palavra grande no corte rápido de uma lista falada (um plano por item).
    `ano` {de: 2026, valor: 1973, texto, em, ate_em}: o ano rola até o valor falado.
    `linhatempo` {marcos: [{rotulo: "1974", nome: "EMERSON FITTIPALDI", cor, em}, ...]}: linha que avança, marco atual em destaque.
    `minimapa` {de, ate, trecho: [a, b], texto, circuito}: traçado real no canto (norte para cima), trecho aceso e ponto do carro. `circuito`: "interlagos" (padrão) ou "lasvegas". `de`/`ate` = as MESMAS frações da volta que o carro percorre no plano (`f = de + (ate - de) * c.k`).
    `perfil` {de, ate, texto}: altitude real da volta de Interlagos, com o ponto andando.
    `torre` {n: 6, de: 1, ate: 4, texto, em}: torre de posições sem nomes; a linha acesa cai (vermelha) ou sobe (verde) e troca de lugar com as outras.
    `relogio` {texto: "SEXTA", horas: [{h: 12, m: 30, texto: "TREINO LIVRE 1", em}, ...]}: ponteiros giram até cada hora falada.
    `sentido` {texto: "ANTI-HORÁRIO", em}: seta circular girando no sentido da volta.
    **`etapas` (cartões/seletor empilhados): NUNCA (Felipe, 2026-11-18: "já pedi mil vezes pra não aparecer").** `foco` é tempero.
    `pos`: "meio" (centro) ou "baixo" (padrão, abaixo do assunto 3D). Com gráfico embaixo, deixe o assunto 3D no meio ou um pouco acima (ex.: alvoY negativo no enquadrar).
  - `foco`: true = modo quadro informativo: a cena 3D escurece e desfoca atrás e o gráfico vai para o centro (trecho
    que é explicação pura). Nunca dois planos seguidos com foco.
  Gráfico e placa no mesmo plano: não (um ou outro).
- Sobreposições (placas, contador, chips, selo, riscado, medidor, gota, chuva): campos do JSON, como no catálogo. Nunca
  desenhe texto de tela no código; rótulo 3D (`rotulo`) só para nomear coisas dentro da cena.

## O que o código recebe
`c`: `c.w` (mundo), `c.t` (segundo do vídeo), `c.s` (segundos desde o início do plano), `c.k` (0 a 1 ao longo do plano),
`c.fim` (duração do plano), `c.ini` (segundo em que o plano começa), `c.n` (número do plano no vídeo: semente de `filmarVariado`), `c.m(nome, frac)` (segundo de uma marca; sem a marca,
`c.ini + c.fim * frac`), `c.tipo(nome, {parâmetros})` (desenha uma cena pronta do catálogo; chame primeiro, depois acrescente).
Para animar: `suave(t, a, b)` (0→1 suave entre os segundos a e b), `entra(t, a, dur)` (0→1 com leve passada).

## Câmera (obrigatória em todo plano)
`camera(w, [x, y, z], [alvoX, alvoY, alvoZ], lente = 40, rolar = 0, topo = false)`: posição, para onde olha, lente (graus;
menor = mais zoom). `topo = true` para vista de cima. Movimente sempre com `c.s` ou `c.k` (a câmera nunca para).
`camCircuito(w, s, angulo, distancia)`: câmera do circuito inteiro.
`enquadrar(w, objetos, de = [0.6, 0.35, 1], folga = 1.15, lente = 36, alvoY = 0)`: câmera que mostra o objeto (ou a
lista de objetos) INTEIRO no quadro vertical, vindo da direção `de` (vetor a partir do centro deles: [0, 1, 0] = de cima,
[1, 0.2, 0] = de lado, [0, 0.3, 1] = de frente). Devolve a distância. **Regra:** cena cujo assunto é um modelo ou um grupo
(escada, pódio, kart com piloto, mapa, carro parado, pilotos lado a lado) usa `enquadrar`; para movimentar, anime `de`,
`folga` (1.4 → 1.05 = aproxima) ou `lente` com `c.k`. `camera()` à mão só para perseguição, POV e passagem rápida.
Exemplo: `enquadrar(w, escada, [0.35, 0.3, 1], 1.25 - c.k * 0.15, 36)`.
`orbitar(w, objetos, de, giro, folga, lente, alvoY)`: como `enquadrar` (com `de` FIXO), mas a câmera gira `giro` rad em
volta do eixo vertical na MESMA distância: movimento sem a peça aumentar e diminuir. Close de peça (freio, medidor) usa
`orbitar(w, f, [0.25, 0.18, 1], -0.22 + 0.44 * c.k, 1.25, 32)` em vez de animar `de`/`folga`.

## Unidades e direções
Metros. y = altura. Carros andam para -z (câmera em +z atrás vê a traseira). Pessoas, pódio e escada olham para +z
(câmera em +z vê de frente). Carro (molde de 2026): 5,4 m de comprimento, 1,9 m de largura, eixos em z = -1,55 e 1,85; piloto: 1,75 m; kart: 1,8 m.

## Carros de F1 (já existem, 22)
`poe(w, k, x, z, giro = 0)`: mostra o carro k (0 a 21) em (x, 0, z). Equipe = k/2 arredondado para baixo; pintura da
equipe e: 0 vermelho, 1 laranja, 2 verde-água, 3 azul, 4 roxo, 5 amarelo, 6 Mercedes (preto e prata, linha verde Petronas), 7 preto e
verde-limão, 8 preto e dourado (Cadillac), 9 verde, 10 branco e azul. Carros 12 e 13 = Mercedes.
`numeroNoCarro(w, k, "12")`: número no bico e nas laterais do carro k (fica nele).
`pneus(w, k, "macio")`: composto dos pneus do carro k (pneu Pirelli das fotos oficiais: PIRELLI, P ZERO ou Cinturato e xadrez na cor do composto; intermediário e chuva com sulcos): macio (vermelho), medio (amarelo, o padrão),
duro (branco), intermediario (verde), chuva (azul). Fica no carro até trocar de novo.
`poeCinza(w, k, x, z)`: carro cinza (eliminado). `grade(w, n, dz)`: n carros no grid de largada (pole em z = Z_POLE = -100;
`gridX(k)`, `gridZ(k)` = lugar k no grid). `halo(w, n, x, z, cor, opacidade)`: auréola de luz no chão (n = 0 a 21).
Outro carro com pintura própria: `obj(w, "carro:ferrari", () => carro({ base, clara, escura, faixa, acento }))` (cores
hex; devolve o objeto: posicione com `.position.set(x, 0, z)`).
Pinturas de época CONFERIDAS (tiradas das referências do Felipe em `F1/dados/modelos3d/`; use exatamente estas, sem
"aproximar"): McLaren MP4/8 1993 (Senna; base BRANCA, vermelho Marlboro nas faixas e asas, sem logos):
`carro({ base: "#f4f4f2", clara: "#ffffff", escura: "#2d2928", faixa: "#f32217", acento: "#f32217", desenho: "marlboro" })`
(`desenho: "marlboro"` põe o vermelho nas mesmas posições da foto: flecha no bico e flecha nos sidepods/traseira).

## Modelos (criados uma vez por chave; a aparência é fixa na chave)
`obj(w, chave, () => criarX(...))` cria na primeira vez e mostra o objeto neste quadro; devolve o objeto THREE (posicione
com `.position.set`, `.rotation.y`, `.scale.setScalar`). Chave diferente = outro objeto (ex.: "piloto:kimi:bone").
- `criarPiloto({ equipe, macacao, detalhe, faixa, bone, logo, capacete, pele, cabelo, traje, crianca, sentado })`:
  pessoa (sem olhos e boca) vestindo macacão. `equipe: "mercedes"` usa as cores conferidas da equipe (macacão preto, detalhes
  prata e verde Petronas, boné preto). Outra equipe: passe macacao/detalhe/faixa/bone/logo em hex, SÓ com cores que o
  briefing ou a folha de estilos confirmem. pele: "clara" | "media" | "morena" | "negra"; cabelo: "castanho" | "preto" |
  "loiro" | "ruivo" | "grisalho"; traje: "capacete" (no carro, correndo) | "bone" (pódio, entrevista, box, fora do carro);
  crianca: true (72%). `bracos(piloto, esq, dir)`: 0 abaixado, 1 erguido (comemoração = 1, 1).
- **Boneco articulado (2026-11-12, `modelos/boneco.ts`; pedido do Felipe: nada de boneco "pau" deslizando).** Todo
  `criarPiloto` tem cadeia de verdade: coluna (dobra no quadril), pescoço, ombro > cotovelo > pulso, quadril > joelho >
  tornozelo. Chame UMA pose por quadro, depois de posicionar o boneco (`.position`, `.rotation.y`; ele olha para +z):
  `andar(p, faseDoPasso(metrosAndados), ampl = 1, modo)` (pernas alternadas, braços balançando; modo "carregar" = caixa
  à frente com as duas mãos, "empurrar" = braços esticados e tronco inclinado); `faseDoPasso(m)` sincroniza o passo com a
  distância (pé não escorrega: mova o boneco em velocidade constante); `carregar(p, k)` parado segurando;
  `agachar(p, k)` (de cócoras, mexendo em roda/chão); `abaixar(p, k, comCaixa)` (curva o tronco para pegar no chão);
  `apontar(p, "esq" | "dir", k, altura)`; `acenar(p, c.t, "esq" | "dir", k)`; `empurrar(p, k)` parado; `neutro(p)` de pé;
  `olhar(p, giro, inclinacao)` por cima de qualquer pose; `maos(p)` = ponto no mundo entre as mãos (ponha ali a caixa:
  `cx.position.copy(maos(p)); cx.position.y -= metadeDaAltura; cx.rotation.y = p.rotation.y`). Gente em cena sempre faz
  alguma coisa (anda, carrega, agacha, aponta); nunca desliza parada. `bracos()` continua valendo.
- `criarKart({ cor, faixa, numero, piloto: {cor, faixa, pele} | false })`: kart com piloto criança sentado (frente -z).
- `criarPodio({ cor })`: pódio 2-1-3; `topoDoPodio(podio, 1|2|3)` = ponto em cima do degrau (para pôr o piloto).
- `criarEscada(["F4", "REGIONAL", "F3", "F2", "F1"], { pulados: [2], passo: 2.6 })`: escada subindo para +x, rótulo
  em cada degrau, pulados = degrau vazado e cinza; `degrau(escada, i)` = ponto em cima do degrau i.
- `criarMapa("ITA", { tamanho: 20, cor, vizinhos: true })`: mapa real do país (código ISO de 3 letras: ITA, BRA, MEX,
  GBR, DEU, ESP, FRA, MCO, NLD, AUS, JPN, USA, ARE, SAU…), deitado no chão (norte para -z), maior lado = tamanho, centro
  na origem. `pontoNoMapa(mapa, lat, lon)` = posição da cidade em cima do mapa. Use `set: "livre"` e câmera de cima
  (`camera(w, [0, 30, 9], [0, 0, 0], 40)` enquadra um mapa de 20 m). Chame `mapa.updateMatrixWorld()` depois de mover.
- `criarMapaRegiao({ centro: [lat, lon], largura: graus, tamanho: 20, cores: { BRA: "#2bb673" }, mar, borda })`: mapa de
  uma REGIÃO com cada país na própria cor e a fronteira desenhada, oceano azul (2026-11-12: "continente como mancha cinza
  não serve"). `cores` = destaque por ISO (fica mais alto); os outros pegam uma cor fixa da paleta. Ex.: mundo atlântico
  `{ centro: [18, -52], largura: 150, tamanho: 40 }`, Europa `{ centro: [47, 8], largura: 34, tamanho: 30 }`.
  `pontoNoMapa` funciona nele; rotas e alfinetes por cima. Ícones (avião, navio, caminhão) grandes o bastante para ler.
- `criarAlfinete("BOLONHA", cor)`: alfinete com rótulo; `.position.copy(pontoNoMapa(mapa, 44.49, 11.34))`.
- `rotulo("TEXTO", { altura, cor, fundo })`: placa 3D que olha para a câmera (dentro de `obj`).
- Também prontos no mundo: `w.trofeu` (troféu dourado: `.visible = true` e posição), `w.sc` (Safety Car; `rolarRodas(w.sc, metros, v)` gira as rodas dele: aro e raios, desde 2026-11-16).

## Logos e texturas de arquivo (2026-11-14; `modelos/logos.ts`)
O Felipe põe o arquivo licenciado em `F1/comum/arte/logos/` (nome do arquivo = chave: `fia.png` = `"logo:fia"`; PNG com fundo
transparente de preferência). A lista "LOGOS DISPONÍVEIS" no fim destes documentos diz quais existem. Logo que não está
na lista NÃO existe: não desenhe à mão nem troque por outro; ponha em `nao_feitos` o arquivo exato que falta (ex.: "falta o
arquivo F1/comum/arte/logos/fia.png"). Sem o arquivo, o objeto mostra um cartão cinza "FALTA fia.png" e o card avisa.
- `logo("logo:fia")` → textura (THREE.Texture) para qualquer material: `new THREE.MeshStandardMaterial({ map: logo("logo:fia"), transparent: true })`.
- `aplicarLogo(malha, "logo:fia")`: troca o material de uma malha que já existe pelo logo.
- `criarPainelLogo("logo:fia", { largura: 2, fundo: "#ffffff", moldura, margem, espessura })`: placa com o logo (frente +z,
  altura pela proporção do logo, centro na origem). Pendure em parede, pórtico, box (apoio físico visível).
- `criarLivro({ capa: "logo:fia", cor: "#16306b", titulo: "REGULAMENTO", largura: 0.6, altura: 0.85, espessura: 0.12 })`:
  livro de capa dura (livro de regras): capa +z, páginas brancas na lateral, logo e título na capa. Deitado na mesa:
  `l.rotation.x = -Math.PI / 2`. Sempre dentro de `obj(w, "livro:fia", () => criarLivro({...}))`.

## Pit stop (equipe coreografada, já pronta)
Use sempre que a fala mostrar um pit stop ou a função de um mecânico: nunca desenhe mecânicos à mão.
`const ps = obj(c.w, "pit:1", () => criarPitStop({ composto: "macio" }))` cria a equipe de 22 (cada função com a cor
dela em `PAPEIS`: pistola laranja, tira azul-claro, poe roxo, macaco amarelo, estabilizador verde-água, asa rosa
[tracejado = opcional], liberacao vermelho, seguranca salmão, apoio cinza), os 2 macacos, as 4 pistolas, o painel de
luzes (pendurado em cima, à frente do bico, num braço preso à parede do box do set `pit`; no estúdio ele some; nunca
desenhe outra luz ou poste) e os 4 pneus novos do composto. `ps.position.set(x, 0, z)` = onde o carro para (set `pit`: 0, 0).
`pitStop(c.w, ps, k, t, { foco, aneis, asa })`: põe o carro k e anima TUDO no segundo `t` do pit stop: t < 0 chegando
(de trás, +z), 0 parado, 0,1–0,4 macacos levantam, 0,2–0,55 pistolas soltam, 0,6–1,05 pneus velhos saem, 0,82–1,2 novos
entram, 1,28–1,5 aperto (cada luz da roda fica verde), 1,85 luz grande verde, 2,05 o carro sai. Tempo real:
`t = c.s - 1`; câmera lenta: `t = 0.3 + c.s * 0.25`; congelado: `t` fixo. As rodas do carro rolam na chegada e na saída (parado = paradas). `foco: ["pistola"]` = as outras
funções ficam translúcidas (close por função; quem segura a roda continua visível como fantasma); `outros: "some"` tira
os outros da cena (a roda que eles carregariam some do cubo e a nova só aparece montada: use quando nenhuma roda se
mexe no plano ou o close é de quem não mexe em roda); `outros: "cinza"` = o antigo cinza; `aneis: 1` (todas) ou `{ macaco: 1 }` = anel no chão na cor da função; `asa: c.k` = ajuste
opcional da asa dianteira (sem = não ajusta). `noPit(ps, nome)` = ponto para mirar a câmera (depois de `pitStop`):
"pistola_d_esq", "tira_t_dir", "poe_d_dir", "roda_t_esq" (d/t = dianteira/traseira, esq/dir), "macaco_d", "macaco_t",
"estabilizador_esq", "asa_dir", "liberacao", "seguranca", "painel", "luz" (a luz grande, para `brilho`), "carro".
`rolarRodas(carro, metros, velocidade?)`: as 4 rodas de um carro que anda (ex.: `poe` no pit lane), proporcional à distância
para a FRENTE (positivo; nunca inverta o sinal à mão: o sentido já é o certo). Pneu, aro e calota giram como uma peça só.
Carro rápido: passe a `velocidade` REAL (m/s) para o giro visto ficar limitado (~2,5 m/s; acima disso os 10 raios e o
PIRELLI "serrilham" a 30 q/s: calota parada ou girando para trás, ou tudo em marcha à ré); `pitStop` já faz isso na chegada
e na saída. Combina com `estercar` em qualquer ordem (um não apaga o outro). Carro de `poeNoCircuito` já rola sozinho. Ex.: `poe(w, 6, 7.5, 40 - 12 * c.s); rolarRodas(w.carros[6], 12 * c.s, 12)`. Visão geral: `camera(c.w, [6, 7, 7], [0, 0.5, 0], 40)`
ou de cima (`topo`); close: câmera a ~2,5 m do ponto, por FORA da equipe (x além de ±3), nunca no meio dos mecânicos.

## Freio (disco de carbono, pinça, pastilhas, tomada de ar; `modelos/freio.ts` e `freio_cena.ts`, 2026-11-12)
Medidas da Brembo: disco de carbono-carbono de 328 mm (frente) e 280 mm (trás), 32 mm de espessura, ~1.050 furos radiais de
ventilação na borda em fileiras; pinça de 6 pistões (metal, NÃO carbono); pastilhas de carbono. Picos acima de 1.000 °C só
em frenagem forte (nunca o disco brilhando a volta toda).
- **No carro (já vem nos 22):** cada roda tem o conjunto `freio_dianteiro_esquerdo` / `_direito` / `freio_traseiro_...`
  dentro do aro (aparece pelas janelas dos raios) e a tomada de ar do freio do lado de DENTRO da roda, boca para a frente
  (`tomada_dianteiro_esquerdo`...). O disco rola com a roda (`rolarRodas`/`poeNoCircuito`) e o conjunto esterça junto.
  `noFreio(carro, "dianteiro_esquerdo")` = centro do disco no mundo (para câmera e `brilho`); `tomadaDeAr(carro,
  "dianteiro_esquerdo", escala = 1)` = centro da boca da tomada no mundo (escala > 1 = tomada maior só neste quadro).
- **Freio solto:** `obj(w, "freio:f1", () => criarFreio({ tipo: "f1" | "rua", eixo: "dianteiro", duto: true }))`: conjunto
  com ~0,45 m de largura, eixo do disco em z (câmera em +z vê a face de fora e a pinça). Peças: disco_freio, canais (os
  canais internos aparecem com `raioX(f, ["disco_freio", "sino", "pinca"])`), sino, pinca, pastilhas, tomada_freio (duto
  com boca em funil, do lado de dentro). `tipo: "rua"` = disco de ferro fundido cinza com aletas e pinça de 1 pistão (para
  comparação). Use `enquadrar` com `de`, `folga` e `lente` FIXOS no plano (o Felipe reprovou a peça "aumentando e
  diminuindo"; o disco girando já não mexe no enquadramento: o rotor entra na caixa parado). Para abrir a peça, enquadre o
  conjunto já aberto e depois anime: `explodir(f, 1, d); enquadrar(...); explodir(f, k, d)`. `criarFreio({ pinca: 90 })`
  = pinça em cima (vista de lado `[1, 0.25, 0.3]` + `raioX(f, ["pinca"], 0.75)` mostra as pastilhas apertando o disco).
  `girarDisco(f, ang)` (o disco gira, a pinça não), `apertarFreio(f, k)` (0 solto, 1 pastilhas encostadas nas duas
  faces; só neste quadro). Freio do carro: nunca `isolar` o carro com a roda girando (o fantasma pisca).
- `aquecer(modelo, graus, w?, quais?, halo = 1)`: incandescência por temperatura (°C), só neste quadro: nada até ~450,
  vermelho escuro ~550, cereja ~750, laranja ~900, laranja-amarelo ~1.000, amarelo-claro >1.150. Só discos (pastilha um
  pouco; a pinça nunca). `modelo` = freio solto ou carro (as 4 rodas; `quais` = ["freio_dianteiro_esquerdo", ...]).
  Com `w` põe também o halo de luz em volta de cada disco. Escuro/noite faz o brilho aparecer. **Só quando a fala é sobre
  freio/frenagem** (2026-11-21: aos 5 s do GP de Las Vegas o plano "mas correr aqui não é tão simples" freava o carro e acendia
  o disco; o Felipe viu "luz saindo de dentro do pneu": "é corrida de F1, tem que estar correndo").
- `ventilar(w, freio, c.t, k)`: ar entrando pela tomada, descendo o duto e saindo pela borda do disco (freio solto).
- `fluxo(w, "chave", [pontos no mundo], c.t, k, { n, cor, tam, vel, espalha })`: partículas correndo por um caminho
  (ar no duto do carro, linhas de túnel de vento, energia). Até 300 por chave; não usa as 140 de `solta`.
- `criarTermometro({ marcas: [{ graus: 1000, texto: "1.000 °C" }] })` (1,2 m de pé; só marcas FALADAS; a marca é o filho
  "marca": `t.getObjectByName("marca").visible = ...`) + `medirTemperatura(t, graus)`.
- `criarMedidorTermico({ rotulos: ["FRIO", "ADEQUADA", "QUENTE"] })` (arco azul/verde/vermelho SEM números: a faixa
  ideal muda com material, pista e equipe) + `ponteiro(med, k)` (0 frio, 0,5 adequada, 1 quente; a zona acende).
- `criarPlacaCarbono()`: placa de fibra de carbono trançada (close do material).
- Híbrido 2026: `poeHibrido(w, carro)` = motor (vermelho), MGU-K (cilindro verde ao lado do motor), bateria (azul, sob o tanque),
  câmbio e eixo traseiro na posição do carro; enxergue com `raioX(carro, ["tampa_do_motor", "monocoque", "sidepod_esquerda",
  "sidepod_direita"])`. `caminhoDaEnergia(h, -1 | 1)` = pontos roda traseira → eixo → câmbio → MGU-K → bateria (para `fluxo`).
- Piloto pisando no freio (raio-X do cockpit, 2026-11-13): `const pd = poePedais(w, carro, k)` (só 2 pedais, como no F1
  de hoje: FREIO à ESQUERDA, mais largo, pisado com o pé ESQUERDO; acelerador à direita; cilindros-mestres e linhas de
  freio laranja até as 4 pinças; k 0 solto, 1 no fundo) + `poePilotoNoCarro(w, carro, k)` (boneco articulado reclinado no
  cockpit, braços no volante, perna esquerda por IK até a sapata: o joelho dobra e o pé acompanha o pedal) +
  `fluxo(w, "pressao", linhaDoFreio(pd, "dianteiro_esquerdo"), c.t, k)` (pressão correndo até a pinça). Enxergue com
  `raioX(carro, ["monocoque", "tampa_do_motor", "sidepod_esquerda", "sidepod_direita", "halo", "roda_dianteira_esquerda",
  "suspensao", "asa_dianteira"])`; câmera de lado a ~3,5 m mostra o piloto inteiro; a ~1,8 m da frente esquerda, o pedal.
- Cockpit em proporção real (2026-11-17): o carro tem ABERTURA de verdade (~0,85 x 0,47 m, fundo escuro, borda
  acolchoada, apoio de cabeça dos lados), halo de 3 pontos (arco na altura da testa, pilar central preso à frente da
  abertura) e um piloto simples dentro (capacete, ombros, volante). `poePilotoNoCarro` troca esse piloto simples pelo
  boneco articulado reclinado (~50°), com o VOLANTE de verdade na coluna (~27 cm à frente do peito) e as mãos nas
  empunhaduras por IK (cotovelos dobrados para baixo); o volante fica em `p.userData.volante` (`apertar`, `girar`,
  `telaDoVolante` funcionam nele; `{ volante: false }` tira). Volante sozinho no carro: `poeVolanteNoCarro(w, car)`. Para destacar o volante sem a coluna: `realcar(v, nomesDasPecas(v).filter(n => n !== "engate_rapido"), k)`.
  Medidas em `COCKPIT` (Carro3D.tsx). Com o carro opaco só aparecem capacete e alto dos ombros (como no real).
- Câmeras do cockpit (com `poePilotoNoCarro`; seguem o carro parado ou no circuito): `cameraNoCockpit(w, car, tipo,
  { k, olhar, lente, rolar })`. `tipo`: "piloto" (o que ele vê: topo do volante, halo e pilar central, a pista; lente
  74), "ombro" (por cima do ombro direito: capacete, mãos e volante), "rosto" (do volante para o capacete, halo em
  volta), "lado" (lateral do cockpit; com raioX do monocoque/tampa/sidepods vê o corpo reclinado), "cima" (do alto, à
  frente: a abertura e o piloto encaixado). `k` 0 a 1 = aproximação lenta (anime com c.k); `olhar` [x, y, z] no espaço
  do carro troca o alvo (ex.: retrovisor esquerdo [-0.5, 0.72, -0.25]). Para enquadrar/orbitar o cockpit inteiro (do
  pedal ao capacete): `enquadrar(w, alvoDoCockpit(w, car), [1, 0.35, 0.2], 1.1, 34)`.
  Ex.: `poe(w, 20, 0, 0); const car = w.carros[20]; const p = poePilotoNoCarro(w, car, 0); apertar(p.userData.volante,
  "ot", k); cameraNoCockpit(w, car, "ombro", { k: c.k });`
- **Polegar até um botão (2026-11-20):** `polegar(p, "ot", k)` (`p` = o piloto de `poePilotoNoCarro` ou `cockpitNaPista`; nomes: ot, boost,
  aero, pl, n, radio, bb_mais, bb_menos). `k` 0 a 1: de 0 a 0,7 o polegar solta a pegada e vai até o botão (por cima da face, sem
  atravessar o volante); de 0,7 a 1 afunda e acende o botão (já chama `apertar`: não use os dois). A mão que alcança é a do lado do
  botão (OT, BOOST, PL, RÁDIO, BB+ = direita; N, AERO, BB− = esquerda); a outra fica na empunhadura. Com k 0 nada muda. Ex.:
  `const p = cockpitNaPista(w, car, q, v, { semCabeca: true }); polegar(p, "ot", suave(c.t, c.m("aperta"), c.m("aperta") + 0.4));`
  (o `realcar(vol, "botao_ot", ...)` continua valendo para o brilho). O polegar é mais comprido que o de repouso: é o alcance real.
- POV do piloto na pista (2026-11-18, "como se nós estivéssemos numa câmera POV"): `poeNoCircuito(...)`, `const p =
  poePilotoNoCarro(w, car, 0); telaDoVolante(p.userData.volante, { marcha: "8" }); cameraNoCockpit(w, car, "piloto",
  { lente: 78, rolar: 0.012 * Math.sin(c.t * 2.1), olhar: [0.25 * Math.sin(c.t * 0.45), 0.45, -5] })` com 2 ou 3 carros
  à frente (`poeNoCircuito(..., f + 0.0026, { lado: 1.7 })`): halo e pilar no meio, volante com a tela embaixo, pista e
  carros. Os retrovisores ficam a ~70° do olhar: não entram no quadro vertical (só olhando de lado). Lista falada no fim
  = esse POV com UM rótulo curto por vez à frente (`rotulo` em `car.localToWorld(V(0, 2.3, -7))`), nunca `etapas`.
- **Piloto andando na pista (v6, 2026-11-18):** `const q = poeNoCircuito(w, k, circ, f, { v }); cockpitNaPista(w, car, q, v,
  { semCabeca: true })`: o volante gira com o esterço das rodas (q.esterco × 4, até ±1 rad) e a tela mostra marcha
  (`marchaDe(kmh)`, 8 marchas) e velocidade de `v` (m/s). Sempre ele, nunca `poePilotoNoCarro` com o carro andando.
  Câmera `cameraNoCockpit(w, car, "pov")` = POV um pouco atrás dos olhos (a cabeça some com `semCabeca`): mãos no
  volante, halo, bico e pista, sem faixa vazia embaixo. Retrovisor: `espelhoReal(w, car, -1 | 1)` (Reflector do three.js
  sobre o vidro do retrovisor do próprio carro, virado ~35° para o piloto) + `cameraNoCockpit(w, car, "piloto", { olhar:
  [-0.56, 0.75, -0.42], lente: 34–40 })`; para a "olhadinha", leve o `olhar` da frente ([0, 0.42, -5]) até o espelho.
  Piloto por dentro sem sujeira: `cortar(car, [1, 0, 0], [x, 0, 0])` com x indo de 1,2 a 0,02 (corte entrando), não
  raio-X translúcido do carro inteiro.
- **v7 (2026-11-18):** POV de verdade = `cameraNoCockpit(w, car, "olhos", { rolar, olhar: [x, 0.6, -5] })`: olhos ABAIXO do
  arco do halo (arco e pilar no alto do quadro, volante grande na altura do peito/queixo), CENTRADA entre os dois
  olhos (v8), lente 82; some com a cabeça (`semCabeca`). Vibração de alta velocidade: some `0.004 * Math.sin(c.t * 53)`
  ao `rolar`. Carro rápido na pista: `rodasRapidas(car, v)` depois de `poeNoCircuito` = face da roda vira disco com
  borrão de movimento (a partir de 25 m/s), opt-in, nada muda nos planos que não chamam.
- **DRS / modo reta na pista (2026-11-20):** `drs(car, k)` abre a ABA MÓVEL da asa traseira do carro. A asa vem FECHADA por padrão (flap inclinado, borda de trás mais alta, carga
  aerodinâmica; redesenhada em 2026-11-20): só abra nos modos que pedem (k 0 fechada, 1 aberta, ~24° a mais, flap quase deitado e a fresta
  aberta; articula na borda de trás, a da frente sobe) e volta sozinha no quadro seguinte. Vale para qualquer carro da biblioteca
  (parado, no circuito, em `perseguir`). Ex.: `const ka = suave(c.t, c.m("abre"), c.m("abre") + 0.3); const kf = suave(c.t, c.m("fecha"), c.m("fecha") + 0.6);
  drs(w.carros[6], ka * (1 - kf)); realcar(w.carros[6], "asa_traseira", ka * (1 - kf), "#ffd23f");` Só a aba traseira mexe (a dianteira é fixa).
- `escurecer(w, k)`: escurece a tela INTEIRA por igual (vidro preto na frente da câmera; chame depois da câmera). Para o
  gancho de abertura com `frase`, sem desfocar a cena (o `foco` desfoca).

## Volante (genérico de 2026, sem equipe)
`obj(w, "volante", () => criarVolante())`: volante real em metros (~29 cm de largura), frente para +z. É pequeno: use
`enquadrar(w, v, [0, 0.08, 1], 1.08, 30)` para a frente inteira, `[0.7, 0.25, -1]` para ver os paddles atrás; close de um
botão com `camera()` a ~8 cm. Comandos (chame a cada quadro, na palavra que cita):
- `apertar(v, nome, k)`: ot (modo de ultrapassagem), boost (energia extra), aero (modo reta da asa ativa), pl (limitador
  do pit), n (neutro), radio, bb_mais / bb_menos (balanço de freio). k 0 solto, 1 afundado e aceso.
- `girar(v, "esquerdo" | "central" | "direito", posicao 0 a 11)`: seletores giratórios (anime com fração).
- `puxar(v, "marcha_direita" | "marcha_esquerda" | "embreagem_direita" | "embreagem_esquerda", k)`: paddles atrás.
- `luzesDeTroca(v, f)`: luzes de troca de marcha (0 apagadas, 1 todas: verde, vermelho, azul).
- `telaDoVolante(v, { marcha, modo, delta, bateria, velocidade })`: o que a tela mostra (ex.: marcha "7", modo "OT").
Peças para o desmonte: tela, luzes, botao_ot, botao_boost, botao_aero, botao_pl, botao_n, botao_radio, botao_bb_mais,
botao_bb_menos, seletor_esquerdo, seletor_central, seletor_direito, frente, placa_de_circuitos, carcaca,
empunhadura_esquerda, empunhadura_direita, paddle_marcha_esquerda, paddle_marcha_direita, embreagem_esquerda,
embreagem_direita, engate_rapido. Os outros botões da face são só aparência.

## Geografia real (set "real": nenhum cenário fixo, névoa longe)
- Circuitos na biblioteca: `"interlagos"` (atual, com cenário), `"lasvegas"` (Las Vegas Strip Circuit, com cenário, ver abaixo),
  `"monaco_1984"` (Mônaco 1976-1985, 3,312 km), `"donington_1993"` (GP da Europa 1993, 4,023 km) e `"silverstone"` (5,891 km, 2026-11-14:
  traçado bacinger/f1-circuits gb-1948 + 18 curvas do MultiViewer, sem cenário; f 0 = linha de chegada; script em F1/dados/mapas/silverstone_dados/preparar.py)
  e `"monaco"` (Circuit de Monaco ATUAL, 3,337 km, 19 curvas do MultiViewer, sem cenário; traçado bacinger mc-1929; script
  preparar_monaco.py). **`"monaco"` = Mônaco de hoje; `"monaco_1984"` = o traçado de 1976-1985 (3,312 km), só para fala sobre
  aquela época (Senna 1984).** Os dois novos têm `numerarCurvas` (posição real de cada curva), mas não `cenario` nem `perfil`.
  Silverstone, numeração oficial (Wikipedia, conferida 2026-11-14): 1 Abbey 0,078; 2 Farm 0,104; 3 Village 0,148; 4 The Loop
  0,178; 5 Aintree 0,210; 6 Brooklands 0,336; 7 Luffield 0,374; 8 Woodcote 0,434; 9 Copse 0,524; 10-13 Maggotts e Becketts
  0,618–0,684; 14 Chapel 0,709; 15 Stowe 0,855; 16 Vale 0,932; 17-18 Club 0,949–0,974. `nomearTrechos` já usa esses nomes.
  Mônaco atual: nomes dos trechos NÃO conferidos curva a curva (só 1 Sainte-Dévote e 11 Nouvelle Chicane); `nomearTrechos`
  não escreve nada nele: nomeie com `rotulo` só o que a fala citar e o briefing confirmar.
  Os antigos só têm o traçado (sem cenário nem curvas numeradas); f 0 = linha de chegada.
  Nunca desenhar traçado à mão: circuito que não está aqui precisa ser criado na biblioteca.
- `obj(w, "circ:interlagos", () => criarCircuito("interlagos", { rotulos }))`: o circuito com o TRAÇADO REAL, em metros
  (4,309 km; asfalto, área de escape, zebras, linha de chegada). Vídeo sobre um circuito usa SEMPRE o traçado real, nunca a
  reta genérica. f = fração da volta no sentido da corrida (0 = linha de chegada). Interlagos (numeração oficial): S do
  Senna 0,07–0,11 (curvas 1-2); Curva do Sol 0,146 (3); Reta Oposta 0,165–0,31; Descida do Lago 0,32–0,36 (4-5); Ferradura
  0,46–0,49 (6-7); Laranjinha 0,53 (8); Pinheirinho 0,56 (9); Bico de Pato 0,627 (10); Mergulho 0,675 (11); Junção 0,743 (12);
  Subida dos Boxes 0,77–0,99 (13-15).
- **Sempre `criarCircuito("interlagos", { cenario: true })`** (chave `"circ:cen"`, é o mesmo objeto em todos os planos): relevo,
  cidade, muros, arquibancadas, boxes e poucas árvores em volta do traçado real. Lado positivo = direita do sentido da corrida = por fora.
- `poeNoCircuito(w, k, circ, f, { lado, escala, v })`: carro na volta, já com esterço das dianteiras (curvatura real um pouco à
  frente do carro, visível: curva lenta ~20-25°, rápida 5-10°, reta 0) E as 4 rodas rolando com a distância de f; `v` = velocidade
  real em m/s (f por segundo × 6201 em Las Vegas; padrão 80), só para limitar o giro visto. Não chame `rolarRodas`/`estercar`
  de novo por cima; `escala` só em vista de longe (4 a 7).
  `v` pode mudar a cada quadro (frenagem, aceleração): acima de 2,5 m/s o giro visto vem do TEMPO do vídeo (sempre o
  mesmo ritmo, sem saltos); abaixo, da distância real (2026-11-13). O giro do carro na pista é interpolado entre os pontos
  do traçado (antes andava em degraus e a câmera presa ao carro dava tranco).
- `poePinturaNoCircuito(w, "chave", { base, clara, escura, faixa, acento }, circ, f, { escala, v })`: carro com pintura própria (só cores conferidas), com esterço e rodas rolando.
- **`filmar(w, circ, f, c.k, ["curva", "lado", "atras"], { lado })`: câmera padrão de carro na volta.** Transita pelas posições ao longo do plano, sem tranco: atras, curva, rasante, lado, ladoesq, frente, alto, heli, roda (e as novas abaixo: rodaFrente, tresQuartos, travelling, nariz, halo, helicoptero, drone, grua, passagem). Use 2 ou 3 posições; com dois carros: alto, atras, frente ou heli (lado corta o outro).
- `perseguir(w, circ, f, { atras, alto, frente, lente })`: câmera atrás do carro olhando a pista à frente; a curva aparece antes de ele virar. Curva: atras 17, alto 6,5, frente 30, lente 50. Reta rápida: atras 11, alto 2,3, frente 30, lente 62. Velocidade real: ~0,016 da volta por segundo.
- **Câmeras novas de `filmar` (2026-11-21, pedido do Felipe: "alto → atrás → alto → atrás o vídeo todo cansa").** Além de
  atras, curva, rasante, lado, ladoesq, frente, alto, heli e roda: `rodaFrente` (baixa, colada na roda dianteira, olhando para a
  frente: pneu e asfalto correndo), `tresQuartos` (3/4 frontal baixa, o carro vindo na direção da lente), `travelling` (corre
  junto, de lado e baixa, a ~5 m), `nariz` (no bico, olhando para a frente), `halo` (sobre o ombro / acima do halo, T-cam),
  `helicoptero` (alto e longe, lente 26, de lado: bom para o pelotão), e as que mudam no próprio trecho: `drone` (orbita o
  carro ~110°), `grua` (sobe do chão a ~18 m) e `passagem` (pan-by: câmera FIXA na beira da pista, o carro vem de longe com lente
  fechada, passa colado e vai embora com a câmera girando atrás dele; passe `{ dur: c.fim }` para ele passar no meio do trecho).
  `{ espelho: true }` troca o lado das tomadas laterais. Famílias (`TIPO_CAMERA`): atras (atras, curva), baixa (rasante),
  lateral (lado, ladoesq, travelling), frente (frente, tresQuartos), alto, heli (heli, helicoptero), roda (roda, rodaFrente),
  onboard (nariz, halo), orbita (drone), grua, fixa (passagem).
- **`filmarVariado(w, circ, f, c.k, c.n, { dur: c.fim, evitar })`: câmera de pista escolhida do repertório pelo número do
  plano (`c.n`).** Planos seguidos nunca repetem a família de câmera; cada um varia ângulo, distância e lente (±12%) e o lado.
  `evitar: ["onboard"]` tira famílias que não servem na cena. Devolve as tomadas usadas. Use-a como padrão nas cenas de pista
  em que a fala não pede um enquadramento específico.
- **`pelotao(w, circ, f, n, { foco, v, forma, posicao, carros, semente })`: n carros (até 22, as 11 equipes × 2 com a pintura
  de cada uma) andando juntos, sem sobreposição.** O carro `foco` (padrão 0) fica em f; `forma`: "pelotao" (padrão: grupos de
  2 a 4 colados e buracos entre eles), "fila", "duelo" (pares lado a lado) ou "espalhado"; `posicao`: "meio" (padrão, carros à
  frente e atrás do foco), "lider" ou "fim"; `v` em m/s (padrão 85). As distâncias respiram devagar (aproximam e afastam). Já
  chama `rodasRapidas` em todos. Devolve [{k, f, lado}]. Não ponha outro carro com `poeNoCircuito` no mesmo número: passe
  `carros` sem ele. Custo medido: ver "Velocidade" abaixo. Ex.: `const f = 0.70 + 0.014 * c.s; pelotao(w, circ, f, 10, { foco: 0, v: 87 });
  filmarVariado(w, circ, f, c.k, c.n, { dur: c.fim });`
- **Velocidade (2026-11-21, Felipe: "o carro parece que está a 30 km/h quando devia estar a 300"; `modelos/velocidade.ts`).**
  Liga SOZINHO em todo plano que põe carro na pista (`poeNoCircuito`, `poePinturaNoCircuito`, `transito`, `pelotao`) ou usa câmera
  de pista (`filmar`, `perseguir`, `filmarVariado`), com a câmera a menos de ~90 m do chão (circuito visto do alto não muda):
  postes do alambrado a cada 3 m, painéis vermelho/branco de 2 m no pé do muro (sem cenário: balizas a cada 8 m), juntas e
  remendos no asfalto; lente que abre até +7° e tremor leve proporcionais à velocidade (só com a câmera perto do carro); e
  borrão de movimento (o quadro é a média de 4 subquadros num obturador de 180°). Carro com `escala` > 1,5 (vista de longe)
  não liga. Desligar no plano: `semVelocidade(w)` (carro parado, box, explicação calma) ou `{ velocidade: false }` na função.
  Ajuste: `velocidade(w, { borrao: 6, obturador: 0.75, tremor: 0, lente: 0, pistas: false })` (borrao = nº de subquadros,
  false = sem).
  Medido no GP de Las Vegas (fluxo óptico em 12 quadros seguidos, px/quadro numa tela de 1080, só onde há desenho): antes, a
  perseguição a 87 m/s tinha 0,5-0,8 e a POV (a cena que o Felipe achou mais rápida) 1,2. Depois: perseguição 2,3, rasante/frente
  4-5, POV 2,1. Alvo para 300 km/h com câmera perto: ≥ 2. Câmera alta/heli continua ~1 (não mostra velocidade, mostra o
  lugar). Custo por quadro (render por blocos, concorrência 3, 48 quadros): perseguição 0,239 → 0,247 s com o borrão
  (diferença dentro do ruído da medida, ~±10%); 22 carros 0,282 s contra 0,246 s com 1 carro (+15%); 22 carros + borrão 0,338 s.
  Estúdio, mapas e circuito visto do alto: diff de pixels 0 e mesmo tempo.
- `panorama(w, circ, azimute, alto, folga)`: a pista inteira em diagonal (alto 0 rasante, 1 de cima; folga 0,86 cabe na tela).
- `transito(w, circ, c.t, [carros], { escala, v })`: carros andando pela volta. `nomearTrechos(w, circ, k)`: nomes reais dos trechos sobre a pista.
- Vista panorâmica acompanhando o carro: `camera(w, [q.x + 330 * sin(az), 400, q.z + 330 * cos(az)], [q.x, 0, q.z], 38)` com carro em escala 7.
- `noCircuito(circ, f, lado)` → {x, z, giro, esterco}: carro na volta (`poe` + `estercar`). Visto do alto, o carro some
  (5 m numa pista de 1 km): marque-o com `brilho(w, "carro", posição, 40, 1)`.
- `pontoNoCircuito(circ, f, altura)`: ponto para câmera e rótulos. `revelarCircuito(circ, k)`: o traçado sendo desenhado.
  `destacarTrecho(w, circ, de, ate, k, cor, largura = 40)`: acende um trecho (S do Senna, miolo, subida).
- `numerarCurvas(w, circ, k, { destaque, tam })`: as curvas numeradas (posição real de cada uma), número num círculo ligado
  por uma linha à curva; entram uma a uma com k. Use na vista do alto quando a fala citar as curvas ("15 curvas").
- Câmera do alto: `enquadrar(w, circ, [0.1, 1, 0.25], 1.08, 40)`. Perseguição: atrás do carro a ~12 m, olhando à frente.
- **Las Vegas** (GP de Las Vegas, circuito de rua, 6,201 km, ANTI-HORÁRIO, 17 curvas): `obj(w, "circ:lv", () =>
  criarCircuito("lasvegas", { cenario: true }))` de dia; à noite `obj(w, "circ:lvn", () => criarCircuito("lasvegas", {
  cenario: true, noite: true }))` com `clima: "noite"` (janelas acesas, rua iluminada desenhando o traçado, Sphere e roda-gigante
  com brilho). Escolha UMA das duas chaves por trecho do vídeo (é o mesmo objeto em todos os planos). f 0 = linha de chegada,
  na reta dos boxes (Grand Prix Plaza, boxes à esquerda = por dentro); a largada fica ~92 m antes dela (F1.com). Curvas (f):
  1 0,044 (grampo); 2 0,060; 3 0,091; 4 0,111; Koval Lane 0,111–0,249 (reta para o norte); 5 0,249 (direita 90°); volta da Sphere
  6 0,294, 7 0,330, 8 0,340, 9 0,362; Sands Avenue 0,362–0,52 (10 0,441 e 11 0,484 rápidas); 12 0,521 (esquerda lenta para a
  Strip); Las Vegas Strip 0,52–0,832 (13 0,643, de pé embaixo; Bellagio, Caesars, Paris, Cosmopolitan ao lado); 14 0,832,
  15 0,843, 16 0,853 (sequência lenta no Planet Hollywood); Harmon Avenue 0,853–0,974; 17 0,974 (esquerda rápida para a reta
  dos boxes). `nomearTrechos` e `numerarCurvas` já usam os de Las Vegas. Anti-horário: a esquerda do carro é o lado de dentro.
  Cenário: prédios reais (contorno e altura do OpenStreetMap), lago do Bellagio, pit lane, Sphere, roda-gigante High Roller,
  réplica da Torre Eiffel do Paris, muro de concreto com placas e alambrado colado na pista, poucas arquibancadas (posição
  aproximada). Sem marcas nem telões. Desde 2026-11-12 (pedido do Felipe: "parecia deserto de neve... é Las Vegas!"): chão de
  dia em tons de asfalto/terreno, postes de luz dos dois lados da pista, palmeiras e letreiros de neon coloridos (sem texto
  nem marca) fora dos prédios; a Sphere é uma tela escura com o LOGO DO CANAL em disco (recorte circular, aro vermelho) nas
  quatro faces (`modelos/logo_canal.ts`).
  **Noite em NEON é o padrão de `"circ:lvn"` (2026-11-21, pedido do Felipe: "muito escuro e sem vida")**: basta a mesma linha
  `obj(w, "circ:lvn", () => criarCircuito("lasvegas", { cenario: true, noite: true }))` com `clima: "noite"` e a cena herda
  tudo: prédios escuros arroxeados com janelas acesas em grades variadas, arestas em neon (coroa e aro no telhado, quinas
  das torres, letreiros verticais acesos; magenta/ciano/laranja/violeta), Sphere com LED colorido em volta do logo,
  roda-gigante magenta e ciano, cones de luz e poça de luz no chão sob cada poste (realce suave; o asfalto é FOSCO, nunca
  espelho), tubo de neon magenta/ciano no alto do alambrado e na base do muro, traçado em neon rosa nas duas margens com um
  PULSO de luz percorrendo a volta, céu e névoa roxo-magenta no horizonte. Do alto (câmera acima de ~160 m, até ~1,4 km) o
  traçado inteiro acende em neon com luz andando e os quarteirões viram contornos de neon (mapa em neon, sem "blocos bege").
  No render: bloom (só no que é luz) + correção de cor (saturação, contraste, sombras arroxeadas, vinheta leve), e os carros
  em pista ganham as luzes traseiras de LED de F1 (luz de chuva vermelha no centro da traseira e as fitas de LED na borda
  de trás das placas da asa traseira, com halo; filete discreto da cor da equipe no assoalho; sem farol, sem seta).
  Tudo isso só quando esse circuito está visível no plano (`modelos/pos_neon.ts`); as outras cenas e vídeos não mudam.
  Custo medido (render por blocos, 120 quadros, concorrência 3): ~+8% por quadro nas cenas Las Vegas noturnas
  (0,158→0,172 s e 0,178→0,191 s); nas outras, nada. `neon: false` no `criarCircuito` volta ao noturno antigo (azul-marinho, sem bloom).
  O `minimapa` com `circuito: "lasvegas"` também é neon (tubo rosa com halo, luz correndo, trecho em ciano); `neon: false`
  no gráfico volta ao cinza.
- **Marcação de chão no código da cena** (faixas, linhas de pátio, sinalização): nunca rente ao piso nem fina demais. Use
  material com `polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4`, ponha a faixa ~3 cm acima do chão e
  com pelo menos 0,5 m de largura quando vista de longe (linha fina de longe "cintila"). Duas superfícies paralelas
  (moldura e painel, porta e fuselagem): afaste pelo menos alguns centímetros. Felipe viu "faixas piscando" (2026-11-12). `marcoNoCircuito(circ, chave, altura)` → ponto real de um marco para câmera e rótulo:
  sphere, high_roller, eiffel, plaza (prédio dos boxes), fontes (Bellagio), campanile, bellagio, venetian, palazzo, caesars,
  wynn, cosmopolitan, planet_hollywood, flamingo, paris, fashion_show, treasure_island, harrahs, linq.
  Câmera do alto (o traçado é comprido de norte a sul): `enquadrar(w, circ, [0, 1, 0.3], 1.05, 40)` (~3,4 km; a névoa recua sozinha).
  Sphere de perto: `const s = marcoNoCircuito(circ, "sphere"); camera(w, [s.x + 380, 190, s.z + 520], [s.x, 50, s.z], 44)`.
  O gráfico `perfil` (altitude) só existe para Interlagos.
- `obj(w, "mapa:brasil", () => criarMapaBrasil({ estado: "35", cidade: "3550308" }))`: Brasil com os estados (IBGE),
  São Paulo destacado e a cidade de São Paulo em amarelo por cima. `areaNoMapa(mapa, "pais" | "estado" | "cidade")` →
  {centro, tamanho}: para a câmera ir do país ao estado e à cidade. `pontoNoMapa(mapa, lat, lon)` funciona nele
  (Interlagos: -23,7036, -46,6997). Alfinete: escale com o tamanho da área (`pino.scale.setScalar(area.tamanho * 0.2)`).

## Destaque, brilho, aura e curva
- `destacar(w, modelo, "peça" | ["peças"], k, distancia = 0.05, cor)`: a peça SAI do modelo para a frente, cresce um
  pouco e ganha brilho atrás; o resto fica normal. É ASSIM que se destaca um comando do volante (nunca isolar/raio-X,
  que deixam o volante transparente). Com título no alto, mostre o volante inteiro e destaque o comando.
- **Destacar uma peça = a PRÓPRIA peça acende (2026-11-18, pedido do Felipe: "ao invés de uma luz em cima da peça, a
  peça poderia emitir um brilho").** `realcar(modelo, "peça" | ["peças"] | null, k, cor = "#ffd23f", contorno = 0.012)`:
  material emissivo + contorno luminoso na própria peça, volta ao normal no quadro seguinte. Nomes de peça do carro:
  `halo` (ou só `halo_arco` / `halo_pilar`), `retrovisor_esquerdo`, `retrovisor_direito`, `banco`, `apoio_cabeca`,
  `borda_cockpit` (contorno da abertura); `null` = o modelo inteiro (ex.: `realcar(p.userData.volante, null, k)`; outro
  carro: `realcar(w.carros[k], null, k, "#ffb020", 0)`). Para o resto em vidro, `raioX`/`isolar` nas OUTRAS peças
  (banco, apoio e retrovisores são peças próprias, não somem com o raioX do monocoque/sidepods). Rótulo curto preso à
  peça (`rotulo`) e câmera nela. **Nunca** `brilho` (bola de luz) como destaque de peça, e nunca acrescente outro
  retrovisor: o carro já tem os dois (em ±0,56, 0,76, -0,42 no espaço do carro).
- **Campo de visão (2026-11-18: "feixe de bolinhas amarelas ridículo"):** `campoDeVisao(w, "chave", origem, para, graus,
  alcance, k, { cor, chao, texto, volume })`: leque translúcido com degradê, bordas e arco luminosos e o volume do olhar
  (pirâmide de vidro do olho até o arco); `chao: 0.05` projeta no chão com a linha-guia descendo do olho. Olhos do piloto
  no carro: `[0, 0.74, -0.215]` (COCKPIT.olhos); espelho: `[±0.56, 0.76, -0.42]`, apontando para trás. Leia melhor visto
  de cima/3-4 (câmera a 9–12 m de altura); de trás e baixo ele vira uma parede. Nunca `fluxo` de pontinhos para visão.
- `brilho(w, "chave", posição, tamanho, k, cor)`: luz num ponto do espaço (efeito de luz, não destaque de peça: ex.:
  a força de frenagem andando do eixo dianteiro ao traseiro, `car.localToWorld(new THREE.Vector3(0, 0.35, z))`).
- `aura(w, modelo, c.t, k, cor = "#3d9bff")`: aura elétrica pulsando e faíscas em volta (ex.: carro no Boost).
- `criarCurva({ raio, largura, angulo, rotulos })` (dentro de `obj`) + `naCurva(curva, f)` → {x, z, giro}: o carro faz a
  curva de verdade (`poe(w, k, q.x, q.z, q.giro); estercar(w.carros[k], q.esterco)`; f 0 entrada, 0,5 meio, 1 saída).
- `estercar(carro, angulo)`: vira as rodas dianteiras (positivo = esquerda). Carro em curva sempre com as rodas viradas.
  Carro andando com `naCurva`/`poe`: chame também `rolarRodas` (todas as 4 rodas giram em carro em movimento).
- `embaralhar(volante, k, semente)`: os botões trocam de lugar (só no quadro; "cada equipe tem seu layout").
- A abertura (primeiros ~15 s) nunca fica parada: troca de plano, comando sendo usado, tela mudando, peça saltando.

## Ligações (ícone preso à peça)
`ligar(w, modelo, [{peca: "botao_radio", icone: "radio", desvio: [-0.06, 0.05]}, ...], k, tam = 0.06)`: ícone num círculo,
ligado por uma linha fina à peça (nomes de peça do modelo). `desvio` = para onde o ícone vai no plano do modelo, em metros
(o volante tem ~0,29 m de largura); `k` 0 a 1 = entrada (anime com `suave`). Bom para "é um painel de controle" (vários
ícones em volta do volante) ou para apontar o comando citado. No máximo 5 ícones.

## Desmonte (mostrar como uma peça funciona)
A peça que faz o trabalho se abre: vale mais que dez voltas de câmera. Tudo volta ao normal no quadro seguinte (chame a
cada quadro). Funciona no carro (`w.carros[k]`) e em todo modelo com peças marcadas; `nomesDasPecas(modelo)` lista os nomes.
- `explodir(modelo, k, distancia = 1)`: k 0 = montado, 1 = aberto; as peças de fora saem primeiro (anime k com `suave`).
- `isolar(modelo, "nome" | ["nomes"], k = 1)`: só as peças citadas ficam inteiras; o resto vira fantasma.
- `raioX(modelo, "nome" | ["nomes"], k = 1)`: as peças citadas (a casca) viram vidro.
- `cortar(modelo, [nx, ny, nz], [x, y, z])`: some tudo do lado para onde a normal aponta (no espaço do modelo).
Peças do carro: asa_dianteira, asa_traseira, halo, tampa_do_motor, monocoque, assoalho, suspensao, sidepod_esquerda,
sidepod_direita, roda_dianteira_esquerda, roda_dianteira_direita, roda_traseira_esquerda, roda_traseira_direita.
Exemplo: `explodir(w.carros[12], suave(c.t, c.m("pecas", 0.2), c.m("pecas", 0.2) + 1.2)); enquadrar(w, w.carros[12], [0.8, 0.6, -0.9], 1.1);`

## Efeitos
`confete(w, t, inicio, x, altura)`, `fumaca(w, t, x, z)`, `bandeira(w, n, x, z, giroY, t, escala)` (n: 0 verde,
1 amarela, 2 azul, 3 vermelha, 4 preta, 5 quadriculada), `luzGantry(w, n, acesa)` (n = 0 a 4, pórtico em Z_PORTICO = -111,
mostre `w.portico.visible = true`), `luzesDesfocadas(w, t)` (bokeh no estúdio), `poePneu(w, n, x, y, z, cor, giro, frenteY, esc)` (cor = nome do composto ou cor; giro 0 = PIRELLI no topo; **`frenteY = Math.PI/2` vira a LATERAL (marca, cor do composto, raios) para uma câmera em +z; com 0 o pneu fica de lado, só o piso aparece**. O pneu real tem ~1,65 m de diâmetro por unidade de `esc` (NÃO 1,03: com esc 0,6 e espaçamento 0,86 eles se atravessam). Vertical (tela estreita), três lado a lado SEM se tocar: `esc` 0,44, x -0,88/0/0,88, y 0,37, câmera [0.1, 0.5, 8.6] olhando [0, 0.2, 0] (conferido 2026-11-16: macio à esquerda, médio no meio, duro à direita; espaçamento mínimo = 1,9 × esc),
`solta(w, n, (i) => ({ p: [x, y, z], e: escala, cor, o: opacidade }))` (partículas), `seed(i)`, `THREE`.

## Exemplos
Piloto da Mercedes comemorando no alto do pódio (set livre, clima claro, marca "campeao"):
```
const w = c.w;
const pod = obj(w, "podio", () => criarPodio());
pod.position.set(0, 0, 0);
pod.updateMatrixWorld();
const kimi = obj(w, "piloto:kimi:bone", () => criarPiloto({ equipe: "mercedes", traje: "bone" }));
kimi.position.copy(topoDoPodio(pod, 1));
const sobe = suave(c.t, c.m("campeao", 0.3), c.m("campeao", 0.3) + 0.6);
bracos(kimi, sobe, sobe);
if (c.t >= c.m("campeao", 0.3)) confete(w, c.t, c.m("campeao", 0.3), 0, 6);
camera(w, [Math.sin(c.s * 0.3) * 2, 2.4 - c.k * 0.6, 7.5 - c.k * 2], [0, 1.7, 0], 34);
```
Itália com Bolonha (set livre, clima claro): a câmera desce do país inteiro até a cidade:
```
const w = c.w;
const m = obj(w, "mapa:ITA", () => criarMapa("ITA"));
m.updateMatrixWorld();
const b = pontoNoMapa(m, 44.49, 11.34);
obj(w, "pino:bolonha", () => criarAlfinete("BOLONHA")).position.copy(b);
const z = suave(c.t, c.ini + 0.4, c.ini + c.fim * 0.8);
camera(w, [b.x * z, 30 - z * 20, 9 - z * 2 + b.z * z], [b.x * z, 0, b.z * z], 40);
```
Carro 12 com número, câmera baixa acompanhando (set pista, clima tarde):
```
const w = c.w;
numeroNoCarro(w, 12, "12");
const z = -200 - 70 * c.s;
poe(w, 12, 0, z);
camera(w, [3.5 - c.s * 0.6, 0.9, z + 6 - c.s], [0, 0.6, z], 38);
```
