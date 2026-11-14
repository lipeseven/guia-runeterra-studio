# montador/ — cenas por motor + transições + UMA mixagem (fase 5: só a ferramenta)

Lê `spec.json` (e o `estado.json`) do projeto, renderiza cada cena no motor marcado nela (Remotion ou HyperFrames) como
trecho de 60 q/s, junta os trechos com as transições do `kit/transicoes` e faz uma mixagem só (narração + trilha + SFX
do `kit/sfx` por âncora de palavra), com loudness medida. Depois verifica o MP4 por quadro e por amostra de áudio.
**Nenhum vídeo completo foi montado** (decisão do Felipe): só o mini-spec de teste de 3 cenas.

```
spec.json + palavras.json ─▶ receitas.py (cena → pedido de render, hash) ─▶ segmentos.py (motor → trecho MP4, cache;
                                                                              Remotion em lotes ≤ 45 s)
                                    transicoes.mjs (estados do kit) ─▶ juncao.py (quadros intermediários)
                                    blocos.py (blocos ≤ 45 s + junções, cache por hash) ─▶ concat SEM recodificar
                          mixagem.py (SFX + narração + trilha → master.wav medido) ─┘      quadros.py (verificação + folhas)
storyboard.py (prévia por cena = trecho do cache + quadros dos momentos-chave; ★ por cena)
```

## Uso
```
.venv\Scripts\python.exe F1\horizontal\montador\montar.py <pasta>/horizontal [--checar] [--cenas id,id] [--final] [--livre] [--registrar] [--forcar]
```
- padrão = **rascunho** 1280×720 (x264 rápido / NVENC); `--final` = 1920×1080, codificação mais lenta (mesmo caminho).
- `--checar`: só diz se dá para montar (tudo o que falta de uma vez); `--cenas`: só os trechos dessas cenas (cena por demanda).
- `--livre`: não exige SPEC ★/verificação no estado (testes). `--registrar`: grava a etapa `rascunho` (`gerado`/`falhou`).
- Saída: `<pasta>/rascunho/rascunho.mp4`, `relatorio.json` (tudo), `audio/` (`mix_bruta.wav`, `sfx.wav`, `master.wav`,
  filtro), `verificacao/` (`verificacao_montagem.json` + folhas JPG). Trechos e cache: `<pasta>/trechos/<cena>_<hash>_<WxH>.mp4`.
- Narração: `<pasta>/narracao.wav` ou `<projeto>/trabalho/gravacao/limpa.wav` (a voz limpa do painel). Trilha: `<pasta>/trilha.wav|.mp3`.
  Sem elas, monta com aviso.

## Relógio e junção (60 q/s, um relógio só)
- Cena k = quadros globais `[round(t0·60), round(t1·60))` (tempos das palavras na SPEC).
- Transição de entrada de n quadros **centrada no corte**, como no kit (`q0 = qCorte − n//2`). O trecho de cada cena é
  renderizado com `pre = n_entrada//2` quadros antes e `pos = n_saída − n_saída//2` depois: os dois lados da transição
  existem de verdade (dá para misturar Remotion com HyperFrames). Nos `pre` quadros a cena segura o quadro 0.
- Quadros intermediários compostos em numpy com o MESMO `estadoTransicao` que os motores aplicam em CSS (opacidade,
  escala no centro, desfoque gaussiano, recorte inset, barra do wipe). O resto é trim por quadro do próprio trecho; uma
  passada do ffmpeg POR BLOCO (blocos juntados sem recodificar, ver abaixo) (filtro por arquivo, `-/filter_complex`), `setpts=N/(60·TB)`, CFR.
- Cache: hash = pedido de render (params resolvidos, tempos, pre/pos) + conteúdo dos dados (comparação, voltas, pista,
  modelos) + código (receita, adaptador, núcleo do kit). Mudou uma cena → só ela é renderizada de novo.

## Blocos de render e de saída (fase 7b)
Medido com `medir_motores.py` (mesma cena renderizada com 1, 3 e 6 s, sem transições; reta tempo = fixo + por_segundo ×
duração; 1280×720, RTX 4060; 2026-11-13, mini-spec de Monza):

| motor | cena | fixo (abrir o motor) | render por segundo de vídeo |
|---|---|---|---|
| Remotion | gráfico (`graficos`) | 4,4 s | 1,52 s/s |
| Remotion | texto + oval (`anotacao`) | 5,6 s | 1,21 s/s |
| HyperFrames | GPS (`gps`, 2 carros 3D + pista plana) | 13,7 s | 2,35 s/s |

Lote do Remotion (`segmentos.renderizar_lote`, composição `LoteDoc` com as cenas em sequência): 2 cenas × 3 s = 13,7 s
contra 17,5 s separadas (economiza ~1 fixo por cena a mais no lote).

Decisões tiradas da medição:
- **Teto = 45 s** de vídeo por lote do Remotion (`segmentos.TETO_LOTE_S`) e por bloco de saída (`blocos.TETO_BLOCO_S`).
  Com fixo ≈ 5 s e ≈ 1,4 s/s, um lote de 45 s leva ~68 s e o fixo vira ~7 % (com 15 s seriam ~20 %). Num vídeo de
  20 min com ~70 cenas, abrir o Remotion por cena custaria ~6 min só de fixo; em lotes de 45 s, ~2 min. O lote **não**
  piora a edição: a cena mudada é renderizada sozinha (o cache continua por cena), só as que faltam vão juntas.
- HyperFrames **não** vai em lote (cada cena GPS é uma página com os modelos 3D dela): paga ~14 s de fixo por cena.
  Juntar várias cenas GPS numa página fica para quando houver muitas (não medido com mais de uma).
- **Blocos de saída** (`blocos.py`): cenas inteiras vizinhas até 45 s, cada bloco codificado à parte (cache por hash em
  `<pasta>/blocos/`), junção final com `ffmpeg -f concat -c:v copy` (nenhum quadro recodificado; o teste confere pacote a
  pacote) + o áudio da mixagem ÚNICA (fora dos blocos). Fronteira só entre cenas que não continuam uma na outra (mesmo
  gráfico/GPS = `blocos.continua`); prefere um corte; sem corte, a transição (wipe/zoom/fade) inteira vira um segmento de
  junção que depende só das duas cenas vizinhas. Mudou uma cena → só o trecho dela, o bloco dela e as junções dela são
  refeitos. Todos os segmentos com o mesmo codificador (NVENC, ou x264 se a máquina não tiver), sem quadros B.
- Codificar um bloco/junção do mini-spec (1280×720, NVENC): ver os tempos `codificado em … s` no log da montagem
  (`relatorio.json` → `blocos.segmentos[].segundos_codificar`).

## Vídeo final (fase 7c; `--final`)
`montar.py <pasta> --final --registrar --progresso` (o motor do painel roda; ver `../docs/painel.md` "Fase 7c"):
- 1920×1080, 60 q/s, o MESMO caminho do rascunho (trechos por cena com cache por hash em `trechos/<cena>_<hash>_1920x1080.mp4`,
  blocos `blocos/final_<hash>.mp4`, concat sem recodificar, mixagem única). Trechos intermediários x264 CRF 10; blocos
  NVENC CQ 16 (x264 `slow` CRF 15 sem NVENC). Áudio AAC 320k.
- Narração: SÓ a gravação limpa do card (`<projeto>/trabalho/gravacao/limpa.wav`); sem ela, `NaoMonta` (a
  `narracao.wav`/voz guia nunca entra no final). Loudness: −14 LUFS e limitador −1,5 dBFS, medida de novo no MP4.
- Codificador: sonda do NVENC (`blocos.codec`); falhou → x264. NVENC que passa na sonda e cai num bloco
  (`blocos.TrocaCodec`) → o vídeo inteiro é refeito em x264 (concat sem recodificar exige um codificador só), com aviso.
  `F1_SEM_NVENC=1` faz o ffmpeg recusar o NVENC de verdade (preset inexistente), para testar a máquina sem NVENC.
- `--progresso`: `PROG <fração> <texto>` (cenas até 55 %, mixagem, "bloco k de N" até 92 %, junção, verificação).
- `--registrar` no final grava `<pasta>/final/final.json` (resumo, loudness do master e do MP4, codificador, blocos
  refeitos/do cache, créditos dos SFX CC BY, `spec_hash`) ou `final/falhou.json`; NÃO mexe no estado.json (o render é
  a etapa "Render" do card). O vídeo sai em `<pasta>/final/final.mp4` e o motor move para `saida/final_vN.mp4`.
- Cena mudou depois do final → só o trecho dela, o bloco dela e as junções vizinhas são refeitos (ver teste).

## Storyboard (fase 7b; `storyboard.py`)
Prévia de uma cena = o PRÓPRIO trecho dela (mesmo cache por hash do rascunho, 1280×720) + quadros JPG (480 px) nos
momentos-chave: início, âncoras dos kits (`ritmo`, anotação…), SFX e fim (`storyboard/<cena>_<hash>_q<N>.jpg`).
`python storyboard.py <pasta> previa <id,id|todas>` roda em processo à parte (o painel dispara; `gerando.json` trava,
`fila.json` junta pedidos que chegam durante o render, `falhas.json` guarda o motivo por cena). ★ da cena =
`aprovacoes.json` {cena: hash}; mudou a cena → hash novo → "desatualizada". `montar.planejar(por_cena=True)` dá o plano
mesmo com cenas sem receita (o motivo fica na cena).

Movimento de câmera da cena (ação direta `movimento` na SPEC): `movimento.js`, o MESMO cálculo nos dois motores
(Remotion: wrapper na `CenaDoc`; HyperFrames: transform no canvas do `gps.html`), suave (cosseno) ao longo dos quadros
puros da cena; parado durante a transição de entrada (os `pre` quadros seguram o quadro 0).

## Receitas (o que já sabe renderizar)
| motor | kit | cena |
|---|---|---|
| remotion | `graficos` | 1 gráfico do kit em tela cheia (`tipo`, `sessao`, `a`, `b`, `trecho`, `dur`, `ritmo[{em,i,d}]` → tempo da palavra) |
| remotion | `anotacao` | `texto` da cena centralizado (caixas medidas na fonte real) + `oval`/`sublinhado`/`riscado`/`corrigido` na palavra `i` |
| hyperframes | `gps` | carros pelo GPS (`sessao`, `carros`, `fator`, `inicio` = s da volta no 1º quadro, `camera_gps` perseguicao/fixa/alta, `rastro`, `hud`, `nota`); pista .glb ou plana conforme a volta; carro por equipe (`receitas.CARROS`); HUD com sigla + km/h por carro e rodapé "tempo real/acelerado N×/câmera lenta N× · Dados: OpenF1 · …"; rodada 1: `mundo` (chão em ladrilhos, zebras, arquibancadas, prédios, placa da curva: `kit/gps/src/gps_mundo.js`), `minimapa`, `etiquetas` (sigla presa a cada carro), carro de trás em fantasma quando colados, `curvas` (das numeradas em `kit/graficos/pista`), `rotulos: [{em, texto}]` e `marcar: [{em, dur}]` (HUD segura a velocidade da palavra) |
| remotion | `cartoes` | cartão de capítulo em tela cheia (`tipo: capitulo`, `numero`, `titulo`, `sessao` → traçado da comparação da sessão); `tipo: duelo` = dois números lado a lado na cor de cada equipe (`titulo`, `sessao`, `unidade`, `destaque`, `lados: [{piloto, valor, em}]`, `rodape`), cada número entra na própria palavra; pessoa e tag ainda sem receita |
| remotion | `foco` | desfoca tudo menos o `alvo` (índice de um `texto` da cena ou caixa {x,y,w,h}); entra na palavra `em`; traços à mão ficam nítidos por cima |

Uso real (card "Nove milésimos", 2026-11-14): `F1_RENDER_PARALELO` (padrão 3) renderiza os lotes do Remotion e as cenas
do HyperFrames ao mesmo tempo; o rascunho usa a voz guia (`trabalho/voz_guia.wav`) quando não há gravação; a
verificação do SFX mede o pico contra o PRÓPRIO som (o `pico_s` do catálogo errado vira aviso; 12 itens corrigidos).

Qualquer outro par motor × kit (imagens, cartões, foco, modelo3d, gps no Remotion, gráficos no HyperFrames, cena só de
texto) dá **erro claro** (`SemReceita`), nunca uma cena "parecida". Arquivo faltando dá `FaltaAtivo` com o comando.

## Mixagem
SFX da SPEC (`categoria` + palavra `i` + `ponto`) e das transições (whoosh no pico do wipe/zoom) pelo `Banco` do kit/sfx
(mesma escolha de variação e âncora = pico do som). Banco: `kit/sfx/banco` desta cópia ou da pasta principal (fora do Git).
Um grafo do ffmpeg: voz 0 dB, trilha levada a −26 LUFS e abaixada sob a voz (sidechain), SFX com o ganho do kit. Mede
(ebur128) → ganho para **−14 LUFS** (a referência da voz limpa) → limitador a −1,5 dBFS com 4× de sobreamostragem → mede de novo.

## Verificação (`quadros.py`, grava `verificacao_montagem.json`)
Formato (60/1 CFR, quadros = soma das cenas, resolução, áudio = duração); por cena, 1º/meio/último quadro puro = o
quadro certo do trecho (deslocamento −2..+2, PSNR); por junção, 2 quadros antes a 2 depois da transição = esperado, sem
quadro preto nem repetido; SFX isolados com o pico (RMS 10 ms) na âncora (12–15 ms; whoosh/riser 150 ms, só aviso);
áudio do MP4 × master (correlação cruzada ≤ 1 ms); loudness do MP4. Folhas: `folha_cenas.jpg`, `folha_juncao_NN_<tipo>.jpg`.

## Painel
Etapa Rascunho do card documentário: `diretor/painel.py` roda `planejar` (rápido, sem render). Faltou algo → 409 com a
lista ("não dá para montar: cena … falta …"). Senão dispara `montar.py --registrar` num processo à parte, marca
`andamento` e o montador grava `gerado` (★ pendente) ou `falhou` com o motivo. A tela mostra o vídeo (`/api/arquivo`).

## Teste (2026-11-13)
`.venv\Scripts\python.exe F1\horizontal\testes\montador\testar.py` (~2 min, internet para gsap/three do CDN na cena HyperFrames):
mini-spec de 3 cenas de 3 s — gráfico de velocidade Monza 2025 Q LEC×HAM (Remotion, corte, impacto) → GPS dos dois
carros na pista plana de Monza (HyperFrames, wipe 24 q) → "0,117 s" com oval (Remotion, zoom 30 q, pop). Narração e
trilha **sintéticas** (ruído com envelope de sílaba e acorde; nenhuma voz de IA). Resultado: 26/26 —
540 quadros 60/1, 180 por cena, quadros puros no deslocamento 0, junções PSNR ≥ 38 dB sem preto/repetido, SFX
impacto +5,6 ms / whoosh −1,3 e +12,5 ms / pop +7,0 ms, áudio × master 0 ms, −14,0 LUFS e −2,1 dBTP no MP4;
2ª montagem toda do cache; texto da c3 mudado → só a c3 renderizada; cena por demanda; mensagens de falta; gancho do
painel ponta a ponta (passo → processo à parte → `gerado` → ★). Folhas olhadas: `testes/montador/folha_*.jpg`.

### Fase 7b (2026-11-13): 55/55
O mesmo teste, agora com blocos de teto 4 s (cada cena um bloco, wipe e zoom como junções): 3 blocos + 2 junções; as 2
cenas Remotion num lote só (1 invocação `LoteDoc`, 0 `CenaDoc`); vídeo final = pacotes dos segmentos (só os quadros-chave
ganham SPS/PPS do concat, +49 bytes; quadros decodificados idênticos); 2ª montagem 0 blocos codificados; texto da c3
mudou → só a junção c2→c3 e o bloco da c3 recodificados; teto padrão → 1 bloco. Codificar: bloco de ~2,7 s em 0,6–0,9 s,
junção de 0,3–0,5 s em 0,4–0,5 s, bloco de 9 s em 1,7 s (NVENC 1280×720). Storyboard: prévia de cenas já montadas sai do
cache (sem render), quadros 480×270 nos momentos-chave, ★ da cena (recusada sem prévia), movimento na c1 → só a c1
afetada, SPEC segue aprovada e o rascunho fica desatualizado, movimento na c2 (HyperFrames) só a c2, entrada da c3 vira
fade → c2 e c3, trocar SFX → nenhuma, ação fora da lista e corte inválido recusados, prévia nova da c1 renderiza só ela e
o zoom aparece no quadro, montagem depois das ações aprovada na verificação por quadro (movimento nos 2 motores + fade),
SFX trocado na mixagem, pedido por voz vira prompt só da c2.

### Fase 7c (2026-11-13): 81/81 (55 + 26 da seção 7)
Vídeo final DE VERDADE do mini-spec, com a "gravação limpa" = a narração sintética copiada para
`trabalho/gravacao/limpa.wav` (o caminho e a regra são os do final; a voz é de teste): final barrado sem a gravação, com
a voz guia valendo, sem todas as cenas ★, com a verificação reprovada (o mini-spec à mão tinha história sem esquema,
hashes velhos e um "2025" na tela que não é dito: o portão pegou) e com o texto da c3 mudado (★ de novo). Comando do
motor (`--final --registrar --progresso`): **9 s de 1080p60 em 76–78 s** (3 cenas renderizadas em 1920×1080, 1 bloco
NVENC), ffprobe 1920×1080 60/1 540 quadros, áudio 9,0 s, verificação por quadro aprovada, **−14,0 LUFS e pico −2,5 dBTP
medidos no MP4**, PROG crescente cena a cena/bloco a bloco até 1,0. `F1_SEM_NVENC=1`: sonda recusada pelo ffmpeg →
todos os blocos em x264 (SEI `x264 - core` no MP4), aprovado; NVENC aceito na sonda e recusado no 1º bloco → aviso
"NVENC falhou no segmento 0… refazendo em x264" e vídeo inteiro em x264, aprovado. Correção pós-final (movimento na
c3): ponte acusa final desatualizado, final barrado até o ★ da c3, depois só a c3 renderizada em 1080p e só a junção
c2→c3 + o bloco da c3 recodificados. Folhas: `testes/montador/final_folha_*.jpg` (olhada a de cenas).

## O que NÃO foi verificado
- **Nenhum vídeo real** nem SPEC escrita pelo diretor/modelo; só o mini-spec à mão. Narração real (limpa.wav) e trilha real não usadas.
- **Ninguém assistiu/ouviu** o MP4 com atenção de editor: conferi as folhas e alguns quadros soltos. A trilha
  sintética e a voz sintética não dizem nada sobre o equilíbrio real voz × trilha × SFX.
- (até a 7b) `--final` não tinha sido rodado; na 7c rodou no mini-spec (ver "Fase 7c" no Teste), NVENC e x264 exercitados.
- Desempenho em 20 min (≈ 70 cenas): não medido. A mixagem abre um arquivo por SFX no ffmpeg (OK para ~200).
- No GPS de Monza os dois carros ficam quase sobrepostos na perseguição (o kit anda cada um no próprio GPS): visto, não mexido.
- Receitas para graficos/anotacao/cartoes(capítulo)/foco (Remotion) e gps (HyperFrames); imagens, modelo3d, pessoa e tag recusam.
- (fase 5) A tela do Rascunho não tinha sido vista no navegador; na 7b o storyboard foi visto na porta 8799 (dados fictícios).
- 7b: blocos e lotes medidos só no mini-spec (3 cenas de 3 s); nenhum vídeo de 20 min. Lote do HyperFrames não existe.
  Movimento de câmera: só conferido que muda os quadros e passa na verificação; ninguém julgou se 8 %/12 % fica bonito.
  O microfone por cena não foi gravado de verdade (sem microfone no teste): é o mesmo ditado das Observações (34/34).
