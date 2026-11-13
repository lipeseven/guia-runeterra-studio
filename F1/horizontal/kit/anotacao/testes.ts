// Teste automático do kit (sem motor, ~1 s):  node F1/horizontal/kit/anotacao/testes.ts
// Confere na cena de teste (exemplo/cena.json), quadro a quadro a 60 q/s:
//  - checar(): oval com tamanho e margem constantes, desenho progressivo monotônico e completo, nada cruzando texto;
//  - o oval nunca encosta na peça REAL (retângulo girando ±12°), em nenhum quadro;
//  - a caixa estável da cena = caixaEnvelope() do giro; e quanto a caixa projetada (método antigo) variaria;
//  - traço irregular determinístico: mesma semente = mesmo caminho; outra semente = outro; desvio da elipse 0,3–4%;
//  - texto à mão: acentos do PT-BR e sinais (% ° ± × /) têm traço; nota "auto" não cruza texto;
//  - riscado encurta para não chegar ao texto vizinho.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { caixaEnvelope, checar, estado, formaOval, montar, montarTexto, ancoraEm, type Cena, type Fonte, type P } from "./anotacao.ts";

const aqui = dirname(fileURLToPath(import.meta.url));
const fonte = JSON.parse(readFileSync(join(aqui, "fonte", "caveat_traco.json"), "utf-8")) as Fonte;
const cena = JSON.parse(readFileSync(join(aqui, "exemplo", "cena.json"), "utf-8")) as Cena & { alvos: Record<string, { peca?: { w: number; h: number; giroAmp: number; giroPeriodo: number; cx: number; cy: number } }> };
let ok = 0;
const falhas: string[] = [];
const conferir = (cond: boolean, msg: string) => { if (cond) ok++; else falhas.push(msg); };

// 1. checagem geral
const m = montar(cena, fonte);
const rel = checar(m);
conferir(rel.falhas.length === 0, `checar(): ${rel.falhas.join("; ")}`);
conferir(rel.avisos.length === 0, `avisos: ${rel.avisos.join("; ")}`);
const ov = rel.ovais["oval-asa"];
conferir(!!ov && ov.variacaoTamanho < 1e-6 && ov.variacaoMargem < 1e-6, `oval variou: ${JSON.stringify(ov && [ov.variacaoTamanho, ov.variacaoMargem])}`);

// 2. oval × peça real girando (polígono do retângulo) em todos os quadros
const asa = cena.alvos.asa, pc = (asa as { peca?: { w: number; h: number; giroAmp: number; giroPeriodo: number; cx: number; cy: number } }).peca!;
const itOval = m.itens.find((i) => i.a.id === "oval-asa")!;
const ptsOval = itOval.tracos[0].pts;
const nq = Math.round(cena.duracao * cena.fps);
const amostras: { centro: P; pontos: P[] }[] = [];
const projW: number[] = [], projH: number[] = [];
let folgaMin = Infinity;
for (let q = 0; q <= nq; q++) {
  const t = q / cena.fps;
  const an = ancoraEm(asa, t);
  const g = (pc.giroAmp * Math.PI / 180) * Math.sin((2 * Math.PI * t) / pc.giroPeriodo);
  const c: P = [pc.cx + an.dx, pc.cy + an.dy];
  const cantos: P[] = [[1, 1], [1, -1], [-1, -1], [-1, 1]].map(([sx, sy]) => {
    const x = (sx * pc.w) / 2, y = (sy * pc.h) / 2;
    return [c[0] + x * Math.cos(g) - y * Math.sin(g), c[1] + x * Math.sin(g) + y * Math.cos(g)];
  });
  amostras.push({ centro: c, pontos: cantos });
  const xs = cantos.map((p) => p[0]), ys = cantos.map((p) => p[1]);
  projW.push(Math.max(...xs) - Math.min(...xs)); projH.push(Math.max(...ys) - Math.min(...ys));
  if (t >= itOval.tracos[0].t0) {
    // distância de cada ponto do oval (deslocado) ao retângulo girado (no referencial da peça)
    for (const p0 of ptsOval) {
      const px = p0[0] + an.dx - c[0], py = p0[1] + an.dy - c[1];
      const lx = px * Math.cos(-g) - py * Math.sin(-g), ly = px * Math.sin(-g) + py * Math.cos(-g);
      const d = Math.hypot(Math.max(Math.abs(lx) - pc.w / 2, 0), Math.max(Math.abs(ly) - pc.h / 2, 0));
      folgaMin = Math.min(folgaMin, d);
    }
  }
}
conferir(folgaMin > 10, `oval chega a ${folgaMin.toFixed(1)} px da peça girando`);
const env = caixaEnvelope(amostras);
conferir(Math.abs(env.w - asa.caixa.w) < 0.01 && Math.abs(env.h - asa.caixa.h) < 0.01, `caixaEnvelope ${env.w}x${env.h} ≠ caixa da cena ${asa.caixa.w}x${asa.caixa.h}`);
const variacaoProjetada = [Math.max(...projW) - Math.min(...projW), Math.max(...projH) - Math.min(...projH)];

// 3. irregularidade determinística
const caixa = { x: 0, y: 0, w: 300, h: 120 };
const a1 = formaOval(caixa, 30, 7), a2 = formaOval(caixa, 30, 7), b1 = formaOval(caixa, 30, 8);
conferir(JSON.stringify(a1.pts) === JSON.stringify(a2.pts), "mesma semente deu oval diferente");
conferir(JSON.stringify(a1.pts) !== JSON.stringify(b1.pts), "sementes diferentes deram o mesmo oval");
// desvio radial em relação à espiral ideal (elipse sem giro, raio 1 + 6% u³ da perninha)
const liso0 = formaOval(caixa, 30, 7, 0);
let dmax = 0;
liso0.pts.forEach(([x, y], i) => {
  const u = i / (liso0.pts.length - 1);
  const r = Math.sqrt(((x - 150) / liso0.rx) ** 2 + ((y - 60) / liso0.ry) ** 2) / (1 + 0.06 * u ** 3);
  dmax = Math.max(dmax, Math.abs(r - 1));
});
conferir(dmax > 0.003 && dmax < 0.04, `ondulação do oval fora de 0,3–4%: ${(dmax * 100).toFixed(2)}%`);
// estado() é função pura do tempo: mesmo t, mesmo desenho (nada de sorteio por quadro)
conferir(JSON.stringify(estado(m, 3.21)) === JSON.stringify(estado(montar(cena, fonte), 3.21)), "estado() não é determinístico");

// 4. texto à mão: cobertura PT-BR
const frase = "ação, pressão é já à frente; você pôs 3,5% a 12° ±0,2 × 1/2";
const mt = montarTexto(frase, fonte);
conferir(mt.faltando.length === 0, `sem glifo: ${JSON.stringify(mt.faltando)}`);
const comAcento = montarTexto("ã", fonte).glifos[0], semAcento = montarTexto("a", fonte).glifos[0];
conferir(comAcento.tracos.length === semAcento.tracos.length + 1 && comAcento.tracos.at(-1)!.tinta, "til não virou traço de tinta");

// 5. riscado encurtado perto do vizinho (valor 323 tem "km/h" a 22 px)
const corr = m.itens.find((i) => i.a.id === "corr-valor")!;
const xMaxRisco = Math.max(...corr.tracos[0].pts.map((p) => p[0]));
conferir(xMaxRisco < cena.alvos.unidade.caixa.x - 3.5 - 4, `riscado chega a ${xMaxRisco.toFixed(1)} (km/h começa em ${cena.alvos.unidade.caixa.x})`);

const resumo = {
  checagens: ok + falhas.length, ok, falhas,
  quadros: rel.quadros,
  oval: { tamanho_px: ov?.tamanho.map((v) => +v.toFixed(2)), margens_px: ov?.margens.map((v) => +v.toFixed(2)), variacao_px: ov && Math.max(ov.variacaoTamanho, ov.variacaoMargem), folga_min_peca_girando_px: +folgaMin.toFixed(1) },
  caixa_projetada_da_peca_variaria_px: variacaoProjetada.map((v) => +v.toFixed(1)),
  ondulacao_oval_pct: +(dmax * 100).toFixed(2),
  desenho_s: Object.fromEntries(Object.entries(rel.desenho).map(([k, d]) => [k, [+d.inicio.toFixed(3), +d.fim.toFixed(3)]])),
};
console.log(JSON.stringify(resumo, null, 1));
process.exit(falhas.length ? 1 : 0);
