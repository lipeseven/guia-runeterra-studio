# Motor documental do horizontal — arquitetura (proposta de 2026-11-13)

## 1. O que é e no que difere
- **Runeterra:** catálogo sequencial. Clipes do acervo montados na ordem, quase automático.
- **Horizontal v1 (Remotion, `F1/video/src/horizontal/`):** diretor com vocabulário fixo de cenas; a direção roda no `claude -p` do painel.
- **Motor documental (este):** primeiro a HISTÓRIA, depois as cenas. Cada vídeo tem direção própria (livre) sobre um KIT fixo de componentes testados. Visual guiado por dados reais (OpenF1), 3D (carros e pista), imagens reais da corrida e motion graphics. Verificação por sequência de quadros, não por foto solta.

## 2. Estrutura de pastas
```
F1/horizontal/            código e docs do horizontal (ver README.md)
  kit/                    módulos independentes de motor: gps, sfx, anotacao, graficos, imagens, foco
  remotion/ hyperframes/  adaptadores de cada motor sobre o kit
  montador/               junta trechos por cena (ffmpeg) e faz UMA mixagem de áudio
  diretor/                historia, spec, ativos, verificar (Python)
  docs/ testes/
F1/vertical/              pasta reservada do vertical (migração só na fase 6)
F1/dados/projetos/<slug>/horizontal/   (fora do Git) historia.json, spec.json, ativos/, trechos/, verificacao/, estado.json
```
Partes que continuam no sistema compartilhado (`app/`, `tools/`): o painel (telas e API) e as funções genéricas. O fluxo do
F1 horizontal documental é declarado em `F1/horizontal/diretor/etapas.py` e referenciado por `[horizontal_doc]` no
`F1/canal.toml`; o painel só ganha ganchos mínimos.

## 3. Fluxo e pontos de aprovação do Felipe (★)
1. Roteiro (já existe) → 2. Narração: gravação dele, limpa e medida por palavra (já existe)
3. **História** (storyline: gancho, tese, evidências, tensão, desfecho, capítulos, ritmo denso/respiro) ★
4. **SPEC por palavra**: cada cena com objetivo, tipo, câmera, texto, dados, motor (`remotion` | `hyperframes`), SFX ★
5. **Ativos**: dados OpenF1 (corrida/volta/GPS), imagens reais validadas, modelos 3D, pista
6. **Composição** por cena no motor marcado
7. **Verificação**: scripts (ancoragem, texto cortado, tamanho estável, carro no chão, sem sumir) + sequências de quadros
8. **Rascunho** em baixa resolução (sem render pesado) ★
9. Render por cena + montador + mixagem única → 10. Publicação (já existe)

## 4. Quem executa
Dois modos sobre o MESMO protocolo de arquivos (`estado.json`, `spec.json`, pedidos):
- **Orquestrado (hoje):** o chat orquestra e subagentes (Opus 5.5 médio) executam cada etapa; o painel mostra o estado e recebe aprovações e pedidos.
- **Automático (futuro, quando o `claude -p` do painel tiver cota):** o painel dispara as mesmas funções de `diretor/`.
Nada depende de um único `claude -p` longo.

## 5. Kit (engine-agnostic) — o que resolve os defeitos vistos nos testes
| Módulo | Faz | Defeito que resolve |
|---|---|---|
| `kit/gps` | posição x,y,z do OpenF1 → carro na pista: interpolação sempre avançando no tempo (monotônica), alinhamento ao traçado, altura/inclinação pelo asfalto, rastro colorido por equipe, orientação pela tangente | carro indo e voltando, sumindo, dentro do chão; carros lado a lado |
| `kit/sfx` | banco único por categoria (impacto, riser, clique, tecla, sino, whoosh, pop, alerta), volume/duração por categoria, sync por palavra | SFX pouco variado; juntar o melhor dos dois testes |
| `kit/anotacao` | oval aberto/perninha, seta, sublinhado, chave, riscado, número corrigido; ancorado em caixa ESTÁVEL de peça; traço de fonte à mão | círculos tortos e pulando |
| `kit/graficos` | velocidade×distância com gap destacado, setores, delta acumulado, telemetria (freio/marcha), gráfico normalizado com disclaimer de fonte | gráficos elogiados, agora reutilizáveis |
| `kit/imagens` | busca de trechos/imagens reais (yt-dlp), **validação** de que batem com a afirmação (volta, piloto, sessão), crédito em FONTES | imagem da volta errada |
| `kit/foco` | blur de profundidade no que não é destaque | falta de foco ao destacar peça |

## 6. Motores: híbrido por cena + montador
O SPEC marca o motor de cada cena. Cenas editoriais (palavra gigante, cartões, números, gráficos) → Remotion (cache por cena,
já integrado). Cenas de pista/GPS e câmeras longas → HyperFrames (3D em tempo real, vídeo real, câmeras). O `montador` junta
os trechos a 60 fps com cortes secos, cortinas e mergulhos de cor; transições que misturam duas imagens exigem quadros de
sobreposição de cada lado. Um único relógio (60 fps, tempos por palavra) e uma única mixagem. Se o híbrido pesar demais,
cada cena do SPEC pode apontar para um só motor sem mudar o resto.

## 7. Painel (o que muda)
Etapas novas no card horizontal (`História`, `SPEC`, `Ativos`, `Verificação`, `Rascunho`) além das atuais. Telas: ver e aprovar
a história e o SPEC, pedir mudança por cena (como o `PainelAnimacao`), status de ativos (dados/imagens/GPS), folhas de
verificação por cena, rascunho para assistir e aprovar. O estado vive em arquivos do projeto (leitura por arquivo, não por memória do servidor).

## 8. Fases (critério de pronto em PLANO.md)
0 Esqueleto e docs · 1 Kit core (GPS, SFX, anotação, imagens) · 2 Kit gráficos + foco + cartões + transições ·
3 Diretor documental (história, SPEC, ativos, verificação) · 4 Painel · 5 Montador + primeiro vídeo completo (comparado aos testes) ·
6 Reorganização do vertical em `F1/vertical/`.

## 9. Riscos
Dois motores = mais manutenção e ponto de falha; interpolação do GPS (3,7 Hz) precisa de suavização cuidadosa; modelos 3D sem
interior limitam raio-X; cota semanal limita a velocidade das fases; o painel compartilhado deve mudar o mínimo.
