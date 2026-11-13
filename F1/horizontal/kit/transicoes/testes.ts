// Teste automático do kit/transicoes (sem motor, ~1 s):  node F1/horizontal/kit/transicoes/testes.ts
//  - checarTransicoes() na cena de teste: duração EXATA em quadros (60 q/s), progresso mensurável, pico no quadro certo;
//  - duração por tipo: corte 0, fade 18, wipe 24, zoom 30; em 30 q/s as durações viram 9/12/15 (mesmo tempo);
//  - sequência: cada quadro desenha a cena certa (pura fora das transições, A e B dentro);
//  - SFX: pedidos → kit/sfx (Banco.dePedidos com o catálogo real): o PICO de cada som cai exatamente no quadro de pico
//    (inicio + pico_s = tPico) e a categoria é a do tipo (impacto no corte pedido, whoosh no wipe e no zoom).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Banco, type Catalogo } from "../sfx/sfx.ts";
import { checarTransicoes, estadoSequencia, montarTransicao, montarTransicoes, pedidosSfx, progresso, type Transicao } from "./transicoes.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
const cena = JSON.parse(readFileSync(join(aqui, "exemplo", "cena.json"), "utf-8")) as { fps: number; duracao: number; transicoes: Transicao[] };
const catalogo = JSON.parse(readFileSync(join(aqui, "..", "sfx", "catalogo.json"), "utf-8")) as Catalogo;
let ok = 0;
const falhas: string[] = [];
const conferir = (cond: boolean, msg: string) => { if (cond) ok++; else falhas.push(msg); };

const ts = montarTransicoes(cena.transicoes, cena.fps);
const rel = checarTransicoes(ts);
conferir(rel.falhas.length === 0, `checarTransicoes: ${rel.falhas.join("; ")}`);
conferir(JSON.stringify(rel.transicoes.map((t) => t.quadros)) === "[0,18,24,30]", `durações ${rel.transicoes.map((t) => t.quadros)}`);
conferir(rel.transicoes.every((t) => t.quadrosMedidos === t.quadros), "quadros medidos ≠ declarados");

// 30 q/s: mesmo tempo, metade dos quadros
for (const tipo of ["fade", "wipe", "zoom"] as const) {
  const a = montarTransicao({ tipo, em: 2 }, 60), b = montarTransicao({ tipo, em: 2 }, 30);
  conferir(b.n * 2 === a.n && checarTransicoes([b]).falhas.length === 0, `${tipo} a 30 q/s: ${b.n} quadros`);
}
// duração pedida (ímpar) respeitada
{
  const t = montarTransicao({ tipo: "fade", em: 1, quadros: 7 });
  conferir(t.n === 7 && checarTransicoes([t]).transicoes[0].quadrosMedidos === 7, "fade de 7 quadros");
}

// sequência
{
  const nq = Math.round(cena.duracao * cena.fps) + 1;
  for (let q = 0; q < nq; q++) {
    const s = estadoSequencia(ts, q);
    const ativa = ts.findIndex((tm) => tm.n > 0 && q >= tm.q0 && q < tm.q0 + tm.n);
    if (ativa >= 0) {
      conferir(s.itens.every((it) => it.cena === ativa || it.cena === ativa + 1) && s.itens.length >= 1, `q${q}: cenas ${s.itens.map((i) => i.cena)}`);
    } else {
      const esperada = ts.filter((tm) => progresso(tm, q) >= 1).length;
      conferir(s.itens.length === 1 && s.itens[0].cena === esperada && s.itens[0].estilo.opacity === "1.0000" && !s.itens[0].estilo.transform, `q${q}: pura ${s.itens.map((i) => i.cena)} (esperada ${esperada})`);
    }
  }
  conferir(estadoSequencia(ts, 59).itens[0].cena === 0 && estadoSequencia(ts, 60).itens[0].cena === 1, "corte não cai no quadro 60");
}

// SFX
{
  const peds = pedidosSfx(ts);
  conferir(JSON.stringify(peds.map((p) => p.categoria)) === '["impacto","whoosh","whoosh"]', `categorias ${peds.map((p) => p.categoria)}`);
  for (const sem of [0, 1, 2]) {
    const evs = new Banco(catalogo, sem).dePedidos(peds);
    evs.forEach((ev, i) => {
      const tm = ts.filter((x) => x.t.sfx)[i];
      const item = catalogo.itens.find((x) => x.id === ev.id)!;
      const pico = ev.inicio - ev.corte_ini + item.pico_s;
      conferir(Math.abs(ev.t - tm.tPico) < 1e-4 && Math.abs(pico - tm.tPico) < 1e-3, `semente ${sem}: ${ev.id} pico em ${pico} (quadro de pico ${tm.tPico})`);
      conferir(Math.abs(tm.tPico * 60 - Math.round(tm.tPico * 60)) < 1e-9, "tPico fora do quadro");
    });
  }
  // corte: o impacto bate no 1º quadro da cena nova
  conferir(ts[0].qPico === 60, `impacto do corte no quadro ${ts[0].qPico}`);
}

console.log(JSON.stringify({ ok, falhas: falhas.length, transicoes: rel.transicoes }));
if (falhas.length) { console.error("FALHAS:\n  " + falhas.join("\n  ")); process.exit(1); }
console.log(`OK: ${ok} checagens, 0 falhas`);
