// Teste automático do kit/foco (sem motor, ~1 s):  node F1/horizontal/kit/foco/testes.ts
// Na cena de teste (exemplo/cena.json), quadro a quadro a 60 q/s:
//  - checarFoco(): entrada/saída suaves, janela = caixa + folga, máscara 0 em toda a caixa, 1 depois da pena;
//  - a máscara SVG (o que o motor recebe) bate com alfaEm(): mesmos anéis, contorno interno = janela;
//  - peça que anda: a janela acompanha a âncora (mesma trilha do carro), sem mudar de tamanho;
//  - intervalo curto: entrada e saída encolhem e nunca passam do intervalo;
//  - forma elipse cobre os 4 cantos da caixa.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { alfaEm, ANEIS, caixaEm, checarFoco, estadoFoco, estilos, forca, janelaEm, montarFoco, type CenaFoco, type P } from "./foco.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
const cena = JSON.parse(readFileSync(join(aqui, "exemplo", "cena.json"), "utf-8")) as CenaFoco;
let ok = 0;
const falhas: string[] = [];
const conferir = (cond: boolean, msg: string) => { if (cond) ok++; else falhas.push(msg); };

const m = montarFoco(cena);
const rel = checarFoco(m);
conferir(rel.falhas.length === 0, `checarFoco: ${rel.falhas.join("; ")}`);
for (const [id, r] of Object.entries(rel.focos)) {
  conferir(r.kMax === 1, `${id}: não chega a k=1`);
  conferir(r.pontosDentro > 1000 && r.pontosFora > 100, `${id}: poucos pontos conferidos`);
}

// máscara SVG × alfaEm: o contorno interno do último anel é exatamente a janela; níveis crescentes; nada dentro
for (const t of [1.5, 2.4, 4.6]) {
  const est = estadoFoco(m, t);
  conferir(est.length === 1, `t=${t}: ${est.length} focos ativos`);
  const e = est[0];
  const f = m.focos.find((x) => x.id === e.id)!;
  const paths = [...e.mascara.matchAll(/<path[^>]*>/g)].map((x) => x[0]);
  conferir(paths.length === ANEIS + 1, `t=${t}: ${paths.length} caminhos na máscara`);
  const niveis = paths.slice(1).map((p) => parseFloat(/fill-opacity="([\d.]+)"/.exec(p)![1]));
  conferir(niveis.every((v, i) => i === 0 || v >= niveis[i - 1]) && niveis[ANEIS - 1] === 1, `t=${t}: níveis dos anéis ${niveis}`);
  // o anel 1 termina na janela: o segundo contorno do 1º anel começa em (janela.x + raio, janela.y) para caixa
  if (f.forma === "caixa") {
    const d1 = /d="([^"]+)"/.exec(paths[1])![1];
    const sub = d1.split("Z")[1];
    const m0 = /^M([-\d.]+) ([-\d.]+)/.exec(sub)!;
    const j = e.janela;
    conferir(Math.abs(+m0[1] - (j.x + f.raio)) < 0.01 && Math.abs(+m0[2] - j.y) < 0.01, `t=${t}: contorno interno ≠ janela (${m0[1]},${m0[2]} × ${j.x + f.raio},${j.y})`);
  }
  // amostras: dentro da caixa = 0; exatamente na janela = 0; 1 px fora = 1º anel (> 0)
  const c = e.caixa, j = e.janela;
  conferir(alfaEm(f, j, [c.x + c.w / 2, c.y + c.h / 2]) === 0 && alfaEm(f, j, [c.x, c.y]) === 0, `t=${t}: centro/canto da caixa com desfoque`);
  if (f.forma === "caixa") {
    conferir(alfaEm(f, j, [j.x + j.w / 2, j.y - 1]) > 0 && alfaEm(f, j, [j.x + j.w / 2, j.y - f.pena - 1]) === 1, `t=${t}: pena fora do lugar`);
  }
  const s = estilos(e);
  conferir(s.camada.backdropFilter.startsWith("blur(") && s.camada.maskImage.startsWith('url("data:image/svg+xml'), `t=${t}: estilo sem blur/máscara`);
}

// janela acompanha a âncora e não muda de tamanho
{
  const f = m.focos[0];
  const ws = new Set<string>();
  for (let q = 40; q < 190; q++) {
    const j = janelaEm(f, q / 60);
    ws.add(`${j.w.toFixed(6)}x${j.h.toFixed(6)}`);
  }
  conferir(ws.size === 1, `tamanho da janela variou: ${[...ws].slice(0, 3)}`);
  const c0 = caixaEm(f.alvo, 0), c4 = caixaEm(f.alvo, 4);
  conferir(Math.abs(c4.x - c0.x + 62) < 1e-9 && Math.abs(c4.y - c0.y + 10) < 1e-9, `âncora: ${c4.x - c0.x}, ${c4.y - c0.y}`);
}

// intervalo curto (0,5 s < entrada + saída padrão 0,8 s)
{
  const mc = montarFoco({ ...cena, focos: [{ id: "curto", em: 1, ate: 1.5, alvo: { caixa: { x: 100, y: 100, w: 50, h: 50 } } }] });
  const f = mc.focos[0];
  conferir(Math.abs(f.entrada + f.saida - 0.5) < 1e-9, `curto: entrada+saida = ${f.entrada + f.saida}`);
  conferir(forca(f, 1) === 0 && forca(f, 1.5) === 0 && forca(f, 1 + f.entrada) > 0.999, `curto: força ${forca(f, 1 + f.entrada)}`);
  conferir(checarFoco(mc).falhas.length === 0, `curto: ${checarFoco(mc).falhas}`);
}

// elipse cobre os cantos da caixa + folga
{
  const f = m.focos[1];
  const j = janelaEm(f, 4.5);
  const cantos: P[] = [[j.x, j.y], [j.x + j.w, j.y], [j.x, j.y + j.h], [j.x + j.w, j.y + j.h]];
  conferir(cantos.every((p) => alfaEm(f, j, p) === 0), "elipse não cobre os cantos");
}

console.log(JSON.stringify({ ok, falhas: falhas.length, quadros: rel.quadros, focos: rel.focos }, null, 0));
if (falhas.length) { console.error("FALHAS:\n  " + falhas.join("\n  ")); process.exit(1); }
console.log(`OK: ${ok} checagens, 0 falhas`);
