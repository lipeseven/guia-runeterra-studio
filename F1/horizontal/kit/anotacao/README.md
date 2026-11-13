# kit/anotacao: anotações à mão do horizontal (independente de motor)

Oval aberto com perninha, seta, sublinhado, chave, riscado, número corrigido e texto escrito à mão (fonte Caveat traçada
em ordem de escrita, como no teste HyperFrames). A mesma conta serve ao Remotion, ao HyperFrames, ao Node e aos testes:
o kit devolve, para cada tempo `t`, os caminhos SVG e quanto de cada um já foi desenhado. O motor só desenha.

## Por que os círculos do teste Remotion pulavam, e o que muda
No teste Remotion o oval era recalculado a cada quadro a partir da **caixa projetada** da peça (os 8 cantos 3D →
tela) e ainda passava por um laço `k += 0,02`. Quando a peça girava, a caixa projetada mudava de tamanho e o oval
crescia e encolhia. Na cena de teste daqui, a caixa projetada da asa girando ±12° varia **15 × 72 px**.

No kit, a geometria de cada anotação é calculada **uma vez**, a partir de uma **caixa estável** (tamanho fixo). Com o
tempo, a âncora só **desloca** (`movimento`: dx, dy) e, se a cena pedir, escala de forma suave (`s`). Para peça que gira
ou peça 3D, `caixaEnvelope(amostras)` dá a caixa estável: o maior meio-tamanho em volta do pivô em todo o intervalo.
O pivô projetado (um ponto, que não "respira") vira o `movimento`.

## Arquivos
| Arquivo | O que é |
|---|---|
| `anotacao.ts` | núcleo (sem dependências): `montar`, `estado`, `checar`, `caixaEnvelope`, `ancoraEm`, `montarTexto`, formas |
| `anotacao.global.js` | o mesmo núcleo em IIFE (`window.Anotacao`) para o HyperFrames. **Gerado** por `testes/anotacao/rodar.py` (esbuild) |
| `fonte/caveat_traco.json` | linhas centrais, contornos e espessura dos 75 glifos da Caveat 700 (ver Licenças) |
| `cli.ts` | `node cli.ts checar\|estado\|montar <cena.json> [t]` |
| `testes.ts` | teste automático sem motor (`node testes.ts`) |
| `exemplo/cena.json` + `gerar_cena.py` | cena de teste 1920x1080, 60 q/s, 7 s, usada pelos dois motores e pelos testes |

Adaptadores: `F1/horizontal/remotion/anotacao/CamadaAnotacao.tsx` e `F1/horizontal/hyperframes/anotacao/camada.js`, cada
um com `exemplo/`. Folhas e medidas de render: `F1/horizontal/testes/anotacao/`.

## Cena (formato)
```jsonc
{ "largura": 1920, "altura": 1080, "fps": 60, "duracao": 7,
  "alvos": {                        // tudo que pode ser anotado; caixas em px na pose de referência
    "asa":   { "caixa": {"x":372,"y":469,"w":375,"h":182}, "movimento": [{"t":0,"dx":0,"dy":0}, {"t":0.25,"dx":0.4,"dy":-4}] },
    "valor": { "caixa": {...}, "texto": true }   // texto: nenhuma anotação pode cruzar
  },
  "anotacoes": [
    {"id":"oval-asa", "tipo":"oval", "alvo":"asa", "em":0.4, "folga":26},
    {"id":"nota-gira", "tipo":"nota", "texto":"gira ±12°", "em":1.15, "perto":{"alvo":"oval-asa","lado":"auto","distancia":60,"desloc":[230,0]}},
    {"id":"seta-gira", "tipo":"seta", "de":"nota-gira", "para":"oval-asa", "em":2.25, "curva":-0.18},
    {"id":"sub", "tipo":"sublinhado", "alvo":"titulo", "em":2.75},
    {"id":"corr", "tipo":"corrigido", "alvo":"valor", "texto":"326", "em":3.3},
    {"id":"chave", "tipo":"chave", "alvos":["s1","s2"], "lado":"direita", "em":4.6},
    {"id":"risco", "tipo":"riscado", "alvo":"x", "em":5, "duplo":true}
  ] }
```
Campos comuns: `em` (s), `cor` (padrão `#d40000`), `espessura` (7 px), `semente` (padrão = hash do `id`), `vel` (px/s).
Um alvo pode ser outra anotação (`oval-asa`, `chave-s12`): a nota e a seta acompanham a âncora dela.

| Tipo | Forma |
|---|---|
| `oval` | elipse inclinada (−1 a −4°) com os cantos da caixa por dentro (97% do raio) + `folga`; começa em cima à esquerda, dá a volta e passa do início por **fora** (raio +6% no fim: a perninha do teste HyperFrames) |
| `seta` | haste curva com ondulação leve + ponta em V aberta (2 traços); sai da borda de `de` e para antes de `para` (`recuo`); se as âncoras se movem de forma diferente, é recalculada a cada quadro |
| `sublinhado` | linha levemente arqueada, ponta final subindo, `folga` 14 px abaixo da caixa |
| `chave` | `}` sobre a união dos `alvos`, em qualquer `lado` |
| `riscado` | traço inclinado por cima do texto; passa das pontas até 14 px, **encurtado** se houver texto vizinho na mesma faixa; `duplo` |
| `corrigido` | riscado + número novo à mão (altura de tinta = 85% do número riscado), `lado` cima/baixo/direita/esquerda |
| `nota` | texto à mão em `pos` (canto da tinta) ou `perto` de um alvo; `lado: "auto"` escolhe o primeiro lado (direita, baixo, esquerda, cima) em que a nota não cruza texto nem sai da tela em todo o movimento |

**Traço irregular determinístico:** o raio do oval ondula por 3 senoides lentas (harmônicos 2, 3 e 5; ~1,5% no total) com
fases e amplitudes tiradas da semente; as linhas ondulam ±1,3 px. Nada de sorteio por quadro nem de "boil": o desenho é
função pura do tempo (por isso não pode pular). Mesma semente → mesmo traço; outra semente → outro.
**Desenho progressivo:** `pathLength=1` + `stroke-dasharray="1 2"` + `stroke-dashoffset = 1 − k`; `k` sai da velocidade
da caneta (oval 2600 px/s, seta 2400, sublinhado/riscado 2200, chave 1800, texto 1150) com arranque e assentamento
suaves e 50 ms de caneta levantada entre traços.
**Texto à mão:** cada glifo é o contorno cheio da Caveat revelado por uma máscara feita das linhas centrais desenhadas em
ordem (técnica do bloco `hw-write-title` do HyperFrames). Acentos (´ ` ^ ~ ¨ ç) e `% ° / × ± = < >` são traços próprios do
kit. A largura vem da tabela (sem kerning), então o kit sabe a caixa do texto sem medir no navegador.

## API
```ts
import { montar, estado, checar } from "F1/horizontal/kit/anotacao/anotacao.ts";
const m = montar(cena, fonte);      // fonte = fonte/caveat_traco.json (cada motor carrega do seu jeito)
estado(m, t)   // [{ id, cor, transform, tracos:[{d, largura, k}], glifos:[{transform, outline, tracos:[{d, largura, k, tinta}]}] }]
checar(m)      // percorre todos os quadros: { falhas, ovais:{tamanho, margens, variacao...}, desenho, cruzamentos, distMinTexto }
```
Remotion: `<CamadaAnotacao montada={m} />`. HyperFrames: `CamadaAnotacao.criar(svg, Anotacao.montar(cena, fonte)).render(t)`
no `onUpdate` da timeline (monta o SVG uma vez; por quadro só troca `transform`, `stroke-dashoffset` e `opacity`).

## Verificação (2026-11-13)
`node F1/horizontal/kit/anotacao/testes.ts`: 12 checagens, 0 falhas em 421 quadros. O oval tem 526,5 × 285,3 px e margens
de 79,5 / 50,8 / 72,1 / 52,1 px em relação à caixa estável, com variação de 0,000 px. A peça real girando nunca chega a menos
de 13,7 px do traço. A ondulação é de 1,5%, o desenho é monotônico e termina, e nenhum traço fica a menos de 4 px de um texto.
Todos os acentos PT-BR têm glifo, e o riscado do "323" foi encurtado antes do "km/h".

`.venv\Scripts\python.exe F1\horizontal\testes\anotacao\rodar.py`: renderiza a cena nos dois motores em PNG quadro a
quadro (Remotion 4.0.539 pelo `F1/video/node_modules`; HyperFrames 0.9.20 por `npx`, sem instalar nada global) e mede
nos **pixels**:

| | Remotion | HyperFrames |
|---|---|---|
| tamanho do oval (77 quadros inteiros, peça andando e girando) | 534–535 × 292–293 px (variação 1 px) | 534 × 292–293 px (1 px) |
| margem esquerda/cima oval × caixa estável (363 quadros) | variação 1,0 px | 1,0 px |
| erro máximo da caixa medida × calculada pelo kit | 0,76 px | 0,76 px |
| pixels vermelhos novos dentro de caixa de texto | 0 | 0 |
| texto da cena fora da caixa declarada | 0 px | 0 px |

A variação de 1 px é arredondamento do pixel num deslocamento subpixel (o traço de 7 px antisserrilhado); a caixa projetada
da peça, no mesmo trecho, variaria 15 × 72 px. A diferença média entre os quadros dos dois motores é 0,03 de 255.
Folhas: `testes/anotacao/folha_<motor>_oval_60qs.jpg` (48 quadros seguidos do oval), `_corrigido_60qs.jpg` e `_cena.jpg`.

## O que NÃO foi verificado
- **O Felipe ainda não viu.** As folhas foram olhadas aqui: oval fechando com perninha, peça girando dentro dele sem
  encostar, "326" escrito traço a traço, `gira ±12°` e `78% aqui` legíveis. Gosto (espessura, velocidade, quanto o
  oval é maior que a peça) ainda depende da opinião dele.
- O pixel não mede o **lado direito/baixo** do oval depois que a seta chega (a seta entra por ali). Nesses quadros só
  esquerda e cima são medidos, e a geometria inteira continua conferida pelo `checar` do kit.
- **Escala** da âncora (câmera aproximando) está implementada (`s` na trilha), mas não foi testada em render. O teste de
  tamanho constante só vale com escala fixa.
- Peça 3D real (three.js/HyperFrames, pista) não foi usada. O giro é 2D, e `caixaEnvelope` foi testado só com o
  retângulo girando. Com um modelo 3D, é preciso projetar os cantos no intervalo inteiro e passar ao helper.
- Kerning da Caveat não é aplicado. Letras como "ta" e "fo" podem ficar levemente espaçadas.
- Não houve teste com texto em várias linhas (a nota é uma linha só).

## Licenças
`fonte/caveat_traco.json` vem de `registry/blocks/hw-write-title/assets/baked/caveat-pen.js` do repositório HyperFrames
(Apache-2.0, HeyGen), convertido para JSON sem mudar os dados. Os dados são derivados da fonte **Caveat** (Impallari Type,
SIL Open Font License 1.1). O vídeo só leva os contornos desenhados e nenhum arquivo de fonte é distribuído.
