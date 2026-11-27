# Estado: painel, fluxo dos cards, áudio e perfil de canal

Saído do CLAUDE.md (2026-11-08). Ao terminar um recurso desta área, registre AQUI, não no CLAUDE.md.

- Fase 0 (base: análise, guia de estilo, acervo catalogado) ✅
- Fase 1 (protótipo Remotion: capa, cartão, recorte, tela cheia, diálogo, citação, mosaico, clipe; efeitos variados) ✅
- Fase 2 (áudio) ✅ — `tools/audio/`: `voz_guia.py` (Fish s2.1-pro-free → reserva local Piper; Edge TTS caiu),
  `limpar_gravacao.py` (fala cortada por volume e transcrita trecho a trecho — o Whisper com o áudio inteiro "corrige"
  falsos começos; regravações, falas fora do roteiro, pausas, -14 LUFS; ruído de fundo do Felipe é ~-80 dB, não aplicar
  denoise), `alinhar.py` (tempos por palavra DO ROTEIRO → a direção usa índices do roteiro; trocar áudio = trocar tabela).
- Painel (Fase 5 adiantada) ✅ — `app/servidor/` (FastAPI+SQLite Runeterra/dados/studio.db; `motor.py` = fila/orquestrador;
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
  `Runeterra/dados/projetos/<slug>/capa.*` para o card. Publicado é definitivo: não sai da coluna, página vira resumo (capa, link, histórico).
- Barra de progresso ✅: `motor.definir_progresso` (estado em `/api/motor` → `progresso`); render lê `PROG <bloco>
  <quadros>` do render_blocos.mjs e estima o tempo restante; direção mostra o passo. Painel: `componentes/Progresso.tsx`
  (página do vídeo, storyboard e cards do quadro). Avisos da versão anterior somem ao pedir versão nova
  (`motor.limpar_avisos`). Busca do storyboard: nome exato → começa com → contém → etiquetas → CLIP, sem acento,
  inclui categoria "canal". Revisão usa o trecho do RASCUNHO (cenas sem imagem dentro dele saem do plano).
- Excluir card = DEFINITIVO, sem Lixeira (2026-10-31, `main.excluir`): pasta do projeto, fila, memória de uso e aprendizado do vídeo. Ficam: .txt de `roteiros/`, mídias do acervo, cache de voz e wiki (compartilhados), regras já aprovadas. Arquivo aberto = 409, nada é apagado.
- **Perfil de canal ✅ (2026-10-19)**: os canais NÃO se conhecem — cada um roda o MESMO código num servidor próprio
  com `GRS_CANAL=<chave>` (`<Canal>/canal.toml`: nome, porta, assunto, pastas de acervo/banco/projetos/docs,
  fontes de fatos, aviso legal). `tools/canal.py` (CANAL, caminho) alimenta `comum.py`, `banco.py`, `motor.py`,
  prompts (planejar/escolher/revisar/roteirista/publicacao/conferencia). Sem GRS_CANAL = runeterra, caminhos de
  sempre (`Runeterra/Iniciar Runeterra.bat`, porta 8765). Hoje só existe o Runeterra (o perfil Pokémon saiu em 2026-11-01; volta pelo histórico do Git).
  Trava `dados/comum/motor.lock` = uma tarefa por vez na máquina entre os canais. Seletor de canal no título do quadro.
- Card **documentário** (2026-11-13, formato `horizontal_doc`, só no canal com `[horizontal_doc]` no canal.toml = F1): etapas
  História ★/SPEC ★/Ativos/Verificação/Rascunho ★ espelhadas do `estado.json` do diretor (`app/servidor/horizontal_doc.py`,
  `PainelDocumental.tsx`); detalhes em `F1/horizontal/docs/painel.md`. Vertical e horizontal animado não mudam.
  Fase 7a: Voz guia, Gravação e Ressincronização do Runeterra no card (SPEC retemporizada por palavra); tarefas que precisam do modelo pausam num prompt para o orquestrador (`motor.executar`/`aguardar_orquestrador`, pendência `orq_*`).
  Fase 7c: etapa Render final (`motor.tarefa_render_doc` → `montar.py --final`, 1080p60, barra por bloco, `ver_final`) e
  Publicação do documentário (`publicacao.gerar_textos_doc`: capítulos da SPEC, miniatura de um quadro do final,
  concorrentes pela YouTube Data API só com `YOUTUBE_API_KEY`), prompt pelo orquestrador. Rótulo da descrição no
  `PainelPublicacao` virou "aviso legal" (vale para os dois canais).
- **Ditado por voz** (`app/servidor/ditado.py`, `componentes/Ditado.tsx`): faster-whisper local PT-BR em processo à parte (`tools/audio/ditado.py`); microfone no "corrigir por voz" das cenas e no pedido geral da animação. A feature "Observações gerais" foi **removida em 2026-11-20** (decisão do Felipe: no card ele só fala do vídeo; o aprendizado sai dos pedidos, ver `aprendizado.py`). Microfone só em localhost/https.
- **Pedidos pesados → orquestrador (2026-11-21)**: pedido de cena que exige capacidade nova ou julgamento visual não vai
  ao diretor (`claude -p`), vai ao ORQUESTRADOR (o chat no Claude Code, que lê o código, edita a biblioteca e olha os
  quadros). Núcleo e CLI em `tools/direcao/pedidos_pesados.py` (testes: `tools/direcao/testar_pedidos_pesados.py`, F1 e
  Runeterra com dados fictícios). Como entra: painel Animação (vertical/horizontal animado) → "Ao orquestrador" ao anotar,
  ou "enviar ao orquestrador" num pedido da fila (por cena ou geral); AUTOMÁTICO no vertical: `vertical.revisar` casa cada
  `nao_feitos` com `"capacidade": true` ao pedido do Felipe e o motor (`motor._promover_pesados`) o promove — sem aviso
  "pedido não feito"; se só sobraram pedidos pesados, não abre "O diretor não aplicou o pedido". Runeterra: no storyboard,
  aba "Pedir ao diretor" → "Enviar ao orquestrador" (ajuste ganha `comentario_pesado`; `storyboard.pendentes_para_o_diretor`
  o ignora). Cada pedido: `<projeto>/orquestrador/pedido_pesado_<id>.md` (texto, cena e fala, código da cena — Runeterra:
  campos da cena —, motivo do diretor, cópia do quadro de conferência, caminho do vertical.json) + fila
  `orquestrador/pedidos_pesados.json` + UMA pendência `orq_pedido_pesado` por card ("Aguardando o orquestrador: N pedido(s)
  pesado(s)"; botão "Já resolvido" fecha todos). Na fila do diretor (`pedidos_vertical.json`) o pedido fica com
  `pesado: <id>` e NÃO conta para "Refazer com os pedidos" nem trava "Só renderizar de novo" (`motor.pedidos_do_diretor`).
  Resolver (CLI ou `POST /api/pedidos-pesados/{id}/resolver {nota, renderizar}`): sai da fila, vai para
  `historico_pedidos_vertical.json` com `via: "orquestrador"` e a nota, pendência atualizada/fechada; `renderizar` só dispara
  quando não sobra pedido pesado aberto no card (vertical: "Só renderizar de novo"; Runeterra: novo rascunho). Descartar no
  painel fecha o pedido como "descartado" (sem histórico). `GET /api/pedidos-pesados` (todos os cards; `?todos=true` inclui
  os fechados); o quadro mostra "N pedidos pesados aguardando o orquestrador". Uso pelo orquestrador
  (`$env:GRS_CANAL='f1'`, ou runeterra):
  `.venv\Scripts\python.exe tools\direcao\pedidos_pesados.py listar` · `mostrar <id>` ·
  `resolver <id> --nota "o que foi feito" [--renderizar] [--porta 8766]`.
- Card no quadro mostra "Aguardando você: <pendência aberta mais recente>" (`/api/quadro` → `aguardando`), exceto enquanto o motor trabalha nele ou ele está na fila (aí mostra "Na fila (Nº): <tarefa>", `/api/motor` → `fila`).
- Celular pelo Wi-Fi (2026-11-01): servidores em `--host 0.0.0.0` (os .bat); acesso em `http://<IP do PC>:8765`. O painel não tem senha: quem estiver na mesma rede pode mexer nele.
- **Fluxo completo de ponta a ponta ✅ (2026-10-13).** Próximos: falas PT-BR de um site de fã, Pesquisa (referência → fatos → detector de semelhança), Mídias da internet,
  exportação para Premiere/DaVinci (XML) e After Effects (script).

## Orquestrador automático (2026-11-26)
Pedido pesado novo (F1 vertical/horizontal animado; o diretor devolveu "sem capacidade" ou o Felipe mandou) acorda sozinho um
`claude -p` (Opus 5.5, esforço médio) que segue `docs/orquestrador_auto.md`: acha a causa (biblioteca ou cena), confere o quadro
(`tools/direcao/quadro_da_cena.py`) e fecha com `pedidos_pesados.py resolver … --renderizar`. Código: `motor.tarefa_orquestrador` /
`acordar_orquestrador` (entra na MESMA fila do motor, depois da direção que devolveu o pedido); gancho `pedidos_pesados.AO_CRIAR`
ligado em `motor.iniciar`; ao ligar o servidor, pedidos que ficaram abertos também acordam. Desliga com `orquestrador_auto = false`
no canal.toml. Falhou/cota: o pedido continua aberto para o chat (log em `<projeto>/orquestrador/auto_<id>.log`). Não vale para
pedidos do storyboard do Runeterra. Testado só em processo isolado (pedido de teste resolvido em 22 s); falta ver pelo servidor.
