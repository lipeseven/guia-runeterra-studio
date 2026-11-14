# Teste: Blender (Cycles/EEVEE) no mod vhe_interlagos — Hamilton no S do Senna (2026-11-14)

Vídeo: `F1/dados/testes_vhe/hamilton_senna_blender.mp4` (1920x1080, 60 q/s, 8,0 s, sem áudio, com o aviso discreto
"traçado lateral inferido") e `hamilton_senna_blender_limpo.mp4` (mesmos quadros, sem nenhum texto — para a camada de
dados entrar depois no Remotion; dados por quadro em `F1/dados/testes_vhe/blender_senna/final/dados_quadros.json`).
Fora do Git: quadros PNG em `F1/dados/testes_vhe/blender_senna/final/`, cena montada `.../senna_cena_montada.blend`,
cópia da cena do Felipe `F1/dados/testes_vhe/interlagos_vhe_full.blend` (a cena aberta dele não foi alterada).
No Git: `F1/horizontal/blender/` (código), folhas em `F1/horizontal/testes/blender/`.

## Resposta curta
**Sim, o Blender chega perto do nível da referência** em luz, sombra, materiais e câmera — bem mais que o three.js do
teste anterior — e **o Cycles com GPU saiu MAIS barato que o EEVEE** nesta cena: **~2,8 s por quadro em 1080p** (mediana 2,77 s no render final de 480 quadros: 22,6 min)
(32 amostras + denoise OptiX + motion blur real, dados persistentes), contra 8–11 s do EEVEE com 24 amostras
(3,5–6 s com 12). Escolhido: **Cycles**. O que ainda separa da referência é conteúdo do mod (pouca árvore e placa
neste trecho, arquibancadas simples, sem piloto no carro) e não o motor.

## Método
1. **Cena**: cópia salva da cena aberta do Felipe (`save_as_mainfile(copy=True)`, 390 MB, texturas DDS embutidas) com o
   mod inteiro importado pelo KN5 Tools (vhe_interlagos + obj_barriers/buildings/extra/fence/trees/groove...).
   Render pela linha de comando com uma cópia do Blender 5.3 da Microsoft Store em
   `C:\Users\Felipe\opus-livre-teste\blender-5.3-portatil\` (o `blender.exe` dentro de `WindowsApps` dá "Acesso negado"
   quando chamado direto; a pasta é legível, então foi copiada com robocopy — nada instalado/global).
2. **Movimento** (`senna.py`, porta do `kit/gps/src/gps.js`): relógio s(t) monotônico (Fritsch–Carlson) da volta
   `voltas/11408_44_12_Interlagos_vhe_ideal.json` — posição AO LONGO da pista do OpenF1/telemetria; posição lateral =
   linha ideal do próprio mod (**inferida**; o OpenF1 não mede lateral). Coordenadas do kit (glTF) → Blender
   `(x, −z, y)`, o mesmo giro do KN5 Tools (conferido: o caminho cai sobre as malhas 1road). Tempo de volta 2,00 → 9,98 s
   (reta dos boxes a 288 km/h, freada, S do Senna 1 — ápice a 78 km/h com 30% do carro na zebra e 21% fora do asfalto,
   segundo o traçado do mod —, S do Senna 2 e saída descendo para a Curva do Sol), **tempo real, sem acelerar**.
3. **Apoio no chão**: a cada quadro, 4 raios verticais (um por roda) numa BVH das malhas de física
   `1road/1kerb/1curb/1grass/1outer/1sand/1pitlane` (34 objetos); altura do centro = média ponderada, arfagem e
   rolagem pelo plano das 4 rodas (zebra levanta o carro de verdade).
4. **Carro**: `ferrari_sf26.glb` (o mesmo das cenas three.js), preparado como `F1/video/src/horizontal/carro.ts`:
   5,4 m, frente pela ponta mais baixa, faces de roda (tyre/rim/disc/hub) separadas por canto com pivô no centro.
   Giro das rodas = ∫v/r (r = 0,35 m medido no modelo), esterço = atan(entre-eixos × curvatura do traçado)
   (máx. 4,9° no S; dianteiras num pivô próprio). Pintura com verniz (coat 1,0, rugosidade 0,03).
5. **Luz/visual**: céu físico `MULTIPLE_SCATTERING` (Nishita novo do 5.x; altitude 760 m) com o céu iluminando
   pouco (0,12) e aparecendo mais claro na câmera (0,30, nó Light Path), sol direcional 6 W/m² com ângulo 1,2°
   (sombras suaves), AgX "Medium High Contrast", compositor com névoa de distância (passo de mist), bloom (Glare) e
   aberração leve; pós no FFmpeg: contraste/saturação leves, vinheta e grão (a MESMA correção nos stills e no vídeo).
   Motion blur real 180° (obturador 0,5; rodas e chão borrados de verdade). Profundidade de campo física por câmera.
6. **Câmeras** (cortes secos, marcadores na timeline): `cam_transmissao` q1–240 (alta, 11,5 m atrás, 2 m à esquerda,
   3,4 m acima, rumo médio dos últimos 0,6 s — sem tranco), `cam_zebra` q241–348 (parada a 0,32 m do chão logo além
   da zebra da saída do S 1, 85 mm f/2, acompanha o carro com 40 ms de atraso), `cam_onboard` q349–480 (presa ao
   carro, dentro do halo, 20 mm — o enquadramento da referência).
7. **Materiais do mod** (o que foi corrigido em relação ao KN5 Tools e ao three.js):
   - `ksMultilayer` (asfalto, zebras, grama, escapes): o KN5 Tools liga só `txDiffuse` (cor média clara, ~0,45) e o
     normal. Agora: `txDiffuse × txDetailR (UV × multR) × ksDiffuse × 2`, com o detalhe extraído do .kn5 pelo
     `kit/gps/py/assetto.py` (cache `blender_senna/kn5_tex/`). **O alfa do txDiffuse NÃO é transparência** — é a
     máscara de brilho do AC: virou rugosidade (0,88 fosco → 0,62 onde o pneu poliu). Escapes pintados (verde/amarelo,
     `RDILE/F/G/YL/KG/YG`) com saturação 0,55 — era o "verde-água" saturado do teste three.js.
   - Colisores (`1wall_collider*`, material COLLIDER, coleção `VHE_obj_collider`): fora do render.
   - Árvores/arbustos (`ksTree`): alfa recortado (dithered/Cycles) — aparecem certas, sem manchas pretas.
   - Borracha `GROOVE`/`MARBLES` (camadas coplanares com alfa): ver bugs.

## Tempos medidos (RTX 4060 8 GB, Ryzen 7 5700X3D; Blender 5.3; 1920x1080; motion blur ligado)
| motor | configuração | s/quadro (1080p) | observação |
|---|---|---|---|
| EEVEE | 24 amostras TAA, raytracing de tela, fast GI | 8,0–10,8 (onboard mais caro) | 1º quadro +compilação dos 280 materiais |
| EEVEE | 12 amostras | 3,5–6,2 | motion blur começa a mostrar degraus |
| Cycles | 32 amostras + OptiX denoise, cada quadro do zero | 4,3–7,3 | reconstrói a BVH de ~1 milhão de faces a cada quadro |
| Cycles | 16 amostras | 3,9–4,9 | quase nada mais rápido: o custo é a cena, não as amostras |
| **Cycles** | **32 amostras + OptiX + dados persistentes** | **2,7–3,6** (5,9 no 1º) | **escolhido** |
| **Render final** | 480 quadros, Cycles 32 + OptiX + persistente | **mediana 2,77; p95 3,58; máx. 7,19 (1º quadro)** | **22,6 min no total** (1.355 s, com abrir o .blend, montar, gravar o .blend montado de 400 MB e os 480 PNG): 2,8 s/quadro de parede |

Montagem da cena (abrir o .blend de 390 MB, materiais, carro, BVH, 480 quadros de animação): ~10 s + abrir o arquivo
(~15 s). Estimativas com 2,8 s/quadro (o medido no render final; Cycles 32, persistente):
- **Uma volta inteira** (90 s a 60 q/s = 5.400 quadros): **~4,2 h** de GPU (EEVEE 24: ~14 h).
- **Vídeo de 15 min**: só as cenas de pista vão para o Blender. Com 3–4 min de pista em 3D: 10.800–14.400 quadros =
  **8,4–11 h** (uma noite); com os 15 min inteiros em 3D: 54.000 quadros = **~42 h** — inviável sem baixar custo
  (720p + upscale, 30 q/s em cenas lentas, ou EEVEE 12 nos planos abertos). Rascunho em 40%/8 amostras: ~1 s/quadro.

## Folhas (F1/horizontal/testes/blender/)
- `comparacao_rodada0_inicial.jpg` — 1ª rodada (EEVEE): tudo lavado (asfalto quase branco, céu forte demais iluminando,
  névoa exagerada), sem sombra; câmera da zebra longe do carro.
- `comparacao_rodada1_eevee.jpg` — multicamada certo (asfalto/grama/escapes), céu mais fraco; ainda sem sombra visível
  (o céu dominava a luz: diagnóstico com céu = 0 mostrou o sol certo, fraco demais).
- `comparacao_rodada2_eevee.jpg` — sol 6 / céu 0,12 (câmera vê 0,30): sombras das arquibancadas e do carro, asfalto
  escuro e neutro (menos reflexo azul), câmera alta reenquadrada.
- `comparacao_eevee_x_cycles_bug_borracha.jpg` — mesmos quadros nos dois motores: no Cycles a pista fica azul-clara
  (bug das camadas de borracha) — corrigido escondendo-as.
- `comparacao_rodada3_cycles.jpg` — Cycles final ao lado da referência. A câmera onboard foi trazida para dentro do halo
  (antes ficava atrás da tomada de ar, vendo um bloco amarelo: o modelo não tem piloto).
- `folha_seq_*.jpg` — 12 quadros seguidos a 60 q/s (tempo = tempo do clipe): reta (q20), freada (q170), corte para a câmera da zebra (q236), zebra no ápice (q290), onboard no S 2 (q440). Olhei todas: carro avança liso quadro a quadro, sem tranco nem recuo, corte seco limpo; rodas/chão com motion blur. Defeito visto: o início da câmera da zebra (q241–260) tem o carro pequeno e metade do quadro de chão escuro desfocado — melhora quando o carro chega (q280+).
- `still_q60/230/300/330/420.jpg` — melhores quadros (corrigidos, 1080p; os PNG sem perda ficam em
  `F1/dados/testes_vhe/blender_senna/final/`).

## O que ficou parecido com a referência
Sol forte com sombras de contato e das estruturas, asfalto escuro com variação e rugosidade, céu físico com névoa de
distância, motion blur real no chão e nas rodas, profundidade de campo (sobretudo na câmera baixa da zebra), cor AgX com
contraste e grão, enquadramento onboard pelo halo com as rodas dianteiras e o bico, banners Pirelli e arquibancadas,
zebras com textura e relevo (o carro sobe nela no ápice do S 1).

## O que falta (honesto)
- **Conteúdo do mod**: neste trecho há poucas árvores e placas perto da pista; arquibancadas e prédios são de baixa
  resolução (texturas 1–2k de 2010); sem público, sem bandeiras, sem fiscais animados. A referência (jogo de F1 atual)
  tem árvores densas, placas Pirelli/Heineken grandes e coloridas perto da câmera e muros com patrocínio.
- **Carro**: sem piloto/capacete (a referência mostra o capacete amarelo); pneus sem marcação Pirelli legível; sem
  suspensão (a carroceria acompanha o plano das 4 rodas, sem rolagem dinâmica de carga); esterço só geométrico.
- **Luz**: sem neblina volumétrica real (a névoa é passo de mist no compositor); bloom discreto; sem lens flare.
- **Movimento**: tremor de câmera onboard (vibração) não simulado; câmera onboard rígida no carro.
- **Traçado**: lateral = linha ideal do mod (inferida) — o vídeo diz isso no canto. A sessão real foi com chuva; a
  imagem é seca.
- **Trecho**: o pedido incluía a entrada da Reta Oposta, mas em tempo real ela só começa ~t = 15 s (depois da Curva
  do Sol); com 8 s o teste termina na saída do S 2, descendo para a Curva do Sol. Para incluir a Reta Oposta sem
  acelerar o tempo: 14 s de vídeo (ou um corte de tempo explícito).

## Bugs do mod / do importador
1. **Alfa das texturas ksMultilayer não é transparência** (é máscara de brilho/especular do AC): o KN5 Tools faz certo
   (não liga o alfa), o `assetto.py`/three.js antigo tratava como cor/recorte. Aqui virou rugosidade.
2. **KN5 Tools não importa o ksMultilayer completo**: só `txDiffuse` + `txDetailNM`; faltam `txMask` e
   `txDetailR/G/B/A` → asfalto/grama claros e lisos. Resolvido extraindo os detalhes do .kn5 (`assetto.ler_kn5`).
3. **`txMask` lido como zero** (`asphalt-main-mask.dds`, `1colormask.dds`: RGBA = 0 no Pillow e no Blender — formato DDS
   que nenhum dos dois decodifica certo, ou máscara realmente vazia). Usado só o detalhe R (neste mod R = G = B quase
   sempre). Os escapes pintados (ROADE/F/G) têm cor base verde-água forte no próprio .dds (0,08/0,75/0,51): no AC o
   detalhe e a luz os escurecem; aqui saturação 0,55.
4. **Borracha (obj_groove: `GROOVE`, `MARBLES`, alfa 0,5 × textura) no Cycles** deixa a pista inteira azul-clara, mesmo
   com cor escura e fosca; no EEVEE a camada coplanar quase não aparece. No Cycles elas ficam fora do render (a linha de
   borracha da própria textura do asfalto continua).
5. Colisores visíveis (`1wall_collider_*`) se não forem escondidos.
6. A cena aberta tem coleções vazias duplicadas (`VHE_INTERLAGOS.001`, `OBJ_*`/`KN5_HIERARCHY.00x`, de importações
   repetidas) — inofensivas.
7. `blender.exe` da Microsoft Store não roda por linha de comando ("Acesso negado"): usar a cópia portátil.

## Recomendação: Blender como 3º motor por cena no montador
- **SPEC**: `motor: "blender"` só para cenas de pista "hero" (onboard, câmera baixa, perseguição perto do carro), onde a
  luz faz diferença; panorâmicas, mapas e comparações continuam no HyperFrames/Remotion (segundos, não horas).
- **Receita nova** `pista_blender` em `montador/receitas.py`: `{sessao, piloto, volta, linha (ideal|livre), t_ini,
  duracao, cameras: [{tipo: transmissao|zebra|onboard|fixa, de_quadro, parametros}], carro, cores, resolucao}` → chama
  `blender -b <cena_base.blend> --python F1/horizontal/blender/senna.py -- --spec <json>` (generalizar o `senna.py`:
  hoje T0, cortes e posição da câmera da zebra são constantes do teste).
- **Cena por demanda**: a cena base do circuito (mod importado + materiais corrigidos, sem carro/câmeras) é gerada uma
  vez por circuito e guardada em `F1/dados/blender/<circuito>.blend`; cada cena do vídeo só acrescenta carro, animação e
  câmeras (~7 s de montagem).
- **Cache por hash** (igual aos blocos do montador): hash = SHA1(.blend base + `senna.py` + JSON da volta + receita +
  motor/amostras/resolução). Os PNG ficam em `F1/dados/<projeto>/blender/<hash>/`; um quadro que existe não é
  renderizado de novo (permite retomar render interrompido). O montador lê a sequência PNG como lê os trechos dos outros
  motores (60 q/s) e aplica o mesmo `GRADE` do `folhas.py`.
- **Rascunho**: 40% e 8 amostras (~1 s/quadro) para o ★ de aprovação; final só depois do OK.
- **Fila**: render longo na GPU compartilhada com o Runeterra → entrar no `motor.lock`/fila existente, em blocos de
  ~600 quadros, com retomada pelo cache.
- **Camada de dados**: o Blender entrega a versão limpa + `dados_quadros.json` (s, velocidade, esterço, bordas,
  zebra, fora do asfalto, câmera ativa por quadro); a barra lateral/velocidade entra no Remotion por cima.
