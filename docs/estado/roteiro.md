# Estado: roteirista, pesquisa e conferência do roteiro

Saído do CLAUDE.md (2026-11-08). Ao terminar um recurso desta área, registre AQUI, não no CLAUDE.md.

- Roteirista no painel ✅ (2026-10-14): `app/servidor/roteirista.py` + tarefa "roteiro" no motor. Gera (do zero ou a
  partir de roteiro BASE gringo — inspiração, nunca tradução) e ajusta por pedido (Claude devolve só os parágrafos
  alterados → barato, preserva edições à mão). Edição à mão, versões (roteiro_vN.txt) com "voltar", conversa em
  direcao/conversa_roteiro.json. Jeito do canal: `Runeterra/docs/estilo_roteiro.md` (formato que o diretor exige + voz do Felipe).
- Conferência do roteiro ✅ (2026-10-19, `app/servidor/conferencia.py`, tarefa "conferencia" a cada roteiro novo):
  semelhança com o roteiro base (`direcao/roteiro_base.txt`; embeddings multilíngues locais, sentence-transformers)
  + fatos de lore (Sonnet extrai afirmações → wiki do LoL/Universe buscados localmente, cache em Runeterra/dados/pesquisa_cache
  → Sonnet dá confere/diverge/sem fonte; cache por parágrafo). Painel: bloco "Conferência do roteiro" no Roteiro.
  Fontes (2026-10-30): wiki.leagueoflegends.com namespace Universe (3006; o fandom parou em 2023) + biografia E conto
  oficial do Universe (meeps `story-preview`); 2 trechos da wiki + 2 da Riot por afirmação; veredito traz `fontes` (quantas
  sustentam) e `fontes_divergem` (Riot oficial prevalece). Afirmações atômicas (1 fato cada), página `Universe:<personagem>`
  sempre incluída (`_pagina_do_personagem`), 3 trechos wiki + 2 Riot, veredito `parcial` ("confere em parte", diz o pedaço).
  Cache por parágrafo inclui `conferencia.REGRAS` (subir a versão ao mudar regra = tudo reconferido no próximo ↻);
  "conferir tudo" no painel (`/roteiro/conferir?tudo=true`) apaga o cache. Botão "Corrigir" em cada item diverge/parcial (individual: o Felipe lê cada um) põe na fila; "Mandar correções" = uma chamada só a `/roteiro/ajustar`, versão nova. "Manter minha versão" tira o item da lista (localStorage, por afirmação; parágrafo editado volta a avaliar). "O que mudou nesta versão" (`MudancasRoteiro.tsx`, `roteirista.mudancas`; difflib local, palavra por palavra): "desfazer" por alteração (`/roteiro/desfazer`) vira versão nova e mantém a mesma base da comparação (`direcao/comparar_com.json`). Regras 4 (2026-10-31): vale o ponto mais recente da história, não a biografia da Riot (`conferencia.REGRA_DAS_FONTES`, também no dossiê e no crivo); busca inclui eventos, LoR e Riftbound (`ns_extra`); `<Canal>/dados/fatos_do_canal.txt` (painel: "fatos do canal") = anotações do Felipe, vale acima de todas. Conferência por TRECHOS (2026-10-31, `conferencia._cortar`: ~60-90 palavras, corte definido pela própria frase; cache `REGRAS:hash` guarda também versões anteriores): só trecho com texto alterado volta ao Claude, em lotes de 8; `conferencia.json` traz `rodada` (novas/resolvidas); cache antigo por parágrafo é repartido (`_migrar`) sem gastar cota. Fontes por trecho do roteiro: página achada para uma afirmação serve às outras do mesmo trecho; a busca leva o nome do personagem; `trecho` -1 = item sem link (nunca fonte só de assunto parecido). Reddit: API bloqueia sem chave (403) — exigiria app Reddit do Felipe.
- **Pesquisa antes do roteiro ✅ (2026-10-29)**: `app/servidor/pesquisa.py` roda dentro da tarefa "roteiro" (gerar): Sonnet lista
  assuntos → wiki/Universe locais (cache) → dossiê de fatos com fonte e selo canon (atual/antigo/jogo) + crivo do roteiro
  base (confirmada/corrigida/desatualizada/sem_fonte) em `direcao/dossie.json`. O roteirista (gerar e ajustar) só afirma
  fatos do dossiê; o base vira só estrutura. Painel: bloco "Pesquisa" na Conferência. Zoom da capa nos hubs (`Capa.tsx`, 2026-10-31): círculo a 8 px do topo e nome a 8 px da base (`montar._folga_do_nome` mede a altura do nome na capa), mesmo zoom em todos os capítulos.
  Roteiro base colado (transcrição do YT) passa por `conferencia.limpar_base` (tira tempos/[Música], junta linhas);
  `frases()` corta texto sem pontuação em trechos de ~20 palavras.
  Encerramento fixo: ao aprovar o vídeo, `publicacao.com_encerramento` junta o último final + `<dados do canal>/encerramento/encerramento.mp4`
  (Runeterra: Runeterra/dados/encerramento/) → `saida/final_vN_publicar.mp4` (só o encerramento é recodificado; final intacto).
  Depois da gravação aprovada, "novo rascunho" no storyboard gera um VÍDEO FINAL novo (voz real), não rascunho com voz guia.
