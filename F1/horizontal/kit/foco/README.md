# kit/foco: foco de profundidade do horizontal (independente de motor)

Resolve o apontamento do Felipe no teste Remotion: faltou blur de foco ao destacar uma peça. Ao falar da asa traseira, o
resto da cena desfoca e escurece de leve, e a asa continua nítida. O kit calcula tudo: a janela nítida, a força do
efeito e a máscara. O motor só põe uma `<div>` com `backdrop-filter` por cima da cena.

Serve para qualquer vídeo. A peça, as caixas, a trilha, a cor do véu e os tempos vêm por parâmetro, e não há nada fixo
de pista, piloto ou equipe. O carro e a asa da cena de teste são só exemplo.

## Arquivos
| Arquivo | O que é |
|---|---|
| `foco.ts` | núcleo (sem dependências): `montarFoco`, `estadoFoco`, `estilos`, `checarFoco`, `alfaEm`, `caixaEm`, `janelaEm` |
| `foco.global.js` | o mesmo núcleo em IIFE (`window.Foco`) para o HyperFrames. **Gerado** por `testes/foco/rodar.py` (esbuild) |
| `testes.ts` | teste automático sem motor (`node testes.ts`) |
| `exemplo/cena.json` + `gerar_cena.py` | cena de teste 1920x1080, 60 q/s, 6 s: carro estilizado andando, foco na asa (caixa) e na roda (elipse) |

Adaptadores: `F1/horizontal/remotion/foco/CamadaFoco.tsx` e `F1/horizontal/hyperframes/foco/camada.js`, cada um com
`exemplo/`. Folhas e medidas: `F1/horizontal/testes/foco/`.

## Como funciona
- **Caixa estável.** É o mesmo formato do `kit/anotacao` (`alvo = { caixa, movimento: [{t, dx, dy, s}] }`). Para peça que
  gira ou peça 3D, use `caixaEnvelope` (reexportado aqui). A janela nítida é a caixa mais a `folga`, deslocada e escalada
  pela âncora em cada quadro. O tamanho não "respira".
- **Máscara em anéis.** A máscara é um SVG (alfa) que vale 1 fora da janela mais a pena e 0 dentro da janela, onde não há
  preenchimento nenhum. No meio ficam 14 anéis concêntricos (`fill-rule evenodd`) com alfa crescente (smoothstep). A pena
  fica **toda fora** da janela, então a caixa da peça sai exatamente igual à cena sem foco.
- **Uma camada por foco.** A `<div>` usa `backdrop-filter: blur(..)` e `mask-image: url(data:svg)`. Uma segunda `<div>`
  com a mesma máscara faz o véu escuro (`opacity` = `escurecer`·k). Assim o conteúdo (inclusive canvas 3D) não é
  desenhado duas vezes.
- **Entrada e saída.** A força k(t) usa smootherstep: a derivada é nula nas pontas e o desfoque não "estala". O desfoque
  é `blur`·k e o véu é `escurecer`·k. Com k = 0 o motor não desenha nada.

## API
```ts
import { montarFoco, estadoFoco, estilos, checarFoco } from "F1/horizontal/kit/foco/foco.ts";
const m = montarFoco({ largura: 1920, altura: 1080, fps: 60, duracao: 6, focos: [
  { id: "asa", em: 0.6, ate: 3.2, alvo: { caixa: {x:1390, y:484, w:154, h:148}, movimento: trilha },
    blur: 10, escurecer: 0.10, folga: 18, raio: 22, pena: 28, forma: "caixa" /* ou "elipse" */, entrada: 0.45, saida: 0.35 } ] });
estadoFoco(m, t)   // [{ id, k, blur, veu, caixa, janela, mascara, mascaraUrl }]  (só os focos ativos)
estilos(e)         // { camada: CSS do desfoque, veu: CSS do véu }, iguais nos dois motores
checarFoco(m)      // { falhas, focos: { quadrosAtivos, kMax, saltoMaxK, pontosDentro, pontosFora, erroJanelaPx } }
```
- No Remotion, `<CamadaFoco montada={m} />` vai **depois** da cena a desfocar e **antes** de legendas e anotações que
  devem continuar nítidas.
- No HyperFrames, `CamadaFoco.criar(divPorCima, Foco.montarFoco(cena)).render(t)` vai no `onUpdate` da timeline.
- Padrões: `blur` 10 px, `escurecer` 0,10 (leve, porque o fundo claro é a assinatura), `folga` 18, `raio` 22, `pena` 28,
  `entrada` 0,45 s e `saida` 0,35 s. Se o intervalo for curto, a entrada e a saída encolhem na proporção.

## Verificação (2026-11-13)
`node F1/horizontal/kit/foco/testes.ts`: 30 checagens, 0 falhas em 361 quadros. Confere:
- k = 0 fora do intervalo e 1 no patamar, com salto máximo de 0,089 por quadro;
- a janela é a caixa mais a folga, com erro de 0 px;
- o alfa é 0 em 10 309 pontos da caixa e 1 depois da pena em 1 464 raios, sem diminuir ao sair;
- a máscara SVG tem o contorno interno igual à janela;
- a elipse cobre os cantos;
- um intervalo curto não passa do tempo.

`.venv\Scripts\python.exe F1\horizontal\testes\foco\rodar.py` renderiza a cena **com e sem** foco nos dois motores
(Remotion 4.0.539, HyperFrames 0.9.20 por `npx`) e compara os pixels:

| | Remotion | HyperFrames |
|---|---|---|
| diferença máxima dentro da caixa da peça (com × sem foco, 286 quadros com foco, peça andando) | **0** | **0** |
| diferença máxima na janela inteira (caixa + folga) | 0 | 0 |
| nitidez das listras finas fora da janela (variância do laplaciano, com/sem, k = 1) | 0,000 | 0,000 |
| quadros sem foco (k = 0) × referência | idênticos | idênticos |
| força medida pelo véu × k do kit | erro ≤ 0,022 | ≤ 0,022 |

Remotion × HyperFrames: diferença média de 0,000 de 255.

Folhas: `testes/foco/folha_<motor>_entrada_60qs.jpg` (48 quadros seguidos com o foco entrando na asa) e `_cena.jpg`.

## O que NÃO foi verificado
- **O Felipe ainda não viu.** Nas folhas olhadas aqui o fundo desfoca suave, a asa fica nítida e a roda aparece em
  elipse. A janela (a folga) aparece **mais clara** que o resto por causa do véu. Lembra um "recorte iluminado". Se não
  agradar, use `escurecer: 0` (só desfoque) ou `folga` menor.
- O teste foi feito em cena 2D (SVG). Com canvas WebGL/three.js, o `backdrop-filter` também deve funcionar no Chrome dos
  dois motores, mas **não foi renderizado** aqui. Com peça 3D, a caixa vem de `caixaEnvelope` dos cantos projetados.
- A escala da âncora (`s`, para câmera aproximando) está implementada e testada só na geometria do kit, não em render.
- O desfoque de borda é o do `backdrop-filter` do Chrome (as bordas do quadro repetem pixels). Não foi comparado com um
  desfoque de profundidade "real" de câmera.
