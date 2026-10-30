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
- **Raiz = só código** (`app/`, `tools/`, `canais/`, `docs/`) + `Iniciar Runeterra.bat` / `Iniciar Pokemon.bat`.
  **Tudo que não é código fica em `dados/`** (fora do Git; reorganizado em 2026-10-30): `dados/runeterra/` e
  `dados/pokemon/` (studio.db, acervo.db, acervo/, acervo_internet/, projetos/, referencias/, analise_referencias/,
  aprendizado/, encerramento/, pesquisa_cache/, roteiros/ = .txt do Felipe, "escolher da pasta" no Roteiro) e `dados/comum/` (modelos, cache_voz, sfx, motor.lock, uso_claude.jsonl;
  `canal.DADOS_COMUM`). Caminhos dos canais em `canais/<chave>/canal.toml`; caminho de arquivo de projeto para o painel:
  `motor.caminho_rel(slug, ...)` (nunca escrever "projetos/..." à mão).
- `docs/instalacao.md` — reinstalar do zero (formatar o PC): backup, programas, `requirements.txt`, npm.
- `projeto.toml` — caminhos (acervo em `C:\Users\Felipe\Downloads\canais\catálogo sequencial LOL`). `.env` — chaves (fora do Git).
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
  --strict-mcp-config`, ~800 tokens de base; imagens via stream-json; log em dados/comum/uso_claude.jsonl), `planejar.py`
  (1ª passada, texto), `candidatos.py` (busca local CLIP+etiquetas, folhas), `escolher.py` (2ª passada, imagens),
  `montar.py` (direção final + render da composição "Video" com --props), `revisar.py` (refaz só cenas com pedido).
- Painel (Fase 5 adiantada) ✅ — `app/servidor/` (FastAPI+SQLite dados/runeterra/studio.db; `motor.py` = fila/orquestrador;
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
  1280×720 da capa. "Marcar como publicado" (ou arrastar p/ Publicado) registra mídias em `uso_midia` (acervo.db; histórico —
  repetir imagem ENTRE vídeos não tem problema; dentro do vídeo, imagem já escolhida desce na busca: `Acervo.usadas_no_video`) e ARQUIVA (pede confirmação): tudo vai para a Lixeira, só fica
  `dados/runeterra/projetos/<slug>/capa.*` para o card. Publicado é definitivo: não sai da coluna, página vira resumo (capa, link, histórico).
- Referências 100% analisadas (2026-10-14): som (`separar_sons.py` Demucs + `analisar_sons.py` CLAP — padrão é voz
  pura, efeito é raro) e leitura visual dos 11 vídeos → guia de estilo v1.0 (seção 10: modos por vídeo e recursos
  que ainda faltam no Remotion). Stable Audio Open (diffusers, ~30 s/efeito, 5,9 GB VRAM) e Freesound prontos.
- Novos recursos visuais ✅ (2026-10-14): `hub` (transição de seção: grade/esteira), `dividida`, `lista`, `meio`,
  `texto`, `citacao` (agora ligada ao diretor), nome sobre arte (telacheia rotulo/subrotulo), clarão, crédito de fan
  art na cena (midias.autor). **Fundo branco é a assinatura do canal**: o vídeo é sempre "claro" (o tema escuro de
`app/video/src/tema.ts` existe mas não é usado); escuro só em telas cheias e no `texto` com fundo escuro, raro. Peças de
  mosaico/dividida/lista ficam em `pecas` (planos antigos: `mosaico`, lido por `planejar.pecas_da_cena`).
- Efeitos sonoros ✅ (2026-10-14): `tools/audio/sfx.py` (catálogo em acervo.db `sons`/`uso_som`, arquivos em
  dados/comum/sfx/; 117 sons do Freesound só CC0/CC BY + Stable Audio Open para completar; busca CLAP texto→áudio com
  reforço da categoria, `tools/audio/clap.py`). Diretor pede `som` por cena; `montar.efeitos_sonoros` impõe as
  regras (≤1 a cada 30 s, ≥18 s entre eles, ~15 dB abaixo da voz); créditos CC BY entram na descrição.
- Roteirista no painel ✅ (2026-10-14): `app/servidor/roteirista.py` + tarefa "roteiro" no motor. Gera (do zero ou a
  partir de roteiro BASE gringo — inspiração, nunca tradução) e ajusta por pedido (Claude devolve só os parágrafos
  alterados → barato, preserva edições à mão). Edição à mão, versões (roteiro_vN.txt) com "voltar", conversa em
  direcao/conversa_roteiro.json. Jeito do canal: `docs/estilo_roteiro.md` (formato que o diretor exige + voz do Felipe).
- Direção por blocos com reaproveitamento ✅ (2026-10-15): `planejar.planejar()` divide o roteiro em blocos
  (introdução + seções; fronteiras reaproveitadas do plano anterior ou pedidas ao Sonnet) e planeja cada bloco à parte
  com cache por conteúdo em `direcao/plano_secoes/<hash>.json`. Bloco igual = 0 cota; mudança pequena (mesmas frases,
  palavras trocadas) = reaproveita e marca "conferir"; bloco reescrito/novo = só ele vai ao Opus. Cada cena tem `id`
  estável (`<bloco>-<hex>`): candidatos, escolhas e ajustes do storyboard são por id (`candidatos.preparar` só manda
  ao Claude as cenas sem escolha). Roteiro novo (`motor.invalidar_depois_do_roteiro`) arquiva só a montagem
  (direcao.json, tempos) e volta as etapas; plano/escolhas/ajustes ficam para o reaproveitamento.
- Render por blocos ✅ (2026-10-15): `montar.renderizar()` agrupa as cenas por bloco (campo `bloco` = seção do
  plano), usa o quadro inicial `q` calculado na montagem e renderiza cada bloco sem áudio via
  `app/video/render_blocos.mjs` (bundle + navegador uma vez só), com cache em `trabalho/blocos/<impressão>.mp4`
  (impressão = cenas + intervalo + tempos + código do Remotion + capa); só blocos alterados são refeitos; áudio
  inteiro à parte (.wav) e junção com FFmpeg concat sem recomprimir. Cenas HERDAM os efeitos da versão anterior
  (mesmo id e tipo; `montar._herdar`), semente e folga de corte são por id → mexer numa cena não muda as outras.
- Escolha de imagens em lotes ✅ (`escolher.py`: 6 folhas por chamada + reenvio do que o Claude "não viu");
  busca com prioridade para personagem/lugar (`candidatos.Acervo`: vocabulário das etiquetas, tolera grafia,
  ≥2 candidatos do personagem; ignora arquivos que sumiram da pasta); `busca.arquivo` = arquivo pedido pelo nome
  (escolha fixa, sem Claude). Revisão ("Pedir ao diretor") vê o trecho inteiro e pode DIVIDIR a cena em várias.
- Barra de progresso ✅: `motor.definir_progresso` (estado em `/api/motor` → `progresso`); render lê `PROG <bloco>
  <quadros>` do render_blocos.mjs e estima o tempo restante; direção mostra o passo. Painel: `componentes/Progresso.tsx`
  (página do vídeo, storyboard e cards do quadro). Avisos da versão anterior somem ao pedir versão nova
  (`motor.limpar_avisos`). Busca do storyboard: nome exato → começa com → contém → etiquetas → CLIP, sem acento,
  inclui categoria "canal". Revisão usa o trecho do RASCUNHO (cenas sem imagem dentro dele saem do plano).
- **Blocos desacoplados** ✅ (2026-10-16): mexer num capítulo só refaz o bloco dele. Em `montar.montar()` a regra
  de não repetir imagem e o sorteio de efeitos (Variador) recomeçam a cada bloco; cena automática MANTÉM a imagem da
  versão anterior (`trecho["fontes"]`, sem condição); escolha manual ("fixa") vale sempre ("poder de Deus"). A
  impressão do bloco não inclui o `k` (posição no plano). Áudio (voz + efeitos) mixado no FFmpeg (`_mixar_audio`), sem
  Remotion. Cena sem imagem entra como texto (`sem_imagem`) no tempo dela para o Felipe escolher no storyboard.
  Storyboard: número fixo por cena (`direcao/numeros.json`; dividida → 40.1, 40.2), contadores "ajustadas no total" e
  "pendentes" (`direcao/ajustes_pendentes.json`, limpo quando o motor lê os ajustes), escolher o momento do clipe no
  vídeo original (`clipe_inicio` → `Midias.tomada(id, inicio)`; rota `/api/acervo/video/{id}`), CLIP pré-carregado.
  "Juntar com a próxima": a cena vira tela dividida (`ajustes[cid].juntar`; item 2 entra onde a próxima começava, peça com `frase`/`palavra`) e a próxima sai (`juntada_em`; "Desfazer" volta as duas).
  Meio a meio: lado da imagem (`lado_felipe`) e outra metade texto OU imagem (`metade2` → nec `<cid>m2`; sai como dividida de 2).
  Pendentes = ajustes diferentes da foto `direcao/ajustes_no_rascunho.json` (tirada quando o motor lê os ajustes).
  Itens de lista/dividida/mosaico: imagem por item no storyboard (`ajustes[cid].pecas[j].candidato` → escolha fixa de `<cid>p<j>`).
  Entrada por item (lista/dividida/mosaico): `ajustes[cid].pecas[j].entrada` (nenhuma/fade/deslizar/revelar/pop; sem escolha = a do
  diretor) → peça `entrada` → `app/video/src/componentes/EntradaManual.ts` (ligado por linhas `impressao:ignorar`).
- Atualizar acervo ✅ (2026-10-17): `tools/acervo/atualizar.py` (inventário → CLIP → tomadas → etiquetas pelo nome do
  arquivo; incremental, sem cota). Tarefa global "acervo" (vid 0) na fila do motor: botão "Atualizar acervo" no topo
  do painel e automática a cada card NOVO (o acervo muda pouco). Resultado em `/api/acervo/situacao`.
- Pacote pós-1º vídeo ✅ (2026-10-19): **estilo visual por vídeo** (`direcao/estilo_visual.json`; o 1º vídeo ficou
  na versão 1, vídeos novos = 2): transições de entrada empurrar/sobrepor (`app/video/src/cenas/Estilo2.tsx`,
  ~1 em 7 cenas, nunca na 1ª do bloco; storyboard "entrada"), cartão sem recorte, texto entra junto com a imagem
  (retrospectiva: docs/regras_de_direcao.md §5). Linhas que ligam o Estilo2 são `impressao:ignorar` → cache dos
  vídeos antigos intacto. Roteiro mudou: só o trecho alterado volta ao Claude (`planejar.remendar_bloco`) e ajustes
  presos a palavras seguem a palavra (`storyboard.remapear_ajustes`); capítulo intocado não reenvia recusadas.
  Storyboard: "a cena começa em" (mover corte), juntar até 4 cenas, movimento "nenhum", lista "sem imagem".
  Cópia de segurança automática (`motor.copia_de_seguranca`, direcao/seguranca/, últimas 15) antes de roteiro
  novo/direção/pedido ao diretor; cache guarda os blocos da versão anterior também. Card "Vídeo já publicado".
- Conferência do roteiro ✅ (2026-10-19, `app/servidor/conferencia.py`, tarefa "conferencia" a cada roteiro novo):
  semelhança com o roteiro base (`direcao/roteiro_base.txt`; embeddings multilíngues locais, sentence-transformers)
  + fatos de lore (Sonnet extrai afirmações → wiki do LoL/Universe buscados localmente, cache em dados/runeterra/pesquisa_cache
  → Sonnet dá confere/diverge/sem fonte; cache por parágrafo). Painel: bloco "Conferência do roteiro" no Roteiro.
  Fontes (2026-10-30): wiki.leagueoflegends.com namespace Universe (3006; o fandom parou em 2023) + biografia E conto
  oficial do Universe (meeps `story-preview`); 2 trechos da wiki + 2 da Riot por afirmação; veredito traz `fontes` (quantas
  sustentam) e `fontes_divergem` (Riot oficial prevalece). Afirmações atômicas (1 fato cada), página `Universe:<personagem>`
  sempre incluída (`_pagina_do_personagem`), 3 trechos wiki + 2 Riot, veredito `parcial` ("confere em parte", diz o pedaço).
  Cache por parágrafo inclui `conferencia.REGRAS` (subir a versão ao mudar regra = tudo reconferido no próximo ↻);
  "conferir tudo" no painel (`/roteiro/conferir?tudo=true`) apaga o cache. Botão "Corrigir" em cada item diverge/parcial (individual de propósito: o Felipe lê cada um) → `/roteiro/ajustar` só naquele parágrafo, versão nova. Reddit: API bloqueia sem chave (403) — exigiria app Reddit do Felipe.
- Mídias da internet ✅ (2026-10-19): acervo baixado fica em `dados/runeterra/acervo_internet/` (fora da pasta do Felipe;
  caminho ABSOLUTO no acervo.db, `inventariar.PASTAS_EXTRA`). `tools/acervo/importar_riot.py` (splash de todas as
  skins via CommunityDragon + splash base 1920 e artes dos contos do Universe; categoria splash/skin/arte, descarta o
  que o Felipe já tem; tarefa "importar_riot"). Storyboard: "buscar na internet" (`app/servidor/internet.py`:
  DuckDuckGo `ddgs` + Wikimedia Commons; baixa e cataloga na hora) e "colar link" de vídeo (yt-dlp → tomadas, tarefa
  "clipes"; início/fim opcionais = baixa só o trecho, `--download-sections`). Gravação por capítulos: vários arquivos em entrada/ são juntados na ordem dos nomes.
- **Perfil de canal ✅ (2026-10-19)**: os canais NÃO se conhecem — cada um roda o MESMO código num servidor próprio
  com `GRS_CANAL=<chave>` (`canais/<chave>/canal.toml`: nome, porta, assunto, pastas de acervo/banco/projetos/docs,
  fontes de fatos, aviso legal). `tools/canal.py` (CANAL, caminho) alimenta `comum.py`, `banco.py`, `motor.py`,
  prompts (planejar/escolher/revisar/roteirista/publicacao/conferencia). Sem GRS_CANAL = runeterra, caminhos de
  sempre (`Iniciar Runeterra.bat`, porta 8765). Pokémon: `Iniciar Pokemon.bat` (porta 8766), dados em dados/pokemon/,
  projetos em dados/pokemon/projetos/, docs em canais/pokemon/docs/, `tools/pokemon/` (pokedex.py, preparar_canal.py).
  Trava `dados/comum/motor.lock` = uma tarefa por vez na máquina entre os canais. Seletor de canal no título do quadro.
- **Aprendizado entre vídeos ✅ (2026-10-20)**: `tools/direcao/aprendizado.py`. Ao publicar (antes de arquivar),
  `coletar()` guarda os pares de legenda "diretor → Felipe" (vão no prompt do diretor: `planejar.sistema_do_diretor`)
  e a retrospectiva dos ajustes; tarefa global "retrospectiva" (Sonnet) propõe regras novas, que só entram em
  regras_de_direcao.md do canal se o Felipe aprovar (botão "Aprendizado" no quadro). Arquivos em <dados do canal>/aprendizado/.
  NÃO aprender "gosto de imagem" por pontuação (o Felipe recusou: as mesmas imagens passariam na frente).
- **Pesquisa antes do roteiro ✅ (2026-10-29)**: `app/servidor/pesquisa.py` roda dentro da tarefa "roteiro" (gerar): Sonnet lista
  assuntos → wiki/Universe locais (cache) → dossiê de fatos com fonte e selo canon (atual/antigo/jogo) + crivo do roteiro
  base (confirmada/corrigida/desatualizada/sem_fonte) em `direcao/dossie.json`. O roteirista (gerar e ajustar) só afirma
  fatos do dossiê; o base vira só estrutura. Painel: bloco "Pesquisa" na Conferência. Zoom da capa nos hubs +20% (`Capa.tsx`, 2,6).
  Roteiro base colado (transcrição do YT) passa por `conferencia.limpar_base` (tira tempos/[Música], junta linhas);
  `frases()` corta texto sem pontuação em trechos de ~20 palavras.
  Encerramento fixo: ao aprovar o vídeo, `publicacao.com_encerramento` junta o último final + `<dados do canal>/encerramento/encerramento.mp4`
  (Runeterra: dados/runeterra/encerramento/) → `saida/final_vN_publicar.mp4` (só o encerramento é recodificado; final intacto).
  Depois da gravação aprovada, "novo rascunho" no storyboard gera um VÍDEO FINAL novo (voz real), não rascunho com voz guia.
- GIF animado ✅: `app/video/src/componentes/Figura.tsx` (`@remotion/gif`); montagem mantém .gif animado.
- **Fluxo completo de ponta a ponta ✅ (2026-10-13).** Próximos: falas PT-BR de um site de fã, Pesquisa (referência → fatos → detector de semelhança), Mídias da internet,
  exportação para Premiere/DaVinci (XML) e After Effects (script).
