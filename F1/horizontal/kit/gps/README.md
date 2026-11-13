# kit/gps — carro pelo GPS real do OpenF1, em QUALQUER pista

Módulo do motor documental horizontal (ver `../../ARQUITETURA.md`). Independente de motor: os dados são JSON e o
núcleo é JS puro (`src/gps.js`, tipos em `src/gps.d.ts`), usado igual no Remotion e no HyperFrames.

Serve para qualquer vídeo de F1 (fase 2b): sessão, piloto e volta por parâmetro; circuito, ano e equipe vêm do OpenF1.
A pista tem dois modos com a mesma saída (`py/pista.py`):
- **`glb`** — o circuito tem modelo 3D em `F1/dados/modelos3d` e parâmetros em `pista/<circuito>.json` (arquivo, nó,
  materiais e o alinhamento gravado por `py/alinhar.py`, alinhador genérico). Hoje: só Interlagos.
- **`plana`** — sem modelo: a pista é **traçada pelo próprio `/v1/location`** (voltas rápidas dos 6 pilotos mais
  rápidos da sessão; linha central = mediana lateral de todas as passagens), superfície plana `y = 0`, gravada em
  `pista/<circuito>_plana.json` (vai para o Git) e desenhada no motor por `criarPistaPlana` (`src/gps_three.js`).
`<circuito>` = `circuit_short_name` do OpenF1 (ex.: `Interlagos`, `Monza`). Automático: `glb` se houver modelo
alinhado, senão `plana`; `--modo plana` força o plano.

Resolve os defeitos dos testes de motor (`C:\Users\Felipe\teste-motores\*\APONTAMENTOS_FELIPE.md`):

| Defeito visto | Causa medida | Como o kit resolve |
|---|---|---|
| carro indo e voltando / "travado" | o carimbo de tempo do GPS do OpenF1 tem ruído de ~2 m ao longo da pista (velocidade derivada do GPS erra ~28 km/h em média); interpolar direto nele dá tranco | o relógio `s(t)` é a **velocidade da telemetria** (`/v1/car_data`) integrada e ancorada às posições do GPS por uma correção lenta e robusta; `s(t)` estritamente crescente (cúbica monotônica Fritsch–Carlson no JS) |
| carro some | trajetória acabava antes da cena / índice fora da faixa | 4 s de GPS antes e depois da volta; fora disso o carro fica parado no extremo (nunca some) |
| carro dentro do chão | altura tirada de uma linha central (3 pontos), não da malha | raio vertical na malha da pista a cada 1 m **e** em 7 pontos intermediários de cada metro; 2 cm de folga; inclinação e rolagem medidas no asfalto |
| carros lado a lado | deslocamento lateral artificial | cada carro anda no próprio traçado GPS; dois carros podem se sobrepor |

## Arquivos
- `py/openf1.py` — baixa e guarda em `cache/` (fora do Git) `laps`, `location`, `car_data`, `drivers`, `sessions`.
- `py/pista.py` — a pista de qualquer circuito nos modos `glb`/`plana` (`carregar`, `tracar_plana`): alinhamento,
  superfícies para a altura (`chao`, `asf`, `pilot`) e máscara pilotável.
- `py/pista_glb.py` — leitor mínimo de .glb (numpy) + `Superficie` (altura por raio vertical).
- `py/alinhar.py` — alinhador genérico: x,y do OpenF1 (dm) -> plano XZ do .glb do circuito (similaridade 2D por ICP
  no material de asfalto de `pista/<circuito>.json`); grava o bloco `alinhamento` no mesmo arquivo. Interlagos: erro
  mediano 0,54 m; 84% dos pontos GPS no asfalto e o resto na zebra/borda (rodado de novo na 2b: resultado idêntico).
- `py/preparar_volta.py` — gera `voltas/<sessao>_<piloto>_<volta>.json` (~240 KB, vai para o Git; `_plana` no fim
  quando o plano foi forçado num circuito que tem modelo). Campos novos: `circuito`, `modo_pista`, `ano`.
- `pista/Interlagos.json` (modelo + alinhamento), `pista/Monza_plana.json` (traçada pelo GPS da classificação 2025).
- `src/gps.js` — núcleo (amostrador). `src/gps_three.js` — adaptador three.js opcional (carro, pose, rastro, pista plana).
- `exemplo/cena_exemplo.js` — cena mínima idêntica nos dois motores (`pista` = .glb ou `pistaPlana` = JSON).
- `cores.json` — cor do rastro por equipe (`cor` e `cor2` para o 2º piloto da mesma equipe; a cena usa `cor2` sozinha
  quando os dois carros são da mesma equipe). Equipe fora da lista: `team_colour` do OpenF1.
- `testes/testar_gps.py` (teste automático do movimento, qualquer modo), `testes/testar_plana.py` (teste da pista
  plana), `testes/amostrar.mjs`, `testes/folha.py` (folha de sequência).

Modelo de Interlagos: `F1/dados/modelos3d/interlagos_sao_paulo.glb` (fora do Git; Sketchfab, SidewalkNZ, CC-BY-4.0).
Os scripts acham `F1/dados` subindo as pastas (funciona também numa worktree dentro do repositório).

### Circuito novo
- **Sem modelo:** nada a fazer — `preparar_volta.py <sessao> <piloto> <volta>` traça `pista/<circuito>_plana.json`
  na primeira vez (baixa `location` de 6 pilotos) e reaproveita depois (outras sessões do mesmo circuito também).
- **Com modelo:** ponha o .glb em `F1/dados/modelos3d`, crie `pista/<circuito>.json` com o bloco `glb` (como em
  `pista/Interlagos.json`: `arquivo`, `no` = nó da pista ou `null`, `asfalto`, `pilotavel`, `fundo`) e rode
  `python py/alinhar.py <circuito> <sessao> <piloto> <piloto>`. Confira `erro_mediano_m` (< ~1 m) e
  `fracao_sobre_asfalto` (> ~0,8) e olhe a folha antes de usar.

## Preparar dados (Python da `.venv`)
```
cd F1/horizontal/kit/gps
python py/openf1.py 11412 16 12                 # baixa (cache) corrida; 11408 = classificação
python py/alinhar.py Interlagos 11412 16 12     # só se trocar o modelo de um circuito
python py/preparar_volta.py 11412 16 51 11412 12 55 11408 16 melhor
python py/preparar_volta.py 9908 16 melhor 9908 44 melhor        # Monza 2025 (sem modelo -> plana)
python py/preparar_volta.py 11408 16 melhor --modo plana          # força o plano mesmo com modelo
python testes/testar_gps.py                     # teste automático de todas as voltas em voltas/
python testes/testar_plana.py                   # teste das pistas planas (+ prova do método em Interlagos)
```
Voltas já preparadas: corrida (11412) LEC v51 e ANT v55 (as do teste "1,481 s"); classificação (11408) LEC v17 e ANT v22
(as mais rápidas); **Monza 2025 classificação (9908) LEC v16 (1:19.007) e HAM v16 (1:19.124), modo `plana`**.

## API (JS)
```js
import { carregarVolta, criarAmostrador, relogioComparacao, cameraSeguindo, faixa } from "kit/gps/src/gps.js";
const lec = await carregarVolta(11412, 16, 51, { base: "voltas/" });   // ou criarAmostrador(jsonJaCarregado)
lec.s(t)          // m ao longo do caminho (sempre crescente)
lec.pos(t)        // [x, y, z] no sistema da pista (.glb ou plana; three.js, Y para cima), já no asfalto
lec.pose(t)       // { x,y,z, yaw,pitch,roll, frente, vel (m/s), s, comDados }
lec.rastro(t0,t1) // { pontos: [[x,y,z]...], cor } — linha atrás do carro
lec.info          // sigla, equipe, cor, cor2, volta, duracao, setores, fonte, circuito, modoPista, ano
const rel = relogioComparacao({ fator: 2.2, inicio: 0 });  // tempo da cena -> tempo de volta ("acelerado 2,2x")
// os dois carros usam o MESMO relógio: largam juntos da linha e cada um anda pelo próprio GPS.
```
`t` = segundos desde o início da volta (0 = cruzou a linha; `duracao` = fim). Use cenas dentro de `[tIni, tFim]`
(~-4,3 s a duracao+4 s); fora disso o carro fica parado (não some, mas para de repente).

three.js (`src/gps_three.js`, recebe o módulo THREE): `prepararCarro(THREE, gltf.scene)` (frente +Z, rodas em y=0),
`aplicarPose(obj, pose)` (`rotation.order = "YXZ"`, `rotation.set(-pitch, yaw, roll)`), `criarRastro(THREE, cor)` →
`malha.atualizar(am.rastro(t - 2.5, t))`, `ajustarPista(gltf.scene)`. A pista entra SEM transformação.
Modo plano: `cena.add(criarPistaPlana(THREE, jsonDe("pista/Monza_plana.json")))` (chão claro, borda branca de 1 m,
asfalto cinza, linha de chegada no ponto 0; cores por opção).

## Exemplos nos dois motores
- Remotion: `F1/horizontal/remotion` → `npm install` (local) e `npm run exemplo-gps` (`preparar.mjs` liga os .glb em `public/`).
  Composições `ExemploGps` (câmera fixa, tempo real), `ExemploGpsPerseguicao` (câmera atrás, 2,2x), `ExemploGpsFolha` (sem rastro/HUD, para a folha);
  2ª pista: `ExemploGpsMonza`, `ExemploGpsMonzaPerseguicao`, `ExemploGpsFolhaMonza` (prop `conjunto: "monza"`, pista plana).
- HyperFrames: `F1/horizontal/hyperframes` → `npm run exemplo-gps` (`preparar.mjs` monta `assets/` com os .glb e uma
  CÓPIA de `kit/gps/{src,exemplo,voltas,pista}` — o HyperFrames só serve arquivos de dentro do projeto; rode de novo após mexer no kit).

## Teste e critérios (resultado em `F1/horizontal/testes/gps/`)
`testes/testar_gps.py` amostra o `gps.js` (Node) a 60 q/s em cada volta (1x, 2,2x e além das margens) e reprova se:
`s` recuar ou não crescer; salto de posição > 100 m/s·dt; |aceleração| > 70 m/s²; giro > 3 rad/s; deslocamento que a
velocidade não explica > 5 cm; qualquer quadro com o centro do carro abaixo do chão (raio vertical na malha) ou sem chão
medido; pose não finita. A altura é medida contra a malha da pista da PRÓPRIA volta (modelo ou plana). Relatório:
`relatorio_teste.json`. A folha (`testes/folha.py`) mede o movimento do carro na própria imagem renderizada (passo
por quadro e recuos).

`testes/testar_plana.py` (relatório `relatorio_plana.json`) reprova uma pista plana se: a linha não fecha ou tem
passo desigual; curvatura > 1/8 m (quina); giro total ≠ 1 volta (ou 0, pista em 8); largura fora de [12, 16] m;
comprimento > 3% longe do oficial (`kit/graficos/pista/<circuito>.json`, quando existe); < 99% do GPS dentro do
asfalto + zebra. E prova o MÉTODO contra a verdade: traça Interlagos pelo GPS da classificação 11408 como se não
houvesse modelo e mede no `interlagos_sao_paulo.glb` quanto da linha central cai sobre asfalto/zebra (≥ 90%) e o
ponto mais longe da área pilotável (≤ 4 m).

### Resultado da 2b (2026-11-13)
- `testar_gps.py`: 18/18 casos OK — as 4 voltas de Interlagos (`glb`, sem mudança: a volta 11412 LEC v51 regerada com o
  código novo saiu idêntica, diferença 0) e as 2 de Monza (`plana`): `s` sempre crescente, salto máx. 1,62 m/quadro
  (limite 1,67 = 100 m/s; Monza chega a 350 km/h), aceleração máx. 57,6 m/s², giro máx. 1,43 rad/s, 0 quadros abaixo
  do chão (folga mín. 2,0 cm), rodas p01 +2,0 cm (plano). Velocidade do relógio x telemetria: erro médio 0,71/0,87 km/h.
- `testar_plana.py`: Monza fecha (0,03 m), passo 2,000 ± 0,001 m, raio mín. 16,3 m, giro 1,001, comprimento 5.762 m
  (oficial 5.793: −0,5%), 100% do GPS dentro. Prova em Interlagos: 88,6% da linha central plana sobre o asfalto do
  modelo, 94,6% sobre asfalto+zebra, ponto mais longe 2,55 m fora.
- Folha `testes/gps/folha_*_remotion_monza.jpg` (render `ExemploGpsFolhaMonza`, freada para a 1ª chicane): 0 recuos na
  tela, passo 23 → 10 px/q descendo liso (variação p95 1,24 px/q). Olhei a folha, a cebola e quadros da perseguição.

## Limites conhecidos
- Ao longo da pista o carro pode estar até ~4 m (RMS) / ~17 m (pico) de onde o GPS bruto diz num instante: é o ruído
  do GPS que foi filtrado (a velocidade bate com a telemetria: erro médio ≤ 1,6 km/h). Entre dois carros, isso é ≤ ~0,05 s.
- Rodas (informativo no teste): com pitch/roll, o contato das rodas fica até ~4 cm abaixo da malha em pontos de zebra/
  ondulação (p01 ≈ -1 cm). O centro do carro nunca fica abaixo.
- Onde o GPS passa da zebra (traçado no limite), o centro é puxado de volta para asfalto/zebra (máx. ~3,7 m, médio 6 cm).
- Só Interlagos tem modelo 3D alinhado. O alinhador é genérico, mas **não foi rodado em outro .glb** (não há outro
  modelo de pista na máquina): materiais/nó de outro arquivo podem pedir ajuste (`pilotavel`, `fundo`).
- **Pista plana — largura não medida:** no OpenF1 o GPS de todos os pilotos cai praticamente na mesma linha (desvio
  lateral mediano 2–3 cm, espalhamento p1–p99 de ~0,1–0,2 m por trecho em Monza e Interlagos: parece projetado
  numa linha de referência), então o espalhamento NÃO mede a largura;
  ela fica no mínimo da faixa (12 m, mínimo da FIA para pista nova). A linha central é o traçado médio dos pilotos, não
  o eixo geométrico da pista: o carro anda sempre perto do meio do asfalto desenhado (em Interlagos a linha plana fica
  até 2,55 m fora da área pilotável do modelo, em zebra/escape de curva).
- Pista plana não tem relevo (`y = 0`, pitch/roll 0), zebras reais, muros nem boxes; a linha de chegada é o ponto 0
  da volta de referência (onde o OpenF1 abre a volta), conferida só a olho.
- HyperFrames: o exemplo de Monza **não** foi renderizado nele (só Remotion); a cena é a mesma (`cena_exemplo.js`).
- O `car_data` e o `location` do OpenF1 vêm de fontes com relógios próprios; a defasagem medida entre eles foi ~0 s
  nesta sessão, mas não é garantida em todas.
