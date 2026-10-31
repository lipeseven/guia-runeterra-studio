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
| **Só texto** | Conceito abstrato, virada, pausa dramática ("A Clareza", "Outra história"); fundo branco por padrão, preto só em ocasião especial | Mais de 1–2 vezes por vídeo |
| **Tela dividida** | Par/trio, comparação, confronto ("Ashe e Tryndamere", "Darkin contra Ascendidos") | Itens sem relação |
| **Lista acumulada** | Enumeração de conceitos com rótulo (torturas, poderes, motivos) | Enumeração de personagens com arte forte (aí é mosaico) |

**Fundo branco é a assinatura do canal** (Felipe): cartões, recortes, listas, meio a meio e diálogos são sempre
no branco. O escuro só aparece nas cenas de tela cheia (arte, clipe, citação, tela dividida) e no "só texto" em
ocasião especial. Não existe vídeo "todo escuro". Quando uma imagem entra **depois** da outra na mesma cena (tela
dividida, itens que chegam com a narração), o espaço ainda vazio fica **branco**, nunca preto (Felipe, 2026-10-17).

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

## 5. Aprendizados do 1º vídeo (retrospectiva de ~300 ajustes do Felipe, 2026-10-19)

Medido no storyboard de "A História de Runeterra" (352 cenas): o que o Felipe mais corrigiu à mão.

- **Texto entra JUNTO com a imagem.** Em 82 de 91 vezes que ele mexeu no momento do texto, foi para "junto com a
  imagem" (e vários pedidos ao diretor eram só isso). Padrão: legenda/rótulo aparecem no corte. Use
  `legenda_na_palavra` só quando o texto é uma PIADA ou REVELAÇÃO que precisa esperar a palavra (raro).
  (Nos vídeos novos a montagem já faz assim; o Felipe escolhe outra palavra no storyboard se quiser.)
- **Mais tela cheia, menos cartão.** As trocas mais comuns: cartão → tela cheia (14), texto → cartão (7),
  meio a meio → cartão (6), clipe → tela cheia (5). Arte boa (splash, cinemática, paisagem) merece tela cheia;
  "texto" só quando não existe imagem que sirva; "meio" só para frase forte de verdade.
- **Clipe só com tomada forte.** Clipe que não mostra exatamente a ação vira tela cheia. Tomada escura ou de
  transição não serve.
- **Legenda específica, com o nome próprio da lore.** Ele trocou textos genéricos por nomes: "a língua dos mortos"
  → "Ochnun - língua dos mortos", "um reino feito de almas" → "… chamado Mitna Rachnun", "Disco destruído" →
  "Disco Solar destruído", "guarda essa arma" → "Chalikar". Se a frase fala de algo com nome na lore, o nome vai
  na legenda.
- **Humor do canal = gíria gamer/internet BR curta**: "vapo", "SUPERA!", "lá ele", "o maior flip da história",
  "nossa guys, bad call". Nada de explicação dentro da piada.
- **Listas que a narração enumera viram texto na tela.** Quando o roteiro apresenta nomes um a um (as três
  irmãs, Força/Visão/Astúcia), cada nome aparece escrito (setas ou legendas), e o padrão vale para TODOS os itens
  da enumeração (ele cobrou o "Sem-Face" que ficou sem texto).
- **Imagem pedida pelo nome do arquivo é lei** (`busca.arquivo`): ele usa muito ("use a imagem floresta1.jpg").

## Aprendizados aprovados pelo Felipe (retrospectivas automáticas)
- Legendas enxutas: cortar o ponto final e os artigos ou adjetivos de enchimento, deixando só o termo-chave ("Runas Globais", "três bruxas", "Ele não fez"). _(vídeo: A História de Runeterra Explicada em X Minutos)_
- Tela cheia nunca fica sem legenda quando a narração cita um nome próprio, uma entidade ou um conceito novo da lore. Pôr um rótulo curto com esse termo, não deixar a cena "(sem texto)". _(vídeo: A História de Runeterra Explicada em X Minutos)_
- Se a arte usada for fanart, não oficial ou apenas representação aproximada de um personagem, avisar na legenda, por exemplo '(arte não oficial)'. Dar preferência a arte oficial quando existir. _(vídeo: Os Darkins de League of Legends Explicados em X Minutos)_
- Cada piada de quebra aparece uma única vez no vídeo, sem repetir bordão nem frase pronta. Se o cartão de humor não tiver uma piada nova e específica para aquele trecho, usar um cartão informativo comum. _(vídeo: Os Darkins de League of Legends Explicados em X Minutos)_
- Quando a lore fala de um Aspecto ou Darkin (Aspecto do Crepúsculo, Myisha, Aatrox etc.), não usar nem citar o campeão jogável de nome parecido (ex.: Zoe) nem um hospedeiro no lugar do Aspecto. A legenda e a imagem devem usar o nome do Aspecto ou Darkin que a narração cita. _(vídeo: Os Darkins de League of Legends Explicados em X Minutos)_
