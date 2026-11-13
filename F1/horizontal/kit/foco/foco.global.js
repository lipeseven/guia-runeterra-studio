// GERADO por esbuild de F1/horizontal/kit/foco/foco.ts (F1/horizontal/testes/motores.py). Não editar à mão.
var Foco = (() => {
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

  // foco.ts
  var foco_exports = {};
  __export(foco_exports, {
    ANEIS: () => ANEIS,
    alfaEm: () => alfaEm,
    ancoraEm: () => ancoraEm,
    caixaEm: () => caixaEm,
    caixaEnvelope: () => caixaEnvelope,
    checarFoco: () => checarFoco,
    distJanela: () => distJanela,
    estadoFoco: () => estadoFoco,
    estilos: () => estilos,
    forca: () => forca,
    janelaEm: () => janelaEm,
    mascaraSvg: () => mascaraSvg,
    montarFoco: () => montarFoco,
    nivelAnel: () => nivelAnel
  });

  // ../anotacao/anotacao.ts
  function caixaEnvelope(amostras) {
    let hw = 0, hh = 0;
    for (const a of amostras) for (const [x, y] of a.pontos) {
      hw = Math.max(hw, Math.abs(x - a.centro[0]));
      hh = Math.max(hh, Math.abs(y - a.centro[1]));
    }
    const [cx, cy] = amostras[0].centro;
    return { x: cx - hw, y: cy - hh, w: 2 * hw, h: 2 * hh };
  }
  function ancoraEm(alvo, t) {
    var _a, _b, _c, _d, _e, _f;
    const m = alvo == null ? void 0 : alvo.movimento;
    if (!m || m.length === 0) return { dx: 0, dy: 0, s: 1 };
    if (t <= m[0].t) return { dx: m[0].dx, dy: m[0].dy, s: (_a = m[0].s) != null ? _a : 1 };
    const n = m.length - 1;
    if (t >= m[n].t) return { dx: m[n].dx, dy: m[n].dy, s: (_b = m[n].s) != null ? _b : 1 };
    let i = 0;
    while (t > m[i + 1].t) i++;
    const k0 = m[Math.max(0, i - 1)], k1 = m[i], k2 = m[i + 1], k3 = m[Math.min(n, i + 2)];
    const u = (t - k1.t) / (k2.t - k1.t), u2 = u * u, u3 = u2 * u;
    const cr = (a, b, c, d) => 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3);
    return { dx: cr(k0.dx, k1.dx, k2.dx, k3.dx), dy: cr(k0.dy, k1.dy, k2.dy, k3.dy), s: cr((_c = k0.s) != null ? _c : 1, (_d = k1.s) != null ? _d : 1, (_e = k2.s) != null ? _e : 1, (_f = k3.s) != null ? _f : 1) };
  }

  // foco.ts
  var ANEIS = 14;
  var PADRAO = { entrada: 0.45, saida: 0.35, blur: 10, escurecer: 0.1, folga: 18, raio: 22, pena: 28, forma: "caixa", cor: "#000" };
  function montarFoco(cena) {
    const focos = cena.focos.map((f) => {
      const r = { ...PADRAO, ...f };
      if (r.ate - r.em < r.entrada + r.saida) {
        const esc = (r.ate - r.em) / (r.entrada + r.saida);
        r.entrada *= esc;
        r.saida *= esc;
      }
      return r;
    });
    return { cena, focos };
  }
  var suave = (x) => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
  var muitoSuave = (x) => x <= 0 ? 0 : x >= 1 ? 1 : x * x * x * (x * (x * 6 - 15) + 10);
  function forca(f, t) {
    if (t <= f.em || t >= f.ate) return 0;
    return Math.min(muitoSuave((t - f.em) / f.entrada), muitoSuave((f.ate - t) / f.saida));
  }
  function caixaEm(alvo, t) {
    const a = ancoraEm(alvo, t);
    const c = alvo.caixa;
    const cx = c.x + c.w / 2 + a.dx, cy = c.y + c.h / 2 + a.dy;
    return { x: cx - c.w / 2 * a.s, y: cy - c.h / 2 * a.s, w: c.w * a.s, h: c.h * a.s };
  }
  function janelaEm(f, t) {
    const c = caixaEm(f.alvo, t);
    return { x: c.x - f.folga, y: c.y - f.folga, w: c.w + 2 * f.folga, h: c.h + 2 * f.folga };
  }
  var n2 = (x) => Math.round(x * 100) / 100;
  function ret(c, r) {
    r = Math.min(r, c.w / 2, c.h / 2);
    const { x, y, w, h } = c;
    return `M${n2(x + r)} ${n2(y)}H${n2(x + w - r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + w)} ${n2(y + r)}V${n2(y + h - r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + w - r)} ${n2(y + h)}H${n2(x + r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x)} ${n2(y + h - r)}V${n2(y + r)}A${n2(r)} ${n2(r)} 0 0 1 ${n2(x + r)} ${n2(y)}Z`;
  }
  function elipse(cx, cy, rx, ry) {
    return `M${n2(cx - rx)} ${n2(cy)}A${n2(rx)} ${n2(ry)} 0 1 1 ${n2(cx + rx)} ${n2(cy)}A${n2(rx)} ${n2(ry)} 0 1 1 ${n2(cx - rx)} ${n2(cy)}Z`;
  }
  function contorno(f, j, off) {
    if (f.forma === "elipse") {
      const k = Math.SQRT2;
      return elipse(j.x + j.w / 2, j.y + j.h / 2, j.w / 2 * k + off, j.h / 2 * k + off);
    }
    return ret({ x: j.x - off, y: j.y - off, w: j.w + 2 * off, h: j.h + 2 * off }, f.raio + off);
  }
  var nivelAnel = (i) => suave(i / ANEIS);
  function mascaraSvg(f, j, largura, altura) {
    const partes = [];
    const offs = Array.from({ length: ANEIS + 1 }, (_, i) => i * f.pena / ANEIS);
    partes.push(`<path fill-rule="evenodd" d="M-2 -2H${largura + 2}V${altura + 2}H-2Z${contorno(f, j, offs[ANEIS])}"/>`);
    for (let i = 1; i <= ANEIS; i++) {
      partes.push(`<path fill-rule="evenodd" fill-opacity="${nivelAnel(i).toFixed(4)}" d="${contorno(f, j, offs[i])}${contorno(f, j, offs[i - 1])}"/>`);
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${largura}" height="${altura}" viewBox="0 0 ${largura} ${altura}"><g fill="#fff">${partes.join("")}</g></svg>`;
  }
  function distJanela(f, j, p) {
    if (f.forma === "elipse") {
      const cx = j.x + j.w / 2, cy = j.y + j.h / 2, rx = j.w / 2 * Math.SQRT2, ry = j.h / 2 * Math.SQRT2;
      const dentro = (off) => ((p[0] - cx) / (rx + off)) ** 2 + ((p[1] - cy) / (ry + off)) ** 2 <= 1;
      if (dentro(0)) return -1;
      let lo = 0, hi = 4e3;
      for (let k = 0; k < 40; k++) {
        const m = (lo + hi) / 2;
        if (dentro(m)) hi = m;
        else lo = m;
      }
      return hi;
    }
    const r = Math.min(f.raio, j.w / 2, j.h / 2);
    const ix0 = j.x + r, ix1 = j.x + j.w - r, iy0 = j.y + r, iy1 = j.y + j.h - r;
    const dx = Math.max(ix0 - p[0], 0, p[0] - ix1), dy = Math.max(iy0 - p[1], 0, p[1] - iy1);
    const d = Math.hypot(dx, dy) - r;
    return d;
  }
  function alfaEm(f, j, p) {
    const d = distJanela(f, j, p);
    if (d <= 0) return 0;
    if (d > f.pena) return 1;
    return nivelAnel(Math.ceil(d / f.pena * ANEIS - 1e-9));
  }
  function estadoFoco(m, t) {
    const out = [];
    for (const f of m.focos) {
      const k = forca(f, t);
      if (k <= 0) continue;
      const caixa = caixaEm(f.alvo, t), janela = janelaEm(f, t);
      const mascara = mascaraSvg(f, janela, m.cena.largura, m.cena.altura);
      out.push({
        id: f.id,
        k,
        blur: f.blur * k,
        veu: f.escurecer * k,
        cor: f.cor,
        caixa,
        janela,
        mascara,
        mascaraUrl: `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(mascara)}")`
      });
    }
    return out;
  }
  function estilos(e) {
    const base = {
      position: "absolute",
      left: "0",
      top: "0",
      width: "100%",
      height: "100%",
      pointerEvents: "none",
      maskImage: e.mascaraUrl,
      WebkitMaskImage: e.mascaraUrl,
      maskSize: "100% 100%",
      WebkitMaskSize: "100% 100%",
      maskRepeat: "no-repeat",
      WebkitMaskRepeat: "no-repeat",
      maskMode: "alpha"
    };
    return {
      camada: { ...base, backdropFilter: `blur(${e.blur.toFixed(3)}px)`, WebkitBackdropFilter: `blur(${e.blur.toFixed(3)}px)` },
      veu: { ...base, background: e.cor, opacity: e.veu.toFixed(4) }
    };
  }
  function checarFoco(m) {
    const { fps, duracao } = m.cena;
    const nq = Math.round(duracao * fps) + 1;
    const rel = { quadros: nq, falhas: [], focos: {} };
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
        r.erroJanelaPx = Math.max(
          r.erroJanelaPx,
          Math.abs(j.x - (c.x - f.folga)),
          Math.abs(j.y - (c.y - f.folga)),
          Math.abs(j.x + j.w - (c.x + c.w + f.folga)),
          Math.abs(j.y + j.h - (c.y + c.h + f.folga))
        );
        if (q % 6 !== 0) continue;
        for (let a = 0; a <= 12; a++) for (let b = 0; b <= 12; b++) {
          const p = [c.x + c.w * a / 12, c.y + c.h * b / 12];
          r.pontosDentro++;
          if (alfaEm(f, j, p) !== 0) rel.falhas.push(`${f.id}: desfoque dentro da caixa em ${p.map(n2)} (q${q})`);
        }
        const cx = j.x + j.w / 2, cy = j.y + j.h / 2;
        for (let ang = 0; ang < 360; ang += 15) {
          const ux = Math.cos(ang * Math.PI / 180), uy = Math.sin(ang * Math.PI / 180);
          let ant = 0;
          for (let s = 0; s < 1400; s += 2) {
            const p = [cx + ux * s, cy + uy * s];
            const al = alfaEm(f, j, p);
            if (al < ant - 1e-12) {
              rel.falhas.push(`${f.id}: alfa diminui saindo da janela (q${q}, ${ang}°)`);
              break;
            }
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
  return __toCommonJS(foco_exports);
})();
