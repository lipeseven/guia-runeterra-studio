# Regras de direção — Explicando F1

Este arquivo entra no prompt do diretor. Todo ajuste fino do Felipe entra aqui.

## Ajustes do Felipe (GP do Brasil, 2026-11-04)
- **Cartões empilhados (`etapas`) cansam.** No máximo 1 por vídeo, e de preferência com `foco` (fundo escuro e desfocado).
  `foco` também é tempero: 1 ou 2 por vídeo. Para o resto, gráfico que interage com a cena: `linhatempo`, `minimapa`,
  `perfil`, `torre`, `relogio`, `ano`, `sentido`, ou a lista falada em cortes rápidos com `palavra`.
- **A abertura pode ser a própria pergunta escrita na tela** (`frase`, com `sem_legenda`), não precisa ser carro na pista.
- **O gráfico pertence à cena.** Falou de um trecho do circuito: o carro PASSA por ele, com o `minimapa` mostrando onde
  está. Falou de um vencedor: o carro na pintura dele, na vista panorâmica.
- **Vista de um circuito real usa `criarCircuito(nome, { cenario: true })`**, nunca a reta genérica (`set: "pista"`).
- **Carro parado fora do box parece acidente.** "Parada" é sempre no set `pit`, na marca, com a equipe em volta.
- **Plano só no carro, sem nada acontecendo, é fraco.** Toda cena mostra o que a fala diz.
- **Som:** nada de barulho de carro. Swoosh em troca forte de cena, pop quando algo aparece, alerta quando algo dá errado.
