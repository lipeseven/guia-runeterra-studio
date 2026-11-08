# Guia de Runeterra Studio

Assistente local de edição de vídeos para o canal **Guia de Runeterra** (lore de League of Legends,
PT-BR, vídeos longos ~20 min). Usuário: Felipe. Converse em **português**.

**Leia antes de mexer:** [docs/arquitetura.md](docs/arquitetura.md) (fluxo, componentes, fases),
[Runeterra/docs/guia_de_estilo.md](Runeterra/docs/guia_de_estilo.md) (estilo do canal),
[Runeterra/docs/regras_de_direcao.md](Runeterra/docs/regras_de_direcao.md) (regras do diretor — todo ajuste fino do Felipe entra aqui).

## Princípios (não negociáveis)
- Tudo **local e gratuito**; o único pago é o Claude (plano **Pro**, sem API → usar `claude -p`, economizar cota).
- **Não parecer produção em massa** (medo de desmonetização): voz real do Felipe, pontos de controle humanos,
  efeitos sempre variados (nunca o mesmo efeito em tudo), memória de uso de mídias.
- **Inspiração, não cópia** do canal de referência (@explainedbynavi): só fatos/temas, detector de semelhança.
- Voz de IA (voz guia) **nunca** vai para o vídeo publicado. Exceção decidida pelo Felipe (2026-11-01): vídeos verticais do Explicando F1, com voz gerada por ele.
- Direção **ancorada em palavras**, não em segundos (trocar a narração ressincroniza tudo).
- Arquivos do acervo do Felipe nunca são movidos/alterados.

## Onde fica cada coisa
- **Raiz = sistema compartilhado** (`app/`, `tools/`, `docs/`, `dados/comum/`). **Cada canal tem a própria pasta na raiz** (2026-11-01):
  `Runeterra/` = `canal.toml`, `docs/`, `Iniciar Runeterra.bat` e `dados/` (fora do Git):
  (studio.db, acervo.db, acervo/, acervo_internet/, projetos/, referencias/, analise_referencias/,
  aprendizado/, encerramento/, pesquisa_cache/, roteiros/ = .txt do Felipe, "escolher da pasta" no Roteiro) e `dados/comum/` (modelos, cache_voz, sfx, motor.lock, uso_claude.jsonl;
  `canal.DADOS_COMUM`). Canal novo = pasta nova na raiz com `canal.toml` (`canal._perfis` procura `*/canal.toml`); caminho de arquivo de projeto para o painel:
  `motor.caminho_rel(slug, ...)` (nunca escrever "projetos/..." à mão).
- `docs/instalacao.md` — reinstalar do zero (formatar o PC): backup, programas, `requirements.txt`, npm.
- `projeto.toml` — parâmetros do sistema (o acervo do canal está em `canal.toml`: `C:\Users\Felipe\Downloads\canais\catálogo sequencial LOL`). `.env` — chaves (fora do Git).
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

## Estado e detalhes por área
O histórico detalhado de cada recurso fica no arquivo da área. **Antes de mexer numa área, leia o arquivo dela**
(só o da área: não precisa ler todos). Ao terminar um recurso, registre lá, não aqui.
- Painel, fluxo dos cards (gravação, publicação, excluir, progresso), áudio, perfil de canal, celular → [docs/estado/sistema.md](docs/estado/sistema.md)
- Diretor do Runeterra, storyboard, render por blocos, efeitos visuais e sonoros, aprendizado entre vídeos → [docs/estado/direcao.md](docs/estado/direcao.md)
- Roteirista, pesquisa antes do roteiro, conferência de fatos → [docs/estado/roteiro.md](docs/estado/roteiro.md)
- Acervo (atualizar, CLIP, etiquetas), referências analisadas, mídias da internet → [docs/estado/acervo.md](docs/estado/acervo.md)
- **Explicando F1** (vertical, horizontal, modelos 3D, briefing, fotos de pessoas) → [F1/docs/estado_f1.md](F1/docs/estado_f1.md)

Resumo: Runeterra com fluxo completo de ponta a ponta ✅ (Fases 0–3 e painel). F1 em construção: vertical ✅, horizontal
no padrão v1 (biblioteca + diretor) e em teste de método com HyperFrames (`C:\Users\Felipe\hyperframes-teste`, isolado).
Próximos (Runeterra): falas PT-BR de site de fã, detector de semelhança, exportação para Premiere/DaVinci (XML) e After Effects.
