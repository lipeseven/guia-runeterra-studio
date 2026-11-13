// Linha de comando do kit (Node 24 roda TypeScript direto):
//   node cli.ts checar <cena.json>            → relatório JSON da verificação (anotacao.checar)
//   node cli.ts estado <cena.json> <t>        → o que o motor desenharia no tempo t
//   node cli.ts montar <cena.json>            → itens montados (caixas, tempos) sem os pontos
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { checar, estado, montar, type Cena, type Fonte } from "./anotacao.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
const fonte = JSON.parse(readFileSync(join(aqui, "fonte", "caveat_traco.json"), "utf-8")) as Fonte;
const [cmd, arq, arg] = process.argv.slice(2);
const cena = JSON.parse(readFileSync(arq, "utf-8")) as Cena;
const m = montar(cena, fonte);
if (cmd === "checar") {
  console.log(JSON.stringify(checar(m)));
} else if (cmd === "estado") {
  console.log(JSON.stringify(estado(m, parseFloat(arg))));
} else if (cmd === "montar") {
  console.log(JSON.stringify({
    avisos: m.avisos,
    itens: m.itens.map((it) => ({
      id: it.a.id, tipo: it.a.tipo, ancora: it.ancora, inicio: it.a.em, fim: it.fim, dinamica: it.dinamica,
      caixaOval: it.caixaOval, elipse: it.elipse, caixaTexto: it.caixaTexto, caixaForma: it.caixaForma, faltando: it.faltando,
      tracos: it.tracos.map((t) => ({ comp: t.comp, t0: t.t0, t1: t.t1, largura: t.largura, pts: t.pts })),
      glifos: it.glifos.length,
    })),
  }));
} else {
  console.error("uso: node cli.ts checar|estado|montar <cena.json> [t]");
  process.exit(2);
}
