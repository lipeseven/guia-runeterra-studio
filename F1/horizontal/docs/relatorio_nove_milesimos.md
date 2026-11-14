# Relatório do 1º vídeo completo do documentário horizontal — card 21 "Nove milésimos" (2026-11-14)

Produzido de madrugada por um agente (Opus 5.5) no papel de orquestrador + diretor, com autonomia do Felipe.
**A narração é a voz guia Fish Audio (PROVISÓRIA, nunca publicar)**: foi colocada na pasta `entrada/` como se fosse a
gravação, para exercitar o fluxo inteiro (limpeza → ressincronização → render final). Trocar pela voz do Felipe antes de
publicar: gravar → "Já coloquei na pasta" → aprovar → o painel ressincroniza e renderiza de novo.

## O que foi feito (fluxo do card)
Roteiro (corrigido, ver abaixo) → conferência pelo orquestrador (4 prompts) → voz guia Fish → História ★ (4 capítulos,
15 afirmações) → SPEC ★ (19 cenas: 14 Remotion, 5 HyperFrames) → Ativos (11 prontos) → Verificação (0 erros, 4 avisos) →
Rascunho (3 rodadas, olhado em folhas de sequência) → Gravação (voz Fish provisória, limpa pelo painel) → Ressincronização
→ Render final 1080p60 → (Publicação não feita).

## Correções do roteiro (mínimas; diff em `roteiro_nove_milesimos.diff`)
Conferido no OpenF1 (sessão 11400, `/laps` e `/car_data`): tempos 1:16.514 × 1:16.523, setores 26.852/30.030/19.632 ×
26.877/30.008/19.638 (25, 22 e 6 milésimos), speed trap (`st_speed`) HAM 347 × RUS 350, Curva 1: último ponto antes do
freio RUS 349 × HAM 344, mínima HAM 104 × RUS 100, freio HAM ~15–22 m depois (amostragem ~4 Hz: ±15 m).
- "Russell chegou a registrar 349 km/h, contra 345" → "logo antes da frenagem, Russell registrava 349 km/h, contra 345"
  (os dois chegam a 350 na reta).
- "aproveitando principalmente sua vantagem nas curvas de alta velocidade" → "ao que tudo indica pela vantagem nas curvas
  mais rápidas do setor" (é interpretação; os dados integrados não sustentam um trecho exato).
- "Russell chegou a atingir 350 km/h, enquanto Hamilton registrou 347 km/h de velocidade máxima na comparação das voltas"
  → "No speed trap, Russell chegou a 350 km/h, enquanto Hamilton registrou 347 km/h." (347 não é a máxima: é o speed trap).
- `**negrito**` tirado (o painel já tira, mas o arquivo ficou limpo).

## As 19 cenas (SPEC aprovada)
| # | trecho | motor | kit | o que mostra |
|---|---|---|---|---|
| 1 | Nove milésimos de segundo. | Remotion | anotacao (sublinhado) | "Nove milésimos" gigante, impacto |
| 2 | Foi essa a diferença entre | HyperFrames | gps (alta, tempo real) | os dois carros nos últimos 6 s da volta, HUD km/h |
| 3 | Mas o mais interessante não | Remotion | graficos velocidade (volta inteira) | a volta inteira desenhada na fala |
| 4 | Hamilton colocou sua Ferrari na | Remotion | anotacao (oval em "514") | 1:16.514 · Hamilton · Ferrari · pole |
| 5 | Russell, com a Mercedes, ficou | Remotion | anotacao (sublinhado) | +0,009 s · Russell · Mercedes |
| 6 | E olhando os setores, a | Remotion | cartoes capítulo | PARTE 01 "A frenagem da curva 1" + traçado; riser+impacto |
| 7 | No primeiro setor, Hamilton foi | Remotion | graficos setores | barras 0,025 / 0,022 / 0,006 / 0,009 |
| 8 | Na aproximação da curva 1, | HyperFrames | gps (alta, tempo real) | reta → frenagem → Curva 1, HUD 349/345… |
| 9 | Mas Lewis compensou na frenagem: | Remotion | graficos telemetria 850–1450 m | acelerador, freio, marcha; Curva 1 |
| 10 | Já no segundo setor, a | Remotion | cartoes capítulo | PARTE 02 "O troco de Russell" |
| 11 | Russell recuperou 22 milésimos, ao | Remotion | graficos velocidade S2 + minimapa | sem destaque (ver bugs) |
| 12 | Mesmo com Hamilton conseguindo acelerar | HyperFrames | gps (alta) | saída do grampo (~2,1 km) |
| 13 | 30.008 contra 30.030. | Remotion | anotacao (oval) | os dois tempos do S2 |
| 14 | No último setor, Hamilton voltou | HyperFrames | gps (alta, acelerado 2×) | estádio |
| 15 | E assim chegamos ao resultado | Remotion | foco | 1:16.514 nítido, "contra 1:16.523" desfocado |
| 16 | No speed trap, Russell chegou | Remotion | graficos velocidade 100–1150 m | a reta: RUS sempre um pouco acima |
| 17 | Mas velocidade de reta não | Remotion | anotacao (riscado) | "Velocidade de reta" riscada, alerta |
| 18 | Hamilton encontrou o tempo justamente | HyperFrames | gps (perseguição, câmera lenta 2×) | a frenagem da Curva 1 de novo |
| 19 | Nove milésimos. Uma pole. | Remotion | anotacao (oval) | fecho, impacto + sino |
Transições: corte (padrão), fade (3, 12, 15, 19), wipe (6, 10, com whoosh), zoom (8, 18). SFX: 9 na SPEC + whoosh das
transições (16 eventos na mixagem), categorias impacto, pop, capitulo, clique, alerta, sino.

## Como cada tecnologia se comportou
- **OpenF1**: ótimo. Tempos e setores batem ao milésimo; `st_speed` resolveu o "347 de velocidade máxima". GPS ~3,7 Hz
  com buracos de até 1,2 s (o kit interpola bem: nada de vai-e-volta visto nas folhas). Telemetria ~4 Hz: o "22 m mais
  tarde" só dá para afirmar com ±15 m.
- **kit/gps**: pista plana do México traçada sozinha pelo GPS (`preparar_volta.py`, 31 s com download). Carros sempre
  avançando, rastro por equipe, nada sumindo, nada dentro do chão (pista plana). Câmera nova "alta" (panorâmica) ficou
  melhor que a perseguição colada. Fraco: o mundo é um plano cinza sem nada (sem arquibancada, sem número de curva,
  sem minimapa), o que vai contra "cor e vida" das regras. Os dois carros quase sempre um em cima do outro (é o GPS real).
- **kit/graficos**: velocidade, setores e telemetria bonitos e corretos. **O delta acumulado e o destaque "auto" NÃO
  servem para diferenças de milésimos**: a distância vem da integral da velocidade (`kit/graficos/py/preparar.py:191`)
  e o erro dela (±0,2 s nas frenagens) é 20× a diferença do vídeo. O delta mostrava picos de 0,3–0,4 s e o destaque do S2
  dizia "HAM ganha 0,121 s aqui" bem quando a fala dizia que Russell recuperou. Troquei por velocidade sem destaque.
  Precisa de distância pelo GPS (ou alinhamento por posição) antes de usar delta/destaque em pole decidida no detalhe.
  Curvas do México sem nome: só a "Curva 1" entrou (`kit/graficos/pista/Mexico City.json`), conferida no mínimo de velocidade.
- **kit/anotacao**: ovais estáveis (não pulam), sublinhado e riscado bons. O começo do oval aberto passa por cima da 1ª
  letra em textos grandes ("Nove", "30.008"): é o estilo, mas parece rabisco em cima do número.
- **kit/cartoes**: capítulo bonito; o adaptador Remotion desenhava o SVG em 1920 px fixos e no rascunho 1280×720 o cartão
  saía 1,5× maior e cortado (corrigido: `remotion/cartoes/CamadaCartoes.tsx`). Pessoa e tag sem receita (pessoa exige foto validada).
- **kit/foco**: funcionou de primeira sobre texto (cena 15). Véu cinza leve; fundo claro preservado.
- **kit/transicoes**: wipe, fade e zoom limpos nas folhas de junção; verificação por quadro aprovada.
- **kit/sfx**: banco com Freesound já no `main`. 12 itens tinham `pico_s` no catálogo diferente do pico real (até 91 ms:
  `alerta_hf_erro` tem dois bipes) e a verificação reprovava; catálogo corrigido e a verificação agora compara com o pico
  do próprio som (catálogo errado vira aviso).
- **kit/imagens**: **não usado**. Não procurei imagens reais desta classificação (tempo); o vídeo não tem nenhuma imagem real.
- **Remotion**: 14 cenas em lotes, estável. **HyperFrames**: 5 cenas GPS, estável, mas lento (~30–60 s por cena) e
  **não paraleliza** entre si (várias ao mesmo tempo terminam espaçadas ~30 s).
- **montador/blocos**: 3 blocos, concat sem recodificar, verificação por quadro e SFX aprovadas. Cache por hash não
  sobrevive à troca de pasta: o código da worktree (LF) e o da pasta principal (CRLF) têm hashes diferentes
  (`montador/receitas.py:62` hash pelo conteúdo bruto) e o rascunho do painel renderizou tudo de novo.
- **diretor**: prompts de história e SPEC claros; a verificação pegou 2 problemas reais da minha SPEC e 2 bugs dela
  mesma (ver abaixo). Exige `graficos/gps/imagens` na própria cena para afirmar um número (`diretor/verificar.py:320`):
  cena só de texto com "1:16.514" não pode citar a afirmação; tirei as afirmações dessas cenas (ficam como aviso).
- **painel**: criar card, enviar roteiro, orquestrador (prompts → resposta → "Continuar"), aprovar ★, ativos,
  verificação, rascunho, prévias, ★ por cena e gravação por pasta: tudo pela API, sem erro. A barra do render final
  ficou em 0 % até acabarem as cenas (efeito do render paralelo; corrigido no 2º PR).
- **voz Fish**: 90,9 s, 162 palavras/min (o ritmo do Felipe). Limpeza do painel: 1 corte, 1 pausa encurtada;
  ressincronização mexeu só na última cena e manteve o ★ dela.
- **conferência**: 11 + 6 afirmações; OpenF1 conferiu todas as numéricas de volta/setor/diferença/posição. Os 2 prompts
  de Wikipedia (fatos) não acharam nada da sessão de 2026 (todos `sem_fonte`) e só gastaram tempo. Não existe tipo
  `speed_trap` no `app/servidor/openf1.py:20` (só `velocidade_max` pelo car_data = 350 nos dois): o 347 ficou sem conferência automática.
- **orquestrador**: protocolo de arquivos funciona; o gargalo é o "Continuar" manual entre prompts.

## Bugs e lacunas achados (arquivo:linha) — e o que foi corrigido
Corrigidos (PR #113 e #114):
- `montador/receitas.py`: só sabia graficos/anotacao/gps → receitas `cartoes` (capítulo) e `foco` (texto ou caixa);
  GPS com câmera `alta`, HUD (sigla + km/h) e rodapé com o relógio e a fonte (`_nota_gps`).
- `remotion/cartoes/CamadaCartoes.tsx`: SVG com largura fixa em px → cartão 1,5× maior e cortado fora de 1920×1080.
- `montador/hyperframes/gps.html`: HUD em px fixos → tamanho relativo mudava entre rascunho (720p) e final (1080p).
- `kit/anotacao/anotacao.ts:180` (`formaOval`): os cantos da caixa eram conferidos SEM o giro; em texto largo o oval
  girado cortava a 1ª e a última letra ("Nove milésimos.", "30.008").
- `diretor/ativos.py` (`pista`): pista PLANA (sem .glb) cobrada como modelo + alinhamento → "falta" e rascunho barrado.
- `diretor/verificar.py` (`_valor`): tempo ABSOLUTO com 2 carros ("30.008 contra 30.030", "1:16.514 contra 1:16.523")
  era cobrado como diferença → VALOR_NAO_BATE falso.
- `montador/montar.py` (`narracao`): rascunho sem voz quando só havia a voz guia; render em série (agora paralelo) e
  barra do painel parada em 0 % com o paralelo.
- `montador/quadros.py` + `kit/sfx/catalogo.json`: `pico_s` de 12 sons errado (até 91 ms) → verificação reprovava.
- `kit/graficos/pista/Mexico City.json` (novo, só Curva 1); `app/painel/.../StoryboardDoc.tsx`: opção "panorâmica alta".

Abertos (não corrigidos):
- `kit/graficos/py/preparar.py:191` — distância pela integral da velocidade: delta e destaque "auto" com erro de
  ±0,2 s, inúteis em diferenças de milésimos (ver acima). Precisa de distância pelo GPS/posição.
- `app/servidor/openf1.py:20` — sem tipo `speed_trap` (`st_speed` do `/laps`) nem velocidade num ponto/curva
  (349×345, 104×100) nem ponto de frenagem: 5 fatos ficaram "não conferidos".
- `diretor/verificar.py:320` — cena só de texto não pode citar afirmação numérica (exige dado na própria cena).
- `montador/receitas.py:62` (`hash_arquivo`) — hash pelo conteúdo bruto: LF (worktree) × CRLF (pasta principal)
  invalida o cache entre as duas cópias (o painel renderizou de novo as 19 cenas).
- `montador/segmentos.py:70` (`_render_hyperframes`) — HyperFrames não paraleliza entre si; ~14 s de custo fixo por cena.
- Aviso do final diz "rascunho sem música" (`montador/montar.py`, texto do aviso de trilha).
- Sem trilha musical no projeto (o vídeo tem só voz + SFX).
- `kit/gps`: mundo vazio (plano cinza): sem minimapa, número de curva, arquibancada; cores e vida das regras do canal não
  atendidas nas cenas de pista. Kit imagens, cartão de pessoa, tag, normalizado, modelo3d: não usados neste vídeo.
- Conferência: os prompts de Wikipedia (`conferencia-fatos`) rodam mesmo quando o OpenF1 já decide tudo.

## O que NÃO verifiquei
- **Ninguém ouviu o vídeo.** Conferi loudness (−14,0 LUFS, pico −1,2 dBTP no MP4), a verificação automática de SFX
  (pico na palavra) e as folhas de quadros; equilíbrio voz × SFX e o gosto dos sons não foram julgados por ouvido.
- Vi 4 quadros por cena (+ quadros soltos), não o vídeo corrido a 60 q/s; suavidade do GPS conferida só nas folhas.
- A voz é a guia Fish acelerada ao ritmo do Felipe (162 ppm); com a voz dele os tempos mudam (o fluxo ressincroniza).
- Publicação não foi feita (nem o prompt de títulos); nada publicado.
- Os fatos não numéricos (349×345, 22 m, 104×100, speed trap) conferi à mão no OpenF1, não pela conferência automática.

## Resultado
- **Vídeo final:** `F1/dados/projetos/nove-milesimos-teste-do-fluxo-completo/saida/final_v2.mp4` (v1 ao lado, antes das
  correções de HUD e oval). 1920×1080, 60 q/s, 5.429 quadros, 90,5 s, H.264 NVENC + AAC; −14,0 LUFS, pico −1,2 dBTP
  medidos no MP4; verificação por quadro, junções e SFX aprovada (0 erros, 0 avisos). **Voz Fish provisória.**
- Card 21 no painel 8766. Tempos de cada etapa: `tempos_nove_milesimos.md`.
