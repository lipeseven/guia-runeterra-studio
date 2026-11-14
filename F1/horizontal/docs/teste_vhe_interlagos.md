# Teste: mod de Assetto Corsa (vhe_interlagos) + melhor volta do Hamilton — fidelidade lateral (2026-11-14)

Vídeo: `F1/dados/testes_vhe/hamilton_melhor_volta_vhe.mp4` (1920x1080, 60 q/s, 53 s, sem áudio; HyperFrames + three.js).
Cena: `F1/horizontal/hyperframes/vhe_interlagos/` (`python preparar.py` e `npx --yes hyperframes@0.9.20 render -o <mp4>`).
Volta: OpenF1 session_key 11408 (Classificação, GP de São Paulo 2026), carro 44, volta 12, 1:30.001.

## Resposta curta (o que é medido e o que é inferido)
**O OpenF1 não mede a posição lateral do carro.** O `/v1/location` de 52 voltas rápidas de 8 pilotos (NOR, HAD, ANT,
LEC, LAW, HAM, RUS, PIA) cai sobre UMA mesma linha: cada ponto fica a 3,4 cm (mediana; p90 10 cm, p99 26 cm) da linha
mediana de todos; a média de cada volta por trecho de 10 m, a 4,6 cm (p90 19 cm, p99 45 cm). Ao longo da pista o mesmo
GPS erra metros (nesta volta: 3,9 m RMS, 13,7 m de pico contra o relógio da telemetria). Ruído de metros ao longo e de
centímetros de lado é impossível num GPS real: o dado é a distância percorrida projetada numa linha de referência
fixa, igual para todos. Logo:
- **Medido:** onde o carro está AO LONGO da pista em cada instante (GPS ancorado na velocidade da telemetria; erro de
  velocidade 1,6–2,0 km/h médio) — ou seja, o ritmo do Hamilton, onde freia e quanto tempo leva em cada curva.
- **Não medido:** a posição lateral do Hamilton. "Meio carro fora do asfalto" na entrada do S do Senna **não pode ser
  afirmado com esses dados** — nem negado.
- **Inferido (o que o vídeo mostra):** o carro anda no **traçado ideal do próprio mod** (`gp/data/ideal_line.ai`, linha
  de IA gravada pelo autor do mod em piso seco) no ritmo medido do Hamilton. A linha azul-clara no chão e o traço azul na
  barra lateral são a linha do OpenF1. O vídeo diz isso na abertura e na legenda da barra.
- A sessão foi **com chuva** (`/v1/weather`: chuva em 66% das leituras): traçado de chuva costuma fugir do seco, então a
  linha ideal do mod é uma referência seca, não "o que o Hamilton fez".

## Método
1. **KN5 → GLB sem Blender** (`kit/gps/py/assetto.py`, numpy + Pillow). Formato `.kn5`: `sc6969`, versão (+1 int se
   > 5), texturas DDS embutidas, materiais (shader, propriedades, mapas), árvore de nós (classe 1 = matriz 4x4 DirectX;
   2 = malha: vértices pos/normal/uv/tangente, índices uint16, material). Coordenadas de mundo do AC sem troca de eixos —
   as mesmas das linhas `.ai`. Conferido: as superfícies saem idênticas (±0,08 mm) às que o Felipe exportou do Blender
   (KN5 Tools), 35 objetos, 93.965 faces.
   - `superficies`: só as malhas de física (nome = dígito + chave do `surfaces.ini`: 1ROAD, 1KERB, 1CURB, 1GRASS...),
     um nó por objeto → `F1/dados/modelos3d/interlagos_vhe_superficies.glb`.
   - `visual`: malhas visíveis agrupadas por material, só vértices usados, texturas reduzidas (512 px, JPEG/PNG) →
     `F1/dados/modelos3d/interlagos_vhe_visual.glb` (35,8 MB; `vhe_interlagos.kn5` + `obj_barriers` + `obj_buildings`,
     sem placas de patrocínio `ads*`, sem horizonte `hor_*`, sem árvores — o recorte de alfa delas saía como manchas
     pretas). Shader `ksMultilayer` (asfalto, grama, zebras) é aproximado: textura base × 2 × cor média dos detalhes; o
     canal alfa dessas texturas NÃO é transparência (usá-lo apagava grama e asfalto).
2. **Formato `.ai`** (`assetto.ler_ai`): cabeçalho 4 int32 (versão 7, n, ...), n × (x, y, z, distância, id), int32 n,
   n × 18 float (velocidade, acelerador, freio, —, raio, **lado esquerdo**, **lado direito**, camber, direção, normal xyz,
   comprimento, frente xyz, tag, inclinação). `fast_lane.ai` = `ideal_line.ai` (idênticos), 2.680 pontos, 4.223 m.
   Esquerda = (fz, 0, −fx): a "lado esquerdo" do `.ai` bate com a borda esquerda da malha 1road com 1,1 m de diferença
   mediana (trocado daria 7,4 m) e os 14 ápices achados pela curvatura viram para o lado certo (S do Senna 1 à esquerda,
   2 à direita, ..., Bico de Pato à direita).
3. **Alinhamento** (`pista/Interlagos_vhe.json`, `py/alinhar.py`): ICP de similaridade 2D contra 1road+1kerb+1curb
   com o GPS de 6 pilotos × 6 voltas (12.351 pontos), reflexão testada (precisa: `refletir`), e **refino novo
   `refinar_dentro`**: o ICP contra uma área de 10–16 m de largura é fraco de lado (duas escolhas de malha-alvo deram
   alinhamentos 4,5 m diferentes, mediana; 6–9% do GPS fora da pista). O refino minimiza a distância para fora de
   asfalto+zebra: **0% do GPS fora**, escala 0,10012 (o OpenF1 está em dm e o mod está em escala: 0,12% de diferença),
   rotação 0,84°. Folga que sobra (translação que ainda mantém tudo dentro): x −0,8/+1,6 m, z −1,0/+6,6 m (z é o eixo das
   retas longas). **Incerteza lateral do alinhamento nas curvas: ~1–2 m.**
4. **Volta** (`py/preparar_volta.py`): `--circuito Interlagos_vhe --lateral livre` (GPS sem puxar de volta para o
   asfalto; correção 0) e `--linha ideal` (caminho = linha do mod; o GPS projetado nela dá só a distância). Mesmo relógio
   s(t) de antes (telemetria + GPS, monotônico). Novo: `lateral.borda_esq/borda_dir/zebra/fora_asfalto` por metro
   (raster de 0,2 m das malhas 1road e das zebras, carro de 2,0 m de largura), lido no JS por `am.lateral(t)`.
5. **Medição** (`py/lateral.py Interlagos_vhe 11408 44` → `testes/gps/Interlagos_vhe_lateral.json`).

## Números
| | valor |
|---|---|
| GPS por volta (HAM v12) | 347 amostras em 90 s (intervalo mediano 0,24 s ≈ 4 Hz; 19 m entre pontos a 280 km/h) |
| espalhamento lateral entre 52 voltas / 8 pilotos | ponto: p50 3,4 cm, p99 26 cm; volta (10 m): p50 4,6 cm, p99 45 cm |
| espalhamento p5–p95 nos ápices | 0,26–0,73 m (Bico de Pato 1,47 m: amostragem num grampo de raio 27 m) |
| linha do OpenF1 × linha ideal do mod | p50 2,07 m, p90 5,09 m, máx. 8,95 m |
| linha do OpenF1 além da borda do asfalto | 2,8% da volta, máx. 0,88 m (sobre zebra) |
| ruído do GPS ao longo da pista (esta volta) | 3,9 m RMS, 13,7 m de pico |
| velocidade do relógio × telemetria | 1,6 km/h (livre) / 2,0 km/h (ideal) médio |
| comprimento da volta | 4.233 m pelo GPS; 4.224 m na linha ideal (oficial: 4.309 m) |

Ápices (linha ideal do mod; "OpenF1" = a linha de referência no mesmo ponto; distâncias do CENTRO do carro à borda):

| curva | lado | borda esq./dir. (ideal) | zebra / fora | OpenF1 esq./dir. |
|---|---|---|---|---|
| S do Senna (1) | E | 0,6 / 14,9 m | 29% / 19% | 2,7 / 12,8 m |
| S do Senna (2) | D | 16,6 / 1,3 m | — | 14,4 / 3,5 m |
| Curva do Sol | E | 0,6 / 13,5 m | 29% / 19% | 1,6 / 12,5 m |
| Descida do Lago (4) | E | 1,8 / 15,3 m | — | 2,6 / 14,5 m |
| Descida do Lago (5) | E | 2,6 / 11,0 m | — | 5,7 / 7,9 m |
| Ferradura (6) / (7) | D | 7,4 / 4,9 · 8,0 / 6,4 m | — | 9,6 / 2,7 · 10,7 / 3,7 m |
| Laranja | D | 18,0 / 1,3 m | — | 13,8 / 5,5 m |
| Pinheirinho | E | 1,2 / 13,2 m | — | 2,2 / 12,2 m |
| Bico de Pato | D | 13,2 / 2,3 m | — | 12,8 / 2,7 m |
| Mergulho (2) | E | 0,9 / 14,2 m | 14% / 5% | −0,9 / 16,0 m |
| Junção | E | 1,4 / 14,1 m | — | 1,9 / 13,6 m |
| Subida dos Boxes | E | 8,3 / 4,6 m | — | 11,1 / 1,8 m |

S do Senna, linha ideal do mod: na reta, 3,0 m da borda direita (pneu a 2,0 m); na frenagem, 1,8 m (pneu a 0,8 m);
no ápice da 1, centro a 0,5 m da borda esquerda — 33% do carro sobre a zebra, 24% fora do asfalto; na 2, 1,2 m da
borda direita. É o padrão "direita → zebra esquerda no ápice", mas **sem meio carro fora na entrada** (o AI do mod não
faz isso). A própria linha do OpenF1 também vai da direita para a esquerda (é uma linha de referência com cara de
traçado), mas no ápice fica a 2,0 m da borda e não toca a zebra.

Erro esperado do que o vídeo mostra: posição ao longo da pista ±4 m (RMS; ≈ ±0,05 s); posição lateral = a do traçado do
mod, que **não é** o Hamilton — a diferença real é desconhecida (entre pilotos/voltas na mesma curva costuma ser de 1–3 m;
a linha do OpenF1 difere da do mod 2 m na mediana e até 9 m), mais ~1–2 m de incerteza do alinhamento.

## Vídeo (decupagem e verificação)
Panorâmica da volta inteira (título com o aviso medido/inferido, 4 s; volta a 7,6×), depois recortes de cima seguindo o
carro (rumo médio de ±0,9 s para cima da tela: esquerda da tela = esquerda do carro): S do Senna (1×), perseguição no
S do Senna (1,5×), Curva do Sol, Descida do Lago (1,5×), Ferradura (1,5×), Laranja, Pinheirinho, Bico de Pato,
Mergulho (1,5×), Junção, Subida dos Boxes. Barra lateral: asfalto com as bordas, carro de 2 m na posição, traço azul
= linha do OpenF1 no mesmo instante, distância do pneu à borda dos dois lados, selo "ZEBRA" (≥ 10% do carro sobre
zebra) e "% do carro fora do asfalto". Rastro vermelho (Ferrari) dos últimos 3 s.

Folhas de 12 quadros seguidos a 60 q/s em `F1/horizontal/testes/vhe/folha_*.jpg` (`python folhas.py <mp4>`): olhei
entrada e ápice do S do Senna, perseguição, Bico de Pato e Mergulho. Corrigido antes da entrega: grama e asfalto brancos
(alfa das texturas multicamada usado como recorte), árvores como manchas pretas (removidas), carro pequeno demais com
câmera fixa por curva (trocada por câmera de cima seguindo, 70 m), carro encostado no painel lateral (câmera recentrada) e
traço do OpenF1 fino demais na barra, "% fora do asfalto" piscando ±10% entre quadros (raster de 0,2 m; agora média
de ±2 m: na saída do Mergulho fica entre 38% e 43%). O carro anda liso (s sempre crescente; distâncias e selo mudam suavemente quadro a
quadro). `testar_gps.py`: as duas voltas novas passam em todos os critérios (0 quadros abaixo do chão, salto máx.
1,35/1,67 m, aceleração máx. 35 m/s², giro 1,07 rad/s). `testes/testar_lateral.py`: 8/8 OK.

Defeitos que ficaram: áreas de escape pintadas (verde-água) saem saturadas demais — a tinta média dos detalhes
multicamada não reproduz o shader do AC; sem som.

## O que melhorar
- **Fonte de posição lateral real:** câmera onboard (F1 TV) com detecção das bordas/zebras, ou imagem aérea/transmissão
  com rastreamento do carro. Nada público do OpenF1/Live Timing dá isso.
- Sessão seca para comparar com a linha do mod (ou várias linhas: o AC grava a do jogador em `ai/` — dá para gravar
  uma volta "no limite" com zebras como alternativa ilustrativa, marcada como simulação).
- Shader multicamada: usar a máscara (`txMask`) para misturar os 4 detalhes em vez da cor média.
- O alinhamento é feito com o GPS; para outro mod, rode `alinhar.py` com `"refinar_dentro": true` e confira a folga.

## Como importar outro mod de pista do AC (repetível, sem Blender)
```
cd F1/horizontal/kit/gps
python py/assetto.py listar <mod>/<pista>.kn5                       # nomes, faces, material (ver as superfícies)
python py/assetto.py superficies <mod> ../../../dados/modelos3d/<x>_superficies.glb [--kn5 <pista>.kn5]
python py/assetto.py visual <mod> ../../../dados/modelos3d/<x>_visual.glb --kn5 <pista>.kn5 obj_barriers.kn5 --textura 512 --excluir "^(ads|hor_)"
python py/assetto.py ai <mod>/<layout>/data/ideal_line.ai           # ou ai/fast_lane.ai
# pista/<Circuito>_<mod>.json: copiar pista/Interlagos_vhe.json e trocar arquivo, linha_ideal e os padrões de nome
python py/alinhar.py <Circuito>_<mod> <sessao> <pilotos...>        # conferir fracao_fora_pilotavel = 0 e a folga
python py/preparar_volta.py <sessao> <piloto> melhor --circuito <Circuito>_<mod> --linha ideal
python py/preparar_volta.py <sessao> <piloto> melhor --circuito <Circuito>_<mod> --lateral livre
python py/lateral.py <Circuito>_<mod> <sessao> <piloto>
python testes/testar_gps.py && python testes/testar_lateral.py
```
Layouts com subpasta (`gp/`, `norm/`): os `.kn5` ficam na raiz do mod e a lista vem de `models_<layout>.ini`
(`--kn5` para escolher). Nomes de superfície mudam de mod para mod: confira com `listar` e ajuste `asfalto`, `zebra`,
`pilotavel`. Licença: mods são de terceiros (este: VheEth, conversão do Automobilista/Reiza) — uso interno de teste; para
publicar, conferir a permissão do autor.
