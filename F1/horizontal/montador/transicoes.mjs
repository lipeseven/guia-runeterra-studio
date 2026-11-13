// Estados das transições do kit/transicoes para o montador (Python): node transicoes.mjs <pedido.json>
// Pedido: { fps, largura, altura, transicoes: [{ tipo, em, quadros?, direcao?, cor?, sfx?, intensidade? }] }
// Saída (stdout, JSON): por transição, { n, q0, qCorte, qPico, tPico, sfx, intensidade, quadros: [{ q, a, b, barra }] }
// a/b = camada { opacidade, escala, tx, ty, blur, recorte } ou null (o mesmo estadoTransicao que os motores aplicam em CSS).
import { readFileSync } from "node:fs";
import { estadoTransicao, montarTransicao } from "../kit/transicoes/transicoes.ts";

const p = JSON.parse(readFileSync(process.argv[2], "utf-8").replace(/^﻿/, ""));
const fps = p.fps ?? 60;
const saida = p.transicoes.map((t) => {
  const tm = montarTransicao(t, fps);
  const quadros = [];
  for (let q = tm.q0; q < tm.q0 + tm.n; q++) quadros.push({ q, ...estadoTransicao(tm, q, p.largura, p.altura) });
  return { tipo: tm.t.tipo, n: tm.n, q0: tm.q0, qCorte: tm.qCorte, qPico: tm.qPico, tPico: tm.tPico, sfx: tm.t.sfx,
           intensidade: tm.t.intensidade, variacao: tm.t.variacao ?? null, quadros };
});
process.stdout.write(JSON.stringify(saida));
