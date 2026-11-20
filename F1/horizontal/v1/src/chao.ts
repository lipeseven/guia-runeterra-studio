// Chão real da pista (.glb): altura do asfalto em qualquer ponto, para o carro não afundar nem flutuar.
import * as THREE from "three";

// altura real do asfalto do .glb: triângulos do chão numa grade de células de 4 m (raycast no arquivo inteiro seria lento)
export type Chao = (x: number, z: number, perto: number) => number | null;
const CELULA = 4;
export function criarChao(malhas: THREE.Mesh[]): Chao {
  const grade = new Map<number, number[]>();
  const tri: number[] = [];
  const v = new THREE.Vector3();
  for (const m of malhas) {
    const p = m.geometry.attributes.position;
    const ix = m.geometry.index;
    const n = ix ? ix.count : p.count;
    for (let i = 0; i < n; i += 3) {
      const t = tri.length / 9;
      let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
      for (let k = 0; k < 3; k++) {
        v.fromBufferAttribute(p, ix ? ix.getX(i + k) : i + k).applyMatrix4(m.matrixWorld);
        tri.push(v.x, v.y, v.z);
        x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); z0 = Math.min(z0, v.z); z1 = Math.max(z1, v.z);
      }
      for (let cx = Math.floor(x0 / CELULA); cx <= Math.floor(x1 / CELULA); cx++)
        for (let cz = Math.floor(z0 / CELULA); cz <= Math.floor(z1 / CELULA); cz++) {
          const c = cx * 100000 + cz;
          (grade.get(c) ?? grade.set(c, []).get(c)!).push(t);
        }
    }
  }
  // altura no ponto (x, z); com mais de um chão (ex.: ponte), o mais perto da altura esperada
  return (x, z, perto) => {
    let melhor: number | null = null;
    for (const t of grade.get(Math.floor(x / CELULA) * 100000 + Math.floor(z / CELULA)) ?? []) {
      const o = t * 9;
      const ax = tri[o], ay = tri[o + 1], az = tri[o + 2];
      const bx = tri[o + 3] - ax, by = tri[o + 4] - ay, bz = tri[o + 5] - az;
      const cx = tri[o + 6] - ax, cy = tri[o + 7] - ay, cz = tri[o + 8] - az;
      const px = x - ax, pz = z - az;
      const d = bx * cz - cx * bz;
      if (Math.abs(d) < 1e-9) continue;
      const s = (px * cz - cx * pz) / d;
      const r = (bx * pz - px * bz) / d;
      if (s < -1e-4 || r < -1e-4 || s + r > 1 + 1e-4) continue;
      const y = ay + s * by + r * cy;
      if (melhor === null || Math.abs(y - perto) < Math.abs(melhor - perto)) melhor = y;
    }
    return melhor;
  };
}
