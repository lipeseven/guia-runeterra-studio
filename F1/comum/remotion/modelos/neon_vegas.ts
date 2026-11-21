// Las Vegas NOTURNA em neon (pedido do Felipe, 2026-11-21: "muito escuro e sem vida"; referência de ambientação: escuro
// mas LUMINOSO, paleta roxo/magenta/ciano, arestas em neon, janelas acesas, bloom, névoa roxa, cones de luz, traçado em neon).
// Só peças fixas, criadas uma vez com o circuito (criarCircuito("lasvegas", { cenario: true, noite: true }) liga o neon por
// padrão; `neon: false` volta ao noturno antigo). O que muda por quadro (pulso de luz na pista, brilho do traçado com a
// altura da câmera, luzes traseiras dos carros, bloom e cor) fica em pos_neon.ts.
// Cores com valor > 1 (HDR): o bloom (limiar ~1) só pega o que é luz de verdade, o resto da cena fica sem halo.
import * as THREE from "three";
import { seed } from "./mundo";

export const NEON = {
  magenta: "#ff2bd6",
  ciano: "#22e5ff",
  laranja: "#ff8a2b",
  violeta: "#8a5bff",
  rosa: "#ff2d6f",
  ambar: "#ffb347",
};
const PALETA = [NEON.magenta, NEON.ciano, NEON.laranja, NEON.violeta, NEON.rosa, NEON.ciano, NEON.magenta];

/** Material de tubo de neon: cor pura, acima de 1 para o bloom. */
export const matNeon = (forca = 3, o: THREE.MeshBasicMaterialParameters = {}) => {
  const m = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, ...o });
  m.color.setScalar(forca);
  return m;
};

let texJanelas: THREE.CanvasTexture[] | null = null;
/** Fachadas à noite em neon: 4 grades diferentes (janelas em fita, em pontos, em colunas, quase apagada), com acesas
 *  quentes, frias e algumas coloridas; cada prédio usa uma e um deslocamento próprio, para nenhum repetir o vizinho. */
export function janelasNeon() {
  if (texJanelas) return texJanelas;
  texJanelas = [0, 1, 2, 3].map((tipo) => {
    const c = document.createElement("canvas");
    c.width = 128;
    c.height = 256;
    const x = c.getContext("2d")!;
    x.fillStyle = "#000";
    x.fillRect(0, 0, 128, 256);
    const cores = ["#ffd9a0", "#ffe9c8", "#bfe6ff", "#ffb45c", "#ff7ad9", "#6fe8ff", "#c9b2ff"];
    for (let l = 0; l < 16; l++) for (let k = 0; k < 8; k++) {
      const r = seed(l * 17 + k * 31 + tipo * 101 + 7);
      const vazio = tipo === 3 ? 0.72 : tipo === 1 ? 0.45 : 0.3;
      if (r < vazio) continue;
      const cor = cores[Math.floor(seed(l * 5 + k * 13 + tipo * 7) * (r > 0.93 ? cores.length : 4))];
      x.globalAlpha = 0.55 + 0.45 * seed(l * 3 + k * 11 + tipo);
      x.fillStyle = cor;
      if (tipo === 0) x.fillRect(k * 16, l * 16 + 4, 16, 7); // fitas horizontais contínuas (vidro corrido)
      else if (tipo === 2) x.fillRect(k * 16 + 5, l * 16, 6, 16); // colunas verticais
      else x.fillRect(k * 16 + 3, l * 16 + 3, 10, 9); // janelas soltas
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 16;
    return t;
  });
  return texJanelas;
}

type Pts = number[]; // contorno achatado x0, n0, x1, n1, ... (z do mundo = -n)

/** Arestas em neon dos prédios reais: coroa no alto de cada fachada, aro no telhado (é o que desenha os quarteirões vistos
 *  do alto), quinas verticais nas torres e letreiros verticais em algumas fachadas. Uma malha só (uma chamada de desenho). */
export function arestasNeon(lista: [number, Pts][]) {
  const pos: number[] = [], cor: number[] = [];
  const c = new THREE.Color();
  const quad = (a: number[], b: number[], d: number[], e: number[]) => {
    pos.push(...a, ...b, ...d, ...b, ...e, ...d);
    for (let k = 0; k < 6; k++) cor.push(c.r, c.g, c.b);
  };
  lista.forEach(([h, p], n) => {
    if (h < 9) return;
    const s = seed(n * 13 + 5);
    if (s < 0.22) return; // nem todo prédio tem neon
    c.set(PALETA[Math.floor(seed(n * 7 + 1) * PALETA.length)]);
    const v: [number, number][] = [];
    for (let i = 0; i < p.length; i += 2) v.push([p[i], -p[i + 1]]);
    if (v.length > 2 && v[0][0] === v[v.length - 1][0] && v[0][1] === v[v.length - 1][1]) v.pop();
    const cx = v.reduce((q, w) => q + w[0], 0) / v.length, cz = v.reduce((q, w) => q + w[1], 0) / v.length;
    const fora = (x: number, z: number, d: number) => {
      const l = Math.hypot(x - cx, z - cz) || 1;
      return [x + ((x - cx) / l) * d, z + ((z - cz) / l) * d];
    };
    const torre = h >= 35;
    const coroa = Math.min(2.4, 0.6 + h * 0.012);
    let maior = -1, iMaior = 0;
    for (let i = 0; i < v.length; i++) {
      const [x0, z0] = v[i], [x1, z1] = v[(i + 1) % v.length];
      const L = Math.hypot(x1 - x0, z1 - z0);
      if (L > maior) [maior, iMaior] = [L, i];
      const [ax, az] = fora(x0, z0, 0.35), [bx, bz] = fora(x1, z1, 0.35);
      // coroa: faixa no alto da fachada
      quad([ax, h - coroa, az], [ax, h, az], [bx, h - coroa, bz], [bx, h, bz]);
      // aro no telhado (horizontal, de dentro para fora): de cima ele vira o contorno do quarteirão
      const [ix, iz] = fora(x0, z0, -2.6), [jx, jz] = fora(x1, z1, -2.6);
      quad([ix, h + 0.08, iz], [ax, h + 0.08, az], [jx, h + 0.08, jz], [bx, h + 0.08, bz]);
      // quinas verticais nas torres (uma sim, uma não)
      if (torre && i % 2 === 0 && s > 0.45) {
        const [px, pz] = fora(x0, z0, 0.4);
        const tx = (x1 - x0) / (L || 1), tz = (z1 - z0) / (L || 1);
        quad([px, 0.5, pz], [px, h, pz], [px + tx * 0.9, 0.5, pz + tz * 0.9], [px + tx * 0.9, h, pz + tz * 0.9]);
      }
    }
    // letreiro vertical aceso na maior fachada de algumas torres (cor própria, sem texto nem marca)
    if (torre && seed(n * 3 + 11) > 0.55 && maior > 14) {
      const [x0, z0] = v[iMaior], [x1, z1] = v[(iMaior + 1) % v.length];
      const m = 0.5 + (seed(n + 3) - 0.5) * 0.4;
      const mx = x0 + (x1 - x0) * m, mz = z0 + (z1 - z0) * m;
      const tx = (x1 - x0) / maior, tz = (z1 - z0) / maior;
      const [ox, oz] = fora(mx, mz, 0.6);
      const meia = 2.2, y0 = h * 0.35, y1 = Math.min(h - coroa - 2, y0 + 14 + seed(n) * 22);
      c.set(PALETA[Math.floor(seed(n * 5 + 9) * PALETA.length)]);
      if (y1 > y0 + 6) quad([ox - tx * meia, y0, oz - tz * meia], [ox - tx * meia, y1, oz - tz * meia], [ox + tx * meia, y0, oz + tz * meia], [ox + tx * meia, y1, oz + tz * meia]);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(cor, 3));
  const m = new THREE.Mesh(g, matNeon(2.6, { polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  m.name = "neon_predios";
  m.userData.semSombra = true;
  return m;
}

let texCone: THREE.CanvasTexture | null = null;
let texPoca: THREE.CanvasTexture | null = null;
/** Cones de luz dos postes (planos aditivos, sem volumetria) e a poça de luz no chão embaixo de cada um: só um realce
 *  suave onde a luz bate (nada de asfalto espelhado, pedido do Felipe). */
export function luzDosPostes(postes: { x: number; z: number }[]) {
  if (!texCone) {
    const c = document.createElement("canvas");
    c.width = 4;
    c.height = 128;
    const x = c.getContext("2d")!;
    const g = x.createLinearGradient(0, 0, 0, 128);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(0.5, "rgba(255,255,255,.35)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    x.fillStyle = g;
    x.fillRect(0, 0, 4, 128);
    texCone = new THREE.CanvasTexture(c);
    const p = document.createElement("canvas");
    p.width = p.height = 128;
    const y = p.getContext("2d")!;
    const r = y.createRadialGradient(64, 64, 4, 64, 64, 64);
    r.addColorStop(0, "rgba(255,255,255,1)");
    r.addColorStop(0.45, "rgba(255,255,255,.35)");
    r.addColorStop(1, "rgba(255,255,255,0)");
    y.fillStyle = r;
    y.fillRect(0, 0, 128, 128);
    texPoca = new THREE.CanvasTexture(p);
  }
  const g = new THREE.Group();
  const o = new THREE.Object3D();
  // ápice na lâmpada (y 10,6), boca no chão; o UV vai de 1 (ápice) a 0 (boca): a luz é forte perto da lâmpada e some no chão
  const cone = new THREE.ConeGeometry(4.6, 10.6, 20, 1, true);
  cone.translate(0, 5.3, 0);
  const mc = new THREE.MeshBasicMaterial({ map: texCone, color: "#ffd9a8", transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false });
  const cones = new THREE.InstancedMesh(cone, mc, postes.length);
  const poca = new THREE.PlaneGeometry(16, 16);
  poca.rotateX(-Math.PI / 2);
  const mp = new THREE.MeshBasicMaterial({ map: texPoca, color: "#ffcf96", transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -8, polygonOffsetUnits: -8 });
  const pocas = new THREE.InstancedMesh(poca, mp, postes.length);
  postes.forEach((p, k) => {
    o.position.set(p.x, 0, p.z);
    o.updateMatrix();
    cones.setMatrixAt(k, o.matrix);
    o.position.y = 0.07;
    o.updateMatrix();
    pocas.setMatrixAt(k, o.matrix);
  });
  cones.userData.semSombra = pocas.userData.semSombra = true; // obj() liga sombra em tudo; pos_neon.ts desliga nestes
  g.add(cones, pocas);
  return g;
}

/** Tela de LED da Sphere: faixas de cor (magenta, laranja, ciano, violeta) com a grade de pixels do LED. */
export function ledSphere() {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 512;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 1024, 0);
  [NEON.magenta, NEON.laranja, "#ffd23f", NEON.ciano, NEON.violeta, NEON.magenta].forEach((cor, k, l) => g.addColorStop(k / (l.length - 1), cor));
  x.fillStyle = g;
  x.fillRect(0, 0, 1024, 512);
  const v = x.createLinearGradient(0, 0, 0, 512);
  v.addColorStop(0, "rgba(10,4,30,.55)");
  v.addColorStop(0.5, "rgba(10,4,30,0)");
  v.addColorStop(1, "rgba(10,4,30,.7)");
  x.fillStyle = v;
  x.fillRect(0, 0, 1024, 512);
  x.fillStyle = "rgba(0,0,0,.45)";
  for (let i = 0; i < 1024; i += 6) x.fillRect(i, 0, 2, 512);
  for (let j = 0; j < 512; j += 6) x.fillRect(0, j, 1024, 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** Névoa roxa e magenta no horizonte: um cilindro aditivo bem longe, com degradê de baixo (forte) para cima (some). */
export function horizonteNeon(centro: THREE.Vector3) {
  const c = document.createElement("canvas");
  c.width = 4;
  c.height = 256;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(0.55, "rgba(120,40,200,.35)");
  g.addColorStop(0.85, "rgba(255,60,190,.85)");
  g.addColorStop(1, "rgba(255,110,170,1)");
  x.fillStyle = g;
  x.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const geo = new THREE.CylinderGeometry(3600, 3600, 900, 64, 1, true);
  geo.translate(0, 330, 0);
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide, fog: false }));
  m.position.set(centro.x, 0, centro.z);
  m.name = "neon_horizonte";
  m.frustumCulled = false;
  m.userData.semSombra = true;
  return m;
}

let texPulso: THREE.CanvasTexture | null = null;
/** Textura do pulso de luz que percorre a pista: cabeça forte e rastro que some, repetida na volta. */
export function texturaPulso() {
  if (texPulso) return texPulso;
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 4;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 512, 0);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(0.62, "rgba(0,0,0,0)");
  g.addColorStop(0.9, "rgba(255,255,255,.55)");
  g.addColorStop(0.985, "rgba(255,255,255,1)");
  g.addColorStop(1, "rgba(0,0,0,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 512, 4);
  texPulso = new THREE.CanvasTexture(c);
  texPulso.wrapS = THREE.RepeatWrapping;
  return texPulso;
}
