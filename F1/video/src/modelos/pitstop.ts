// Pit stop coreografado: equipe de 22 por função (pistola, tira, põe, macaco, estabilizador, asa, liberação, segurança,
// apoio), macacos dianteiro e traseiro, pistolas, painel de luzes e pneus novos. Coreografia portada do teste livre do
// Blender (`C:\Users\Felipe\opus-livre-teste\pit-stop\scripts\cena.py`, 2026-11-09): braços e pernas com IK de dois ossos.
// A conta é feita no espaço do Blender (x = frente do carro, y = lado, z = altura) e convertida no fim por `O()`; o carro
// da biblioteca (frente para -z, eixos em z = -1,55 e 1,85) recebe a mesma coreografia. Tudo é refeito a cada quadro.
import * as THREE from "three";
import { roda } from "./Carro3D";
import { achar, deslocar, girarPeca } from "./desmonte";
import type { Mundo } from "./mundo";

type V3 = THREE.Vector3;
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

// ----------------------------------------------------------------- utilidades (mesmos nomes do teste)
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const sm = (x: number) => {
  x = clamp(x);
  return x * x * (3 - 2 * x);
};
const ss = (t: number, a: number, b: number) => (b > a ? sm((t - a) / (b - a)) : Number(t >= a));
const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
const vl = (a: V3, b: V3, u: number) => a.clone().lerp(b, u);
function path(t: number, keys: [number, V3][]): V3 {
  if (t <= keys[0][0]) return keys[0][1].clone();
  for (let i = 0; i < keys.length - 1; i++) {
    const [a, pa] = keys[i], [b, pb] = keys[i + 1];
    if (t <= b) return vl(pa, pb, ss(t, a, b));
  }
  return keys[keys.length - 1][1].clone();
}

// Blender → cena: x do Blender (frente) vira -z com a escala dos eixos do nosso molde; y (lado) vira x; z vira y.
const FRENTE = 1.55 / 1.8, TRAS = 1.85 / 1.8;
const bz = (x: number) => -x * (x > 0 ? FRENTE : TRAS);
const O = (p: V3) => V(p.y, p.z, bz(p.x));
const dirO = (d: V3) => V(d.y, d.z, -d.x).normalize();
const mBase = new THREE.Matrix4();
/** Põe `o` em `pos` com a frente na direção `fwd` e o alto em `up` (vetores do Blender). Geometria local: x = frente,
 *  y = alto, z = lado. */
function base(o: THREE.Object3D, pos: V3, fwd: V3, up: V3) {
  const X = dirO(fwd), Y = dirO(up), Z = X.clone().cross(Y).normalize();
  Y.copy(Z).cross(X).normalize();
  mBase.makeBasis(X, Y, Z);
  o.quaternion.setFromRotationMatrix(mBase);
  o.position.copy(O(pos));
}
const giro = (yaw: number, lean = 0): [V3, V3] => [
  V(Math.cos(yaw) * Math.cos(lean), Math.sin(yaw) * Math.cos(lean), -Math.sin(lean)),
  V(Math.cos(yaw) * Math.sin(lean), Math.sin(yaw) * Math.sin(lean), Math.cos(lean)),
];

const mat = (cor: string, rough = 0.5, metal = 0) => new THREE.MeshStandardMaterial({ color: cor, roughness: rough, metalness: metal });
const caixa = (x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, m: THREE.Material) => {
  // (x frente, y lado, z alto) do Blender → geometria local (x frente, y alto, z lado)
  const g = new THREE.BoxGeometry(x1 - x0, z1 - z0, y1 - y0);
  g.translate((x0 + x1) / 2, (z0 + z1) / 2, (y0 + y1) / 2);
  return new THREE.Mesh(g, m);
};
const CIL = new THREE.CylinderGeometry(1, 1, 1, 12).translate(0, 0.5, 0);
const ESF = new THREE.SphereGeometry(1, 14, 10);
const cima = V(0, 1, 0);
const qTmp = new THREE.Quaternion();
/** Cilindro de A a B (pontos do Blender), raio r. */
function segmento(o: THREE.Object3D, A: V3, B: V3, r: number) {
  const a = O(A), d = O(B).sub(a);
  const L = Math.max(d.length(), 1e-4);
  o.position.copy(a);
  o.quaternion.copy(qTmp.setFromUnitVectors(cima, d.divideScalar(L)));
  o.scale.set(r, L, r);
}
function junta(o: THREE.Object3D, p: V3, r: number) {
  o.position.copy(O(p));
  o.scale.setScalar(r);
}

function ik2(A: V3, T: V3, l1: number, l2: number, pole: V3): [V3, V3] {
  const d = T.clone().sub(A);
  const dist = d.length();
  const dn = dist > 1e-6 ? d.clone().normalize() : V(0, 0, -1);
  const dc = clamp(dist, Math.abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3);
  const T2 = A.clone().addScaledVector(dn, dc);
  const cA = clamp((l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc), -1, 1);
  const sA = Math.sqrt(Math.max(0, 1 - cA * cA));
  const p = pole.clone().addScaledVector(dn, -pole.dot(dn));
  if (p.length() < 1e-6) p.set(dn.y, -dn.x, 0);
  p.normalize();
  return [A.clone().addScaledVector(dn, l1 * cA).addScaledVector(p, l1 * sA), T2];
}

// ----------------------------------------------------------------- mecânicos
export const PAPEIS: Record<string, string> = {
  pistola: "#ff7a00", tira: "#35c2ff", poe: "#8b4dff", macaco: "#ffc400", estabilizador: "#00b3a4",
  asa: "#ff3d8b", liberacao: "#e53935", seguranca: "#ff8a80", apoio: "#9aa1ab",
};
const CINZA = new THREE.Color("#8d929a");
type Modo = "normal" | "fantasma" | "some" | "cinza";
// Fantasma: um material só (mesma cor e opacidade) para todos os translúcidos, sem escrever profundidade e sem sombra:
// a mistura dá o mesmo resultado em qualquer ordem de desenho, então não pisca quando a ordem muda entre quadros.
const FANTASMA = new THREE.MeshStandardMaterial({ color: "#e4e8ee", roughness: 0.6, transparent: true, opacity: 0.1, depthWrite: false });
const ORIG = new WeakMap<THREE.Mesh, { mat: THREE.Material | THREE.Material[]; sombra: boolean }>();
function fantasma(malhas: THREE.Object3D[], sim: boolean) {
  for (const raiz of malhas)
    raiz.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      if (!ORIG.has(m)) ORIG.set(m, { mat: m.material, sombra: m.castShadow });
      const og = ORIG.get(m)!;
      m.material = sim ? FANTASMA : og.mat;
      m.castShadow = sim ? false : og.sombra;
    });
}
const UNI = mat("#2b3038", 0.6), LUVA = mat("#141518", 0.6), VISOR = mat("#0d0f12", 0.08, 0.3);

type Pose = { h?: number; lean?: number; maos?: [V3 | null, V3 | null]; olha?: V3 | null; anda?: [V3, number] | null; anel?: number };

class Mecanico {
  g = new THREE.Group();
  cor: THREE.MeshStandardMaterial;
  anel: THREE.Group;
  tronco: THREE.Group;
  pelve: THREE.Mesh;
  cabeca: THREE.Group;
  membros: THREE.Mesh[] = [];
  juntas: THREE.Mesh[] = [];
  maos: THREE.Mesh[] = [];
  botas: THREE.Mesh[] = [];
  topo = V(0, 0, 0);
  corpo: THREE.Mesh[] = [];
  constructor(public papel: string) {
    const cor = PAPEIS[papel];
    this.cor = mat(cor, 0.35);
    this.tronco = new THREE.Group();
    // o tronco escuro termina DENTRO da faixa colorida do ombro: faces de cima no mesmo plano brigavam na profundidade e
    // na sombra (a cor da faixa "piscava" de um quadro para o outro)
    this.tronco.add(caixa(-0.12, 0.12, -0.2, 0.2, 0, 0.45, UNI), caixa(-0.13, 0.13, -0.225, 0.225, 0.38, 0.5, this.cor));
    this.pelve = caixa(-0.11, 0.11, -0.17, 0.17, -0.14, 0.05, UNI);
    this.cabeca = new THREE.Group();
    const capacete = new THREE.Mesh(ESF, this.cor);
    capacete.scale.set(0.128 * 1.08, 0.128, 0.128);
    this.cabeca.add(capacete, caixa(0.06, 0.137, -0.09, 0.09, -0.03, 0.04, VISOR));
    for (let k = 0; k < 8; k++) this.membros.push(new THREE.Mesh(CIL, UNI));
    for (let k = 0; k < 6; k++) this.juntas.push(new THREE.Mesh(ESF, UNI));
    for (let k = 0; k < 2; k++) {
      const m = new THREE.Mesh(ESF, LUVA);
      m.scale.set(0.052 * 1.2, 0.052 * 0.85, 0.052);
      this.maos.push(m);
      this.botas.push(caixa(-0.07, 0.19, -0.055, 0.055, -0.085, 0.03, LUVA));
    }
    // anel no chão na cor da função (tracejado = tarefa opcional: asa)
    this.anel = new THREE.Group();
    const corAnel = new THREE.MeshBasicMaterial({ color: cor });
    const n = papel === "asa" ? 14 : 1;
    for (let k = 0; k < n; k++) {
      const arco = new THREE.Mesh(new THREE.TorusGeometry(0.46, 0.03, 6, n > 1 ? 6 : 48, n > 1 ? Math.PI / n : Math.PI * 2), corAnel);
      arco.rotation.set(-Math.PI / 2, 0, (k * 2 * Math.PI) / n);
      this.anel.add(arco);
    }
    this.g.add(this.tronco, this.pelve, this.cabeca, this.anel, ...this.membros, ...this.juntas, ...this.maos, ...this.botas);
    for (const o of [...this.tronco.children, this.pelve, ...this.membros, ...this.juntas, ...this.botas]) o.castShadow = true;
    this.corpo = [...this.tronco.children, this.pelve, ...this.cabeca.children, ...this.membros, ...this.juntas, ...this.maos, ...this.botas] as THREE.Mesh[];
  }

  /** normal | fantasma (translúcido) | some (fora da cena) | cinza (cor da função apagada) */
  modo(m: Modo) {
    this.cor.color.set(m === "cinza" ? CINZA : PAPEIS[this.papel]);
    this.g.visible = m !== "some";
    fantasma(this.corpo, m === "fantasma");
    if (m === "fantasma") this.anel.visible = false;
  }

  pose(raiz: V3, yaw: number, p: Pose = {}) {
    const h = p.h ?? 0.92, lean = p.lean ?? 0.06;
    const root = V(raiz.x, raiz.y, 0);
    const fwd = V(Math.cos(yaw), Math.sin(yaw), 0), left = V(-Math.sin(yaw), Math.cos(yaw), 0), Z = V(0, 0, 1);
    const P = root.clone().addScaledVector(Z, h);
    const up = fwd.clone().multiplyScalar(Math.sin(lean)).addScaledVector(Z, Math.cos(lean));
    const [f1, u1] = giro(yaw, lean);
    base(this.tronco, P, f1, u1);
    base(this.pelve, P, fwd, Z);
    const head = P.clone().addScaledVector(up, 0.68);
    let hy = yaw;
    if (p.olha) {
      const d = p.olha.clone().sub(head);
      const dyaw = ((Math.atan2(d.y, d.x) - yaw + Math.PI * 3) % (2 * Math.PI)) - Math.PI;
      hy = yaw + clamp(dyaw, -1.2, 1.2);
    }
    const [f2, u2] = giro(hy, lean * 0.4);
    base(this.cabeca, head, f2, u2);
    this.topo.copy(head);
    // pernas
    let fl: V3, fr: V3;
    if (h < 0.75) {
      fl = root.clone().addScaledVector(left, 0.17).addScaledVector(fwd, 0.18);
      fr = root.clone().addScaledVector(left, -0.17).addScaledVector(fwd, -0.12);
    } else {
      fl = root.clone().addScaledVector(left, 0.12).addScaledVector(fwd, 0.03);
      fr = root.clone().addScaledVector(left, -0.12).addScaledVector(fwd, 0.03);
    }
    fl.z = fr.z = 0.085;
    if (p.anda) {
      const [wd, ph] = p.anda;
      const w = V(wd.x, wd.y, 0);
      fl.addScaledVector(w, 0.17 * Math.sin(ph));
      fr.addScaledVector(w, -0.17 * Math.sin(ph));
      fl.z += Math.max(0, Math.cos(ph)) * 0.07;
      fr.z += Math.max(0, -Math.cos(ph)) * 0.07;
    }
    const quadris = [P.clone().addScaledVector(left, 0.1).addScaledVector(Z, -0.07), P.clone().addScaledVector(left, -0.1).addScaledVector(Z, -0.07)];
    [fl, fr].forEach((ft, k) => {
      const [jo, pe] = ik2(quadris[k], ft, 0.45, 0.43, fwd.clone().addScaledVector(Z, 0.1));
      segmento(this.membros[k * 2], quadris[k], jo, 0.075);
      segmento(this.membros[k * 2 + 1], jo, pe, 0.064);
      junta(this.juntas[k], jo, 0.07);
      base(this.botas[k], pe, fwd, Z);
    });
    // braços
    const ombros = [P.clone().addScaledVector(up, 0.45).addScaledVector(left, 0.215), P.clone().addScaledVector(up, 0.45).addScaledVector(left, -0.215)];
    const maos = p.maos ?? [null, null];
    ombros.forEach((sp, k) => {
      const lado = left.clone().multiplyScalar(k === 0 ? 1 : -1);
      const alvo = maos[k] ?? sp.clone().addScaledVector(Z, -0.56).addScaledVector(fwd, 0.06).addScaledVector(lado, 0.05);
      const [co, mao] = ik2(sp, alvo, 0.3, 0.29, fwd.clone().multiplyScalar(-0.4).addScaledVector(Z, -0.6).addScaledVector(lado, 0.7));
      segmento(this.membros[4 + k * 2], sp, co, 0.052);
      segmento(this.membros[5 + k * 2], co, mao, 0.045);
      junta(this.juntas[2 + k], co, 0.05);
      junta(this.juntas[4 + k], sp, 0.06);
      base(this.maos[k], mao, fwd, Z);
    });
    const s = p.anel ?? 0;
    this.anel.visible = s > 0.01;
    this.anel.position.copy(O(V(root.x, root.y, 0.012)));
    this.anel.scale.setScalar(Math.max(s, 0.01));
  }
}

// ----------------------------------------------------------------- equipamentos
const FERR = mat("#3b4048", 0.35, 0.4), ESCURO = mat("#17181d", 0.6), METAL = mat("#b8bcc4", 0.3, 0.8), MACACO = mat("#d8dce2", 0.35, 0.3);

function pistola() {
  const g = new THREE.Group();
  const soq = new THREE.Mesh(new THREE.CylinderGeometry(0.042, 0.042, 0.09, 16).rotateZ(Math.PI / 2).translate(-0.045, 0, 0), METAL);
  g.add(soq, caixa(-0.34, -0.08, -0.05, 0.05, -0.065, 0.065, FERR), caixa(-0.31, -0.24, -0.03, 0.03, -0.2, -0.05, ESCURO), caixa(-0.16, -0.1, -0.025, 0.025, 0.06, 0.12, ESCURO));
  return g;
}

type Macaco = { base: THREE.Group; haste: THREE.Mesh; braco: THREE.Mesh; berco: THREE.Mesh; pega: THREE.Mesh; frente: boolean };
function macaco(frente: boolean): Macaco {
  const s = frente ? 1 : -1;
  const b = new THREE.Group();
  const [x0, x1] = [-s * 0.08, s * 0.14].sort((a, c) => a - c);
  b.add(caixa(x0, x1, -0.2, 0.2, 0.06, frente ? 0.34 : 0.42, MACACO));
  for (const sy of [1, -1]) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.05, 16).rotateX(Math.PI / 2), ESCURO);
    r.position.set(s * 0.06, 0.06, sy * 0.24);
    b.add(r);
  }
  return { base: b, haste: new THREE.Mesh(CIL, METAL), braco: new THREE.Mesh(CIL, MACACO), berco: new THREE.Mesh(CIL, ESCURO), pega: new THREE.Mesh(CIL, ESCURO), frente };
}

// ----------------------------------------------------------------- tempos do pit stop (t em segundos; 0 = carro parado)
const JIT: Record<string, number> = { "1,1": 0, "1,-1": 0.03, "-1,1": 0.05, "-1,-1": 0.02 };
const T_GO = 2.05;
const AX: Record<number, number> = { 1: 1.8, [-1]: -1.8 };
const HUBY: Record<number, number> = { 1: 0.81, [-1]: 0.76 }; // largura entre rodas do nosso molde (dianteira, traseira)
const R_TYRE = 0.36;
const WHALF: Record<number, number> = { 1: 0.15, [-1]: 0.19 };
const FJ_P = V(3.39, 0, 0.38), RJ_P = V(-2.98, 0, 0.46);
const carX = (t: number) => (t < 0 ? -6 * t * t : t > T_GO ? 4 * (t - T_GO) ** 2 : 0);
const jackFrente = (t: number) => (t < 0.14 ? lerp(0.6, 0.41, ss(t, 0.02, 0.14)) : t < 1.9 ? lerp(0.41, 0.2, ss(t, 0.15, 0.32)) : lerp(0.2, 0.6, ss(t, 1.9, 2.02)));
const jackTras = (t: number) => (t < 0.28 ? lerp(0.6, 0.41, ss(t, 0.2, 0.28)) : t < 1.9 ? lerp(0.41, 0.2, ss(t, 0.28, 0.42)) : lerp(0.2, 0.6, ss(t, 1.9, 2.02)));
function carro(t: number) {
  const bf = jackFrente(t), br = jackTras(t);
  const hf = t >= -0.05 ? Math.max(0, FJ_P.z - 0.4 * Math.sin(bf) - 0.22) : 0;
  const hr = t >= 0.2 ? Math.max(0, RJ_P.z - 0.4 * Math.sin(br) - 0.3) : 0;
  const z0 = (hf + hr) / 2, pitch = Math.atan2(hf - hr, 5.65);
  const M = new THREE.Matrix4().makeTranslation(carX(t), 0, z0).multiply(new THREE.Matrix4().makeRotationY(-pitch));
  return { M, x: carX(t), z0, pitch };
}
const noCarro = (M: THREE.Matrix4, x: number, y: number, z: number) => V(x, y, z).applyMatrix4(M);
const cubo = (M: THREE.Matrix4, sx: number, sy: number) => noCarro(M, AX[sx], sy * HUBY[sx], R_TYRE);

// ----------------------------------------------------------------- montagem
export type PitStop = THREE.Group & { userData: { pontos: Record<string, V3> } };

/** Equipe, macacos, pistolas, painel de luzes e os 4 pneus novos (composto). Ponha com `obj(w, "pit:...", ...)`. */
export function criarPitStop(o: { composto?: string; parede?: number } = {}): PitStop {
  const g = new THREE.Group() as PitStop;
  const M: Record<string, Mecanico> = {};
  const add = (nome: string, papel: string) => {
    M[nome] = new Mecanico(papel);
    g.add(M[nome].g);
  };
  const novas: Record<string, THREE.Group> = {}, pistolas: Record<string, THREE.Group> = {};
  for (const sx of [1, -1])
    for (const sy of [1, -1]) {
      const k = `${sx},${sy}`;
      for (const r of ["pistola", "tira", "poe"]) add(`${r}:${k}`, r);
      novas[k] = roda(0, 0, R_TYRE, sx > 0 ? 0.28 : 0.38, o.composto ?? "medio");
      pistolas[k] = pistola();
      g.add(novas[k], pistolas[k]);
    }
  add("macaco:1", "macaco");
  add("macaco:-1", "macaco");
  for (const sy of [1, -1]) {
    add(`estabilizador:${sy}`, "estabilizador");
    add(`asa:${sy}`, "asa");
  }
  add("liberacao", "liberacao");
  add("seguranca", "seguranca");
  add("apoio:1", "apoio");
  add("apoio:2", "apoio");
  const jf = macaco(true), jt = macaco(false);
  for (const j of [jf, jt]) g.add(j.base, j.haste, j.braco, j.berco, j.pega);
  const chaves: Record<number, THREE.Mesh> = { 1: new THREE.Mesh(CIL, METAL), [-1]: new THREE.Mesh(CIL, METAL) };
  const controle = caixa(-0.06, 0.06, -0.1, 0.1, -0.03, 0.03, ESCURO);
  g.add(chaves[1], chaves[-1], controle);
  // painel de luzes do box: pendurado em cima, à frente do bico e virado para o piloto, num braço preso à parede do box
  // (set `pit`: fachada das garagens em x = 12,45 m, a da garagem em frente ao carro vai de z = -1,5 a 13,5). Nada no chão:
  // o carro sai por baixo. O braço não conta no `enquadrar` (foraDoEnquadro).
  const painel = new THREE.Group();
  const suporte = new THREE.Group();
  const viga = (a: THREE.Vector3, b: THREE.Vector3, r: number) => {
    const m = new THREE.Mesh(CIL, ESCURO);
    const d = b.clone().sub(a);
    m.position.copy(a);
    m.quaternion.setFromUnitVectors(cima, d.clone().normalize());
    m.scale.set(r, d.length(), r);
    m.userData.foraDoEnquadro = true;
    suporte.add(m);
  };
  const ALTO = 4.3, PAREDE = o.parede ?? 12.45, XL = 0.1, ZL = bz(4.27), ZB = -0.9;
  viga(V(XL, 3.04, ZL), V(XL, ALTO, ZL), 0.03); // haste que segura a caixa das luzes
  viga(V(XL, ALTO, ZL - 0.05), V(XL, ALTO, ZB), 0.06); // braço para trás, até a viga principal
  viga(V(XL - 0.06, ALTO, ZB), V(PAREDE, ALTO, ZB), 0.07); // viga principal, saindo da parede do box
  viga(V(PAREDE, ALTO - 1.6, ZB), V(PAREDE - 2.4, ALTO, ZB), 0.045); // mão-francesa
  const chapa = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2.1, 0.5), ESCURO);
  chapa.position.set(PAREDE - 0.03, ALTO - 0.75, ZB);
  chapa.userData.foraDoEnquadro = true;
  suporte.add(chapa);
  const placa = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.62, 0.04), ESCURO);
  placa.position.copy(O(V(4.27, 0.1, 2.75)));
  const luz = (r: number, p: V3) => {
    const m = new THREE.Mesh(new THREE.CircleGeometry(r, 28), new THREE.MeshBasicMaterial({ color: "#e00000" }));
    m.position.copy(O(p)).add(V(0, 0, 0.025));
    painel.add(m);
    return m;
  };
  const luzMain = luz(0.095, V(4.245, 0.1, 2.58));
  const luzRoda: Record<string, THREE.Mesh> = {};
  const pos: Record<string, [number, number]> = { "1,1": [0.18, 2.9], "1,-1": [0.02, 2.9], "-1,1": [0.18, 2.77], "-1,-1": [0.02, 2.77] };
  for (const [k, [py, pz]] of Object.entries(pos)) luzRoda[k] = luz(0.04, V(4.245, py, pz));
  painel.add(placa);
  g.add(painel, suporte);
  g.userData = { pontos: {} };
  Object.assign(g.userData, { M, novas, pistolas, jf, jt, chaves, controle, luzMain, luzRoda, painel, suporte });
  return g;
}

const RODAS: Record<string, string> = { "1,1": "roda_dianteira_direita", "1,-1": "roda_dianteira_esquerda", "-1,1": "roda_traseira_direita", "-1,-1": "roda_traseira_esquerda" };
const NOMES_EIXO: Record<number, string> = { 1: "d", [-1]: "t" };
const NOMES_LADO: Record<number, string> = { 1: "dir", [-1]: "esq" };

export type OpcoesPit = {
  foco?: string[]; // funções em destaque: as outras ficam translúcidas (ou como `outros` mandar)
  outros?: "translucido" | "some" | "cinza"; // o que acontece com quem não está no foco (padrão: translúcido)
  aneis?: number | Record<string, number>; // anel no chão por função (0 a 1; número = todas)
  asa?: number | null; // ajuste opcional da asa dianteira (0 a 1 ao longo do ajuste); sem = não ajusta
};

/** Coreografia no quadro: carro k (da biblioteca) chega, para no pit, troca os 4 pneus e sai. `t` = segundos do pit stop
 *  (negativo = chegando; 0 = parado; ~0,1–0,4 macacos; 0,6–1,2 troca; 1,85 luz verde; 2,05 sai). */
export function pitStop(w: Mundo, rig: PitStop, k: number, t: number, op: OpcoesPit = {}) {
  const d = rig.userData as unknown as {
    M: Record<string, Mecanico>; novas: Record<string, THREE.Group>; pistolas: Record<string, THREE.Group>; jf: Macaco; jt: Macaco;
    chaves: Record<number, THREE.Mesh>; controle: THREE.Mesh; luzMain: THREE.Mesh; luzRoda: Record<string, THREE.Mesh>; pontos: Record<string, V3>;
    painel: THREE.Group; suporte: THREE.Group;
  };
  const M = d.M;
  const anelDe = (papel: string) => (typeof op.aneis === "number" ? op.aneis : op.aneis?.[papel] ?? 0);
  const foco = op.foco && op.foco.length ? new Set(op.foco) : null;
  const fora: Modo = op.outros === "some" ? "some" : op.outros === "cinza" ? "cinza" : "fantasma";
  const modoDe = (papel: string): Modo => (foco && !foco.has(papel) ? fora : "normal");
  for (const m of Object.values(M)) m.modo(modoDe(m.papel));
  // ferramentas na mão de quem saiu do foco seguem o dono (macacos e pneus ficam: seguram o carro e as rodas)
  const ferramenta = (objs: THREE.Object3D[], papel: string) => {
    const md = modoDe(papel);
    fantasma(objs, md === "fantasma");
    for (const x of objs) x.visible = md !== "some";
  };
  ferramenta(Object.values(d.pistolas), "pistola");
  ferramenta([d.controle], "liberacao");
  // painel de luzes: só no set do box (preso à parede das garagens); no estúdio não há parede
  d.painel.visible = d.suporte.visible = w.sets.pit.visible;
  // carro
  const C = carro(t);
  const Mc = C.M;
  const car = w.carros[k];
  car.visible = true;
  car.scale.setScalar(1);
  car.rotation.y = 0;
  car.position.copy(rig.position).add(O(V(C.x, 0, C.z0)));
  girarPeca(car, C.pitch, 0, 0);
  const carInv = new THREE.Matrix4().compose(O(V(C.x, 0, C.z0)), new THREE.Quaternion().setFromEuler(new THREE.Euler(C.pitch, 0, 0)), V(1, 1, 1)).invert();
  if (C.x < 0) rolarRodas(car, C.x); // chegando: as rodas rolam com a distância e param junto com o carro
  const wp = op.asa ?? null;
  const pontos = d.pontos;
  for (const sx of [1, -1])
    for (const sy of [1, -1]) {
      const key = `${sx},${sy}`;
      const tc = t - JIT[key];
      const o = V(0, sy, 0);
      const H = cubo(Mc, sx, sy);
      const Hrest = V(AX[sx], sy * HUBY[sx], R_TYRE);
      const Hc = t >= -0.02 ? H : Hrest;
      // roda velha (a do carro): sai do cubo e vai para o chão
      const velha = achar(car, RODAS[key]);
      let oldp = H;
      if (tc >= 0.6) {
        oldp = path(tc, [[0.6, H], [0.75, H.clone().addScaledVector(o, 0.3)], [1.05, V(AX[sx] - 0.75, sy * 1.45, 0.38)], [1.5, V(AX[sx] - 1.05, sy * 1.78, R_TYRE)]]);
        const hubLocal = V(sy * HUBY[sx], R_TYRE, bz(AX[sx]));
        // quem tira saiu da cena (outros: "some"): a roda velha some do cubo em vez de flutuar sozinha
        if (velha) deslocar(velha, O(oldp).applyMatrix4(carInv).sub(hubLocal), modoDe("tira") === "some" ? 1e-4 : 1);
      }
      // roda nova
      let newp: V3;
      const nova = d.novas[key];
      if (tc >= 1.2) {
        newp = H;
        nova.visible = true;
        nova.rotation.x = -Math.max(0, C.x) / R_TYRE;
      } else {
        const n0 = V(AX[sx] + 0.8, sy * 1.4, 0.4);
        newp = path(tc, [[0.82, n0], [1.0, V(AX[sx] + 0.3, sy * 1.12, H.z)], [1.14, H.clone().addScaledVector(o, 0.06)], [1.2, H]]);
        nova.rotation.x = 0;
        nova.visible = modoDe("poe") !== "some"; // sem quem põe, a roda nova só aparece já montada
      }
      nova.position.copy(O(newp));
      // pistola
      const nut = H.clone().addScaledVector(o, WHALF[sx] + 0.065);
      const ready = Hc.clone().addScaledVector(o, 0.36).add(V(0, 0, 0.05));
      const upp = H.clone().addScaledVector(o, 0.45).add(V(0, 0, 0.45));
      const ready2 = H.clone().addScaledVector(o, 0.38).add(V(0, 0, 0.1));
      let gp = path(tc, [[0.1, ready], [0.22, nut], [0.55, nut.clone().addScaledVector(o, 0.02)], [0.66, upp], [1.2, upp], [1.28, nut], [1.5, nut], [1.58, ready2]]);
      const gunStand = ss(t, 2.08, 2.3);
      const groot = V(AX[sx], sy * 1.62, 0).addScaledVector(o, 0.45 * gunStand);
      if (t > 2.08) gp = vl(ready2, groot.clone().add(V(0.15, 0, 0.95)).addScaledVector(o, -0.35), gunStand);
      base(d.pistolas[key], gp, o.clone().negate(), V(0, 0, 1));
      const g1 = gp.clone().addScaledVector(o, 0.28).add(V(0, 0, -0.13)), g2 = gp.clone().addScaledVector(o, 0.13).add(V(0, 0, 0.09));
      const back = 0.25 * ss(tc, 0.55, 0.66) * (1 - ss(tc, 1.15, 1.25));
      M[`pistola:${key}`].pose(groot.clone().addScaledVector(o, back * 0.4), Math.atan2(-sy, 0), {
        h: lerp(0.55, 0.92, gunStand), lean: lerp(0.5, 0.1, gunStand) - back, maos: sy < 0 ? [g2, g1] : [g1, g2], olha: H, anel: anelDe("pistola"),
      });
      // tira o pneu velho
      const offOfs = V(-0.62, sy * 0.62, 0);
      const mo = M[`tira:${key}`];
      if (tc < 0.6) {
        const ro = V(AX[sx], sy * HUBY[sx], 0).add(offOfs);
        const reach = ss(tc, 0.42, 0.58);
        const wc = t >= -0.02 ? H : Hrest;
        const hA = vl(ro.clone().add(V(0.35, -sy * 0.15, 0.7)), wc.clone().add(V(-0.22, sy * 0.14, 0.2)), reach);
        const hB = vl(ro.clone().add(V(0.35, 0, 0.55)), wc.clone().add(V(-0.27, sy * 0.14, -0.12)), reach);
        mo.pose(ro, Math.atan2(-offOfs.y, -offOfs.x), { h: 0.8, lean: 0.35, maos: sy > 0 ? [hA, hB] : [hB, hA], olha: wc, anel: anelDe("tira") });
      } else {
        const ro = V(oldp.x, oldp.y, 0).addScaledVector(offOfs, 1 + 0.2 * ss(tc, 0.75, 1.05));
        const d0 = V(AX[sx], sy * HUBY[sx], 0).add(offOfs);
        const dist = ro.distanceTo(d0);
        const toW = V(oldp.x, oldp.y, 0).sub(ro).normalize();
        const hA = oldp.clone().add(V(-0.22, sy * 0.14, 0.2)), hB = oldp.clone().add(V(-0.27, sy * 0.14, -0.12));
        const anda = tc - 0.6 > 0 && tc - 0.6 < 0.95;
        mo.pose(ro, Math.atan2(toW.y, toW.x), {
          h: 0.8, lean: 0.3, maos: sy > 0 ? [hA, hB] : [hB, hA], olha: oldp,
          anda: anda ? [dist > 1e-3 ? ro.clone().sub(d0).normalize() : V(1, 0, 0), (dist / 0.33) * Math.PI] : null, anel: anelDe("tira"),
        });
      }
      // põe o pneu novo
      const onOfs = V(0.55, sy * 0.45, 0);
      const mn = M[`poe:${key}`];
      if (tc < 1.24) {
        const rn = V(newp.x, newp.y, 0).add(onOfs);
        const hA = newp.clone().add(V(0.22, sy * 0.14, 0.2)), hB = newp.clone().add(V(0.27, sy * 0.14, -0.12));
        const n0r = V(AX[sx] + 0.8, sy * 1.4, 0).add(onOfs);
        const dist = rn.distanceTo(n0r);
        const mv = tc > 0.82 && tc < 1.2;
        mn.pose(rn, Math.atan2(-onOfs.y, -onOfs.x), {
          h: 0.82, lean: 0.3, maos: sy < 0 ? [hA, hB] : [hB, hA], olha: newp,
          anda: mv && dist > 1e-3 ? [rn.clone().sub(n0r).normalize(), (dist / 0.33) * Math.PI] : null, anel: anelDe("poe"),
        });
      } else {
        const seat = V(AX[sx], sy * HUBY[sx], 0).add(onOfs);
        const backTo = V(AX[sx] + 1.25, sy * 1.35, 0);
        const u = ss(tc, 1.6, 1.9);
        const rn = vl(seat, backTo, u);
        if (t > 2.1) rn.addScaledVector(o, 0.4 * ss(t, 2.1, 2.4));
        mn.pose(rn, Math.atan2(-onOfs.y, -onOfs.x), {
          h: lerp(0.82, 0.92, u), lean: lerp(0.3, 0.1, u), olha: H,
          anda: u > 0 && u < 1 ? [backTo.clone().sub(seat).normalize(), (rn.distanceTo(seat) / 0.33) * Math.PI] : null, anel: anelDe("poe"),
        });
      }
      const nome = `${NOMES_EIXO[sx]}_${NOMES_LADO[sy]}`;
      pontos[`roda_${nome}`] = O(H);
      for (const r of ["pistola", "tira", "poe"]) pontos[`${r}_${nome}`] = O(M[`${r}:${key}`].topo);
    }
  // macacos
  const poeMacaco = (j: Macaco, piv: V3, b: number) => {
    const s = j.frente ? 1 : -1;
    const dir = V(s * Math.cos(b), 0, Math.sin(b) * (j.frente ? 1 : 1));
    j.base.position.copy(O(V(piv.x, piv.y, 0)));
    segmento(j.haste, piv, piv.clone().addScaledVector(dir, 1.25), 0.024);
    const bracoFim = piv.clone().addScaledVector(dir, -0.4).add(V(0, 0, -0.02));
    segmento(j.braco, piv, bracoFim, 0.03);
    segmento(j.berco, bracoFim.clone().add(V(0, -0.11, 0.0)), bracoFim.clone().add(V(0, 0.11, 0)), 0.035);
    const pega = piv.clone().addScaledVector(dir, 1.2);
    segmento(j.pega, pega.clone().add(V(0, -0.2, 0)), pega.clone().add(V(0, 0.2, 0)), 0.025);
    return pega;
  };
  const bf = jackFrente(t);
  const fp = FJ_P.clone();
  fp.x += 0.7 * ss(t, 2.02, 2.18);
  fp.y += 1.9 * ss(t, 2.16, 2.5);
  // a alavanca desce (b diminui) para levantar: mão na pega
  const Hh = poeMacaco(d.jf, fp, bf);
  M["macaco:1"].pose(V(Hh.x + 0.5, Hh.y, 0), Math.PI, {
    h: 0.9, lean: 0.25 + 0.4 * (1.08 - Hh.z), maos: [Hh.clone().add(V(0, -0.16, 0.02)), Hh.clone().add(V(0, 0.16, 0.02))], olha: V(2.5, 0, 0.4),
    anda: t > 2.16 && t < 2.5 ? [V(0, 1, 0), (fp.y / 0.33) * Math.PI] : null, anel: anelDe("macaco"),
  });
  const br = jackTras(t);
  const rp = RJ_P.clone();
  const yo = t < 1 ? 1.8 * (1 - ss(t, 0, 0.22)) : 0;
  rp.y += yo;
  rp.x -= 0.6 * ss(t, 2.02, 2.3);
  const Hr = poeMacaco(d.jt, rp, br);
  M["macaco:-1"].pose(V(Hr.x - 0.5, Hr.y, 0), 0, {
    h: 0.9, lean: 0.25 + 0.4 * (1.15 - Hr.z), maos: [Hr.clone().add(V(0, 0.16, 0.02)), Hr.clone().add(V(0, -0.16, 0.02))],
    olha: t > -0.3 ? V(-2.4, 0, 0.4) : V(C.x, 0, 0.5), anda: t > 0 && t < 0.22 ? [V(0, -1, 0), ((1.8 - yo) / 0.33) * Math.PI] : null, anel: anelDe("macaco"),
  });
  pontos.macaco_d = O(M["macaco:1"].topo);
  pontos.macaco_t = O(M["macaco:-1"].topo);
  // estabilizadores
  for (const sy of [1, -1]) {
    const u = ss(t, 0.12, 0.32) * (1 - ss(t, 1.98, 2.25));
    const rs = V(0.28, sy * lerp(1.75, 1.22, u), 0);
    const ha = vl(rs.clone().add(V(-0.1, -sy * 0.15, 0.95)), noCarro(Mc, 0.08, sy * 0.68, 0.61), u);
    const hb = vl(rs.clone().add(V(0.15, -sy * 0.15, 0.95)), noCarro(Mc, 0.5, sy * 0.66, 0.6), u);
    const mvs = (t > 0.12 && t < 0.32) || (t > 1.98 && t < 2.25);
    M[`estabilizador:${sy}`].pose(rs, Math.atan2(-sy, 0), {
      h: 0.88, lean: lerp(0.1, 0.42, u), maos: sy < 0 ? [hb, ha] : [ha, hb], olha: noCarro(Mc, 0.3, 0, 0.6),
      anda: mvs ? [V(0, -sy, 0), ((1.75 - Math.abs(rs.y)) / 0.33) * Math.PI] : null, anel: anelDe("estabilizador"),
    });
    pontos[`estabilizador_${NOMES_LADO[sy]}`] = O(M[`estabilizador:${sy}`].topo);
  }
  // asa dianteira (opcional)
  for (const sy of [1, -1]) {
    const mw = M[`asa:${sy}`], ch = d.chaves[sy];
    if (wp === null) {
      mw.pose(V(3.75, sy * (0.98 + 0.75 * ss(t, 1.98, 2.28)), 0), Math.PI, { h: 0.92, lean: 0.08 + 0.02 * Math.sin(t * 1.1 + sy), olha: V(2.8, sy * 0.6, 0.3), anel: anelDe("asa") });
      ch.visible = false;
    } else {
      const kk = ss(wp, 0, 0.25);
      const adj = noCarro(Mc, 2.55, sy * 0.92, 0.33);
      const top = adj.clone().add(V(0, 0, 0.16));
      const rr = vl(V(3.75, sy * 0.98, 0), V(3.38, sy * 1.05, 0), kk);
      const th = vl(rr.clone().add(V(-0.2, -sy * 0.2, 0.75)), top, ss(wp, 0.15, 0.4));
      const outra = vl(rr.clone().add(V(-0.2, sy * 0.2, 0.75)), noCarro(Mc, 2.95, sy * 0.99, 0.32), ss(wp, 0.15, 0.4));
      mw.pose(rr, Math.PI, { h: lerp(0.92, 0.55, kk), lean: lerp(0.08, 0.45, kk), maos: sy < 0 ? [th, outra] : [outra, th], olha: adj, anel: anelDe("asa") });
      ch.visible = modoDe("asa") !== "some";
      fantasma([ch], modoDe("asa") === "fantasma");
      segmento(ch, th, th.clone().add(V(0, 0, -0.16)), 0.012);
    }
    pontos[`asa_${NOMES_LADO[sy]}`] = O(mw.topo);
  }
  // liberação, segurança e apoio
  const rr = V(4.05, 2.55, 0), yaw = Math.atan2(-1, -0.25);
  const cc = rr.clone().add(V(Math.cos(yaw) * 0.32, Math.sin(yaw) * 0.32, 1.12));
  M.liberacao.pose(rr, yaw, { lean: 0.08, maos: [cc.clone().add(V(0.08, 0, 0)), cc.clone().add(V(-0.08, 0, 0))], olha: V(4.3, 0.1, 2.7), anel: anelDe("liberacao") });
  base(d.controle, cc.clone().add(V(0, 0, 0.02)), V(Math.cos(yaw), Math.sin(yaw), 0), V(0, 0, 1));
  const rs = V(-0.55, 2.85, 0);
  M.seguranca.pose(rs, -Math.PI / 2, { lean: 0.06, olha: noCarro(Mc, 0.5, 0, 0.6), anel: anelDe("seguranca") });
  M["apoio:1"].pose(V(-3.4, 3.1, 0), -Math.PI / 2 + 0.2, { lean: 0.03, olha: noCarro(Mc, 0, 0, 0.5), anel: anelDe("apoio") });
  M["apoio:2"].pose(V(-2.4, 3.35, 0), -Math.PI / 2 - 0.1, { lean: 0.03, olha: noCarro(Mc, 0, 0, 0.5), anel: anelDe("apoio") });
  pontos.liberacao = O(M.liberacao.topo);
  pontos.seguranca = O(M.seguranca.topo);
  pontos.painel = O(V(4.245, 0.1, 2.75));
  pontos.luz = O(V(4.245, 0.1, 2.58)).add(V(0, 0, 0.03));
  pontos.carro = O(V(C.x, 0, C.z0 + 0.5));
  // painel: cada roda acende verde depois do aperto; a luz grande fica verde depois das 4
  let todas = true;
  for (const [key, m] of Object.entries(d.luzRoda)) {
    const ok = t >= 1.56 + JIT[key] + 0.03 && t < 3.5;
    todas = todas && ok;
    (m.material as THREE.MeshBasicMaterial).color.set(ok ? "#22e06b" : "#7a1010");
  }
  (d.luzMain.material as THREE.MeshBasicMaterial).color.set(t >= 1.85 && todas ? "#22e06b" : "#e00000");
}

/** Ponto (no mundo) de um integrante ou peça do pit stop, para mirar a câmera: "pistola_d_esq", "tira_t_dir", "poe_d_dir",
 *  "roda_t_esq", "macaco_d", "macaco_t", "estabilizador_esq", "asa_dir", "liberacao", "seguranca", "painel", "carro".
 *  Vale depois de `pitStop` no mesmo quadro. */
export function noPit(rig: PitStop, nome: string): V3 {
  const p = rig.userData.pontos[nome] ?? rig.userData.pontos.carro ?? V(0, 0.5, 0);
  return p.clone().add(rig.position);
}

/** Rodas de um carro da biblioteca rolando: `metros` = distância andada para a frente desde a parada (ex.: pista do
 *  carro que passa). Proporcional à distância: carro parado = rodas paradas. Chame a cada quadro. */
export function rolarRodas(car: THREE.Object3D, metros: number) {
  for (const nome of Object.values(RODAS)) {
    const r = achar(car, nome)?.children[0];
    if (r) girarPeca(r, -metros / R_TYRE, 0, 0);
  }
}
