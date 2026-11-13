// Linha de comando do kit/graficos (Node 24 roda TypeScript direto):
//   node cli.ts checar <cena.json>        → relatório da verificação geométrica (graficos.checar)
//   node cli.ts estado <cena.json> <t>    → o que o motor desenharia no tempo t
//   node cli.ts montar <cena.json>        → elementos montados (geometria, séries, eixos), para a verificação em Python
// A cena aponta para os dados (`"dados": "comparacoes/<arquivo>.json"`, relativo a kit/graficos).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { checar, estado, montar, type Dados, type Larguras, type Spec } from "./graficos.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
export type Cena = { largura: number; altura: number; fps: number; duracao: number; tema?: "claro" | "escuro"; dados: string; graficos: Spec[] };
export function carregar(arq: string) {
  const cena = JSON.parse(readFileSync(arq, "utf-8")) as Cena;
  const dados = JSON.parse(readFileSync(join(aqui, cena.dados), "utf-8")) as Dados;
  const larg = JSON.parse(readFileSync(join(aqui, "fonte", "segoe_larguras.json"), "utf-8")) as Larguras;
  const specs = cena.graficos.map((g) => ({ tema: cena.tema, ...g }));
  return { cena, dados, m: montar(specs, dados, larg) };
}

const [cmd, arq, arg] = process.argv.slice(2);
if (cmd) {
  const { m } = carregar(arq);
  if (cmd === "checar") console.log(JSON.stringify(checar(m)));
  else if (cmd === "estado") console.log(JSON.stringify(estado(m, parseFloat(arg))));
  else if (cmd === "montar") console.log(JSON.stringify({ avisos: m.avisos, graficos: m.graficos.map((g) => ({ ...g, tema: g.tema.nome })) }));
  else { console.error("uso: node cli.ts checar|estado|montar <cena.json> [t]"); process.exit(2); }
}
