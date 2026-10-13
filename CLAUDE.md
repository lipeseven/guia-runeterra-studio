# Guia de Runeterra Studio

Assistente local de edição de vídeos para o canal **Guia de Runeterra** (lore de League of Legends,
PT-BR, vídeos longos ~20 min). Usuário: Felipe. Converse em **português**.

**Leia antes de mexer:** [docs/arquitetura.md](docs/arquitetura.md) (fluxo, componentes, fases),
[docs/guia_de_estilo.md](docs/guia_de_estilo.md) (estilo do canal),
[docs/regras_de_direcao.md](docs/regras_de_direcao.md) (regras do diretor — todo ajuste fino do Felipe entra aqui).

## Princípios (não negociáveis)
- Tudo **local e gratuito**; o único pago é o Claude (plano **Pro**, sem API → usar `claude -p`, economizar cota).
- **Não parecer produção em massa** (medo de desmonetização): voz real do Felipe, pontos de controle humanos,
  efeitos sempre variados (nunca o mesmo efeito em tudo), memória de uso de mídias.
- **Inspiração, não cópia** do canal de referência (@explainedbynavi): só fatos/temas, detector de semelhança.
- Voz de IA (voz guia) **nunca** vai para o vídeo publicado.
- Direção **ancorada em palavras**, não em segundos (trocar a narração ressincroniza tudo).
- Arquivos do acervo do Felipe nunca são movidos/alterados.

## Onde fica cada coisa
- `projeto.toml` — caminhos (acervo em `C:\Users\Felipe\Downloads\catálogo sequencial LOL`). `.env` — chaves (fora do Git).
- `tools/` — scripts Python (rodar com `.venv\Scripts\python.exe`): `analise_referencias/`, `acervo/`
  (inventário, busca CLIP, tomadas de clipes, etiquetas), `capa.py` (detecta ícones na capa), `direcao/variacao.py`
  (editor de variedade), `prototipo/preparar.py`.
- `app/video/` — Remotion (React/TS): cenas em `src/cenas/`, efeitos em `src/efeitos.tsx`.
  `npx remotion studio` para visualizar; `npx remotion render <Composição> saida.mp4`.
- `dados/` (fora do Git) — `acervo.db` (SQLite: `midias`, `tomadas`), miniaturas, índices CLIP, análises, renders.

## Ambiente (Windows)
RTX 4060 8 GB, 16 GB RAM, Ryzen 7 5700X3D. Python 3.12 (.venv com faster-whisper, torch CUDA, open_clip, opencv),
Node 24, FFmpeg 9 (NVENC; filtros longos via `-/filter_complex arquivo.txt`; `drawtext` precisa de `fontfile`).
O caminho do scratchpad excede MAX_PATH para Python — passar scripts por stdin.
Repositório privado: github.com/lipeseven/guia-runeterra-studio (gh logado como lipeseven).

## Estado atual
- Fase 0 (base: análise, guia de estilo, acervo catalogado) ✅
- Fase 1 (protótipo Remotion: capa, cartão, recorte, tela cheia, diálogo, citação, mosaico, clipe; efeitos variados) ✅
- Fase 2 (áudio) ✅ — `tools/audio/`: `voz_guia.py` (Fish s2.1-pro-free → reserva local Piper; Edge TTS caiu),
  `limpar_gravacao.py` (fala cortada por volume e transcrita trecho a trecho — o Whisper com o áudio inteiro "corrige"
  falsos começos; regravações, falas fora do roteiro, pausas, -14 LUFS; ruído de fundo do Felipe é ~-80 dB, não aplicar
  denoise), `alinhar.py` (tempos por palavra DO ROTEIRO → a direção usa índices do roteiro; trocar áudio = trocar tabela).
- Fase 3 (diretor) ✅ — `tools/direcao/`: `claude_cli.py` (Claude Code headless enxuto: `--tools "" --setting-sources ""
  --strict-mcp-config`, ~800 tokens de base; imagens via stream-json; log em dados/uso_claude.jsonl), `planejar.py`
  (1ª passada, texto), `candidatos.py` (busca local CLIP+etiquetas, folhas), `escolher.py` (2ª passada, imagens),
  `montar.py` (direção final + render da composição "Video" com --props), `revisar.py` (refaz só cenas com pedido).
- Painel (Fase 5 adiantada) ✅ — `app/servidor/` (FastAPI+SQLite dados/studio.db; `motor.py` = fila/orquestrador;
  `storyboard.py`), `app/painel/` (React/Vite). Fluxo pelo painel: Ideia → mover p/ Roteiro → .txt → aprovar → voz guia
  → capa → aprovar → Direção automática (retoma de onde parou) → rascunho → storyboard (ajustes/pedidos) → novo rascunho.
- 2026-10-13: sistema zerado para o Felipe testar "como se estivesse pronto" e anotar bugs (banco, projetos e testes
  foram para a Lixeira; acervo catalogado mantido).
- Card Gravação ✅ — mover p/ Gravação aceita o rascunho e pede o arquivo (upload com progresso ou pasta entrada/ +
  "Já coloquei na pasta"); motor: limpar → alinhar → montar com a voz real → saida/final_vN.mp4 → card vai p/ Revisão.
  Rascunhos e finais: cada versão em arquivo próprio (nunca renomear arquivo que pode estar aberto no player).
  Gravação tem ponto de controle: limpeza PARA em "Confira a gravação limpa"; só a aprovação dispara ressinc + render.
- Card Publicação ✅ — "Vídeo aprovado" → `app/servidor/publicacao.py` (5 títulos, descrição com capítulos reais
  [≥3 seções] + créditos de autores + aviso Legal Jibber Jabber, tags, comentário fixado; Claude sonnet) + thumbnail
  1280×720 da capa. "Marcar como publicado" (ou arrastar p/ Publicado) registra mídias em `uso_midia` (acervo.db; o
  diretor penaliza as dos últimos 3 vídeos) e abre a limpeza (trabalho/saída/entrada → Lixeira; direcao/ sempre fica).
- **Fluxo completo de ponta a ponta ✅ (2026-10-13).** Próximos: efeitos sonoros (Freesound + Stable Audio Open),
  falas PT-BR de um site de fã, Pesquisa (referência → fatos → detector de semelhança), Mídias da internet,
  exportação para Premiere/DaVinci (XML) e After Effects (script).
