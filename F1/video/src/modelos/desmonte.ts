// Desmonte dos modelos (técnicas do skill "teardown", MIT, reescritas para o nosso Remotion): explodir em camadas,
// isolar uma peça (o resto vira fantasma), raio-X (a casca vira vidro) e corte por um plano.
// Um modelo declara as peças com `peca(grupo, nome, sai, camada)`: `sai` = para onde a peça vai quando explode (metros),
// `camada` 0 = sai primeiro (a de fora). Tudo é refeito a cada quadro: `restaurar()` volta tudo ao normal antes da cena,
// então o desmonte de um plano nunca vaza para o seguinte.
import * as THREE from "three";

type V = [number, number, number];
const mexidos = new Set<THREE.Object3D>();
// estado guardado fora do userData (o userData é copiado em JSON quando um modelo é clonado)
const pos0 = new WeakMap<THREE.Object3D, THREE.Vector3>();
const escala0 = new WeakMap<THREE.Object3D, THREE.Vector3>();
const rot0 = new WeakMap<THREE.Object3D, THREE.Euler>();
// Materiais gêmeos fixos por malha (como no Teardown): o efeito TROCA de material, nunca liga/desliga a transparência
// do original. Ligar e desligar a cada quadro fazia cada aba do render (são 3 em paralelo) montar o shader de um jeito,
// e os quadros alternados piscavam.
type Gemeos = { orig: THREE.Material; fantasma: THREE.MeshStandardMaterial; corte: THREE.MeshStandardMaterial; plano: THREE.Plane };
const gemeos = new WeakMap<THREE.Mesh, Gemeos>();const SEM_CORTE = new THREE.Plane(new THREE.Vector3(0, 1, 0), 1e6);

/** Marca um grupo como peça do modelo (para explodir, isolar e raio-X). */
export function peca<T extends THREE.Object3D>(o: T, nome: string, sai: V = [0, 0, 0], camada = 0): T {
  o.userData.peca = nome;
  o.userData.sai = sai;
  o.userData.camada = camada;
  return o;
}

const pecas = (modelo: THREE.Object3D) => {
  const lista: THREE.Object3D[] = [];
  modelo.traverse((o) => o.userData.peca && lista.push(o));
  return lista;
};

/** Move/escala uma peça só neste quadro (volta sozinha no restaurar): base de destacar e embaralhar. */
export function deslocar(o: THREE.Object3D, d: THREE.Vector3, escala = 1) {
  if (!pos0.has(o)) pos0.set(o, o.position.clone());
  if (!escala0.has(o)) escala0.set(o, o.scale.clone());
  o.position.add(d);
  if (escala !== 1) o.scale.copy(escala0.get(o)!).multiplyScalar(escala);
  mexidos.add(o);
}

/** Gira uma peça só neste quadro (volta sozinha no restaurar): ex.: roda dianteira esterçando. */
export function girarPeca(o: THREE.Object3D, x: number, y: number, z: number) {
  if (!rot0.has(o)) rot0.set(o, o.rotation.clone());
  const r = rot0.get(o)!;
  o.rotation.set(r.x + x, r.y + y, r.z + z);
  mexidos.add(o);
}

/** A peça com esse nome (ou null). */
export const achar = (modelo: THREE.Object3D, nome: string) => {
  let r: THREE.Object3D | null = null;
  modelo.traverse((o) => {
    if (!r && o.userData.peca === nome) r = o;
  });
  return r as THREE.Object3D | null;
};

/** Nomes das peças de um modelo (para o diretor saber o que pode isolar). */
export const nomesDasPecas = (modelo: THREE.Object3D) => pecas(modelo).map((o) => o.userData.peca as string);

const suave = (x: number) => {
  const t = Math.min(1, Math.max(0, x));
  return t * t * t * (t * (t * 6 - 15) + 10);
};

/** Afasta as peças: k = 0 montado, 1 aberto. Cada camada sai no seu trecho (a de fora primeiro), para nada atravessar nada. */
export function explodir(modelo: THREE.Object3D, k: number, distancia = 1) {
  const lista = pecas(modelo);
  const n = Math.max(1, ...lista.map((o) => (o.userData.camada as number) + 1));
  for (const o of lista) {
    if (!pos0.has(o)) pos0.set(o, o.position.clone());
    const ini = ((o.userData.camada as number) / n) * 0.55;
    const t = suave((k - ini) / 0.45) * distancia;
    const [dx, dy, dz] = o.userData.sai as V;
    o.position.copy(pos0.get(o)!).add(new THREE.Vector3(dx * t, dy * t, dz * t));
    mexidos.add(o);
  }
}

const deMalha = (m: THREE.Mesh): Gemeos => {
  let g = gemeos.get(m);
  if (!g) {
    const orig = m.material as THREE.Material;
    const plano = SEM_CORTE.clone();
    const fantasma = orig.clone() as THREE.MeshStandardMaterial;
    const corte = orig.clone() as THREE.MeshStandardMaterial;
    g = { orig, fantasma, corte, plano };
    gemeos.set(m, g);
  } else if (m.material !== g.fantasma && m.material !== g.corte) {
    g.orig = m.material as THREE.Material; // o material da malha foi trocado por fora (ex.: composto do pneu)
  }
  mexidos.add(m);
  return g;
};
/** Recopia o original (cor, brilho do botão apertado…) e fixa o que o gêmeo tem de próprio: sempre o mesmo shader. */
const prepararFantasma = (g: Gemeos, opacidade: number) => {
  g.fantasma.copy(g.orig as THREE.MeshStandardMaterial);
  Object.assign(g.fantasma, { transparent: true, opacity: opacidade, depthWrite: false, clippingPlanes: [g.plano], polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  return g.fantasma;
};

const transparencia = (o: THREE.Object3D, opacidade: number) =>
  o.traverse((x) => {
    const m = x as THREE.Mesh;
    if (!m.isMesh) return;
    m.material = prepararFantasma(deMalha(m), opacidade);
    m.renderOrder = 10; // ordem fixa entre as transparentes: nada troca de lugar quando a câmera anda
  });
/** Só as peças citadas ficam inteiras; o resto vira fantasma (k = 0 normal, 1 quase invisível). */
export function isolar(modelo: THREE.Object3D, nomes: string | string[], k = 1) {
  const quero = new Set(Array.isArray(nomes) ? nomes : [nomes]);
  for (const o of pecas(modelo)) if (!quero.has(o.userData.peca)) transparencia(o, 1 - 0.88 * Math.min(1, Math.max(0, k)));
}

/** Raio-X: as peças citadas (a casca) viram vidro para mostrar o que tem dentro. */
export function raioX(modelo: THREE.Object3D, nomes: string | string[], k = 1) {
  const quero = new Set(Array.isArray(nomes) ? nomes : [nomes]);
  for (const o of pecas(modelo)) if (quero.has(o.userData.peca)) transparencia(o, 1 - 0.78 * Math.min(1, Math.max(0, k)));
}

/** Corte: tira tudo o que fica do lado para onde `normal` aponta, a partir do ponto `em` (no espaço do modelo).
 *  Ex.: cortar(carro, [1, 0, 0]) = some a metade da direita do carro (x > 0). */
export function cortar(modelo: THREE.Object3D, normal: V = [1, 0, 0], em: V = [0, 0, 0]) {
  modelo.updateMatrixWorld(true);
  const ponto = new THREE.Vector3(...em).applyMatrix4(modelo.matrixWorld);
  const n = new THREE.Vector3(...normal).transformDirection(modelo.matrixWorld).negate();
  modelo.traverse((x) => {
    const m = x as THREE.Mesh;
    if (!m.isMesh) return;
    const g = deMalha(m);
    g.plano.setFromNormalAndCoplanarPoint(n, ponto);
    if (m.material !== g.fantasma) {
      g.corte.copy(g.orig as THREE.MeshStandardMaterial);
      Object.assign(g.corte, { clippingPlanes: [g.plano], side: THREE.DoubleSide });
      m.material = g.corte;
    }
  });
}
// modelos com estado próprio (botão apertado, seletor girado) voltam ao normal junto
const voltas = new Set<() => void>();
export const aoRestaurar = (fn: () => void) => voltas.add(fn);

/** Volta tudo o que foi mexido ao normal (chamado antes de cada quadro). */
export function restaurar() {
  voltas.forEach((fn) => fn());
  for (const o of mexidos) {
    const p0 = pos0.get(o);
    if (p0) o.position.copy(p0);
    const e0 = escala0.get(o);
    if (e0) o.scale.copy(e0);
    const r0 = rot0.get(o);
    if (r0) o.rotation.copy(r0);
    const m = o as THREE.Mesh;
    const g = m.isMesh ? gemeos.get(m) : undefined;
    if (g) {
      if (m.material === g.fantasma || m.material === g.corte) m.material = g.orig;
      m.renderOrder = 0;
      g.plano.copy(SEM_CORTE);
    }
  }
  mexidos.clear();
}
