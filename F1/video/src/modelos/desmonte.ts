// Desmonte dos modelos (técnicas do skill "teardown", MIT, reescritas para o nosso Remotion): explodir em camadas,
// isolar uma peça (o resto vira fantasma), raio-X (a casca vira vidro) e corte por um plano.
// Um modelo declara as peças com `peca(grupo, nome, sai, camada)`: `sai` = para onde a peça vai quando explode (metros),
// `camada` 0 = sai primeiro (a de fora). Tudo é refeito a cada quadro: `restaurar()` volta tudo ao normal antes da cena,
// então o desmonte de um plano nunca vaza para o seguinte.
import * as THREE from "three";

type V = [number, number, number];
type Original = { transparent: boolean; opacity: number; depthWrite: boolean };
const mexidos = new Set<THREE.Object3D>();
// estado guardado fora do userData (o userData é copiado em JSON quando um modelo é clonado)
const pos0 = new WeakMap<THREE.Object3D, THREE.Vector3>();
const original = new WeakMap<THREE.Mesh, Original>();
const planos = new WeakMap<THREE.Mesh, THREE.Plane>();
const SEM_CORTE = new THREE.Plane(new THREE.Vector3(0, 1, 0), 1e6);

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

/** Material próprio de cada malha (o modelo é clonado e os clones dividem materiais): copiado uma vez só. */
const proprio = (m: THREE.Mesh) => {
  if (!original.has(m)) {
    const mt = (m.material as THREE.Material).clone();
    m.material = mt;
    original.set(m, { transparent: mt.transparent, opacity: mt.opacity, depthWrite: mt.depthWrite });
  }
  mexidos.add(m);
  return m.material as THREE.MeshStandardMaterial;
};

const transparencia = (o: THREE.Object3D, opacidade: number) =>
  o.traverse((x) => {
    const m = x as THREE.Mesh;
    if (!m.isMesh) return;
    const mt = proprio(m);
    mt.transparent = opacidade < 0.999;
    mt.opacity = opacidade;
    mt.depthWrite = opacidade > 0.5;
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
    const mt = proprio(m);
    let p = planos.get(m);
    if (!p) {
      // o plano fica no material para sempre (trocar a lista de planos recompila o shader); sem corte = plano bem longe
      p = new THREE.Plane();
      planos.set(m, p);
      mt.clippingPlanes = [p];
      mt.side = THREE.DoubleSide;
      mt.needsUpdate = true;
    }
    p.setFromNormalAndCoplanarPoint(n, ponto);
  });
}

/** Volta tudo o que foi mexido ao normal (chamado antes de cada quadro). */
export function restaurar() {
  for (const o of mexidos) {
    const p0 = pos0.get(o);
    if (p0) o.position.copy(p0);
    const m = o as THREE.Mesh;
    const orig = m.isMesh ? original.get(m) : undefined;
    if (orig) Object.assign(m.material as THREE.Material, orig);
    planos.get(m)?.copy(SEM_CORTE);
  }
  mexidos.clear();
}
