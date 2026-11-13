// GERADO por F1/horizontal/testes/graficos/rodar.py (esbuild de graficos.ts). Não editar à mão.
var Graficos = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // graficos.ts
  var graficos_exports = {};
  __export(graficos_exports, {
    FONTE_CSS: () => FONTE_CSS,
    METRICAS: () => METRICAS,
    TEMAS: () => TEMAS,
    checar: () => checar,
    contraste: () => contraste,
    corLegivel: () => corLegivel,
    destaqueAuto: () => destaqueAuto,
    distCursor: () => distCursor,
    estado: () => estado,
    fmt: () => fmt,
    larguraTexto: () => larguraTexto,
    metrica: () => metrica,
    montar: () => montar,
    vantagem: () => vantagem
  });
  var TEMAS = {
    claro: { nome: "claro", fundo: "#f2f1ed", tinta: "#151515", tinta2: "#5f5e5a", grade: "#dcdbd5", eixo: "#9c9b96", destaque: "#d40000" },
    escuro: { nome: "escuro", fundo: "#141518", tinta: "#f2f1ed", tinta2: "#a9a8a3", grade: "#2d2e33", eixo: "#64656a", destaque: "#ff4a3d" }
  };
  var FONTE_CSS = "'Segoe UI', Arial, sans-serif";
  function rgb(h) {
    const s = h.replace("#", "");
    return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16));
  }
  function hex(c) {
    return "#" + c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
  }
  function lum(h) {
    const [r, g, b] = rgb(h).map((v) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  function contraste(a, b) {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  }
  function corLegivel(cor, fundo, minimo = 3) {
    const alvo = lum(fundo) > 0.5 ? [0, 0, 0] : [255, 255, 255];
    let c = rgb(cor);
    for (let i = 0; i < 40 && contraste(hex(c), fundo) < minimo; i++) c = c.map((v, k) => v + (alvo[k] - v) * 0.06);
    return hex(c);
  }
  var LARG = null;
  function larguraTexto(texto, tam, peso) {
    var _a, _b;
    const tab = LARG.pesos[String(peso)] || LARG.pesos["400"];
    let w = 0;
    for (const ch of texto) w += (_b = (_a = tab[ch]) != null ? _a : tab["M"]) != null ? _b : 600;
    return w * tam / 1e3;
  }
  function caixaTexto(x, y, texto, tam, peso, ancora) {
    const w = larguraTexto(texto, tam, peso);
    const x0 = ancora === "start" ? x : ancora === "middle" ? x - w / 2 : x - w;
    return { x: x0, y: y - LARG.ascendente * tam, w, h: (LARG.ascendente + LARG.descendente) * tam };
  }
  function fmt(v, casas = 0, sinal = false) {
    const neg = v < 0 && Math.abs(v) >= 0.5 * 10 ** -casas;
    const [i, f] = Math.abs(v).toFixed(casas).split(".");
    const mil = i.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (neg ? "−" : sinal && v > 0 ? "+" : "") + mil + (f ? "," + f : "");
  }
  function cruza(a, b, folga = 0) {
    return a.x < b.x + b.w + folga && b.x < a.x + a.w + folga && a.y < b.y + b.h + folga && b.y < a.y + a.h + folga;
  }
  var lim = (v, a, b) => Math.max(a, Math.min(b, v));
  var suave = (k) => 0.5 - 0.5 * Math.cos(Math.PI * lim(k, 0, 1));
  function interp(xs, ys, x) {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
    let lo = 0, hi = xs.length - 1;
    while (hi - lo > 1) {
      const m = lo + hi >> 1;
      if (xs[m] <= x) lo = m;
      else hi = m;
    }
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / (xs[hi] - xs[lo]);
  }
  function ticks(v0, v1, alvo = 5) {
    var _a;
    const bruto = (v1 - v0) / alvo, p = 10 ** Math.floor(Math.log10(bruto));
    const passo = (_a = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= bruto * 0.8)) != null ? _a : 10 * p;
    const out = [];
    for (let v = Math.ceil(v0 / passo - 1e-9) * passo; v <= v1 + 1e-9; v += passo) out.push(Math.round(v / passo) * passo);
    return out;
  }
  function passoTick(v0, v1, alvo = 5) {
    const t = ticks(v0, v1, alvo);
    return t.length > 1 ? t[1] - t[0] : 1;
  }
  function indices(D, d0, d1) {
    const out = [];
    D.grade_d.forEach((d, i) => {
      if (d >= d0 - 1e-6 && d <= d1 + 1e-6) out.push(i);
    });
    return out;
  }
  var Construtor = class {
    constructor(spec, D) {
      __publicField(this, "els", []);
      __publicField(this, "avisos", []);
      __publicField(this, "eixos", []);
      __publicField(this, "textos", []);
      __publicField(this, "s");
      __publicField(this, "tema");
      __publicField(this, "A");
      __publicField(this, "B");
      __publicField(this, "corA");
      __publicField(this, "corB");
      __publicField(this, "spec");
      __publicField(this, "D");
      __publicField(this, "cursor", null);
      __publicField(this, "plot", null);
      var _a, _b;
      this.spec = spec;
      this.D = D;
      this.tema = TEMAS[(_a = spec.tema) != null ? _a : "claro"];
      this.s = (_b = spec.escala) != null ? _b : lim(Math.min(spec.area.w / 1700, spec.area.h / 920), 0.55, 1.3);
      [this.A, this.B] = D.pilotos;
      this.corA = corLegivel(this.A.cor, this.tema.fundo);
      this.corB = corLegivel(this.B.cor, this.tema.fundo);
      if (contraste(this.corA, this.corB) < 1.25) this.corB = corLegivel(this.B.cor, this.tema.fundo, 4.5);
    }
    get T() {
      return this.tema;
    }
    t(id, papel, x, y, texto, tam, peso, cor, ancora, em, dur = 0.2) {
      const e = {
        id: `${this.spec.id}:${id}`,
        grafico: this.spec.id,
        papel,
        tipo: "texto",
        x,
        y,
        texto,
        tam,
        peso,
        cor,
        ancora,
        caixa: caixaTexto(x, y, texto, tam, peso, ancora),
        em,
        dur
      };
      this.els.push(e);
      this.textos.push(e.caixa);
      return e;
    }
    /** cabe sem cruzar nenhum texto já posto (folga em px) e dentro da área */
    cabe(c, folga = 6 * this.s) {
      const a = this.spec.area;
      if (c.x < a.x || c.y < a.y || c.x + c.w > a.x + a.w || c.y + c.h > a.y + a.h) return false;
      return !this.textos.some((o) => cruza(o, c, folga));
    }
    linha(id, papel, pts, cor, largura, em, dur, revela, extra = {}) {
      const e = { id: `${this.spec.id}:${id}`, grafico: this.spec.id, papel, tipo: "linha", pts, cor, largura, em, dur, revela, ...extra };
      this.els.push(e);
      return e;
    }
    ret(id, papel, x, y, w, h, cor, opac, em, dur, revela, extra = {}) {
      const e = { id: `${this.spec.id}:${id}`, grafico: this.spec.id, papel, tipo: "ret", x, y, w, h, cor, opac, em, dur, revela, ...extra };
      this.els.push(e);
      return e;
    }
    /** título, subtítulo e legenda (amostra de linha + sigla) no topo; devolve o y de baixo do cabeçalho */
    cabecalho(titulo, subtitulo, legenda, larguraLegenda) {
      const { area } = this.spec, s = this.s, pad = 30 * s, em = this.spec.em;
      let y = area.y + pad + 44 * s * LARG.ascendente;
      this.t("titulo", "titulo", area.x + pad, y, titulo, 44 * s, 700, this.T.tinta, "start", em);
      if (legenda) {
        let x = area.x + area.w - pad - (larguraLegenda != null ? larguraLegenda : 0);
        for (const [P, cor, k] of [[this.B, this.corB, "b"], [this.A, this.corA, "a"]]) {
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
      return y + LARG.descendente * 25 * s + 14 * s;
    }
    rodape() {
      var _a;
      const { area } = this.spec, s = this.s, pad = 30 * s;
      const f = this.spec.fonte === false ? "" : (_a = this.spec.fonte) != null ? _a : this.D.fonte_curta;
      const y = area.y + area.h - pad * 0.6 - LARG.descendente * 18 * s;
      if (f) this.t("fonte", "fonte", area.x + pad, y, f, 18 * s, 400, this.T.tinta2, "start", this.spec.em);
      return y - LARG.ascendente * 18 * s - 10 * s;
    }
    /** fileiras de rótulos acima do gráfico: cada item vai na primeira fileira em que cabe (ou é omitido com aviso) */
    fileiras(itens, yBase, n, tam, x0, x1) {
      const out = [], alt = tam * 1.3;
      for (const it of itens) {
        let pos = null;
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
    rotulosFim(itens, x, tam, em, yMin, yMax) {
      const alt = tam * (LARG.ascendente + LARG.descendente) + 8 * this.s;
      const ord = itens.map((it) => ({ ...it, yc: it.y })).sort((a, b) => a.yc - b.yc);
      for (let it = 0; it < 30; it++) {
        let mexeu = false;
        for (let i = 1; i < ord.length; i++) {
          const sep = ord[i].yc - ord[i - 1].yc;
          if (sep < alt) {
            const m = (alt - sep) / 2;
            ord[i - 1].yc -= m;
            ord[i].yc += m;
            mexeu = true;
          }
        }
        const lo = yMin + alt / 2, hi = yMax - alt / 2;
        if (ord[0].yc < lo) {
          const m = lo - ord[0].yc;
          ord.forEach((o) => o.yc += m);
        }
        if (ord[ord.length - 1].yc > hi) {
          const m = ord[ord.length - 1].yc - hi;
          ord.forEach((o) => o.yc -= m);
        }
        if (!mexeu) break;
      }
      for (const o of ord) {
        const base = o.yc + tam * (LARG.ascendente - LARG.descendente) / 2;
        this.t(o.id, "legenda", x, base, o.texto, tam, 700, o.cor, "start", em);
      }
    }
  };
  function ritmoDe(spec, d0, d1, tDados) {
    var _a;
    if (spec.ritmo && spec.ritmo.length >= 2) return spec.ritmo.map((r) => ({ t: r.t, d: lim(r.d, d0, d1) }));
    const dur = (_a = spec.dur) != null ? _a : 3, n = 24;
    return Array.from({ length: n + 1 }, (_, i) => ({ t: tDados + dur * i / n, d: d0 + (d1 - d0) * suave(i / n) }));
  }
  function distCursor(r, t) {
    return interp(r.map((p) => p.t), r.map((p) => p.d), t);
  }
  function tempoEm(r, d) {
    for (let i = 1; i < r.length; i++) if (r[i].d >= d) {
      const a = r[i - 1], b = r[i];
      return b.d === a.d ? a.t : a.t + (d - a.d) / (b.d - a.d) * (b.t - a.t);
    }
    return r[r.length - 1].t;
  }
  function plano(c, plot, d0, d1, v0, v1, nomeY, unidadeY, fmtY, nFileiras, passoY) {
    var _a, _b, _c;
    const { spec, s, T } = c, em = spec.em;
    const xOf = (d) => plot.x + (d - d0) / (d1 - d0) * plot.w;
    const yOf = (v) => plot.y + plot.h - (v - v0) / (v1 - v0) * plot.h;
    const tDados = (_c = (_b = (_a = spec.ritmo) == null ? void 0 : _a[0]) == null ? void 0 : _b.t) != null ? _c : em + 0.55;
    const ritmo = ritmoDe(spec, d0, d1, tDados);
    const tFim = ritmo[ritmo.length - 1].t;
    const tEm = (d) => tempoEm(ritmo, d);
    c.eixos.push({ d0, d1, x0: plot.x, x1: plot.x + plot.w, v0, v1, y0: yOf(v0), y1: yOf(v1), nome: nomeY });
    const ty = [];
    if (passoY) for (let v = Math.ceil(v0 / passoY - 1e-9) * passoY; v <= v1 + 1e-9; v += passoY) ty.push(+v.toFixed(6));
    else ty.push(...ticks(v0, v1, 5));
    for (const v of ty) {
      c.linha(`grade-y-${v}`, "grade", [[plot.x, yOf(v)], [plot.x + plot.w, yOf(v)]], v === 0 ? T.eixo : T.grade, (v === 0 ? 2.5 : 1.5) * s, em + 0.1, 0.45, "x");
      c.t(`tick-y-${v}`, "eixo", plot.x - 12 * s, yOf(v) + 7 * s, fmtY(v), 20 * s, 400, T.tinta2, "end", em + 0.25);
    }
    c.t("unidade-y", "eixo", plot.x - 12 * s, plot.y - 26 * s, unidadeY, 20 * s, 600, T.tinta2, "end", em + 0.25);
    c.linha("base-x", "eixo", [[plot.x, plot.y + plot.h], [plot.x + plot.w, plot.y + plot.h]], T.eixo, 2 * s, em + 0.1, 0.45, "x");
    const px = passoTick(d0, d1, Math.max(3, Math.round(plot.w / 260)));
    for (let d = Math.ceil(d0 / px) * px; d <= d1 + 1e-6; d += px) {
      c.t(`tick-x-${d}`, "eixo", xOf(d), plot.y + plot.h + 28 * s, fmt(d), 20 * s, 400, T.tinta2, "middle", em + 0.25);
    }
    c.t("unidade-x", "eixo", plot.x + plot.w, plot.y + plot.h + 58 * s, "distância na volta (m)", 20 * s, 600, T.tinta2, "end", em + 0.25);
    const rotulos = [];
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
  function serie(P, Pi, campo, ids, degrau = false, map = (v) => v) {
    const D = P.c.D, arr = Pi[campo];
    const pts = [];
    ids.forEach((i, j) => {
      const x = P.xOf(D.grade_d[i]), y = P.yOf(map(arr[i]));
      if (degrau && j > 0 && arr[i] !== arr[ids[j - 1]]) pts.push([x, P.yOf(map(arr[ids[j - 1]]))]);
      pts.push([x, y]);
    });
    return pts;
  }
  function destaqueAuto(D, d0, d1, janela = 250) {
    const g = D.grade_d, n = g.length;
    const r = Math.max(1, Math.round(50 / D.passo_m)), rs = Math.max(1, Math.round(150 / D.passo_m));
    const sv = g.map((_, i2) => {
      const w = D.delta.slice(Math.max(0, i2 - rs), Math.min(n, i2 + rs + 1)).sort((a, b) => a - b);
      return w[w.length >> 1];
    });
    const passos = Math.round(janela / D.passo_m);
    let bi = -1, bj = -1, bg = 0;
    for (let i2 = 0; i2 < n; i2++) {
      if (g[i2] < d0 || g[i2] + janela > d1) continue;
      const j2 = Math.min(n - 1, i2 + passos);
      if (Math.abs(sv[j2] - sv[i2]) > Math.abs(bg)) {
        bi = i2;
        bj = j2;
        bg = sv[j2] - sv[i2];
      }
    }
    if (bi < 0) return { d0, d1: Math.min(d1, d0 + janela), ganho: 0 };
    const firme = (k) => {
      let b = k;
      for (let q = Math.max(0, k - r); q <= Math.min(n - 1, k + r); q++) if (Math.abs(D.delta[q] - sv[q]) < Math.abs(D.delta[b] - sv[b])) b = q;
      return b;
    };
    const i = firme(bi), j = firme(bj);
    return { d0: g[i], d1: g[j], ganho: D.delta[j] - D.delta[i] };
  }
  function textoGanho(c, ganho) {
    const P = ganho < 0 ? c.A : c.B;
    return { texto: `${P.sigla} ganha ${fmt(Math.abs(ganho), 3)} s aqui`, cor: c.T.destaque };
  }
  function minimapa(c, caixa, dest, emDest) {
    const tr = c.D.tracado;
    if (!tr) {
      c.avisos.push("minimapa pedido mas os dados não têm traçado");
      return;
    }
    const xs = tr.x, zs = tr.z;
    const [xmin, xmax, zmin, zmax] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
    const m = 12 * c.s, k = Math.min((caixa.w - 2 * m) / (xmax - xmin), (caixa.h - 2 * m) / (zmax - zmin));
    const ox = caixa.x + (caixa.w - (xmax - xmin) * k) / 2, oz = caixa.y + (caixa.h - (zmax - zmin) * k) / 2;
    const P = (i) => [ox + (xs[i] - xmin) * k, oz + (zs[i] - zmin) * k];
    const todos = xs.map((_, i) => P(i));
    c.linha("mapa-pista", "mapa", [...todos, todos[0]], c.T.eixo, 7 * c.s, c.spec.em + 0.2, 0.8, "comp");
    if (dest) {
      const sel = tr.d.map((d, i) => [d, i]).filter(([d]) => d >= dest.d0 && d <= dest.d1).map(([, i]) => P(i));
      if (sel.length > 1) c.linha("mapa-trecho", "destaque", sel, c.T.destaque, 11 * c.s, emDest, 0.35, "comp");
    }
  }
  function grafVelocidade(c, temDelta = false) {
    var _a, _b, _c, _d, _e, _f;
    const { spec, s, D, T } = c, area = spec.area, pad = 30 * s;
    const [d0, d1] = (_a = spec.trecho) != null ? _a : [0, D.comprimento_m];
    const ids = indices(D, d0, d1);
    const titulo = (_b = spec.titulo) != null ? _b : temDelta ? "Quem está à frente, metro a metro" : "Velocidade, metro a metro";
    const sub = (_c = spec.subtitulo) != null ? _c : temDelta ? `Diferença acumulada de tempo · ${c.A.sigla} volta ${c.A.volta} (${fmt(c.A.tempo, 3)}) × ${c.B.sigla} volta ${c.B.volta} (${fmt(c.B.tempo, 3)})` : `${c.A.sigla} volta ${c.A.volta} (${fmt(c.A.tempo, 3)}) × ${c.B.sigla} volta ${c.B.volta} (${fmt(c.B.tempo, 3)})`;
    const mapaW = spec.minimapa ? Math.min(300 * s, area.w * 0.2) : 0;
    const yTop = c.cabecalho(titulo, sub, !temDelta, 0);
    const yBot = c.rodape();
    const fil = 3, alt = 21 * s * 1.3;
    const fimW = Math.max(larguraTexto(c.A.sigla, 26 * s, 700), larguraTexto(c.B.sigla, 26 * s, 700)) + 16 * s;
    let plot;
    let Pl;
    const dest = spec.destaque === false ? null : spec.destaque === "auto" || spec.destaque === void 0 ? destaqueAuto(D, d0, d1) : { ...spec.destaque, ganho: interp(D.grade_d, D.delta, spec.destaque.d1) - interp(D.grade_d, D.delta, spec.destaque.d0) };
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
      let hi = Math.max(0.02, ...vs) * 1.08, lo = Math.min(-0.02, ...vs) * 1.08;
      hi = Math.max(hi, -lo * 0.22);
      lo = Math.min(lo, -hi * 0.22);
      const st = passoTick(lo, hi, 5);
      const v1 = Math.ceil(hi / st - 1e-9) * st, v0 = Math.floor(lo / st + 1e-9) * st;
      const ylw = Math.max(...ticks(v0, v1, 5).map((v) => larguraTexto(fmt(Math.abs(v), 2) + " s", 20 * s, 400)), larguraTexto("vantagem", 20 * s, 600));
      plot = { x: area.x + pad + ylw + 12 * s, y: yTop + fil * alt + 22 * s, w: 0, h: 0 };
      const rotW = Math.max(larguraTexto(`${c.A.sigla} à frente`, 24 * s, 700), larguraTexto(`${c.B.sigla} à frente`, 24 * s, 700));
      plot.w = area.x + area.w - pad - Math.max(fimW, rotW * 0) - (mapaW ? mapaW + pad : 0) - plot.x;
      plot.h = yBot - 70 * s - plot.y;
      Pl = plano(c, plot, d0, d1, v0, v1, "vantagem (s)", "vantagem", (v) => v === 0 ? "0" : fmt(Math.abs(v), 2) + " s", fil, st);
    }
    c.cursor = { ritmo: Pl.ritmo, x0: plot.x, x1: plot.x + plot.w, d0, d1 };
    c.plot = plot;
    const emDest = (_d = spec.destaqueEm) != null ? _d : Pl.tFim + 0.3;
    if (dest) {
      const xa = Pl.xOf(dest.d0), xb = Pl.xOf(dest.d1);
      c.els.unshift({
        id: `${spec.id}:destaque-faixa`,
        grafico: spec.id,
        papel: "destaque",
        tipo: "ret",
        x: xa,
        y: plot.y,
        w: xb - xa,
        h: plot.h,
        cor: T.destaque,
        opac: T.nome === "claro" ? 0.1 : 0.16,
        em: emDest,
        dur: 0.3,
        revela: "fade"
      });
      const g = textoGanho(c, dest.ganho);
      const tx = (_e = dest.texto) != null ? _e : g.texto;
      const tam = 24 * s, w = larguraTexto(tx, tam, 700);
      const xc = lim((xa + xb) / 2, plot.x + w / 2, plot.x + plot.w - w / 2);
      const livre = [0, 1, 2].map((r) => plot.y - 16 * s - r * alt);
      let ok = false;
      for (const y of livre) {
        const cx = caixaTexto(xc, y, tx, tam, 700, "middle");
        if (c.cabe(cx)) {
          c.t("destaque-rotulo", "destaque", xc, y, tx, tam, 700, g.cor, "middle", emDest + 0.15);
          ok = true;
          break;
        }
      }
      if (!ok) {
        const y = livre[0], cx = caixaTexto(xc, y, tx, tam, 700, "middle");
        const tirar = c.els.filter((e) => e.tipo === "texto" && e.papel === "rotulo" && cruza(e.caixa, cx, 6 * s));
        for (const e of tirar) {
          c.els.splice(c.els.indexOf(e), 1);
          c.textos.splice(c.textos.indexOf(e.caixa), 1);
          c.avisos.push(`rótulo "${e.texto}" cedeu lugar ao destaque`);
        }
        c.t("destaque-rotulo", "destaque", xc, y, tx, tam, 700, g.cor, "middle", emDest + 0.15);
      }
    }
    if (!temDelta) {
      const pa = serie(Pl, c.A, "vel", ids), pb = serie(Pl, c.B, "vel", ids);
      if (dest) {
        const sel = ids.filter((i) => D.grade_d[i] >= dest.d0 && D.grade_d[i] <= dest.d1);
        const sup = sel.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(Math.max(c.A.vel[i], c.B.vel[i]))]);
        const inf = sel.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(Math.min(c.A.vel[i], c.B.vel[i]))]);
        c.els.push({
          id: `${spec.id}:destaque-entre`,
          grafico: spec.id,
          papel: "destaque",
          tipo: "area",
          sup,
          inf,
          cor: dest.ganho < 0 ? c.corA : c.corB,
          opac: 0.3,
          em: emDest + 0.1,
          dur: 0.35,
          revela: "fade"
        });
      }
      c.linha("serie-b", "dado", pb, c.corB, 4.5 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: c.B.sigla, campo: "vel" } });
      c.linha("serie-a", "dado", pa, c.corA, 4.5 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: c.A.sigla, campo: "vel" } });
      const il = ids[ids.length - 1];
      c.rotulosFim(
        [{ id: "fim-a", y: Pl.yOf(c.A.vel[il]), texto: c.A.sigla, cor: c.corA }, { id: "fim-b", y: Pl.yOf(c.B.vel[il]), texto: c.B.sigla, cor: c.corB }],
        plot.x + plot.w + 12 * s,
        26 * s,
        Pl.tFim,
        plot.y,
        plot.y + plot.h
      );
    } else {
      const v = (i) => -D.delta[i];
      const lin = ids.map((i) => [Pl.xOf(D.grade_d[i]), Pl.yOf(v(i))]);
      const zero = Pl.yOf(0);
      c.els.push({
        id: `${spec.id}:area-a`,
        grafico: spec.id,
        papel: "dado",
        tipo: "area",
        sup: lin.map(([x, y]) => [x, Math.min(y, zero)]),
        inf: lin.map(([x]) => [x, zero]),
        cor: c.corA,
        opac: 0.28,
        em: Pl.tDados,
        dur: Pl.tFim - Pl.tDados,
        revela: "cursor"
      });
      c.els.push({
        id: `${spec.id}:area-b`,
        grafico: spec.id,
        papel: "dado",
        tipo: "area",
        sup: lin.map(([x]) => [x, zero]),
        inf: lin.map(([x, y]) => [x, Math.max(y, zero)]),
        cor: c.corB,
        opac: 0.28,
        em: Pl.tDados,
        dur: Pl.tFim - Pl.tDados,
        revela: "cursor"
      });
      c.linha("serie-delta", "dado", lin, T.tinta, 4 * s, Pl.tDados, Pl.tFim - Pl.tDados, "cursor", { serie: { piloto: `${c.A.sigla}-${c.B.sigla}`, campo: "vantagem" } });
      for (const [k, P, cor, sinal] of [["a", c.A, c.corA, 1], ["b", c.B, c.corB, -1]]) {
        const tx = `${P.sigla} à frente`;
        const y = sinal > 0 ? plot.y + 34 * s : plot.y + plot.h - 14 * s;
        const cands = [plot.x + 16 * s, plot.x + plot.w * 0.25, plot.x + plot.w * 0.5, plot.x + plot.w * 0.75];
        let ok = false;
        for (const x of cands) {
          const cx = caixaTexto(x, y, tx, 24 * s, 700, "start");
          const bate = lin.some(([px, py]) => px >= cx.x - 6 && px <= cx.x + cx.w + 6 && py >= cx.y - 6 && py <= cx.y + cx.h + 6);
          if (!bate && c.cabe(cx) && cx.x + cx.w <= plot.x + plot.w) {
            c.t(`regiao-${k}`, "legenda", x, y, tx, 24 * s, 700, cor, "start", c.spec.em + 0.3);
            ok = true;
            break;
          }
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
      c.t(
        "mapa-rotulo",
        "rotulo",
        mx + mapaW / 2,
        plot.y + Math.min(plot.h, mapaW * 1.1) + 26 * s,
        dest ? "trecho destacado" : (_f = c.D.circuito) != null ? _f : "",
        19 * s,
        600,
        dest ? T.destaque : T.tinta2,
        "middle",
        emDest + 0.15
      );
    }
  }
  function grafSetores(c) {
    var _a, _b;
    const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
    const yTop = c.cabecalho((_a = spec.titulo) != null ? _a : "Onde a volta foi ganha", (_b = spec.subtitulo) != null ? _b : "Diferença de tempo em cada setor (OpenF1, tempos oficiais de setor)", false);
    const yBot = c.rodape();
    const linhas = c.A.setores.map((a, k) => ({ rot: `Setor ${k + 1}`, a, b: c.B.setores[k] }));
    linhas.push({ rot: "Volta", a: c.A.tempo, b: c.B.tempo });
    const tamR = 30 * s, tamV = 28 * s, tamP = 20 * s;
    const rotW = Math.max(...linhas.map((l) => larguraTexto(l.rot, tamR, 700))) + 24 * s;
    const xc = area.x + pad + rotW + (area.w - 2 * pad - rotW) / 2;
    const meio = (area.w - 2 * pad - rotW) / 2;
    const valW = larguraTexto("0,000 s", tamV, 700) + 18 * s;
    const maxD = Math.max(...linhas.map((l) => Math.abs(l.a - l.b)), 0.05);
    const st = passoTick(0, maxD, 3);
    const top = Math.ceil(maxD * 1.02 / st) * st;
    const escala = (meio - valW) / top;
    const yH = yTop + 34 * s;
    c.t("lado-a", "legenda", xc - 18 * s, yH, `◀ ${c.A.sigla} mais rápido`, 26 * s, 700, c.corA, "end", em + 0.15);
    c.t("lado-b", "legenda", xc + 18 * s, yH, `${c.B.sigla} mais rápido ▶`, 26 * s, 700, c.corB, "start", em + 0.15);
    const y0 = yH + 34 * s, y1 = yBot - 56 * s;
    const passo = (y1 - y0) / linhas.length, barH = Math.min(58 * s, passo * 0.42);
    c.eixos.push({ d0: -top, d1: top, x0: xc - top * escala, x1: xc + top * escala, v0: 0, v1: 0, y0, y1, nome: "segundos (setores)" });
    for (let v = 0; v <= top + 1e-9; v += st) {
      for (const sg of v === 0 ? [1] : [-1, 1]) {
        const x = xc + sg * v * escala;
        c.linha(`grade-${sg}-${v.toFixed(3)}`, v === 0 ? "eixo" : "grade", [[x, y0], [x, y1]], v === 0 ? T.eixo : T.grade, (v === 0 ? 2.5 : 1.5) * s, em + 0.1, 0.4, "comp");
        c.t(`tick-${sg}-${v.toFixed(3)}`, "eixo", x, y1 + 28 * s, v === 0 ? "0" : `${fmt(v, 2)} s`, 20 * s, 400, T.tinta2, "middle", em + 0.25);
      }
    }
    linhas.forEach((l, k) => {
      const yc = y0 + passo * (k + 0.5), d = l.a - l.b;
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
    c.cursor = null;
    c.plot = { x: xc - meio, y: y0, w: 2 * meio, h: y1 - y0 };
  }
  function grafTelemetria(c) {
    var _a, _b, _c, _d, _e, _f, _g;
    const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
    const [d0, d1] = (_a = spec.trecho) != null ? _a : [0, D.comprimento_m];
    const ids = indices(D, d0, d1);
    const paineis = (_b = spec.paineis) != null ? _b : ["acelerador", "freio", "marcha"];
    const yTop = c.cabecalho((_c = spec.titulo) != null ? _c : "Acelerador, freio e marcha", (_d = spec.subtitulo) != null ? _d : `${fmt(d0)}–${fmt(d1)} m da volta`, true);
    const yBot = c.rodape();
    const tamP = 22 * s;
    const nomeW = Math.max(...["Acelerador", "Velocidade", "Freio", "Marcha"].map((n) => larguraTexto(n, tamP, 700))) + 12 * s;
    const tickW = larguraTexto("100 %", 20 * s, 400) + 10 * s;
    const fimW = Math.max(larguraTexto(c.A.sigla, 22 * s, 700), larguraTexto(c.B.sigla, 22 * s, 700)) + 16 * s;
    const x0 = area.x + pad + nomeW + tickW, x1 = area.x + area.w - pad - fimW;
    const fil = 2, alt = 21 * s * 1.3;
    const yA = yTop + fil * alt + 26 * s, yB = yBot - 70 * s;
    const pesos = { acelerador: 1, velocidade: 1, marcha: 0.8, freio: 0.42 };
    const gap = 34 * s, tot = paineis.reduce((a, p) => a + pesos[p], 0), hUtil = yB - yA - gap * (paineis.length - 1);
    let y = yA;
    let primeiro = null;
    const plot = { x: x0, y: yA, w: x1 - x0, h: yB - yA };
    const xOf = (d) => x0 + (d - d0) / (d1 - d0) * (x1 - x0);
    const tDados = (_g = (_f = (_e = spec.ritmo) == null ? void 0 : _e[0]) == null ? void 0 : _f.t) != null ? _g : em + 0.55;
    const ritmo = ritmoDe(spec, d0, d1, tDados), tFim = ritmo[ritmo.length - 1].t;
    paineis.forEach((p, k) => {
      const h = hUtil * pesos[p] / tot;
      const caixa = { x: x0, y, w: x1 - x0, h };
      const nomes = { acelerador: "Acelerador", velocidade: "Velocidade", marcha: "Marcha", freio: "Freio" };
      c.t(`painel-${p}`, "rotulo", area.x + pad, y + 22 * s, nomes[p], tamP, 700, T.tinta, "start", em + 0.2);
      if (p === "freio") {
        const fh = Math.min(16 * s, h / 3);
        [[c.A, c.corA, 0], [c.B, c.corB, 1]].forEach(([P, cor, j]) => {
          const Pi = P, yy = y + h * (j === 0 ? 0.3 : 0.72) - fh / 2;
          c.linha(`freio-base-${j}`, "grade", [[x0, yy + fh / 2], [x1, yy + fh / 2]], T.grade, 1.5 * s, em + 0.1, 0.4, "x");
          c.t(`freio-sigla-${j}`, "rotulo", x0 - 10 * s, yy + fh / 2 + 7 * s, Pi.sigla, 19 * s, 700, cor, "end", em + 0.2);
          let ini = -1;
          ids.forEach((i, q) => {
            const on = Pi.freio[i] > 0;
            if (on && ini < 0) ini = i;
            if (ini >= 0 && (!on || q === ids.length - 1)) {
              const fim = on ? i : ids[q - 1];
              const xa = xOf(D.grade_d[ini]), xb = Math.max(xOf(D.grade_d[fim]), xa + 2 * s);
              c.ret(
                `freio-${j}-${ini}`,
                "dado",
                xa,
                yy,
                xb - xa,
                fh,
                cor,
                1,
                tDados,
                tFim - tDados,
                "cursor",
                { valor: D.grade_d[fim] - D.grade_d[ini], raio: 3 * s }
              );
              ini = -1;
            }
          });
        });
        c.eixos.push({ d0, d1, x0, x1, v0: 0, v1: 1, y0: y + h, y1: y, nome: "freio" });
      } else {
        const cfg = p === "acelerador" ? { v0: 0, v1: 100, ticks: [0, 50, 100], f: (v) => `${v} %`, campo: "acel", degrau: false } : p === "marcha" ? (() => {
          const mx = Math.max(...ids.flatMap((i) => [c.A.marcha[i], c.B.marcha[i]]), 2), mn = Math.min(...ids.flatMap((i) => [c.A.marcha[i], c.B.marcha[i]]));
          const tk = [];
          for (let g = Math.max(1, mn); g <= mx; g++) if (mx - mn <= 4 || g % 2 === 0) tk.push(g);
          return { v0: Math.max(0, mn - 0.6), v1: mx + 0.6, ticks: tk, f: (v) => `${v}ª`, campo: "marcha", degrau: true };
        })() : (() => {
          const vs = ids.flatMap((i) => [c.A.vel[i], c.B.vel[i]]);
          const st = passoTick(Math.min(...vs), Math.max(...vs), 3);
          const a = Math.floor(Math.min(...vs) / st) * st, b = Math.ceil(Math.max(...vs) / st) * st;
          return { v0: a, v1: b, ticks: ticks(a, b, 3), f: (v) => fmt(v), campo: "vel", degrau: false };
        })();
        const yOf = (v) => y + h - (v - cfg.v0) / (cfg.v1 - cfg.v0) * h;
        for (const v of cfg.ticks) {
          c.linha(`grade-${p}-${v}`, "grade", [[x0, yOf(v)], [x1, yOf(v)]], T.grade, 1.5 * s, em + 0.1, 0.4, "x");
          c.t(`tick-${p}-${v}`, "eixo", x0 - 10 * s, yOf(v) + 7 * s, cfg.f(v), 19 * s, 400, T.tinta2, "end", em + 0.25);
        }
        const P = { c, plot: caixa, d0, d1, v0: cfg.v0, v1: cfg.v1, xOf, yOf, tDados, tFim, ritmo, tEm: (d) => tempoEm(ritmo, d) };
        c.eixos.push({ d0, d1, x0, x1, v0: cfg.v0, v1: cfg.v1, y0: yOf(cfg.v0), y1: yOf(cfg.v1), nome: p });
        const pb = serie(P, c.B, cfg.campo, ids, cfg.degrau), pa = serie(P, c.A, cfg.campo, ids, cfg.degrau);
        c.linha(`serie-${p}-b`, "dado", pb, c.corB, 3.5 * s, tDados, tFim - tDados, "cursor", { serie: { piloto: c.B.sigla, campo: cfg.campo, degrau: cfg.degrau } });
        c.linha(`serie-${p}-a`, "dado", pa, c.corA, 3.5 * s, tDados, tFim - tDados, "cursor", { serie: { piloto: c.A.sigla, campo: cfg.campo, degrau: cfg.degrau } });
        const il = ids[ids.length - 1];
        c.rotulosFim(
          [{ id: `fim-${p}-a`, y: yOf(c.A[cfg.campo][il]), texto: c.A.sigla, cor: c.corA }, { id: `fim-${p}-b`, y: yOf(c.B[cfg.campo][il]), texto: c.B.sigla, cor: c.corB }],
          x1 + 10 * s,
          22 * s,
          tFim,
          y,
          y + h
        );
        if (!primeiro) primeiro = P;
      }
      y += h + gap;
    });
    c.linha("base-x", "eixo", [[x0, yB], [x1, yB]], T.eixo, 2 * s, em + 0.1, 0.45, "x");
    const px = passoTick(d0, d1, Math.max(3, Math.round((x1 - x0) / 260)));
    for (let d = Math.ceil(d0 / px) * px; d <= d1 + 1e-6; d += px) c.t(`tick-x-${d}`, "eixo", xOf(d), yB + 28 * s, fmt(d), 20 * s, 400, T.tinta2, "middle", em + 0.25);
    c.t("unidade-x", "eixo", x1, yB + 58 * s, "distância na volta (m)", 20 * s, 600, T.tinta2, "end", em + 0.25);
    const rot = [];
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
  function metrica(D, P, m, d0, d1) {
    var _a;
    const g = D.grade_d;
    if (m === "vmedia") {
      const ta = interp(g, P.t, d0), tb = interp(g, P.t, d1);
      return (d1 - d0) / (tb - ta) * 3.6;
    }
    const b = (_a = P.bruto) != null ? _a : { t: P.t, d: g, vel: P.vel, acel: P.acel, freio: P.freio, marcha: P.marcha };
    const ids = b.d.map((d, i) => [d, i]).filter(([d]) => d >= d0 && d <= d1).map(([, i]) => i);
    if (m === "vmax") return Math.max(...ids.map((i) => b.vel[i]));
    if (m === "vmin") return Math.min(...ids.map((i) => b.vel[i]));
    let tot = 0, dist = 0;
    for (let q = 1; q < ids.length; q++) {
      const i = ids[q], h = ids[q - 1];
      if (m === "acelPleno") {
        dist += b.d[i] - b.d[h];
        if (b.acel[h] >= 98 && b.acel[i] >= 98) tot += b.d[i] - b.d[h];
      } else if (b.freio[h] > 0) tot += b.t[i] - b.t[h];
    }
    return m === "acelPleno" ? 100 * tot / dist : tot;
  }
  var METRICAS = {
    vmax: { nome: "Velocidade máxima", unid: "km/h", casas: 0, maiorMelhor: true },
    vmin: { nome: "Velocidade na curva mais lenta", unid: "km/h", casas: 0, maiorMelhor: true },
    vmedia: { nome: "Velocidade média", unid: "km/h", casas: 2, maiorMelhor: true },
    acelPleno: { nome: "Acelerador a fundo", unid: "% do trecho", casas: 1, maiorMelhor: true },
    freando: { nome: "Tempo pisando no freio", unid: "s", casas: 2, maiorMelhor: false }
  };
  function vantagem(va, vb, maiorMelhor) {
    const aMelhor = maiorMelhor ? va > vb : va < vb;
    const [m, p] = aMelhor ? [va, vb] : [vb, va];
    const pct = p === 0 ? 0 : (maiorMelhor ? (m - p) / p : (p - m) / p) * 100;
    return { pct: Math.abs(pct), aMelhor };
  }
  function grafNormalizado(c) {
    var _a, _b, _c, _d;
    const { spec, s, D, T } = c, area = spec.area, pad = 30 * s, em = spec.em;
    const [d0, d1] = (_a = spec.trecho) != null ? _a : [0, D.comprimento_m];
    const ms = (_b = spec.metricas) != null ? _b : ["vmax", "vmin", "vmedia", "acelPleno", "freando"];
    const yTop = c.cabecalho(
      (_c = spec.titulo) != null ? _c : "Quem foi melhor em cada quesito",
      (_d = spec.subtitulo) != null ? _d : "Medidas diferentes na mesma régua: quanto um piloto foi melhor que o outro, em % do valor do outro",
      false
    );
    const yBot = c.rodape();
    const tamN = 27 * s, tamU = 20 * s, tamV = 26 * s;
    const linhas = ms.map((m) => {
      const M = METRICAS[m], va = metrica(D, c.A, m, d0, d1), vb = metrica(D, c.B, m, d0, d1);
      const u = M.unid === "% do trecho" ? "%" : ` ${M.unid}`;
      return {
        m,
        M,
        va,
        vb,
        ...vantagem(va, vb, M.maiorMelhor),
        real: `${c.A.sigla} ${fmt(va, M.casas)}${u} · ${c.B.sigla} ${fmt(vb, M.casas)}${u}`,
        dica: M.maiorMelhor ? "maior é melhor" : "menor é melhor"
      };
    });
    const nomeW = Math.max(...linhas.map((l) => Math.max(larguraTexto(l.M.nome, tamN, 700), larguraTexto(l.real, tamU, 400), larguraTexto(l.dica, tamU, 400)))) + 34 * s;
    const xc = area.x + pad + nomeW + (area.w - 2 * pad - nomeW) / 2, meio = (area.w - 2 * pad - nomeW) / 2;
    const valW = larguraTexto("+00,0 %", tamV, 700) + 18 * s;
    const maxP = Math.max(...linhas.map((l) => l.pct), 0.5);
    const st = passoTick(0, maxP, 3), top = Math.ceil(maxP * 1.02 / st) * st, escala = (meio - valW) / top;
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
    c.cursor = null;
    c.plot = { x: xc - meio, y: y0, w: 2 * meio, h: y1 - y0 };
  }
  function montar(specs, dados, larguras) {
    LARG = larguras;
    const graficos = [];
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
  function caminho(pts, fechar = false) {
    if (!pts.length) return "";
    let d = `M${pts[0][0].toFixed(2)} ${pts[0][1].toFixed(2)}`;
    for (let i = 1; i < pts.length; i++) d += `L${pts[i][0].toFixed(2)} ${pts[i][1].toFixed(2)}`;
    return fechar ? d + "Z" : d;
  }
  function cortaX(pts, xc) {
    if (!pts.length || xc < pts[0][0]) return [];
    const out = [];
    for (let i = 0; i < pts.length; i++) {
      if (pts[i][0] <= xc) {
        out.push(pts[i]);
        continue;
      }
      const a = pts[i - 1], b = pts[i];
      if (a && b[0] > a[0]) out.push([xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0])]);
      break;
    }
    return out;
  }
  function cortaComp(pts, k) {
    if (k <= 0 || pts.length < 2) return [];
    if (k >= 1) return pts;
    const L = [0];
    for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const alvo = k * L[L.length - 1], out = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      if (L[i] <= alvo) {
        out.push(pts[i]);
        continue;
      }
      const u = (alvo - L[i - 1]) / (L[i] - L[i - 1]);
      out.push([pts[i - 1][0] + u * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + u * (pts[i][1] - pts[i - 1][1])]);
      break;
    }
    return out;
  }
  function retPath(x, y, w, h, r = 0) {
    if (w <= 0.01 || h <= 0.01) return "";
    r = Math.min(r, w / 2, h / 2);
    if (r <= 0) return `M${x} ${y}h${w}v${h}h${-w}Z`;
    return `M${x + r} ${y}h${w - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}v${h - 2 * r}a${r} ${r} 0 0 1 ${-r} ${r}h${-(w - 2 * r)}a${r} ${r} 0 0 1 ${-r} ${-r}v${-(h - 2 * r)}a${r} ${r} 0 0 1 ${r} ${-r}Z`;
  }
  function estado(m, t) {
    var _a;
    const out = [];
    for (const g of m.graficos) {
      if (g.spec.ate !== void 0 && t >= g.spec.ate) continue;
      const xc = g.cursor ? g.cursor.x0 + (distCursor(g.cursor.ritmo, t) - g.cursor.d0) / (g.cursor.d1 - g.cursor.d0) * (g.cursor.x1 - g.cursor.x0) : Infinity;
      const cursorOn = g.cursor ? t >= g.cursor.ritmo[0].t : true;
      for (const e of g.elementos) {
        if (t < e.em) continue;
        const k = e.dur > 0 ? lim((t - e.em) / e.dur, 0, 1) : 1;
        if (e.tipo === "texto") {
          out.push({ id: e.id, tipo: "texto", x: e.x, y: e.y, texto: e.texto, tam: e.tam, peso: e.peso, cor: e.cor, ancora: e.ancora, opac: k });
        } else if (e.tipo === "linha") {
          let pts;
          if (e.revela === "cursor") pts = cursorOn ? cortaX(e.pts, xc) : [];
          else if (e.revela === "x") {
            const xa = e.pts[0][0], xb = e.pts[e.pts.length - 1][0];
            pts = xb > xa ? cortaX(e.pts, xa + suave(k) * (xb - xa)) : cortaComp(e.pts, suave(k));
          } else pts = cortaComp(e.pts, suave(k));
          if (pts.length >= 2) out.push({ id: e.id, tipo: "path", d: caminho(pts), stroke: e.cor, largura: e.largura, opac: 1, tracejado: e.tracejado });
        } else if (e.tipo === "area") {
          let sup = e.sup, inf = e.inf, op = e.opac;
          if (e.revela === "cursor") {
            sup = cortaX(sup, xc);
            inf = cortaX(inf, xc);
          } else op *= k;
          if (sup.length >= 2) out.push({ id: e.id, tipo: "path", d: caminho([...sup, ...inf.slice().reverse()], true), fill: e.cor, opac: op });
        } else {
          let { x, y, w, h } = e, op = e.opac;
          const kk = suave(k);
          if (e.revela === "dir") w *= kk;
          else if (e.revela === "esq") {
            x += w * (1 - kk);
            w *= kk;
          } else if (e.revela === "cima") {
            y += h * (1 - kk);
            h *= kk;
          } else if (e.revela === "cursor") w = lim(xc - x, 0, w);
          else op *= k;
          const d = retPath(x, y, w, h, (_a = e.raio) != null ? _a : 0);
          if (d) out.push({ id: e.id, tipo: "path", d, fill: e.cor, opac: op });
        }
      }
    }
    return out;
  }
  function checar(m) {
    const falhas = [], rel = {};
    for (const g of m.graficos) {
      const a = g.spec.area, id = g.spec.id;
      const dentro = (x, y, tol = 0.5) => x >= a.x - tol && x <= a.x + a.w + tol && y >= a.y - tol && y <= a.y + a.h + tol;
      let fora = 0;
      const textos = g.elementos.filter((e) => e.tipo === "texto");
      for (const e of g.elementos) {
        const meia = e.tipo === "linha" ? e.largura / 2 : 0;
        const pts = e.tipo === "linha" ? e.pts : e.tipo === "area" ? [...e.sup, ...e.inf] : e.tipo === "ret" ? [[e.x, e.y], [e.x + e.w, e.y + e.h]] : [[e.caixa.x, e.caixa.y], [e.caixa.x + e.caixa.w, e.caixa.y + e.caixa.h]];
        const ruins = pts.filter(([x, y]) => !(dentro(x - meia, y - meia) && dentro(x + meia, y + meia)));
        if (ruins.length) {
          fora++;
          falhas.push(`${e.id}: ${ruins.length} ponto(s) fora da área`);
        }
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
  return __toCommonJS(graficos_exports);
})();
