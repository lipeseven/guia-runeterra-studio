# kit/transicoes: corte, fade, wipe e zoom-through medidos e sincronizados ao SFX (independente de motor)

Transições entre cenas com duração **exata em quadros** (60 q/s) e o som do `kit/sfx` ancorado no quadro de maior
movimento. O kit devolve, por quadro, o estilo de cada camada (opacidade, escala, recorte, desfoque) e a barra do wipe.
O motor só aplica esses estilos em duas `<div>` (cena que sai e cena que entra). Isso continua a troca de cena elogiada
no teste HyperFrames.

Serve para qualquer vídeo: tipos, tempos, cor da barra e SFX vêm por parâmetro.

## Arquivos
| Arquivo | O que é |
|---|---|
| `transicoes.ts` | núcleo: `montarTransicao(es)`, `progresso`, `estadoTransicao`, `estiloCamada`, `estadoSequencia`, `pedidosSfx`, `checarTransicoes` |
| `transicoes.global.js` | IIFE `window.Transicoes` para o HyperFrames. **Gerado** por `testes/transicoes/rodar.py` |
| `testes.ts` | teste automático sem motor (usa o `kit/sfx` com o catálogo real) |
| `exemplo/cena.json` + `gerar_cena.py` | 5 cenas paradas ligadas por corte (impacto) em 1 s, fade em 2 s, wipe em 3 s e zoom em 4 s (5 s) |

Adaptadores: `F1/horizontal/remotion/transicoes/SequenciaTransicoes.tsx` (o som vai pelo `TrilhaSfx` do kit/sfx) e
`F1/horizontal/hyperframes/transicoes/camada.js` (o som vai em tags `<audio>`), com `exemplo/`. Folhas e medidas:
`F1/horizontal/testes/transicoes/`.

## Tipos e durações (quadros intermediários a 60 q/s; nem cena A pura nem B pura)
| tipo | quadros | o que faz | SFX padrão (pico no quadro de pico) |
|---|---|---|---|
| `corte` | 0 | o quadro do corte já é a cena B inteira | nenhum. Com `sfx: "impacto"`, o impacto bate no 1º quadro de B |
| `fade` | 18 (0,3 s) | B por cima de A com opacidade crescente | nenhum (pode pedir `whoosh`) |
| `wipe` | 24 (0,4 s) | B revelada atrás de uma borda que anda (`direcao`), com barra de 14 px na `cor` | `whoosh` |
| `zoom` | 30 (0,5 s) | A mergulha (escala 1 → 2,4 e desfoca). B vem "de perto" (1,6 → 1) saindo do desfoque e não mostra borda | `whoosh` |

- A transição fica **centrada** no instante `em`, arredondado ao quadro: q0 = qCorte − ⌊n/2⌋. Também aceita `quadros`
  próprio. Em 30 q/s as durações viram 9, 12 e 15 quadros, o mesmo tempo.
- **Curva:** 70% smoothstep + 30% linear. Com a suave pura, o 1º e o último quadro intermediário seriam quase iguais às
  cenas puras e a transição "pareceria" mais curta do que a declarada. Assim cada quadro anda pelo menos 1%.
- **Pico:** é o quadro em que o progresso mais anda (o do meio). O `tPico` é sempre um quadro inteiro.
  `pedidosSfx(ts)` dá os pedidos para `Banco.dePedidos` do kit/sfx, que alinha o **pico** do som (`pico_s` do catálogo)
  nesse instante.

## API
```ts
import { montarTransicoes, estadoSequencia, pedidosSfx } from "F1/horizontal/kit/transicoes/transicoes.ts";
import { Banco } from "F1/horizontal/kit/sfx/sfx.ts";
const ts = montarTransicoes([{ tipo: "corte", em: 1, sfx: "impacto" }, { tipo: "fade", em: 2 }, { tipo: "wipe", em: 3, direcao: "direita", cor },
                             { tipo: "zoom", em: 4 }], 60);
estadoSequencia(ts, q)   // { itens: [{ cena, estilo }], barra }: as camadas do quadro q, de baixo para cima
const eventos = new Banco(catalogo, 0).dePedidos(pedidosSfx(ts));   // → TrilhaSfx (Remotion) / <audio> (HyperFrames)
```
- No Remotion: `<SequenciaTransicoes ts={ts} cenas={[...]} />` + `<TrilhaSfx eventos={eventos} />`.
- No HyperFrames: `CamadaTransicoes.criar(pai, [elA, elB, …], ts, 60).render(t)`. As tags `<audio>` são geradas como em
  `sfx.py/para_hyperframes`.
- Uma cena que entra deve estar **em movimento**, como diz a folha horizontal ("a cena nova já começa com a câmera em
  movimento"). Nas cenas do exemplo ficou parada de propósito, só para medir.

## Verificação (2026-11-13)
`node F1/horizontal/kit/transicoes/testes.ts`: 329 checagens, 0 falhas. Confere:
- durações [0, 18, 24, 30], com quadros intermediários contados = declarados;
- 30 q/s e duração ímpar pedida;
- a cena certa em cada quadro da sequência;
- em 3 sementes do banco, o pico de cada som cai no quadro de pico, com erro < 1 ms;
- impacto no corte e whoosh no wipe e no zoom.

`.venv\Scripts\python.exe F1\horizontal\testes\transicoes\rodar.py` renderiza PNG e MP4 com som nos dois motores e mede:

| | Remotion | HyperFrames |
|---|---|---|
| duração medida nos pixels (quadros que não são A nem B) corte / fade / wipe / zoom | 0 / 18 / 24 / 30 | 0 / 18 / 24 / 30 |
| 1º e último quadro intermediário = os do kit | sim (todos) | sim |
| quadro de maior mudança × pico do kit (fade, wipe, zoom) | +2, 0, +2 | +2, 0, +2 |
| pico do som medido no MP4 (RMS 10 ms) × quadro de pico: impacto / whoosh wipe / whoosh zoom | +7,6 / +0,9 / +4,5 ms | +0,6 / −6,1 / +7,5 ms |

Remotion × HyperFrames (todos os quadros): diferença média de 0,000 de 255. O Remotion só posiciona áudio em quadro
inteiro (até 8,3 ms de deslocamento), como já medido no kit/sfx.

Folhas: `testes/transicoes/folha_<motor>_<fade|wipe|zoom>_60qs.jpg`, com todos os quadros da transição mais 2 quadros
puros de cada lado.

## O que NÃO foi verificado
- **Ninguém assistiu nem ouviu.** O sincronismo é medido pelo pico do envelope. No `whoosh_capitulo_remotion` (whoosh
  largo), o envelope de amostra (4 ms) tem o máximo ~120 ms depois do `pico_s` do catálogo (RMS 10 ms). Se o ouvido
  sentir o golpe atrasado, ajuste o `pico_s` desse som no kit/sfx.
- Cenas em movimento e cenas 3D (canvas) não foram usadas nas transições. O `filter: blur` do zoom sobre canvas WebGL deve
  funcionar no Chrome dos dois motores, mas não foi renderizado aqui.
- No pipeline de dois motores (montador), transição entre um trecho Remotion e um trecho HyperFrames exige que os dois
  trechos tenham os quadros de sobreposição (ARQUITETURA §6). Isso não foi exercitado: aqui as duas cenas estão no mesmo
  motor.
- `glitch`, `empurrar` e `cortina` de baixo para cima e `cor` (mergulho em cor lisa) da folha horizontal v1 não entraram
  neste kit.
