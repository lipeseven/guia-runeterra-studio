# API das cenas do horizontal (lida pelo diretor)

A tela tem 1920×1080 e as coordenadas são em pixels. Cada cena começa no trecho `em`, que é uma cópia exata de 2 a 6
palavras do roteiro, e vai até a próxima cena. Todo sub-item com `em` entra naquela palavra. A palavra gigante aparece
~0,25 s depois de falada e as anotações ~0,4 s depois.

A montagem impõe variedade: câmera, ângulo, lado do carro, entrada da palavra e posição da nota não repetem as cenas
anteriores. Varie você também: só a sua escolha de câmera que não repete é mantida.

## Duração das cenas
- `estudio` dura 3–8 s. Dentro dele, a tela muda por anotação, rótulo ou contador a cada 2–3 s, e não por corte.
- Quem tem cortes curtos (1–2 s) é a rajada, no máximo 3 seguidas e só em lista ou impacto.
- `pista` (respiro) dura 5–15 s, depois de cada bloco denso de 30–60 s.
- A palavra-chave deve estar no começo da fala da cena. Se a palavra vem no fim da frase, comece a cena nela.

## Cena (campos comuns)
- `em`: o trecho exato do roteiro onde a cena começa.
- `tipo`: `estudio` | `pista` | `pessoa` | `capitulo` | `solta`.
- `entrada`: `{ "tipo": "corte" }`, `{ "tipo": "empurrar", "dir": "esq" | "dir" | "cima" | "baixo" }`, `{ "tipo": "glitch" }`,
  `{ "tipo": "cortina" }` ou `{ "tipo": "cor", "cor"?: "#hex" }`.
  - A cada 16 trocas, a mistura alvo é 3–4 cortes, 3–4 empurrões, 3–4 câmeras contínuas (a mesma cena segue), 1 cor e
    0–1 glitch ou cortina.
- `som`: `{ "o_que": "whoosh rápido" | "pop curto" | "alerta" | "clique", "em": "trecho" }`.
  - Só em momento-chave. No máximo um a cada ~12 s.
  - Nunca som de motor.

## estudio
Carro oficial 3D no estúdio, com a palavra gigante ATRÁS dele.
- `modo`:
  - `claro`: análise, pessoas, opinião. É o padrão.
  - `cheio`: fundo na cor de destaque e palavra branca, para a virada de argumento.
  - `escuro`: respiro dramático.
  - `tecnico`: carro em planta (só as arestas) sobre grade escura, para dados e mecânica.
- `camera`: `{ "tipo", "de"?: graus de onde a câmera começa, "vel"?: rad/s da órbita (padrão 0,066), "sentido"?: 1 | -1,
  "enquadre"?: "esquerda" | "centro" | "direita" (lado da tela onde fica o carro), "alvo"? (só no `detalhe`) }`.
  - `de`: positivo = frente do carro para a esquerda da tela; negativo = para a direita; ~145–200 = de trás.
  - `orbita`: gira devagar.
  - `aproximar`: push-in.
  - `deslizar`: o carro anda de lado na tela.
  - `chegada`: o carro entra rodando e para (abertura de bloco).
  - `frente` / `traseira`: mais perto, de frente ou de trás.
  - `perfil`: de lado puro.
  - `cima`: vista de cima.
  - `baixo`: câmera rente ao chão, carro "herói".
  - `detalhe`: close de uma peça. `alvo`: `asa_dianteira` | `roda_dianteira` | `cockpit` | `asa_traseira` | `roda_traseira`.
  - `passagem`: o carro cruza a tela com rastro, em 1–2 s.
- Onde fica o carro na tela:
  - `orbita` / `chegada` / `deslizar`: x 240–1560, y 380–760.
  - `frente`: x 0–1650, y 260–760.
  - A palavra gigante ocupa y 120–560 e o carro tapa a parte de baixo dela.
  - Livres para anotação: canto de cima à direita (x 1300–1850, y 150–350), embaixo à esquerda (x 100–600,
    y 800–1000) e embaixo à direita (x 1300–1850, y 800–1000).

## pista
Respiro em Interlagos (pista real, carros apoiados no asfalto).
- `carros`: `[{ "u0": fração da volta onde começa (0 = linha de chegada), "km": velocidade, "lado"?: metros da linha
  central (+ = direita), "ladoAte"?: { "valor", "de", "ate" } }]`. É um carro por item; até 4.
  - S do Senna: u0 0,03–0,10. Reta oposta: 0,15–0,30. Miolo: 0,38–0,75. Junção: 0,78–0,84. Subida dos boxes: 0,84–0,99.
- `camera`: `{ "tipo": "helicoptero" | "drone" | "lado" | "passagem" | "pov", "alvo"?: índice do carro }`.
  - `passagem`: câmera parada, o carro passa com rastro.
  - `pov`: o olho do piloto.

## pessoa
É a primeira menção de uma pessoa.
- Campos: `nome`, `cargo`?, `foto`? (arquivo livre já no acervo; sem foto = silhueta), `lado`? (`esq` | `dir`).
- `citacao`?: só se a FALA do roteiro cita a pessoa. Use exatamente o trecho falado; as palavras aparecem junto da voz.
- Nunca invente citação.

## capitulo
`n`, `titulo` (curto), `circuito`? (`interlagos`). Dura 3–5 s e entra ANTES da fala da seção, com `entrada` `cor`.

## solta
`texto` (1 palavra), `modo`? (`escuro` | `cheio`), `sub`? (2–4 palavras). É para momento dramático, 2–3 s.

## Sobreposições (em estudio e pista)
- `palavra`: `{ "texto": 1–3 palavras-chave, "em": "trecho", "ate"?: "trecho", "tam"?: 300–520, "topo"?: px }`.
  - A palavra sai do roteiro e nunca é a frase inteira.
  - `entrada`?: `decodificar` (letras embaralhadas assentando) | `subir` | `impacto` | `deslizar` | `letras` | `digitar` |
    `seco`. `contorno`?: só o traço da letra.
  - Na pista, use `topo` 60 e `tam` 300.
- `anotacoes`: até 3 por cena, à mão, e não em toda cena (uma a cada 2–3 cenas). Elas comentam a fala sem repeti-la.
  A posição e o jeito da letra de `nota` e `corrigido` são decididos na montagem, conforme o lado do carro. Tipos:
  - `{ "tipo": "nota", "texto": "Por quê?", "x", "y", "tam"?: 54, "giro"?: -4, "largura"?, "em" }`
  - `{ "tipo": "seta", "de": [x, y], "para": [x, y], "curva"?: -0,3–0,3, "em" }`: aponta da nota para o assunto.
  - `{ "tipo": "circulo", "centro": [x, y], "rx", "ry", "em" }`
  - `{ "tipo": "sublinhado" | "riscado", "de": [x, y], "para": [x, y], "em" }`
  - `{ "tipo": "chave", "de": [x, y], "para": [x, y], "em" }`: chave vertical.
  - `{ "tipo": "corrigido", "antes": "+0.15s", "depois": "+0.015s", "x", "y", "em" }`: número corrigido à mão.
  - `{ "tipo": "caixa", "centro": [x, y], "w", "h", "em" }`: retângulo à mão em volta de algo.
  - `{ "tipo": "x" | "check", "centro": [x, y], "tam"?, "em" }`
  - `{ "tipo": "marca", "de": [x, y], "para": [x, y], "altura"?, "em" }`: marca-texto passado por cima.
  - Todo tipo aceita `cor`?.
- `contador`: `{ "valor", "unidade"?, "rotulo"?, "de"?, "casas"?, "x"?, "y"?, "em" }`. O número sobe até o valor falado.
  O padrão é o canto de cima à esquerda.
- `rotulos`: `[{ "texto", "de": [x, y] (ponto no objeto), "para": [x, y] (onde fica o texto), "em" }]`.

## Exemplo
```json
{"cenas": [
 {"em": "A Ferrari chegou a", "tipo": "estudio", "camera": {"tipo": "chegada"},
  "palavra": {"texto": "FERRARI", "em": "Ferrari"},
  "anotacoes": [{"tipo": "nota", "texto": "de novo?", "x": 1320, "y": 220, "em": "chegou"}]},
 {"em": "mas o carro novo", "tipo": "estudio", "entrada": {"tipo": "empurrar", "dir": "esq"}, "camera": {"tipo": "frente", "de": 30},
  "palavra": {"texto": "ASA", "em": "asa"}, "som": {"o_que": "whoosh rápido", "em": "mas o carro"}},
 {"em": "na primeira volta", "tipo": "pista", "camera": {"tipo": "helicoptero"},
  "carros": [{"u0": 0.034, "km": 262}, {"u0": 0.04, "km": 250, "lado": 0.4}]}
]}
```
