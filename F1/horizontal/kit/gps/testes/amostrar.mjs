// Amostra o kit/gps (o MESMO gps.js usado nos motores) quadro a quadro e grava as poses em JSON para o teste Python.
// Uso: node amostrar.mjs <volta.json> <fps> <fator> <saida.json> [tIni tFim]
import { readFileSync, writeFileSync } from "node:fs";
import { criarAmostrador, relogioComparacao } from "../src/gps.js";

const [arq, fpsS, fatorS, saida, a, b] = process.argv.slice(2);
const fps = Number(fpsS), fator = Number(fatorS);
const am = criarAmostrador(JSON.parse(readFileSync(arq, "utf-8")));
const relogio = relogioComparacao({ fator, inicio: a !== undefined ? Number(a) : 0 });
const tLimite = b !== undefined ? Number(b) : am.duracao;
const t0 = a !== undefined ? Number(a) : 0;
const nq = Math.floor(((tLimite - t0) / fator) * fps) + 1;
const out = { sigla: am.info.sigla, volta: am.info.volta, fps, fator, tIni: am.tIni, tFim: am.tFim, q: [] };
for (let k = 0; k < nq; k++) {
  const t = relogio(k / fps);
  const p = am.pose(t);
  out.q.push([+t.toFixed(5), p.s, p.x, p.y, p.z, p.yaw, p.pitch, p.roll, p.vel, p.comDados ? 1 : 0]);
}
// rastro: amostra alguns trechos para conferir que é contínuo e acompanha o carro
out.rastros = [];
for (const t of [5, 20, 40, 60]) {
  const r = am.rastro(t - 2.5, t);
  out.rastros.push({ t, n: r.pontos.length, fim: r.pontos[r.pontos.length - 1], pos: am.pos(t) });
}
writeFileSync(saida, JSON.stringify(out));
console.log(`${out.sigla} v${out.volta}: ${nq} quadros a ${fps} q/s (fator ${fator})`);
