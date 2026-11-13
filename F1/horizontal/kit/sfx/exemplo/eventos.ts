// Calcula os eventos do exemplo de 20 s com a API TS (sfx.ts) e imprime JSON (usado no teste de paridade com o Python).
//   node F1/horizontal/kit/sfx/exemplo/eventos.ts [semente]
import { readFileSync } from "node:fs";
import { Banco } from "../sfx.ts";

const aqui = new URL(".", import.meta.url);
const ler = (rel: string) => JSON.parse(readFileSync(new URL(rel, aqui), "utf-8"));
const b = new Banco(ler("../catalogo.json"), Number(process.argv[2] ?? 0));
console.log(JSON.stringify(b.dePedidos(ler("pedidos.json"), ler("palavras.json"))));
