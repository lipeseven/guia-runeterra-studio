// kit/transicoes: corte, fade, wipe (cortina com barra na cor) e zoom-through entre duas cenas, com duração EXATA em
// quadros (60 q/s) e o SFX do kit/sfx (whoosh/impacto) ancorado no quadro de maior movimento. Núcleo sem motor:
// devolve, por quadro, o estilo de cada camada (opacidade, transform, recorte, desfoque); Remotion e HyperFrames só
// aplicam esses estilos em duas <div> (cena que sai e cena que entra).
//   const ts = montarTransicoes([{ tipo: "wipe", em: 3 }, ...], 60);
//   estadoSequencia(ts, q) → [{ cena: índice, estilo }, ...] (de baixo para cima) + barra
//   pedidosSfx(ts) → pedidos para Banco.dePedidos do kit/sfx (pico do som no quadro de pico)
export type TipoTransicao = "corte" | "fade" | "wipe" | "zoom";
export type Categoria = "whoosh" | "impacto";

/** duração padrão em quadros a 60 q/s (quadros INTERMEDIÁRIOS: nem a cena A pura nem a B pura) */
export const QUADROS: Record<TipoTransicao, number> = { corte: 0, fade: 18, wipe: 24, zoom: 30 };
/** SFX padrão por tipo (null = sem som; corte seco por padrão, peça "impacto" quando o corte for uma revelação) */
export const SFX_PADRAO: Record<TipoTransicao, Categoria | null> = { corte: null, fade: null, wipe: "whoosh", zoom: "whoosh" };

export type Transicao = {
  tipo: TipoTransicao;
  /** s: instante do corte (arredondado ao quadro); a transição fica centrada nele */
  em: number;
  /** quadros intermediários (padrão por tipo; corte = 0) */
  quadros?: number;
  /** wipe: para onde a borda anda (padrão "direita": a cena nova entra da esquerda para a direita) */
  direcao?: "direita" | "esquerda" | "baixo" | "cima";
  /** wipe: cor da barra que corre na borda (padrão vermelho F1) */
  cor?: string;
  /** SFX: categoria, ou false para nenhum (padrão SFX_PADRAO) */
  sfx?: Categoria | false;
  intensidade?: number;
  /** força uma variação do banco (id do catálogo) */
  variacao?: string;
};
export type TransicaoM = {
  t: Required<Omit<Transicao, "sfx" | "variacao">> & { sfx: Categoria | null; variacao?: string };
  fps: number;
  /** quadros intermediários */
  n: number;
  /** quadro do corte: a partir dele a cena B domina (corte seco: 1º quadro de B) */
  qCorte: number;
  /** primeiro quadro intermediário (= qCorte − ⌊n/2⌋) */
  q0: number;
  /** quadro de maior movimento (onde cai o pico do SFX) e seu tempo exato */
  qPico: number;
  tPico: number;
};

export const LARGURA = 1920, ALTURA = 1080;

const lim = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => { x = lim(x); return x * x * (3 - 2 * x); };
/**
 * Curva das transições: 70% suave + 30% linear. Pura suave deixaria o 1º e o último quadro intermediário quase iguais
 * às cenas puras (a transição "pareceria" mais curta que a duração declarada); com 30% linear, cada quadro
 * intermediário anda pelo menos ~2% (a duração MEDIDA nos pixels é a declarada).
 */
export const curva = (p: number) => 0.7 * smooth(p) + 0.3 * lim(p);

export function montarTransicao(t: Transicao, fps = 60): TransicaoM {
  const n = t.tipo === "corte" ? 0 : Math.max(2, Math.round(t.quadros ?? (QUADROS[t.tipo] * fps) / 60));
  const qCorte = Math.round(t.em * fps);
  const q0 = qCorte - Math.floor(n / 2);
  const sfx = t.sfx === false ? null : t.sfx ?? SFX_PADRAO[t.tipo];
  const tm: TransicaoM = {
    t: { tipo: t.tipo, em: qCorte / fps, quadros: n, direcao: t.direcao ?? "direita", cor: t.cor ?? "#e10600", intensidade: t.intensidade ?? 0.7, sfx, variacao: t.variacao },
    fps, n, qCorte, q0, qPico: qCorte, tPico: qCorte / fps,
  };
  if (n > 0) {
    // pico = quadro em que o progresso mais anda (empate: o mais perto do corte)
    let melhor = -1;
    for (let q = q0; q < q0 + n; q++) {
      const d = progresso(tm, q) - progresso(tm, q - 1);
      if (d > melhor + 1e-12 || (Math.abs(d - melhor) <= 1e-12 && Math.abs(q - qCorte) < Math.abs(tm.qPico - qCorte))) { melhor = d; tm.qPico = q; }
    }
    tm.tPico = tm.qPico / fps;
  }
  return tm;
}
export const montarTransicoes = (ts: Transicao[], fps = 60) => ts.map((t) => montarTransicao(t, fps));

/** progresso 0..1 no quadro q (0 = A pura, 1 = B pura; intermediários estritamente entre os dois) */
export function progresso(tm: TransicaoM, q: number): number {
  if (tm.n === 0) return q >= tm.qCorte ? 1 : 0;
  if (q < tm.q0) return 0;
  if (q >= tm.q0 + tm.n) return 1;
  return curva((q - tm.q0 + 1) / (tm.n + 1));
}

export type Camada = { opacidade: number; escala: number; tx: number; ty: number; blur: number; recorte: [number, number, number, number] | null };
export type EstadoTransicao = { a: Camada | null; b: Camada | null; barra: { x: number; y: number; w: number; h: number; cor: string } | null };

const PURA: Camada = { opacidade: 1, escala: 1, tx: 0, ty: 0, blur: 0, recorte: null };

/** estilo das duas cenas no quadro q (a = cena que sai, b = cena que entra; null = não desenhar) */
export function estadoTransicao(tm: TransicaoM, q: number, W = LARGURA, H = ALTURA): EstadoTransicao {
  const e = progresso(tm, q);
  if (e <= 0) return { a: { ...PURA }, b: null, barra: null };
  if (e >= 1) return { a: null, b: { ...PURA }, barra: null };
  switch (tm.t.tipo) {
    case "fade":
      return { a: { ...PURA }, b: { ...PURA, opacidade: e }, barra: null };
    case "wipe": {
      // recorte inset (cima, direita, baixo, esquerda) em %: a cena B aparece atrás da borda que anda
      const r = (1 - e) * 100;
      const rec: Record<string, [number, number, number, number]> = {
        direita: [0, r, 0, 0], esquerda: [0, 0, 0, r], baixo: [0, 0, r, 0], cima: [r, 0, 0, 0],
      };
      const bw = 14;
      const d = tm.t.direcao;
      const barra = d === "direita" ? { x: e * W - bw / 2, y: 0, w: bw, h: H } : d === "esquerda" ? { x: (1 - e) * W - bw / 2, y: 0, w: bw, h: H }
        : d === "baixo" ? { x: 0, y: e * H - bw / 2, w: W, h: bw } : { x: 0, y: (1 - e) * H - bw / 2, w: W, h: bw };
      return { a: { ...PURA }, b: { ...PURA, recorte: rec[d] }, barra: { ...barra, cor: tm.t.cor } };
    }
    case "zoom": {
      // A mergulha (escala 1 → 2,4, desfoca); B já vem "de perto" (1,6 → 1) saindo do desfoque, sem borda à mostra;
      // a troca acontece em volta de e = 0,5
      const a = lim(e / 0.58);
      const b = lim((e - 0.42) / 0.58);
      const opB = smooth((e - 0.42) / 0.16);
      return {
        a: opB >= 1 ? null : { ...PURA, escala: 1 + 1.4 * a, blur: 14 * a * a },
        b: opB <= 0 ? null : { ...PURA, opacidade: opB, escala: 1 + 0.6 * (1 - b), blur: 14 * (1 - b) * (1 - b) },
        barra: null,
      };
    }
    default:
      return { a: null, b: { ...PURA }, barra: null };
  }
}

/** CSS de uma camada (camelCase; o adaptador HyperFrames converte) — o mesmo nos dois motores */
export function estiloCamada(c: Camada): Record<string, string> {
  const s: Record<string, string> = { position: "absolute", left: "0", top: "0", width: "100%", height: "100%", opacity: c.opacidade.toFixed(4) };
  if (c.escala !== 1 || c.tx || c.ty) { s.transform = `translate(${c.tx.toFixed(2)}px, ${c.ty.toFixed(2)}px) scale(${c.escala.toFixed(5)})`; s.transformOrigin = "50% 50%"; }
  if (c.blur > 0.01) s.filter = `blur(${c.blur.toFixed(3)}px)`;
  if (c.recorte) s.clipPath = `inset(${c.recorte.map((v) => v.toFixed(4) + "%").join(" ")})`;
  return s;
}

// ---------------------------------------------------------------- sequência de cenas
export type ItemSequencia = { cena: number; estilo: Record<string, string> };
/**
 * Cenas 0..N ligadas pelas transições ts (ts[i] liga a cena i à cena i+1; em ordem e sem sobreposição — checar).
 * Devolve as camadas a desenhar no quadro q, de baixo para cima, e a barra do wipe (se houver).
 */
export function estadoSequencia(ts: TransicaoM[], q: number): { itens: ItemSequencia[]; barra: EstadoTransicao["barra"] } {
  for (let i = 0; i < ts.length; i++) {
    const tm = ts[i];
    if (tm.n > 0 && q >= tm.q0 && q < tm.q0 + tm.n) {
      const e = estadoTransicao(tm, q);
      const itens: ItemSequencia[] = [];
      if (e.a) itens.push({ cena: i, estilo: estiloCamada(e.a) });
      if (e.b) itens.push({ cena: i + 1, estilo: estiloCamada(e.b) });
      return { itens, barra: e.barra };
    }
  }
  const cena = ts.filter((tm) => q >= tm.q0 + tm.n && (tm.n > 0 || q >= tm.qCorte)).length;
  return { itens: [{ cena, estilo: estiloCamada(PURA) }], barra: null };
}

/** pedidos para o kit/sfx (`Banco.dePedidos`): o PICO do som cai exatamente no quadro de pico da transição */
export function pedidosSfx(ts: TransicaoM[]): { categoria: Categoria; t: number; intensidade: number; variacao?: string }[] {
  return ts.filter((tm) => tm.t.sfx).map((tm) => ({
    categoria: tm.t.sfx!, t: tm.tPico, intensidade: tm.t.intensidade, ...(tm.t.variacao ? { variacao: tm.t.variacao } : {}),
  }));
}

// ---------------------------------------------------------------- verificação
export type RelatorioTransicoes = {
  falhas: string[];
  transicoes: { tipo: TipoTransicao; quadros: number; quadrosMedidos: number; q0: number; qCorte: number; qPico: number; tPico: number; passoMin: number; primeiro: number; ultimo: number }[];
};

const igualPura = (c: Camada | null) => !!c && c.opacidade === 1 && c.escala === 1 && c.tx === 0 && c.ty === 0 && c.blur === 0 && c.recorte === null;

/**
 * Para cada transição: (1) duração inteira em quadros = a declarada; (2) quadros cujo estado não é "A pura" nem
 * "B pura" = exatamente n; (3) progresso estritamente crescente, com cada passo ≥ 1% e 1º/último quadro a ≥ 1% das
 * pontas (mensurável); (4) pico dentro da transição e no quadro de maior passo; tPico·fps inteiro; (5) sem sobreposição.
 */
export function checarTransicoes(ts: TransicaoM[]): RelatorioTransicoes {
  const rel: RelatorioTransicoes = { falhas: [], transicoes: [] };
  ts.forEach((tm, i) => {
    const ini = tm.n > 0 ? tm.q0 : tm.qCorte;
    let medidos = 0, passoMin = 1, ant = 0;
    for (let q = ini - 10; q < ini + tm.n + 10; q++) {
      const e = estadoTransicao(tm, q);
      const pureA = igualPura(e.a) && e.b === null && e.barra === null;
      const pureB = igualPura(e.b) && e.a === null && e.barra === null;
      if (!pureA && !pureB) medidos++;
      const p = progresso(tm, q);
      if (q > ini - 10 && p > ant) passoMin = Math.min(passoMin, p - ant);
      if (p < ant) rel.falhas.push(`${i} ${tm.t.tipo}: progresso volta (q${q})`);
      ant = p;
    }
    const primeiro = tm.n ? progresso(tm, tm.q0) : 1, ultimo = tm.n ? progresso(tm, tm.q0 + tm.n - 1) : 1;
    if (medidos !== tm.n) rel.falhas.push(`${i} ${tm.t.tipo}: ${medidos} quadros intermediários (declarado ${tm.n})`);
    if (tm.t.tipo !== "corte" && tm.n !== Math.round(tm.t.quadros)) rel.falhas.push(`${i}: duração não inteira`);
    if (tm.n && (passoMin < 0.01 || primeiro < 0.01 || ultimo > 0.99)) rel.falhas.push(`${i} ${tm.t.tipo}: passo ${passoMin.toFixed(4)}, pontas ${primeiro.toFixed(4)}/${ultimo.toFixed(4)}`);
    if (tm.n && (tm.qPico < tm.q0 || tm.qPico >= tm.q0 + tm.n)) rel.falhas.push(`${i}: pico fora da transição`);
    if (Math.abs(tm.tPico * tm.fps - Math.round(tm.tPico * tm.fps)) > 1e-9) rel.falhas.push(`${i}: pico fora do quadro`);
    if (i > 0) {
      const p = ts[i - 1];
      const fimAnt = p.n > 0 ? p.q0 + p.n : p.qCorte;
      if (ini < fimAnt + 1) rel.falhas.push(`${i}: sobrepõe a transição anterior`);
    }
    rel.transicoes.push({ tipo: tm.t.tipo, quadros: tm.n, quadrosMedidos: medidos, q0: tm.q0, qCorte: tm.qCorte, qPico: tm.qPico, tPico: tm.tPico, passoMin, primeiro, ultimo });
  });
  return rel;
}
