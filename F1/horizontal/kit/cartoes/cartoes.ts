// kit/cartoes: cartão de pessoa (foto + nome + função), cartão de capítulo/título ("PARTE 0N" + título + traçado) e tag
// ancorada numa posição da pista (ponto + perninha + caixa de texto). Núcleo sem dependência de motor.
// O kit faz TODO o layout sem navegador (larguras da Bahnschrift em larguras.ts) e devolve, para cada tempo t, o SVG de
// cada cartão. Remotion e HyperFrames só colocam esse SVG por cima da cena (mesmo resultado nos dois).
//   const m = montarCartoes(cena);  estadoCartoes(m, t) → [{ id, tipo, opacidade, caixa, svg, ... }]
// Texto entra SECO (sem letra a letra, sem decodificação): o cartão aparece com fade curto e um deslize pequeno.
import { LARGURAS, type Estilo } from "./larguras.ts";

export type P = [number, number];
export type Caixa = { x: number; y: number; w: number; h: number };

export type Pessoa = {
  tipo: "pessoa"; id: string; em: number; ate: number;
  nome: string; funcao?: string;
  /** URL da foto (cada motor resolve: staticFile/import no Remotion, assets/ no HyperFrames); sem foto = silhueta */
  foto?: string;
  /** tamanho natural da foto em px (para o recorte "cover" ser calculado aqui) */
  fotoTam?: [number, number];
  /** centro do rosto na foto (fração 0..1); padrão [0,5, 0,3] */
  fotoFoco?: [number, number];
  /** P&B (padrão true, regra do horizontal: foto livre em P&B) */
  pb?: boolean;
  lado?: "esquerda" | "direita";
  /** posição do canto superior esquerdo (substitui `lado`) */
  pos?: P;
  cor?: string;
};
export type Capitulo = {
  tipo: "capitulo"; id: string; em: number; ate: number;
  numero: number; titulo: string;
  /** traçado do circuito (caminho SVG) e o tamanho do seu sistema de coordenadas */
  tracado?: { d: string; largura: number; altura: number };
  cor?: string;
  fundo?: string;
};
export type Tag = {
  tipo: "tag"; id: string; em: number; ate: number;
  texto: string;
  /** posição da pista na tela: ponto fixo ou trilha {t,x,y} (ex.: projeção do carro a cada quadro); interpolação linear */
  ancora: P | { t: number; x: number; y: number }[];
  /** lado da caixa em relação ao ponto: ne (cima-direita), no, se, so; "auto" = o 1º que cabe no quadro o tempo todo */
  lado?: "auto" | "ne" | "no" | "se" | "so";
  /** comprimento da perninha em px (padrão 110) */
  perna?: number;
  cor?: string;
};
export type Cartao = Pessoa | Capitulo | Tag;
export type CenaCartoes = { largura: number; altura: number; fps: number; duracao: number; margem?: number; cartoes: Cartao[] };

export const COR = "#e10600";
export const TINTA = "#141414";
export const MARGEM = 48;

// ---------------------------------------------------------------- texto (layout sem navegador)
export type Texto = { texto: string; tam: number; estilo: Estilo; cor: string; x: number; y: number; w: number; h: number; base: number };

export function larguraTexto(texto: string, tam: number, estilo: Estilo): number {
  const t = LARGURAS[estilo];
  let s = 0;
  for (const ch of texto) s += t.av[ch] ?? t.av["M"];
  // +0,5%: o Chrome arredonda o avanço de cada glifo pelo hinting (até ~0,3% a mais em corpo grande, medido no teste)
  return (s * tam * 1.005) / 1000;
}
/** caixa de tinta (inclui acento das maiúsculas e descendentes) com o canto em (x, y) */
export function texto(txt: string, tam: number, estilo: Estilo, cor: string, x: number, y: number): Texto {
  const t = LARGURAS[estilo];
  const h = ((t.tinta_cima + t.tinta_baixo) * tam) / 1000;
  return { texto: txt, tam, estilo, cor, x, y, w: larguraTexto(txt, tam, estilo), h, base: y + (t.tinta_cima * tam) / 1000 };
}
const caracteresFaltando = (s: string, estilo: Estilo) => [...s].filter((c) => LARGURAS[estilo].av[c] === undefined);

// ---------------------------------------------------------------- tempo
const lim = (x: number) => Math.max(0, Math.min(1, x));
const saiCubica = (x: number) => 1 - Math.pow(1 - lim(x), 3);
const suave = (x: number) => { x = lim(x); return x * x * (3 - 2 * x); };
/** opacidade do cartão: fade de `ent` s na entrada e `sai` s na saída */
function envelope(c: { em: number; ate: number }, t: number, ent: number, sai: number): number {
  if (t < c.em || t > c.ate) return 0;
  return Math.min(suave((t - c.em) / ent), suave((c.ate - t) / sai));
}

// ---------------------------------------------------------------- montagem
type Rect = { x: number; y: number; w: number; h: number; r?: number; cor: string; sombra?: boolean };
type Img = { clip: Caixa; r: number; img: Caixa; src?: string; pb: boolean };
export type PessoaM = { c: Required<Pick<Pessoa, "cor" | "pb">> & Pessoa; cartao: Rect; barra: Rect; foto: Img; textos: Texto[]; caixa: Caixa; dx0: number };
export type CapituloM = { c: Capitulo & { cor: string; fundo: string }; textos: Texto[]; tracado?: { d: string; transform: string; caixa: Caixa; larg: number }; caixa: Caixa };
export type TagM = {
  c: Tag & { cor: string; perna: number };
  lado: "ne" | "no" | "se" | "so";
  /** true = nenhum lado cabe o tempo todo: a caixa é empurrada para dentro do quadro quadro a quadro */
  empurrada: boolean;
  w: number; h: number; texto: Texto;
};
export type MontadaCartoes = { cena: CenaCartoes; itens: { tipo: Cartao["tipo"]; m: PessoaM | CapituloM | TagM }[]; avisos: string[] };

function montarPessoa(c: Pessoa, cena: CenaCartoes, avisos: string[]): PessoaM {
  const cor = c.cor ?? COR, pb = c.pb ?? true;
  const pad = 18, foto = 176, gap = 26, barra = 8;
  const tx = barra + pad + foto + gap;
  let tamNome = 54;
  const maxTexto = 1100 - tx - pad - 22;
  while (tamNome > 30 && larguraTexto(c.nome, tamNome, "forte") > maxTexto) tamNome -= 1;
  let tamF = 30;
  while (c.funcao && tamF > 20 && larguraTexto(c.funcao, tamF, "normal") > maxTexto) tamF -= 1;
  const nome = texto(c.nome, tamNome, "forte", TINTA, tx, 0);
  const func = c.funcao ? texto(c.funcao, tamF, "normal", "#4a4a4a", tx, 0) : null;
  const h = foto + 2 * pad;
  const blocoH = nome.h + (func ? 14 + func.h : 0);
  const y0 = (h - blocoH) / 2;
  const tNome = texto(c.nome, tamNome, "forte", TINTA, tx, y0);
  const textos = [tNome];
  if (func) textos.push(texto(c.funcao!, tamF, "normal", "#4a4a4a", tx, y0 + nome.h + 14));
  const w = Math.ceil(tx + Math.max(...textos.map((t) => t.w)) + pad + 22);
  for (const s of [c.nome, c.funcao ?? ""]) {
    const f = caracteresFaltando(s, "forte");
    if (f.length) avisos.push(`${c.id}: sem largura para ${f.join("")}`);
  }
  const m = cena.margem ?? MARGEM;
  const x = c.pos ? c.pos[0] : c.lado === "direita" ? cena.largura - 96 - w : 96;
  const y = c.pos ? c.pos[1] : cena.altura - 96 - h;
  if (x < m || y < m || x + w > cena.largura - m || y + h > cena.altura - m) avisos.push(`${c.id}: cartão encosta na margem`);
  // tudo em coordenadas do quadro
  const desloca = (t: Texto): Texto => ({ ...t, x: t.x + x, y: t.y + y, base: t.base + y });
  // recorte "cover" com o rosto no foco
  const [iw, ih] = c.fotoTam ?? [foto, foto];
  const esc = Math.max(foto / iw, foto / ih);
  const [fx, fy] = c.fotoFoco ?? [0.5, 0.3];
  const dw = iw * esc, dh = ih * esc;
  const ix = Math.min(0, Math.max(foto - dw, foto / 2 - fx * dw)), iy = Math.min(0, Math.max(foto - dh, foto / 2 - fy * dh));
  const fxp = x + barra + pad, fyp = y + pad;
  return {
    c: { ...c, cor, pb },
    cartao: { x, y, w, h, r: 6, cor: "#ffffff", sombra: true },
    barra: { x, y, w: barra, h, cor },
    foto: { clip: { x: fxp, y: fyp, w: foto, h: foto }, r: 4, img: { x: fxp + ix, y: fyp + iy, w: dw, h: dh }, src: c.foto, pb },
    textos: textos.map(desloca),
    caixa: { x, y, w, h },
    dx0: c.lado === "direita" ? 40 : -40,
  };
}

function montarCapitulo(c: Capitulo, cena: CenaCartoes, avisos: string[]): CapituloM {
  const cor = c.cor ?? COR, fundo = c.fundo ?? "#f3f1ec";
  const W = cena.largura, H = cena.altura, maxW = W - 2 * 160;
  const parte = `PARTE ${String(c.numero).padStart(2, "0")}`;
  const tParte = texto(parte, 64, "forte", cor, 0, 0);
  // título: uma linha até 110 px de corpo; senão, duas linhas equilibradas
  let linhas = [c.titulo];
  let tam = 168;
  while (tam > 110 && larguraTexto(c.titulo, tam, "forte") > maxW) tam -= 2;
  if (larguraTexto(c.titulo, tam, "forte") > maxW) {
    const ps = c.titulo.split(" ");
    let melhor = 1, pior = Infinity;
    for (let i = 1; i < ps.length; i++) {
      const a = larguraTexto(ps.slice(0, i).join(" "), 100, "forte"), b = larguraTexto(ps.slice(i).join(" "), 100, "forte");
      if (Math.max(a, b) < pior) { pior = Math.max(a, b); melhor = i; }
    }
    linhas = [ps.slice(0, melhor).join(" "), ps.slice(melhor).join(" ")];
    tam = 150;
    while (tam > 60 && Math.max(...linhas.map((l) => larguraTexto(l, tam, "forte"))) > maxW) tam -= 2;
    if (Math.max(...linhas.map((l) => larguraTexto(l, tam, "forte"))) > maxW) avisos.push(`${c.id}: título não cabe nem em 2 linhas`);
  }
  const tLinhas = linhas.map((l) => texto(l, tam, "forte", TINTA, 0, 0));
  const tr = c.tracado ? { w: 420, h: 250 } : null;
  const gap1 = 44, gap2 = 22, entre = Math.round(tam * 0.08);
  const blocoH = (tr ? tr.h + gap1 : 0) + tParte.h + gap2 + tLinhas.reduce((s, t) => s + t.h, 0) + entre * (tLinhas.length - 1);
  let y = (H - blocoH) / 2;
  let tracado: CapituloM["tracado"];
  if (tr && c.tracado) {
    const s = Math.min(tr.w / c.tracado.largura, tr.h / c.tracado.altura);
    const w = c.tracado.largura * s, h = c.tracado.altura * s;
    const x = (W - w) / 2, yy = y + (tr.h - h) / 2;
    tracado = { d: c.tracado.d, transform: `translate(${n2(x)} ${n2(yy)}) scale(${s.toFixed(5)})`, caixa: { x, y: yy, w, h }, larg: 9 / s };
    y += tr.h + gap1;
  }
  const textos: Texto[] = [];
  textos.push(texto(parte, 64, "forte", cor, (W - tParte.w) / 2, y));
  y += tParte.h + gap2;
  for (const t of tLinhas) {
    textos.push(texto(t.texto, tam, "forte", TINTA, (W - t.w) / 2, y));
    y += t.h + entre;
  }
  for (const s of [c.titulo]) {
    const f = caracteresFaltando(s, "forte");
    if (f.length) avisos.push(`${c.id}: sem largura para ${f.join("")}`);
  }
  return { c: { ...c, cor, fundo }, textos, tracado, caixa: { x: 0, y: 0, w: W, h: H } };
}

/** posição da âncora da tag no tempo t (interpolação linear da trilha) */
export function ancoraTag(c: Tag, t: number): P {
  const a = c.ancora;
  if (typeof a[0] === "number") return a as P;
  const tr = a as { t: number; x: number; y: number }[];
  if (t <= tr[0].t) return [tr[0].x, tr[0].y];
  const n = tr.length - 1;
  if (t >= tr[n].t) return [tr[n].x, tr[n].y];
  let i = 0;
  while (t > tr[i + 1].t) i++;
  const u = (t - tr[i].t) / (tr[i + 1].t - tr[i].t);
  return [tr[i].x + (tr[i + 1].x - tr[i].x) * u, tr[i].y + (tr[i + 1].y - tr[i].y) * u];
}

const DIRS = { ne: [0.55, -0.85], no: [-0.55, -0.85], se: [0.55, 0.85], so: [-0.55, 0.85] } as const;
const PAD_X = 18, PAD_Y = 12, LISTRA = 6;

/** caixa da tag para âncora p e lado (sem empurrar) */
function caixaTag(m: Pick<TagM, "w" | "h" | "lado"> & { perna: number }, p: P): Caixa {
  const [ux, uy] = DIRS[m.lado];
  const ex = p[0] + ux * m.perna, ey = p[1] + uy * m.perna; // ponta da perninha
  const x = ux > 0 ? ex : ex - m.w;
  const y = uy < 0 ? ey - m.h : ey;
  return { x, y, w: m.w, h: m.h };
}

function montarTag(c: Tag, cena: CenaCartoes, avisos: string[]): TagM {
  const cor = c.cor ?? COR, perna = c.perna ?? 110;
  const tx = texto(c.texto, 32, "medio", TINTA, 0, 0);
  const w = Math.ceil(LISTRA + PAD_X + tx.w + PAD_X), h = Math.ceil(tx.h + 2 * PAD_Y);
  const f = caracteresFaltando(c.texto, "medio");
  if (f.length) avisos.push(`${c.id}: sem largura para ${f.join("")}`);
  const marg = cena.margem ?? MARGEM;
  const ordem: TagM["lado"][] = !c.lado || c.lado === "auto" ? ["ne", "no", "se", "so"] : [c.lado];
  let escolhido: TagM["lado"] | null = null;
  let melhor: TagM["lado"] = ordem[0], menor = Infinity;
  for (const lado of ordem) {
    let pior = 0;
    for (let q = Math.floor(c.em * cena.fps); q <= Math.ceil(c.ate * cena.fps); q++) {
      const b = caixaTag({ w, h, lado, perna }, ancoraTag(c, q / cena.fps));
      pior = Math.max(pior, marg - b.x, marg - b.y, b.x + b.w - (cena.largura - marg), b.y + b.h - (cena.altura - marg));
    }
    if (pior <= 0) { escolhido = lado; break; }
    if (pior < menor) { menor = pior; melhor = lado; }
  }
  if (!escolhido) avisos.push(`${c.id}: nenhum lado cabe o tempo todo; caixa empurrada para dentro (até ${menor.toFixed(0)} px)`);
  return { c: { ...c, cor, perna }, lado: escolhido ?? melhor, empurrada: !escolhido, w, h, texto: tx };
}

export function montarCartoes(cena: CenaCartoes): MontadaCartoes {
  const avisos: string[] = [];
  const itens = cena.cartoes.map((c) => ({
    tipo: c.tipo,
    m: c.tipo === "pessoa" ? montarPessoa(c, cena, avisos) : c.tipo === "capitulo" ? montarCapitulo(c, cena, avisos) : montarTag(c, cena, avisos),
  }));
  return { cena, itens, avisos };
}

// ---------------------------------------------------------------- estado por quadro
const n2 = (x: number) => Math.round(x * 100) / 100;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function svgTexto(t: Texto, dx = 0, dy = 0): string {
  const L = LARGURAS[t.estilo];
  return `<text x="${n2(t.x + dx)}" y="${n2(t.base + dy)}" font-family="Bahnschrift" font-size="${t.tam}" fill="${t.cor}" ` +
    `style="font-variation-settings:'wght' ${L.wght},'wdth' ${L.wdth};font-weight:${L.wght};font-stretch:${L.wdth}%;font-kerning:none;font-feature-settings:'kern' 0,'liga' 0">${esc(t.texto)}</text>`;
}
function rr(x: number, y: number, w: number, h: number, r: number): string {
  return `M${n2(x + r)} ${n2(y)}H${n2(x + w - r)}A${r} ${r} 0 0 1 ${n2(x + w)} ${n2(y + r)}V${n2(y + h - r)}A${r} ${r} 0 0 1 ${n2(x + w - r)} ${n2(y + h)}` +
    `H${n2(x + r)}A${r} ${r} 0 0 1 ${n2(x)} ${n2(y + h - r)}V${n2(y + r)}A${r} ${r} 0 0 1 ${n2(x + r)} ${n2(y)}Z`;
}
/** defs comuns (sombra suave do cartão); cada SVG de cartão já as inclui */
const SOMBRA = (id: string) => `<filter id="${id}" x="-20%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.16"/></filter>`;

export type CartaoEstado = {
  id: string; tipo: Cartao["tipo"]; opacidade: number;
  /** caixa ocupada no quadro neste tempo (cartão + ponto + perninha), já com o deslize */
  caixa: Caixa;
  /** caixas de texto (tinta) no quadro, já com o deslize */
  textos: Caixa[];
  /** só tag: ponto, ponta da perninha, caixa da etiqueta e lado */
  tag?: { ancora: P; ponta: P; caixa: Caixa; lado: string; empurrada: boolean };
  /** SVG do cartão (grupo <g>), coordenadas do quadro */
  svg: string;
};

function estadoPessoa(p: PessoaM, t: number): CartaoEstado | null {
  const op = envelope(p.c, t, 0.3, 0.25);
  if (op <= 0) return null;
  const dx = p.dx0 * (1 - saiCubica((t - p.c.em) / 0.3));
  const id = `cp-${p.c.id}`;
  const f = p.foto;
  const foto = f.src
    ? `<image href="${esc(f.src)}" x="${n2(f.img.x)}" y="${n2(f.img.y)}" width="${n2(f.img.w)}" height="${n2(f.img.h)}" preserveAspectRatio="none" clip-path="url(#${id}-r)"${f.pb ? ` style="filter:grayscale(1) contrast(1.12)"` : ""}/>`
    : `<g clip-path="url(#${id}-r)"><rect x="${f.clip.x}" y="${f.clip.y}" width="${f.clip.w}" height="${f.clip.h}" fill="#c9c7c2"/>` +
      `<circle cx="${f.clip.x + f.clip.w / 2}" cy="${f.clip.y + f.clip.h * 0.4}" r="${f.clip.w * 0.2}" fill="#8d8b87"/>` +
      `<ellipse cx="${f.clip.x + f.clip.w / 2}" cy="${f.clip.y + f.clip.h}" rx="${f.clip.w * 0.36}" ry="${f.clip.h * 0.32}" fill="#8d8b87"/></g>`;
  const k = p.cartao;
  const svg = `<g opacity="${op.toFixed(4)}" transform="translate(${n2(dx)} 0)"><defs>${SOMBRA(id + "-s")}` +
    `<clipPath id="${id}-r"><path d="${rr(f.clip.x, f.clip.y, f.clip.w, f.clip.h, f.r)}"/></clipPath></defs>` +
    `<path d="${rr(k.x, k.y, k.w, k.h, k.r ?? 0)}" fill="${k.cor}" filter="url(#${id}-s)"/>` +
    `<rect x="${p.barra.x}" y="${p.barra.y}" width="${p.barra.w}" height="${p.barra.h}" fill="${p.barra.cor}"/>` +
    foto + p.textos.map((tx) => svgTexto(tx)).join("") + `</g>`;
  return {
    id: p.c.id, tipo: "pessoa", opacidade: op, caixa: { ...p.caixa, x: p.caixa.x + dx },
    textos: p.textos.map((tx) => ({ x: tx.x + dx, y: tx.y, w: tx.w, h: tx.h })), svg,
  };
}

function estadoCapitulo(c: CapituloM, t: number, cena: CenaCartoes): CartaoEstado | null {
  const op = envelope(c.c, t, 0.2, 0.3);
  if (op <= 0) return null;
  const dy = 18 * (1 - saiCubica((t - c.c.em - 0.05) / 0.4));
  let svg = `<g opacity="${op.toFixed(4)}"><rect x="0" y="0" width="${cena.largura}" height="${cena.altura}" fill="${c.c.fundo}"/>`;
  if (c.tracado) {
    const k = suave((t - c.c.em - 0.15) / 1.3);
    svg += `<g transform="${c.tracado.transform}"><path d="${esc(c.tracado.d)}" fill="none" stroke="${c.c.cor}" stroke-width="${n2(c.tracado.larg)}" ` +
      `stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="${(1 - k).toFixed(5)}" opacity="${k > 0 ? 1 : 0}"/></g>`;
  }
  svg += c.textos.map((tx, i) => svgTexto(tx, 0, i === 0 ? 0 : dy)).join("") + `</g>`;
  return {
    id: c.c.id, tipo: "capitulo", opacidade: op, caixa: c.caixa,
    textos: c.textos.map((tx, i) => ({ x: tx.x, y: tx.y + (i === 0 ? 0 : dy), w: tx.w, h: tx.h })), svg,
  };
}

/** ponto da caixa mais perto de p (fim da perninha) */
function pertoNaCaixa(b: Caixa, p: P): P {
  return [Math.max(b.x, Math.min(b.x + b.w, p[0])), Math.max(b.y, Math.min(b.y + b.h, p[1]))];
}

export function geometriaTag(g: TagM, t: number, cena: CenaCartoes): { ancora: P; caixa: Caixa; ponta: P } {
  const a = ancoraTag(g.c, t);
  const b = caixaTag({ w: g.w, h: g.h, lado: g.lado, perna: g.c.perna }, a);
  if (g.empurrada) {
    const m = cena.margem ?? MARGEM;
    b.x = Math.max(m, Math.min(cena.largura - m - b.w, b.x));
    b.y = Math.max(m, Math.min(cena.altura - m - b.h, b.y));
  }
  return { ancora: a, caixa: b, ponta: pertoNaCaixa(b, a) };
}

function estadoTag(g: TagM, t: number, cena: CenaCartoes): CartaoEstado | null {
  if (t < g.c.em || t > g.c.ate) return null;
  const sai = suave((g.c.ate - t) / 0.2);
  const u = t - g.c.em;
  const kPonto = saiCubica(u / 0.14), kPerna = suave((u - 0.08) / 0.18), kCaixa = suave((u - 0.2) / 0.14);
  const { ancora: a, caixa: b, ponta } = geometriaTag(g, t, cena);
  const tx = { ...g.texto, x: b.x + LISTRA + PAD_X, y: b.y + PAD_Y, base: b.y + PAD_Y + (g.texto.base - g.texto.y) };
  const px = a[0] + (ponta[0] - a[0]) * kPerna, py = a[1] + (ponta[1] - a[1]) * kPerna;
  const id = `tg-${g.c.id}`;
  const svg = `<g opacity="${sai.toFixed(4)}"><defs>${SOMBRA(id + "-s")}</defs>` +
    (kPerna > 0 ? `<line x1="${n2(a[0])}" y1="${n2(a[1])}" x2="${n2(px)}" y2="${n2(py)}" stroke="${g.c.cor}" stroke-width="3.5" stroke-linecap="round"/>` : "") +
    `<g opacity="${kCaixa.toFixed(4)}"><rect x="${n2(b.x)}" y="${n2(b.y)}" width="${b.w}" height="${b.h}" rx="5" fill="#ffffff" filter="url(#${id}-s)"/>` +
    `<rect x="${n2(b.x)}" y="${n2(b.y)}" width="${LISTRA}" height="${b.h}" fill="${g.c.cor}"/>${svgTexto(tx)}</g>` +
    `<circle cx="${n2(a[0])}" cy="${n2(a[1])}" r="${n2(8 * kPonto)}" fill="${g.c.cor}" stroke="#ffffff" stroke-width="${n2(3 * kPonto)}"/></g>`;
  const ext = 8 + 3 / 2;
  const x0 = Math.min(b.x, a[0] - ext), y0 = Math.min(b.y, a[1] - ext);
  const x1 = Math.max(b.x + b.w, a[0] + ext), y1 = Math.max(b.y + b.h, a[1] + ext);
  return {
    id: g.c.id, tipo: "tag", opacidade: sai * kCaixa, caixa: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 },
    textos: [{ x: tx.x, y: tx.y, w: tx.w, h: tx.h }], tag: { ancora: a, ponta, caixa: b, lado: g.lado, empurrada: g.empurrada }, svg,
  };
}

export function estadoCartoes(m: MontadaCartoes, t: number): CartaoEstado[] {
  const out: CartaoEstado[] = [];
  for (const it of m.itens) {
    const e = it.tipo === "pessoa" ? estadoPessoa(it.m as PessoaM, t)
      : it.tipo === "capitulo" ? estadoCapitulo(it.m as CapituloM, t, m.cena) : estadoTag(it.m as TagM, t, m.cena);
    if (e) out.push(e);
  }
  return out;
}

/** SVG inteiro (quadro) com todos os cartões ativos em t: o que os dois motores desenham */
export function svgCartoes(m: MontadaCartoes, t: number): string {
  return estadoCartoes(m, t).map((e) => e.svg).join("");
}

// ---------------------------------------------------------------- verificação
export type RelatorioCartoes = {
  quadros: number; falhas: string[]; avisos: string[];
  porCartao: Record<string, { quadros: number; folgaMinQuadro: number; lados: string[]; textoForaDoCartao: number; pernaErroMax?: number }>;
};

/**
 * Quadro a quadro: (1) tudo do cartão dentro do quadro e da margem segura (tag e pessoa; capítulo é tela cheia);
 * (2) texto dentro do cartão/etiqueta (e do título dentro da área útil); (3) tag: perninha começa no ponto e termina na
 * borda da etiqueta, com o mesmo lado o tempo todo (sem pular de lado); (4) pessoa: foto dentro do cartão e coberta.
 */
export function checarCartoes(m: MontadaCartoes): RelatorioCartoes {
  const { fps, duracao, largura: W, altura: H } = m.cena;
  const marg = m.cena.margem ?? MARGEM;
  const nq = Math.round(duracao * fps) + 1;
  const rel: RelatorioCartoes = { quadros: nq, falhas: [], avisos: [...m.avisos], porCartao: {} };
  const dentro = (a: Caixa, b: Caixa, tol = 1e-6) => a.x >= b.x - tol && a.y >= b.y - tol && a.x + a.w <= b.x + b.w + tol && a.y + a.h <= b.y + b.h + tol;
  for (let q = 0; q < nq; q++) {
    for (const e of estadoCartoes(m, q / fps)) {
      const r = (rel.porCartao[e.id] ??= { quadros: 0, folgaMinQuadro: Infinity, lados: [], textoForaDoCartao: 0 });
      r.quadros++;
      const fol = (c: Caixa) => Math.min(c.x, c.y, W - (c.x + c.w), H - (c.y + c.h));
      // tag: a ETIQUETA respeita a margem segura; o ponto fica onde a pista está (só precisa estar no quadro se a
      // própria âncora estiver)
      const folga = fol(e.tag ? e.tag.caixa : e.caixa);
      r.folgaMinQuadro = Math.min(r.folgaMinQuadro, folga);
      if (e.tipo !== "capitulo" && folga < marg - 1e-6) rel.falhas.push(`${e.id}: sai da margem segura (folga ${folga.toFixed(1)} px, q${q})`);
      const ancDentro = !e.tag || (e.tag.ancora[0] >= 10 && e.tag.ancora[1] >= 10 && e.tag.ancora[0] <= W - 10 && e.tag.ancora[1] <= H - 10);
      if (ancDentro && fol(e.caixa) < -1e-6) rel.falhas.push(`${e.id}: sai do quadro (q${q})`);
      const cont = e.tipo === "tag" ? e.tag!.caixa : e.tipo === "capitulo" ? { x: 160, y: 0, w: W - 320, h: H } : e.caixa;
      for (const tx of e.textos) if (!dentro(tx, cont)) { r.textoForaDoCartao++; rel.falhas.push(`${e.id}: texto fora do cartão (q${q})`); }
      if (e.tag) {
        if (!r.lados.includes(e.tag.lado)) r.lados.push(e.tag.lado);
        const b = e.tag.caixa, p = e.tag.ponta;
        const naBorda = Math.min(Math.abs(p[0] - b.x), Math.abs(p[0] - b.x - b.w), Math.abs(p[1] - b.y), Math.abs(p[1] - b.y - b.h));
        r.pernaErroMax = Math.max(r.pernaErroMax ?? 0, naBorda);
        const comp = Math.hypot(p[0] - e.tag.ancora[0], p[1] - e.tag.ancora[1]);
        if (!e.tag.empurrada && comp < 40) rel.falhas.push(`${e.id}: perninha curta (${comp.toFixed(1)} px, q${q})`);
      }
    }
  }
  for (const [id, r] of Object.entries(rel.porCartao)) {
    if (r.lados.length > 1) rel.falhas.push(`${id}: tag trocou de lado (${r.lados})`);
    if ((r.pernaErroMax ?? 0) > 1e-6) rel.falhas.push(`${id}: perninha não termina na borda da etiqueta (${r.pernaErroMax})`);
  }
  for (const it of m.itens) if (it.tipo === "pessoa") {
    const p = it.m as PessoaM;
    if (!dentro(p.foto.clip, p.cartao)) rel.falhas.push(`${p.c.id}: foto fora do cartão`);
    if (!dentro(p.foto.clip, p.foto.img, 1e-3)) rel.falhas.push(`${p.c.id}: foto não cobre o recorte`);
  }
  rel.falhas = [...new Set(rel.falhas)].slice(0, 40);
  return rel;
}
