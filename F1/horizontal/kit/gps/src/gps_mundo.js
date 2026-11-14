// "Vida" em volta da pista PLANA (kit/gps, modo sem modelo 3D). Uso real (card "Nove milésimos", 2026-11-14): o mundo
// era um plano cinza liso; a 349 km/h o fundo andava ~0,1 px por quadro e o carro parecia parado. Tudo aqui é
// procedural, determinístico (mesma pista = mesmo mundo nos dois motores) e só usa o traçado da pista plana:
//  - chão com ladrilhos claros (referência de movimento), fundo claro preservado (assinatura do canal);
//  - zebras vermelho/branco no lado de dentro das curvas (curvatura alta);
//  - placas de distância a cada 100 m nas retas e "arquibancadas"/prédios como blocos coloridos fora da pista;
//  - placa com o número da curva (curvas = [{n, frac}] = fração da volta, da distância do kit/graficos).
// Não importa o three: recebe THREE como parâmetro.

function rng(semente) {
  let x = semente >>> 0 || 1;
  return () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
}

/** Pontos da linha central com distância acumulada, tangente, normal e curvatura (1/m). */
export function amostrarCentro(plana) {
  const c = plana.centro;
  const n = c.x.length;
  const pts = [];
  let s = 0;
  for (let k = 0; k < n; k++) {
    const a = [c.x[k], c.z[k]], b = [c.x[(k + 1) % n], c.z[(k + 1) % n]];
    if (k > 0) s += Math.hypot(a[0] - pts[k - 1].x, a[1] - pts[k - 1].z);
    const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz) || 1;
    pts.push({ x: a[0], z: a[1], s, tx: dx / l, tz: dz / l, nx: -dz / l, nz: dx / l });
  }
  const L = s + Math.hypot(pts[0].x - pts[n - 1].x, pts[0].z - pts[n - 1].z);
  // curvatura com sinal pela variação do rumo numa janela de ±8 pontos
  for (let k = 0; k < n; k++) {
    const a = pts[(k - 8 + n) % n], b = pts[(k + 8) % n];
    let d = Math.atan2(b.tx, b.tz) - Math.atan2(a.tx, a.tz);
    while (d > Math.PI) d -= 2 * Math.PI;
    while (d < -Math.PI) d += 2 * Math.PI;
    const ds = Math.max(1, (b.s - a.s + L) % L);
    pts[k].k = d / ds;
  }
  return { pts, L };
}

/** Ponto da linha central na fração `f` da volta (0 = linha de chegada). */
export function pontoNaFracao(amostra, f) {
  const alvo = ((f % 1) + 1) % 1 * amostra.L;
  const p = amostra.pts;
  let i = 0;
  while (i < p.length - 1 && p[i + 1].s < alvo) i++;
  return p[i];
}

function distanciaMin(pts, x, z) {
  let m = Infinity;
  for (let k = 0; k < pts.length; k += 2) m = Math.min(m, (pts[k].x - x) ** 2 + (pts[k].z - z) ** 2);
  return Math.sqrt(m);
}

function texturaLadrilho(THREE) {
  const cv = document.createElement("canvas");
  cv.width = cv.height = 128;
  const g = cv.getContext("2d");
  g.fillStyle = "#e4e6dc";
  g.fillRect(0, 0, 128, 128);
  g.fillStyle = "#d6dacb";
  g.fillRect(0, 0, 64, 64);
  g.fillRect(64, 64, 64, 64);
  g.strokeStyle = "#c9cdbd";
  g.lineWidth = 2;
  g.strokeRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function placa(THREE, texto, { cor = "#141414", fundo = "#ffffff", w = 6, h = 4 } = {}) {
  const cv = document.createElement("canvas");
  cv.width = 256;
  cv.height = Math.round((256 * h) / w);
  const g = cv.getContext("2d");
  g.fillStyle = fundo;
  g.fillRect(0, 0, cv.width, cv.height);
  g.strokeStyle = cor;
  g.lineWidth = 10;
  g.strokeRect(5, 5, cv.width - 10, cv.height - 10);
  g.fillStyle = cor;
  g.font = `900 ${Math.round(cv.height * 0.62)}px "Bahnschrift", "Arial Black", sans-serif`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(texto, cv.width / 2, cv.height / 2 + 4);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
  return m;
}

/**
 * Grupo com o mundo em volta da pista plana. opcoes: { curvas: [{n, frac}], semente }.
 * Coordenadas = as da pista plana (y = 0 é o asfalto).
 */
export function criarMundoPlano(THREE, plana, { curvas = [], semente = 7 } = {}) {
  const g = new THREE.Group();
  g.name = "mundo_plano";
  const am = amostrarCentro(plana);
  const P = am.pts;
  const meia = plana.largura_m / 2 + (plana.zebra_m ?? 1);
  const r = rng(semente);

  // chão com ladrilhos de 20 m (fica por baixo da pista; não escreve profundidade)
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const p of P) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); z0 = Math.min(z0, p.z); z1 = Math.max(z1, p.z); }
  const W = x1 - x0 + 1400, H = z1 - z0 + 1400;
  const tex = texturaLadrilho(THREE);
  tex.repeat.set(W / 40, H / 40);
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshLambertMaterial({ map: tex, depthWrite: false }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.set((x0 + x1) / 2, -0.01, (z0 + z1) / 2);
  chao.renderOrder = -3;
  g.add(chao);

  // zebras: blocos de 3 m alternando vermelho/branco do lado de dentro das curvas
  const zebraGeo = new THREE.BoxGeometry(1.4, 0.06, 3);
  const mVerm = new THREE.MeshLambertMaterial({ color: 0xd8262b }), mBran = new THREE.MeshLambertMaterial({ color: 0xffffff });
  let alt = 0, ultimo = -10;
  for (const p of P) {
    if (Math.abs(p.k) < 0.012 || p.s - ultimo < 3) continue;
    ultimo = p.s;
    const lado = p.k > 0 ? 1 : -1;   // dentro da curva
    const b = new THREE.Mesh(zebraGeo, alt++ % 2 ? mVerm : mBran);
    b.position.set(p.x + p.nx * lado * (plana.largura_m / 2 + 0.7), 0.03, p.z + p.nz * lado * (plana.largura_m / 2 + 0.7));
    b.rotation.y = Math.atan2(p.tx, p.tz);
    g.add(b);
  }

  // retas: placas de distância a cada 100 m e arquibancadas do lado de fora
  const coresArq = [0x7fa7c9, 0xd9c27a, 0xc98a84, 0x8fbfa3, 0xa898c4];   // tons suaves: fundo claro continua a assinatura
  let proxPlaca = 0, proxArq = 0;
  for (const p of P) {
    const reta = Math.abs(p.k) < 0.002;
    if (reta && p.s >= proxPlaca) {
      proxPlaca = p.s + 100;
      const pl = placa(THREE, String(Math.round((p.s % 1000) / 100) || "1"), { w: 2.4, h: 1.6 });
      pl.position.set(p.x + p.nx * (meia + 3), 1.3, p.z + p.nz * (meia + 3));
      pl.rotation.y = Math.atan2(p.tx, p.tz) + Math.PI;
      g.add(pl);
    }
    if (reta && p.s >= proxArq) {
      proxArq = p.s + 34 + 20 * r();
      for (const lado of [1, -1]) {
        const off = meia + 30 + 10 * r();
        const x = p.x + p.nx * lado * off, z = p.z + p.nz * lado * off;
        if (distanciaMin(P, x, z) < meia + 16) continue;   // não invade outro trecho da pista
        const h = 4 + 4 * r(), w = 22 + 8 * r();
        const arq = new THREE.Mesh(new THREE.BoxGeometry(w, h, 7),
          new THREE.MeshLambertMaterial({ color: coresArq[Math.floor(r() * coresArq.length)] }));
        arq.position.set(x, h / 2, z);
        arq.rotation.y = Math.atan2(p.tx, p.tz) + Math.PI / 2;
        g.add(arq);
      }
    }
  }

  // prédios longe da pista (a cidade em volta): blocos claros de alturas variadas
  const coresPred = [0xf2efe6, 0xe6dccb, 0xd9e3ea, 0xefe1d6, 0xdfe7d8];
  for (let k = 0; k < 260; k++) {
    const x = x0 - 500 + r() * (W - 200), z = z0 - 500 + r() * (H - 200);
    if (distanciaMin(P, x, z) < 90) continue;
    const w = 20 + 40 * r(), d = 20 + 40 * r(), h = 12 + 70 * r() * r();
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d),
      new THREE.MeshLambertMaterial({ color: coresPred[Math.floor(r() * coresPred.length)] }));
    b.position.set(x, h / 2, z);
    b.rotation.y = r() * Math.PI;
    g.add(b);
  }

  // placa com o número de cada curva pedida, do lado de fora, em pé
  for (const c of curvas) {
    const p = pontoNaFracao(am, c.frac);
    const lado = p.k > 0 ? -1 : 1;   // fora da curva
    const pl = placa(THREE, String(c.n), { cor: "#ffffff", fundo: "#d8262b", w: 5, h: 5 });
    pl.position.set(p.x + p.nx * lado * (meia + 9), 4.2, p.z + p.nz * lado * (meia + 9));
    pl.rotation.y = Math.atan2(p.tx, p.tz) + Math.PI;
    const poste = new THREE.Mesh(new THREE.BoxGeometry(0.3, 4.2, 0.3), new THREE.MeshLambertMaterial({ color: 0x555555 }));
    poste.position.set(pl.position.x, 2.1, pl.position.z);
    g.add(pl, poste);
  }
  return g;
}

/** Deixa o carro translúcido (fantasma) ou opaco de novo. Clona os materiais na 1ª vez (o .glb pode ser compartilhado). */
export function opacidadeCarro(obj, a) {
  if (obj.userData.opacidade === a) return;
  obj.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.userData.matProprio) {
      o.material = Array.isArray(o.material) ? o.material.map((m) => m.clone()) : o.material.clone();
      o.userData.matProprio = true;
    }
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      m.transparent = a < 1;
      m.opacity = a;
      m.depthWrite = a >= 1;
    }
  });
  obj.userData.opacidade = a;
}
