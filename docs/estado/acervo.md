# Estado: acervo, referências e mídias da internet

Saído do CLAUDE.md (2026-11-08). Ao terminar um recurso desta área, registre AQUI, não no CLAUDE.md.

- Referências 100% analisadas (2026-10-14): som (`separar_sons.py` Demucs + `analisar_sons.py` CLAP — padrão é voz
  pura, efeito é raro) e leitura visual dos 11 vídeos → guia de estilo v1.0 (seção 10: modos por vídeo e recursos
  que ainda faltam no Remotion). Stable Audio Open (diffusers, ~30 s/efeito, 5,9 GB VRAM) e Freesound prontos.
- Atualizar acervo ✅ (2026-10-17): `tools/acervo/atualizar.py` (inventário → CLIP → tomadas → etiquetas pelo nome do
  arquivo; incremental, sem cota). Tarefa global "acervo" (vid 0) na fila do motor: botão "Atualizar acervo" no topo
  do painel e automática a cada card NOVO (o acervo muda pouco). Resultado em `/api/acervo/situacao`.
- Mídias da internet ✅ (2026-10-19): acervo baixado fica em `Runeterra/dados/acervo_internet/` (fora da pasta do Felipe;
  caminho ABSOLUTO no acervo.db, `inventariar.PASTAS_EXTRA`). `tools/acervo/importar_riot.py` (splash de todas as
  skins via CommunityDragon + splash base 1920 e artes dos contos do Universe; categoria splash/skin/arte, descarta o
  que o Felipe já tem; tarefa "importar_riot"). Storyboard: "buscar na internet" (`app/servidor/internet.py`:
  DuckDuckGo `ddgs` + Wikimedia Commons; baixa e cataloga na hora) e "colar link" de vídeo (yt-dlp → tomadas, tarefa
  "clipes"; início/fim opcionais = baixa só o trecho, `--download-sections`). Gravação por capítulos: vários arquivos em entrada/ são juntados na ordem dos nomes.
