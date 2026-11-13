# Painel do documentário horizontal (fase 4)

Card novo no painel do F1: formato **`horizontal_doc`** ("documentário" no botão do quadro), ligado por
`[horizontal_doc]` no `F1/canal.toml`. Serve para qualquer vídeo de F1: o painel não sabe nada de GP, piloto ou pista,
só mostra e grava o protocolo de arquivos do `diretor/` (ver `../diretor/README.md`).

## Etapas do card
Roteiro → Narração → **História ★** → **SPEC ★** → Ativos → Verificação → **Rascunho ★** → Publicação.
Roteiro e Narração são os de sempre (painel Roteiro e painel Voz: a gravação do Felipe é limpa e medida, como no
horizontal animado). As cinco do meio são o `estado.json` de `F1/dados/projetos/<slug>/horizontal/`, espelhado nas
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

Entradas: `direcao/roteiro.txt` do card vira `horizontal/roteiro.txt`; `direcao/tempos_voz.json` (narração medida) vira
`horizontal/palavras.json` **só** se tiver o mesmo número de palavras do roteiro (senão aviso e tempos estimados).

## Observações gerais do Felipe
O painel "Observações gerais" do card (voz ou texto, `docs/observacoes.md` na raiz) grava `<projeto>/observacoes.json`;
a ponte (`sincronizar_observacoes`, em `resumo`/`passo`) copia para `horizontal/observacoes.txt`, e `comum.observacoes`
põe o texto nos prompts da História, da SPEC e do pedido por cena (`{{observacoes}}`).

## Testes
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\testar_api.py [-v] [--manter]` — 86 checagens (61 + 25 do
  storyboard: listar, ação direta mantém a SPEC aprovada, movimento/ação desconhecida recusados, corte movido, ★ da cena
  recusada sem prévia/receita, pedido por voz vira prompt só da cena), ~15 s,
  TestClient em processo (sem porta), dados fictícios em `testes/painel/dados/api/` (apagados no fim). Caminho inteiro:
  criar → roteiro → narração → História (prompt, orquestrador, pedido/retirar, ★) → SPEC (arquivo mexido barrado,
  pedido por cena, refazer só a cena, ★) → Ativos → Verificação → Rascunho "sem montador ainda"; vertical e
  horizontal animado com as etapas de sempre; motor não põe a direção do animado na fila.
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\servidor.py --porta 8799` — painel numa porta temporária
  (recusa 8765/8766) com dados fictícios e um card documental semeado (História aguardando ★), para ver as telas.
  Precisa do `app/painel/dist` compilado. `--storyboard` semeia mais um card já no Rascunho com o mini-spec e os
  trechos do `testes/montador/testar.py` (rode-o antes) para ver o storyboard com quadros de verdade.

## Limites (o que não foi verificado / não existe)
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
