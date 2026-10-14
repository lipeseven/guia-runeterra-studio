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
| **Transição de seção (hub)** | Início de cada seção a partir da 2ª, quando o personagem está na capa (o roteiro fala só o nome) | No meio de uma seção |
| **Nome sobre a arte** (tela cheia + rótulo) | Apresentar um personagem/lugar pela 1ª vez ("Raum / o demônio dos segredos") | Personagem já apresentado |
| **Meio a meio** | Ideia/conceito forte que cabe numa frase curta ao lado da arte | Frases comuns (aí é cartão) |
| **Só texto** | Conceito abstrato, virada, pausa dramática ("A Clareza", "Outra história") | Mais de 1–2 vezes por vídeo |
| **Tela dividida** | Par/trio, comparação, confronto ("Ashe e Tryndamere", "Darkin contra Ascendidos") | Itens sem relação |
| **Lista acumulada** | Enumeração de conceitos com rótulo (torturas, poderes, motivos) | Enumeração de personagens com arte forte (aí é mosaico) |
| **Modo escuro** (vídeo inteiro) | Temas sombrios/épicos, guerras, horror, versus | Vídeos explicativos leves, com humor (modo claro) |

Recursos "especiais" (mosaico, clipe, diálogo, citação, meio a meio, só texto, dividida, lista) devem parecer
escolhas, não rotina. Nada de copiar as marcas registradas da referência (emoji amarelo apontando, boneco-bolha,
Poro no final) — ver guia de estilo §10.4.

## 3. Áudio de clipes

- **Por padrão, todo clipe entra MUDO** (menos risco de reivindicação de direitos no YouTube
  e a narração não compete com nada).
- **Exceção rara**: um momento curto em que o som original acrescenta muito (grito, golpe,
  fala marcante) pode entrar **baixo, por baixo da narração**. Deve ser exceção, poucas vezes por vídeo.
- **Efeitos sonoros** (catálogo `tools/audio/sfx.py`): o padrão do canal é voz pura; efeito é tempero raro,
  só em momento marcante (revelação, golpe, magia, criatura, morte, explosão, presságio). A montagem garante:
  no máximo 1 a cada 30 s em média, mínimo de 18 s entre dois, sem repetir o mesmo arquivo, volume ~15 dB
  abaixo da voz. Nada de whoosh em corte; metáfora não vira som literal.

## 4. Variedade

- Efeitos de entrada, movimentos e layouts vêm do editor de variedade
  (`tools/direcao/variacao.py`): sem repetição seguida, corte seco frequente.
- Ícones das seções e a abertura vêm da **capa feita pelo Felipe**.
