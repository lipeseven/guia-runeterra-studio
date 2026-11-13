// Teste automático do kit/cartoes (sem motor, ~1 s):  node F1/horizontal/kit/cartoes/testes.ts
//  - checarCartoes() na cena de teste: nada sai do quadro/margem, texto dentro do cartão, perninha da tag ligada, lado fixo;
//  - tag presa ao carro que chega perto da borda direita: o kit escolhe um lado que cabe o tempo todo (não "ne");
//  - tag impossível (carro cruza o quadro inteiro): caixa empurrada para dentro, nunca fora do quadro;
//  - título longo quebra em 2 linhas equilibradas e cabe na área útil; acentos PT-BR têm largura;
//  - entrada/saída: opacidade 0 fora do intervalo, sem salto > 0,2 por quadro.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { checarCartoes, estadoCartoes, larguraTexto, montarCartoes, type CenaCartoes, type TagM, type CapituloM } from "./cartoes.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
const cena = JSON.parse(readFileSync(join(aqui, "exemplo", "cena.json"), "utf-8")) as CenaCartoes;
let ok = 0;
const falhas: string[] = [];
const conferir = (cond: boolean, msg: string) => { if (cond) ok++; else falhas.push(msg); };

const m = montarCartoes(cena);
const rel = checarCartoes(m);
conferir(rel.falhas.length === 0, `checarCartoes: ${rel.falhas.join("; ")}`);
conferir(rel.avisos.length === 0, `avisos: ${rel.avisos.join("; ")}`);
for (const id of ["curva8", "leclerc", "pessoa", "parte2"]) conferir((rel.porCartao[id]?.quadros ?? 0) > 100, `${id}: poucos quadros`);
const lec = m.itens.find((i) => i.tipo === "tag" && (i.m as TagM).c.id === "leclerc")!.m as TagM;
conferir(lec.lado !== "ne" && !lec.empurrada, `leclerc: lado ${lec.lado}, empurrada ${lec.empurrada}`);

// tag impossível: ponto no canto superior direito, etiqueta comprida
{
  const c2: CenaCartoes = { ...cena, cartoes: [{ tipo: "tag", id: "canto", em: 0, ate: 1, texto: "Uma etiqueta comprida demais para o canto", ancora: [{ t: 0, x: 60, y: 540 }, { t: 1, x: 1860, y: 540 }] }] };
  const m2 = montarCartoes(c2);
  const r2 = checarCartoes(m2);
  conferir((m2.itens[0].m as TagM).empurrada && r2.avisos.length === 1, "canto: deveria ser empurrada com aviso");
  conferir(r2.falhas.every((f) => !f.includes("sai do quadro") && !f.includes("margem")), `canto: ${r2.falhas}`);
}

// título longo
{
  const titulo = "Por que a Ferrari perdeu três décimos nas curvas lentas de Interlagos";
  const c3: CenaCartoes = { ...cena, cartoes: [{ tipo: "capitulo", id: "longo", em: 0, ate: 2, numero: 3, titulo }] };
  const m3 = montarCartoes(c3);
  const cap = m3.itens[0].m as CapituloM;
  conferir(cap.textos.length === 3, `título longo: ${cap.textos.length - 1} linhas`);
  conferir(cap.textos.every((t) => t.x >= 160 - 1e-6 && t.x + t.w <= 1760 + 1e-6), "título longo sai da área útil");
  const [a, b] = [cap.textos[1].w, cap.textos[2].w];
  conferir(Math.min(a, b) / Math.max(a, b) > 0.6, `linhas desequilibradas ${a.toFixed(0)} × ${b.toFixed(0)}`);
  conferir(checarCartoes(m3).falhas.length === 0, `título longo: ${checarCartoes(m3).falhas}`);
}

// acentos e larguras
conferir(larguraTexto("ÁÉÍÓÚÃÕÇ", 100, "forte") > 0 && larguraTexto("MMM", 100, "forte") < larguraTexto("MMM", 100, "normal"), "larguras: condensada deveria ser mais estreita");

// opacidade
{
  let ant: Record<string, number> = {};
  let salto = 0;
  for (let q = 0; q <= cena.duracao * cena.fps; q++) {
    const t = q / cena.fps;
    const est = Object.fromEntries(estadoCartoes(m, t).map((e) => [e.id, e.opacidade]));
    for (const c of cena.cartoes) {
      const o = est[c.id] ?? 0;
      if (t < c.em || t > c.ate) conferir(o === 0, `${c.id}: visível fora do intervalo (q${q})`);
      salto = Math.max(salto, Math.abs(o - (ant[c.id] ?? 0)));
    }
    ant = est;
  }
  conferir(salto <= 0.2, `salto de opacidade ${salto.toFixed(3)} por quadro`);
}

console.log(JSON.stringify({ ok, falhas: falhas.length, quadros: rel.quadros, porCartao: rel.porCartao, ladoLeclerc: lec.lado }));
if (falhas.length) { console.error("FALHAS:\n  " + falhas.join("\n  ")); process.exit(1); }
console.log(`OK: ${ok} checagens, 0 falhas`);
