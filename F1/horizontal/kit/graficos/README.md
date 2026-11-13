# kit/graficos: gráficos de comparação de duas voltas (independente de motor)

Cinco gráficos com dados reais do OpenF1, os mesmos nos dois motores, para **qualquer** sessão, pista, piloto, equipe e
número de setores: tudo isso entra por parâmetro (`py/preparar.py`) e vai no JSON de comparação. Nada no código é fixo
de um GP. Interlagos 2026 (LEC × ANT) é o exemplo principal, e Monza 2025 (LEC × HAM, mesma equipe) é o teste de outra
pista. O kit faz toda a conta: escala, ticks, posição de
cada rótulo sem sobreposição, cor legível no fundo e desenho progressivo. Para cada tempo `t`, devolve caminhos (`path`)
e textos em px da tela, e o motor só desenha.

| Tipo | O que mostra | De onde veio |
|---|---|---|
| `velocidade` | velocidade × distância dos dois pilotos, curvas e setores no topo, **gap destacado** (faixa + área entre as curvas na cor de quem ganhou + "ANT ganha 0,419 s aqui") e minimapa com o trecho | gráfico de velocidade do teste Remotion (~1:04) e gráfico de ~36 s do HyperFrames |
| `setores` | barras divergentes da diferença em cada setor e na volta, para o lado de quem foi mais rápido, com os tempos oficiais embaixo | gráfico de setores do teste Remotion (~1:18) |
| `delta` | vantagem acumulada metro a metro. Para cima, A à frente, e para baixo, B. As regiões têm a cor de quem está à frente e o valor final fica na ponta | contador de diferença do HyperFrames |
| `telemetria` | acelerador (%), freio (faixas por piloto) e marcha (degrau) num trecho, com as curvas | Bico de Pato do teste Remotion |
| `normalizado` | comparativo **claro**: métricas de unidades diferentes numa só régua, a vantagem relativa em % (barra para o lado de quem foi melhor), com os dois valores reais e "maior/menor é melhor" escritos | substitui o "normalizado" confuso do HyperFrames |

## Por que o normalizado ficou claro
O do teste HyperFrames misturava a distância normalizada com o eixo e não dizia o que era 100%. Agora:
- uma régua só, rotulada: **"vantagem relativa (% do valor do outro piloto)"**, com ticks em % dos dois lados do zero;
- legenda direta no topo de cada lado: `◀ LEC melhor` / `ANT melhor ▶`, na cor de cada um;
- em cada linha: nome da métrica, os **dois valores reais com unidade** (`LEC 71 km/h · ANT 65 km/h`) e
  `maior é melhor` ou `menor é melhor`;
- o número na ponta da barra é a vantagem (`+9,2 %`). Valores iguais aparecem como `empate`, sem barra.
- vantagem = (melhor − pior) / pior × 100 (no "menor é melhor", (pior − melhor) / pior).

## Arquivos
| Arquivo | O que é |
|---|---|
| `graficos.ts` | núcleo (sem dependências): `montar`, `estado`, `checar`, `metrica`, `vantagem`, `corLegivel`, `TEMAS` |
| `graficos.global.js` | o mesmo núcleo em IIFE (`window.Graficos`) para o HyperFrames. **Gerado** por `testes/graficos/rodar.py` (esbuild) |
| `cli.ts` | `node cli.ts checar\|estado\|montar <cena.json> [t]` |
| `py/preparar.py` | OpenF1 (cache do `kit/gps`) → `comparacoes/<sessao>_<pA>-<voltaA>_<pB>-<voltaB>.json` |
| `py/larguras.py` | gera `fonte/segoe_larguras.json` (avanço de cada caractere da Segoe UI, 400/600/700) |
| `pista/<circuit_short_name>.json` | opcional, por pista: `comprimento_m` oficial, `sentido` e `curvas` com nome e distância. Há `Interlagos.json` (com curvas) e `Monza.json` (sem curvas) |
| `comparacoes/11408_16-17_12-22.json` | classificação SP 2026: LEC v17 (88,082) × ANT v22 (88,095) |
| `comparacoes/9908_16-16_44-16.json` | classificação Monza 2025: LEC v16 (79,007) × HAM v16 (79,124), 2º piloto da equipe com `cor2` |
| `exemplo/cena.json` | cena de teste 1920x1080, 60 q/s, 26 s: os 5 gráficos em sequência (renderizada nos 2 motores) |
| `exemplo/cena_*.json` | outras sessões (`cena_monza.json`). O teste confere dados e textos e fotografa o estado final no Chrome |

Adaptadores: `F1/horizontal/remotion/graficos/CamadaGrafico.tsx` e `F1/horizontal/hyperframes/graficos/camada.js`, cada
um com `exemplo/`. Teste, medidas e folhas: `F1/horizontal/testes/graficos/`.

## Dados (`py/preparar.py`)
```
.venv\Scripts\python.exe F1\horizontal\kit\graficos\py\preparar.py <sessao> <pilotoA> <voltaA> <pilotoB> <voltaB> [--comprimento M]
   ex.: ... 11408 16 17 12 22         (Interlagos 2026)     ... 9908 16 melhor 44 melhor   (Monza 2025)
```
- Usa o cache do OpenF1 do `kit/gps` (`kit/gps/cache/<sessao>/`, fora do Git). Se faltar, baixa por `kit/gps/py/openf1.py`.
- **Distância:** é a integral da velocidade do `car_data` no tempo da volta (trapézio, de `date_start` a `+lap_duration`),
  normalizada ao comprimento da pista, cada piloto sozinho. O comprimento vem de `--comprimento`; se faltar, de
  `pista/<circuito>.json`; e se também faltar, da média das distâncias integradas (registrado em `comprimento_origem`). É o mesmo método do teste HyperFrames.
  Por isso o delta termina **exatamente** na diferença oficial dos tempos de volta. A distância integrada bruta foi
  4.247,9 m (LEC) e 4.237,5 m (ANT) em Interlagos e 5.772,9 m e 5.758,0 m em Monza; a normalização corrige 0,3–1,7%.
- **Setores:** são tantos quanto o `/laps` trouxer (`duration_sector_1..N`). Volta sem tempo de setor é recusada.
- Grade de 5 m: `t`, `vel`, `acel` interpolados; `freio` e `marcha` em **degrau** (valor da última amostra, sem
  "marcha 3,5"). O acelerador é limitado a 0–100, porque o OpenF1 usa 104 como valor inválido. Freio é ligado ou
  desligado (> 0).
- As **amostras brutas** da volta (`bruto`) ficam no JSON. A verificação confere o JSON contra elas e contra o cache, e o
  normalizado calcula as métricas a partir delas, não da grade.
- Fronteiras de setor em distância: onde cada piloto estava ao fechar o setor, pela média dos dois (diferença de 0,1–1,7 m).
- `tracado` (minimapa): `/v1/location` de A na volta (x, y do OpenF1; na tela, z = −y), com a distância pelo relógio da
  volta. Funciona em qualquer pista e não depende do `kit/gps`.
- Cores: `kit/gps/cores.json` pela equipe. Se a equipe faltar, vale a `team_colour` do OpenF1. O 2º piloto da mesma equipe
  usa `cor2`; em Monza, HAM ficou com `#FFD12E`, que `corLegivel` escurece no fundo claro.
- Destaque `"auto"`: a janela é escolhida no delta suavizado (mediana de ±150 m), e as pontas são ajustadas (±50 m) para
  fora de picos. O número escrito é o delta **bruto** entre as pontas. Motivo: nas frenagens fortes, o erro da distância
  integrada de cada piloto gera picos que vão e voltam. Na 1ª chicane de Monza foram 0,2 s em ~350 m, e isso não é
  ganho que fica.

## Cena / spec
```jsonc
{ "largura": 1920, "altura": 1080, "fps": 60, "duracao": 26, "tema": "claro",
  "dados": "comparacoes/11408_16-17_12-22.json",
  "graficos": [
    { "id": "vel", "tipo": "velocidade", "area": {"x":60,"y":40,"w":1800,"h":1000}, "em": 0, "ate": 5.5,
      "dur": 3.2, "destaque": "auto", "curvas": true, "minimapa": true },
    { "id": "dlt", "tipo": "delta", "area": {...}, "em": 10.5,
      "ritmo": [{"t":11.05,"d":0}, {"t":12.3,"d":1237}, {"t":14.0,"d":3167}, {"t":14.6,"d":4309}] },
    { "id": "tel", "tipo": "telemetria", "area": {...}, "em": 16, "trecho": [2250, 2900] } ] }
```
| Campo | Efeito |
|---|---|
| `area` | caixa em px. **Nada** é desenhado fora dela, e o tamanho do texto acompanha a área (`escala` força outro) |
| `em` / `ate` | entrada e saída (corte seco; a transição é do montador) |
| `tema` | `claro` (padrão, a assinatura do canal: `#f2f1ed`) ou `escuro` (`#141518`), só quando for pedido |
| `trecho` | `[d0, d1]` em m (velocidade, delta, telemetria, normalizado) |
| `dur` | duração do desenho dos dados (s), com arranque e chegada suaves |
| `ritmo` | **âncora de tempo**: `[{t, d}]` = no segundo `t` o desenho chega ao metro `d` (linear entre âncoras). Vem das palavras da narração ("...no fim do setor 1..." → `d` da fronteira). Os nomes das curvas e as linhas de setor aparecem quando o desenho passa por eles |
| `destaque` | `"auto"` (janela de 250 m em que o delta mais muda), `{d0, d1, texto?}` ou `false`; `destaqueEm` (s) |
| `curvas` | `true` (todas com nome no trecho), lista de números ou `false` |
| `setores`, `minimapa`, `paineis`, `metricas`, `titulo`, `subtitulo`, `fonte` | opcionais (`fonte: false` tira o crédito) |

**Desenho progressivo:** as séries usam um único **cursor de distância**. Em cada `t`, todas as linhas e áreas são
cortadas no mesmo x, com o último ponto interpolado exatamente no cursor, então as duas linhas chegam juntas a cada
curva. Grade e eixos se desenham da esquerda para a direita. Barras crescem do zero, textos entram em 0,2 s (sem
animação de texto) e o destaque entra depois do fim do desenho.
**Cores:** `corLegivel` escurece (no claro) ou clareia (no escuro) a cor da equipe até ter contraste ≥ 3:1 com o fundo
(WCAG para elemento gráfico). A Mercedes `#00D7B6` virou `#00806C` no claro, e a Ferrari `#E8002D` já passava. O
vermelho de destaque (`#d40000`) é o mesmo das anotações. Como a Ferrari também é vermelha, o destaque é uma **faixa
clara** de fundo, e não uma linha.

## API
```ts
import { montar, estado, checar, TEMAS } from "F1/horizontal/kit/graficos/graficos.ts";
const m = montar(specs, dados, larguras);   // larguras = fonte/segoe_larguras.json
estado(m, t)   // [{ id, tipo: "path", d, stroke|fill, largura, opac, tracejado } | { id, tipo: "texto", x, y, texto, tam, peso, cor, ancora, opac }]
checar(m)      // { falhas, avisos, graficos: { <id>: { elementos, textos, fim, menorFolgaTextos, foraDaArea } } }
```
Remotion: `<AbsoluteFill style={{background: TEMAS.claro.fundo}}><CamadaGrafico montado={m} /></AbsoluteFill>`.
HyperFrames: `CamadaGrafico.criar(svg, Graficos.montar(specs, dados, larguras)).render(t)` no `onUpdate` da timeline. O SVG
é montado uma vez; por quadro só trocam `d` e `opacity`. Fonte: Segoe UI do Windows, a mesma nos dois motores.

## Verificação
`.venv\Scripts\python.exe F1\horizontal\testes\graficos\rodar.py` (com `--so-dados`, sem render, ~10 s; com
`--sem-render`, reaproveita os PNG). O resultado fica em `testes/graficos/resultado.json`. Os números estão em
"Resultado (2026-11-13)", abaixo.
1. **Kit, sem motor** (`checar`, temas claro e escuro): nenhum ponto fora da área; nenhum par de textos a menos de 4 px;
   nenhum texto sobre linha de dados; o ritmo não volta e o desenho chega ao fim do trecho; tudo aparece no fim.
2. **Dados plotados = dados da fonte**, com conta independente (numpy) a partir do cache bruto do OpenF1. Tempos de
   volta e de setor iguais ao `/laps`, e amostras do JSON iguais ao `/car_data`. A distância é refeita. Depois o teste
   pega os **pontos em px montados pelo kit**, desfaz a escala do eixo e compara cada um com a fonte: velocidade,
   acelerador, marcha (degrau exato), vantagem acumulada, faixas de freio ponto a ponto, barras de setor contra os
   tempos oficiais, barras do normalizado contra as métricas refeitas e os números escritos (destaque, valor final,
   setores, valores reais). Também confere que as curvas com nome ficam a ≤ 60 m do mínimo de velocidade (ou longe de
   qualquer mínimo, quando são de pé embaixo) e que o minimapa anda no sentido anti-horário.
3. **Rótulos no Chrome:** caixas reais (largura de `getBBox`, altura da tinta de `measureText`) no estado final de cada
   gráfico. O teste exige que nenhum par se sobreponha, que todos fiquem dentro da área e que a estimativa do kit não
   fique menor que o real por mais de 2 px.
4. **Pixels**, nos dois motores e em todos os quadros: nenhum pixel desenhado fora da área do gráfico ativo; a ponta
   das linhas (pixel mais à direita de qualquer série; uma pode estar por baixo da outra) nunca recua e fica a ≤ 4,5 px do cursor do kit (a ponta redonda passa um pouco do cursor); as
   âncoras do `ritmo` caem no metro pedido. Os dois motores também são comparados entre si.

## Resultado (2026-11-13)
`rodar.py` completo (render de Interlagos nos dois motores, 1.561 quadros PNG cada, ~6 min, mais as verificações de Monza): **0 falhas**.

| Conferência | Resultado |
|---|---|
| checar do kit, claro e escuro | 0 falhas, 0 avisos; menor folga entre textos (estimada) 6,4 px |
| velocidade plotada × car_data (863 pontos por piloto) | erro máx. 0,005 km/h (arredondamento da grade) |
| acelerador / marcha (degrau) | 0,05 % / 0 |
| vantagem acumulada (863 pontos) | 0,0001 s; termina em 0,013 s = 88,095 − 88,082 |
| barras de setor | iguais a \|LEC − ANT\| do `/laps`: 0,065 / 0,693 / 0,745 / 0,013 s |
| faixas de freio × freio bruto, a cada 5 m | 0 pontos errados (LEC 4 faixas, ANT 3) |
| normalizado (refeito do bruto) | vmín +9,2 % LEC (71 × 65 km/h), acelerador a fundo +12,0 % ANT, freio +2,8 % ANT, vméd +0,01 % LEC, vmáx empate |
| destaque automático | "ANT ganha 0,419 s aqui" = vantagem refeita no trecho 3.270–3.520 m (Junção → Subida dos Boxes) |
| textos reais no Chrome (163) | nenhum sobreposto (menor folga 5,9 px), todos dentro da área, real ≤ 1,63 px além da estimativa |
| pixels fora da área (todos os quadros) | 0 no Remotion, 0 no HyperFrames |
| ponta do desenho × cursor do kit (330 quadros por gráfico) | 0 recuos; erro máx. 1,56 px (velocidade), 1,23 px (delta) |
| âncoras do `ritmo` | na folha do delta, os quadros 12,3 s e 14,0 s mostram a ponta exatamente nas linhas de fim do S1 e do S2 |
| Remotion × HyperFrames | diferença média 0,000/255 (pior quadro 0,003) |

Folhas olhadas aqui: `testes/graficos/folha_<motor>_<vel|set|dlt|tel|nrm>.jpg` (entrada quadro a quadro até o fim do
desenho) e `folha_<motor>_seguidos_60qs.jpg` (24 quadros seguidos). Nelas, as duas linhas avançam juntas, os nomes das
curvas aparecem quando a linha chega, o destaque e o minimapa entram no fim e as barras crescem do zero, uma por vez.

## O que NÃO foi verificado
- **O Felipe ainda não viu.** As folhas foram olhadas aqui. O gosto ainda depende da opinião dele: tamanhos, ritmo de
  3 s do desenho, a faixa de destaque clara em vez de vermelho forte e o texto do normalizado.
- Testado em duas pistas: Interlagos, com render completo nos 2 motores, e Monza, com dados, textos e fotos do estado final
  (sem vídeo). Outras pistas não foram testadas. Sem `pista/<circuito>.json`, o gráfico sai sem nomes de curva e com o
  comprimento estimado.
- **Picos no delta em frenagens** (Monza, 1ª chicane): vêm do método da distância integrada e são desenhados como vieram.
  O destaque automático os ignora, mas o gráfico mostra. Uma distância pelo GPS resolveria isso e não foi feita.
- As distâncias das curvas vêm do arquivo de referência do teste HyperFrames, reescaladas. A verificação só garante que
  as curvas **lentas** batem com a telemetria (≤ 60 m). Curvas de pé embaixo (Curva do Sol, Mergulho para LEC) não têm
  como ser conferidas pela velocidade.
- A largura do texto é estimada sem kerning. O Chrome mostrou erro ≤ 2 px, mas só com a Segoe UI do Windows. Em outra
  máquina, sem a fonte, o fallback (Arial) muda as larguras.
- O tema escuro passou na geometria e nos dados, mas **não foi renderizado** nem olhado.
- `minimapa` usa o traçado do GPS de A. A forma da pista foi conferida pelo sentido (anti-horário), não contra um mapa
  oficial.
- A fonte tem esquisitices que o gráfico mostra como vieram, sem correção: 1ª marcha a ~70 km/h no Pinheirinho e no
  Bico de Pato e acelerador abaixo de 100% em retas curtas. O teste garante a fidelidade ao OpenF1, não que o OpenF1
  esteja certo.
- O `car_data` tem ~3,7 Hz (~20 m entre amostras a 280 km/h). A linha passa reta entre amostras, e picos entre elas
  não existem na fonte.
