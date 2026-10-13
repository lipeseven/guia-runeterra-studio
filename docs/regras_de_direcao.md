# Regras de direção

Regras que o diretor (Claude) segue ao transformar roteiro + tempos em cenas.
Complementa o [guia de estilo](guia_de_estilo.md). Este arquivo entra no prompt do diretor,
então cada ajuste fino do Felipe vira uma regra aqui.

## 1. Sentido antes da palavra

- Escolher imagens pelo **sentido da frase no contexto**, nunca pela palavra isolada.
- **Metáforas não são literais.** "Devorar nações inteiras" = destruir, arrasar, conquistar —
  ilustrar com destruição/guerra/ruína, **não** com algo comendo (ex.: Tahm Kench, que devora
  literalmente, é a escolha errada aqui).
- Na dúvida entre literal e figurado, ler a frase anterior e a seguinte para decidir.

## 2. Cada recurso tem a sua hora

Ter um recurso não é motivo para usá-lo. Cada tipo de cena tem um gatilho:

| Recurso | Quando usar | Quando NÃO usar |
|---|---|---|
| **Mosaico** | Enumeração rápida de itens do mesmo assunto ("os Deuses do Freljord: Volibear, Ornn e Anivia") — cada item entra quando é falado, de direções diferentes | Frases comuns; itens sem relação entre si; mais de um mosaico em sequência |
| **Clipe de animação** | Momentos de ação, revelação ou emoção em que existe tomada que mostra exatamente aquilo | Só para "encher"; tomada que não corresponde ao que está sendo dito |
| **Diálogo** | Fala atribuída a um personagem dirigida a outro | Narração comum |
| **Citação sobre arte** | Frase marcante citada de um personagem/conto, com autor | Frases do próprio narrador |
| **Cartão emoldurado** | Padrão para apresentar lugar, conceito, personagem, evento | — (é o "feijão com arroz") |
| **Tela cheia** | Momentos de impacto, atmosfera, transição entre seções | Sequências longas seguidas |
| **Meme / quebra** | Humor, ironia, alívio depois de trecho pesado | Momentos sérios ou trágicos |

Recursos "especiais" (mosaico, clipe, diálogo, citação) devem parecer escolhas, não rotina.

## 3. Áudio de clipes

- **Por padrão, todo clipe entra MUDO** (menos risco de reivindicação de direitos no YouTube
  e a narração não compete com nada).
- **Exceção rara**: um momento curto em que o som original acrescenta muito (grito, golpe,
  fala marcante) pode entrar **baixo, por baixo da narração**. Deve ser exceção, poucas vezes por vídeo.
- Efeitos sonoros: catálogo próprio (Fase 8) — tratados à parte.

## 4. Variedade

- Efeitos de entrada, movimentos e layouts vêm do editor de variedade
  (`tools/direcao/variacao.py`): sem repetição seguida, corte seco frequente.
- Ícones das seções e a abertura vêm da **capa feita pelo Felipe**.
