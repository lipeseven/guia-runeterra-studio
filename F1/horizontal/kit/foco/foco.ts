// kit/foco: foco de profundidade (desfoque + escurecimento leve) em tudo que NÃO é a peça destacada.
// Núcleo sem dependência de motor: para cada tempo t devolve a janela nítida (caixa estável da peça + folga, deslocada
// pela âncora), a força do efeito (entrada/saída suaves) e a MÁSCARA (SVG em anéis) que o motor aplica numa camada com
// backdrop-filter. Remotion e HyperFrames só copiam `estilo(estado)` para uma <div> por cima da cena.
//   const m = montarFoco(cena);  estadoFoco(m, t)  →  [{ id, k, blur, veu, janela, mascara, ... }]
// A caixa estável e a trilha de movimento usam o MESMO formato do kit/anotacao (caixa + movimento dx/dy/s).
import { ancoraEm, caixaEnvelope, type Alvo, type Caixa, type P } from "../anotacao/anotacao.ts";

export { ancoraEm, caixaEnvelope };
export type { Alvo, Caixa, P };

export type Foco = {
  id: string;
  /** caixa ESTÁVEL da peça (pose de referência) + trilha da âncora; ver kit/anotacao (caixaEnvelope para peça que gira) */
  alvo: Alvo;
  /** s: começa a entrar em `em`; termina de sair em `ate` */
  em: number;
  ate: number;
  /** s de entrada e de saída (padrão 0,45 e 0,35) */
  entrada?: number;
  saida?: number;
  /** px de desfoque no pico (padrão 10) */
  blur?: number;
  /** 0..1: opacidade do véu escuro no pico (padrão 0,10; leve: o fundo claro continua claro) */
  escurecer?: number;
  /** px nítidos em volta da caixa (padrão 18) */
  folga?: number;
  /** canto arredondado da janela nítida (padrão 22) */
  raio?: number;
  /** px de transição nítido → desfocado, TODA fora da janela (padrão 28) */
  pena?: number;
  /** "caixa" (retângulo arredondado, padrão) ou "elipse" (circunscreve a caixa + folga) */
  forma?: "caixa" | "elipse";
  /** cor do véu (padrão preto) */
  cor?: string;
};
export type CenaFoco = { largura: number; altura: number; fps: number; duracao: number; focos: Foco[] };
export type MontadaFoco = { cena: CenaFoco; focos: Required<Foco>[] };

/** Número de anéis da pena (degraus de ~2 px com a pena padrão) */
export const ANEIS = 14;

const PADRAO = { entrada: 0.45, saida: 0.35, blur: 10, escurecer: 0.1, folga: 18, raio: 22, pena: 28, forma: "caixa" as const, cor: "#000" };

export function montarFoco(cena: CenaFoco): MontadaFoco {
  const focos = cena.focos.map((f) => {
    const r = { ...PADRAO, ...f } as Required<Foco>;
    if (r.ate - r.em < r.entrada + r.saida) {
      // intervalo curto: entrada e saída dividem o tempo, sem patamar
      const esc = (r.ate - r.em) / (r.entrada + r.saida);
      r.entrada *= esc;
      r.saida *= esc;
    }
    return r;
  });
  return { cena, focos };
}

const suave = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
/** smootherstep (derivada nula nas pontas: o desfoque não "estala" ao começar nem ao terminar) */
const muitoSuave = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * x * (x * (x * 6 - 15) + 10));

/** força do efeito 0..1 no tempo t */
export function forca(f: Required<Foco>, t: number): number {
  if (t <= f.em || t >= f.ate) return 0;
  return Math.min(muitoSuave((t - f.em) / f.entrada), muitoSuave((f.ate - t) / f.saida));
}

/** caixa da peça no tempo t (caixa estável deslocada e escalada pela âncora, em volta do centro) */
export function caixaEm(alvo: Alvo, t: number): Caixa {
  const a = ancoraEm(alvo, t);
  const c = alvo.caixa;
  const cx = c.x + c.w / 2 + a.dx, cy = c.y + c.h / 2 + a.dy;
  return { x: cx - (c.w / 2) * a.s, y: cy - (c.h / 2) * a.s, w: c.w * a.s, h: c.h * a.s };
}

/** janela nítida = caixa + folga (retângulo) ou elipse que passa pelos cantos da caixa + folga */
export function janelaEm(f: Required<Foco>, t: number): Caixa {
  const c = caixaEm(f.alvo, t);
  return { x: c.x - f.folga, y: c.y - f.folga, w: c.w + 2 * f.folga, h: c.h + 2 * f.folga };
}

const n2 = (x: number) => Math.round(x * 100) / 100;

/** retângulo arredondado (horário) */
function ret(c: Caixa, r: number): string {
  r = Math.min(r, c.w / 2, c.h / 2);
  const { x, y, w, h } = c;
  return `M${n2(x + r)} ${n2(y)}H${n2(x + w - r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + w)} ${n2(y + r)}V${n2(y + h - r)}` +
    `A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + w - r)} ${n2(y + h)}H${n2(x + r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x)} ${n2(y + h - r)}` +
    `V${n2(y + r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + r)} ${n2(y)}Z`;
}
function elipse(cx: number, cy: number, rx: number, ry: number): string {
  return `M${n2(cx - rx)} ${n2(cy)}A${n2(rx)} ${n2(ry)} 0 1 1 ${n2(cx + rx)} ${n2(cy)}A${n2(rx)} ${n2(ry)} 0 1 1 ${n2(cx - rx)} ${n2(cy)}Z`;
}

/** contorno da janela expandida por `off` px */
function contorno(f: Required<Foco>, j: Caixa, off: number): string {
  if (f.forma === "elipse") {
    const k = Math.SQRT2; // elipse que passa pelos cantos do retângulo j
    return elipse(j.x + j.w / 2, j.y + j.h / 2, (j.w / 2) * k + off, (j.h / 2) * k + off);
  }
  return ret({ x: j.x - off, y: j.y - off, w: j.w + 2 * off, h: j.h + 2 * off }, f.raio + off);
}

/** Opacidade da camada de desfoque em cada anel i (1..ANEIS): o anel i vai de off (i-1)·pena/N até i·pena/N. */
export const nivelAnel = (i: number) => suave(i / ANEIS);

/**
 * Máscara (alfa) da camada desfocada: 1 fora da janela + pena, anéis com alfa crescente na pena, 0 DENTRO da janela
 * (não há nenhum preenchimento ali: a peça fica exatamente como sem foco). Anéis com fill-rule evenodd (dois contornos).
 */
export function mascaraSvg(f: Required<Foco>, j: Caixa, largura: number, altura: number): string {
  const partes: string[] = [];
  const offs = Array.from({ length: ANEIS + 1 }, (_, i) => (i * f.pena) / ANEIS);
  // fora de tudo: quadro inteiro menos o contorno externo
  partes.push(`<path fill-rule="evenodd" d="M-2 -2H${largura + 2}V${altura + 2}H-2Z${contorno(f, j, offs[ANEIS])}"/>`);
  for (let i = 1; i <= ANEIS; i++) {
    partes.push(`<path fill-rule="evenodd" fill-opacity="${nivelAnel(i).toFixed(4)}" d="${contorno(f, j, offs[i])}${contorno(f, j, offs[i - 1])}"/>`);
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${largura}" height="${altura}" viewBox="0 0 ${largura} ${altura}"><g fill="#fff">${partes.join("")}</g></svg>`;
}

/** distância (px, >0 = fora) de p ao contorno da janela; para elipse, aproximação radial (mesma usada pelos anéis) */
export function distJanela(f: Required<Foco>, j: Caixa, p: P): number {
  if (f.forma === "elipse") {
    const cx = j.x + j.w / 2, cy = j.y + j.h / 2, rx = (j.w / 2) * Math.SQRT2, ry = (j.h / 2) * Math.SQRT2;
    // menor off tal que p está dentro da elipse (rx+off, ry+off): busca binária
    const dentro = (off: number) => ((p[0] - cx) / (rx + off)) ** 2 + ((p[1] - cy) / (ry + off)) ** 2 <= 1;
    if (dentro(0)) return -1;
    let lo = 0, hi = 4000;
    for (let k = 0; k < 40; k++) { const m = (lo + hi) / 2; if (dentro(m)) hi = m; else lo = m; }
    return hi;
  }
  // retângulo arredondado expandido: distância ao retângulo interno (encolhido pelo raio) − raio
  const r = Math.min(f.raio, j.w / 2, j.h / 2);
  const ix0 = j.x + r, ix1 = j.x + j.w - r, iy0 = j.y + r, iy1 = j.y + j.h - r;
  const dx = Math.max(ix0 - p[0], 0, p[0] - ix1), dy = Math.max(iy0 - p[1], 0, p[1] - iy1);
  const d = Math.hypot(dx, dy) - r;
  return d;
}

/** alfa da camada desfocada no ponto p (mesma regra dos anéis da máscara): 0 dentro da janela, 1 depois da pena */
export function alfaEm(f: Required<Foco>, j: Caixa, p: P): number {
  const d = distJanela(f, j, p);
  if (d <= 0) return 0;
  if (d > f.pena) return 1;
  return nivelAnel(Math.ceil((d / f.pena) * ANEIS - 1e-9));
}

export type FocoEstado = {
  id: string;
  /** força 0..1 (0 = sem efeito: o motor não desenha nada) */
  k: number;
  /** px de desfoque neste quadro */
  blur: number;
  /** opacidade do véu neste quadro */
  veu: number;
  cor: string;
  /** caixa da peça e janela nítida neste quadro (px do quadro) */
  caixa: Caixa;
  janela: Caixa;
  /** SVG da máscara (alfa) e o mesmo como data URI para mask-image */
  mascara: string;
  mascaraUrl: string;
};

export function estadoFoco(m: MontadaFoco, t: number): FocoEstado[] {
  const out: FocoEstado[] = [];
  for (const f of m.focos) {
    const k = forca(f, t);
    if (k <= 0) continue;
    const caixa = caixaEm(f.alvo, t), janela = janelaEm(f, t);
    const mascara = mascaraSvg(f, janela, m.cena.largura, m.cena.altura);
    out.push({
      id: f.id, k, blur: f.blur * k, veu: f.escurecer * k, cor: f.cor, caixa, janela, mascara,
      mascaraUrl: `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(mascara)}")`,
    });
  }
  return out;
}

/**
 * Estilos CSS (mesmos nos dois motores) para UMA camada por foco, por cima da cena:
 *  - `camada`: desfoca o que está atrás (backdrop-filter) só onde a máscara deixa;
 *  - `veu`: escurece de leve com a mesma máscara.
 * Nomes em camelCase (React); o adaptador HyperFrames converte para kebab-case.
 */
export function estilos(e: FocoEstado): { camada: Record<string, string>; veu: Record<string, string> } {
  const base = {
    position: "absolute", left: "0", top: "0", width: "100%", height: "100%", pointerEvents: "none",
    maskImage: e.mascaraUrl, WebkitMaskImage: e.mascaraUrl, maskSize: "100% 100%", WebkitMaskSize: "100% 100%",
    maskRepeat: "no-repeat", WebkitMaskRepeat: "no-repeat", maskMode: "alpha",
  };
  return {
    camada: { ...base, backdropFilter: `blur(${e.blur.toFixed(3)}px)`, WebkitBackdropFilter: `blur(${e.blur.toFixed(3)}px)` },
    veu: { ...base, background: e.cor, opacity: e.veu.toFixed(4) },
  };
}

// ---------------------------------------------------------------- verificação
export type RelatorioFoco = {
  quadros: number;
  falhas: string[];
  focos: Record<string, { quadrosAtivos: number; kMax: number; saltoMaxK: number; pontosDentro: number; pontosFora: number; erroJanelaPx: number }>;
};

/**
 * Percorre todos os quadros e confere, para cada foco:
 *  - k = 0 antes de `em` e depois de `ate`; k = 1 no patamar; salto de k por quadro ≤ 1,9/(entrada·fps) (sem estalo);
 *  - janela = caixa da peça + folga exatamente (erro < 1e-6 px), acompanhando a âncora;
 *  - alfa da camada desfocada = 0 em TODA a caixa da peça (grade 13×13 + bordas) e = 1 a mais de `pena` px da janela;
 *  - alfa nunca diminui saindo da janela (raios a partir do centro).
 */
export function checarFoco(m: MontadaFoco): RelatorioFoco {
  const { fps, duracao } = m.cena;
  const nq = Math.round(duracao * fps) + 1;
  const rel: RelatorioFoco = { quadros: nq, falhas: [], focos: {} };
  for (const f of m.focos) {
    const r = { quadrosAtivos: 0, kMax: 0, saltoMaxK: 0, pontosDentro: 0, pontosFora: 0, erroJanelaPx: 0 };
    let kAnt = 0;
    const limSalto = 1.9 / (Math.min(f.entrada, f.saida) * fps);
    for (let q = 0; q < nq; q++) {
      const t = q / fps;
      const k = forca(f, t);
      if (k > 0) r.quadrosAtivos++;
      r.kMax = Math.max(r.kMax, k);
      r.saltoMaxK = Math.max(r.saltoMaxK, Math.abs(k - kAnt));
      kAnt = k;
      if ((t <= f.em || t >= f.ate) && k !== 0) rel.falhas.push(`${f.id}: k=${k} fora do intervalo (q${q})`);
      if (t >= f.em + f.entrada && t <= f.ate - f.saida && Math.abs(k - 1) > 1e-9) rel.falhas.push(`${f.id}: k=${k} no patamar (q${q})`);
      const c = caixaEm(f.alvo, t), j = janelaEm(f, t);
      r.erroJanelaPx = Math.max(r.erroJanelaPx, Math.abs(j.x - (c.x - f.folga)), Math.abs(j.y - (c.y - f.folga)),
        Math.abs(j.x + j.w - (c.x + c.w + f.folga)), Math.abs(j.y + j.h - (c.y + c.h + f.folga)));
      if (q % 6 !== 0) continue;
      // caixa inteira nítida
      for (let a = 0; a <= 12; a++) for (let b = 0; b <= 12; b++) {
        const p: P = [c.x + (c.w * a) / 12, c.y + (c.h * b) / 12];
        r.pontosDentro++;
        if (alfaEm(f, j, p) !== 0) rel.falhas.push(`${f.id}: desfoque dentro da caixa em ${p.map(n2)} (q${q})`);
      }
      // raios: monotônico e = 1 depois da pena
      const cx = j.x + j.w / 2, cy = j.y + j.h / 2;
      for (let ang = 0; ang < 360; ang += 15) {
        const ux = Math.cos((ang * Math.PI) / 180), uy = Math.sin((ang * Math.PI) / 180);
        let ant = 0;
        for (let s = 0; s < 1400; s += 2) {
          const p: P = [cx + ux * s, cy + uy * s];
          const al = alfaEm(f, j, p);
          if (al < ant - 1e-12) { rel.falhas.push(`${f.id}: alfa diminui saindo da janela (q${q}, ${ang}°)`); break; }
          ant = al;
          if (distJanela(f, j, p) > f.pena + 1e-6) {
            r.pontosFora++;
            if (al !== 1) rel.falhas.push(`${f.id}: alfa ${al} depois da pena (q${q})`);
            break;
          }
        }
      }
    }
    if (r.saltoMaxK > limSalto) rel.falhas.push(`${f.id}: salto de k ${r.saltoMaxK.toFixed(3)} por quadro (> ${limSalto.toFixed(3)})`);
    if (r.erroJanelaPx > 1e-6) rel.falhas.push(`${f.id}: janela ≠ caixa + folga (${r.erroJanelaPx} px)`);
    rel.focos[f.id] = r;
  }
  rel.falhas = [...new Set(rel.falhas)].slice(0, 40);
  return rel;
}
