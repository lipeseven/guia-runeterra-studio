// GERADO por esbuild de F1/horizontal/kit/cartoes/cartoes.ts (F1/horizontal/testes/motores.py). Não editar à mão.
var Cartoes = (() => {
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

  // cartoes.ts
  var cartoes_exports = {};
  __export(cartoes_exports, {
    COR: () => COR,
    MARGEM: () => MARGEM,
    TINTA: () => TINTA,
    ancoraTag: () => ancoraTag,
    checarCartoes: () => checarCartoes,
    estadoCartoes: () => estadoCartoes,
    geometriaTag: () => geometriaTag,
    larguraTexto: () => larguraTexto,
    montarCartoes: () => montarCartoes,
    svgCartoes: () => svgCartoes,
    texto: () => texto
  });

  // larguras.ts
  var LARGURAS = { "forte": { "wght": 700, "wdth": 87.5, "asc": 794, "desc": 207, "tinta_cima": 961, "tinta_baixo": 207, "av": { " ": 233, "!": 233, '"': 326, "#": 543, "$": 501, "%": 636, "&": 573, "'": 158, "(": 281, ")": 281, "*": 348, "+": 424, ",": 197, "-": 416, ".": 197, "/": 321, "0": 480, "1": 299, "2": 456, "3": 460, "4": 498, "5": 473, "6": 447, "7": 440, "8": 484, "9": 447, ":": 197, ";": 197, "<": 343, "=": 365, ">": 345, "?": 388, "@": 790, "A": 541, "B": 528, "C": 514, "D": 540, "E": 483, "F": 460, "G": 540, "H": 547, "I": 230, "J": 427, "K": 530, "L": 467, "M": 663, "N": 568, "O": 544, "P": 526, "Q": 553, "R": 548, "S": 520, "T": 410, "U": 528, "V": 485, "W": 699, "X": 476, "Y": 424, "Z": 450, "[": 248, "\\": 321, "]": 248, "^": 429, "_": 377, "`": 241, "a": 467, "b": 470, "c": 435, "d": 468, "e": 461, "f": 284, "g": 468, "h": 485, "i": 224, "j": 237, "k": 463, "l": 259, "m": 737, "n": 485, "o": 459, "p": 470, "q": 468, "r": 367, "s": 420, "t": 293, "u": 479, "v": 441, "w": 667, "x": 452, "y": 427, "z": 421, "{": 305, "|": 231, "}": 305, "~": 414, "À": 541, "Á": 541, "Â": 541, "Ã": 541, "Ä": 541, "Ç": 514, "È": 483, "É": 483, "Ê": 483, "Ë": 483, "Í": 230, "Î": 230, "Ï": 230, "Ñ": 568, "Ó": 544, "Ô": 544, "Õ": 544, "Ö": 544, "Ú": 528, "Û": 528, "Ü": 528, "à": 467, "á": 467, "â": 467, "ã": 467, "ä": 467, "ç": 435, "è": 461, "é": 461, "ê": 461, "ë": 461, "í": 224, "î": 224, "ï": 224, "ñ": 485, "ó": 459, "ô": 459, "õ": 459, "ö": 459, "ú": 479, "û": 479, "ü": 479, "º": 314, "ª": 311, "°": 316, "·": 189, "–": 486, "—": 750, "…": 518, "×": 425, "±": 424, "’": 158, "‘": 158, "“": 299, "”": 299, "«": 465, "»": 465, "€": 529 } }, "medio": { "wght": 600, "wdth": 100, "asc": 794, "desc": 207, "tinta_cima": 949, "tinta_baixo": 207, "av": { " ": 269, "!": 271, '"': 378, "#": 624, "$": 577, "%": 687, "&": 652, "'": 178, "(": 339, ")": 339, "*": 430, "+": 528, ",": 227, "-": 480, ".": 227, "/": 378, "0": 552, "1": 333, "2": 517, "3": 529, "4": 569, "5": 544, "6": 513, "7": 503, "8": 563, "9": 513, ":": 227, ";": 227, "<": 424, "=": 459, ">": 429, "?": 432, "@": 890, "A": 647, "B": 646, "C": 619, "D": 656, "E": 598, "F": 559, "G": 646, "H": 679, "I": 275, "J": 505, "K": 642, "L": 573, "M": 779, "N": 700, "O": 646, "P": 623, "Q": 657, "R": 652, "S": 616, "T": 481, "U": 655, "V": 587, "W": 847, "X": 567, "Y": 503, "Z": 544, "[": 294, "\\": 378, "]": 294, "^": 503, "_": 436, "`": 294, "a": 532, "b": 544, "c": 498, "d": 539, "e": 536, "f": 317, "g": 539, "h": 559, "i": 251, "j": 268, "k": 529, "l": 290, "m": 856, "n": 559, "o": 545, "p": 544, "q": 539, "r": 427, "s": 519, "t": 326, "u": 556, "v": 500, "w": 773, "x": 517, "y": 483, "z": 495, "{": 360, "|": 275, "}": 360, "~": 514, "À": 647, "Á": 647, "Â": 647, "Ã": 647, "Ä": 647, "Ç": 619, "È": 598, "É": 598, "Ê": 598, "Ë": 598, "Í": 275, "Î": 275, "Ï": 275, "Ñ": 700, "Ó": 646, "Ô": 646, "Õ": 646, "Ö": 646, "Ú": 655, "Û": 655, "Ü": 655, "à": 532, "á": 532, "â": 532, "ã": 532, "ä": 532, "ç": 498, "è": 536, "é": 536, "ê": 536, "ë": 536, "í": 251, "î": 251, "ï": 251, "ñ": 559, "ó": 545, "ô": 545, "õ": 545, "ö": 545, "ú": 556, "û": 556, "ü": 556, "º": 342, "ª": 344, "°": 364, "·": 212, "–": 558, "—": 856, "…": 583, "×": 503, "±": 528, "’": 178, "‘": 178, "“": 319, "”": 319, "«": 502, "»": 502, "€": 630 } }, "normal": { "wght": 400, "wdth": 100, "asc": 794, "desc": 207, "tinta_cima": 936, "tinta_baixo": 207, "av": { " ": 269, "!": 271, '"': 378, "#": 624, "$": 577, "%": 687, "&": 652, "'": 178, "(": 339, ")": 339, "*": 430, "+": 528, ",": 227, "-": 480, ".": 227, "/": 378, "0": 552, "1": 333, "2": 517, "3": 529, "4": 569, "5": 544, "6": 513, "7": 503, "8": 563, "9": 513, ":": 227, ";": 227, "<": 424, "=": 459, ">": 429, "?": 432, "@": 890, "A": 647, "B": 646, "C": 619, "D": 656, "E": 598, "F": 559, "G": 646, "H": 679, "I": 275, "J": 505, "K": 642, "L": 573, "M": 779, "N": 700, "O": 646, "P": 623, "Q": 657, "R": 652, "S": 616, "T": 481, "U": 655, "V": 587, "W": 847, "X": 567, "Y": 503, "Z": 544, "[": 294, "\\": 378, "]": 294, "^": 503, "_": 436, "`": 294, "a": 532, "b": 544, "c": 498, "d": 539, "e": 536, "f": 317, "g": 539, "h": 559, "i": 251, "j": 268, "k": 529, "l": 290, "m": 856, "n": 559, "o": 545, "p": 544, "q": 539, "r": 427, "s": 519, "t": 326, "u": 556, "v": 500, "w": 773, "x": 517, "y": 483, "z": 495, "{": 360, "|": 275, "}": 360, "~": 514, "À": 647, "Á": 647, "Â": 647, "Ã": 647, "Ä": 647, "Ç": 619, "È": 598, "É": 598, "Ê": 598, "Ë": 598, "Í": 275, "Î": 275, "Ï": 275, "Ñ": 700, "Ó": 646, "Ô": 646, "Õ": 646, "Ö": 646, "Ú": 655, "Û": 655, "Ü": 655, "à": 532, "á": 532, "â": 532, "ã": 532, "ä": 532, "ç": 498, "è": 536, "é": 536, "ê": 536, "ë": 536, "í": 251, "î": 251, "ï": 251, "ñ": 559, "ó": 545, "ô": 545, "õ": 545, "ö": 545, "ú": 556, "û": 556, "ü": 556, "º": 342, "ª": 344, "°": 364, "·": 212, "–": 558, "—": 856, "…": 583, "×": 503, "±": 528, "’": 178, "‘": 178, "“": 319, "”": 319, "«": 502, "»": 502, "€": 630 } } };

  // cartoes.ts
  var COR = "#e10600";
  var TINTA = "#141414";
  var MARGEM = 48;
  function larguraTexto(texto2, tam, estilo) {
    var _a;
    const t = LARGURAS[estilo];
    let s = 0;
    for (const ch of texto2) s += (_a = t.av[ch]) != null ? _a : t.av["M"];
    return s * tam * 1.005 / 1e3;
  }
  function texto(txt, tam, estilo, cor, x, y) {
    const t = LARGURAS[estilo];
    const h = (t.tinta_cima + t.tinta_baixo) * tam / 1e3;
    return { texto: txt, tam, estilo, cor, x, y, w: larguraTexto(txt, tam, estilo), h, base: y + t.tinta_cima * tam / 1e3 };
  }
  var caracteresFaltando = (s, estilo) => [...s].filter((c) => LARGURAS[estilo].av[c] === void 0);
  var lim = (x) => Math.max(0, Math.min(1, x));
  var saiCubica = (x) => 1 - Math.pow(1 - lim(x), 3);
  var suave = (x) => {
    x = lim(x);
    return x * x * (3 - 2 * x);
  };
  function envelope(c, t, ent, sai) {
    if (t < c.em || t > c.ate) return 0;
    return Math.min(suave((t - c.em) / ent), suave((c.ate - t) / sai));
  }
  function montarPessoa(c, cena, avisos) {
    var _a, _b, _c, _d, _e, _f;
    const cor = (_a = c.cor) != null ? _a : COR, pb = (_b = c.pb) != null ? _b : true;
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
    if (func) textos.push(texto(c.funcao, tamF, "normal", "#4a4a4a", tx, y0 + nome.h + 14));
    const w = Math.ceil(tx + Math.max(...textos.map((t) => t.w)) + pad + 22);
    for (const s of [c.nome, (_c = c.funcao) != null ? _c : ""]) {
      const f = caracteresFaltando(s, "forte");
      if (f.length) avisos.push(`${c.id}: sem largura para ${f.join("")}`);
    }
    const m = (_d = cena.margem) != null ? _d : MARGEM;
    const x = c.pos ? c.pos[0] : c.lado === "direita" ? cena.largura - 96 - w : 96;
    const y = c.pos ? c.pos[1] : cena.altura - 96 - h;
    if (x < m || y < m || x + w > cena.largura - m || y + h > cena.altura - m) avisos.push(`${c.id}: cartão encosta na margem`);
    const desloca = (t) => ({ ...t, x: t.x + x, y: t.y + y, base: t.base + y });
    const [iw, ih] = (_e = c.fotoTam) != null ? _e : [foto, foto];
    const esc2 = Math.max(foto / iw, foto / ih);
    const [fx, fy] = (_f = c.fotoFoco) != null ? _f : [0.5, 0.3];
    const dw = iw * esc2, dh = ih * esc2;
    const ix = Math.min(0, Math.max(foto - dw, foto / 2 - fx * dw)), iy = Math.min(0, Math.max(foto - dh, foto / 2 - fy * dh));
    const fxp = x + barra + pad, fyp = y + pad;
    return {
      c: { ...c, cor, pb },
      cartao: { x, y, w, h, r: 6, cor: "#ffffff", sombra: true },
      barra: { x, y, w: barra, h, cor },
      foto: { clip: { x: fxp, y: fyp, w: foto, h: foto }, r: 4, img: { x: fxp + ix, y: fyp + iy, w: dw, h: dh }, src: c.foto, pb },
      textos: textos.map(desloca),
      caixa: { x, y, w, h },
      dx0: c.lado === "direita" ? 40 : -40
    };
  }
  function montarCapitulo(c, cena, avisos) {
    var _a, _b;
    const cor = (_a = c.cor) != null ? _a : COR, fundo = (_b = c.fundo) != null ? _b : "#f3f1ec";
    const W = cena.largura, H = cena.altura, maxW = W - 2 * 160;
    const parte = `PARTE ${String(c.numero).padStart(2, "0")}`;
    const tParte = texto(parte, 64, "forte", cor, 0, 0);
    let linhas = [c.titulo];
    let tam = 168;
    while (tam > 110 && larguraTexto(c.titulo, tam, "forte") > maxW) tam -= 2;
    if (larguraTexto(c.titulo, tam, "forte") > maxW) {
      const ps = c.titulo.split(" ");
      let melhor = 1, pior = Infinity;
      for (let i = 1; i < ps.length; i++) {
        const a = larguraTexto(ps.slice(0, i).join(" "), 100, "forte"), b = larguraTexto(ps.slice(i).join(" "), 100, "forte");
        if (Math.max(a, b) < pior) {
          pior = Math.max(a, b);
          melhor = i;
        }
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
    let tracado;
    if (tr && c.tracado) {
      const s = Math.min(tr.w / c.tracado.largura, tr.h / c.tracado.altura);
      const w = c.tracado.largura * s, h = c.tracado.altura * s;
      const x = (W - w) / 2, yy = y + (tr.h - h) / 2;
      tracado = { d: c.tracado.d, transform: `translate(${n2(x)} ${n2(yy)}) scale(${s.toFixed(5)})`, caixa: { x, y: yy, w, h }, larg: 9 / s };
      y += tr.h + gap1;
    }
    const textos = [];
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
  function ancoraTag(c, t) {
    const a = c.ancora;
    if (typeof a[0] === "number") return a;
    const tr = a;
    if (t <= tr[0].t) return [tr[0].x, tr[0].y];
    const n = tr.length - 1;
    if (t >= tr[n].t) return [tr[n].x, tr[n].y];
    let i = 0;
    while (t > tr[i + 1].t) i++;
    const u = (t - tr[i].t) / (tr[i + 1].t - tr[i].t);
    return [tr[i].x + (tr[i + 1].x - tr[i].x) * u, tr[i].y + (tr[i + 1].y - tr[i].y) * u];
  }
  var DIRS = { ne: [0.55, -0.85], no: [-0.55, -0.85], se: [0.55, 0.85], so: [-0.55, 0.85] };
  var PAD_X = 18;
  var PAD_Y = 12;
  var LISTRA = 6;
  function caixaTag(m, p) {
    const [ux, uy] = DIRS[m.lado];
    const ex = p[0] + ux * m.perna, ey = p[1] + uy * m.perna;
    const x = ux > 0 ? ex : ex - m.w;
    const y = uy < 0 ? ey - m.h : ey;
    return { x, y, w: m.w, h: m.h };
  }
  function montarTag(c, cena, avisos) {
    var _a, _b, _c;
    const cor = (_a = c.cor) != null ? _a : COR, perna = (_b = c.perna) != null ? _b : 110;
    const tx = texto(c.texto, 32, "medio", TINTA, 0, 0);
    const w = Math.ceil(LISTRA + PAD_X + tx.w + PAD_X), h = Math.ceil(tx.h + 2 * PAD_Y);
    const f = caracteresFaltando(c.texto, "medio");
    if (f.length) avisos.push(`${c.id}: sem largura para ${f.join("")}`);
    const marg = (_c = cena.margem) != null ? _c : MARGEM;
    const ordem = !c.lado || c.lado === "auto" ? ["ne", "no", "se", "so"] : [c.lado];
    let escolhido = null;
    let melhor = ordem[0], menor = Infinity;
    for (const lado of ordem) {
      let pior = 0;
      for (let q = Math.floor(c.em * cena.fps); q <= Math.ceil(c.ate * cena.fps); q++) {
        const b = caixaTag({ w, h, lado, perna }, ancoraTag(c, q / cena.fps));
        pior = Math.max(pior, marg - b.x, marg - b.y, b.x + b.w - (cena.largura - marg), b.y + b.h - (cena.altura - marg));
      }
      if (pior <= 0) {
        escolhido = lado;
        break;
      }
      if (pior < menor) {
        menor = pior;
        melhor = lado;
      }
    }
    if (!escolhido) avisos.push(`${c.id}: nenhum lado cabe o tempo todo; caixa empurrada para dentro (até ${menor.toFixed(0)} px)`);
    return { c: { ...c, cor, perna }, lado: escolhido != null ? escolhido : melhor, empurrada: !escolhido, w, h, texto: tx };
  }
  function montarCartoes(cena) {
    const avisos = [];
    const itens = cena.cartoes.map((c) => ({
      tipo: c.tipo,
      m: c.tipo === "pessoa" ? montarPessoa(c, cena, avisos) : c.tipo === "capitulo" ? montarCapitulo(c, cena, avisos) : montarTag(c, cena, avisos)
    }));
    return { cena, itens, avisos };
  }
  var n2 = (x) => Math.round(x * 100) / 100;
  var esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  function svgTexto(t, dx = 0, dy = 0) {
    const L = LARGURAS[t.estilo];
    return `<text x="${n2(t.x + dx)}" y="${n2(t.base + dy)}" font-family="Bahnschrift" font-size="${t.tam}" fill="${t.cor}" style="font-variation-settings:'wght' ${L.wght},'wdth' ${L.wdth};font-weight:${L.wght};font-stretch:${L.wdth}%;font-kerning:none;font-feature-settings:'kern' 0,'liga' 0">${esc(t.texto)}</text>`;
  }
  function rr(x, y, w, h, r) {
    return `M${n2(x + r)} ${n2(y)}H${n2(x + w - r)}A${r} ${r} 0 0 1 ${n2(x + w)} ${n2(y + r)}V${n2(y + h - r)}A${r} ${r} 0 0 1 ${n2(x + w - r)} ${n2(y + h)}H${n2(x + r)}A${r} ${r} 0 0 1 ${n2(x)} ${n2(y + h - r)}V${n2(y + r)}A${r} ${r} 0 0 1 ${n2(x + r)} ${n2(y)}Z`;
  }
  var SOMBRA = (id) => `<filter id="${id}" x="-20%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.16"/></filter>`;
  function estadoPessoa(p, t) {
    var _a;
    const op = envelope(p.c, t, 0.3, 0.25);
    if (op <= 0) return null;
    const dx = p.dx0 * (1 - saiCubica((t - p.c.em) / 0.3));
    const id = `cp-${p.c.id}`;
    const f = p.foto;
    const foto = f.src ? `<image href="${esc(f.src)}" x="${n2(f.img.x)}" y="${n2(f.img.y)}" width="${n2(f.img.w)}" height="${n2(f.img.h)}" preserveAspectRatio="none" clip-path="url(#${id}-r)"${f.pb ? ` style="filter:grayscale(1) contrast(1.12)"` : ""}/>` : `<g clip-path="url(#${id}-r)"><rect x="${f.clip.x}" y="${f.clip.y}" width="${f.clip.w}" height="${f.clip.h}" fill="#c9c7c2"/><circle cx="${f.clip.x + f.clip.w / 2}" cy="${f.clip.y + f.clip.h * 0.4}" r="${f.clip.w * 0.2}" fill="#8d8b87"/><ellipse cx="${f.clip.x + f.clip.w / 2}" cy="${f.clip.y + f.clip.h}" rx="${f.clip.w * 0.36}" ry="${f.clip.h * 0.32}" fill="#8d8b87"/></g>`;
    const k = p.cartao;
    const svg = `<g opacity="${op.toFixed(4)}" transform="translate(${n2(dx)} 0)"><defs>${SOMBRA(id + "-s")}<clipPath id="${id}-r"><path d="${rr(f.clip.x, f.clip.y, f.clip.w, f.clip.h, f.r)}"/></clipPath></defs><path d="${rr(k.x, k.y, k.w, k.h, (_a = k.r) != null ? _a : 0)}" fill="${k.cor}" filter="url(#${id}-s)"/><rect x="${p.barra.x}" y="${p.barra.y}" width="${p.barra.w}" height="${p.barra.h}" fill="${p.barra.cor}"/>` + foto + p.textos.map((tx) => svgTexto(tx)).join("") + `</g>`;
    return {
      id: p.c.id,
      tipo: "pessoa",
      opacidade: op,
      caixa: { ...p.caixa, x: p.caixa.x + dx },
      textos: p.textos.map((tx) => ({ x: tx.x + dx, y: tx.y, w: tx.w, h: tx.h })),
      svg
    };
  }
  function estadoCapitulo(c, t, cena) {
    const op = envelope(c.c, t, 0.2, 0.3);
    if (op <= 0) return null;
    const dy = 18 * (1 - saiCubica((t - c.c.em - 0.05) / 0.4));
    let svg = `<g opacity="${op.toFixed(4)}"><rect x="0" y="0" width="${cena.largura}" height="${cena.altura}" fill="${c.c.fundo}"/>`;
    if (c.tracado) {
      const k = suave((t - c.c.em - 0.15) / 1.3);
      svg += `<g transform="${c.tracado.transform}"><path d="${esc(c.tracado.d)}" fill="none" stroke="${c.c.cor}" stroke-width="${n2(c.tracado.larg)}" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="${(1 - k).toFixed(5)}" opacity="${k > 0 ? 1 : 0}"/></g>`;
    }
    svg += c.textos.map((tx, i) => svgTexto(tx, 0, i === 0 ? 0 : dy)).join("") + `</g>`;
    return {
      id: c.c.id,
      tipo: "capitulo",
      opacidade: op,
      caixa: c.caixa,
      textos: c.textos.map((tx, i) => ({ x: tx.x, y: tx.y + (i === 0 ? 0 : dy), w: tx.w, h: tx.h })),
      svg
    };
  }
  function pertoNaCaixa(b, p) {
    return [Math.max(b.x, Math.min(b.x + b.w, p[0])), Math.max(b.y, Math.min(b.y + b.h, p[1]))];
  }
  function geometriaTag(g, t, cena) {
    var _a;
    const a = ancoraTag(g.c, t);
    const b = caixaTag({ w: g.w, h: g.h, lado: g.lado, perna: g.c.perna }, a);
    if (g.empurrada) {
      const m = (_a = cena.margem) != null ? _a : MARGEM;
      b.x = Math.max(m, Math.min(cena.largura - m - b.w, b.x));
      b.y = Math.max(m, Math.min(cena.altura - m - b.h, b.y));
    }
    return { ancora: a, caixa: b, ponta: pertoNaCaixa(b, a) };
  }
  function estadoTag(g, t, cena) {
    if (t < g.c.em || t > g.c.ate) return null;
    const sai = suave((g.c.ate - t) / 0.2);
    const u = t - g.c.em;
    const kPonto = saiCubica(u / 0.14), kPerna = suave((u - 0.08) / 0.18), kCaixa = suave((u - 0.2) / 0.14);
    const { ancora: a, caixa: b, ponta } = geometriaTag(g, t, cena);
    const tx = { ...g.texto, x: b.x + LISTRA + PAD_X, y: b.y + PAD_Y, base: b.y + PAD_Y + (g.texto.base - g.texto.y) };
    const px = a[0] + (ponta[0] - a[0]) * kPerna, py = a[1] + (ponta[1] - a[1]) * kPerna;
    const id = `tg-${g.c.id}`;
    const svg = `<g opacity="${sai.toFixed(4)}"><defs>${SOMBRA(id + "-s")}</defs>` + (kPerna > 0 ? `<line x1="${n2(a[0])}" y1="${n2(a[1])}" x2="${n2(px)}" y2="${n2(py)}" stroke="${g.c.cor}" stroke-width="3.5" stroke-linecap="round"/>` : "") + `<g opacity="${kCaixa.toFixed(4)}"><rect x="${n2(b.x)}" y="${n2(b.y)}" width="${b.w}" height="${b.h}" rx="5" fill="#ffffff" filter="url(#${id}-s)"/><rect x="${n2(b.x)}" y="${n2(b.y)}" width="${LISTRA}" height="${b.h}" fill="${g.c.cor}"/>${svgTexto(tx)}</g><circle cx="${n2(a[0])}" cy="${n2(a[1])}" r="${n2(8 * kPonto)}" fill="${g.c.cor}" stroke="#ffffff" stroke-width="${n2(3 * kPonto)}"/></g>`;
    const ext = 8 + 3 / 2;
    const x0 = Math.min(b.x, a[0] - ext), y0 = Math.min(b.y, a[1] - ext);
    const x1 = Math.max(b.x + b.w, a[0] + ext), y1 = Math.max(b.y + b.h, a[1] + ext);
    return {
      id: g.c.id,
      tipo: "tag",
      opacidade: sai * kCaixa,
      caixa: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 },
      textos: [{ x: tx.x, y: tx.y, w: tx.w, h: tx.h }],
      tag: { ancora: a, ponta, caixa: b, lado: g.lado, empurrada: g.empurrada },
      svg
    };
  }
  function estadoCartoes(m, t) {
    const out = [];
    for (const it of m.itens) {
      const e = it.tipo === "pessoa" ? estadoPessoa(it.m, t) : it.tipo === "capitulo" ? estadoCapitulo(it.m, t, m.cena) : estadoTag(it.m, t, m.cena);
      if (e) out.push(e);
    }
    return out;
  }
  function svgCartoes(m, t) {
    return estadoCartoes(m, t).map((e) => e.svg).join("");
  }
  function checarCartoes(m) {
    var _a, _b, _c, _d, _e, _f;
    const { fps, duracao, largura: W, altura: H } = m.cena;
    const marg = (_a = m.cena.margem) != null ? _a : MARGEM;
    const nq = Math.round(duracao * fps) + 1;
    const rel = { quadros: nq, falhas: [], avisos: [...m.avisos], porCartao: {} };
    const dentro = (a, b, tol = 1e-6) => a.x >= b.x - tol && a.y >= b.y - tol && a.x + a.w <= b.x + b.w + tol && a.y + a.h <= b.y + b.h + tol;
    for (let q = 0; q < nq; q++) {
      for (const e of estadoCartoes(m, q / fps)) {
        const r = (_d = (_b = rel.porCartao)[_c = e.id]) != null ? _d : _b[_c] = { quadros: 0, folgaMinQuadro: Infinity, lados: [], textoForaDoCartao: 0 };
        r.quadros++;
        const fol = (c) => Math.min(c.x, c.y, W - (c.x + c.w), H - (c.y + c.h));
        const folga = fol(e.tag ? e.tag.caixa : e.caixa);
        r.folgaMinQuadro = Math.min(r.folgaMinQuadro, folga);
        if (e.tipo !== "capitulo" && folga < marg - 1e-6) rel.falhas.push(`${e.id}: sai da margem segura (folga ${folga.toFixed(1)} px, q${q})`);
        const ancDentro = !e.tag || e.tag.ancora[0] >= 10 && e.tag.ancora[1] >= 10 && e.tag.ancora[0] <= W - 10 && e.tag.ancora[1] <= H - 10;
        if (ancDentro && fol(e.caixa) < -1e-6) rel.falhas.push(`${e.id}: sai do quadro (q${q})`);
        const cont = e.tipo === "tag" ? e.tag.caixa : e.tipo === "capitulo" ? { x: 160, y: 0, w: W - 320, h: H } : e.caixa;
        for (const tx of e.textos) if (!dentro(tx, cont)) {
          r.textoForaDoCartao++;
          rel.falhas.push(`${e.id}: texto fora do cartão (q${q})`);
        }
        if (e.tag) {
          if (!r.lados.includes(e.tag.lado)) r.lados.push(e.tag.lado);
          const b = e.tag.caixa, p = e.tag.ponta;
          const naBorda = Math.min(Math.abs(p[0] - b.x), Math.abs(p[0] - b.x - b.w), Math.abs(p[1] - b.y), Math.abs(p[1] - b.y - b.h));
          r.pernaErroMax = Math.max((_e = r.pernaErroMax) != null ? _e : 0, naBorda);
          const comp = Math.hypot(p[0] - e.tag.ancora[0], p[1] - e.tag.ancora[1]);
          if (!e.tag.empurrada && comp < 40) rel.falhas.push(`${e.id}: perninha curta (${comp.toFixed(1)} px, q${q})`);
        }
      }
    }
    for (const [id, r] of Object.entries(rel.porCartao)) {
      if (r.lados.length > 1) rel.falhas.push(`${id}: tag trocou de lado (${r.lados})`);
      if (((_f = r.pernaErroMax) != null ? _f : 0) > 1e-6) rel.falhas.push(`${id}: perninha não termina na borda da etiqueta (${r.pernaErroMax})`);
    }
    for (const it of m.itens) if (it.tipo === "pessoa") {
      const p = it.m;
      if (!dentro(p.foto.clip, p.cartao)) rel.falhas.push(`${p.c.id}: foto fora do cartão`);
      if (!dentro(p.foto.clip, p.foto.img, 1e-3)) rel.falhas.push(`${p.c.id}: foto não cobre o recorte`);
    }
    rel.falhas = [...new Set(rel.falhas)].slice(0, 40);
    return rel;
  }
  return __toCommonJS(cartoes_exports);
})();
