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
- `som` (opcional): {"o_que": "descrição curta EM INGLÊS do som", "em": "trecho exato"}. Só quando o som faz sentido
  na fala: clique de botão apertado ou seletor girando ("single button click", "rotary knob clicks"), bipe de rádio
  ("radio beep static"), carro passando ou acelerando ("race car pass by", "race car accelerating"), whoosh de troca
  rápida. Raro: no máximo 1 a cada ~7 s (o motor corta o excesso, mínimo de 3 s entre eles); nunca música.
- Sobreposições (placas, contador, chips, selo, riscado, medidor, gota, chuva): campos do JSON, como no catálogo. Nunca
  desenhe texto de tela no código; rótulo 3D (`rotulo`) só para nomear coisas dentro da cena.

## O que o código recebe
`c`: `c.w` (mundo), `c.t` (segundo do vídeo), `c.s` (segundos desde o início do plano), `c.k` (0 a 1 ao longo do plano),
`c.fim` (duração do plano), `c.ini` (segundo em que o plano começa), `c.m(nome, frac)` (segundo de uma marca; sem a marca,
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

## Unidades e direções
Metros. y = altura. Carros andam para -z (câmera em +z atrás vê a traseira). Pessoas, pódio e escada olham para +z
(câmera em +z vê de frente). Carro (molde de 2026): 5,4 m de comprimento, 1,9 m de largura, eixos em z = -1,55 e 1,85; piloto: 1,75 m; kart: 1,8 m.

## Carros de F1 (já existem, 22)
`poe(w, k, x, z, giro = 0)`: mostra o carro k (0 a 21) em (x, 0, z). Equipe = k/2 arredondado para baixo; pintura da
equipe e: 0 vermelho, 1 laranja, 2 verde-água, 3 azul, 4 roxo, 5 amarelo, 6 Mercedes (preto e prata, linha verde Petronas), 7 preto e
verde-limão, 8 preto e dourado (Cadillac), 9 verde, 10 branco e azul. Carros 12 e 13 = Mercedes.
`numeroNoCarro(w, k, "12")`: número no bico e nas laterais do carro k (fica nele).
`pneus(w, k, "macio")`: composto dos pneus do carro k (faixa no flanco): macio (vermelho), medio (amarelo, o padrão),
duro (branco), intermediario (verde), chuva (azul). Fica no carro até trocar de novo.
`poeCinza(w, k, x, z)`: carro cinza (eliminado). `grade(w, n, dz)`: n carros no grid de largada (pole em z = Z_POLE = -100;
`gridX(k)`, `gridZ(k)` = lugar k no grid). `halo(w, n, x, z, cor, opacidade)`: auréola de luz no chão (n = 0 a 21).
Outro carro com pintura própria: `obj(w, "carro:ferrari", () => carro({ base, clara, escura, faixa, acento }))` (cores
hex; devolve o objeto: posicione com `.position.set(x, 0, z)`).

## Modelos (criados uma vez por chave; a aparência é fixa na chave)
`obj(w, chave, () => criarX(...))` cria na primeira vez e mostra o objeto neste quadro; devolve o objeto THREE (posicione
com `.position.set`, `.rotation.y`, `.scale.setScalar`). Chave diferente = outro objeto (ex.: "piloto:kimi:bone").
- `criarPiloto({ equipe, macacao, detalhe, faixa, bone, logo, capacete, pele, cabelo, traje, crianca, sentado })`:
  pessoa (sem olhos e boca) vestindo macacão. `equipe: "mercedes"` usa as cores conferidas da equipe (macacão preto, detalhes
  prata e verde Petronas, boné preto). Outra equipe: passe macacao/detalhe/faixa/bone/logo em hex, SÓ com cores que o
  briefing ou a folha de estilos confirmem. pele: "clara" | "media" | "morena" | "negra"; cabelo: "castanho" | "preto" |
  "loiro" | "ruivo" | "grisalho"; traje: "capacete" (no carro, correndo) | "bone" (pódio, entrevista, box, fora do carro);
  crianca: true (72%). `bracos(piloto, esq, dir)`: 0 abaixado, 1 erguido (comemoração = 1, 1).
- `criarKart({ cor, faixa, numero, piloto: {cor, faixa, pele} | false })`: kart com piloto criança sentado (frente -z).
- `criarPodio({ cor })`: pódio 2-1-3; `topoDoPodio(podio, 1|2|3)` = ponto em cima do degrau (para pôr o piloto).
- `criarEscada(["F4", "REGIONAL", "F3", "F2", "F1"], { pulados: [2], passo: 2.6 })`: escada subindo para +x, rótulo
  em cada degrau, pulados = degrau vazado e cinza; `degrau(escada, i)` = ponto em cima do degrau i.
- `criarMapa("ITA", { tamanho: 20, cor, vizinhos: true })`: mapa real do país (código ISO de 3 letras: ITA, BRA, MEX,
  GBR, DEU, ESP, FRA, MCO, NLD, AUS, JPN, USA, ARE, SAU…), deitado no chão (norte para -z), maior lado = tamanho, centro
  na origem. `pontoNoMapa(mapa, lat, lon)` = posição da cidade em cima do mapa. Use `set: "livre"` e câmera de cima
  (`camera(w, [0, 30, 9], [0, 0, 0], 40)` enquadra um mapa de 20 m). Chame `mapa.updateMatrixWorld()` depois de mover.
- `criarAlfinete("BOLONHA", cor)`: alfinete com rótulo; `.position.copy(pontoNoMapa(mapa, 44.49, 11.34))`.
- `rotulo("TEXTO", { altura, cor, fundo })`: placa 3D que olha para a câmera (dentro de `obj`).
- Também prontos no mundo: `w.trofeu` (troféu dourado: `.visible = true` e posição), `w.sc` (Safety Car).

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
mostre `w.portico.visible = true`), `luzesDesfocadas(w, t)` (bokeh no estúdio), `poePneu(w, n, x, y, z, cor, giro, frenteY)`,
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
