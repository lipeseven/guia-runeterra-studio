// GERADO por esbuild de F1/horizontal/kit/transicoes/transicoes.ts (F1/horizontal/testes/motores.py). Não editar à mão.
var Transicoes = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
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

  // transicoes.ts
  var transicoes_exports = {};
  __export(transicoes_exports, {
    ALTURA: () => ALTURA,
    LARGURA: () => LARGURA,
    QUADROS: () => QUADROS,
    SFX_PADRAO: () => SFX_PADRAO,
    checarTransicoes: () => checarTransicoes,
    curva: () => curva,
    estadoSequencia: () => estadoSequencia,
    estadoTransicao: () => estadoTransicao,
    estiloCamada: () => estiloCamada,
    montarTransicao: () => montarTransicao,
    montarTransicoes: () => montarTransicoes,
    pedidosSfx: () => pedidosSfx,
    progresso: () => progresso
  });
  var QUADROS = { corte: 0, fade: 18, wipe: 24, zoom: 30 };
  var SFX_PADRAO = { corte: null, fade: null, wipe: "whoosh", zoom: "whoosh" };
  var LARGURA = 1920;
  var ALTURA = 1080;
  var lim = (x) => Math.max(0, Math.min(1, x));
  var smooth = (x) => {
    x = lim(x);
    return x * x * (3 - 2 * x);
  };
  var curva = (p) => 0.7 * smooth(p) + 0.3 * lim(p);
  function montarTransicao(t, fps = 60) {
    var _a, _b, _c, _d, _e;
    const n = t.tipo === "corte" ? 0 : Math.max(2, Math.round((_a = t.quadros) != null ? _a : QUADROS[t.tipo] * fps / 60));
    const qCorte = Math.round(t.em * fps);
    const q0 = qCorte - Math.floor(n / 2);
    const sfx = t.sfx === false ? null : (_b = t.sfx) != null ? _b : SFX_PADRAO[t.tipo];
    const tm = {
      t: { tipo: t.tipo, em: qCorte / fps, quadros: n, direcao: (_c = t.direcao) != null ? _c : "direita", cor: (_d = t.cor) != null ? _d : "#e10600", intensidade: (_e = t.intensidade) != null ? _e : 0.7, sfx, variacao: t.variacao },
      fps,
      n,
      qCorte,
      q0,
      qPico: qCorte,
      tPico: qCorte / fps
    };
    if (n > 0) {
      let melhor = -1;
      for (let q = q0; q < q0 + n; q++) {
        const d = progresso(tm, q) - progresso(tm, q - 1);
        if (d > melhor + 1e-12 || Math.abs(d - melhor) <= 1e-12 && Math.abs(q - qCorte) < Math.abs(tm.qPico - qCorte)) {
          melhor = d;
          tm.qPico = q;
        }
      }
      tm.tPico = tm.qPico / fps;
    }
    return tm;
  }
  var montarTransicoes = (ts, fps = 60) => ts.map((t) => montarTransicao(t, fps));
  function progresso(tm, q) {
    if (tm.n === 0) return q >= tm.qCorte ? 1 : 0;
    if (q < tm.q0) return 0;
    if (q >= tm.q0 + tm.n) return 1;
    return curva((q - tm.q0 + 1) / (tm.n + 1));
  }
  var PURA = { opacidade: 1, escala: 1, tx: 0, ty: 0, blur: 0, recorte: null };
  function estadoTransicao(tm, q, W = LARGURA, H = ALTURA) {
    const e = progresso(tm, q);
    if (e <= 0) return { a: { ...PURA }, b: null, barra: null };
    if (e >= 1) return { a: null, b: { ...PURA }, barra: null };
    switch (tm.t.tipo) {
      case "fade":
        return { a: { ...PURA }, b: { ...PURA, opacidade: e }, barra: null };
      case "wipe": {
        const r = (1 - e) * 100;
        const rec = {
          direita: [0, r, 0, 0],
          esquerda: [0, 0, 0, r],
          baixo: [0, 0, r, 0],
          cima: [r, 0, 0, 0]
        };
        const bw = 14;
        const d = tm.t.direcao;
        const barra = d === "direita" ? { x: e * W - bw / 2, y: 0, w: bw, h: H } : d === "esquerda" ? { x: (1 - e) * W - bw / 2, y: 0, w: bw, h: H } : d === "baixo" ? { x: 0, y: e * H - bw / 2, w: W, h: bw } : { x: 0, y: (1 - e) * H - bw / 2, w: W, h: bw };
        return { a: { ...PURA }, b: { ...PURA, recorte: rec[d] }, barra: { ...barra, cor: tm.t.cor } };
      }
      case "zoom": {
        const a = lim(e / 0.58);
        const b = lim((e - 0.42) / 0.58);
        const opB = smooth((e - 0.42) / 0.16);
        return {
          a: opB >= 1 ? null : { ...PURA, escala: 1 + 1.4 * a, blur: 14 * a * a },
          b: opB <= 0 ? null : { ...PURA, opacidade: opB, escala: 1 + 0.6 * (1 - b), blur: 14 * (1 - b) * (1 - b) },
          barra: null
        };
      }
      default:
        return { a: null, b: { ...PURA }, barra: null };
    }
  }
  function estiloCamada(c) {
    const s = { position: "absolute", left: "0", top: "0", width: "100%", height: "100%", opacity: c.opacidade.toFixed(4) };
    if (c.escala !== 1 || c.tx || c.ty) {
      s.transform = `translate(${c.tx.toFixed(2)}px, ${c.ty.toFixed(2)}px) scale(${c.escala.toFixed(5)})`;
      s.transformOrigin = "50% 50%";
    }
    if (c.blur > 0.01) s.filter = `blur(${c.blur.toFixed(3)}px)`;
    if (c.recorte) s.clipPath = `inset(${c.recorte.map((v) => v.toFixed(4) + "%").join(" ")})`;
    return s;
  }
  function estadoSequencia(ts, q) {
    for (let i = 0; i < ts.length; i++) {
      const tm = ts[i];
      if (tm.n > 0 && q >= tm.q0 && q < tm.q0 + tm.n) {
        const e = estadoTransicao(tm, q);
        const itens = [];
        if (e.a) itens.push({ cena: i, estilo: estiloCamada(e.a) });
        if (e.b) itens.push({ cena: i + 1, estilo: estiloCamada(e.b) });
        return { itens, barra: e.barra };
      }
    }
    const cena = ts.filter((tm) => q >= tm.q0 + tm.n && (tm.n > 0 || q >= tm.qCorte)).length;
    return { itens: [{ cena, estilo: estiloCamada(PURA) }], barra: null };
  }
  function pedidosSfx(ts) {
    return ts.filter((tm) => tm.t.sfx).map((tm) => ({
      categoria: tm.t.sfx,
      t: tm.tPico,
      intensidade: tm.t.intensidade,
      ...tm.t.variacao ? { variacao: tm.t.variacao } : {}
    }));
  }
  var igualPura = (c) => !!c && c.opacidade === 1 && c.escala === 1 && c.tx === 0 && c.ty === 0 && c.blur === 0 && c.recorte === null;
  function checarTransicoes(ts) {
    const rel = { falhas: [], transicoes: [] };
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
  return __toCommonJS(transicoes_exports);
})();
