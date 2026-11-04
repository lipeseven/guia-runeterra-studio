// Ligações: ícone num círculo, preso por uma linha fina à peça que ele explica (ex.: microfone → botão do rádio).
// É 3D (acompanha a câmera e o modelo), mas desenhado por cima de tudo, como um gráfico informativo.
import * as THREE from "three";
import { desenharIcone } from "./icones";
import { obj } from "./extras";
import type { Mundo } from "./mundo";

const texturas = new Map<string, THREE.CanvasTexture>();
function textura(icone: string) {
  let t = texturas.get(icone);
  if (t) return t;
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  x.fillStyle = "rgba(9,19,38,0.92)";
  x.beginPath();
  x.arc(128, 128, 112, 0, Math.PI * 2);
  x.fill();
  x.strokeStyle = "#2ec4b6";
  x.lineWidth = 14;
  x.stroke();
  desenharIcone(x, icone, 128, 128, 130);
  t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  texturas.set(icone, t);
  return t;
}

export type Ligacao = { peca: string; icone: string; desvio?: [number, number] };

/** Liga ícones às peças do modelo: `desvio` = para onde o ícone vai, no plano do modelo (metros; padrão: para cima).
 *  `k` 0 a 1 = entrada (anime com suave); `tam` = diâmetro do ícone em metros (0,045 serve ao volante). */
export function ligar(w: Mundo, modelo: THREE.Object3D, itens: Ligacao[], k = 1, tam = 0.045) {
  modelo.updateMatrixWorld(true);
  for (const it of itens) {
    let peca: THREE.Object3D | null = null;
    modelo.traverse((o) => {
      if (!peca && o.userData.peca === it.peca) peca = o;
    });
    if (!peca) continue;
    const centro = new THREE.Box3().setFromObject(peca).getCenter(new THREE.Vector3());
    const local = modelo.worldToLocal(centro.clone());
    const [dx, dy] = it.desvio ?? [0, 0.06];
    const alvo = modelo.localToWorld(local.add(new THREE.Vector3(dx, dy, 0.03)));
    const chave = `lig:${modelo.uuid}:${it.peca}:${it.icone}`;
    const s = obj(w, chave, () => new THREE.Sprite(new THREE.SpriteMaterial({ map: textura(it.icone), transparent: true, depthTest: false })));
    s.position.copy(alvo);
    s.scale.setScalar(tam * (0.7 + 0.3 * k));
    s.renderOrder = 30;
    (s.material as THREE.SpriteMaterial).opacity = k;
    const l = obj(w, `${chave}:linha`, () => new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: "#2ec4b6", transparent: true, depthTest: false })));
    // a linha sai da peça e para na borda do ícone
    const dir = alvo.clone().sub(centro);
    const fim = centro.clone().add(dir.multiplyScalar(Math.max(0, 1 - (tam * 0.5) / Math.max(1e-4, alvo.distanceTo(centro)))));
    (l.geometry as THREE.BufferGeometry).setFromPoints([centro, fim]);
    l.renderOrder = 29;
    (l.material as THREE.LineBasicMaterial).opacity = k;
  }
}
