# kit/cartoes: cartões de pessoa e de capítulo e tag ancorada na pista (independente de motor)

Três peças editoriais do horizontal. O kit faz todo o layout **sem navegador** e devolve, para cada tempo, o SVG de cada
cartão. Remotion e HyperFrames só colocam esse SVG por cima da cena.
- **Pessoa**: foto P&B, nome e função. É um cartão branco com barra na cor de destaque, no terço inferior.
- **Capítulo**: "PARTE 0N", título e, se houver, o traçado do circuito se desenhando. Ocupa a tela cheia, com fundo claro.
- **Tag**: ponto, perninha e etiqueta branca. Fica ancorada numa posição da pista, fixa ou vinda de uma trilha
  (por exemplo, a projeção do carro a cada quadro), e acompanha o ponto.

O texto entra **seco**, sem letra a letra e sem decodificação. O cartão aparece com um fade curto e um deslize pequeno
(40 px na pessoa, 18 px no título). Isso segue o feedback de texto sem animação exagerada.

Serve para qualquer vídeo. Nomes, funções, fotos, títulos, traçado, cor, posição e trilha vêm por parâmetro, e não há
nada fixo de pista, piloto ou equipe. O "Leclerc" e a pista da cena de teste são só exemplo, e a cor padrão (`#e10600`)
deve ser trocada pela cor da equipe ou do tema.

## Arquivos
| Arquivo | O que é |
|---|---|
| `cartoes.ts` | núcleo: `montarCartoes`, `estadoCartoes`, `svgCartoes`, `checarCartoes`, `ancoraTag`, `geometriaTag`, `larguraTexto` |
| `larguras.ts` | avanço de cada caractere (PT-BR) da Bahnschrift em 3 estilos. **Gerado** por `gerar_larguras.py` (PIL) |
| `cartoes.global.js` | IIFE `window.Cartoes` para o HyperFrames. **Gerado** por `testes/cartoes/rodar.py` |
| `testes.ts` | teste automático sem motor |
| `exemplo/cena.json`, `gerar_cena.py`, `foto_exemplo.jpg` | cena de teste de 7 s. A foto é um **retrato sintético**, não é foto de pessoa real |

Adaptadores: `F1/horizontal/remotion/cartoes/CamadaCartoes.tsx` e `F1/horizontal/hyperframes/cartoes/camada.js`, com
`exemplo/`. Folhas e medidas: `F1/horizontal/testes/cartoes/`.

## API
```ts
import { montarCartoes, svgCartoes, checarCartoes } from "F1/horizontal/kit/cartoes/cartoes.ts";
const m = montarCartoes({ largura: 1920, altura: 1080, fps: 60, duracao: 7, margem: 48, cartoes: [
  { tipo: "pessoa", id: "p", em: 1.2, ate: 3.6, nome: "…", funcao: "…", foto: url, fotoTam: [480, 600], fotoFoco: [0.5, 0.36], lado: "esquerda", cor },
  { tipo: "capitulo", id: "c", em: 4, ate: 6.9, numero: 2, titulo: "…", tracado: { d, largura, altura }, cor, fundo },
  { tipo: "tag", id: "t", em: 0.8, ate: 3.6, texto: "…", ancora: [x, y] /* ou [{t, x, y}, …] */, lado: "auto", perna: 110, cor },
] });
svgCartoes(m, t)      // SVG (grupos <g>) de tudo que está ativo em t: o que os dois motores desenham
estadoCartoes(m, t)   // [{ id, tipo, opacidade, caixa, textos, tag: { ancora, ponta, caixa, lado }, svg }]
checarCartoes(m)      // { falhas, avisos, porCartao: { folgaMinQuadro, lados, textoForaDoCartao, pernaErroMax } }
```
- **Largura do texto sem navegador.** `larguras.ts` guarda o avanço de cada glifo. Os motores desenham com
  `font-kerning: none`, e o kit soma 0,5% de folga, porque o hinting do Chrome chega a ~0,3% a mais em corpo grande.
  - Estilos: `forte` = Bahnschrift Bold SemiCondensed (nomes, títulos, PARTE), `medio` = SemiBold (tag) e
    `normal` = Regular (função).
  - O Chrome **não aplica** o eixo `wdth` 75 (Condensed) na Bahnschrift do sistema. Ele só chega à instância
    SemiCondensed (87,5), e isso foi medido. Por isso o "forte" é SemiCondensed.
- **Pessoa.** O nome encolhe até caber em 1100 px de cartão. A foto usa recorte "cover" calculado no kit, com o rosto
  em `fotoFoco`. Sem foto, entra uma silhueta.
- **Capítulo.** O título fica numa linha até corpo 110. Se não couber, vira duas linhas equilibradas e cabe na área útil
  (160 px de cada lado). O traçado é desenhado com `stroke-dashoffset` em 1,3 s.
- **Tag.** O lado `auto` é o 1º entre ne, no, se e so em que a etiqueta fica dentro da margem segura (48 px) **durante o
  intervalo inteiro**. Assim a tag não troca de lado no meio. Se nenhum lado couber (um carro que cruza o quadro
  inteiro, por exemplo), a etiqueta é empurrada para dentro quadro a quadro, com um aviso. A perninha sempre vai do
  ponto à borda mais próxima da etiqueta.

## Verificação (2026-11-13)
`node F1/horizontal/kit/cartoes/testes.ts`: 1017 checagens, 0 falhas. Em 421 quadros, nada sai do quadro ou da margem,
o texto fica dentro do cartão e a perninha termina na borda, com erro de 0 px. Também confere:
- a tag presa ao carro que chega a x ≈ 1810 escolhe "no" e não troca de lado;
- a tag impossível é empurrada e nunca sai do quadro;
- o título longo quebra em 2 linhas equilibradas;
- a opacidade é 0 fora do intervalo, com salto de no máximo 0,2 por quadro.

`.venv\Scripts\python.exe F1\horizontal\testes\cartoes\rodar.py` renderiza nos dois motores e mede nos pixels:

| | Remotion | HyperFrames |
|---|---|---|
| etiquetas (branco) × caixa do kit | erro 0,85 px | 0,85 px |
| quadros com etiqueta fora da margem de 48 px | 0 | 0 |
| tinta do texto do cartão de pessoa fora da caixa do kit | 0 px | 0 px |
| largura do nome: medida × tabela | 327 × 330,6 px | 327 × 330,6 px |
| tinta do título do capítulo fora da caixa / fora da área útil | 0 px / 0 | 0 px / 0 |

Remotion × HyperFrames: diferença média de 0,000 de 255.

Folhas: `testes/cartoes/folha_<motor>_tag_60qs.jpg`, `_pessoa_60qs.jpg` e `_cena.jpg`.

## O que NÃO foi verificado
- **O Felipe ainda não viu.** As folhas foram olhadas aqui: a tag acompanha o carro, a perninha liga, a pessoa entra
  seca e o capítulo tem o traçado se desenhando. O tamanho dos textos (nome 54, função 30, tag 32) e o estilo ainda
  dependem do gosto dele.
- A foto do exemplo é sintética. Uma foto real (Wikimedia, P&B) não foi testada, e o crédito da foto fica com quem a
  escolher (FONTES).
- Texto em várias linhas só existe no título (2 linhas). Nome e função muito longos encolhem e não quebram.
- O cartão de pessoa não tem a citação palavra a palavra do v1 (`F1/video/src/horizontal/cartoes.tsx`).
- A tabela de larguras depende da Bahnschrift do Windows. Em outro sistema (Docker/Linux) a fonte muda e é preciso
  regerar a tabela e embutir a fonte.
