# Tempos de trabalho — card 21 "Nove milésimos (teste do fluxo completo)" (medição por etapa)

Início da execução autônoma: 2026-11-14 01:04:16 (prazo do Felipe: ~8 h). Card NOVO (21) no fluxo documental novo; o
card 20 antigo (fluxo V1) não foi mexido. Executor "produtor" = um agente Opus 5.5 no papel de orquestrador + diretor.
Relógio da máquina (America/Sao_Paulo).

| etapa | início | fim | duração | executor | gargalo / ideia |
|---|---|---|---|---|---|
| leitura de docs, memória e apontamentos | 01:20 | 01:22 | ~2 min | produtor | — |
| correção do roteiro (diff em `roteiro_nove_milesimos.diff`) + conferência própria no OpenF1 (/laps, st_speed) | 01:21 | 01:22:43 | ~1 min | produtor | — |
| card criado + roteiro enviado (API) | 01:22:50 | 01:23:31 | 41 s | painel | curl do Git Bash quebra UTF-8 no corpo JSON: usar Python/urllib |
| conferência do roteiro (4 prompts do orquestrador respondidos) | 01:23:31 | 01:27:22 | 3 min 51 s | painel + produtor | cada prompt espera o "Continuar" (≈ 20–30 s parado entre prompts); 2 prompts `fatos` só com Wikipedia, inúteis para dados de 2026: pular a Wikipedia quando o OpenF1 resolve todos os números |
| voz guia Fish (90,9 s de áudio) + tempos por palavra (Whisper) | 01:28:21 | 01:29:33 | 1 min 12 s | motor do painel | — |
| GPS (2 voltas, pista plana do México) + comparação do kit/graficos | 01:28:51 | 01:29:22 | 31 s (+10 s) | produtor (CLI do kit) | rodou em paralelo com a voz guia |
| História (prompt → resposta → aplicar → ★) | 01:30:01 | 01:30:33 | 32 s (+ escrita) | produtor | — |
| SPEC (19 cenas) + 1 retrabalho (AFIRMACAO_SEM_ATIVO em cenas só de texto) | 01:30:39 | 01:37:13 | ~6,5 min | produtor | escrita da SPEC e do código novo intercaladas |
| código: receitas cartoes/foco, HUD/câmera alta do GPS, correções de ativos/verificação | 01:31 | 01:39 | ~8 min | produtor (worktree) | — |
| Ativos + Verificação (worktree) | 01:37 | 01:39 | ~2 min | produtor | 2 bugs: pista plana cobrada como .glb; tempo absoluto de setor com 2 carros cobrado como diferença |
| Rascunho 1 (19 cenas, 1280×720, EM SÉRIE) | ~01:37:50 | 01:45:23 | ~7,5 min | montador | 5 cenas HyperFrames uma a uma (~60–90 s cada) e lotes Remotion depois: CPU/GPU ociosas → paralelo (abaixo) |
| PAUSA: cota da janela de 5 h esgotada | ~01:47 | ~02:40 | ~53 min | — | maior gargalo da noite; retomado quando o coordenador liberou |
| revisão das folhas de sequência + correções (cartão cortado, gráfico de delta enganoso, destaque contraditório, câmera) | 01:45 / 02:40 | 02:45 | ~8 min úteis | produtor | folha própria (4 quadros por cena) achou o que a verificação automática não acha |
| Rascunho 2 (5 cenas novas, PARALELO 3) | 02:43 | 02:46 | 2 min 55 s | montador | 4 Remotion num lote + 1 HyperFrames ao mesmo tempo |
| Rascunho 3 (5 cenas GPS, câmera alta recentrada, paralelo 3) | 02:47 | 02:52 | 4 min 58 s | montador | as 5 cenas HyperFrames terminaram a ~30 s uma da outra (02:49:02 → 02:51:14): o HyperFrames (npx) NÃO paraleliza na prática (serializa por dentro ou disputa a GPU); o paralelo só ganha juntando Remotion com HyperFrames |
| testes (diretor 91, painel 163+34+34, receitas 21) | 02:46 | 02:53 | ~4 min | produtor | — |
| gravação provisória (voz Fish copiada para entrada/) + limpeza do painel | 02:58:40 | 02:59 | <1 min | motor do painel | 1 corte, 1 pausa encurtada |
| PR #113 (receitas, correções, dados) + testes do montador (81/81, ~10 min com render real) | 02:53 | 03:12 | ~19 min | produtor | o teste do montador é o mais lento (renders reais nos 2 motores): rodar só quando o montador mudar |
| pull na pasta principal (coordenador) | 03:12 | 03:12:50 | <1 min | coordenador | o agente na worktree não pode mexer no git da pasta principal |
| Ativos + Verificação + Rascunho pelo PAINEL (código novo, 19 cenas, paralelo) | 03:13:02 | 03:17:50 | 4 min 48 s | painel + montador | cache não aproveitado: hash do código muda entre worktree (LF) e pasta principal (CRLF) → tudo renderizado de novo |
| prévias + ★ das 19 cenas + ★ do Rascunho | 03:18 | 03:19:40 | ~1,5 min | painel (API) | prévias saíram do cache do rascunho (na hora) |
| aprovar gravação → ressincronização (1 cena) → RENDER FINAL v1 1080p60 | 03:19:47 | 03:26:53 | 7 min 06 s | motor do painel | cenas 1080p em ~3,5 min (paralelo), 3 blocos NVENC ~1 min, verificação por quadro ~2 min; barra parada em 0 % durante as cenas (corrigido no 2º PR) |
| revisão do final v1 (folhas) → correções: HUD pequeno em 1080p, oval cortando letras | 03:27 | 03:40 | ~13 min | produtor | — |
| PR #114 + testes (anotacao com render nos 2 motores, montador 81/81 duas vezes: 1 falha de texto da barra corrigida) | 03:33 | 03:50 | ~17 min | produtor | — |
| pull (coordenador) → Ativos/Verificação/Rascunho no painel (11 cenas renderizadas, 8 do cache) | 03:50:31 | 03:55:10 | 4 min 39 s | painel + montador | — |
| prévias + ★ de 11 cenas + ★ Rascunho → "Renderizar o vídeo final" | 03:55 | 03:56:21 | ~1,5 min | painel (API) | — |
| RENDER FINAL v2 1080p60 (barra cena a cena funcionando) | 03:56:23 | 04:02:58 | 6 min 35 s (montador 398,5 s) | motor do painel | MP4 pronto às 04:00:54; ~2 min de verificação por quadro depois |

## Resumo
- Do card criado ao 1º vídeo final: 01:22:50 → 03:26:53 = 2 h 04 min de relógio, dos quais ~53 min de pausa por cota.
  Trabalho útil ≈ 1 h 10 min. Versão corrigida (v2): 04:02:58.
- Maiores gargalos: (1) pausa da cota; (2) escrever código que faltava no meio do fluxo (receitas, bugs);
  (3) o teste completo do montador (~10 min com render real, rodado 3×); (4) HyperFrames ~30–60 s por cena GPS,
  sem ganho de paralelo entre cenas HyperFrames; (5) o "Continuar" manual entre prompts da conferência.
- Otimizações aplicadas: render paralelo (Remotion + HyperFrames juntos; rascunho completo 7,5 min → 4,8 min),
  GPS/comparação baixados em paralelo com a voz guia, prévias do storyboard saindo do cache do rascunho.
- Próximas: hash do código sem depender de fim de linha (CRLF×LF) para reaproveitar o cache entre worktree e pasta
  principal; HyperFrames com várias cenas GPS numa página (1 custo fixo); conferência pular Wikipedia quando o OpenF1
  decide; o painel retomar o orquestrador sozinho quando aparece o arquivo de resposta.
