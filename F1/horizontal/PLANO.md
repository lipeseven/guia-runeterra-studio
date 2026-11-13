# PLANO e estado do motor documental horizontal

Memória entre sessões. Atualize a cada marco. Arquitetura em `ARQUITETURA.md`.

## Autonomia (Felipe, 2026-11-13, ao dormir)
Autorizado a continuar SEM perguntar nada, assim que a janela de 5 h resetar e a cada reset seguinte, até o fim das fases.
Decisões de detalhe são do orquestrador. Regras que continuam valendo: o repositório só recebe mudanças por PR pequeno com merge
logo após o PR (memória `feedback-merge-sozinho`); vertical existente não pode quebrar; nada global instalado; painel 8766 e
8765 não são reiniciados à força; pedidos explícitos do Felipe valem mais que regras pré-setadas.

## Cota
Parar a 94% da janela de 5 h (salvar estado aqui e esperar o reset; um cron de sessão retoma). Semana: gastar livremente até 92%.
Janela de 5 h de 2026-11-13 resetou/reseta ~06:20 local; semanal 11:00. Medir com `get_usage` antes de cada lote.
Subagentes: Opus 5.5 médio (`model: opus`); Fable 5.2 só até 2026-11-16 e só para modelagem 3D (não necessário agora).

## Fases e critério de pronto
- [x] **0 Esqueleto e docs** (`F1/horizontal/`, `F1/vertical/README.md`, ARQUITETURA, PLANO).
- [ ] **1 Kit core** (4 módulos independentes, em paralelo de 2 em 2 por causa da cota):
  - [x] `kit/gps` (PR f1-horizontal-kit-gps; ver `kit/gps/README.md`; teste e folhas em `testes/gps/`): carro pelo GPS do OpenF1, interpolação monotônica sem vai-e-vem, sem sumir, apoiado no asfalto (pista real `interlagos_sao_paulo.glb`), rastro por equipe, dois carros podem se sobrepor. Pronto = folha de sequência a 60 q/s sem tranco + teste automático de monotonicidade/altura + uso nos 2 motores em exemplo mínimo.
  - [x] `kit/sfx` (2026-11-13, PR `f1-horizontal-kit-sfx`; 66 sons, testes ok; falta o Felipe OUVIR e reprovar o que não servir): banco por categoria (impacto, riser/crescendo, clique, tecla, sino, whoosh, pop, alerta) reunindo o melhor dos sons dos testes (`C:\Users\Felipe\teste-motores\remotion` e `\hyperframes`, procurar `tools/trilha*`/`sfx*`/assets) e sons livres (CC0) + sintetizados; API por palavra, volume/duração por categoria, normalização medida. Pronto = banco com ≥ 5 variações por categoria, catálogo JSON, teste de loudness estéreo.
  - [x] `kit/anotacao` (2026-11-13, PR `f1-horizontal-kit-anotacao`; caixa estável + `caixaEnvelope`, texto à mão por traço da Caveat; `testes.ts` 12/12 e render nos 2 motores com oval constante a 1 px; falta o Felipe VER as folhas em `testes/anotacao/`): oval aberto/perninha, seta, sublinhado, chave, riscado, número corrigido, traço de fonte à mão (estilo do teste HyperFrames), ancorado em caixa ESTÁVEL; verificação automática (caixa do oval × caixa da peça, sem cruzar texto, tamanho constante). Pronto = folha de sequência e checagem por script nos 2 motores.
  - [x] `kit/imagens`: busca de trechos/imagens reais com yt-dlp e VALIDAÇÃO (volta/piloto/sessão batem com a afirmação), créditos em FONTES.txt. Pronto = exemplo que acerta a volta pedida. (2026-11-13, PR `f1-horizontal-kit-imagens`: contador da TV por OCR × relógio da sessão do OpenF1; LEC volta 55 = `nao_encontrado` em vídeo oficial, nunca a volta 1; HAM volta 62 validado; 57 testes offline + `--rede`. Ver `kit/imagens/README.md`.)
- [ ] **2 Kit gráficos + foco + cartões + transições**: velocidade×distância com gap, setores, delta, telemetria (freio/marcha), gráfico normalizado claro; blur de foco; cartões de pessoa/capítulo; transições medidas.
  - [ ] `kit/graficos`.
  - [x] `kit/foco` (2026-11-13, PR `f1-horizontal-kit-foco-cartoes`; `testes.ts` 30/30; render nos 2 motores: peça com diferença 0 com × sem foco, fundo desfocado; falta o Felipe VER `testes/foco/`).
  - [x] `kit/cartoes` (mesmo PR; pessoa, capítulo, tag com perninha; layout sem navegador, `testes.ts` 1017/1017; tag nunca fora da margem, texto dentro das caixas medido em pixel; falta o Felipe VER `testes/cartoes/`).
  - [x] `kit/transicoes` (mesmo PR; corte/fade/wipe/zoom 0/18/24/30 quadros medidos em pixel nos 2 motores; pico do SFX ≤ 8 ms do quadro de pico no MP4; falta o Felipe VER/OUVIR `testes/transicoes/`).
- [ ] **2b Generalização (diretriz do Felipe: QUALQUER vídeo de F1, não um GP)**: `kit/gps` sem depender de modelo 3D (traçar a pista pelo próprio GPS do OpenF1, alinhar a qualquer pista com modelo, outra pista de teste); `kit/imagens` e gráficos sem GP/piloto fixos; teste com 2ª sessão/pista.
- [ ] **3 Diretor documental** (`diretor/`): `historia.py`, `spec.py` (por palavra, com motor por cena), `ativos.py`, `verificar.py`; protocolo de arquivos (`estado.json`).
- [ ] **4 Painel**: etapas História/SPEC/Ativos/Verificação/Rascunho no card horizontal + telas de aprovação e pedidos por cena; ganchos mínimos em `app/`.
- [ ] **5 Montador + primeiro vídeo completo** (ex.: roteiro do teste "1,481 s"), comparado aos dois testes.
- [ ] **6 Reorganização do vertical** em `F1/vertical/` (docs e atalhos; `canal.toml`, painel e `CLAUDE.md` no mesmo PR; render de validação).

## Estado atual
Fase 0 pronta (não commitada ainda). Fase 1: aguardando reset da janela de 5 h (~06:20) para o 1º lote (gps + sfx).
Insumos já gravados: `C:\Users\Felipe\teste-motores\remotion\APONTAMENTOS_FELIPE.md` e `\hyperframes\APONTAMENTOS_FELIPE.md`; memórias `feedback-teste-remotion-vs-hyperframes`, `feedback-60fps`.

## Diário
- 2026-11-13 04:3x: esqueleto, ARQUITETURA e PLANO escritos; cron de retomada agendado.
- 2026-11-13 ~07h: kit/gps pronto (relógio pela velocidade da telemetria ancorada ao GPS, altura por raio na malha, exemplos Remotion e HyperFrames com a mesma cena; teste automático OK em 4 voltas).
- 2026-11-13: kit/sfx construído (banco fora do Git, `gerar.py` regera; exemplo de 20 s renderizado em numpy, ffmpeg, Remotion e HyperFrames).
- 2026-11-13: kit/anotacao construído (núcleo TS sem dependências, adaptadores `remotion/anotacao` e `hyperframes/anotacao`, `testes/anotacao/rodar.py` renderiza nos dois motores e mede nos pixels).
- 2026-11-13: kit/foco, kit/cartoes e kit/transicoes construídos (núcleo TS + adaptadores Remotion/HyperFrames + `testes/<modulo>/rodar.py` sobre `testes/motores.py`; tudo parametrizado, nada fixo de GP/piloto/equipe).
- 2026-11-13: `kit/imagens` pronto (PR não mesclado). `rapidocr-onnxruntime` instalado no `.venv`.
