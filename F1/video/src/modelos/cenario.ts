// Cenário do circuito em volta do traçado real (low-poly): relevo, árvores, lago, arquibancadas com torcida, prédio dos
// boxes e paddock. Só aparência: o traçado e as distâncias continuam os reais. Ligado por criarCircuito(nome, { cenario: true }).
// Nada aqui muda por quadro: tudo é fixo na criação.
import * as THREE from "three";
import { seed } from "./mundo";

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

/** Lugar `dist` metros ao lado do traçado na fração f (dist positiva = à direita do sentido da corrida). */
export function aoLado(pts: THREE.Vector3[], f: number, dist: number) {
  const N = pts.length;
  const i = Math.floor((((f % 1) + 1) % 1) * N);
  const a = pts[i];
  const t = pts[(i + 4) % N].clone().sub(a).normalize();
  return { x: a.x - t.z * dist, z: a.z + t.x * dist };
}

// ---- relevo: grama em facetas, plana perto da pista, com morros suaves longe dela
function relevo(pts: THREE.Vector3[], lagos: { x: number; z: number; r: number }[]) {
  const geo = new THREE.PlaneGeometry(6000, 6000, 150, 150).toNonIndexed();
  geo.rotateX(-Math.PI / 2);
  const pos = geo.getAttribute("position") as THREE.BufferAttribute;
  const dist = distanciaAoTracado(pts);
  const onda = (x: number, z: number) => Math.sin(x * 0.0041 + 1.3) * Math.cos(z * 0.0037) + 0.6 * Math.sin(x * 0.011 - z * 0.009) + 0.3 * Math.cos(x * 0.023 + z * 0.019);
  const cores: number[] = [];
  const tons = ["#6fae4b", "#5c9c42", "#4b8a3a"].map((c) => new THREE.Color(c));
  for (let i = 0; i < pos.count; i += 3) {
    let soma = 0;
    for (let j = 0; j < 3; j++) {
      const x = pos.getX(i + j), z = pos.getZ(i + j);
      const dLago = Math.min(Infinity, ...lagos.map((l) => Math.hypot((x - l.x) / 1.5, z - l.z) - l.r * 1.1)); // o lago fica em terreno plano
      const longe = Math.min(1, Math.max(0, Math.min(dist(x, z) - 70, dLago) / 260));
      pos.setY(i + j, -0.15 + longe * longe * (14 + onda(x, z) * 16));
      soma += onda(x, z);
    }
    const c = tons[soma > 1 ? 0 : soma > -1 ? 1 : 2];
    for (let j = 0; j < 3; j++) cores.push(c.r, c.g, c.b);
  }
  geo.setAttribute("color", new THREE.Float32BufferAttribute(cores, 3));
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true }));
  m.receiveShadow = true;
  return m;
}

// ---- árvores: copas em facetas, em grupos (instanciadas: milhares sem pesar)
function arvores(pts: THREE.Vector3[], reservado: (x: number, z: number) => boolean) {
  const dist = distanciaAoTracado(pts);
  const lugares: [number, number, number][] = [];
  const area = new THREE.Box3().setFromPoints(pts);
  for (let i = 0; lugares.length < 1500 && i < 14000; i++) {
    const g = Math.floor(i / 9);
    const cx = area.min.x - 500 + seed(g * 3 + 1) * (area.max.x - area.min.x + 1000);
    const cz = area.min.z - 500 + seed(g * 3 + 2) * (area.max.z - area.min.z + 1000);
    const x = cx + (seed(i * 2 + 11) - 0.5) * 110;
    const z = cz + (seed(i * 2 + 12) - 0.5) * 110;
    if (dist(x, z) < 42 || reservado(x, z)) continue;
    lugares.push([x, z, 15 + seed(i + 5) * 16]);
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

export type Cenario = {
  arquibancadas: { f0: number; f1: number; coberta?: boolean; dist: number }[];
  boxes?: { f0: number; f1: number; dist: number };
  lagos?: { f: number; dist: number; r: number }[];
};

/** Veste o circuito: tudo entra marcado como fora do enquadramento (enquadrar() só olha a pista). */
export function vestirCircuito(g: THREE.Group, pts: THREE.Vector3[], comprimento: number, o: Cenario) {
  const tudo = new THREE.Group();
  // o lago sai de perto da pista: empurrado para fora até ficar longe do traçado (nunca cobre o asfalto)
  const dist = distanciaAoTracado(pts);
  const meio = new THREE.Box3().setFromPoints(pts).getCenter(new THREE.Vector3());
  const lagos = (o.lagos ?? []).map((l) => {
    const q = aoLado(pts, l.f, l.dist);
    for (let i = 0; i < 40 && dist(q.x, q.z) < l.r * 1.7 + 60; i++) {
      const n = Math.hypot(q.x - meio.x, q.z - meio.z) || 1;
      q.x += ((q.x - meio.x) / n) * 40;
      q.z += ((q.z - meio.z) / n) * 40;
    }
    return { ...q, r: l.r };
  });
  tudo.add(relevo(pts, lagos));
  for (const l of lagos) tudo.add(lago(l.x, l.z, l.r));
  const grupo = new THREE.Group();
  for (const a of o.arquibancadas) grupo.add(arquibancadas(pts, a.f0, a.f1, a.dist, a.coberta ?? false, comprimento));
  if (o.boxes) grupo.add(boxes(pts, o.boxes.f0, o.boxes.f1, o.boxes.dist));
  tudo.add(grupo);
  grupo.updateMatrixWorld(true);
  const blocos: THREE.Box3[] = [];
  grupo.children.forEach((x) => x.children.length && blocos.push(new THREE.Box3().setFromObject(x).expandByScalar(9)));
  const reservado = (x: number, z: number) => {
    if (lagos.some((l) => Math.hypot((x - l.x) / 1.5, z - l.z) < l.r * 1.12)) return true;
    const p = new THREE.Vector3(x, 1, z);
    return blocos.some((b) => b.containsPoint(p));
  };
  tudo.add(arvores(pts, reservado));
  g.add(fora(tudo));
}
