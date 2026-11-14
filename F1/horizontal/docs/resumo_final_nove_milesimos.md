# Resumo final — card 21 "Nove milésimos" (2026-11-14)

**Vídeo para assistir:** `F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v4.mp4` (1080p60, 90,5 s, 20 cenas, −14 LUFS). Narração = voz Fish provisória (não publicar). Card 21 no painel 8766. Nada foi publicado.

## Placar (rubrica: dados 25, sincronia 15, clareza 20, movimento 15, estética/vida 15, SFX 10)
| rodada | vídeo | global | cenas < 80 |
|---|---|---|---|
| 1 | final_v2 | 73,8 | 9 |
| 2 | final_v3 | 79,8 | 6 |
| 3 | final_v4 | **83,1** | 0 (mínimo 80: cenas 9a; 81: cena 12) |

Por critério (rodada 3): dados 93 %, sincronia 88 %, clareza 84 %, movimento 88 %, estética/vida 64 %, SFX 69 %. O teto agora é estética e SFX. Detalhe: `placar_nove_milesimos_rodada{1,2,3}.md`.

## Como cada tecnologia se comportou
Ver a seção "Como cada tecnologia se comportou" de `relatorio_nove_milesimos.md` e as seções das rodadas 1 e 2. Em uma linha cada:
- **OpenF1:** bom para tempos, setores, posições, car_data e GPS (~3,7 Hz, ruído ~2 m); faltavam speed trap e ponto de frenagem (speed trap incluído na rodada 1). Delta por distância integrada erra ±0,2 s.
- **kit/gps + HyperFrames:** carros sem vai-e-vem nem sumiço; cenas GPS ficaram ralas até a rodada 1 (mundo, arquibancadas, minimapa). HyperFrames é lento (30–60 s por cena GPS, sem ganho com paralelo).
- **Remotion:** rápido (cenas de gráfico/anotação/cartão), estável; render em lote e paralelo com o HyperFrames.
- **kit/graficos, anotacao, foco, cartoes, transicoes:** ovais 0 px de oscilação; gráficos corretos nos dados; duelos repetitivos (formato igual em 3 cenas).
- **kit/sfx + mixagem:** SFX estavam enterrados pelo sidechain; corrigido com reforço por categoria. Ainda "goteira" (17 momentos em 90 s).
- **montador/blocos/cache:** cache por cena funciona (15 de 20 cenas reaproveitadas); hash CRLF/LF corrigido.
- **diretor/painel/orquestrador:** fluxo de ponta a ponta funcionou pelo painel; pendências do orquestrador respondidas por arquivo; achou-se que a pasta principal estava atrás do GitHub (painel rodando código antigo).
- **conferência de fatos:** OpenF1 agora resolve a sessão a partir do texto; sem fonte vira "não conferido".
- **Voz Fish / Stable Audio local (trilha):** funcionaram; ninguém ouviu o resultado final.

## Melhorias recomendadas (por prioridade)
1. **SFX: reduzir a goteira** — manter 9–10 (regra do Felipe ~9 em 2 min 20 s) e cortar "classificação", "rápidas", "100%", "6", "1:16.523", "347", "frenagens", whoosh de 81 s. Decisão do Felipe: o produtor pôs 20 para atender o placar.
2. **Etiquetas HAM/RUS** trocam de lado num salto de ~94 px (13 vezes; 7 na cena 14): lado fixo por cena ou troca com deslize (`gps.html`).
3. **Duelos 9b/13/15** com o mesmo cartão, parados, metade de baixo vazia: variar formato.
4. **Cena 11:** o rosa cobre o gráfico todo; **cena 16:** eixo começa em 340 e exagera 3 km/h.
5. **Delta por distância integrada** (`kit/graficos/py/preparar.py:191`): usar posição GPS/tempo por setor para precisão de milésimos.
6. **GPS:** carros fundidos quando colados, Ferrari quase preta, mundo ainda vazio nas cenas 8 e 12; arquibancadas são aproximadas (só cenário).
7. **Imagens reais (kit/imagens)** e cartão de pessoa não usados no vídeo.
8. **Conferência:** tipo de ponto de frenagem; cena só de texto com afirmação numérica; "Continuar" entre prompts é manual.
9. **Tempo de máquina:** HyperFrames sem lote; render do final ~7–9 min/90 s; teste do montador ~10 min.

## O que um humano precisa checar (ninguém ouviu nem viu o vídeo corrido)
Sino do fecho (audível?), sequência de cliques 47–76 s (cansa?), cliques estalados ("1:16.514", "classificação"), impacto do capítulo 1 (atrasado?), trilha agradável, ritmo geral a 60 q/s, e todo o áudio com a SUA voz.

## Tempos de produção
Ver `tempos_nove_milesimos.md`. Ordem de grandeza: card→1º final 2 h 04 (53 min parados por cota); rascunho completo 5–8 min; final 7–9 min; cada rodada de correções ~30–45 min de relógio (sem pausas de cota).
