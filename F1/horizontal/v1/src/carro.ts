// Carro oficial (.glb do acervo F1/dados/modelos3d) pronto para as cenas: de pé no chão, 5,4 m, comprimento em z,
// rodas separadas em pivôs. Saiu do teste do estúdio (TesteEstudio.tsx).
import * as THREE from "three";

const RODA = /tyre|tire|wheel_hub|disc|rim/i;

export type Roda = { pivo: THREE.Group; frente: boolean };

/** Carro do arquivo → grupo de pé no chão, 5,4 m, comprimento em z; rodas separadas em pivôs que giram no eixo x. */
export function preparar(cena: THREE.Group): { carro: THREE.Group; rodas: Roda[]; raio: number; frenteZ: number } {
  cena.updateMatrixWorld(true);
  let caixa = new THREE.Box3().setFromObject(cena);
  let t = caixa.getSize(new THREE.Vector3());
  const giro = new THREE.Matrix4();
  if (t.x > t.z) giro.makeRotationY(Math.PI / 2);
  const malhas: THREE.Mesh[] = [];
  cena.traverse((o) => { if ((o as THREE.Mesh).isMesh) malhas.push(o as THREE.Mesh); });
  // assa as transformações na geometria (sem a hierarquia do arquivo)
  const assadas = malhas.map((m) => {
    const g = m.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(giro, m.matrixWorld));
    return { g, mat: m.material as THREE.Material, roda: RODA.test((m.material as THREE.Material).name) };
  });
  caixa = new THREE.Box3();
  assadas.forEach((a) => { a.g.computeBoundingBox(); caixa.union(a.g.boundingBox!); });
  t = caixa.getSize(new THREE.Vector3());
  const s = 5.4 / t.z;
  const c = caixa.getCenter(new THREE.Vector3());
  const ajuste = new THREE.Matrix4().makeScale(s, s, s).multiply(new THREE.Matrix4().makeTranslation(-c.x, -caixa.min.y, -c.z));
  assadas.forEach((a) => a.g.applyMatrix4(ajuste));
  // frente = ponta mais baixa (a asa traseira é alta)
  const alto = (z0: number, z1: number) => {
    let m = 0;
    assadas.forEach(({ g, roda }) => {
      if (roda) return;
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) { const z = p.getZ(i); if (z > z0 && z < z1) m = Math.max(m, p.getY(i)); }
    });
    return m;
  };
  const frenteZ = alto(-2.7, -2.0) < alto(2.0, 2.7) ? -1 : 1;
  // rodas: cada triângulo vai para o canto do seu centro (x, z)
  const carro = new THREE.Group();
  const cantos: Record<string, { g: THREE.BufferGeometry; mat: THREE.Material }[]> = {};
  assadas.forEach(({ g, mat, roda }) => {
    if (!roda) { const m = new THREE.Mesh(g, mat); m.castShadow = true; m.receiveShadow = true; carro.add(m); return; }
    const ng = g.index ? g.toNonIndexed() : g;
    const p = ng.attributes.position;
    const por: Record<string, number[]> = {};
    for (let i = 0; i < p.count; i += 3) {
      const cx = (p.getX(i) + p.getX(i + 1) + p.getX(i + 2)) / 3;
      const cz = (p.getZ(i) + p.getZ(i + 1) + p.getZ(i + 2)) / 3;
      (por[`${cx > 0 ? "d" : "e"}${cz > 0 ? "+" : "-"}`] ??= []).push(i);
    }
    for (const [k, ids] of Object.entries(por)) {
      const nova = new THREE.BufferGeometry();
      for (const nome of Object.keys(ng.attributes)) {
        const at = ng.attributes[nome] as THREE.BufferAttribute;
        const n = at.itemSize;
        const arr = new Float32Array(ids.length * 3 * n);
        ids.forEach((i, j) => { for (let v = 0; v < 3; v++) for (let q = 0; q < n; q++) arr[(j * 3 + v) * n + q] = at.getComponent(i + v, q); });
        nova.setAttribute(nome, new THREE.BufferAttribute(arr, n));
      }
      (cantos[k] ??= []).push({ g: nova, mat });
    }
  });
  const rodas: Roda[] = [];
  let raio = 0.36;
  for (const [k, geos] of Object.entries(cantos)) {
    const cx = new THREE.Box3();
    geos.forEach(({ g }) => { g.computeBoundingBox(); cx.union(g.boundingBox!); });
    const centro = cx.getCenter(new THREE.Vector3());
    raio = (cx.max.y - cx.min.y) / 2;
    const pivo = new THREE.Group();
    pivo.position.copy(centro);
    const gira = new THREE.Group();
    pivo.add(gira);
    geos.forEach(({ g, mat }) => {
      g.translate(-centro.x, -centro.y, -centro.z);
      const m = new THREE.Mesh(g, mat);
      m.castShadow = true;
      gira.add(m);
    });
    carro.add(pivo);
    rodas.push({ pivo, frente: (k.endsWith("+") ? 1 : -1) === frenteZ });
  }
  return { carro, rodas, raio, frenteZ };
}
