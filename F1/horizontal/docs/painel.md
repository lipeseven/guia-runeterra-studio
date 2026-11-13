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
| Rascunho sem `montador/montar.py` | Em breve — "sem montador ainda" |

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
- Rascunho: só o gancho, "sem montador ainda" (montador é a fase 5).

## API (`app/servidor/horizontal_doc.py`)
| Rota | Faz |
|---|---|
| `GET /api/videos/{id}/doc` | sincroniza roteiro/narração do card para a pasta horizontal e devolve estado, história, SPEC, ativos, verificação, tarefas do orquestrador |
| `POST /api/videos/{id}/doc/passo/{historia\|spec\|ativos\|verificacao\|rascunho}` | dispara o passo (409 com o motivo quando não vale: roteiro não aprovado, etapa anterior sem ★, "sem montador ainda") |
| `POST /api/videos/{id}/doc/aprovar/{historia\|spec\|rascunho}` | ★ pelo `etapas.aprovar` |
| `POST /api/videos/{id}/doc/pedido` `{etapa, texto, cena?}` | `etapas.pedir` (cena precisa existir na SPEC) |
| `DELETE /api/videos/{id}/doc/pedido/{pid}` | retira (status `recusado`); sem outros pedidos abertos a etapa volta a `gerado` |

Entradas: `direcao/roteiro.txt` do card vira `horizontal/roteiro.txt`; `direcao/tempos_voz.json` (narração medida) vira
`horizontal/palavras.json` **só** se tiver o mesmo número de palavras do roteiro (senão aviso e tempos estimados).

## Testes
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\testar_api.py [-v] [--manter]` — 61 checagens, ~10 s,
  TestClient em processo (sem porta), dados fictícios em `testes/painel/dados/api/` (apagados no fim). Caminho inteiro:
  criar → roteiro → narração → História (prompt, orquestrador, pedido/retirar, ★) → SPEC (arquivo mexido barrado,
  pedido por cena, refazer só a cena, ★) → Ativos → Verificação → Rascunho "sem montador ainda"; vertical e
  horizontal animado com as etapas de sempre; motor não põe a direção do animado na fila.
- `.venv\Scripts\python.exe F1\horizontal\testes\painel\servidor.py --porta 8799` — painel numa porta temporária
  (recusa 8765/8766) com dados fictícios e um card documental semeado (História aguardando ★), para ver as telas.
  Precisa do `app/painel/dist` compilado.

## Limites (o que não foi verificado / não existe)
- Nenhum prompt rodou num modelo; as respostas dos testes são as fixas de `testes/diretor/exemplo/`.
- O card só se atualiza quando alguém lê `/doc` (página do vídeo aberta) ou quando o motor avisa (roteiro aprovado,
  narração pronta). Arquivo escrito pelo orquestrador com a página fechada aparece no quadro na próxima leitura.
- Narração real (upload, limpeza, medição) não foi exercida no teste: o `tempos_voz.json` é fictício.
- `ativos.py --produzir` não é disparado pelo painel (rede): o comando vai para o orquestrador.
- Rascunho: sem montador ainda; aprovar Rascunho devolve 409.
