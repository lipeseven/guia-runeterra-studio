# Folha de estilo do horizontal — Explicando F1 (v1, 2026-11-06)

Padrão dos vídeos longos (16:9, 10–16 min). Base: o estudo de 10 referências em
`F1/dados/estilo/referencias_horizontais/analise_horizontal.md`. A linguagem vem principalmente da Formula Addict:
3D, palavras-chave e anotações. Da Documentsui entram o cartão de capítulo com o traçado, a palavra solta em tela
escura e o cartão de pontos.

Código: `F1/video/src/horizontal/`, composição `Horizontal` (plano em JSON). A demonstração é `DEMO_HORIZONTAL`, de
~50 s, com todos os recursos. Esta folha vale só para o horizontal do F1. Não valem aqui as regras do Runeterra nem as
do vertical.

## 1. Decisões
- Mescla da Formula Addict com a Documentsui, com regras próprias (Felipe, 2026-11-05).
- Carros sempre oficiais e o mais atuais possível: `.glb` em `F1/dados/modelos3d/`.
  - O leitor `horizontal/carro.ts` ajusta escala e orientação e separa as rodas.
- **Exceção ao "texto sem animação":** no horizontal do F1 a palavra-chave entra por decodificação, como assinatura.
  - Legenda e microlegenda continuam secas.
- Pessoas: foto livre (Wikimedia ou licença aberta) em P&B; sem foto, silhueta. Nunca rosto em 3D.
  - Nunca inventar citação de pessoa real. A citação só existe se a pessoa disse aquilo (fonte no briefing).
- Identidade própria:
  - O capítulo é "PARTE 0N" com o traçado do circuito, não "CHAPTER N".
  - Sem janelas ".EXE".
  - A cor de destaque vem da equipe ou do tema do vídeo.

## 2. Cenas (tipos do plano)
| tipo | o que é | quando |
|---|---|---|
| `estudio` | carro 3D com a palavra gigante ATRÁS dele e anotações por cima | análise, pessoas, opinião (cena-base, 25–35 vezes por vídeo) |
| `estudio` modo `cheio` | fundo na cor de destaque, palavra branca | virada de argumento |
| `estudio` modo `tecnico` | fundo escuro com grade e grão; carro em planta (arestas na cor) | dados e mecânica |
| `estudio` modo `escuro` | fundo escuro, carro herói | respiro dramático, fechamento |
| `pista` | Interlagos real (.glb), carros apoiados no asfalto | respiro (35–40% do tempo): helicóptero, drone, lado, passagem com rastro, POV |
| `pessoa` | cartão de papel inclinado, nome em marca-texto, citação palavra a palavra | 1ª menção de uma pessoa |
| `capitulo` | "PARTE 0N" + título + traçado se desenhando | antes da fala da seção, 3–5 s, sobre pausa da narração |
| `solta` | uma palavra decodificando em tela escura (ou cor cheia) | momento dramático, 2–3 s |

Câmeras do estúdio: `orbita`, `aproximar`, `deslizar`, `chegada`, `frente`, `traseira`, `passagem`. O carro nunca fica
parado.
Câmeras da pista: `helicoptero`, `drone`, `lado`, `passagem` (câmera parada, rastro de 8 amostras), `pov` (olho do
piloto, borrão leve).

Sobreposições em `estudio` e `pista`:
- `palavra`: texto, em, ate, tam, topo.
- `anotacoes`: seta, círculo, sublinhado, riscado, chave, nota à mão e número corrigido.
- `contador`: sobe até o valor.
- `rotulos`: linha-guia com ponto quadrado.

## 3. Medidas (das referências, convertidas para 30 fps)
- **Palavra gigante:** 1–3 palavras-chave da frase, nunca a frase inteira.
  - Tamanho: 25–60% da altura (440 px por padrão), condensada ultra-bold, caixa-alta.
  - Entra 0–1 s depois da palavra falada.
  - Decodificação: 0,52 letra por quadro, em ordem aleatória, com 2–4 letras-isca. Sai ao contrário em ~12 quadros.
- **Anotação à mão:** comenta a fala, sem repeti-la ("Por quê?", "Não!", "Dominou").
  - Traço a ~105 px por quadro; a letra à mão vai na metade disso.
  - Cor: preta, ou na cor de destaque.
- **Ritmo:**
  - Alterna planos contínuos de 6–16 s com rajadas de cortes de 0,1–0,3 s.
  - Nos blocos de análise entra algo novo a cada 2–3 s.
  - Ciclo: gancho → bloco denso de 30–60 s → respiro de 7–40 s → bloco denso…
- **Transições** (`linha.tsx`), mistura alvo a cada 16 momentos: 3–4 cortes, 3–4 empurrões, 3–4 câmeras contínuas,
  2–3 entradas de texto, 1 cor e 0–1 glitch ou cortina.
  - `corte`: 0 quadros. A cena nova já começa com a câmera em movimento.
  - `empurrar`: a antiga sai em 10 quadros (ease-in), com borrão na direção e esticada 1,2×. A nova entra 9 quadros
    depois, em 15 quadros (ease-out), sem rebote. O fundo não se mexe. Esquerda ou direita em 70% dos casos.
  - `glitch`: 5 quadros, só horizontal, sem cor. Raro.
  - `cortina`: sempre de baixo para cima, 15 quadros.
  - `cor`: mergulho em cor lisa (8 + 6 + 8 quadros), para capítulo ou virada.
- **Contadores e tabelas:** ficam 5–7 s na tela.
- **Trilha:** contínua, 16–26 dB abaixo da voz. Pausa de 3–11 s na narração antes de cada capítulo.
- **Abertura e fim:** abre direto no gancho, sem logo. Fecha com 15–20 s de 3D em movimento e espaço livre para o vídeo
  sugerido da tela final.

## 4. Fatos e números
- Só números que a fala diz.
- Dado de exemplo leva "(EXEMPLO)" e nunca vai para vídeo publicado.
- Fontes no briefing, conferidas antes da voz, com a mesma regra do vertical.

## 5. O que ainda falta (próximos passos)
1. ~~Diretor do horizontal~~ ✅ (2026-11-06): `tools/direcao/horizontal.py` + `api_horizontal.md`; card horizontal novo usa o fluxo animado (sua gravação → direção → render). Falta: rodada de conferência pelas imagens (como no vertical).
2. Efeitos sonoros ligados às transições: whoosh no empurrar, pop na palavra.
3. Acabamento de render: oclusão de ambiente, profundidade de campo e reflexos. O Blender fica para depois, para os
   respiros.
4. Modelos: carros de 2026 das outras equipes, cockpit (para o POV mostrar o halo), box e objetos de metáfora.
5. Cartão de pontos do campeonato (Documentsui).
