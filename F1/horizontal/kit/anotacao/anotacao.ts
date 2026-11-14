// kit/anotacao — anotações à mão do horizontal, independentes de motor (Remotion, HyperFrames, Node, testes).
//
// Regra central (defeito do teste Remotion: "círculos pulando"): a geometria de cada anotação é calculada UMA vez,
// nas coordenadas locais da sua âncora, a partir de uma CAIXA ESTÁVEL (tamanho fixo). Ao longo do tempo a âncora só
// desloca (dx, dy) e, se a cena pedir, escala de forma suave (s). Nunca se mede de novo a caixa projetada de uma peça
// que gira: é isso que fazia o oval crescer e encolher. Para peça 3D/girando, `caixaEnvelope` dá a caixa estável
// (o maior meio-tamanho ao redor do pivô em todo o intervalo).
//
// Traço: polilinha com ondulação lenta e determinística (semente) → curva lisa (Catmull-Rom). Desenho progressivo por
// stroke-dashoffset com pathLength=1 (o motor não precisa medir o caminho). Texto à mão: linhas centrais dos glifos da
// Caveat 700 (dados em fonte/caveat_traco.json) reveladas em ordem de escrita, como máscara sobre o contorno cheio.
//
// TypeScript só com tipos apagáveis: roda direto no Node 24 (`node arquivo.ts`), no Remotion (webpack) e vira
// anotacao.global.js (esbuild, IIFE window.Anotacao) para o HyperFrames.

export type P = [number, number];
/** Caixa em px: canto superior esquerdo + tamanho. */
export type Caixa = { x: number; y: number; w: number; h: number };
export type Chave = { t: number; dx: number; dy: number; s?: number };
export type Alvo = {
  /** caixa ESTÁVEL na pose de referência (deslocamento 0) */
  caixa: Caixa;
  /** true = texto da cena: nenhuma anotação pode cruzar (exceto riscado/corrigido sobre ele mesmo) */
  texto?: boolean;
  /** trilha da âncora (deslocamento do centro e escala); interpolação Catmull-Rom; sem trilha = parado */
  movimento?: Chave[];
};

type Base = {
  id: string;
  /** início (s) */
  em: number;
  cor?: string;
  /** px */
  espessura?: number;
  semente?: number;
  /** velocidade da caneta em px/s (padrão por tipo) */
  vel?: number;
};
export type Lado = "cima" | "baixo" | "esquerda" | "direita";
export type Anotacao =
  | (Base & { tipo: "oval"; alvo: string; folga?: number; giro?: number })
  | (Base & { tipo: "seta"; de: string; para: string; recuo?: number; curva?: number })
  | (Base & { tipo: "sublinhado"; alvo: string; folga?: number })
  | (Base & { tipo: "chave"; alvos: string[]; lado?: Lado; folga?: number; ponta?: number })
  | (Base & { tipo: "riscado"; alvo: string; duplo?: boolean })
  | (Base & { tipo: "nota"; texto: string; tamanho?: number; pos?: P; perto?: { alvo: string; lado: Lado | "auto"; distancia?: number; desloc?: P } })
  | (Base & { tipo: "corrigido"; alvo: string; texto: string; tamanho?: number; lado?: Lado });

export type Cena = {
  largura: number;
  altura: number;
  fps: number;
  duracao: number;
  alvos: Record<string, Alvo>;
  anotacoes: Anotacao[];
};

/** Dados de fonte/caveat_traco.json (unidades de glifo: upem 1000, y para baixo, linha de base em 0). */
export type Fonte = {
  meta: { upem: number; ascent: number; descent: number };
  glyphs: Record<string, { adv: number; outline: string; stem: number; strokes: string[] }>;
};

// ---------------------------------------------------------------- padrões
export const COR = "#d40000";
export const ESPESSURA = 7;
const VEL = { oval: 2600, seta: 2400, sublinhado: 2200, chave: 1800, riscado: 2200, texto: 1150 } as const;
const LEVANTA = 0.05; // s entre traços (caneta levanta)
const LEVANTA_LETRA = 0.03;
const ESPACO = 300; // avanço do espaço em unidades de glifo

// ---------------------------------------------------------------- utilidades
export function aleatorio(semente: number): () => number {
  let a = (semente | 0) ^ 0x9e3779b9;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashTexto(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193);
  return h >>> 0;
}
const f1 = (v: number) => (Math.round(v * 10) / 10).toString();
const dist = (a: P, b: P) => Math.hypot(b[0] - a[0], b[1] - a[1]);
export function comprimento(pts: P[]): number {
  let s = 0;
  for (let i = 1; i < pts.length; i++) s += dist(pts[i - 1], pts[i]);
  return s;
}
/** Curva lisa (Catmull-Rom uniforme → cúbicas) pelos pontos. */
export function liso(q: P[]): string {
  let d = `M ${f1(q[0][0])} ${f1(q[0][1])}`;
  for (let i = 0; i < q.length - 1; i++) {
    const p0 = q[Math.max(0, i - 1)], p1 = q[i], p2 = q[i + 1], p3 = q[Math.min(q.length - 1, i + 2)];
    d += ` C ${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`;
  }
  return d;
}
/** Achata um caminho SVG absoluto (M L Q C Z) em polilinhas. */
export function achatar(d: string, passos = 10): P[][] {
  const tk = d.match(/[MLQCZ]|-?\d*\.?\d+(?:e-?\d+)?/gi) || [];
  const out: P[][] = [];
  let cur: P[] = [], i = 0, cmd = "", x = 0, y = 0, x0 = 0, y0 = 0;
  const n = () => parseFloat(tk[i++]);
  while (i < tk.length) {
    if (/[A-Za-z]/.test(tk[i])) cmd = tk[i++];
    if (cmd === "M") { if (cur.length > 1) out.push(cur); x = n(); y = n(); x0 = x; y0 = y; cur = [[x, y]]; cmd = "L"; }
    else if (cmd === "L") { x = n(); y = n(); cur.push([x, y]); }
    else if (cmd === "Q") {
      const cx = n(), cy = n(), ex = n(), ey = n();
      for (let k = 1; k <= passos; k++) { const u = k / passos, v = 1 - u; cur.push([v * v * x + 2 * v * u * cx + u * u * ex, v * v * y + 2 * v * u * cy + u * u * ey]); }
      x = ex; y = ey;
    } else if (cmd === "C") {
      const ax = n(), ay = n(), bx = n(), by = n(), ex = n(), ey = n();
      for (let k = 1; k <= passos; k++) {
        const u = k / passos, v = 1 - u;
        cur.push([v * v * v * x + 3 * v * v * u * ax + 3 * v * u * u * bx + u * u * u * ex, v * v * v * y + 3 * v * v * u * ay + 3 * v * u * u * by + u * u * u * ey]);
      }
      x = ex; y = ey;
    } else if (cmd === "Z" || cmd === "z") { cur.push([x0, y0]); x = x0; y = y0; if (cur.length > 1) out.push(cur); cur = []; cmd = ""; }
    else throw new Error(`achatar: comando não suportado "${cmd}"`);
  }
  if (cur.length > 1) out.push(cur);
  return out;
}
export function caixaDe(pts: P[]): Caixa {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y; }
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}
export function uniao(cs: Caixa[]): Caixa {
  return caixaDe(cs.flatMap((c) => [[c.x, c.y], [c.x + c.w, c.y + c.h]] as P[]));
}
export const centro = (c: Caixa): P => [c.x + c.w / 2, c.y + c.h / 2];
/** Distância de um ponto a uma caixa (0 se dentro). */
export function distCaixa(p: P, c: Caixa): number {
  const dx = Math.max(c.x - p[0], 0, p[0] - (c.x + c.w));
  const dy = Math.max(c.y - p[1], 0, p[1] - (c.y + c.h));
  return Math.hypot(dx, dy);
}
/** Tempo → fração desenhada (caneta: arranca, corre, assenta). */
const caneta = (u: number) => { u = Math.min(1, Math.max(0, u)); return 0.45 * u + 0.55 * (0.5 - 0.5 * Math.cos(Math.PI * u)); };

/**
 * Caixa ESTÁVEL de uma peça que gira/move: recebe, para cada quadro do intervalo, o pivô projetado e os pontos
 * projetados da peça; devolve a caixa (centrada no pivô de referência = 1ª amostra) com o MAIOR meio-tamanho visto.
 * Use-a como `caixa` do alvo e o pivô projetado como `movimento`.
 */
export function caixaEnvelope(amostras: { centro: P; pontos: P[] }[]): Caixa {
  let hw = 0, hh = 0;
  for (const a of amostras) for (const [x, y] of a.pontos) { hw = Math.max(hw, Math.abs(x - a.centro[0])); hh = Math.max(hh, Math.abs(y - a.centro[1])); }
  const [cx, cy] = amostras[0].centro;
  return { x: cx - hw, y: cy - hh, w: 2 * hw, h: 2 * hh };
}

// ---------------------------------------------------------------- âncoras
export function ancoraEm(alvo: Alvo | undefined, t: number): { dx: number; dy: number; s: number } {
  const m = alvo?.movimento;
  if (!m || m.length === 0) return { dx: 0, dy: 0, s: 1 };
  if (t <= m[0].t) return { dx: m[0].dx, dy: m[0].dy, s: m[0].s ?? 1 };
  const n = m.length - 1;
  if (t >= m[n].t) return { dx: m[n].dx, dy: m[n].dy, s: m[n].s ?? 1 };
  let i = 0;
  while (t > m[i + 1].t) i++;
  const k0 = m[Math.max(0, i - 1)], k1 = m[i], k2 = m[i + 1], k3 = m[Math.min(n, i + 2)];
  const u = (t - k1.t) / (k2.t - k1.t), u2 = u * u, u3 = u2 * u;
  const cr = (a: number, b: number, c: number, d: number) => 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3);
  return { dx: cr(k0.dx, k1.dx, k2.dx, k3.dx), dy: cr(k0.dy, k1.dy, k2.dy, k3.dy), s: cr(k0.s ?? 1, k1.s ?? 1, k2.s ?? 1, k3.s ?? 1) };
}

// ---------------------------------------------------------------- formas (coordenadas absolutas da pose de referência)
type Forma = { pts: P[]; largura: number; mascara?: boolean };

/** Oval aberto com perninha: começa em cima à esquerda, dá a volta e passa do início por FORA (raio +6% no fim). */
export function formaOval(c: Caixa, folga: number, semente: number, giro?: number): { pts: P[]; rx: number; ry: number } {
  const r = aleatorio(semente);
  const hw = c.w / 2, hh = c.h / 2;
  let rx = hw + folga, ry = hh + folga;
  // giro "à mão" de -1° a -4°, limitado em caixa larga (a ponta subiria mais que ~1/3 da altura do texto)
  const gMax = (Math.asin(Math.min(1, (0.35 * hh) / Math.max(hw, 1))) * 180) / Math.PI;
  const tilt = ((giro ?? -Math.min(1 + 3 * r(), Math.max(0.5, gMax))) * Math.PI) / 180;
  // os cantos da caixa ficam por dentro (a 97% do raio, antes da ondulação), JÁ com o giro: em texto largo, 3° de giro
  // levam a ponta do oval ±45 px para cima/baixo e ela cortava a 1ª e a última letra (uso real, "Nove milésimos.", 2026-11-14)
  const cg = Math.cos(tilt), sg = Math.sin(tilt);
  let q = 0;
  for (const [x, y] of [[hw, hh], [hw, -hh], [-hw, hh], [-hw, -hh]]) {
    const u = x * cg + y * sg, v = -x * sg + y * cg;   // canto no sistema do oval girado
    q = Math.max(q, Math.sqrt((u / rx) ** 2 + (v / ry) ** 2) / 0.97);
  }
  if (q > 1) { rx *= q; ry *= q; }
  const a0 = -2.75 + 0.5 * r();
  const over = 0.38 + 0.12 * r();
  const harm = [2, 3, 5].map((k, j) => ({ k, A: [0.012, 0.008, 0.004][j] * (0.6 + 0.8 * r()), f: r() * Math.PI * 2 }));
  const [cx, cy] = centro(c);
  const ct = Math.cos(tilt), st = Math.sin(tilt);
  const n = 120, pts: P[] = [];
  for (let i = 0; i <= n; i++) {
    const u = i / n, a = a0 + u * (Math.PI * 2 + over);
    let k = 1 + 0.06 * u * u * u;
    for (const h of harm) k += h.A * Math.sin(h.k * (a - a0) + h.f) * Math.sin(Math.PI * Math.min(1, u * 1.15)); // fecha liso
    const x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
    pts.push([cx + x * ct - y * st, cy + x * st + y * ct]);
  }
  return { pts, rx, ry };
}
/** Linha à mão de a até b com curvatura (fração do comprimento) e ondulação lenta. */
function linhaMao(a: P, b: P, curva: number, semente: number, amp = 1.2, n = 40): P[] {
  const r = aleatorio(semente);
  const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
  const nx = -dy / L, ny = dx / L;
  const f1_ = r() * 6.28, f2 = r() * 6.28, A = amp * (0.6 + 0.8 * r());
  const pts: P[] = [];
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const off = Math.sin(Math.PI * u) * curva * L + A * Math.sin(Math.PI * u) * (Math.sin(2.1 * Math.PI * u + f1_) * 0.7 + Math.sin(4.3 * Math.PI * u + f2) * 0.3);
    pts.push([a[0] + dx * u + nx * off, a[1] + dy * u + ny * off]);
  }
  return pts;
}
function formaSublinhado(c: Caixa, folga: number, semente: number): P[] {
  const r = aleatorio(semente);
  const y = c.y + c.h + folga;
  const a: P = [c.x - 6 - 4 * r(), y + 1], b: P = [c.x + c.w + 8 + 6 * r(), y - 5 - 3 * r()];
  return linhaMao(a, b, 0.012, semente + 1, 1.0);
}
/** Risco por cima do texto, passando um pouco das pontas (até `ext`, encurtado se houver outro texto do lado). */
function formaRiscado(c: Caixa, semente: number, desloc = 0, ext: [number, number] = [14, 14]): P[] {
  const r = aleatorio(semente);
  const ym = c.y + c.h * (0.52 + desloc);
  return linhaMao([c.x - ext[0] * (0.7 + 0.3 * r()), ym + 7 + 3 * r()], [c.x + c.w + ext[1] * (0.7 + 0.3 * r()), ym - 7 - 3 * r()], 0.01, semente + 3, 1.0);
}
function formaChave(c: Caixa, lado: Lado, folga: number, ponta: number, semente: number): P[] {
  // monta "}" na vertical (ponta para +x) e gira para o lado pedido
  const vertical = lado === "direita" || lado === "esquerda";
  const H = vertical ? c.h : c.w;
  const p = ponta, q = Math.min(p * 0.6, H / 5), m = H / 2;
  const d = `M 0 0 Q ${p / 2} 0 ${p / 2} ${q} L ${p / 2} ${m - q} Q ${p / 2} ${m} ${p} ${m} Q ${p / 2} ${m} ${p / 2} ${m + q} L ${p / 2} ${H - q} Q ${p / 2} ${H} 0 ${H}`;
  const base = achatar(d, 8)[0];
  const r = aleatorio(semente);
  const w = base.map(([x, y], i) => [x + 0.8 * Math.sin(i * 0.35 + r() * 0.2 + semente), y] as P);
  return w.map(([x, y]): P => {
    if (lado === "direita") return [c.x + c.w + folga + x, c.y + y];
    if (lado === "esquerda") return [c.x - folga - x, c.y + y];
    if (lado === "baixo") return [c.x + y, c.y + c.h + folga + x];
    return [c.x + y, c.y - folga - x];
  });
}

// ---------------------------------------------------------------- texto à mão (glifos da Caveat)
type GlifoBase = { adv: number; outline: string | null; stem: number; strokes: string[] };
/** Sinais que a tabela não tem: só traço (sem contorno), em unidades de glifo. */
const EXTRAS: Record<string, GlifoBase> = {
  "%": { adv: 560, outline: null, stem: 60, strokes: ["M 190 -560 C 120 -560 95 -500 100 -455 C 105 -410 150 -385 190 -390 C 235 -395 265 -440 255 -490 C 248 -530 220 -560 190 -560", "M 470 -580 L 120 0", "M 400 -190 C 335 -190 305 -130 312 -88 C 318 -45 360 -20 400 -25 C 445 -30 475 -75 467 -122 C 460 -160 432 -190 400 -190"] },
  "°": { adv: 300, outline: null, stem: 55, strokes: ["M 150 -600 C 95 -600 70 -560 75 -525 C 80 -490 115 -470 150 -473 C 190 -477 215 -510 210 -545 C 205 -578 180 -600 150 -600"] },
  "/": { adv: 380, outline: null, stem: 60, strokes: ["M 330 -620 L 60 60"] },
  "×": { adv: 420, outline: null, stem: 60, strokes: ["M 90 -400 L 330 -120", "M 330 -400 L 90 -120"] },
  "±": { adv: 430, outline: null, stem: 60, strokes: ["M 215 -470 L 210 -200", "M 80 -340 L 350 -335", "M 80 -90 L 350 -95"] },
  "=": { adv: 420, outline: null, stem: 60, strokes: ["M 80 -330 L 340 -335", "M 80 -190 L 340 -195"] },
  ">": { adv: 400, outline: null, stem: 60, strokes: ["M 90 -420 L 320 -255 L 90 -100"] },
  "<": { adv: 400, outline: null, stem: 60, strokes: ["M 320 -420 L 90 -255 L 320 -100"] },
};
/** Diacríticos (marca combinante NFD) desenhados sobre a caixa de tinta do glifo base. */
function diacritico(marca: string, bx: number, topo: number, base: number, larg: number): string[] {
  const y = topo - 70, x = bx;
  switch (marca) {
    case "́": return [`M ${x - 40} ${y + 10} L ${x + 70} ${y - 110}`]; // agudo
    case "̀": return [`M ${x + 40} ${y + 10} L ${x - 70} ${y - 110}`]; // grave
    case "̂": return [`M ${x - 80} ${y + 5} L ${x} ${y - 100} L ${x + 80} ${y + 5}`]; // circunflexo
    case "̃": return [`M ${x - 95} ${y - 20} C ${x - 60} ${y - 90} ${x - 25} ${y - 70} ${x} ${y - 45} C ${x + 25} ${y - 20} ${x + 60} ${y - 10} ${x + 95} ${y - 80}`]; // til
    case "̈": return [`M ${x - 55} ${y - 40} L ${x - 50} ${y - 55}`, `M ${x + 50} ${y - 40} L ${x + 55} ${y - 55}`]; // trema
    case "̧": return [`M ${x + 10} ${base + 10} C ${x + 10} ${base + 60} ${x + 90} ${base + 80} ${x + 50} ${base + 140} C ${x + 30} ${base + 170} ${x - 30} ${base + 175} ${x - 50} ${base + 160}`]; // cedilha
    default: return [];
  }
}

type GlifoMontado = { x: number; outline: string | null; tracos: { pts: P[]; d: string; comp: number; tinta: boolean }[]; mascara: number; tinta: Caixa; largTraco: number };
const cacheTinta = new Map<string, Caixa>();
function tintaDoGlifo(ch: string, g: GlifoBase): Caixa {
  const k = ch + "|" + g.adv;
  let c = cacheTinta.get(k);
  if (!c) {
    const pts = g.outline ? achatar(g.outline, 4).flat() : g.strokes.flatMap((s) => achatar(s, 6).flat());
    c = caixaDe(pts);
    if (!g.outline) c = { x: c.x - g.stem / 2, y: c.y - g.stem / 2, w: c.w + g.stem, h: c.h + g.stem };
    cacheTinta.set(k, c);
  }
  return c;
}
/** Monta o texto em unidades de glifo a partir de x=0, linha de base y=0. */
export function montarTexto(texto: string, fonte: Fonte): { glifos: GlifoMontado[]; largura: number; faltando: string[] } {
  const glifos: GlifoMontado[] = [];
  const faltando: string[] = [];
  let x = 0;
  for (const chOrig of Array.from(texto)) {
    if (chOrig === " ") { x += ESPACO; continue; }
    const dec = Array.from(chOrig.normalize("NFD"));
    const baseCh = fonte.glyphs[chOrig] || EXTRAS[chOrig] ? chOrig : dec[0];
    const marcas = baseCh === chOrig ? [] : dec.slice(1);
    const g: GlifoBase | undefined = fonte.glyphs[baseCh] || EXTRAS[baseCh];
    if (!g) { faltando.push(chOrig); x += 450; continue; }
    const tinta0 = tintaDoGlifo(baseCh, g);
    const strokes = [...g.strokes];
    for (const m of marcas) strokes.push(...diacritico(m, tinta0.x + tinta0.w / 2, tinta0.y, 0, tinta0.w));
    // traços da tabela = máscara que revela o contorno; acentos e sinais extras = tinta visível
    const tracos = strokes.map((s, i) => { const pts = achatar(s, 10).flat(); return { pts, d: s, comp: comprimento(pts), tinta: !g.outline || i >= g.strokes.length }; });
    let tinta = tinta0;
    if (marcas.length) {
      const extra = tracos.slice(g.strokes.length).flatMap((t) => t.pts);
      const ce = caixaDe(extra);
      tinta = uniao([tinta0, { x: ce.x - 35, y: ce.y - 35, w: ce.w + 70, h: ce.h + 70 }]);
    }
    glifos.push({ x, outline: g.outline, tracos, mascara: Math.max(30, Math.round(g.stem * 1.35)), tinta: { ...tinta, x: tinta.x + x }, largTraco: g.stem * 1.05 });
    x += g.adv;
  }
  return { glifos, largura: x, faltando };
}

// ---------------------------------------------------------------- montagem
export type Traco = { pts: P[]; d: string; comp: number; largura: number; t0: number; t1: number; tinta?: boolean };
export type GlifoM = { x: number; y: number; k: number; outline: string | null; tracos: Traco[] };
export type Item = {
  a: Anotacao;
  /** alvo que dá a âncora (a anotação inteira se desloca com ele) */
  ancora?: string;
  cor: string;
  tracos: Traco[];
  glifos: GlifoM[];
  /** caixa de tinta do texto à mão (coordenadas da pose de referência) */
  caixaTexto?: Caixa;
  /** caixa e elipse do oval (pose de referência), para a checagem e para setas que apontam para ele */
  caixaOval?: Caixa;
  elipse?: { rx: number; ry: number; cx: number; cy: number };
  /** caixa de todos os traços (pose de referência): permite usar qualquer anotação como alvo de nota/seta */
  caixaForma?: Caixa;
  /** fim do desenho (s) */
  fim: number;
  /** precisa recalcular a cada quadro (seta entre âncoras que se movem de forma diferente) */
  dinamica: boolean;
  faltando: string[];
};
export type Montada = { cena: Cena; itens: Item[]; avisos: string[] };

function cronometrar(formas: Forma[], em: number, vel: number): { tracos: Traco[]; fim: number } {
  let t = em;
  const tracos: Traco[] = [];
  formas.forEach((f, i) => {
    if (i > 0) t += LEVANTA;
    const comp = comprimento(f.pts);
    const dur = Math.max(1 / 60, comp / vel);
    tracos.push({ pts: f.pts, d: liso(f.pts), comp, largura: f.largura, t0: t, t1: t + dur });
    t += dur;
  });
  return { tracos, fim: t };
}
function cabeca(pts: P[], comp: number, esp: number): P[][] {
  const n = pts.length - 1;
  const fim = pts[n];
  let j = n; while (j > 0 && dist(pts[j], fim) < Math.min(22, comp * 0.15)) j--;
  const g = Math.atan2(fim[1] - pts[j][1], fim[0] - pts[j][0]);
  const L = 24 * (esp / ESPESSURA) + 0.04 * Math.min(comp, 300);
  const lado = (s: number): P[] => [[fim[0] + Math.cos(g + Math.PI - s * 0.48) * L, fim[1] + Math.sin(g + Math.PI - s * 0.48) * L], fim];
  return [lado(1), lado(-1)];
}

/** Ponto onde a semi-reta do centro c na direção u sai da caixa (ou da elipse) + recuo. */
function saida(alvo: { caixa: Caixa; elipse?: { rx: number; ry: number; cx: number; cy: number } }, dir: P, recuo: number): P {
  if (alvo.elipse) {
    const { rx, ry, cx, cy } = alvo.elipse;
    const s = 1 / Math.sqrt((dir[0] / rx) ** 2 + (dir[1] / ry) ** 2);
    return [cx + dir[0] * (s * 1.06 + recuo), cy + dir[1] * (s * 1.06 + recuo)];
  }
  const c = alvo.caixa, [cx, cy] = centro(c);
  const sx = dir[0] ? (c.w / 2) / Math.abs(dir[0]) : Infinity, sy = dir[1] ? (c.h / 2) / Math.abs(dir[1]) : Infinity;
  const s = Math.min(sx, sy);
  return [cx + dir[0] * (s + recuo), cy + dir[1] * (s + recuo)];
}

export function montar(cena: Cena, fonte: Fonte): Montada {
  const avisos: string[] = [];
  const itens: Item[] = [];
  const porId = new Map<string, Item>();
  const caixaAlvo = (id: string): Caixa => {
    const a = cena.alvos[id];
    if (a) return a.caixa;
    const it = porId.get(id);
    if (it?.caixaOval) return it.caixaOval;
    if (it?.caixaTexto) return it.caixaTexto;
    if (it?.caixaForma) return it.caixaForma;
    throw new Error(`alvo desconhecido: ${id}`);
  };
  const ancoraDe = (id: string): string | undefined => (cena.alvos[id] ? id : porId.get(id)?.ancora);
  const obstaculos = Object.entries(cena.alvos).filter(([, a]) => a.texto);
  /** quanto o risco pode passar de cada ponta sem chegar a outro texto na mesma faixa (pose de referência) */
  const extensao = (id: string, esp: number): [number, number] => {
    const c = caixaAlvo(id);
    let e = 14, d = 14;
    for (const [oid, o] of obstaculos) {
      if (oid === id) continue;
      const oc = o.caixa;
      if (oc.y > c.y + c.h || oc.y + oc.h < c.y) continue;
      const folga = esp / 2 + 8;
      if (oc.x >= c.x + c.w) d = Math.min(d, oc.x - (c.x + c.w) - folga);
      if (oc.x + oc.w <= c.x) e = Math.min(e, c.x - (oc.x + oc.w) - folga);
    }
    return [Math.max(0, e), Math.max(0, d)];
  };

  for (const a of cena.anotacoes) {
    const cor = a.cor ?? COR, esp = a.espessura ?? ESPESSURA;
    const sem = a.semente ?? hashTexto(a.id);
    const base: Item = { a, cor, tracos: [], glifos: [], fim: a.em, dinamica: false, faltando: [] };
    if (a.tipo === "oval") {
      const c = caixaAlvo(a.alvo);
      const o = formaOval(c, a.folga ?? 30, sem, a.giro);
      const { tracos, fim } = cronometrar([{ pts: o.pts, largura: esp }], a.em, a.vel ?? VEL.oval);
      Object.assign(base, { tracos, fim, ancora: ancoraDe(a.alvo), caixaOval: caixaDe(o.pts), elipse: { rx: o.rx, ry: o.ry, cx: centro(c)[0], cy: centro(c)[1] } });
    } else if (a.tipo === "sublinhado" || a.tipo === "riscado") {
      const c = caixaAlvo(a.alvo);
      const formas: Forma[] = a.tipo === "sublinhado"
        ? [{ pts: formaSublinhado(c, a.folga ?? 14, sem), largura: esp }]
        : [{ pts: formaRiscado(c, sem, 0, extensao(a.alvo, esp)), largura: esp }, ...(a.duplo ? [{ pts: formaRiscado(c, sem + 7, 0.14, extensao(a.alvo, esp)), largura: esp }] : [])];
      const { tracos, fim } = cronometrar(formas, a.em, a.vel ?? VEL[a.tipo]);
      Object.assign(base, { tracos, fim, ancora: ancoraDe(a.alvo) });
    } else if (a.tipo === "chave") {
      const c = uniao(a.alvos.map(caixaAlvo));
      const { tracos, fim } = cronometrar([{ pts: formaChave(c, a.lado ?? "direita", a.folga ?? 16, a.ponta ?? 26, sem), largura: esp }], a.em, a.vel ?? VEL.chave);
      Object.assign(base, { tracos, fim, ancora: ancoraDe(a.alvos[0]) });
    } else if (a.tipo === "nota" || a.tipo === "corrigido") {
      const mt = montarTexto(a.texto, fonte);
      base.faltando = mt.faltando;
      if (mt.faltando.length) avisos.push(`${a.id}: sem glifo para ${JSON.stringify(mt.faltando)}`);
      const tinta = caixaDe(mt.glifos.flatMap((g) => [[g.tinta.x, g.tinta.y], [g.tinta.x + g.tinta.w, g.tinta.y + g.tinta.h]] as P[]));
      // número corrigido: altura de tinta = 85% da altura do número riscado
      const tam = a.tamanho ?? (a.tipo === "corrigido" ? Math.round((0.85 * caixaAlvo(a.alvo).h * 1000) / tinta.h) : 64);
      const k = tam / 1000;
      const tw = tinta.w * k, th = tinta.h * k;
      // posição do canto superior esquerdo da tinta
      let pos: P, ancora: string | undefined;
      let riscos: Forma[] = [];
      if (a.tipo === "corrigido") {
        const c = caixaAlvo(a.alvo);
        ancora = ancoraDe(a.alvo);
        riscos = [{ pts: formaRiscado(c, sem, 0, extensao(a.alvo, esp)), largura: esp }];
        const lado = a.lado ?? "cima";
        pos = lado === "cima" ? [c.x + c.w / 2 - tw / 2, c.y - th - 12]
          : lado === "baixo" ? [c.x + c.w / 2 - tw / 2, c.y + c.h + 14]
          : lado === "direita" ? [c.x + c.w + 22, c.y + c.h / 2 - th / 2] : [c.x - tw - 22, c.y + c.h / 2 - th / 2];
      } else if (a.perto) {
        const c = caixaAlvo(a.perto.alvo);
        ancora = ancoraDe(a.perto.alvo);
        const dd = a.perto.distancia ?? 26, [ex, ey] = a.perto.desloc ?? [0, 0];
        const posLado = (l: Lado): P => {
          const p: P = l === "cima" ? [c.x + c.w / 2 - tw / 2, c.y - th - dd] : l === "baixo" ? [c.x + c.w / 2 - tw / 2, c.y + c.h + dd]
            : l === "direita" ? [c.x + c.w + dd, c.y + c.h / 2 - th / 2] : [c.x - tw - dd, c.y + c.h / 2 - th / 2];
          return [p[0] + ex, p[1] + ey];
        };
        if (a.perto.lado === "auto") {
          // primeiro lado em que a nota (em todo o tempo da âncora) não cruza texto e cabe na tela
          const ordem: Lado[] = ["direita", "baixo", "esquerda", "cima"];
          const livre = (l: Lado) => {
            const p = posLado(l);
            for (let f = 0; f <= cena.duracao * cena.fps; f += 6) {
              const an = ancoraEm(ancora ? cena.alvos[ancora] : undefined, f / cena.fps);
              const bx: Caixa = { x: p[0] + an.dx, y: p[1] + an.dy, w: tw, h: th };
              if (bx.x < 20 || bx.y < 20 || bx.x + bx.w > cena.largura - 20 || bx.y + bx.h > cena.altura - 20) return false;
              for (const [id, o] of obstaculos) {
                const ao = ancoraEm(o, f / cena.fps), oc = o.caixa;
                const ox = { x: oc.x + ao.dx - 12, y: oc.y + ao.dy - 12, w: oc.w + 24, h: oc.h + 24 };
                if (id !== a.perto!.alvo && bx.x < ox.x + ox.w && ox.x < bx.x + bx.w && bx.y < ox.y + ox.h && ox.y < bx.y + bx.h) return false;
              }
            }
            return true;
          };
          const l = ordem.find(livre);
          if (!l) avisos.push(`${a.id}: nenhum lado livre; usei "direita"`);
          pos = posLado(l ?? "direita");
        } else pos = posLado(a.perto.lado);
      } else {
        pos = a.pos ?? [0, 0];
      }
      const ox = pos[0] - tinta.x * k, oy = pos[1] - tinta.y * k; // origem (linha de base) em px
      const { tracos: tr, fim: fimR } = cronometrar(riscos, a.em, a.vel ?? VEL.riscado);
      let t = riscos.length ? fimR + 0.12 : a.em;
      const velT = (a.tipo === "nota" ? a.vel : undefined) ?? VEL.texto;
      const glifos: GlifoM[] = mt.glifos.map((g, gi) => {
        if (gi > 0) t += LEVANTA_LETRA;
        const tracos = g.tracos.map((s, si) => {
          if (si > 0) t += LEVANTA * 0.5;
          const dur = Math.max(1 / 60, (s.comp * k) / velT);
          const tt: Traco = { pts: s.pts.map(([x, y]) => [ox + (g.x + x) * k, oy + y * k] as P), d: s.d, comp: s.comp * k, largura: (s.tinta ? g.largTraco : g.mascara) * k, t0: t, t1: t + dur, tinta: s.tinta };
          t += dur;
          return tt;
        });
        return { x: ox + g.x * k, y: oy, k, outline: g.outline, tracos };
      });
      Object.assign(base, { tracos: tr, glifos, fim: t, ancora, caixaTexto: { x: pos[0], y: pos[1], w: tw, h: th } });
    } else if (a.tipo === "seta") {
      base.ancora = ancoraDe(a.de);
      base.dinamica = ancoraDe(a.para) !== base.ancora;
    }
    if (base.tracos.length) base.caixaForma = caixaDe(base.tracos.flatMap((t) => t.pts));
    itens.push(base);
    porId.set(a.id, base);
  }
  // setas: geometria depende da posição relativa dos dois lados
  const m: Montada = { cena, itens, avisos };
  for (const it of itens) if (it.a.tipo === "seta") geometriaSeta(m, it, it.a.em);
  return m;
}

function alvoGeom(m: Montada, id: string): { caixa: Caixa; elipse?: { rx: number; ry: number; cx: number; cy: number }; ancora?: string } {
  const a = m.cena.alvos[id];
  if (a) return { caixa: a.caixa, ancora: id };
  const it = m.itens.find((i) => i.a.id === id);
  if (!it) throw new Error(`alvo desconhecido: ${id}`);
  return { caixa: it.caixaOval ?? it.caixaTexto ?? it.caixaForma!, elipse: it.elipse, ancora: it.ancora };
}
/** Calcula (ou recalcula, se dinâmica) a seta no referencial da âncora de origem. */
function geometriaSeta(m: Montada, it: Item, t: number) {
  const a = it.a as Extract<Anotacao, { tipo: "seta" }>;
  const de = alvoGeom(m, a.de), para = alvoGeom(m, a.para);
  const anDe = ancoraEm(de.ancora ? m.cena.alvos[de.ancora] : undefined, t), anPara = ancoraEm(para.ancora ? m.cena.alvos[para.ancora] : undefined, t);
  // posição do alvo "para" vista no referencial da âncora de origem
  const off: P = [anPara.dx - anDe.dx, anPara.dy - anDe.dy];
  const cDe = centro(de.caixa), cPara0 = centro(para.caixa), cPara: P = [cPara0[0] + off[0], cPara0[1] + off[1]];
  const L = dist(cDe, cPara) || 1, u: P = [(cPara[0] - cDe[0]) / L, (cPara[1] - cDe[1]) / L];
  const s = saida(de, u, 10);
  const paraDesl = { caixa: { ...para.caixa, x: para.caixa.x + off[0], y: para.caixa.y + off[1] }, elipse: para.elipse ? { ...para.elipse, cx: para.elipse.cx + off[0], cy: para.elipse.cy + off[1] } : undefined };
  const e = saida(paraDesl, [-u[0], -u[1]], a.recuo ?? 14);
  const sem = a.semente ?? hashTexto(a.id);
  const esp = a.espessura ?? ESPESSURA;
  const haste = linhaMao(s, e, a.curva ?? 0.12, sem, 1.3);
  const comp = comprimento(haste);
  const [h1, h2] = cabeca(haste, comp, esp);
  const { tracos, fim } = cronometrar([{ pts: haste, largura: esp }, { pts: h1, largura: esp }, { pts: h2, largura: esp }], a.em, a.vel ?? VEL.seta);
  it.tracos = tracos;
  it.fim = fim;
}

// ---------------------------------------------------------------- estado por quadro (o que o motor desenha)
/** k = fração desenhada (0..1); tinta = traço visível (false = traço de máscara que revela o contorno do glifo) */
export type TracoEstado = { d: string; largura: number; k: number; tinta?: boolean };
export type ItemEstado = {
  id: string;
  tipo: Anotacao["tipo"];
  cor: string;
  /** transformação SVG da âncora (deslocamento + escala em torno do centro da caixa da âncora) */
  transform: string;
  dx: number; dy: number; s: number;
  tracos: TracoEstado[];
  /** cada glifo em unidades de fonte (transform já escala); outline = contorno cheio revelado pela máscara */
  glifos: { transform: string; outline: string | null; tracos: TracoEstado[] }[];
};
const frac = (tr: Traco, t: number) => (t <= tr.t0 ? 0 : t >= tr.t1 ? 1 : caneta((t - tr.t0) / (tr.t1 - tr.t0)));

export function estado(m: Montada, t: number): ItemEstado[] {
  return m.itens.map((it) => {
    if (it.dinamica) geometriaSeta(m, it, t);
    const al = it.ancora ? m.cena.alvos[it.ancora] : undefined;
    const an = ancoraEm(al, t);
    let transform = `translate(${f1(an.dx)} ${f1(an.dy)})`;
    if (Math.abs(an.s - 1) > 1e-4 && al) {
      const [cx, cy] = centro(al.caixa);
      transform = `translate(${f1(an.dx + cx)} ${f1(an.dy + cy)}) scale(${an.s.toFixed(4)}) translate(${f1(-cx)} ${f1(-cy)})`;
    }
    return {
      id: it.a.id, tipo: it.a.tipo, cor: it.cor, transform, dx: an.dx, dy: an.dy, s: an.s,
      tracos: it.tracos.map((tr) => ({ d: tr.d, largura: tr.largura, k: frac(tr, t) })),
      glifos: it.glifos.map((g) => ({
        transform: `translate(${f1(g.x)} ${f1(g.y)}) scale(${g.k.toFixed(5)})`,
        outline: g.outline,
        tracos: g.tracos.map((tr) => ({ d: tr.d, largura: tr.largura / g.k, k: frac(tr, t), tinta: !!tr.tinta })),
      })),
    };
  });
}

// ---------------------------------------------------------------- verificação (mesma conta para todos os motores)
export type Relatorio = {
  quadros: number;
  avisos: string[];
  falhas: string[];
  ovais: Record<string, { tamanho: [number, number]; variacaoTamanho: number; margens: [number, number, number, number]; variacaoMargem: number; folgaMinPeca: number; caixasPorQuadro: [number, number, number, number][] }>;
  desenho: Record<string, { inicio: number; fim: number; monotono: boolean; completo: boolean }>;
  cruzamentos: { id: string; texto: string; quadro: number; dist: number }[];
  distMinTexto: Record<string, number>;
};

function pontosVisiveis(tr: Traco, k: number): P[] {
  if (k <= 0) return [];
  const alvo = tr.comp * k;
  const out: P[] = [tr.pts[0]];
  let s = 0;
  for (let i = 1; i < tr.pts.length; i++) {
    const a = tr.pts[i - 1], b = tr.pts[i], L = dist(a, b);
    const n = Math.max(1, Math.ceil(L / 2)); // pontos a cada ≤ 2 px: nenhum canto de texto escapa entre dois pontos
    for (let j = 1; j <= n; j++) {
      if (s + (L * j) / n > alvo + 0.5) return out;
      out.push([a[0] + ((b[0] - a[0]) * j) / n, a[1] + ((b[1] - a[1]) * j) / n]);
    }
    s += L;
  }
  return out;
}

/** Percorre todos os quadros e confere: oval de tamanho e margem constantes, desenho progressivo, nada cruzando texto. */
export function checar(m: Montada, opcoes: { tolerancia?: number; folgaTexto?: number } = {}): Relatorio {
  const tol = opcoes.tolerancia ?? 0.25;
  const folgaTexto = opcoes.folgaTexto ?? 4;
  const { cena } = m;
  const nq = Math.round(cena.duracao * cena.fps);
  const rel: Relatorio = { quadros: nq + 1, avisos: [...m.avisos], falhas: [], ovais: {}, desenho: {}, cruzamentos: [], distMinTexto: {} };
  const ultimoK = new Map<string, number[]>();
  for (const it of m.itens) rel.desenho[it.a.id] = { inicio: Infinity, fim: -Infinity, monotono: true, completo: false };
  const textos = Object.entries(cena.alvos).filter(([, a]) => a.texto);
  for (let q = 0; q <= nq; q++) {
    const t = q / cena.fps;
    for (const it of m.itens) {
      if (it.dinamica) geometriaSeta(m, it, t);
      const al = it.ancora ? cena.alvos[it.ancora] : undefined;
      const an = ancoraEm(al, t);
      const cc = al ? centro(al.caixa) : [0, 0];
      const tf = (p: P): P => [cc[0] + (p[0] - cc[0]) * an.s + an.dx, cc[1] + (p[1] - cc[1]) * an.s + an.dy];
      const todos = [...it.tracos, ...it.glifos.flatMap((g) => g.tracos)];
      const ks = todos.map((tr) => frac(tr, t));
      const prev = ultimoK.get(it.a.id);
      const d = rel.desenho[it.a.id];
      if (prev && ks.some((k, i) => k < prev[i] - 1e-9)) d.monotono = false;
      ultimoK.set(it.a.id, ks);
      if (ks.some((k) => k > 0)) d.inicio = Math.min(d.inicio, t);
      if (ks.every((k) => k >= 1)) { if (!d.completo) d.fim = t; d.completo = true; }
      // oval: caixa inteira (tamanho/margem) em todo quadro em que aparece
      if (it.a.tipo === "oval" && ks[0] > 0) {
        const alvo = cena.alvos[it.a.alvo];
        const anAlvo = ancoraEm(alvo, t);
        const cA = centro(alvo.caixa);
        const pc: Caixa = { x: cA[0] + (alvo.caixa.x - cA[0]) * anAlvo.s + anAlvo.dx, y: cA[1] + (alvo.caixa.y - cA[1]) * anAlvo.s + anAlvo.dy, w: alvo.caixa.w * anAlvo.s, h: alvo.caixa.h * anAlvo.s };
        const ob = caixaDe(it.tracos[0].pts.map(tf));
        const o = (rel.ovais[it.a.id] ??= { tamanho: [ob.w, ob.h], variacaoTamanho: 0, margens: [pc.x - ob.x, pc.y - ob.y, ob.x + ob.w - pc.x - pc.w, ob.y + ob.h - pc.y - pc.h], variacaoMargem: 0, folgaMinPeca: Infinity, caixasPorQuadro: [] });
        o.variacaoTamanho = Math.max(o.variacaoTamanho, Math.abs(ob.w - o.tamanho[0]), Math.abs(ob.h - o.tamanho[1]));
        const mg = [pc.x - ob.x, pc.y - ob.y, ob.x + ob.w - pc.x - pc.w, ob.y + ob.h - pc.y - pc.h];
        o.variacaoMargem = Math.max(o.variacaoMargem, ...mg.map((v, i) => Math.abs(v - o.margens[i])));
        o.caixasPorQuadro.push([q, ob.x, ob.y, ob.w]);
        for (const p of it.tracos[0].pts) { const dd = distCaixa(tf(p), pc); if (dd === 0) o.folgaMinPeca = 0; }
        // menor distância do traço até a borda da caixa (por dentro da elipse)
        const [cx, cy] = centro(pc);
        let mn = Infinity;
        for (const p0 of it.tracos[0].pts) { const p = tf(p0); const dx = Math.max(Math.abs(p[0] - cx) - pc.w / 2, 0), dy = Math.max(Math.abs(p[1] - cy) - pc.h / 2, 0); mn = Math.min(mn, Math.hypot(dx, dy)); }
        o.folgaMinPeca = Math.min(o.folgaMinPeca, mn);
      }
      // cruzamento com texto: pontos visíveis de cada traço x caixas de texto (exceto o próprio alvo de riscado/corrigido/sublinhado)
      const permitido = new Set<string>();
      if (it.a.tipo === "riscado" || it.a.tipo === "corrigido") permitido.add(it.a.alvo);
      for (let i = 0; i < it.tracos.length; i++) {
        if (ks[i] <= 0) continue;
        const r = it.tracos[i].largura / 2;
        for (const p0 of pontosVisiveis(it.tracos[i], ks[i])) {
          const p = tf(p0);
          for (const [tid, tx] of textos) {
            if (permitido.has(tid)) continue;
            const at = ancoraEm(tx, t);
            const dd = distCaixa(p, { x: tx.caixa.x + at.dx, y: tx.caixa.y + at.dy, w: tx.caixa.w, h: tx.caixa.h }) - r;
            const key = `${it.a.id}×${tid}`;
            rel.distMinTexto[key] = Math.min(rel.distMinTexto[key] ?? Infinity, dd);
            if (dd < folgaTexto && !rel.cruzamentos.some((c) => c.id === it.a.id && c.texto === tid)) rel.cruzamentos.push({ id: it.a.id, texto: tid, quadro: q, dist: dd });
          }
        }
      }
      // texto à mão: caixa de tinta x textos da cena e x outras notas
      if (it.caixaTexto && it.glifos.some((g) => g.tracos.some((tr) => frac(tr, t) > 0))) {
        const c = it.caixaTexto;
        const p0 = tf([c.x, c.y]), p1 = tf([c.x + c.w, c.y + c.h]);
        const bx: Caixa = { x: p0[0], y: p0[1], w: p1[0] - p0[0], h: p1[1] - p0[1] };
        for (const [tid, tx] of textos) {
          if (it.a.tipo === "corrigido" && tid === it.a.alvo) continue;
          const at = ancoraEm(tx, t), o = { x: tx.caixa.x + at.dx, y: tx.caixa.y + at.dy, w: tx.caixa.w, h: tx.caixa.h };
          const gx = Math.max(o.x - (bx.x + bx.w), bx.x - (o.x + o.w)), gy = Math.max(o.y - (bx.y + bx.h), bx.y - (o.y + o.h));
          const dd = Math.max(gx, gy);
          const key = `${it.a.id}(texto)×${tid}`;
          rel.distMinTexto[key] = Math.min(rel.distMinTexto[key] ?? Infinity, dd);
          if (dd < folgaTexto && !rel.cruzamentos.some((c2) => c2.id === it.a.id && c2.texto === tid)) rel.cruzamentos.push({ id: it.a.id, texto: tid, quadro: q, dist: dd });
        }
        if (bx.x < 0 || bx.y < 0 || bx.x + bx.w > cena.largura || bx.y + bx.h > cena.altura) {
          const msg = `${it.a.id}: texto à mão sai da tela no quadro ${q}`;
          if (!rel.falhas.includes(msg)) rel.falhas.push(msg);
        }
      }
    }
  }
  for (const [id, o] of Object.entries(rel.ovais)) {
    const al = cena.alvos[(m.itens.find((i) => i.a.id === id)!.a as { alvo: string }).alvo];
    const escalaFixa = !al.movimento || al.movimento.every((k) => (k.s ?? 1) === (al.movimento![0].s ?? 1));
    if (escalaFixa && o.variacaoTamanho > tol) rel.falhas.push(`${id}: tamanho do oval variou ${o.variacaoTamanho.toFixed(3)} px`);
    if (escalaFixa && o.variacaoMargem > tol) rel.falhas.push(`${id}: margem oval×peça variou ${o.variacaoMargem.toFixed(3)} px`);
    if (o.folgaMinPeca <= 0) rel.falhas.push(`${id}: o traço do oval encosta na caixa da peça`);
  }
  for (const [id, d] of Object.entries(rel.desenho)) {
    if (!d.monotono) rel.falhas.push(`${id}: desenho voltou para trás`);
    if (!d.completo) rel.falhas.push(`${id}: não terminou de desenhar até o fim da cena`);
  }
  for (const c of rel.cruzamentos) rel.falhas.push(`${c.id} cruza o texto ${c.texto} (quadro ${c.quadro}, ${c.dist.toFixed(1)} px)`);
  return rel;
}
