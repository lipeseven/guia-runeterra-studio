# Orquestrador automático (pedidos pesados do F1 vertical)

O Studio acorda sozinho um Claude Code (`claude -p`, plano Pro) quando surge um **pedido pesado** — aquele que o diretor
devolveu "sem capacidade" ou que o Felipe mandou para o orquestrador — e ele atende o pedido do começo ao fim. Este
arquivo é a instrução que esse agente lê. Leia também o `CLAUDE.md` e `F1/vertical/docs/api_cenas.md`.

## Procedimento (um pedido por vez)

1. Veja o pedido: `.venv/Scripts/python.exe tools/direcao/pedidos_pesados.py mostrar <id>`
   (card, cena, fala, texto do Felipe, motivo do diretor, código atual da cena, quadro de conferência).
2. Ache a **causa**. Se o defeito é geral (biblioteca: `F1/comum/remotion/modelos/*`, `F1/vertical/video/src/*`), conserte
   NA BIBLIOTECA (vale para todos os vídeos e cenas). Se é só desta cena, edite o `codigo` do plano em
   `<projeto>/direcao/vertical.json` (faça uma cópia com Write em `<projeto>/direcao/vertical_versoes/` antes; mude só o plano pedido).
3. **Confira olhando a imagem**: `.venv/Scripts/python.exe tools/direcao/quadro_da_cena.py <id_do_plano> --frac 0.6 --escala 0.5`
   imprime o caminho de um .jpg; abra com a ferramenta Read e olhe. Use `--codigo arquivo.js` para testar um código de cena
   sem gravar. Texto que entra palavra por palavra: `--frac 0.93`. Repita até o defeito sumir e nada mais quebrar.
4. Se mexeu em TypeScript: `npx tsc --noEmit -p F1/vertical/video` (sem erro).
5. Feche o pedido: `.venv/Scripts/python.exe tools/direcao/pedidos_pesados.py resolver <id> --nota "causa e o que mudou" --renderizar`
   (`--renderizar` só no ÚLTIMO pedido aberto do card; o painel então renderiza de novo sozinho).

## Regras

- **`GRS_CANAL` já está definido no ambiente** do seu processo: rode os comandos exatamente como estão acima, SEM prefixo
  `GRS_CANAL=...` e sem `$env:` (o Bash bloqueia comando que mexe em variável de ambiente).
- Comandos de Bash: só `.venv/Scripts/python.exe ...`, `node ...` e `npx tsc ...` (sem `cd`, sem pipes, sem `&&`). Para ler arquivos
  use Read/Grep/Glob; para editar, Edit/Write.

- Só o pedido recebido: não mexa em outras cenas, nem "melhore" o que não foi pedido.
- Nada de `git commit`/`push`. Não apague arquivos do projeto nem do acervo. Não toque em outro canal (Runeterra).
- Pedido do Felipe vale mais que regras ou limites pré-setados; se o pedido contradiz um padrão, faça e anote.
- Seja curto na nota: causa + o que mudou + "conferido no quadro".
- Se não conseguir resolver depois de tentar de verdade: NÃO chame `resolver`. Escreva o motivo em
  `<projeto>\orquestrador\auto_<id>_nao_resolvido.txt` e termine. O pedido continua aberto para o chat do Felipe.
