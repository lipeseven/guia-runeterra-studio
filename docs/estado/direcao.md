# Estado: diretor, storyboard, render, efeitos visuais e sonoros, aprendizado (Runeterra / horizontal antigo)

Saído do CLAUDE.md (2026-11-08). Ao terminar um recurso desta área, registre AQUI, não no CLAUDE.md.

- Fase 3 (diretor) ✅ — `tools/direcao/`: `claude_cli.py` (Claude Code headless enxuto: `--tools "" --setting-sources ""
  --strict-mcp-config`, ~800 tokens de base; imagens via stream-json; log em dados/comum/uso_claude.jsonl), `planejar.py`
  (1ª passada, texto), `candidatos.py` (busca local CLIP+etiquetas, folhas), `escolher.py` (2ª passada, imagens),
  `montar.py` (direção final + render da composição "Video" com --props), `revisar.py` (refaz só cenas com pedido).
- Novos recursos visuais ✅ (2026-10-14): `hub` (transição de seção: grade/esteira), `dividida`, `lista`, `meio`,
  `texto`, `citacao` (agora ligada ao diretor), nome sobre arte (telacheia rotulo/subrotulo), clarão, crédito de fan
  art na cena (midias.autor). **Fundo branco é a assinatura do canal**: o vídeo é sempre "claro" (o tema escuro de
`app/video/src/tema.ts` existe mas não é usado); escuro só em telas cheias e no `texto` com fundo escuro, raro. Peças de
  mosaico/dividida/lista ficam em `pecas` (planos antigos: `mosaico`, lido por `planejar.pecas_da_cena`).
- Efeitos sonoros ✅ (2026-10-14): `tools/audio/sfx.py` (catálogo em acervo.db `sons`/`uso_som`, arquivos em
  dados/comum/sfx/; 117 sons do Freesound só CC0/CC BY + Stable Audio Open para completar; busca CLAP texto→áudio com
  reforço da categoria, `tools/audio/clap.py`). Diretor pede `som` por cena; `montar.efeitos_sonoros` impõe as
  regras (≤1 a cada 30 s, ≥18 s entre eles, ~15 dB abaixo da voz); créditos CC BY entram na descrição.
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
  (impressão = cenas + intervalo + tempos + código do Remotion que desenha o bloco + capa); só blocos alterados são refeitos; áudio
  inteiro à parte (.wav) e junção com FFmpeg concat sem recomprimir. Cenas HERDAM os efeitos da versão anterior
  (mesmo id e tipo; `montar._herdar`), semente e folga de corte são por id → mexer numa cena não muda as outras.
- Escolha de imagens em lotes ✅ (`escolher.py`: 6 folhas por chamada + reenvio do que o Claude "não viu");
  busca com prioridade para personagem/lugar (`candidatos.Acervo`: vocabulário das etiquetas, tolera grafia,
  ≥2 candidatos do personagem; ignora arquivos que sumiram da pasta); `busca.arquivo` = arquivo pedido pelo nome
  (escolha fixa, sem Claude). Revisão ("Pedir ao diretor") vê o trecho inteiro e pode DIVIDIR a cena em várias.
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
- Pacote pós-1º vídeo ✅ (2026-10-19): **estilo visual por vídeo** (`direcao/estilo_visual.json`; o 1º vídeo ficou
  na versão 1, vídeos novos = 2): transições de entrada empurrar/sobrepor (`app/video/src/cenas/Estilo2.tsx`,
  ~1 em 7 cenas, nunca na 1ª do bloco; storyboard "entrada"), cartão sem recorte, texto entra junto com a imagem
  (retrospectiva: Runeterra/docs/regras_de_direcao.md §5). Linhas que ligam o Estilo2 são `impressao:ignorar` → cache dos
  vídeos antigos intacto. Roteiro mudou: só o trecho alterado volta ao Claude (`planejar.remendar_bloco`) e ajustes
  presos a palavras seguem a palavra (`storyboard.remapear_ajustes`); capítulo intocado não reenvia recusadas.
  Storyboard: "a cena começa em" (mover corte), juntar até 4 cenas, movimento "nenhum", lista "sem imagem".
  Cópia de segurança automática (`motor.copia_de_seguranca`, direcao/seguranca/, últimas 15) antes de roteiro
  novo/direção/pedido ao diretor; cache guarda os blocos da versão anterior também. Card "Vídeo já publicado".
- **Aprendizado entre vídeos ✅ (2026-10-20)**: `tools/direcao/aprendizado.py`. Ao publicar (antes de arquivar),
  `coletar()` guarda os pares de legenda "diretor → Felipe" (vão no prompt do diretor: `planejar.sistema_do_diretor`)
  e a retrospectiva dos ajustes; tarefa global "retrospectiva" (Sonnet) propõe regras novas, que só entram em
  regras_de_direcao.md do canal se o Felipe aprovar (botão "Aprendizado" no quadro). Arquivos em <dados do canal>/aprendizado/.
  Vertical (2026-11-05): cada "Refazer com os pedidos" guarda os pedidos em `direcao/historico_pedidos_vertical.json`
  (`motor.guardar_pedidos_vertical`, com a fala do plano); na publicação `aprendizado.coletar_vertical` faz a retrospectiva.
  Pedido feito pelo chat (animação escrita pela sessão) entra no mesmo arquivo com `"via": "chat"`.
  NÃO aprender "gosto de imagem" por pontuação (o Felipe recusou: as mesmas imagens passariam na frente).
- GIF animado ✅: `app/video/src/componentes/Figura.tsx` (`@remotion/gif`); montagem mantém .gif animado.
