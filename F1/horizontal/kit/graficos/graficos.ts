// kit/graficos — gráficos de comparação de duas voltas (OpenF1), independente de motor.
//
// O kit faz TODA a conta: escala, ticks, posição de cada rótulo (sem sobreposição), cores legíveis no fundo e o desenho
// progressivo. O motor só desenha o que `estado(m, t)` devolve: caminhos (path) e textos, em px da tela.
//
//   const m = montar([spec, ...], dados, larguras);   // uma vez (dados = kit/graficos/comparacoes/*.json, larguras = fonte/segoe_larguras.json)
//   estado(m, t)                                      // por quadro: [{ id, tipo: "path"|"texto", ... }]
//   checar(m)                                         // verificação geométrica (área, rótulos, desenho que termina)
//
// Tipos de gráfico: velocidade (× distância, gap destacado), setores (delta por setor), delta (acumulado),
// telemetria (acelerador / freio / marcha) e normalizado (comparativo por métrica, escala de cada linha explícita).
// Sem dependências: roda no Node 24 (`node cli.ts`), no Remotion (import) e no HyperFrames (graficos.global.js).

// ------------------------------------------------------------------------------------------------ tipos públicos
export type Caixa = { x: number; y: number; w: number; h: number };
export type Ritmo = { t: number; d: number }[];
export type Spec = {
  id: string;
  tipo: "velocidade" | "setores" | "delta" | "telemetria" | "normalizado";
  area: Caixa;                       // px na tela; nada é desenhado fora dela
  em: number;                        // s: início da entrada
  ate?: number;                      // s: some a partir daqui (corte seco; transição é do montador). Padrão: fica.
  tema?: "claro" | "escuro";         // claro = assinatura do canal (padrão)
  titulo?: string;
  subtitulo?: string;
  fonte?: string | false;            // linha de crédito no rodapé (padrão: dados.fonte_curta)
  trecho?: [number, number];         // m (velocidade, delta, telemetria, normalizado)
  dur?: number;                      // s do desenho dos dados (padrão 3)
  ritmo?: Ritmo;                     // âncoras tempo → distância alcançada pelo desenho (sincroniza com a narração)
  destaque?: false | "auto" | { d0: number; d1: number; texto?: string };
  destaqueEm?: number;               // s (padrão: fim do desenho + 0,3)
  curvas?: boolean | number[];       // nomes das curvas acima do gráfico (true = todas com nome no trecho)
  setores?: boolean;                 // linhas de setor (padrão true)
  minimapa?: boolean;                // traçado da pista com o trecho destacado (velocidade, delta)
  paineis?: ("acelerador" | "freio" | "marcha" | "velocidade")[]; // telemetria
  metricas?: Metrica[];              // normalizado
  escala?: number;                   // multiplica os tamanhos de texto (padrão: pelo tamanho da área)
};
export type Metrica = "vmax" | "vmin" | "vmedia" | "acelPleno" | "freando";

export type Piloto = {
  numero: number; sigla: string; nome: string; equipe: string; cor: string; volta: number; tempo: number;
  setores: number[]; t: number[]; vel: number[]; acel: number[]; freio: number[]; marcha: number[];
  bruto?: { t: number[]; d: number[]; vel: number[]; acel: number[]; freio: number[]; marcha: number[] }; // amostras do car_data
};
export type Dados = {
  fonte: string; fonte_curta: string; circuito?: string; comprimento_m: number; passo_m: number; grade_d: number[];
  pilotos: Piloto[]; delta: number[]; setores_d: { d: number }[];
  curvas: { n: number; nome: string; d: number }[];
  tracado: { x: number[]; z: number[]; d: number[] } | null;
};
export type Larguras = { ascendente: number; descendente: number; pesos: Record<string, Record<string, number>> };

type Pt = [number, number];
type Base = { id: string; grafico: string; papel: string; em: number; dur: number };
export type SerieRef = { piloto: string; campo: string; degrau?: boolean };
export type ElLinha = Base & { tipo: "linha"; pts: Pt[]; cor: string; largura: number; tracejado?: string;
  revela: "cursor" | "x" | "comp"; serie?: SerieRef; fechada?: boolean };
export type ElArea = Base & { tipo: "area"; sup: Pt[]; inf: Pt[]; cor: string; opac: number; revela: "cursor" | "fade" };
export type ElRet = Base & { tipo: "ret"; x: number; y: number; w: number; h: number; cor: string; opac: number;
  revela: "cursor" | "dir" | "esq" | "cima" | "fade"; valor?: number; escala?: number; raio?: number };
export type ElTexto = Base & { tipo: "texto"; x: number; y: number; texto: string; tam: number; peso: number; cor: string;
  ancora: "start" | "middle" | "end"; caixa: Caixa };
export type El = ElLinha | ElArea | ElRet | ElTexto;
export type Eixo = { d0: number; d1: number; x0: number; x1: number; v0: number; v1: number; y0: number; y1: number; nome: string };
export type Grafico = {
  spec: Spec; tema: Tema; elementos: El[]; eixos: Eixo[]; plot: Caixa | null;
  cursor: { ritmo: Ritmo; x0: number; x1: number; d0: number; d1: number } | null; fim: number; avisos: string[];
};
export type Montado = { graficos: Grafico[]; avisos: string[]; fonteCss: string };
export type Desenho =
  | { id: string; tipo: "path"; d: string; stroke?: string; fill?: string; largura?: number; opac: number; tracejado?: string }
  | { id: string; tipo: "texto"; x: number; y: number; texto: string; tam: number; peso: number; cor: string; ancora: string; opac: number };

// ------------------------------------------------------------------------------------------------ tema e cores
export type Tema = { nome: string; fundo: string; tinta: string; tinta2: string; grade: string; eixo: string; destaque: string };
export const TEMAS: Record<string, Tema> = {
  claro: { nome: "claro", fundo: "#f2f1ed", tinta: "#151515", tinta2: "#5f5e5a", grade: "#dcdbd5", eixo: "#9c9b96", destaque: "#d40000" },
  escuro: { nome: "escuro", fundo: "#141518", tinta: "#f2f1ed", tinta2: "#a9a8a3", grade: "#2d2e33", eixo: "#64656a", destaque: "#ff4a3d" },
};
export const FONTE_CSS = "'Segoe UI', Arial, sans-serif";

function rgb(h: string): number[] { const s = h.replace("#", ""); return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16)); }
function hex(c: number[]): string { return "#" + c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join(""); }
function lum(h: string): number {
  const [r, g, b] = rgb(h).map((v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
export function contraste(a: string, b: string): number { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); }
/** Cor da equipe ajustada até contraste ≥ 3:1 com o fundo (WCAG para elementos gráficos): escurece no claro, clareia no escuro. */
export function corLegivel(cor: string, fundo: string, minimo = 3): string {
  const alvo = lum(fundo) > 0.5 ? [0, 0, 0] : [255, 255, 255];
  let c = rgb(cor);
  for (let i = 0; i < 40 && contraste(hex(c), fundo) < minimo; i++) c = c.map((v, k) => v + (alvo[k] - v) * 0.06);
  return hex(c);
}

// ------------------------------------------------------------------------------------------------ texto
let LARG: Larguras | null = null;
export function larguraTexto(texto: string, tam: number, peso: number): number {
  const tab = LARG!.pesos[String(peso)] || LARG!.pesos["400"];
  let w = 0;
  for (const ch of texto) w += tab[ch] ?? tab["M"] ?? 600;
  return (w * tam) / 1000;
}
function caixaTexto(x: number, y: number, texto: string, tam: number, peso: number, ancora: ElTexto["ancora"]): Caixa {
  const w = larguraTexto(texto, tam, peso);
  const x0 = ancora === "start" ? x : ancora === "middle" ? x - w / 2 : x - w;
  return { x: x0, y: y - LARG!.ascendente * tam, w, h: (LARG!.ascendente + LARG!.descendente) * tam };
}
export function fmt(v: number, casas = 0, sinal = false): string {
  const neg = v < 0 && Math.abs(v) >= 0.5 * 10 ** -casas;
  const [i, f] = Math.abs(v).toFixed(casas).split(".");
  const mil = i.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (neg ? "−" : sinal && v > 0 ? "+" : "") + mil + (f ? "," + f : "");
}
function cruza(a: Caixa, b: Caixa, folga = 0): boolean {
  return a.x < b.x + b.w + folga && b.x < a.x + a.w + folga && a.y < b.y + b.h + folga && b.y < a.y + a.h + folga;
}

// ------------------------------------------------------------------------------------------------ utilitários
const lim = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const suave = (k: number) => 0.5 - 0.5 * Math.cos(Math.PI * lim(k, 0, 1));
function interp(xs: number[], ys: number[], x: number): number {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  return ys[lo] + ((ys[hi] - ys[lo]) * (x - xs[lo])) / (xs[hi] - xs[lo]);
}
function ticks(v0: number, v1: number, alvo = 5): number[] {
  const bruto = (v1 - v0) / alvo, p = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= bruto * 0.8) ?? 10 * p;
  const out: number[] = [];
  for (let v = Math.ceil(v0 / passo - 1e-9) * passo; v <= v1 + 1e-9; v += passo) out.push(Math.round(v / passo) * passo);
  return out;
}
function passoTick(v0: number, v1: number, alvo = 5): number { const t = ticks(v0, v1, alvo); return t.length > 1 ? t[1] - t[0] : 1; }
function indices(D: Dados, d0: number, d1: number): number[] {
  const out: number[] = [];
  D.grade_d.forEach((d, i) => { if (d >= d0 - 1e-6 && d <= d1 + 1e-6) out.push(i); });
  return out;
}

// ------------------------------------------------------------------------------------------------ construtor de um gráfico
class Construtor {
  els: El[] = []; avisos: string[] = []; eixos: Eixo[] = [];
  textos: Caixa[] = [];
  s: number; tema: Tema; A: Piloto; B: Piloto; corA: string; corB: string;
  spec: Spec; D: Dados;
  cursor: Grafico["cursor"] = null; plot: Caixa | null = null;
  constructor(spec: Spec, D: Dados) {
    this.spec = spec; this.D = D;
    this.tema = TEMAS[spec.tema ?? "claro"];
    this.s = spec.escala ?? lim(Math.min(spec.area.w / 1700, spec.area.h / 920), 0.55, 1.3);
    [this.A, this.B] = D.pilotos;
    this.corA = corLegivel(this.A.cor, this.tema.fundo);
    this.corB = corLegivel(this.B.cor, this.tema.fundo);
    if (contraste(this.corA, this.corB) < 1.25) this.corB = corLegivel(this.B.cor, this.tema.fundo, 4.5);
  }
  get T() { return this.tema; }
  t(id: string, papel: string, x: number, y: number, texto: string, tam: number, peso: number, cor: string,
    ancora: ElTexto["ancora"], em: number, dur = 0.2): ElTexto {
    const e: ElTexto = { id: `${this.spec.id}:${id}`, grafico: this.spec.id, papel, tipo: "texto", x, y, texto, tam, peso, cor, ancora,
      caixa: caixaTexto(x, y, texto, tam, peso, ancora), em, dur };
    this.els.push(e); this.textos.push(e.caixa);
    return e;
  }
  /** cabe sem cruzar nenhum texto já posto (folga em px) e dentro da área */
  cabe(c: Caixa, folga = 6 * this.s): boolean {
    const a = this.spec.area;
    if (c.x < a.x || c.y < a.y || c.x + c.w > a.x + a.w || c.y + c.h > a.y + a.h) return false;
    return !this.textos.some((o) => cruza(o, c, folga));
  }
  linha(id: string, papel: string, pts: Pt[], cor: string, largura: number, em: number, dur: number,
    revela: ElLinha["revela"], extra: Partial<ElLinha> = {}): ElLinha {
    const e: ElLinha = { id: `${this.spec.id}:${id}`, grafico: this.spec.id, papel, tipo: "linha", pts, cor, largura, em, dur, revela, ...extra };
    this.els.push(e);
    return e;
  }
  ret(id: string, papel: string, x: number, y: number, w: number, h: number, cor: string, opac: number, em: number, dur: number,
    revela: ElRet["revela"], extra: Partial<ElRet> = {}): ElRet {
    const e: ElRet = { id: `${this.spec.id}:${id}`, grafico: this.spec.id, papel, tipo: "ret", x, y, w, h, cor, opac, em, dur, revela, ...extra };
    this.els.push(e);
    return e;
  }
  /** título, subtítulo e legenda (amostra de linha + sigla) no topo; devolve o y de baixo do cabeçalho */
  cabecalho(titulo: string, subtitulo: string, legenda: boolean, larguraLegenda?: number): number {
    const { area } = this.spec, s = this.s, pad = 30 * s, em = this.spec.em;
    let y = area.y + pad + 44 * s * LARG!.ascendente;
    this.t("titulo", "titulo", area.x + pad, y, titulo, 44 * s, 700, this.T.tinta, "start", em);
    if (legenda) {
      let x = area.x + area.w - pad - (larguraLegenda ?? 0);
      for (const [P, cor, k] of [[this.B, this.corB, "b"], [this.A, this.corA, "a"]] as const) {
        const rot = `${P.sigla} · ${P.nome.split(" ").slice(-1)[0][0]}${P.nome.split(" ").slice(-1)[0].slice(1).toLowerCase()}`;
        const tt = this.t(`leg-${k}`, "legenda", x, y - 2 * s, rot, 24 * s, 600, cor, "end", em + 0.1);
        x = tt.caixa.x - 12 * s;
        this.linha(`leg-amostra-${k}`, "legenda", [[x - 34 * s, y - 10 * s], [x, y - 10 * s]], cor, 6 * s, em + 0.1, 0.2, "x");
        x -= 34 * s + 30 * s;
      }
    }
    if (subtitulo) {
      y += 40 * s;
      this.t("subtitulo", "titulo", area.x + pad, y, subtitulo, 25 * s, 400, this.T.tinta2, "start", em + 0.05);
    }
    return y + LARG!.descendente * 25 * s + 14 * s;
  }
  rodape(): number {
    const { area } = this.spec, s = this.s, pad = 30 * s;
    const f = this.spec.fonte === false ? "" : this.spec.fonte ?? this.D.fonte_curta;
    const y = area.y + area.h - pad * 0.6 - LARG!.descendente * 18 * s;
    if (f) this.t("fonte", "fonte", area.x + pad, y, f, 18 * s, 400, this.T.tinta2, "start", this.spec.em);
    return y - LARG!.ascendente * 18 * s - 10 * s;
  }
  /** fileiras de rótulos acima do gráfico: cada item vai na primeira fileira em que cabe (ou é omitido com aviso) */
  fileiras(itens: { id: string; x: number; texto: string; cor: string; peso: number; em: number; obrig?: boolean }[],
    yBase: number, n: number, tam: number, x0: number, x1: number): ElTexto[] {
    const out: ElTexto[] = [], alt = tam * 1.3;
    for (const it of itens) {
      let pos: ElTexto | null = null;
      for (let r = 0; r < n && !pos; r++) {
        const y = yBase - r * alt;
        const w = larguraTexto(it.texto, tam, it.peso);
        const xc = lim(it.x, x0 + w / 2, x1 - w / 2);
        const c = caixaTexto(xc, y, it.texto, tam, it.peso, "middle");
        if (this.cabe(c)) pos = this.t(it.id, "rotulo", xc, y, it.texto, tam, it.peso, it.cor, "middle", it.em);
      }
      if (pos) out.push(pos);
      else this.avisos.push(`rótulo "${it.texto}" omitido (sem espaço)`);
    }
    return out;
  }
  /** rótulos diretos no fim das linhas (à direita do gráfico), separados na vertical se estiverem perto */
  rotulosFim(itens: { id: string; y: number; texto: string; cor: string }[], x: number, tam: number, em: number, yMin: number, yMax: number) {
    const alt = tam * (LARG!.ascendente + LARG!.descendente) + 8 * this.s;
    const ord = itens.map((it) => ({ ...it, yc: it.y })).sort((a, b) => a.yc - b.yc);
    for (let it = 0; it < 30; it++) {
      let mexeu = false;
      for (let i = 1; i < ord.length; i++) {
        const sep = ord[i].yc - ord[i - 1].yc;
        if (sep < alt) { const m = (alt - sep) / 2; ord[i - 1].yc -= m; ord[i].yc += m; mexeu = true; }
      }
      const lo = yMin + alt / 2, hi = yMax - alt / 2;
      if (ord[0].yc < lo) { const m = lo - ord[0].yc; ord.forEach((o) => (o.yc += m)); }
      if (ord[ord.length - 1].yc > hi) { const m = ord[ord.length - 1].yc - hi; ord.forEach((o) => (o.yc -= m)); }
      if (!mexeu) break;
    }
    for (const o of ord) {
      const base = o.yc + (tam * (LARG!.ascendente - LARG!.descendente)) / 2;
      this.t(o.id, "legenda", x, base, o.texto, tam, 700, o.cor, "start", em);
    }
  }
}

// ------------------------------------------------------------------------------------------------ peças comuns de gráfico × distância
type Plano = { c: Construtor; plot: Caixa; d0: number; d1: number; v0: number; v1: number; xOf: (d: number) => number; yOf: (v: number) => number;
  tDados: number; tFim: number; ritmo: Ritmo; tEm: (d: number) => number };

function ritmoDe(spec: Spec, d0: number, d1: number, tDados: number): Ritmo {
  if (spec.ritmo && spec.ritmo.length >= 2) return spec.ritmo.map((r) => ({ t: r.t, d: lim(r.d, d0, d1) }));
  const dur = spec.dur ?? 3, n = 24;
  // um único trecho: arranque e chegada suaves, amostrado em 24 pontos (vira o mesmo formato das âncoras)
  return Array.from({ length: n + 1 }, (_, i) => ({ t: tDados + (dur * i) / n, d: d0 + (d1 - d0) * suave(i / n) }));
}
export function distCursor(r: Ritmo, t: number): number {
  return interp(r.map((p) => p.t), r.map((p) => p.d), t);
}
function tempoEm(r: Ritmo, d: number): number {
  for (let i = 1; i < r.length; i++) if (r[i].d >= d) {
    const a = r[i - 1], b = r[i];
    return b.d === a.d ? a.t : a.t + ((d - a.d) / (b.d - a.d)) * (b.t - a.t);
  }
  return r[r.length - 1].t;
}

/** eixos x (distância) e y, grade, ticks, setores e curvas; devolve o plano para as séries */
function plano(c: Construtor, plot: Caixa, d0: number, d1: number, v0: number, v1: number, nomeY: string, unidadeY: string,
  fmtY: (v: number) => string, nFileiras: number, passoY?: number): Plano {
  const { spec, s, T } = c, em = spec.em;
  const xOf = (d: number) => plot.x + ((d - d0) / (d1 - d0)) * plot.w;
  const yOf = (v: number) => plot.y + plot.h - ((v - v0) / (v1 - v0)) * plot.h;
  const tDados = spec.ritmo?.[0]?.t ?? em + 0.55;
  const ritmo = ritmoDe(spec, d0, d1, tDados);
  const tFim = ritmo[ritmo.length - 1].t;
  const tEm = (d: number) => tempoEm(ritmo, d);
  c.eixos.push({ d0, d1, x0: plot.x, x1: plot.x + plot.w, v0, v1, y0: yOf(v0), y1: yOf(v1), nome: nomeY });
  // grade horizontal + ticks y
  const ty: number[] = [];
  if (passoY) for (let v = Math.ceil(v0 / passoY - 1e-9) * passoY; v <= v1 + 1e-9; v += passoY) ty.push(+v.toFixed(6));
  else ty.push(...ticks(v0, v1, 5));
  for (const v of ty) {
    c.linha(`grade-y-${v}`, "grade", [[plot.x, yOf(v)], [plot.x + plot.w, yOf(v)]], v === 0 ? T.eixo : T.grade, (v === 0 ? 2.5 : 1.5) * s, em + 0.1, 0.45, "x");
    c.t(`tick-y-${v}`, "eixo", plot.x - 12 * s, yOf(v) + 7 * s, fmtY(v), 20 * s, 400, T.tinta2, "end", em + 0.25);
  }
  c.t("unidade-y", "eixo", plot.x - 12 * s, plot.y - 26 * s, unidadeY, 20 * s, 600, T.tinta2, "end", em + 0.25);
  // eixo x: linha de base, ticks em m
  c.linha("base-x", "eixo", [[plot.x, plot.y + plot.h], [plot.x + plot.w, plot.y + plot.h]], T.eixo, 2 * s, em + 0.1, 0.45, "x");
  const px = passoTick(d0, d1, Math.max(3, Math.round(plot.w / 260)));
  for (let d = Math.ceil(d0 / px) * px; d <= d1 + 1e-6; d += px) {
    c.t(`tick-x-${d}`, "eixo", xOf(d), plot.y + plot.h + 28 * s, fmt(d), 20 * s, 400, T.tinta2, "middle", em + 0.25);
  }
  c.t("unidade-x", "eixo", plot.x + plot.w, plot.y + plot.h + 58 * s, "distância na volta (m)", 20 * s, 600, T.tinta2, "end", em + 0.25);
  // setores: linha tracejada + "S1 S2 S3" na primeira fileira acima
  const rotulos: Parameters<Construtor["fileiras"]>[0] = [];
  if (spec.setores !== false) {
    const fr = [0, ...c.D.setores_d.map((f) => f.d), c.D.comprimento_m];
    for (let k = 0; k < fr.length - 1; k++) {
      const a = Math.max(fr[k], d0), b = Math.min(fr[k + 1], d1);
      if (b - a < (d1 - d0) * 0.06) continue;
      rotulos.push({ id: `setor-${k + 1}`, x: xOf((a + b) / 2), texto: `SETOR ${k + 1}`, cor: T.tinta2, peso: 700, em: em + 0.3 });
    }
    c.D.setores_d.forEach((f, k) => {
      if (f.d <= d0 || f.d >= d1) return;
      c.linha(`setor-linha-${k + 1}`, "grade", [[xOf(f.d), plot.y + plot.h], [xOf(f.d), plot.y - 6 * s]], T.eixo, 2 * s, em + 0.3, 0.3, "comp", { tracejado: `${8 * s} ${7 * s}` });
    });
  }
  if (spec.curvas !== false) {
    const lista = c.D.curvas.filter((k) => k.nome && k.d > d0 && k.d < d1 && (Array.isArray(spec.curvas) ? spec.curvas.includes(k.n) : true));
    for (const k of lista) {
      const tk = tEm(k.d);
      rotulos.push({ id: `curva-${k.n}`, x: xOf(k.d), texto: k.nome, cor: T.tinta, peso: 600, em: tk });
      c.linha(`curva-linha-${k.n}`, "grade", [[xOf(k.d), plot.y - 4 * s], [xOf(k.d), plot.y + plot.h]], T.grade, 2 * s, tk, 0.25, "comp", { tracejado: `${3 * s} ${6 * s}` });
    }
  }
  c.fileiras(rotulos, plot.y - 16 * s, nFileiras, 21 * s, plot.x, plot.x + plot.w);
  return { c, plot, d0, d1, v0, v1, xOf, yOf, tDados, tFim, ritmo, tEm };
}

function serie(P: Plano, Pi: Piloto, campo: "vel" | "acel" | "marcha", ids: number[], degrau = false, map = (v: number) => v): Pt[] {
  const D = P.c.D, arr = Pi[campo] as number[];
  const pts: Pt[] = [];
  ids.forEach((i, j) => {
    const x = P.xOf(D.grade_d[i]), y = P.yOf(map(arr[i]));
    if (degrau && j > 0 && arr[i] !== arr[ids[j - 1]]) pts.push([x, P.yOf(map(arr[ids[j - 1]]))]);
    pts.push([x, y]);
  });
  return pts;
}

/** trecho de maior ganho: janela (m) em que o delta mais muda */
export function destaqueAuto(D: Dados, d0: number, d1: number, janela = 250): { d0: number; d1: number; ganho: number } {
  const g = D.grade_d, n = g.length;
  // escolhe a janela pelo delta suavizado (mediana de ±150 m): nas frenagens fortes, o erro da distância integrada de
  // cada piloto gera picos que vão e voltam (0,2 s em ~350 m na 1ª chicane de Monza) e não são ganho que fica
  const r = Math.max(1, Math.round(50 / D.passo_m)), rs = Math.max(1, Math.round(150 / D.passo_m));
  const sv = g.map((_, i) => { const w = D.delta.slice(Math.max(0, i - rs), Math.min(n, i + rs + 1)).sort((a, b) => a - b); return w[w.length >> 1]; });
  const passos = Math.round(janela / D.passo_m);
  let bi = -1, bj = -1, bg = 0;
  for (let i = 0; i < n; i++) {
    if (g[i] < d0 || g[i] + janela > d1) continue;
    const j = Math.min(n - 1, i + passos);
    if (Math.abs(sv[j] - sv[i]) > Math.abs(bg)) { bi = i; bj = j; bg = sv[j] - sv[i]; }
  }
  if (bi < 0) return { d0, d1: Math.min(d1, d0 + janela), ganho: 0 };
  // pontas: o ponto (±50 m) em que o delta bruto mais se aproxima do suavizado (fora de pico); o ganho escrito é o BRUTO
  const firme = (k: number) => { let b = k; for (let q = Math.max(0, k - r); q <= Math.min(n - 1, k + r); q++) if (Math.abs(D.delta[q] - sv[q]) < Math.abs(D.delta[b] - sv[b])) b = q; return b; };
  const i = firme(bi), j = firme(bj);
  return { d0: g[i], d1: g[j], ganho: D.delta[j] - D.delta[i] };
}
function textoGanho(c: Construtor, ganho: number): { texto: string; cor: string } {
  // delta = tA − tB: se diminui no trecho, A ganhou tempo
  const P = ganho < 0 ? c.A : c.B;
  return { texto: `${P.sigla} ganha ${fmt(Math.abs(ganho), 3)} s aqui`, cor: c.T.destaque };
}

function minimapa(c: Construtor, caixa: Caixa, dest: { d0: number; d1: number } | null, emDest: number) {
  const tr = c.D.tracado;
  if (!tr) { c.avisos.push("minimapa pedido mas os dados não têm traçado"); return; }
  const xs = tr.x, zs = tr.z;
  const [xmin, xmax, zmin, zmax] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
  const m = 12 * c.s, k = Math.min((caixa.w - 2 * m) / (xmax - xmin), (caixa.h - 2 * m) / (zmax - zmin));
  const ox = caixa.x + (caixa.w - (xmax - xmin) * k) / 2, oz = caixa.y + (caixa.h - (zmax - zmin) * k) / 2;
  const P = (i: number): Pt => [ox + (xs[i] - xmin) * k, oz + (zs[i] - zmin) * k];
  const todos = xs.map((_, i) => P(i));
  c.linha("mapa-pista", "mapa", [...todos, todos[0]], c.T.eixo, 7 * c.s, c.spec.em + 0.2, 0.8, "comp");
  if (dest) {
    const sel = tr.d.map((d, i) => [d, i] as const).filter(([d]) => d >= dest.d0 && d <= dest.d1).map(([, i]) => P(i));
    if (sel.length > 1) c.linha("mapa-trecho", "destaque", sel, c.T.destaque, 11 * c.s, emDest, 0.35, "comp");
  }
}

// ------------------------------------------------------------------------------------------------ 1. velocidade × distância
function grafVelocidade(c: Construtor, temDelta = false) {
  const { spec, s, D, T } = c, area = spec.area, pad = 30 * s;
  const [d0, d1] = spec.trecho ?? [0, D.comprimento_m];
  const ids = indices(D, d0, d1);
  const titulo = spec.titulo ?? (temDelta ? "Quem está à frente, metro a metro" : "Velocidade, metro a metro");
  const sub = spec.subtitulo ?? (temDelta
    ? `Diferença acumulada de tempo · ${c.A.sigla} volta ${c.A.volta} (${fmt(c.A.tempo, 3)}) × ${c.B.sigla} volta ${c.B.volta} (${fmt(c.B.tempo, 3)})`
    : `${c.A.sigla} volta ${c.A.volta} (${fmt(c.A.tempo, 3)}) × ${c.B.sigla} volta ${c.B.volta} (${fmt(c.B.tempo, 3)})`);
  const mapaW = spec.minimapa ? Math.min(300 * s, area.w * 0.2) : 0;
  const yTop = c.cabecalho(titulo, sub, !temDelta, 0);
  const yBot = c.rodape();
  const fil = 3, alt = 21 * s * 1.3;
  const fimW = Math.max(larguraTexto(c.A.sigla, 26 * s, 700), larguraTexto(c.B.sigla, 26 * s, 700)) + 16 * s;
  let plot: Caixa;
  let Pl: Plano;
  const dest = spec.destaque === false ? null : spec.destaque === "auto" || spec.destaque === undefined
    ? destaqueAuto(D, d0, d1) : { ...spec.destaque, ganho: interp(D.grade_d, D.delta, spec.destaque.d1) - interp(D.grade_d, D.delta, spec.destaque.d0) };
  if (!temDelta) {
    const vs = ids.flatMap((i) => [c.A.vel[i], c.B.vel[i]]);
    const st = passoTick(Math.min(...vs), Math.max(...vs));
    const v0 = Math.floor((Math.min(...vs) - st * 0.3) / st) * st, v1 = Math.ceil((Math.max(...vs) + st * 0.3) / st) * st;
    const ylw = Math.max(...ticks(v0, v1).map((v) => larguraTexto(fmt(v), 20 * s, 400)), larguraTexto("km/h", 20 * s, 600));
    plot = { x: area.x + pad + ylw + 12 * s, y: yTop + fil * alt + 22 * s, w: 0, h: 0 };
    plot.w = area.x + area.w - pad - fimW - (mapaW ? mapaW + pad : 0) - plot.x;
    plot.h = yBot - 70 * s - plot.y;
    Pl = plano(c, plot, d0, d1, v0, v1, "velocidade (km/h)", "km/h", (v) => fmt(v), fil);
  } else {
    const vs = ids.map((i) => -D.delta[i]);
    // faixa assimétrica (não desperdiça metade do gráfico), mas cada lado com ≥ 22% para caber o rótulo da região
    let hi = Math.max(0.02, ...vs) * 1.08, lo = Math.min(-0.02, ...vs) * 1.08;
    hi = Math.max(hi, -lo * 0.22); lo = Math.min(lo, -hi * 0.22);
    const st = passoTick(lo, hi, 5);
    const v1 = Math.ceil(hi / st - 1e-9) * st, v0 = Math.floor(lo / st + 1e-9) * st;
    const ylw = Math.max(...ticks(v0, v1, 5).map((v) => larguraTexto(fmt(Math.abs(v), 2) + " s", 20 * s, 400)), larguraTexto("vantagem", 20 * s, 600));
    plot = { x: area.x + pad + ylw + 12 * s, y: yTop + fil * alt + 22 * s, w: 0, h: 0 };
    const rotW = Math.max(larguraTexto(`${c.A.sigla} à frente`, 24 * s, 700), larguraTexto(`${c.B.sigla} à frente`, 24 * s, 700));
    plot.w = area.x + area.w - pad - Math.max(fimW, rotW * 0) - (mapaW ? mapaW + pad : 0) - plot.x;
    plot.h = yBot - 70 * s - plot.y;
    Pl = plano(c, plot, d0, d1, v0, v1, "vantagem (s)", "vantagem", (v) => (v === 0 ? "0" : fmt(Math.abs(v), 2) + " s"), fil, st);
  }
  c.cursor = { ritmo: Pl.ritmo, x0: plot.x, x1: plot.x + plot.w, d0, d1 };
  c.plot = plot;
  const emDest = spec.destaqueEm ?? Pl.tFim + 0.3;
  // destaque: faixa clara de fundo (antes das linhas, para ficar atrás)
  if (dest) {
    const xa = Pl.xOf(dest.d0), xb = Pl.xOf(dest.d1);
    c.els.unshift({ id: `${spec.id}:destaque-faixa`, grafico: spec.id, papel: "destaque", tipo: "ret", x: xa, y: plot.y, w: xb - xa, h: plot.h,
      cor: T.destaque, opac: T.nome === "claro" ? 0.1 : 0.16, em: emDest, dur: 0.3, revela: "fade" });
    const g = textoGanho(c, dest.ganho);
    const tx = (dest as { texto?: string }).texto ?? g.texto;
    // o rótulo do destaque fica DENTRO da faixa, no canto de cima, se couber; senão na fileira livre acima
    const tam = 24 * s, w = larguraTexto(tx, tam, 700);
    const xc = lim((xa + xb) / 2, plot.x + w / 2, plot.x + plot.w - w / 2);
    const livre = [0, 1, 2].map((r) => plot.y - 16 * s - r * alt);
    let ok = false;
    for (const y of livre) {
      const cx = caixaTexto(xc, y, tx, tam, 700, "middle");
      if (c.cabe(cx)) { c.t("destaque-rotulo", "destaque", xc, y, tx, tam, 700, g.cor, "middle", emDest + 0.15); ok = true; break; }
    }
    if (!ok) {
      // tira o rótulo de curva que estiver no caminho (o destaque é mais importante)
      const y = livre[0], cx = caixaTexto(xc, y, tx, tam, 700, "middle");
      const tirar = c.els.filter((e) => e.tipo === "texto" && e.papel === "rotulo" && cruza(e.caixa, cx, 6 * s)) as ElTexto[];
      for (const e of tirar) { c.els.splice(c.els.indexOf(e), 1); c.textos.splice(c.textos.indexOf(e.caixa), 1); c.avisos.push(`rótulo "${e.texto}" cedeu lugar ao destaque`); }
      c.t("destaque-rotulo", "destaque", xc, y, tx, tam, 700, g.cor, "middle", emDest + 0.15);
    }
  }
  if (!temDelta) {
    const pa = serie(Pl, c.A, "vel", ids), pb = serie(Pl, c.B, "vel", ids);
    if (dest) {
      // entre as duas curvas no trecho destacado: cor de quem ganhou
      const sel = ids.filter((i) => D.grade_d[i] >= dest.d0 && D.grade_d[i] <= dest.d1);
      const sup: Pt[] = sel.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(Math.max(c.A.vel[i], c.B.vel[i]))]);
      const inf: Pt[] = sel.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(Math.min(c.A.vel[i], c.B.vel[i]))]);
      c.els.push({ id: `${spec.id}:destaque-entre`, grafico: spec.id, papel: "destaque", tipo: "area", sup, inf,
        cor: dest.ganho < 0 ? c.corA : c.corB, opac: 0.3, em: emDest + 0.1, dur: 0.35, revela: "fade" });
    }
    c.linha("serie-b", "dado", pb, c.corB, 4.5 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: c.B.sigla, campo: "vel" } });
    c.linha("serie-a", "dado", pa, c.corA, 4.5 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: c.A.sigla, campo: "vel" } });
    const il = ids[ids.length - 1];
    c.rotulosFim([{ id: "fim-a", y: Pl.yOf(c.A.vel[il]), texto: c.A.sigla, cor: c.corA }, { id: "fim-b", y: Pl.yOf(c.B.vel[il]), texto: c.B.sigla, cor: c.corB }],
      plot.x + plot.w + 12 * s, 26 * s, Pl.tFim, plot.y, plot.y + plot.h);
  } else {
    // delta: positivo para cima = A à frente; preenchimento na cor de quem está à frente
    const v = (i: number) => -D.delta[i];
    const lin: Pt[] = ids.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(v(i))]);
    const zero = Pl.yOf(0);
    c.els.push({ id: `${spec.id}:area-a`, grafico: spec.id, papel: "dado", tipo: "area", sup: lin.map(([x, y]) => [x, Math.min(y, zero)] as Pt),
      inf: lin.map(([x]) => [x, zero] as Pt), cor: c.corA, opac: 0.28, em: Pl.tDados, dur: Pl.tFim - Pl.tDados, revela: "cursor" });
    c.els.push({ id: `${spec.id}:area-b`, grafico: spec.id, papel: "dado", tipo: "area", sup: lin.map(([x]) => [x, zero] as Pt),
      inf: lin.map(([x, y]) => [x, Math.max(y, zero)] as Pt), cor: c.corB, opac: 0.28, em: Pl.tDados, dur: Pl.tFim - Pl.tDados, revela: "cursor" });
    c.linha("serie-delta", "dado", lin, T.tinta, 4 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: `${c.A.sigla}-${c.B.sigla}`, campo: "vantagem" } });
    // rótulos das regiões, dentro do gráfico, onde não há linha
    for (const [k, P, cor, sinal] of [["a", c.A, c.corA, 1], ["b", c.B, c.corB, -1]] as const) {
      const tx = `${P.sigla} à frente`;
      const y = sinal > 0 ? plot.y + 34 * s : plot.y + plot.h - 14 * s;
      const cands = [plot.x + 16 * s, plot.x + plot.w * 0.25, plot.x + plot.w * 0.5, plot.x + plot.w * 0.75];
      let ok = false;
      for (const x of cands) {
        const cx = caixaTexto(x, y, tx, 24 * s, 700, "start");
        const bate = lin.some(([px, py]) => px >= cx.x - 6 && px <= cx.x + cx.w + 6 && py >= cx.y - 6 && py <= cx.y + cx.h + 6);
        if (!bate && c.cabe(cx) && cx.x + cx.w <= plot.x + plot.w) { c.t(`regiao-${k}`, "legenda", x, y, tx, 24 * s, 700, cor, "start", c.spec.em + 0.3); ok = true; break; }
      }
      if (!ok) c.avisos.push(`rótulo da região "${tx}" sem espaço`);
    }
    const fimV = v(ids[ids.length - 1]);
    const quem = fimV > 0 ? c.A : c.B;
    const txf = `${fmt(Math.abs(fimV), 3)} s`;
    c.rotulosFim([{ id: "fim-delta", y: Pl.yOf(fimV), texto: txf, cor: fimV > 0 ? c.corA : c.corB }], plot.x + plot.w + 12 * s, 22 * s, Pl.tFim, plot.y, plot.y + plot.h);
    void quem;
  }
  if (spec.minimapa) {
    const mx = area.x + area.w - pad - mapaW;
    minimapa(c, { x: mx, y: plot.y, w: mapaW, h: Math.min(plot.h, mapaW * 1.1) }, dest, emDest);
    c.t("mapa-rotulo", "rotulo", mx + mapaW / 2, plot.y + Math.min(plot.h, mapaW * 1.1) + 26 * s, dest ? "trecho destacado" : (c.D.circuito ?? ""),
      19 * s, 600, dest ? T.destaque : T.tinta2, "middle", emDest + 0.15);
  }
}

// ------------------------------------------------------------------------------------------------ 2. setores (delta por setor)
function grafSetores(c: Construtor) {
  const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
  const yTop = c.cabecalho(spec.titulo ?? "Onde a volta foi ganha", spec.subtitulo ?? "Diferença de tempo em cada setor (OpenF1, tempos oficiais de setor)", false);
  const yBot = c.rodape();
  const linhas = c.A.setores.map((a, k) => ({ rot: `Setor ${k + 1}`, a, b: c.B.setores[k] }));
  linhas.push({ rot: "Volta", a: c.A.tempo, b: c.B.tempo });
  const tamR = 30 * s, tamV = 28 * s, tamP = 20 * s;
  const rotW = Math.max(...linhas.map((l) => larguraTexto(l.rot, tamR, 700))) + 24 * s;
  const xc = area.x + pad + rotW + (area.w - 2 * pad - rotW) / 2;  // centro (zero)
  const meio = (area.w - 2 * pad - rotW) / 2;
  const valW = larguraTexto("0,000 s", tamV, 700) + 18 * s;
  const maxD = Math.max(...linhas.map((l) => Math.abs(l.a - l.b)), 0.05);
  const st = passoTick(0, maxD, 3);
  const top = Math.ceil((maxD * 1.02) / st) * st;
  const escala = (meio - valW) / top; // px por segundo
  // cabeçalho das duas metades
  const yH = yTop + 34 * s;
  c.t("lado-a", "legenda", xc - 18 * s, yH, `◀ ${c.A.sigla} mais rápido`, 26 * s, 700, c.corA, "end", em + 0.15);
  c.t("lado-b", "legenda", xc + 18 * s, yH, `${c.B.sigla} mais rápido ▶`, 26 * s, 700, c.corB, "start", em + 0.15);
  const y0 = yH + 34 * s, y1 = yBot - 56 * s;
  const passo = (y1 - y0) / linhas.length, barH = Math.min(58 * s, passo * 0.42);
  c.eixos.push({ d0: -top, d1: top, x0: xc - top * escala, x1: xc + top * escala, v0: 0, v1: 0, y0, y1, nome: "segundos (setores)" });
  // grade vertical simétrica + ticks
  for (let v = 0; v <= top + 1e-9; v += st) {
    for (const sg of v === 0 ? [1] : [-1, 1]) {
      const x = xc + sg * v * escala;
      c.linha(`grade-${sg}-${v.toFixed(3)}`, v === 0 ? "eixo" : "grade", [[x, y0], [x, y1]], v === 0 ? T.eixo : T.grade, (v === 0 ? 2.5 : 1.5) * s, em + 0.1, 0.4, "comp");
      c.t(`tick-${sg}-${v.toFixed(3)}`, "eixo", x, y1 + 28 * s, v === 0 ? "0" : `${fmt(v, 2)} s`, 20 * s, 400, T.tinta2, "middle", em + 0.25);
    }
  }
  linhas.forEach((l, k) => {
    const yc = y0 + passo * (k + 0.5), d = l.a - l.b; // d < 0: A mais rápido
    const P = d < 0 ? c.A : c.B, cor = d < 0 ? c.corA : c.corB, w = Math.abs(d) * escala;
    const emB = em + 0.6 + k * 0.45;
    const volta = l.rot === "Volta";
    if (volta) c.linha("sep-volta", "grade", [[area.x + pad, yc - passo / 2], [area.x + area.w - pad, yc - passo / 2]], T.grade, 2 * s, em + 0.1, 0.4, "x");
    c.t(`rot-${k}`, "rotulo", area.x + pad, yc + 10 * s, l.rot, tamR, 700, T.tinta, "start", emB - 0.2);
    const x = d < 0 ? xc - w : xc;
    c.ret(`barra-${k}`, "dado", x, yc - barH / 2, w, barH, cor, 1, emB, 0.5, d < 0 ? "esq" : "dir", { valor: Math.abs(d), escala, raio: 4 * s });
    const vx = d < 0 ? x - 12 * s : x + w + 12 * s;
    c.t(`val-${k}`, "valor", vx, yc + 10 * s, `${fmt(Math.abs(d), 3)} s`, tamV, 700, cor, d < 0 ? "end" : "start", emB + 0.5);
    c.t(`tempos-${k}`, "rotulo", area.x + pad, yc + 10 * s + 30 * s, `${c.A.sigla} ${fmt(l.a, 3)} · ${c.B.sigla} ${fmt(l.b, 3)}`, tamP, 400, T.tinta2, "start", emB - 0.2);
    void P;
  });
  c.cursor = null; c.plot = { x: xc - meio, y: y0, w: 2 * meio, h: y1 - y0 };
}

// ------------------------------------------------------------------------------------------------ 3. telemetria (acelerador / freio / marcha)
function grafTelemetria(c: Construtor) {
  const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
  const [d0, d1] = spec.trecho ?? [0, D.comprimento_m];
  const ids = indices(D, d0, d1);
  const paineis = spec.paineis ?? ["acelerador", "freio", "marcha"];
  const yTop = c.cabecalho(spec.titulo ?? "Acelerador, freio e marcha", spec.subtitulo ?? `${fmt(d0)}–${fmt(d1)} m da volta`, true);
  const yBot = c.rodape();
  const tamP = 22 * s;
  const nomeW = Math.max(...["Acelerador", "Velocidade", "Freio", "Marcha"].map((n) => larguraTexto(n, tamP, 700))) + 12 * s;
  const tickW = larguraTexto("100 %", 20 * s, 400) + 10 * s;
  const fimW = Math.max(larguraTexto(c.A.sigla, 22 * s, 700), larguraTexto(c.B.sigla, 22 * s, 700)) + 16 * s;
  const x0 = area.x + pad + nomeW + tickW, x1 = area.x + area.w - pad - fimW;
  const fil = 2, alt = 21 * s * 1.3;
  const yA = yTop + fil * alt + 26 * s, yB = yBot - 70 * s;
  const pesos: Record<string, number> = { acelerador: 1, velocidade: 1, marcha: 0.8, freio: 0.42 };
  const gap = 34 * s, tot = paineis.reduce((a, p) => a + pesos[p], 0), hUtil = yB - yA - gap * (paineis.length - 1);
  // eixo x e curvas usam o primeiro painel como plano e a base do último
  let y = yA;
  let primeiro: Plano | null = null;
  const plot: Caixa = { x: x0, y: yA, w: x1 - x0, h: yB - yA };
  const xOf = (d: number) => x0 + ((d - d0) / (d1 - d0)) * (x1 - x0);
  // ritmo / cursor comum
  const tDados = spec.ritmo?.[0]?.t ?? em + 0.55;
  const ritmo = ritmoDe(spec, d0, d1, tDados), tFim = ritmo[ritmo.length - 1].t;
  paineis.forEach((p, k) => {
    const h = (hUtil * pesos[p]) / tot;
    const caixa: Caixa = { x: x0, y, w: x1 - x0, h };
    const nomes: Record<string, string> = { acelerador: "Acelerador", velocidade: "Velocidade", marcha: "Marcha", freio: "Freio" };
    c.t(`painel-${p}`, "rotulo", area.x + pad, y + 22 * s, nomes[p], tamP, 700, T.tinta, "start", em + 0.2);
    if (p === "freio") {
      const fh = Math.min(16 * s, h / 3);
      [[c.A, c.corA, 0], [c.B, c.corB, 1]].forEach(([P, cor, j]) => {
        const Pi = P as Piloto, yy = y + h * (j === 0 ? 0.3 : 0.72) - fh / 2;
        c.linha(`freio-base-${j}`, "grade", [[x0, yy + fh / 2], [x1, yy + fh / 2]], T.grade, 1.5 * s, em + 0.1, 0.4, "x");
        c.t(`freio-sigla-${j}`, "rotulo", x0 - 10 * s, yy + fh / 2 + 7 * s, Pi.sigla, 19 * s, 700, cor as string, "end", em + 0.2);
        // trechos contínuos de freio = retângulos
        let ini = -1;
        ids.forEach((i, q) => {
          const on = Pi.freio[i] > 0;
          if (on && ini < 0) ini = i;
          if (ini >= 0 && (!on || q === ids.length - 1)) {
            const fim = on ? i : ids[q - 1];
            const xa = xOf(D.grade_d[ini]), xb = Math.max(xOf(D.grade_d[fim]), xa + 2 * s);
            c.ret(`freio-${j}-${ini}`, "dado", xa, yy, xb - xa, fh, cor as string, 1, tDados, tFim - tDados, "cursor",
              { valor: (D.grade_d[fim] - D.grade_d[ini]), raio: 3 * s });
            ini = -1;
          }
        });
      });
      c.eixos.push({ d0, d1, x0, x1, v0: 0, v1: 1, y0: y + h, y1: y, nome: "freio" });
    } else {
      const cfg = p === "acelerador" ? { v0: 0, v1: 100, ticks: [0, 50, 100], f: (v: number) => `${v} %`, campo: "acel" as const, degrau: false }
        : p === "marcha" ? (() => { const mx = Math.max(...ids.flatMap((i) => [c.A.marcha[i], c.B.marcha[i]]), 2), mn = Math.min(...ids.flatMap((i) => [c.A.marcha[i], c.B.marcha[i]]));
            const tk: number[] = []; for (let g = Math.max(1, mn); g <= mx; g++) if (mx - mn <= 4 || g % 2 === 0) tk.push(g);
            return { v0: Math.max(0, mn - 0.6), v1: mx + 0.6, ticks: tk, f: (v: number) => `${v}ª`, campo: "marcha" as const, degrau: true }; })()
        : (() => { const vs = ids.flatMap((i) => [c.A.vel[i], c.B.vel[i]]); const st = passoTick(Math.min(...vs), Math.max(...vs), 3);
            const a = Math.floor(Math.min(...vs) / st) * st, b = Math.ceil(Math.max(...vs) / st) * st;
            return { v0: a, v1: b, ticks: ticks(a, b, 3), f: (v: number) => fmt(v), campo: "vel" as const, degrau: false }; })();
      const yOf = (v: number) => y + h - ((v - cfg.v0) / (cfg.v1 - cfg.v0)) * h;
      for (const v of cfg.ticks) {
        c.linha(`grade-${p}-${v}`, "grade", [[x0, yOf(v)], [x1, yOf(v)]], T.grade, 1.5 * s, em + 0.1, 0.4, "x");
        c.t(`tick-${p}-${v}`, "eixo", x0 - 10 * s, yOf(v) + 7 * s, cfg.f(v), 19 * s, 400, T.tinta2, "end", em + 0.25);
      }
      const P: Plano = { c, plot: caixa, d0, d1, v0: cfg.v0, v1: cfg.v1, xOf, yOf, tDados, tFim, ritmo, tEm: (d) => tempoEm(ritmo, d) };
      c.eixos.push({ d0, d1, x0, x1, v0: cfg.v0, v1: cfg.v1, y0: yOf(cfg.v0), y1: yOf(cfg.v1), nome: p });
      const pb = serie(P, c.B, cfg.campo, ids, cfg.degrau), pa = serie(P, c.A, cfg.campo, ids, cfg.degrau);
      c.linha(`serie-${p}-b`, "dado", pb, c.corB, 3.5 * s, tDados, tFim - tDados, "cursor", { serie: { piloto: c.B.sigla, campo: cfg.campo, degrau: cfg.degrau } });
      c.linha(`serie-${p}-a`, "dado", pa, c.corA, 3.5 * s, tDados, tFim - tDados, "cursor", { serie: { piloto: c.A.sigla, campo: cfg.campo, degrau: cfg.degrau } });
      const il = ids[ids.length - 1];
      c.rotulosFim([{ id: `fim-${p}-a`, y: yOf(c.A[cfg.campo][il]), texto: c.A.sigla, cor: c.corA }, { id: `fim-${p}-b`, y: yOf(c.B[cfg.campo][il]), texto: c.B.sigla, cor: c.corB }],
        x1 + 10 * s, 22 * s, tFim, y, y + h);
      if (!primeiro) primeiro = P;
    }
    y += h + gap;
  });
  // eixo x embaixo + curvas e setores em cima (linhas atravessando todos os painéis)
  c.linha("base-x", "eixo", [[x0, yB], [x1, yB]], T.eixo, 2 * s, em + 0.1, 0.45, "x");
  const px = passoTick(d0, d1, Math.max(3, Math.round((x1 - x0) / 260)));
  for (let d = Math.ceil(d0 / px) * px; d <= d1 + 1e-6; d += px) c.t(`tick-x-${d}`, "eixo", xOf(d), yB + 28 * s, fmt(d), 20 * s, 400, T.tinta2, "middle", em + 0.25);
  c.t("unidade-x", "eixo", x1, yB + 58 * s, "distância na volta (m)", 20 * s, 600, T.tinta2, "end", em + 0.25);
  const rot: Parameters<Construtor["fileiras"]>[0] = [];
  for (const k of D.curvas.filter((q) => q.nome && q.d > d0 && q.d < d1 && (Array.isArray(spec.curvas) ? spec.curvas.includes(q.n) : spec.curvas !== false))) {
    const tk = tempoEm(ritmo, k.d);
    rot.push({ id: `curva-${k.n}`, x: xOf(k.d), texto: k.nome, cor: T.tinta, peso: 600, em: tk });
    c.linha(`curva-linha-${k.n}`, "grade", [[xOf(k.d), yA - 4 * s], [xOf(k.d), yB]], T.grade, 2 * s, tk, 0.25, "comp", { tracejado: `${3 * s} ${6 * s}` });
  }
  if (spec.setores !== false) D.setores_d.forEach((f, k) => {
    if (f.d <= d0 || f.d >= d1) return;
    rot.unshift({ id: `setor-fim-${k + 1}`, x: xOf(f.d), texto: `fim do setor ${k + 1}`, cor: T.tinta2, peso: 700, em: tempoEm(ritmo, f.d) });
    c.linha(`setor-linha-${k + 1}`, "grade", [[xOf(f.d), yB], [xOf(f.d), yA - 6 * s]], T.eixo, 2 * s, tempoEm(ritmo, f.d), 0.3, "comp", { tracejado: `${8 * s} ${7 * s}` });
  });
  c.fileiras(rot, yA - 16 * s, fil, 21 * s, x0, x1);
  c.cursor = { ritmo, x0, x1, d0, d1 };
  c.plot = plot;
  void primeiro;
}

// ------------------------------------------------------------------------------------------------ 4. normalizado (comparativo por métrica)
/** valor da métrica no trecho, das amostras BRUTAS do car_data (se houver) — não da grade interpolada */
export function metrica(D: Dados, P: Piloto, m: Metrica, d0: number, d1: number): number {
  const g = D.grade_d;
  if (m === "vmedia") {
    const ta = interp(g, P.t, d0), tb = interp(g, P.t, d1);
    return ((d1 - d0) / (tb - ta)) * 3.6;
  }
  const b = P.bruto ?? { t: P.t, d: g, vel: P.vel, acel: P.acel, freio: P.freio, marcha: P.marcha };
  const ids = b.d.map((d, i) => [d, i] as const).filter(([d]) => d >= d0 && d <= d1).map(([, i]) => i);
  if (m === "vmax") return Math.max(...ids.map((i) => b.vel[i]));
  if (m === "vmin") return Math.min(...ids.map((i) => b.vel[i]));
  let tot = 0, dist = 0;
  for (let q = 1; q < ids.length; q++) {
    const i = ids[q], h = ids[q - 1];
    if (m === "acelPleno") { dist += b.d[i] - b.d[h]; if (b.acel[h] >= 98 && b.acel[i] >= 98) tot += b.d[i] - b.d[h]; }
    else if (b.freio[h] > 0) tot += b.t[i] - b.t[h];
  }
  return m === "acelPleno" ? (100 * tot) / dist : tot;
}
export const METRICAS: Record<Metrica, { nome: string; unid: string; casas: number; maiorMelhor: boolean }> = {
  vmax: { nome: "Velocidade máxima", unid: "km/h", casas: 0, maiorMelhor: true },
  vmin: { nome: "Velocidade na curva mais lenta", unid: "km/h", casas: 0, maiorMelhor: true },
  vmedia: { nome: "Velocidade média", unid: "km/h", casas: 2, maiorMelhor: true },
  acelPleno: { nome: "Acelerador a fundo", unid: "% do trecho", casas: 1, maiorMelhor: true },
  freando: { nome: "Tempo pisando no freio", unid: "s", casas: 2, maiorMelhor: false },
};
/** vantagem relativa (%) de quem foi melhor: (melhor − pior) / pior, com o sentido certo para "menor é melhor" */
export function vantagem(va: number, vb: number, maiorMelhor: boolean): { pct: number; aMelhor: boolean } {
  const aMelhor = maiorMelhor ? va > vb : va < vb;
  const [m, p] = aMelhor ? [va, vb] : [vb, va];
  const pct = p === 0 ? 0 : (maiorMelhor ? (m - p) / p : (p - m) / p) * 100;
  return { pct: Math.abs(pct), aMelhor };
}
/**
 * Comparativo normalizado: métricas de unidades diferentes numa MESMA escala, a vantagem relativa em %.
 * Barra para o lado de quem foi melhor (como o gráfico de setores); embaixo do nome, os dois valores reais com unidade.
 */
function grafNormalizado(c: Construtor) {
  const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
  const [d0, d1] = spec.trecho ?? [0, D.comprimento_m];
  const ms = spec.metricas ?? ["vmax", "vmin", "vmedia", "acelPleno", "freando"];
  const yTop = c.cabecalho(spec.titulo ?? "Quem foi melhor em cada quesito",
    spec.subtitulo ?? "Medidas diferentes na mesma régua: quanto um piloto foi melhor que o outro, em % do valor do outro", false);
  const yBot = c.rodape();
  const tamN = 27 * s, tamU = 20 * s, tamV = 26 * s;
  const linhas = ms.map((m) => {
    const M = METRICAS[m], va = metrica(D, c.A, m, d0, d1), vb = metrica(D, c.B, m, d0, d1);
    const u = M.unid === "% do trecho" ? "%" : ` ${M.unid}`;
    return { m, M, va, vb, ...vantagem(va, vb, M.maiorMelhor), real: `${c.A.sigla} ${fmt(va, M.casas)}${u} · ${c.B.sigla} ${fmt(vb, M.casas)}${u}`,
      dica: M.maiorMelhor ? "maior é melhor" : "menor é melhor" };
  });
  const nomeW = Math.max(...linhas.map((l) => Math.max(larguraTexto(l.M.nome, tamN, 700), larguraTexto(l.real, tamU, 400), larguraTexto(l.dica, tamU, 400)))) + 34 * s;
  const xc = area.x + pad + nomeW + (area.w - 2 * pad - nomeW) / 2, meio = (area.w - 2 * pad - nomeW) / 2;
  const valW = larguraTexto("+00,0 %", tamV, 700) + 18 * s;
  const maxP = Math.max(...linhas.map((l) => l.pct), 0.5);
  const st = passoTick(0, maxP, 3), top = Math.ceil((maxP * 1.02) / st) * st, escala = (meio - valW) / top;
  const yH = yTop + 34 * s;
  c.t("lado-a", "legenda", xc - 18 * s, yH, `◀ ${c.A.sigla} melhor`, 26 * s, 700, c.corA, "end", em + 0.15);
  c.t("lado-b", "legenda", xc + 18 * s, yH, `${c.B.sigla} melhor ▶`, 26 * s, 700, c.corB, "start", em + 0.15);
  const y0 = yH + 30 * s, y1 = yBot - 60 * s, passo = (y1 - y0) / linhas.length, barH = Math.min(46 * s, passo * 0.36);
  for (let v = 0; v <= top + 1e-9; v += st) for (const sg of v === 0 ? [1] : [-1, 1]) {
    const x = xc + sg * v * escala;
    c.linha(`grade-${sg}-${v.toFixed(3)}`, v === 0 ? "eixo" : "grade", [[x, y0], [x, y1]], v === 0 ? T.eixo : T.grade, (v === 0 ? 2.5 : 1.5) * s, em + 0.1, 0.4, "comp");
    c.t(`tick-${sg}-${v.toFixed(3)}`, "eixo", x, y1 + 28 * s, v === 0 ? "0" : `${fmt(v, st < 1 ? 1 : 0)} %`, 20 * s, 400, T.tinta2, "middle", em + 0.25);
  }
  c.t("unidade-x", "eixo", area.x + area.w - pad, y1 + 58 * s, "vantagem relativa (% do valor do outro piloto)", 20 * s, 600, T.tinta2, "end", em + 0.25);
  c.eixos.push({ d0: -top, d1: top, x0: xc - top * escala, x1: xc + top * escala, v0: 0, v1: 0, y0, y1, nome: "vantagem relativa (%)" });
  linhas.forEach((l, k) => {
    const yc = y0 + passo * (k + 0.5), emL = em + 0.6 + k * 0.4;
    if (k > 0) c.linha(`sep-${k}`, "grade", [[area.x + pad, yc - passo / 2], [area.x + area.w - pad, yc - passo / 2]], T.grade, 1.5 * s, em + 0.1, 0.4, "x");
    c.t(`nome-${l.m}`, "rotulo", area.x + pad, yc - 6 * s, l.M.nome, tamN, 700, T.tinta, "start", emL - 0.2);
    c.t(`real-${l.m}`, "valor", area.x + pad, yc + 24 * s, l.real, tamU, 400, T.tinta2, "start", emL - 0.2);
    c.t(`dica-${l.m}`, "rotulo", area.x + pad, yc + 50 * s, l.dica, tamU, 400, T.tinta2, "start", emL - 0.2);
    const casas = l.pct < 0.095 ? 2 : 1;
    const empate = Math.abs(l.va - l.vb) < 0.5 * 10 ** -l.M.casas;
    if (empate) {
      c.t(`val-${l.m}`, "valor", xc + 14 * s, yc + 9 * s, "empate", tamV, 700, T.tinta2, "start", emL + 0.2);
      return;
    }
    const cor = l.aMelhor ? c.corA : c.corB, w = l.pct * escala, x = l.aMelhor ? xc - w : xc;
    c.ret(`barra-${l.m}`, "dado", x, yc - barH / 2, w, barH, cor, 1, emL, 0.5, l.aMelhor ? "esq" : "dir", { valor: l.pct, escala, raio: 4 * s });
    c.t(`val-${l.m}`, "valor", l.aMelhor ? x - 12 * s : x + w + 12 * s, yc + 9 * s, `+${fmt(l.pct, casas)} %`, tamV, 700, cor, l.aMelhor ? "end" : "start", emL + 0.5);
  });
  c.cursor = null; c.plot = { x: xc - meio, y: y0, w: 2 * meio, h: y1 - y0 };
}

// ------------------------------------------------------------------------------------------------ montar / estado
export function montar(specs: Spec[], dados: Dados, larguras: Larguras): Montado {
  LARG = larguras;
  const graficos: Grafico[] = [];
  for (const spec of specs) {
    const c = new Construtor(spec, dados);
    if (spec.tipo === "velocidade") grafVelocidade(c);
    else if (spec.tipo === "delta") grafVelocidade(c, true);
    else if (spec.tipo === "setores") grafSetores(c);
    else if (spec.tipo === "telemetria") grafTelemetria(c);
    else if (spec.tipo === "normalizado") grafNormalizado(c);
    const fim = Math.max(...c.els.map((e) => e.em + e.dur));
    graficos.push({ spec, tema: c.tema, elementos: c.els, eixos: c.eixos, plot: c.plot, cursor: c.cursor, fim, avisos: c.avisos });
  }
  return { graficos, avisos: graficos.flatMap((g) => g.avisos.map((a) => `${g.spec.id}: ${a}`)), fonteCss: FONTE_CSS };
}

function caminho(pts: Pt[], fechar = false): string {
  if (!pts.length) return "";
  let d = `M${pts[0][0].toFixed(2)} ${pts[0][1].toFixed(2)}`;
  for (let i = 1; i < pts.length; i++) d += `L${pts[i][0].toFixed(2)} ${pts[i][1].toFixed(2)}`;
  return fechar ? d + "Z" : d;
}
/** pontos com x ≤ xc, com o último ponto interpolado exatamente em xc (o desenho avança junto do cursor) */
function cortaX(pts: Pt[], xc: number): Pt[] {
  if (!pts.length || xc < pts[0][0]) return [];
  const out: Pt[] = [];
  for (let i = 0; i < pts.length; i++) {
    if (pts[i][0] <= xc) { out.push(pts[i]); continue; }
    const a = pts[i - 1], b = pts[i];
    if (a && b[0] > a[0]) out.push([xc, a[1] + ((b[1] - a[1]) * (xc - a[0])) / (b[0] - a[0])]);
    break;
  }
  return out;
}
function cortaComp(pts: Pt[], k: number): Pt[] {
  if (k <= 0 || pts.length < 2) return [];
  if (k >= 1) return pts;
  const L = [0];
  for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const alvo = k * L[L.length - 1], out: Pt[] = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    if (L[i] <= alvo) { out.push(pts[i]); continue; }
    const u = (alvo - L[i - 1]) / (L[i] - L[i - 1]);
    out.push([pts[i - 1][0] + u * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + u * (pts[i][1] - pts[i - 1][1])]);
    break;
  }
  return out;
}
function retPath(x: number, y: number, w: number, h: number, r = 0): string {
  if (w <= 0.01 || h <= 0.01) return "";
  r = Math.min(r, w / 2, h / 2);
  if (r <= 0) return `M${x} ${y}h${w}v${h}h${-w}Z`;
  return `M${x + r} ${y}h${w - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}v${h - 2 * r}a${r} ${r} 0 0 1 ${-r} ${r}h${-(w - 2 * r)}a${r} ${r} 0 0 1 ${-r} ${-r}v${-(h - 2 * r)}a${r} ${r} 0 0 1 ${r} ${-r}Z`;
}

/** o que desenhar no tempo t (s). Antes de `em` de cada elemento, nada; depois do fim, o gráfico completo e parado. */
export function estado(m: Montado, t: number): Desenho[] {
  const out: Desenho[] = [];
  for (const g of m.graficos) {
    if (g.spec.ate !== undefined && t >= g.spec.ate) continue;
    const xc = g.cursor ? g.cursor.x0 + ((distCursor(g.cursor.ritmo, t) - g.cursor.d0) / (g.cursor.d1 - g.cursor.d0)) * (g.cursor.x1 - g.cursor.x0) : Infinity;
    const cursorOn = g.cursor ? t >= g.cursor.ritmo[0].t : true;
    for (const e of g.elementos) {
      if (t < e.em) continue;
      const k = e.dur > 0 ? lim((t - e.em) / e.dur, 0, 1) : 1;
      if (e.tipo === "texto") {
        out.push({ id: e.id, tipo: "texto", x: e.x, y: e.y, texto: e.texto, tam: e.tam, peso: e.peso, cor: e.cor, ancora: e.ancora, opac: k });
      } else if (e.tipo === "linha") {
        let pts: Pt[];
        if (e.revela === "cursor") pts = cursorOn ? cortaX(e.pts, xc) : [];
        else if (e.revela === "x") { const xa = e.pts[0][0], xb = e.pts[e.pts.length - 1][0]; pts = xb > xa ? cortaX(e.pts, xa + suave(k) * (xb - xa)) : cortaComp(e.pts, suave(k)); }
        else pts = cortaComp(e.pts, suave(k));
        if (pts.length >= 2) out.push({ id: e.id, tipo: "path", d: caminho(pts), stroke: e.cor, largura: e.largura, opac: 1, tracejado: e.tracejado });
      } else if (e.tipo === "area") {
        let sup = e.sup, inf = e.inf, op = e.opac;
        if (e.revela === "cursor") { sup = cortaX(sup, xc); inf = cortaX(inf, xc); } else op *= k;
        if (sup.length >= 2) out.push({ id: e.id, tipo: "path", d: caminho([...sup, ...inf.slice().reverse()], true), fill: e.cor, opac: op });
      } else {
        let { x, y, w, h } = e, op = e.opac;
        const kk = suave(k);
        if (e.revela === "dir") w *= kk;
        else if (e.revela === "esq") { x += w * (1 - kk); w *= kk; }
        else if (e.revela === "cima") { y += h * (1 - kk); h *= kk; }
        else if (e.revela === "cursor") w = lim(xc - x, 0, w);
        else op *= k;
        const d = retPath(x, y, w, h, e.raio ?? 0);
        if (d) out.push({ id: e.id, tipo: "path", d, fill: e.cor, opac: op });
      }
    }
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ verificação geométrica
export type Relatorio = { falhas: string[]; avisos: string[]; graficos: Record<string, { elementos: number; textos: number; fim: number;
  menorFolgaTextos: number; foraDaArea: number }> };
/** confere, sem motor: tudo dentro da área; textos sem sobreposição (folga ≥ 4 px) nem sobre linhas de dados; fim do desenho */
export function checar(m: Montado): Relatorio {
  const falhas: string[] = [], rel: Relatorio["graficos"] = {};
  for (const g of m.graficos) {
    const a = g.spec.area, id = g.spec.id;
    const dentro = (x: number, y: number, tol = 0.5) => x >= a.x - tol && x <= a.x + a.w + tol && y >= a.y - tol && y <= a.y + a.h + tol;
    let fora = 0;
    const textos = g.elementos.filter((e): e is ElTexto => e.tipo === "texto");
    for (const e of g.elementos) {
      const meia = e.tipo === "linha" ? e.largura / 2 : 0;
      const pts: Pt[] = e.tipo === "linha" ? e.pts : e.tipo === "area" ? [...e.sup, ...e.inf]
        : e.tipo === "ret" ? [[e.x, e.y], [e.x + e.w, e.y + e.h]] : [[e.caixa.x, e.caixa.y], [e.caixa.x + e.caixa.w, e.caixa.y + e.caixa.h]];
      const ruins = pts.filter(([x, y]) => !(dentro(x - meia, y - meia) && dentro(x + meia, y + meia)));
      if (ruins.length) { fora++; falhas.push(`${e.id}: ${ruins.length} ponto(s) fora da área`); }
      if ([...pts.flat()].some((v) => !Number.isFinite(v))) falhas.push(`${e.id}: coordenada não finita`);
    }
    let menor = Infinity;
    for (let i = 0; i < textos.length; i++) for (let j = i + 1; j < textos.length; j++) {
      const p = textos[i].caixa, q = textos[j].caixa;
      const dx = Math.max(q.x - (p.x + p.w), p.x - (q.x + q.w)), dy = Math.max(q.y - (p.y + p.h), p.y - (q.y + q.h));
      const folga = Math.max(dx, dy);
      menor = Math.min(menor, folga);
      if (folga < 4) falhas.push(`textos se sobrepõem: "${textos[i].texto}" × "${textos[j].texto}" (folga ${folga.toFixed(1)} px)`);
    }
    for (const tx of textos) for (const e of g.elementos) {
      if (e.tipo !== "linha" || e.papel !== "dado") continue;
      const c = tx.caixa, hit = e.pts.some(([x, y]) => x > c.x - 2 && x < c.x + c.w + 2 && y > c.y - 2 && y < c.y + c.h + 2);
      if (hit) falhas.push(`texto "${tx.texto}" sobre a linha de dados ${e.id}`);
    }
    // o desenho termina e é monotônico (cursor nunca volta)
    if (g.cursor) {
      const r = g.cursor.ritmo;
      for (let i = 1; i < r.length; i++) if (r[i].t < r[i - 1].t || r[i].d < r[i - 1].d) falhas.push(`${id}: ritmo volta no tempo ou na distância (${i})`);
      if (Math.abs(distCursor(r, g.fim + 1) - g.cursor.d1) > 1e-6) falhas.push(`${id}: desenho não chega ao fim do trecho`);
    }
    const final = estado({ ...m, graficos: [g] }, g.fim + 0.01);
    const vistos = new Set(final.map((d) => d.id));
    const faltam = g.elementos.filter((e) => !vistos.has(e.id) && !(e.tipo === "ret" && e.w <= 0.01));
    if (faltam.length) falhas.push(`${id}: ${faltam.length} elemento(s) não aparecem no fim: ${faltam.slice(0, 3).map((e) => e.id).join(", ")}`);
    rel[id] = { elementos: g.elementos.length, textos: textos.length, fim: +g.fim.toFixed(3), menorFolgaTextos: +menor.toFixed(1), foraDaArea: fora };
  }
  return { falhas, avisos: m.avisos, graficos: rel };
}
