// Cenário do circuito em volta do traçado real (low-poly): autódromo DENTRO DA CIDADE (decisão do Felipe, 2026-11-04): prédios
// e ruas em volta, muros e alambrados ao longo da pista, arquibancadas com torcida, boxes e paddock, poucas árvores só no miolo.
// Só aparência: o traçado e as distâncias continuam os reais. Ligado por criarCircuito(nome, { cenario: true }).
// Nada aqui muda por quadro: tudo é fixo na criação.
import * as THREE from "three";
import { seed } from "./mundo";
import { texturaLogo } from "./logo_canal";

const mat = (cor: string, o: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.9, flatShading: true, ...o });
const fora = <T extends THREE.Object3D>(o: T) => {
  o.traverse((x) => (x.userData.foraDoEnquadro = true));
  return o;
};
const caixa = (l: number, a: number, p: number, m: THREE.Material, x = 0, y = 0, z = 0) => {
  const o = new THREE.Mesh(new THREE.BoxGeometry(l, a, p), m);
  o.position.set(x, y, z);
  return o;
};

/** Distância aproximada de (x, z) ao traçado, usando um ponto a cada 8. */
const distanciaAoTracado = (pts: THREE.Vector3[]) => {
  const amostra = pts.filter((_, i) => i % 8 === 0);
  return (x: number, z: number) => {
    let m = Infinity;
    for (const p of amostra) m = Math.min(m, (p.x - x) ** 2 + (p.z - z) ** 2);
    return Math.sqrt(m);
  };
};

/** O ponto está dentro do contorno da pista? */
const dentroDoTracado = (pts: THREE.Vector3[]) => {
  const c = pts.filter((_, i) => i % 8 === 0);
  return (x: number, z: number) => {
    let d = false;
    for (let i = 0, j = c.length - 1; i < c.length; j = i++) {
      if (c[i].z > z !== c[j].z > z && x < ((c[j].x - c[i].x) * (z - c[i].z)) / (c[j].z - c[i].z) + c[i].x) d = !d;
    }
    return d;
  };
};

/** Lugar `dist` metros ao lado do traçado na fração f (dist positiva = à direita do sentido da corrida). */
export function aoLado(pts: THREE.Vector3[], f: number, dist: number) {
  const N = pts.length;
  const i = Math.floor((((f % 1) + 1) % 1) * N);
  const a = pts[i];
  const t = pts[(i + 4) % N].clone().sub(a).normalize();
  return { x: a.x - t.z * dist, z: a.z + t.x * dist };
}

type Local = { x: number; z: number; r: number };
const LIMITE_AUTODROMO = 105; // metros além da pista onde começa a cidade

// ---- chão: grama no autódromo, cidade em volta, morros só bem longe
function relevo(pts: THREE.Vector3[], altura: (x: number, z: number) => number, ehCidade: (x: number, z: number) => boolean, coresRua?: string[]) {
  const geo = new THREE.PlaneGeometry(9000, 9000, 180, 180).toNonIndexed();
  geo.rotateX(-Math.PI / 2);
  const pos = geo.getAttribute("position") as THREE.BufferAttribute;
  const cores: number[] = [];
  const grama = ["#6fae4b", "#64a345", "#5c9c42"].map((c) => new THREE.Color(c));
  const rua = (coresRua ?? ["#8f8d88", "#9a9892", "#85837f"]).map((c) => new THREE.Color(c));
  for (let i = 0; i < pos.count; i += 3) {
    let cx = 0, cz = 0;
    for (let j = 0; j < 3; j++) {
      const x = pos.getX(i + j), z = pos.getZ(i + j);
      pos.setY(i + j, altura(x, z));
      cx += x / 3;
      cz += z / 3;
    }
    const n = Math.floor(seed(i + 17) * 3);
    const c = ehCidade(cx, cz) ? rua[Math.floor(seed(i + 17) * rua.length)] : grama[n];
    for (let j = 0; j < 3; j++) cores.push(c.r, c.g, c.b);
  }
  geo.setAttribute("color", new THREE.Float32BufferAttribute(cores, 3));
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true }));
  m.receiveShadow = true;
  return m;
}

// ---- cidade: quarteirões em grade, muitos prédios baixos e torres espalhadas (instanciados)
let texJanelas: THREE.CanvasTexture | null = null;
function janelas() {
  if (texJanelas) return texJanelas;
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = "#ffffff";
  x.fillRect(0, 0, 64, 128);
  for (let l = 0; l < 8; l++) for (let k = 0; k < 4; k++) {
    x.fillStyle = seed(l * 7 + k * 31) > 0.72 ? "#8b98a8" : "#46505e";
    x.fillRect(5 + k * 15, 5 + l * 15.6, 9, 9);
  }
  texJanelas = new THREE.CanvasTexture(c);
  texJanelas.wrapS = texJanelas.wrapT = THREE.RepeatWrapping;
  texJanelas.colorSpace = THREE.SRGBColorSpace;
  texJanelas.anisotropy = 16; // janelas de longe com a câmera girando cintilavam (2026-11-12)
  return texJanelas;
}

function cidade(altura: (x: number, z: number) => number, ehCidade: (x: number, z: number) => boolean, livre: (x: number, z: number) => boolean, centro: THREE.Vector3) {
  const PASSO = 48;
  const lugares: { x: number; z: number; l: number; p: number; h: number; c: THREE.Color }[] = [];
  const tons = ["#d9d3c4", "#c9c2b2", "#e4e0d6", "#b8b3a8", "#c98f6b", "#a9b4bd", "#d6c7a8", "#9aa3a8"].map((c) => new THREE.Color(c));
  for (let a = -70; a <= 70; a++) for (let b = -70; b <= 70; b++) {
    if (a % 6 === 0 || b % 6 === 0) continue; // avenidas
    const x = centro.x + a * PASSO, z = centro.z + b * PASSO;
    const R = Math.hypot(x - centro.x, z - centro.z);
    const s = a * 211 + b * 89;
    if (R > 3300 || !ehCidade(x, z) || !livre(x, z) || seed(s) > 0.86) continue;
    const r = seed(s + 1);
    const h = r > 0.965 ? 62 + seed(s + 2) * 60 : r > 0.84 ? 24 + seed(s + 2) * 30 : 6 + seed(s + 2) * 12;
    lugares.push({ x: x + (seed(s + 3) - 0.5) * 8, z: z + (seed(s + 4) - 0.5) * 8, l: 20 + seed(s + 5) * 16, p: 20 + seed(s + 6) * 16, h, c: tons[Math.floor(seed(s + 7) * tons.length) % tons.length] });
  }
  const lado = new THREE.MeshStandardMaterial({ map: janelas(), roughness: 0.9 });
  const topo = new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 1 });
  const m = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), [lado, lado, topo, topo, lado, lado], lugares.length);
  const a = new THREE.Object3D();
  lugares.forEach((q, i) => {
    a.position.set(q.x, altura(q.x, q.z) + q.h / 2, q.z);
    a.scale.set(q.l, q.h, q.p);
    a.updateMatrix();
    m.setMatrixAt(i, a.matrix);
    m.setColorAt(i, q.c);
  });
  return m;
}

// ---- muro ao longo do traçado: faixa vertical; `d(i)` = distância lateral (positiva = direita), `cor(i)` null = sem muro ali
function muro(pts: THREE.Vector3[], d: (i: number) => number, y0: number, y1: number, cor: (i: number) => THREE.Color | null, material?: THREE.Material) {
  const N = pts.length;
  const pos: number[] = [], cores: number[] = [], ind: number[] = [];
  const lado = (i: number) => {
    const a = pts[i % N], t = pts[(i + 1) % N].clone().sub(a).normalize(), dd = d(i % N);
    return [a.x - t.z * dd, a.z + t.x * dd];
  };
  for (let i = 0; i < N; i++) {
    const c = cor(i);
    if (!c) continue;
    const [ax, az] = lado(i), [bx, bz] = lado(i + 1);
    const v = pos.length / 3;
    pos.push(ax, y0, az, ax, y1, az, bx, y0, bz, bx, y1, bz);
    for (let k = 0; k < 4; k++) cores.push(c.r, c.g, c.b);
    ind.push(v, v + 1, v + 2, v + 1, v + 3, v + 2);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(cores, 3));
  geo.setIndex(ind);
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, material ?? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide }));
}

/** Muros de proteção dos dois lados, placas coloridas sem marca, alambrado por cima e o muro externo do autódromo. */
function muros(pts: THREE.Vector3[], bordas: { fora: (i: number) => number; dentro: (i: number) => number }, distancia: (x: number, z: number) => number, noMiolo: (x: number, z: number) => boolean, o: { externo?: boolean; noite?: boolean } = {}) {
  const g = new THREE.Group();
  const N = pts.length;
  const placas = ["#1f5fd1", "#f4f4f2", "#d92b2b", "#169c46", "#ffd21f", "#22262e", "#f4f4f2"].map((c) => new THREE.Color(c));
  const concreto = new THREE.Color("#c9c9c4");
  const livre = (i: number, dd: number) => {
    const a = pts[i], t = pts[(i + 1) % N].clone().sub(a).normalize();
    return distancia(a.x - t.z * dd, a.z + t.x * dd) > Math.abs(dd) * 0.72; // não atravessa outro trecho da pista
  };
  const fora = (i: number) => bordas.fora(i) + 3, dentro = (i: number) => -(bordas.dentro(i) + 3);
  for (const d of [fora, dentro]) {
    g.add(muro(pts, d, 0, 1.3, (i) => (livre(i, d(i)) ? concreto : null)));
    g.add(muro(pts, d, 1.3, 2.5, (i) => (livre(i, d(i)) ? placas[Math.floor(i / 7) % placas.length] : null)));
    g.add(muro(pts, d, 2.5, 6.5, (i) => (livre(i, d(i)) ? new THREE.Color("#aab2ba") : null),
      new THREE.MeshStandardMaterial({ vertexColors: true, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false })));
    // à noite: faixa de luz no alto do muro (a pista de rua iluminada vista de longe)
    if (o.noite) g.add(muro(pts, d, 6.3, 7.2, (i) => (livre(i, d(i)) ? new THREE.Color("#fff1d6") : null), new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })));
  }
  if (o.externo === false) return g;
  const externo = () => LIMITE_AUTODROMO - 8;
  const externoLivre = (i: number) => {
    const a = pts[i], t = pts[(i + 1) % N].clone().sub(a).normalize(), dd = externo();
    return livre(i, dd) && !noMiolo(a.x - t.z * dd, a.z + t.x * dd); // o muro externo nunca entra no miolo do autódromo
  };
  g.add(muro(pts, externo, 0, 6, (i) => (externoLivre(i) ? new THREE.Color("#b7b2a6") : null)));
  return g;
}

// ---- árvores: poucas, só no miolo do autódromo
function arvores(pts: THREE.Vector3[], reservado: (x: number, z: number) => boolean, dentro: (x: number, z: number) => boolean) {
  const dist = distanciaAoTracado(pts);
  const lugares: [number, number, number][] = [];
  const area = new THREE.Box3().setFromPoints(pts);
  for (let i = 0; lugares.length < 130 && i < 6000; i++) {
    const g = Math.floor(i / 6);
    const x = area.min.x + seed(g * 3 + 1) * (area.max.x - area.min.x) + (seed(i * 2 + 11) - 0.5) * 50;
    const z = area.min.z + seed(g * 3 + 2) * (area.max.z - area.min.z) + (seed(i * 2 + 12) - 0.5) * 50;
    if (!dentro(x, z) || dist(x, z) < 72 || reservado(x, z)) continue;
    lugares.push([x, z, 12 + seed(i + 5) * 10]);
  }
  const copa = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), mat("#ffffff"), lugares.length);
  const tronco = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.16, 0.22, 1, 5), mat("#6b4a2e"), lugares.length);
  const a = new THREE.Object3D();
  const verdes = ["#2f7d3a", "#3b8f3f", "#28703a", "#469a44"].map((c) => new THREE.Color(c));
  lugares.forEach(([x, z, h], i) => {
    a.position.set(x, h * 0.28, z);
    a.scale.set(h * 0.2, h * 0.56, h * 0.2);
    a.rotation.y = 0;
    a.updateMatrix();
    tronco.setMatrixAt(i, a.matrix);
    a.position.set(x, h * 0.72, z);
    a.scale.setScalar(h * 0.42);
    a.rotation.y = seed(i) * 6;
    a.updateMatrix();
    copa.setMatrixAt(i, a.matrix);
    copa.setColorAt(i, verdes[i % verdes.length]);
  });
  copa.castShadow = true;
  return new THREE.Group().add(tronco, copa);
}

// ---- torcida: textura de pontinhos coloridos (fixa)
let texTorcida: THREE.CanvasTexture | null = null;
function torcida() {
  if (texTorcida) return texTorcida;
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = "#3d4048";
  x.fillRect(0, 0, 512, 128);
  const cores = ["#ffd21f", "#169c46", "#f4f1ea", "#d92b2b", "#1f5fd1", "#ff8a1f", "#22262e", "#ffd21f", "#169c46"];
  for (let i = 0; i < 2600; i++) {
    x.fillStyle = cores[Math.floor(seed(i + 900) * cores.length) % cores.length];
    x.fillRect(seed(i + 1) * 512, seed(i + 3000) * 128, 4, 5);
  }
  texTorcida = new THREE.CanvasTexture(c);
  texTorcida.wrapS = THREE.RepeatWrapping;
  texTorcida.colorSpace = THREE.SRGBColorSpace;
  return texTorcida;
}

/** Um lance de arquibancada de `largura` metros: rampa com torcida, cobertura opcional, pilares. Frente para +z local. */
function lance(largura: number, coberta: boolean) {
  const g = new THREE.Group();
  const prof = 26, alto = 15;
  const tx = torcida().clone();
  tx.repeat.set(largura / 40, 1);
  tx.needsUpdate = true;
  const rampa = new THREE.Mesh(new THREE.PlaneGeometry(largura, Math.hypot(prof, alto)), new THREE.MeshStandardMaterial({ map: tx, roughness: 1, side: THREE.DoubleSide }));
  rampa.position.set(0, alto / 2 + 3, 0);
  rampa.rotation.x = -Math.PI / 2 + Math.atan2(alto, prof);
  g.add(rampa);
  const corpo = mat("#a9adb5");
  g.add(caixa(largura, alto + 3, 1.5, corpo, 0, (alto + 3) / 2, -prof / 2));
  for (const lado of [-1, 1]) g.add(caixa(1, alto + 3, prof, corpo, (lado * largura) / 2, (alto + 3) / 2, 0));
  for (let x = -largura / 2 + 4; x < largura / 2; x += 9) g.add(caixa(1, 3.2, 1, corpo, x, 1.6, prof / 2 - 1));
  if (coberta) {
    const teto = caixa(largura + 3, 1.1, prof + 7, mat("#d3d6db"), 0, alto + 11, 1);
    teto.rotation.x = 0.07;
    g.add(teto);
    for (let x = -largura / 2 + 2; x <= largura / 2; x += largura / 3) g.add(caixa(0.9, 11, 0.9, corpo, x, alto + 5.5, -prof / 2));
  }
  return g;
}

/** Arquibancadas seguindo o traçado de f0 a f1, a `dist` metros (com sinal), de frente para a pista. */
function arquibancadas(pts: THREE.Vector3[], f0: number, f1: number, dist: number, coberta: boolean, comprimento: number) {
  const g = new THREE.Group();
  const passos = Math.max(1, Math.round(((f1 - f0) * comprimento) / 64));
  for (let k = 0; k < passos; k++) {
    const f = f0 + ((k + 0.5) / passos) * (f1 - f0);
    const q = aoLado(pts, f, dist);
    const a = aoLado(pts, f, 0);
    const l = lance(58, coberta);
    l.position.set(q.x, 0, q.z);
    l.rotation.y = Math.atan2(a.x - q.x, a.z - q.z); // +z local olha para a pista
    g.add(l);
  }
  return g;
}

// ---- boxes e paddock: prédio comprido ao lado da pista, garagens coloridas, torre de controle, motorhomes e caminhões
function boxes(pts: THREE.Vector3[], f0: number, f1: number, dist: number) {
  const g = new THREE.Group();
  const a = aoLado(pts, f0, dist), b = aoLado(pts, f1, dist);
  const comp = Math.hypot(b.x - a.x, b.z - a.z);
  const meio = aoLado(pts, (f0 + f1) / 2, dist), pista = aoLado(pts, (f0 + f1) / 2, 0);
  g.position.set((a.x + b.x) / 2, 0, (a.z + b.z) / 2);
  g.rotation.y = Math.atan2(-(b.z - a.z), b.x - a.x); // x local ao longo da reta
  // +z local para longe da pista
  const longe = new THREE.Vector3(Math.sin(g.rotation.y), 0, Math.cos(g.rotation.y));
  const sinal = longe.dot(new THREE.Vector3(meio.x - pista.x, 0, meio.z - pista.z)) > 0 ? 1 : -1;
  const coresEq = ["#d11f4e", "#d9571a", "#0f8f80", "#2547c4", "#7a35c0", "#e6a500", "#3a3e45", "#23262f", "#c9a54a", "#178a4a", "#e8e8ee"];
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(comp + 40, 95), new THREE.MeshStandardMaterial({ color: "#55585f", roughness: 1 }));
  piso.rotation.x = -Math.PI / 2;
  piso.position.set(0, 0.004, sinal * 47);
  g.add(piso);
  g.add(caixa(comp, 11, 24, mat("#c6c9cf"), 0, 5.5, sinal * 12), caixa(comp + 3, 1, 28, mat("#8d9097"), 0, 11.5, sinal * 12));
  const n = Math.floor(comp / 13);
  for (let i = 0; i < n; i++) g.add(caixa(10, 5.5, 0.5, mat(coresEq[Math.floor((i / n) * coresEq.length)]), -comp / 2 + (i + 0.5) * (comp / n), 2.75, sinal * -0.2));
  g.add(caixa(14, 12, 14, mat("#8d9097"), 0, 18, sinal * 12), caixa(18, 6, 18, mat("#3a4a5e", { roughness: 0.3 }), 0, 27, sinal * 12));
  for (let i = 0; i < 10; i++) g.add(caixa(46, 9, 15, mat(i % 3 === 2 ? "#b5b8bf" : "#9ea2aa"), -comp / 2 + 40 + (i % 5) * ((comp - 80) / 4), 4.5, sinal * (i < 5 ? 46 : 74)));
  for (let i = 0; i < 12; i++) {
    const c = caixa(14, 3.6, 3.2, mat(coresEq[i % coresEq.length]), -comp / 2 + 24 + seed(i + 70) * (comp - 48), 1.8, sinal * (34 + seed(i + 90) * 52));
    c.rotation.y = i % 2 ? 0 : Math.PI / 2;
    g.add(c);
  }
  return g;
}

function lago(cx: number, cz: number, r: number) {
  const s = new THREE.Shape();
  for (let i = 0; i <= 36; i++) {
    const ang = (i / 36) * Math.PI * 2;
    const raio = r * (0.72 + 0.34 * seed(3 + (i % 36)));
    if (i === 0) s.moveTo(Math.cos(ang) * raio * 1.5, Math.sin(ang) * raio);
    else s.lineTo(Math.cos(ang) * raio * 1.5, Math.sin(ang) * raio);
  }
  const m = new THREE.Mesh(new THREE.ShapeGeometry(s), new THREE.MeshStandardMaterial({ color: "#3f7fb5", roughness: 0.35, metalness: 0.1, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2;
  m.position.set(cx, 0.35, cz);
  return m;
}

// ---- circuito de rua (Las Vegas): prédios de verdade (contorno e altura do OpenStreetMap), água, pit lane e marcos
/** Dados de cidade real no quadro do circuito: [x leste, n norte] em metros (z do mundo = -n). */
export type CidadeReal = {
  predios: [number, number[]][]; // [altura, contorno achatado x0, n0, x1, n1, ...]
  agua: number[][];
  pit?: number[][];
  marcos: Record<string, { nome: string; xn: number[]; eixo?: number[]; extensao?: number[] }>;
};

let texJanelasNoite: THREE.CanvasTexture | null = null;
/** Fachada à noite: escura, com janelas acesas (quentes e frias), para o mapa de brilho. */
function janelasNoite() {
  if (texJanelasNoite) return texJanelasNoite;
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = "#000000";
  x.fillRect(0, 0, 64, 128);
  for (let l = 0; l < 8; l++) for (let k = 0; k < 4; k++) {
    const r = seed(l * 13 + k * 29 + 5);
    if (r < 0.35) continue;
    x.fillStyle = r > 0.85 ? "#bcd6ff" : r > 0.6 ? "#ffd38a" : "#ffb45c";
    x.fillRect(5 + k * 15, 5 + l * 15.6, 9, 9);
  }
  texJanelasNoite = new THREE.CanvasTexture(c);
  texJanelasNoite.wrapS = texJanelasNoite.wrapT = THREE.RepeatWrapping;
  texJanelasNoite.colorSpace = THREE.SRGBColorSpace;
  texJanelasNoite.anisotropy = 16;
  return texJanelasNoite;
}

/** Junta as faces de vários ExtrudeGeometry em duas malhas (laterais com janelas, topos lisos), com cor por prédio. */
function prediosReais(lista: CidadeReal["predios"], noite: boolean) {
  const lados: number[][] = [[], [], [], []], topos: number[][] = [[], [], []]; // pos, normal, uv, cor
  const tons = ["#e9e4d8", "#ddd6c6", "#f1eee6", "#d4cdbd", "#e2d3b4", "#cfd6dc", "#e8dcc4"].map((c) => new THREE.Color(c));
  const tonsNoite = ["#3a3f4c", "#454a58", "#30343f", "#4a4553"].map((c) => new THREE.Color(c));
  lista.forEach(([h, plano], n) => {
    const pts: THREE.Vector2[] = [];
    for (let i = 0; i < plano.length; i += 2) pts.push(new THREE.Vector2(plano[i], plano[i + 1]));
    if (THREE.ShapeUtils.isClockWise(pts)) pts.reverse();
    const geo = new THREE.ExtrudeGeometry(new THREE.Shape(pts), { depth: h, bevelEnabled: false });
    geo.rotateX(-Math.PI / 2); // forma em x/n → chão em x/-z, altura para cima
    const pos = geo.getAttribute("position"), nor = geo.getAttribute("normal"), uv = geo.getAttribute("uv");
    const cor = (noite ? tonsNoite : tons)[Math.floor(seed(n * 7 + 3) * 97) % (noite ? tonsNoite.length : tons.length)];
    for (const gr of geo.groups) {
      const alvo = gr.materialIndex === 1 ? lados : topos;
      for (let i = gr.start; i < gr.start + gr.count; i++) {
        alvo[0].push(pos.getX(i), pos.getY(i), pos.getZ(i));
        alvo[1].push(nor.getX(i), nor.getY(i), nor.getZ(i));
        if (gr.materialIndex === 1) {
          alvo[2].push(uv.getX(i) / 14, uv.getY(i) / 26); // ~3,5 m por janela
          alvo[3].push(cor.r, cor.g, cor.b);
        } else alvo[2].push(cor.r, cor.g, cor.b);
      }
    }
    geo.dispose();
  });
  const malha = (dados: number[][], comUv: boolean, m: THREE.Material) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(dados[0], 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(dados[1], 3));
    if (comUv) g.setAttribute("uv", new THREE.Float32BufferAttribute(dados[2], 2));
    g.setAttribute("color", new THREE.Float32BufferAttribute(comUv ? dados[3] : dados[2], 3));
    const o = new THREE.Mesh(g, m);
    o.castShadow = o.receiveShadow = true;
    return o;
  };
  const lado = noite
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, emissive: "#ffffff", emissiveMap: janelasNoite(), emissiveIntensity: 1.1 })
    : new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, map: janelas() });
  const topo = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, color: noite ? "#7d8294" : "#ffffff" });
  return new THREE.Group().add(malha(lados, true, lado), malha(topos, false, topo));
}

/** Espelhos d'água (lago do Bellagio etc.) no chão. */
function aguaReal(lista: number[][], noite: boolean) {
  const formas = lista.map((p) => {
    const v: THREE.Vector2[] = [];
    for (let i = 0; i < p.length; i += 2) v.push(new THREE.Vector2(p[i], p[i + 1]));
    return new THREE.Shape(v);
  });
  const m = new THREE.Mesh(new THREE.ShapeGeometry(formas), new THREE.MeshStandardMaterial({ color: noite ? "#1d5d8f" : "#4f9fd6", roughness: 0.3, metalness: 0.1, emissive: noite ? "#1b6fb0" : "#000000", emissiveIntensity: noite ? 0.5 : 0, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.3;
  return m;
}

/** Pit lane (OpenStreetMap) como faixa de asfalto ao lado da reta. */
function pitLane(pts: number[][]) {
  const v = pts.map(([x, n]) => new THREE.Vector3(x, 0.015, -n));
  const curva = new THREE.CatmullRomCurve3(v, false, "centripetal");
  const N = 120, pos: number[] = [], ind: number[] = [];
  for (let i = 0; i <= N; i++) {
    const p = curva.getPointAt(i / N), t = curva.getTangentAt(i / N);
    for (const s of [-6, 6]) pos.push(p.x - t.z * s, 0.015, p.z + t.x * s);
    if (i < N) ind.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  return new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: "#5a5f69", roughness: 0.9, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }));
}

/** Vida de Las Vegas ao longo da pista (pedido do Felipe, 2026-11-12: "é Las Vegas!"): postes de luz dos dois lados,
 *  palmeiras e letreiros de neon (painéis coloridos sem marca nem texto) em postes, fora dos prédios reais. De dia o
 *  neon e as lâmpadas brilham pouco; à noite, forte. Instanciado (poucas chamadas de desenho). */
function vidaDeVegas(pts: THREE.Vector3[], noite: boolean, ocupado: (x: number, z: number) => boolean) {
  const g = new THREE.Group();
  const N = pts.length;
  const lugares = (passo: number, dist: number, fase = 0) => {
    const r: { x: number; z: number; giro: number }[] = [];
    for (let f = fase; f < 1; f += passo / 6201) {
      const p = aoLado(pts, f, dist);
      if (ocupado(p.x, p.z)) continue;
      const i = Math.floor(f * N), a = pts[i], b = pts[(i + 4) % N];
      r.push({ ...p, giro: Math.atan2(b.x - a.x, b.z - a.z) });
    }
    return r;
  };
  const inst = (geo: THREE.BufferGeometry, m: THREE.Material, lista: { x: number; y: number; z: number; giro?: number; e?: number; cor?: string }[]) => {
    const im = new THREE.InstancedMesh(geo, m, Math.max(1, lista.length));
    const o = new THREE.Object3D();
    const c = new THREE.Color();
    lista.forEach((q, k) => {
      o.position.set(q.x, q.y, q.z);
      o.rotation.set(0, q.giro ?? 0, 0);
      o.scale.setScalar(q.e ?? 1);
      o.updateMatrix();
      im.setMatrixAt(k, o.matrix);
      if (q.cor) im.setColorAt(k, c.set(q.cor));
    });
    im.count = lista.length;
    im.castShadow = true;
    return im;
  };
  // postes: dos dois lados, a cada ~45 m, a 11 m do eixo
  const postes = [...lugares(45, 11), ...lugares(45, -11, 0.003)];
  g.add(inst(new THREE.CylinderGeometry(0.18, 0.25, 11, 6), mat("#5d636e", { flatShading: false, metalness: 0.5, roughness: 0.4 }), postes.map((p) => ({ ...p, y: 5.5 }))));
  g.add(inst(new THREE.BoxGeometry(0.9, 0.35, 2.6), new THREE.MeshStandardMaterial({ color: "#fff4d6", emissive: "#ffe2a8", emissiveIntensity: noite ? 3 : 0.9 }), postes.map((p) => ({ ...p, y: 11.1 }))));
  // palmeiras: tronco e copa (folhas em estrela), a ~16 m do eixo
  const palmas = [...lugares(70, 16, 0.006), ...lugares(70, -16, 0.012)];
  g.add(inst(new THREE.CylinderGeometry(0.35, 0.55, 12, 6), mat("#8a6a45"), palmas.map((p) => ({ ...p, y: 6 }))));
  const copa = new THREE.ConeGeometry(4.2, 2.2, 7);
  copa.translate(0, -0.4, 0);
  g.add(inst(copa, mat(noite ? "#2f5f3a" : "#3f9a4a"), palmas.map((p) => ({ ...p, y: 12.4 }))));
  // letreiros de neon: painéis coloridos em dois postes, a cada ~130 m, alternando os lados
  const neon = ["#ff2bd6", "#22e5ff", "#ffd400", "#ff5a2b", "#8a5bff", "#2bff88"];
  const placas = [...lugares(260, 22, 0.02), ...lugares(260, -22, 0.041)].map((p, k) => ({ ...p, cor: neon[k % neon.length] }));
  // painel sem luz própria do sol (MeshBasic): a cor da instância aparece pura, como LED/neon, de dia e de noite
  // painel aceso visto dos dois lados; a moldura são 4 barras EM VOLTA dele (antes era uma caixa atrás/dentro do painel e
  // as faces paralelas brigavam na profundidade: o painel piscava entre a cor e o preto, 2026-11-12)
  g.add(inst(new THREE.BoxGeometry(14, 5, 0.3), new THREE.MeshBasicMaterial({ color: "#ffffff" }), placas.map((p) => ({ ...p, y: 15 }))));
  const moldura = mat("#15161b");
  for (const s of [-1, 1]) {
    g.add(inst(new THREE.BoxGeometry(14.8, 0.4, 0.4).translate(0, s * 2.7, 0), moldura, placas.map((p) => ({ ...p, y: 15 }))));
    g.add(inst(new THREE.BoxGeometry(0.4, 5, 0.4).translate(s * 7.2, 0, 0), moldura, placas.map((p) => ({ ...p, y: 15 }))));
  }
  const pes = placas.flatMap((p) => [-5, 5].map((d) => ({ x: p.x + Math.cos(p.giro) * d, y: 6.3, z: p.z - Math.sin(p.giro) * d })));
  g.add(inst(new THREE.CylinderGeometry(0.3, 0.3, 12.6, 6), mat("#3a3f48", { flatShading: false, metalness: 0.5 }), pes));
  return g;
}

/** Logo do canal (redondo) nas quatro faces da Sphere: calota com projeção plana, sem distorcer de frente. */
function logoNaEsfera(r: number, cap = 0.66) {
  const g = new THREE.Group();
  const tex = texturaLogo();
  // disco com fundo transparente: só o círculo do logo aparece sobre a esfera (nada dos cantos do JPEG)
  const m = new THREE.MeshStandardMaterial({ map: tex, emissive: "#ffffff", emissiveMap: tex, emissiveIntensity: 0.85, roughness: 0.45, transparent: true, alphaTest: 0.04, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  const geo = new THREE.SphereGeometry(r + 0.4, 64, 48, Math.PI / 2 - cap, cap * 2, Math.PI / 2 - cap, cap * 2);
  const pos = geo.getAttribute("position"), uv = geo.getAttribute("uv");
  const meia = (r + 0.4) * Math.sin(cap);
  for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5 + pos.getX(i) / (2 * meia), 0.5 + pos.getY(i) / (2 * meia));
  uv.needsUpdate = true;
  for (let k = 0; k < 4; k++) {
    const c = new THREE.Mesh(geo, m);
    c.rotation.y = (k * Math.PI) / 2;
    g.add(c);
  }
  return g;
}

/** Marcos de Las Vegas em volume simples, nas posições reais (OSM): a Sphere (esfera de 157 m de diâmetro e 112 m de
 *  altura), a roda-gigante High Roller (167 m) e a réplica da Torre Eiffel do Paris (165 m). Sem marcas nem telões. */
function marcosVegas(m: CidadeReal["marcos"], noite: boolean) {
  const g = new THREE.Group();
  const em = (cor: string, forca: number) => (noite ? { emissive: cor, emissiveIntensity: forca } : {});
  if (m.sphere) {
    const [x, n] = m.sphere.xn;
    const r = 78.5;
    // tela de LED escura com o logo do canal (redondo como ela) nas quatro faces (pedido do Felipe, 2026-11-12)
    const esfera = new THREE.Mesh(new THREE.SphereGeometry(r, 48, 32), mat("#101218", { flatShading: false, roughness: 0.4, metalness: 0.2, emissive: "#0b1530", emissiveIntensity: noite ? 0.8 : 0.3 }));
    esfera.position.set(x, 112 - r, -n);
    esfera.castShadow = true;
    g.add(esfera);
    const logo = logoNaEsfera(r);
    logo.position.copy(esfera.position);
    g.add(logo);
    const base = new THREE.Mesh(new THREE.CylinderGeometry(52, 58, 8, 40), mat("#8e939c"));
    base.position.set(x, 4, -n);
    g.add(base);
  }
  if (m.high_roller) {
    const [x, n] = m.high_roller.xn;
    const e = m.high_roller.eixo ?? [1, 0];
    const roda = new THREE.Group();
    const R = 79, aco = mat("#e4e6ea", { flatShading: false, roughness: 0.4, metalness: 0.4, ...em("#b06cff", 1.2) });
    const aro = new THREE.Mesh(new THREE.TorusGeometry(R, 1.6, 8, 96), aco);
    roda.add(aro);
    const aroInt = new THREE.Mesh(new THREE.TorusGeometry(R - 7, 0.9, 6, 96), aco);
    roda.add(aroInt);
    for (let i = 0; i < 28; i++) {
      const a = (i / 28) * Math.PI * 2;
      const raio = caixa(0.5, R - 4, 0.5, mat("#c9ccd2"), Math.cos(a) * (R - 4) / 2, Math.sin(a) * (R - 4) / 2, 0);
      raio.rotation.z = a - Math.PI / 2;
      roda.add(raio);
      const cab = new THREE.Mesh(new THREE.SphereGeometry(3.2, 10, 8), mat("#f4f6f8", { flatShading: false, roughness: 0.2, ...em("#e8f0ff", 0.6) }));
      cab.position.set(Math.cos(a) * (R + 2.5), Math.sin(a) * (R + 2.5), 0);
      roda.add(cab);
    }
    roda.position.set(0, 167 - R - 3, 0);
    const pernas = new THREE.Group().add(roda);
    for (const s of [-1, 1]) {
      const perna = caixa(3, 92, 3, mat("#c9ccd2"), 0, 46, s * 14);
      perna.rotation.x = s * -0.15;
      pernas.add(perna);
    }
    pernas.position.set(x, 0, -n);
    pernas.rotation.y = Math.atan2(-e[1], e[0]); // plano da roda ao longo do eixo maior do contorno no OSM
    g.add(pernas);
  }
  if (m.eiffel) {
    const [x, n] = m.eiffel.xn;
    const ferro = mat("#b9a68a", { ...em("#ffb45c", 0.9) });
    const t = new THREE.Group();
    // quatro pés que se juntam, plataformas e a agulha: volume baixo-poli, 165 m como a réplica
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const pe = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 3.2, 62, 5), ferro);
      pe.position.set(sx * 13, 30, sz * 13);
      pe.rotation.set(sz * 0.36, 0, -sx * 0.36);
      t.add(pe);
    }
    t.add(caixa(34, 3, 34, ferro, 0, 58, 0));
    const meio = new THREE.Mesh(new THREE.CylinderGeometry(4, 11, 55, 4), ferro);
    meio.position.y = 86;
    meio.rotation.y = Math.PI / 4;
    t.add(meio, caixa(14, 2.5, 14, ferro, 0, 114, 0));
    const topo = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 4, 50, 4), ferro);
    topo.position.y = 140;
    topo.rotation.y = Math.PI / 4;
    t.add(topo);
    t.position.set(x, 0, -n);
    g.add(t);
  }
  return g;
}

export type Cenario = {
  arquibancadas: { f0: number; f1: number; coberta?: boolean; dist: number }[];
  boxes?: { f0: number; f1: number; dist: number };
  lagos?: { f: number; dist: number; r: number }[]; // os lagos ficam longe, para além da cidade
  /** circuito de rua: chão de cidade, muro colado na pista, sem grama, árvores nem muro externo de autódromo */
  rua?: boolean;
  /** prédios e marcos de verdade (OpenStreetMap) no quadro do circuito */
  real?: CidadeReal;
  /** cidade acesa (janelas, marcos e água com brilho): para o clima "noite" */
  noite?: boolean;
};

/** Veste o circuito: tudo entra marcado como fora do enquadramento (enquadrar() só olha a pista). `bordas` = até onde vão as
 *  áreas de escape em cada ponto da volta, para o muro ficar depois delas. */
export function vestirCircuito(g: THREE.Group, pts: THREE.Vector3[], comprimento: number, o: Cenario, bordas: { fora: (i: number) => number; dentro: (i: number) => number }) {
  const tudo = new THREE.Group();
  const dist = distanciaAoTracado(pts);
  const dentro = dentroDoTracado(pts);
  const meio = new THREE.Box3().setFromPoints(pts).getCenter(new THREE.Vector3());
  // o lago sai de perto da pista: empurrado para fora até ficar longe do traçado (nunca cobre o asfalto)
  const lagos: Local[] = (o.lagos ?? []).map((l) => {
    const q = aoLado(pts, l.f, l.dist);
    for (let i = 0; i < 80 && dist(q.x, q.z) < l.r * 1.7 + 260; i++) {
      const n = Math.hypot(q.x - meio.x, q.z - meio.z) || 1;
      q.x += ((q.x - meio.x) / n) * 40;
      q.z += ((q.z - meio.z) / n) * 40;
    }
    return { ...q, r: l.r };
  });
  const noLago = (x: number, z: number, folga = 1.12) => lagos.some((l) => Math.hypot((x - l.x) / 1.5, z - l.z) < l.r * folga);
  const ehCidade = (x: number, z: number) => !dentro(x, z) && dist(x, z) > LIMITE_AUTODROMO && !noLago(x, z, 1.04);
  // plano até 1,8 km do centro; morros só no horizonte
  const altura = (x: number, z: number) => {
    const longe = Math.min(1, Math.max(0, (Math.hypot(x - meio.x, z - meio.z) - 1800) / 1400));
    return -0.15 + longe * longe * (70 + Math.sin(x * 0.0021 + 1.3) * Math.cos(z * 0.0017) * 60);
  };
  if (o.rua) {
    vestirRua(tudo, pts, comprimento, o, bordas, dist, dentro, meio, altura);
    g.add(fora(tudo));
    return;
  }
  tudo.add(relevo(pts, altura, ehCidade));
  for (const l of lagos) tudo.add(lago(l.x, l.z, l.r));
  const grupo = new THREE.Group();
  for (const a of o.arquibancadas) grupo.add(arquibancadas(pts, a.f0, a.f1, a.dist, a.coberta ?? false, comprimento));
  if (o.boxes) grupo.add(boxes(pts, o.boxes.f0, o.boxes.f1, o.boxes.dist));
  tudo.add(grupo);
  grupo.updateMatrixWorld(true);
  const blocos: THREE.Box3[] = [];
  grupo.children.forEach((x) => x.children.length && blocos.push(new THREE.Box3().setFromObject(x).expandByScalar(9)));
  const reservado = (x: number, z: number) => {
    if (noLago(x, z)) return true;
    const p = new THREE.Vector3(x, 1, z);
    return blocos.some((b) => b.containsPoint(p));
  };
  tudo.add(muros(pts, bordas, dist, dentro));
  tudo.add(cidade(altura, ehCidade, (x, z) => !reservado(x, z), meio));
  tudo.add(arvores(pts, reservado, dentro));
  g.add(fora(tudo));
}

/** Circuito de rua: a cidade chega até o muro. Com `real`, prédios de verdade (OSM) perto da pista e a grade genérica só
 *  para além deles, no horizonte. */
function vestirRua(tudo: THREE.Group, pts: THREE.Vector3[], comprimento: number, o: Cenario, bordas: { fora: (i: number) => number; dentro: (i: number) => number },
  dist: (x: number, z: number) => number, dentro: (x: number, z: number) => boolean, meio: THREE.Vector3, altura: (x: number, z: number) => number) {
  const noite = o.noite ?? false;
  // dia: chão de cidade em asfalto, terreno e estacionamentos (o bege claro de antes parecia "deserto de neve", Felipe 2026-11-12)
  const solo = noite ? ["#23262e", "#272a33", "#20232a"] : ["#6e6a64", "#7b746a", "#625f5b", "#86796a", "#716d68"];
  tudo.add(relevo(pts, altura, () => true, solo));
  // contornos dos prédios reais: para não pôr arquibancada dentro de um prédio
  const caixas: { b: THREE.Box2; p: number[] }[] = (o.real?.predios ?? []).map(([, p]) => {
    const b = new THREE.Box2();
    for (let i = 0; i < p.length; i += 2) b.expandByPoint(new THREE.Vector2(p[i], -p[i + 1]));
    return { b, p };
  });
  const emPredio = (x: number, z: number, folga = 0) => caixas.some(({ b, p }) => {
    if (!b.clone().expandByScalar(folga).containsPoint(new THREE.Vector2(x, z))) return false;
    if (folga > 0) return true;
    let d = false;
    for (let i = 0, j = p.length - 2; i < p.length; j = i, i += 2) {
      const zi = -p[i + 1], zj = -p[j + 1];
      if (zi > z !== zj > z && x < ((p[j] - p[i]) * (z - zi)) / (zj - zi) + p[i]) d = !d;
    }
    return d;
  });
  const grupo = new THREE.Group();
  for (const a of o.arquibancadas) {
    const arq = arquibancadas(pts, a.f0, a.f1, a.dist, a.coberta ?? false, comprimento);
    for (const l of [...arq.children]) if (emPredio(l.position.x, l.position.z, 12)) arq.remove(l);
    grupo.add(arq);
  }
  tudo.add(grupo);
  tudo.add(muros(pts, bordas, dist, dentro, { externo: false, noite }));
  if (o.real) {
    tudo.add(prediosReais(o.real.predios, noite));
    if (o.real.agua.length) tudo.add(aguaReal(o.real.agua, noite));
    if (o.real.pit) tudo.add(pitLane(o.real.pit));
    tudo.add(marcosVegas(o.real.marcos, noite));
    tudo.add(vidaDeVegas(pts, noite, (x, z) => emPredio(x, z, 4)));
  }
  // horizonte: grade genérica só fora da área com prédios reais
  const area = new THREE.Box2();
  for (const { b } of caixas) area.union(b);
  if (caixas.length) area.expandByScalar(120);
  const longe = (x: number, z: number) => !caixas.length || !area.containsPoint(new THREE.Vector2(x, z));
  const cid = cidade(altura, (x, z) => dist(x, z) > 160 && longe(x, z), () => true, meio);
  if (noite) {
    const m = cid.material as THREE.MeshStandardMaterial[];
    const lado = new THREE.MeshStandardMaterial({ color: "#3a3f4c", roughness: 0.8, emissive: "#ffffff", emissiveMap: janelasNoite(), emissiveIntensity: 0.8 });
    cid.material = [lado, lado, m[2], m[3], lado, lado];
    (m[2] as THREE.MeshStandardMaterial).color.set("#5d6170");
  }
  tudo.add(cid);
}
