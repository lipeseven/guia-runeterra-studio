# montador/ — cenas por motor + transições + UMA mixagem (fase 5: só a ferramenta)

Lê `spec.json` (e o `estado.json`) do projeto, renderiza cada cena no motor marcado nela (Remotion ou HyperFrames) como
trecho de 60 q/s, junta os trechos com as transições do `kit/transicoes` e faz uma mixagem só (narração + trilha + SFX
do `kit/sfx` por âncora de palavra), com loudness medida. Depois verifica o MP4 por quadro e por amostra de áudio.
**Nenhum vídeo completo foi montado** (decisão do Felipe): só o mini-spec de teste de 3 cenas.

```
spec.json + palavras.json ─▶ receitas.py (cena → pedido de render, hash) ─▶ segmentos.py (motor → trecho MP4, cache)
                                    transicoes.mjs (estados do kit) ─▶ juncao.py (quadros intermediários + 1 passada ffmpeg)
                          mixagem.py (SFX + narração + trilha → master.wav medido) ─┘      quadros.py (verificação + folhas)
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
  passada do ffmpeg (filtro por arquivo, `-/filter_complex`), `setpts=N/(60·TB)`, CFR.
- Cache: hash = pedido de render (params resolvidos, tempos, pre/pos) + conteúdo dos dados (comparação, voltas, pista,
  modelos) + código (receita, adaptador, núcleo do kit). Mudou uma cena → só ela é renderizada de novo.

## Receitas (o que já sabe renderizar)
| motor | kit | cena |
|---|---|---|
| remotion | `graficos` | 1 gráfico do kit em tela cheia (`tipo`, `sessao`, `a`, `b`, `trecho`, `dur`, `ritmo[{em,i,d}]` → tempo da palavra) |
| remotion | `anotacao` | `texto` da cena centralizado (caixas medidas na fonte real) + `oval`/`sublinhado`/`riscado`/`corrigido` na palavra `i` |
| hyperframes | `gps` | carros pelo GPS (`sessao`, `carros`, `fator`, `inicio` = s da volta no 1º quadro, `camera_gps` perseguicao/fixa, `rastro`); pista .glb ou plana conforme a volta; carro por equipe (`receitas.CARROS`) |

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

## O que NÃO foi verificado
- **Nenhum vídeo real** nem SPEC escrita pelo diretor/modelo; só o mini-spec à mão. Narração real (limpa.wav) e trilha real não usadas.
- **Ninguém assistiu/ouviu** o MP4 com atenção de editor: conferi as folhas e alguns quadros soltos. A trilha
  sintética e a voz sintética não dizem nada sobre o equilíbrio real voz × trilha × SFX.
- `--final` (1920×1080) não foi rodado; o vídeo final do teste saiu em h264_nvenc (x264 é a alternativa automática se o NVENC falhar; não exercitada).
- Desempenho em 20 min (≈ 70 cenas): não medido. A mixagem abre um arquivo por SFX no ffmpeg (OK para ~200).
- No GPS de Monza os dois carros ficam quase sobrepostos na perseguição (o kit anda cada um no próprio GPS): visto, não mexido.
- Receitas só para graficos/anotacao (Remotion) e gps (HyperFrames); o resto recusa.
- A tela do painel (TSX) passou no `tsc`, mas o `app/painel/dist` NÃO foi recompilado e a tela não foi vista no navegador.
