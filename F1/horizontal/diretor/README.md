# diretor/ — história, SPEC por palavra, ativos e verificação (horizontal documental)

Fase 3 do `../PLANO.md`. Serve para **qualquer** vídeo de F1: nada de GP, piloto ou pista fixo no código; tudo vem do
roteiro, do briefing e da sessão do OpenF1 que a história cita. Não renderiza nada.

Quem escreve a história e a SPEC é o modelo (Claude), pelos prompts em `prompts/`. Este pacote **não chama** o modelo
(nada de `claude -p` aqui): ele monta o prompt, recebe a resposta (arquivo JSON), prende tudo às palavras do roteiro,
valida e grava. Quem executa o prompt é o orquestrador (hoje, o chat com subagentes) ou o painel (no futuro), sobre o
mesmo protocolo de arquivos.

```
roteiro.txt + palavras.json ─▶ historia.py ─▶ historia.json ★ ─▶ spec.py ─▶ spec.json ★ ─▶ ativos.py ─▶ ativos.json
                                                                                         └──────▶ verificar.py ─▶ verificacao/verificacao.json
```
★ = aprovação do Felipe (`etapas.aprovar`). Pedido de mudança por cena: `etapas.pedir(..., cena=id)` + `spec.py pedido`.

## Arquivos
| Arquivo | O que faz |
|---|---|
| `historia.py` | prompt da história; resposta → `historia.json` (capítulos e afirmações presos a trechos literais do roteiro) |
| `spec.py` | prompt da SPEC; resposta → `spec.json` (cenas por palavra, motor por cena, kits e parâmetros); `retemporizar` (narração nova), `prompt_pedido`/`trocar_cena` (pedido em UMA cena) |
| `ativos.py` | resolve o que cada cena precisa nos kits (OpenF1 via `kit/gps` e `kit/graficos`, imagens via `kit/imagens`, `kit/sfx`, modelos 3D); `--produzir` roda o que falta (rede) |
| `verificar.py` | checagens automáticas da SPEC (lista abaixo); grava `verificacao/verificacao.json`; sai 1 se houver erro |
| `etapas.py` | fluxo e `estado.json` (gerado/aprovado/desatualizado, pedidos, histórico) |
| `painel.py` | ponte com o painel (JSON pela entrada/saída padrão) e `aplicar` do orquestrador; ver `../docs/painel.md` |
| `ajustes.py` | ações diretas do storyboard (movimento, transição, corte/fim, SFX, escolhas fechadas do kit) aplicadas na SPEC sem modelo; gravadas por `etapas.ajustar` (SPEC segue aprovada, etapas seguintes desatualizadas); campo novo da cena: `movimento` {tipo, intensidade?, foco?} |
| `comum.py` | caminhos, palavras e âncoras (mesma regra do `tools/direcao/vertical.py`), cache por prompt, **registro dos kits** (`KITS`) |
| `esquema.py` | validador de JSON Schema (subconjunto, sem dependência; o `.venv` não tem `jsonschema`) |
| `esquemas/*.schema.json` | JSON Schema de `historia`, `spec`, `ativos` e `estado` (padrão draft 2020-12) |
| `prompts/historia.txt`, `spec.txt`, `pedido_cena.txt` | prompts do diretor (`{{campo}}` preenchido pelo código; as regras de `F1/docs/regras_de_direcao.md` entram inteiras) |

Teste: `.venv\Scripts\python.exe F1\horizontal\testes\diretor\testar.py [-v]` (offline, ~1 s).

## Protocolo de arquivos (pasta `F1/dados/projetos/<slug>/horizontal/`, fora do Git)
| Arquivo | Quem escreve | Conteúdo |
|---|---|---|
| `roteiro.txt` | painel (roteiro gravado) | texto falado, igual ao da narração |
| `palavras.json` | painel (narração medida) | `[{"t": palavra, "i": início s, "f": fim s}]`. Sem ele, tempos **estimados** (`comum.estimar_tempos`, marcados `tempos: "estimados"`) |
| `briefing.txt` | roteirista (opcional) | pedidos do vídeo: sessão(ões) do OpenF1, pilotos, o que evitar |
| `prompts/<etapa>.prompt.txt` | `historia.py prompt`, `spec.py prompt/pedido` | o prompt pronto para o modelo |
| `cache/<etapa>_<hash do prompt>.json` | `aplicar` | resposta do modelo por prompt (mesmo prompt = sem gastar cota de novo) |
| `historia.json` | `historia.py aplicar` | ver `esquemas/historia.schema.json` |
| `spec.json` | `spec.py aplicar` | ver `esquemas/spec.schema.json`; guarda `roteiro_hash` e `historia_hash` |
| `ativos.json` | `ativos.py` | itens `pronto/falta/nao_validado/reprovado/nao_encontrado`, com `comando` do que falta; guarda `spec_hash` |
| `ativos/imagens/` | `kit/imagens.achar` | `<slug>.mp4/.png/.json` + `FONTES.txt` (o `.json` tem o `status` da validação) |
| `verificacao/verificacao.json` | `verificar.py` | `status` (`reprovado` / `pendente` / `aprovado`), `erros`, `pendencias`, `avisos` |
| `estado.json` | `etapas.py` (todas as etapas) | `etapa_atual`, cada etapa com `status`, `hash`, `base_hash`, `aprovado_em`; `pedidos` (por cena) e `historico` |

Regras do estado: cada etapa grava o hash do próprio arquivo e o da etapa de que veio. Arquivo regravado com outro
conteúdo deixa as etapas seguintes `desatualizado`. `aprovar` recusa se o arquivo mudou depois de gerado ou se a etapa
anterior não está aprovada (ou gerada, nas etapas sem ★). Gravação atômica (o painel nunca lê meio arquivo).

### Como o orquestrador roda uma etapa
```
python F1/horizontal/diretor/historia.py prompt  <pasta>                  # → prompts/historia.prompt.txt
   (o modelo lê o prompt e devolve JSON → resposta_historia.json)
python F1/horizontal/diretor/historia.py aplicar <pasta> resposta_historia.json
   (Felipe aprova no painel → etapas.aprovar(pasta, "historia"))
python F1/horizontal/diretor/spec.py prompt  <pasta>   |   spec.py aplicar <pasta> resposta_spec.json
python F1/horizontal/diretor/ativos.py <pasta> [--produzir]
python F1/horizontal/diretor/verificar.py <pasta>
```

## SPEC: uma cena
```jsonc
{ "id": "8616fdff",                 // hash do trecho-âncora (estável entre versões)
  "em": "Na classificação de 2025,", "i0": 14, "i1": 25, "t0": 5.6, "t1": 9.8,   // índices e tempos vêm das palavras (valores ilustrativos)
  "capitulo": "c2", "objetivo": "os dois carros na mesma pista, cada um no próprio GPS",
  "motor": "hyperframes", "camera": "panorâmica alta acompanhando os dois",
  "kits": [{"kit": "gps", "params": {"sessao": 9908, "carros": [{"piloto": 16, "volta": 16}, {"piloto": 44, "volta": 16}], "fator": 2.2}}],
  "afirmacoes": [], "texto": ["Classificação · Monza 2025", "acelerado 2,2x"],
  "sfx": [{"categoria": "impacto", "em": "Monza?", "i": 13, "intensidade": 0.8}],
  "transicao": {"tipo": "wipe", "quadros": 24},
  "aceitar_nao_validado": "(só com OK do Felipe) motivo"  }
```
Âncoras dentro de `params` (qualquer objeto com `"em"`, como `graficos.ritmo[]`) ganham `"i"` da palavra.
O registro `comum.KITS` diz o que cada kit exige (`requer`, `tipos`) e o motor indicado; ele também vai no prompt.

## O que a verificação barra (erro) — todos com caso no teste
Âncoras: `ANCORA_CENA`, `ANCORA_SFX`, `ANCORA_PARAMETRO` (trecho que não existe ou não está na palavra marcada, ou fora
da cena), `ANCORA_CAPITULO`, `ANCORA_AFIRMACAO`, `ORDEM` (buraco/sobreposição, 1ª cena fora da palavra 0),
`ROTEIRO_MUDOU`, `HISTORIA_MUDOU`, `ATIVOS_DESATUALIZADOS` (hashes). Tempo: `TEMPO` (t0/t1 diferentes das palavras),
`DURACAO` (< 1 s ou > 30 s; > 12 s = aviso). Motor e kits: `MOTOR`, `ESQUEMA_SPEC`, `KIT_PARAMETRO`, `KIT_DESCONHECIDO`,
`TRANSICAO` (1ª cena sem corte, corte com quadros, transição maior que metade da cena). Afirmações:
`AFIRMACAO_INEXISTENTE`, `AFIRMACAO_FORA_DA_CENA` (a prova apareceria quando a fala já passou), `AFIRMACAO_DADOS`
(gráfico/GPS de outra sessão, carro ou volta), `AFIRMACAO_SEM_ATIVO` (tempo/diferença/setor/velocidade sem gps,
graficos ou imagens), `VALOR_NAO_BATE` (valor dito × tempos oficiais na comparação do `kit/graficos`; tolerância
0,5 ms no tempo e 1,5 ms na diferença), `IMAGEM_SEM_AFIRMACAO`. Imagens: `IMAGEM_NAO_VALIDADA` (não validada sem
`aceitar_nao_validado`, ou aceita sem "imagem ilustrativa"/"não validada" escrito na tela), `ATIVO_REPROVADO`,
`ATIVO_NAO_ENCONTRADO`. Tela e som: `NUMERO_NA_TELA` (número que a fala da cena não diz nem está numa afirmação dela;
rodapé técnico "acelerado…", "Dados:…", "em tempo real" é livre), `SFX_PERTO` (< 0,5 s), `SFX_CATEGORIA`.
Pendência (não é erro): `ATIVO_FALTA` (com o comando), `ATIVOS_NAO_RESOLVIDOS`.
Avisos: `DURACAO_LONGA`, `MOTOR_PREFERIDO`, `CAPITULO_TROCADO`, `TRANSICAO_FORA_DO_PADRAO`, `SFX_DENSIDADE`
(mais de 1 a cada 8 s), `AFIRMACAO_SEM_CENA`, `VALOR_NAO_CONFERIDO`, `IMAGEM_NAO_VALIDADA_ACEITA`.

## Resultado do teste (2026-11-13)
Roteiro de exemplo de 91 palavras (~41 s estimados): Monza 2025, classificação (session_key 9908), LEC v16 1:19,007 ×
HAM v16 1:19,124. História: 4 capítulos, 7 afirmações (6 verificáveis; a inventada saiu com aviso). SPEC: 8 cenas (a
de trecho inventado saiu), 2 em HyperFrames e 6 em Remotion. Ativos: comparação do `kit/graficos` pronta (os 6 valores
— 2 tempos, a diferença de 0,117 e os 3 setores — conferidos com o OpenF1), GPS de Monza **falta** com o comando (desde a fase 2b o
GPS de Monza existe no `kit/gps`: o teste aponta `ativos.VOLTAS_GPS` para uma pasta vazia para exercitar a falta e
confere à parte que o kit real dá `pronto`), imagem `nao_validado` (resultado **simulado** do `kit/imagens`: classificação
não tem contador de volta). Verificação: `pendente`, 0 erros. Depois, 34 casos errados, cada um barrado com o código
esperado. 82 checagens, 0 falhas.

## O que NÃO foi verificado
- **Nenhum prompt foi executado por um modelo.** As respostas do teste (`testes/diretor/exemplo/resposta_*.json`) foram
  escritas à mão no formato pedido. A qualidade da história/SPEC que o Claude escrever com estes prompts só se vê no
  primeiro uso real; o código barra o que for estruturalmente errado, não direção fraca.
- Tempos do exemplo são **estimados** (sem narração gravada). `retemporizar` foi testado só com tempos escalados.
- `ativos.py --produzir` (rede: OpenF1, `preparar_volta.py`, `preparar.py`, `kit/imagens.achar`) **não foi rodado**
  nesta fase; os comandos montados seguem os READMEs dos kits. O resultado de imagem do teste é fictício.
- `VALOR_NAO_BATE` só confere tempo de volta, diferença e setor, e só quando há comparação pronta dos mesmos carros
  (velocidade, posição, evento ficam `VALOR_NAO_CONFERIDO`/sem conferência numérica).
- `NUMERO_NA_TELA` compara dígitos: número falado por extenso ("um décimo") no roteiro não conta como dito.
- Pista para o GPS: o item `pista` exige o `.glb` em `F1/dados/modelos3d` e um alinhamento em `kit/gps/pista/`
  (hoje só Interlagos). A generalização do `kit/gps` é a fase 2b.
- Painel: ligado na fase 4 (`painel.py` + `app/servidor/horizontal_doc.py`, ver `../docs/painel.md`).
