// Calcula os eventos do exemplo de 20 s com a API TS (sfx.ts) e imprime JSON (usado no teste de paridade com o Python).
//   node F1/horizontal/kit/sfx/exemplo/eventos.ts [semente]
//   node F1/horizontal/kit/sfx/exemplo/eventos.ts <semente> <pedidos.json>   → {"eventos": [...], "creditos": [...]}
//   (a 2ª forma usa pedidos com "t" em segundos; o teste cobre todas as categorias e os créditos CC BY)
import { readFileSync } from "node:fs";
import { Banco } from "../sfx.ts";

const aqui = new URL(".", import.meta.url);
const ler = (rel: string) => JSON.parse(readFileSync(new URL(rel, aqui), "utf-8"));
const b = new Banco(ler("../catalogo.json"), Number(process.argv[2] ?? 0));
if (process.argv[3]) {
  const evs = b.dePedidos(JSON.parse(readFileSync(process.argv[3], "utf-8")));
  console.log(JSON.stringify({ eventos: evs, creditos: b.creditos(evs) }));
} else {
  console.log(JSON.stringify(b.dePedidos(ler("pedidos.json"), ler("palavras.json"))));
}
