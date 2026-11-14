# Painel do documentário horizontal (fase 4)

Card novo no painel do F1: formato **`horizontal_doc`** ("documentário" no botão do quadro), ligado por
`[horizontal_doc]` no `F1/canal.toml`. Serve para qualquer vídeo de F1: o painel não sabe nada de GP, piloto ou pista,
só mostra e grava o protocolo de arquivos do `diretor/` (ver `../diretor/README.md`).

## Etapas do card
Roteiro → Voz guia → **História ★** → **SPEC ★** → Ativos → Verificação → **Rascunho ★** → Gravação → Ressincronização →
**Render final** (7c) → Publicação (fase 7a; card criado antes, com a etapa "Narração" `voz_ia`, continua no fluxo antigo: `etapas.ETAPAS_HORIZONTAL_DOC_V1`).
Roteiro, Voz guia, Gravação e Ressincronização são as do Runeterra (ver "Fase 7a" abaixo). As cinco do meio são o `estado.json` de `F1/dados/projetos/<slug>/horizontal/`, espelhado nas
etapas e pendências do banco a cada leitura (o estado vive no arquivo; o banco só reflete).

| estado.json | card |
|---|---|
| `pendente` | Aguardando |
| `prompt_pronto` | Em andamento — "aguardando o orquestrador" |
| `gerado` | ★: Precisa de você ("aprove ★"); sem ★: Concluído |
| `aprovado` | Concluído |
| `mudanca_pedida`, `desatualizado`, `falhou` | Precisa de você |
| `andamento` (montador rodando, só Rascunho) | Em andamento — "montando N cenas…" |
| Rascunho sem `montador/montar.py` | Em breve — "sem montador ainda" (não acontece mais desde a fase 5) |

## Quem faz o quê
- **Painel** (`app/servidor/horizontal_doc.py`, gancho mínimo): chama a ponte `diretor/painel.py` num processo à
  parte (os nomes `comum`/`etapas` do diretor colidem com `tools/`), pedido e resposta em JSON. Toda gravação do
  `estado.json` passa por `diretor/etapas.py`.
- **Botões dos 4 passos**: História e SPEC **não chamam o Claude** — gravam `prompts/<etapa>.prompt.txt` (com os pedidos
  abertos no fim), marcam `prompt_pronto` e abrem a pendência "Orquestrador: rodar o prompt…" com o caminho do prompt
  e o comando que aplica a resposta. Se o mesmo prompt já foi respondido (`cache/`), aplica sem gastar cota.
  Ativos (`ativos.py` sem `--produzir`, offline) e Verificação (`verificar.py`) rodam no próprio painel.
- **Orquestrador** (chat): roda o prompt no modelo, grava a resposta JSON e executa
  `python F1/horizontal/diretor/painel.py aplicar <pasta> historia|spec <resposta.json> [--cena <id>]`
  (aplica, prende às palavras, valida, registra o hash e marca os pedidos atendidos).
- **Felipe**: aprova ★ (o `etapas.aprovar` recusa arquivo mexido depois de gerado e etapa anterior não aprovada),
  pede mudança geral da etapa ou **por cena** na SPEC, retira pedido.

## Telas (painel "Documentário" na página do vídeo)
Abas das 5 etapas com o estado; botão do passo; "Aprovar ★"; caixa "Para o orquestrador" com prompt e comando.
- História: tese, capítulos (função, ritmo, trecho-âncora), afirmações e avisos.
- SPEC: cada cena com tempo, motor, transição, objetivo, câmera, kits, texto na tela e SFX; abaixo da cena, os
  ativos dela que não estão prontos e os erros/pendências/avisos da verificação daquela cena; "pedir mudança" por cena.
  Pedido só de cenas gera um prompt curto por cena (`spec.prompt_pedido`); as outras ficam como estão (ids estáveis).
- Ativos: resumo (pronto/falta/não validado/reprovado/não encontrado), os que faltam com o comando para produzir
  (rede: OpenF1/YouTube, fica para o orquestrador), prontos recolhidos.
- Verificação: status e as listas de erros, pendências e avisos com código e cena.
- Rascunho (fase 5): "Montar rascunho" → a ponte roda `montador/montar.planejar` (sem render). Faltando ativo/receita
  → 409 com a lista por cena. Senão dispara `montador/montar.py --registrar` em processo à parte (`andamento`,
  `rascunho/montagem.log`); ao terminar, `gerado` (★) ou `falhou` com o motivo. O vídeo aparece na aba
  (`rascunho_video` → `/api/arquivo`). Ver `../montador/README.md`.

## Storyboard do Rascunho (fase 7b)
Na aba Rascunho, abaixo do vídeo: uma linha por cena da SPEC, como o storyboard do Runeterra (por frases e momentos-
chave, ancorado em palavras). Cada cena mostra: número, id, tempo, capítulo, **motor**, **kits**, **estado**
(`sem prévia` · `renderizando…` · `prévia pronta · aprove ★` · `aprovada ★` · `desatualizada` · `prévia falhou` ·
`sem receita no montador`), os **quadros de prévia** nos momentos-chave (início, âncoras dos kits, SFX, fim), o **texto
falado em frases** com o tempo, o objetivo e o texto na tela.
- **Prévia**: botão "prévia" da cena ou "Gerar prévias que faltam" → `montador/storyboard.py` em processo à parte
  (o trecho do montador da cena, cache por hash; o que já está no cache sai na hora). Ver `../montador/README.md`.
- **Aprovar ★ da cena**: guarda o hash que o Felipe viu; a cena mudou → "desatualizada". (O ★ do Rascunho inteiro
  continua sendo o da etapa.)
- **Ações diretas** (na hora, SEM modelo; `diretor/ajustes.py` → `etapas.ajustar` grava o `spec.json`, a SPEC continua
  aprovada, Ativos e Verificação rodam de novo, o Rascunho fica desatualizado): câmera (parado, aproximar, afastar,
  pan ←/→, subir, descer + intensidade), entrada (corte/fade/wipe/zoom + quadros), "começa em" / "termina antes de"
  (move o corte com a vizinha), SFX (categoria, palavra, remover, + SFX) e escolhas fechadas do kit (câmera do GPS,
  minimapa do gráfico). Só as cenas cujo trecho mudou (hash da receita) renderizam de novo; trocar SFX não renderiza
  nada (só o áudio muda). Histórico em `horizontal/ajustes_diretos.json` (para o aprendizado).
- **Pedido por cena** (texto OU voz): microfone dentro de cada cena ("Corrigir a cena N por voz", o mesmo ditado local
  das Observações, `componentes/Ditado.tsx` + `/api/videos/{id}/observacoes/transcrever`); o texto transcrito aparece
  no campo para corrigir e só então "Enviar". Vira pedido da cena na SPEC (marcado "ditado por voz") + o prompt SÓ
  daquela cena (`spec.prompt_pedido`) e a pendência para o orquestrador, numa chamada (`painel.pedido_cena`).

## API (`app/servidor/horizontal_doc.py`)
| Rota | Faz |
|---|---|
| `GET /api/videos/{id}/doc` | sincroniza roteiro/narração do card para a pasta horizontal e devolve estado, história, SPEC, ativos, verificação, tarefas do orquestrador |
| `POST /api/videos/{id}/doc/passo/{historia\|spec\|ativos\|verificacao\|rascunho}` | dispara o passo (409 com o motivo quando não vale: roteiro não aprovado, etapa anterior sem ★, "sem montador ainda") |
| `POST /api/videos/{id}/doc/aprovar/{historia\|spec\|rascunho}` | ★ pelo `etapas.aprovar` |
| `POST /api/videos/{id}/doc/pedido` `{etapa, texto, cena?}` | `etapas.pedir` (cena precisa existir na SPEC) |
| `DELETE /api/videos/{id}/doc/pedido/{pid}` | retira (status `recusado`); sem outros pedidos abertos a etapa volta a `gerado` |
| `GET /api/videos/{id}/doc/storyboard` | cenas com frases, momentos-chave, quadros (caminhos para `/api/arquivo`), motor, kits, estado |
| `POST /api/videos/{id}/doc/cena/{cid}/ajuste` `{acao, previa?}` | ação direta na SPEC (409 com o motivo se não vale); dispara a prévia das cenas afetadas |
| `POST /api/videos/{id}/doc/previa` `{cenas?}` | prévia das cenas (todas se vazio), processo à parte |
| `POST /api/videos/{id}/doc/cena/{cid}/aprovar` | ★ da cena (409 sem prévia da versão atual) |
| `POST /api/videos/{id}/doc/cena/{cid}/pedido` `{texto, origem: texto\|voz}` | pedido da cena + prompt só dela para o orquestrador |
| `POST /api/videos/{id}/doc/final` | (7c) confere tudo e põe o render final na fila (409 com o motivo; 409 se já está na fila) |

Entradas: `direcao/roteiro.txt` do card vira `horizontal/roteiro.txt`; `direcao/tempos_voz.json` (narração medida) vira
`horizontal/palavras.json` **só** se tiver o mesmo número de palavras do roteiro (senão aviso e tempos estimados).

## Fase 7a: Roteiro, Voz guia, Gravação e Ressincronização (como no Runeterra)
O MESMO código do Runeterra, com dois ganchos: o card documental não chama `claude -p` e os números de F1 vão ao OpenF1.
- **Modo orquestrador** (`tools/direcao/claude_cli.pelo_orquestrador`): o motor roda `roteiro` (roteirista + pesquisa),
  `conferencia` e `publicacao` deste card dentro dele (`motor.executar`, `TAREFAS_DO_ORQUESTRADOR`). Cada chamada ao
  modelo vira `<projeto>/orquestrador/<etiqueta>_<hash>.prompt.txt` (sistema + prompt + onde responder) e a tarefa pausa
  (`PrecisaOrquestrador`, `orquestrador/aguardando.json`, pendência `orq_<tarefa>` com o caminho). O chat grava
  `<mesmo nome>.resposta.txt`; o painel retoma sozinho na próxima leitura de `/doc` (ou botão "Continuar" =
  `POST /api/videos/{id}/doc/orquestrador/continuar`). A tarefa recomeça do zero e as chamadas já respondidas saem do
  arquivo (sem cota), até o próximo prompt. Trocar o roteiro com o roteirista pausado cancela a pausa.
- **Pesquisa antes do roteiro** (`pesquisa.py`, só F1): além da Wikipedia, os assuntos trazem as `sessoes` citadas e
  `openf1.fatos_da_sessao` põe no dossiê resultado (top 10 + pilotos pedidos), melhor volta e pit stops, com a fonte
  `OpenF1 · <circuito> <ano> <sessão> (session_key …)`. O roteirista só escreve com o dossiê.
- **Conferência** (`conferencia.py`, só F1: `REGRAS` ganha `-of1`, o Runeterra não reconfere): cada afirmação com
  número traz `openf1` {tipo, ano, local, sessao, piloto, piloto2, volta, valor, casas}; `app/servidor/openf1.py`
  recalcula dos dados brutos (cliente e cache do `kit/gps`): tempo de volta, diferença, posição final/largada, voltas,
  pit stops, tempo parado, velocidade máxima, com tolerância de meia unidade da casa dita. O OpenF1 decide o veredito
  dos números (vale acima da Wikipedia); antes de 2023, sessão ambígua ou sem dados = `sem_dados` e fica a Wikipedia.
  Painel: selo "OpenF1 confere/diverge/sem dados" e a fonte com o `session_key`.
- **Voz guia**: roteiro aprovado → `voz_guia` (Fish Audio s2.1, reserva Piper, `tools/audio/voz_guia.py`); só no
  documentário os tempos por palavra (`tempos.tempos_da_narracao`, Whisper) vão para `direcao/tempos_guia.json` e a
  ponte copia para `horizontal/palavras.json`. Nunca vai para vídeo publicado.
- **Gravação**: igual ao Runeterra (upload com progresso ou pasta `entrada/` + "Já coloquei na pasta"; limpeza
  `limpar_gravacao.py`; ponto de controle "Confira a gravação limpa"; linha do tempo de cortes). O painel aparece depois da voz guia.
- **Ressincronização**: aprovar a gravação → `motor.tarefa_ressinc_doc` (no lugar do render do Runeterra, que é a 7c):
  `alinhar.py` (tempos por palavra DO ROTEIRO na sua voz) → `direcao/tempos_gravacao.json` → a ponte
  (`painel.ressincronizar`) roda `spec.retemporizar`: mesmas cenas, ids e índices; só mudam os tempos das cenas
  afetadas (`horizontal/ressinc.json`). `etapas.retemporizar` grava o hash novo SEM perder o ★ da SPEC (o Felipe aprovou
  cenas presas a palavras) e deixa ativos/verificação/rascunho `desatualizado`. Qualquer troca de narração (estimados →
  voz guia → gravação) passa pelo mesmo caminho. Tempos que valem: gravação > voz guia > `tempos_voz.json` (card antigo).
  `alinhar.py` conta todo token ("—"); a ponte descarta os sem letra/número para bater com o diretor.

## Fase 7c: Render final e Publicação (como no Runeterra)
Etapas do card: … Gravação → Ressincronização → **Render final** → Publicação (card da 7a/7b ganha a linha "render" na
1ª leitura do `/doc`).
- **Quando sai**: só com a SUA narração (`trabalho/gravacao/limpa.wav`, tempos da gravação, SPEC ressincronizada), a
  SPEC ★, **todas as cenas ★ no storyboard na versão atual** e a verificação da SPEC atual sem erro (`painel.final_checar`
  roda Ativos/Verificação desatualizados de novo, offline). A ressincronização mantém o ★ da cena que só foi
  retemporizada (o Felipe aprovou o conteúdo preso às palavras; `ressinc.json` → `aprovacoes_mantidas`); cena mexida
  depois do ★ precisa de ★ de novo.
- **Disparo**: gravação aprovada → ressincronização → render na mesma tarefa, como no Runeterra; faltando algo, a etapa
  Render diz o quê (pendência "Vídeo final: falta pouco") e o botão **“Renderizar o vídeo final”** (painel Documentário)
  dispara depois (`POST /doc/final`, 409 com o motivo).
- **Render** (`motor.tarefa_render_doc`, fila do motor e trava da máquina): `montador/montar.py --final --registrar
  --progresso` num processo à parte: 1920×1080, 60 q/s, NVENC (x264 se a máquina não tiver, ou se o NVENC cair no meio:
  o vídeo inteiro vira x264), UMA mixagem com a narração gravada, loudness medida no MP4. Linhas `PROG` → barra do painel
  (cena a cena, bloco a bloco) e o detalhe do card ("bloco 3 de 7"). Sai `saida/final_vN.mp4` (cada versão um arquivo),
  a etapa mostra resolução, LUFS, pico, codificador e blocos refeitos/do cache; pendência **"Assista o vídeo final"**
  (`ver_final`) e card em Revisão. Falha = pendência `erro_render_doc` com o motivo (`final/falhou.json`).
- **Correção depois do final**: storyboard (ação direta ou pedido por cena) → a SPEC muda → o final fica "desatualizado"
  (sai o "Assista", entra "Vídeo final desatualizado"); ★ da cena mexida e “Renderizar de novo”: o montador refaz só os
  trechos e os blocos que mudaram (cache por hash em `trechos/` e `blocos/final_*`).
- **“Vídeo aprovado”** (resolver `ver_final`) → Publicação, pelo orquestrador (`publicacao` já é tarefa do orquestrador
  desde a 7a): `publicacao.gerar_textos_doc` monta UM prompt (`orquestrador/publicacao-doc_<hash>.prompt.txt`) com
  título provisório, duração, tese, capítulos, a lista de cenas (id, início, o que mostra), o roteiro e, se houver
  `YOUTUBE_API_KEY` no `.env`, os vídeos que já existem sobre o tema (YouTube Data API v3: busca + views, cache em
  `direcao/concorrentes.json`; sem chave ou com erro de cota/rede, pula com aviso). Resposta: 6 títulos, gancho, 10–15
  tags, comentário fixado e a miniatura (texto curto, enquadramento, cena). A descrição junta gancho + capítulos +
  créditos (OpenF1, imagens validadas dos ativos, SFX CC BY do final) + aviso legal do F1.
  **Capítulos** = 1ª cena de cada capítulo da História na SPEC, nos tempos da gravação; regras do YouTube (0:00, ≥ 3,
  ≥ 10 s; capítulo curto junta com o anterior). **Miniatura**: quadro 1280×720 do vídeo final no meio da cena escolhida
  (`saida/miniatura_base.jpg`); o texto sugerido vai por cima no editor do Felipe (nada é desenhado). VidIQ: não (decisão
  do Felipe depois). “Marcar como publicado” é o do Runeterra.

## Correções do 1º uso real (2026-11-14, card 20 "Nove milésimos")
- **Card novo com "Narração" e sem voz guia**: o código da 7a estava certo (`banco.criar_video` → `etapas_do_formato`
  sem `chaves` = `ETAPAS_HORIZONTAL_DOC`; `aprovar_roteiro` só pede a gravação quando o card tem `voz_ia`). A causa: a
  pasta principal estava no commit do PR #108 (antes da 7a) com #109–#111 já mesclados no GitHub, e o painel 8766 subiu
  desse código. Card criado assim fica no fluxo antigo (`ETAPAS_HORIZONTAL_DOC_V1`, de propósito: não muda card antigo).
  Proteção nova: `app/servidor/versao.py` guarda o commit carregado; `/api/canal` traz `codigo` e o quadro mostra o aviso
  quando a pasta (no `main`) está atrás do `origin/main` conhecido localmente (último fetch/pull, sem rede) ou quando o
  código mudou depois que o painel subiu (reinicie). Ao subir com aviso, também vai para a atividade (alerta).
- **Markdown no roteiro** (`**negrito**` ia para roteiro.txt, palavras, âncoras e prompts): `tools/direcao/notas.separar`
  tira `**x**`, `__x__`, `*x*`, `_x_`, `# título`, `> citação`, crase e asterisco solto na borda de palavra, ANTES de
  contar as palavras das notas. Decisão: vale para **todos os formatos** (Runeterra, vertical, animado, documentário): a
  voz guia leria os asteriscos em qualquer canal, e roteiro sem Markdown sai idêntico (testado; nenhum roteiro do
  Runeterra tinha essas marcas). `roteiro_fonte.txt` guarda como veio. `_` dentro de palavra e `2*3` ficam.
  `comum.frases`: ponto seguido de fecho (`.**`, `.”`) termina a frase, e a última frase sempre tem tempo final.
- **Conferência F1 (OpenF1)**: o card 20 rodou com o código antigo (conferência sem OpenF1: 16/16 "sem fonte"). Mesmo
  no código da 7a a sessão não resolvia: o modelo manda `local: "México"`/`"Hermanos Rodríguez"`, `sessao:
  "Classificação"`, e os trechos sem a sessão ("No primeiro setor…") vinham sem ano/local. Agora:
  `openf1.sessao_do_texto` lê GP/país/circuito (PT/EN), ano e sessão do roteiro inteiro; o prompt das afirmações diz a
  sessão lida ("Sessão do vídeo (lida do roteiro): ano 2026, local "Mexico City", sessão "Qualifying"") ou, se não deu
  para ler, pede o `session_key` ao orquestrador; a sessão lida preenche SÓ o que o pedido não traz; `LOCAIS` e
  `NOMES_SESSAO` traduzem nomes (país com mais de um GP — Itália, Espanha, EUA — fica ambíguo de propósito); tipo novo
  `setor` (tempo ou diferença entre dois no setor). A pesquisa usa o tema/orientações como contexto e pede o
  `session_key` também. `REGRAS` do F1 = `4-of2` (o que saiu sem fonte é conferido de novo uma vez; Runeterra fica `4`).
- **"Sem fonte" não é conferido**: card do Roteiro "conferido: 0 ⚠️ fato(s) · 3 não conferido(s)" ou, se nenhum tem
  fonte, "não conferido: N fato(s) sem fonte"; atividade "Roteiro conferido: X de N fato(s) com fonte…, N NÃO
  conferido(s)" (alerta se nenhum tem fonte); painel: grupo "NÃO conferidas" e aviso "Nenhum fato foi conferido…". Vale
  para todos os canais (só muda o texto).
- **Verificação** (`verificar.py`): número de cronômetro na tela ("1:16.514", "1 min 16 s 514") conta como os segundos
  (76.514) da afirmação; na fala, "1 minuto, 16 segundos e 514 milésimos" e "9 milésimos" (0.009) também contam;
  "PARTE 02"/"Capítulo 3" é número de capítulo livre (o resto do texto continua conferido).
- Teste: `testes/painel/testar_uso_real.py` (34 checagens, ~10 s, sem rede: OpenF1 fictício com os números reais da
  sessão 11400); casos no `testes/diretor/testar.py` (88). Visto no navegador (porta 8799, `servidor.py`): conferência do
  card "Fluxo 7a" com o OpenF1 REAL (prompt com a sessão lida, setores 2 e 3 conferidos sem ano/local no pedido, sessão
  9908), "NÃO conferidas" e o aviso de nenhum conferido. O card 20 real não foi mexido: o roteiro dele continua com `**`
  até ser reenviado, e ele segue no fluxo antigo (`voz_ia`).

## Observações gerais do Felipe
O painel "Observações gerais" do card (voz ou texto, `docs/observacoes.md` na raiz) grava `<projeto>/observacoes.json`;
a ponte (`sincronizar_observacoes`, em `resumo`/`passo`) copia para `horizontal/observacoes.txt`, e `comum.observacoes`
põe o texto nos prompts da História, da SPEC e do pedido por cena (`{{observacoes}}`).

## Testes
- Fase 7c: `testar_api.py` agora 163 checagens (132 + 31 da 7c): Render final no card, ressincronização sem cenas ★ só
  avisa, botão recusado (cenas sem ★; sem gravação), card antigo ganha a linha, render pelo motor com um MONTADOR
  FICTÍCIO no mesmo protocolo (PROG + final.json + MP4 1080p60 real de 2 s): barra bloco a bloco, final_v1/v2 (o v1 fica),
  desatualizado depois de ação direta e em dia depois de renderizar de novo, falha com motivo, “Vídeo aprovado” →
  Publicação pelo orquestrador (prompt, resposta, 6 títulos, tags, descrição com créditos e aviso legal, capítulos nas
  regras, miniatura 1280×720 do final na cena escolhida, concorrentes pulados sem chave), regra dos capítulos, YouTube
  Data API fictícia (ordem por views, cache, no prompt; cota estourada não quebra). O render final DE VERDADE (1080p60,
  NVENC e x264, mixagem com a "gravação") está em `testes/montador/testar.py` (seção 7).
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\testar_api.py [-v] [--manter]` — 107 checagens (61 da fase 4 +
  46 da 7a), ~15 s, motor sem thread (`motor.executar` tarefa a tarefa). 7a: roteirista+pesquisa e conferência pelo
  orquestrador (3 + 2 prompts respondidos no teste; `claude_cli.EXE` apontado para um caminho que não existe), números
  do OpenF1 fictícios (valores reais de Monza 2025 Q) com confere/diverge/sem dados/ambíguo/tolerância, voz guia e
  Whisper fictícios, gravação por upload com limpeza fictícia (voz 1,5 s mais lenta a partir da metade), alinhamento
  e retemporização reais: só as cenas depois do meio mudam, exatamente +1,5 s, SPEC continua ★, verificação sem TEMPO.
  Fase 4:

- `.venv\Scripts\python.exe F1\horizontal\testes\painel\testar_api.py [-v] [--manter]` — 86 checagens (61 + 25 do
  storyboard: listar, ação direta mantém a SPEC aprovada, movimento/ação desconhecida recusados, corte movido, ★ da cena
  recusada sem prévia/receita, pedido por voz vira prompt só da cena), ~15 s,
  TestClient em processo (sem porta), dados fictícios em `testes/painel/dados/api/` (apagados no fim). Caminho inteiro:
  criar → roteiro → narração → História (prompt, orquestrador, pedido/retirar, ★) → SPEC (arquivo mexido barrado,
  pedido por cena, refazer só a cena, ★) → Ativos → Verificação → Rascunho "sem montador ainda"; vertical e
  horizontal animado com as etapas de sempre; motor não põe a direção do animado na fila.
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\servidor.py --porta 8799` — painel numa porta temporária
  (recusa 8765/8766) com dados fictícios e um card documental semeado (História aguardando ★), para ver as telas.
  Precisa do `app/painel/dist` compilado. Fase 7a: 2º card "Fluxo 7a" com o roteiro enviado; `--voz-windows` troca o
  Fish pela voz pt-BR do Windows (fala de verdade para o Whisper) e deixa `gravacao_exemplo.wav` (mais lenta, com uma
  frase repetida) na pasta do projeto.

  Precisa do `app/painel/dist` compilado. `--storyboard` semeia mais um card já no Rascunho com o mini-spec e os
  trechos do `testes/montador/testar.py` (rode-o antes) para ver o storyboard com quadros de verdade.

## Limites (o que não foi verificado / não existe)
- Fase 7c, visto no navegador (porta 8797, `servidor.py --storyboard --final`, dados fictícios): card com Render final,
  1º clique recusado com o motivo na tela (verificação reprovada do seed antigo; corrigido o seed), depois render REAL
  1080p60 pelo motor (barra: "cena 3 de 3", mixagem, verificação), etapa "0:09 · v1" com −14,0 LUFS / −2,5 dBTP / NVENC,
  vídeo na Prévia, "Assista o vídeo final" → “Vídeo aprovado” → prompt da publicação (respondido pelo chat no papel do
  orquestrador) → painel Publicação com 6 títulos, descrição com créditos (OpenF1, SFX CC BY) e aviso legal do F1,
  miniatura sugerida + quadro 1280×720, concorrentes "pulada: sem YOUTUBE_API_KEY". Vertical/horizontal abrem iguais.
- NÃO exercido na 7c: YouTube Data API real (sem chave; só a fictícia no teste), narração gravada de verdade (sintética),
  vídeo longo (só 9 s: tempo de um final de 20 min não medido), capítulos num vídeo real (o mini-spec tem 9 s e 1
  capítulo: 0 capítulos, como manda a regra), “Marcar como publicado” no documentário, progresso "bloco k de N" com
  vários blocos na tela (o mini-spec cabe num bloco; os vários blocos estão no teste do montador e no fictício da API).
- Fase 7a (2026-11-13), visto no navegador (porta 8799, `--voz-windows`): conferência com Wikipedia e **OpenF1 reais**
  (LEC 1:19,007 e HAM 1:19,124 na volta 16 e a diferença 0,117 conferidos na sessão 9908), prompts respondidos pelo
  chat no papel de orquestrador, voz guia da voz do Windows medida pelo Whisper real (91 palavras, 8 estimadas),
  gravação de exemplo limpa pelo `limpar_gravacao` real (1 corte: a frase repetida), aprovação e ressincronização
  (8 de 8 cenas retemporizadas: a voz de exemplo é mais lenta do começo ao fim).
- **Fish Audio não foi exercido** (sem `FISH_API_KEY` no worktree; a chave do Felipe não foi usada): a voz guia real
  continua sendo o `voz_guia.py` de sempre, sem mudança. Roteirista e pesquisa (Wikipedia + OpenF1) só no teste
  automático com dados fictícios; no navegador só a conferência. Nenhum prompt rodou num modelo via `claude -p`.
- Números por extenso: a voz do Windows lê "1:19,007" diferente do texto e a limpeza marca "Leitura diferente do
  roteiro" (só informativo); com o Felipe gravando depende de como ele fala os números.
- Nenhum prompt rodou num modelo; as respostas dos testes são as fixas de `testes/diretor/exemplo/`.
- O card só se atualiza quando alguém lê `/doc` (página do vídeo aberta) ou quando o motor avisa (roteiro aprovado,
  narração pronta). Arquivo escrito pelo orquestrador com a página fechada aparece no quadro na próxima leitura.
- Narração real (upload, limpeza, medição) não foi exercida no teste: o `tempos_voz.json` é fictício.
- `ativos.py --produzir` não é disparado pelo painel (rede): o comando vai para o orquestrador.
- Rascunho: no `testar_api.py` só a recusa clara (a SPEC de exemplo tem kits sem receita); o caminho inteiro (passo →
  processo → `gerado` → ★) é testado em `testes/montador/testar.py` pela ponte, não pelo servidor HTTP.
- Storyboard (7b): visto no navegador na porta 8799 (`servidor.py --storyboard`): quadros reais das 3 cenas, ação direta
  (câmera da cena 3) → só ela renderizada de novo, prévia HyperFrames pelo botão, ★ da cena, pedido por texto enviado.
  NÃO exercido: gravar com microfone de verdade na cena (o ditado é o mesmo das Observações); ação direta que reprova a
  verificação deixa a etapa Verificação "falhou" (no teste, porque a história semeada é fictícia).
