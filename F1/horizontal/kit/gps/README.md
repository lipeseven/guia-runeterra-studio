# kit/gps — carro pelo GPS real do OpenF1, apoiado na pista 3D

Módulo do motor documental horizontal (ver `../../ARQUITETURA.md`). Independente de motor: os dados são JSON e o
núcleo é JS puro (`src/gps.js`, tipos em `src/gps.d.ts`), usado igual no Remotion e no HyperFrames.

Resolve os defeitos dos testes de motor (`C:\Users\Felipe\teste-motores\*\APONTAMENTOS_FELIPE.md`):

| Defeito visto | Causa medida | Como o kit resolve |
|---|---|---|
| carro indo e voltando / "travado" | o carimbo de tempo do GPS do OpenF1 tem ruído de ~2 m ao longo da pista (velocidade derivada do GPS erra ~28 km/h em média); interpolar direto nele dá tranco | o relógio `s(t)` é a **velocidade da telemetria** (`/v1/car_data`) integrada e ancorada às posições do GPS por uma correção lenta e robusta; `s(t)` estritamente crescente (cúbica monotônica Fritsch–Carlson no JS) |
| carro some | trajetória acabava antes da cena / índice fora da faixa | 4 s de GPS antes e depois da volta; fora disso o carro fica parado no extremo (nunca some) |
| carro dentro do chão | altura tirada de uma linha central (3 pontos), não da malha | raio vertical na malha da pista a cada 1 m **e** em 7 pontos intermediários de cada metro; 2 cm de folga; inclinação e rolagem medidas no asfalto |
| carros lado a lado | deslocamento lateral artificial | cada carro anda no próprio traçado GPS; dois carros podem se sobrepor |

## Arquivos
- `py/openf1.py` — baixa e guarda em `cache/` (fora do Git) `laps`, `location`, `car_data`, `drivers`, `sessions`.
- `py/pista_glb.py` — leitor mínimo de .glb (numpy) + `Superficie` (altura por raio vertical).
- `py/alinhar.py` — alinha x,y do OpenF1 (dm) ao plano XZ do `interlagos_sao_paulo.glb` (similaridade 2D por ICP no
  asfalto, material `mesh2_7`). Saída `pista/interlagos_alinhamento.json` (vai para o Git). Erro mediano 0,54 m; 84%
  dos pontos GPS caem no asfalto e o resto na zebra/borda (conferido em imagem de 12 trechos da volta).
- `py/preparar_volta.py` — gera `voltas/<sessao>_<piloto>_<volta>.json` (~240 KB, vai para o Git).
- `src/gps.js` — núcleo (amostrador). `src/gps_three.js` — adaptador three.js opcional (carro, pose, rastro).
- `exemplo/cena_exemplo.js` — cena mínima idêntica nos dois motores.
- `cores.json` — cor do rastro por equipe (`cor` e `cor2` para o 2º piloto da mesma equipe).
- `testes/testar_gps.py` (teste automático), `testes/amostrar.mjs`, `testes/folha.py` (folha de sequência).

O modelo da pista vem de `F1/dados/modelos3d/interlagos_sao_paulo.glb` (fora do Git; Sketchfab, SidewalkNZ, CC-BY-4.0).
Os scripts acham `F1/dados` subindo as pastas (funciona também numa worktree dentro do repositório).

## Preparar dados (Python da `.venv`)
```
cd F1/horizontal/kit/gps
python py/openf1.py 11412 16 12                 # baixa (cache) corrida; 11408 = classificação
python py/alinhar.py 11412 16 12                # só se trocar de pista/modelo
python py/preparar_volta.py 11412 16 51 11412 12 55 11408 16 melhor
python testes/testar_gps.py                     # teste automático de todas as voltas em voltas/
```
Voltas já preparadas: corrida (11412) LEC v51 e ANT v55 (as do teste "1,481 s"); classificação (11408) LEC v17 e ANT v22 (as mais rápidas).

## API (JS)
```js
import { carregarVolta, criarAmostrador, relogioComparacao, cameraSeguindo, faixa } from "kit/gps/src/gps.js";
const lec = await carregarVolta(11412, 16, 51, { base: "voltas/" });   // ou criarAmostrador(jsonJaCarregado)
lec.s(t)          // m ao longo do caminho (sempre crescente)
lec.pos(t)        // [x, y, z] no sistema do .glb (three.js, Y para cima), já no asfalto
lec.pose(t)       // { x,y,z, yaw,pitch,roll, frente, vel (m/s), s, comDados }
lec.rastro(t0,t1) // { pontos: [[x,y,z]...], cor } — linha atrás do carro
lec.info          // sigla, equipe, cor, cor2, volta, duracao, setores, fonte
const rel = relogioComparacao({ fator: 2.2, inicio: 0 });  // tempo da cena -> tempo de volta ("acelerado 2,2x")
// os dois carros usam o MESMO relógio: largam juntos da linha e cada um anda pelo próprio GPS.
```
`t` = segundos desde o início da volta (0 = cruzou a linha; `duracao` = fim). Use cenas dentro de `[tIni, tFim]`
(~-4,3 s a duracao+4 s); fora disso o carro fica parado (não some, mas para de repente).

three.js (`src/gps_three.js`, recebe o módulo THREE): `prepararCarro(THREE, gltf.scene)` (frente +Z, rodas em y=0),
`aplicarPose(obj, pose)` (`rotation.order = "YXZ"`, `rotation.set(-pitch, yaw, roll)`), `criarRastro(THREE, cor)` →
`malha.atualizar(am.rastro(t - 2.5, t))`, `ajustarPista(gltf.scene)`. A pista entra SEM transformação.

## Exemplos nos dois motores
- Remotion: `F1/horizontal/remotion` → `npm install` (local) e `npm run exemplo-gps` (`preparar.mjs` liga os .glb em `public/`).
  Composições `ExemploGps` (câmera fixa, tempo real), `ExemploGpsPerseguicao` (câmera atrás, 2,2x), `ExemploGpsFolha` (sem rastro/HUD, para a folha).
- HyperFrames: `F1/horizontal/hyperframes` → `npm run exemplo-gps` (`preparar.mjs` monta `assets/` com os .glb e uma
  CÓPIA de `kit/gps/{src,exemplo,voltas}` — o HyperFrames só serve arquivos de dentro do projeto; rode de novo após mexer no kit).

## Teste e critérios (resultado em `F1/horizontal/testes/gps/`)
`testes/testar_gps.py` amostra o `gps.js` (Node) a 60 q/s em cada volta (1x, 2,2x e além das margens) e reprova se:
`s` recuar ou não crescer; salto de posição > 100 m/s·dt; |aceleração| > 70 m/s²; giro > 3 rad/s; deslocamento que a
velocidade não explica > 5 cm; qualquer quadro com o centro do carro abaixo do chão (raio vertical na malha) ou sem chão
medido; pose não finita. Relatório: `relatorio_teste.json`. A folha (`testes/folha.py`) mede o movimento do carro na
própria imagem renderizada (passo por quadro e recuos).

## Limites conhecidos
- Ao longo da pista o carro pode estar até ~4 m (RMS) / ~17 m (pico) de onde o GPS bruto diz num instante: é o ruído
  do GPS que foi filtrado (a velocidade bate com a telemetria: erro médio ≤ 1,6 km/h). Entre dois carros, isso é ≤ ~0,05 s.
- Rodas (informativo no teste): com pitch/roll, o contato das rodas fica até ~4 cm abaixo da malha em pontos de zebra/
  ondulação (p01 ≈ -1 cm). O centro do carro nunca fica abaixo.
- Onde o GPS passa da zebra (traçado no limite), o centro é puxado de volta para asfalto/zebra (máx. ~3,7 m, médio 6 cm).
- Só Interlagos (`interlagos_sao_paulo.glb`) está alinhada; outra pista = novo `alinhar.py` com o .glb dela.
- O `car_data` e o `location` do OpenF1 vêm de fontes com relógios próprios; a defasagem medida entre eles foi ~0 s
  nesta sessão, mas não é garantida em todas.
