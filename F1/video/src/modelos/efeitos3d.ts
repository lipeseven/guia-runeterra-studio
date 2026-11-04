// Efeitos 3D dos vídeos informativos: destacar uma peça (ela sai do modelo com brilho), brilho num ponto (ex.: a força
// de frenagem andando de um eixo ao outro), aura elétrica em volta do carro (Boost) e a curva de pista para o carro
// fazer de verdade (entrada, meio e saída). Tudo é refeito a cada quadro.
import * as THREE from "three";
import { achar, deslocar, girarPeca } from "./desmonte";
import { obj, rotulo } from "./extras";
import type { Mundo } from "./mundo";

let texBrilho: THREE.CanvasTexture | null = null;
function brilhoTex() {
  if (texBrilho) return texBrilho;
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.25, "rgba(255,255,255,0.55)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
  texBrilho = new THREE.CanvasTexture(c);
  return texBrilho;
}
const sprite = (cor: string) =>
  new THREE.Sprite(new THREE.SpriteMaterial({ map: brilhoTex(), color: cor, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));

/** Brilho (luz colorida) num ponto do mundo: `chave` identifica o brilho; `tam` em metros; `k` 0 a 1 = intensidade. */
export function brilho(w: Mundo, chave: string, pos: THREE.Vector3 | [number, number, number], tam: number, k = 1, cor = "#2ec4b6") {
  const s = obj(w, `brilho:${chave}`, () => sprite(cor));
  s.position.copy(Array.isArray(pos) ? new THREE.Vector3(...pos) : pos);
  s.scale.setScalar(tam);
  (s.material as THREE.SpriteMaterial).opacity = Math.max(0, Math.min(1, k));
  (s.material as THREE.SpriteMaterial).color.set(cor);
  s.renderOrder = 25;
  return s;
}

/** Destaca peças: elas saem para a frente do modelo (+z, `distancia` em metros), crescem um pouco e ganham brilho
 *  atrás. O resto do modelo fica normal (nada de fantasma). k 0 a 1 (anime com suave). */
export function destacar(w: Mundo, modelo: THREE.Object3D, nomes: string | string[], k = 1, distancia = 0.05, cor = "#2ec4b6") {
  for (const nome of Array.isArray(nomes) ? nomes : [nomes]) {
    const p = achar(modelo, nome);
    if (!p) continue;
    deslocar(p, new THREE.Vector3(0, 0, distancia * k), 1 + 0.18 * k);
    modelo.updateMatrixWorld(true);
    const caixa = new THREE.Box3().setFromObject(p);
    const tam = caixa.getSize(new THREE.Vector3()).length();
    const centro = caixa.getCenter(new THREE.Vector3());
    const atras = modelo.localToWorld(modelo.worldToLocal(centro.clone()).add(new THREE.Vector3(0, 0, -0.01)));
    brilho(w, `${modelo.uuid}:${nome}`, atras, tam * 2.4, 0.85 * k, cor);
  }
}

/** Aura elétrica em volta do modelo (ex.: carro no Boost): brilho azul pulsando e faíscas em volta. */
export function aura(w: Mundo, modelo: THREE.Object3D, t: number, k = 1, cor = "#3d9bff") {
  modelo.updateMatrixWorld(true);
  const caixa = new THREE.Box3().setFromObject(modelo);
  const centro = caixa.getCenter(new THREE.Vector3());
  const tam = caixa.getSize(new THREE.Vector3());
  const pulso = 0.75 + 0.25 * Math.sin(t * 9);
  brilho(w, `aura:${modelo.uuid}`, centro, Math.max(tam.x, tam.z) * 1.5, 0.7 * k * pulso, cor);
  for (let n = 0; n < 16; n++) {
    const fase = (t * (1.6 + (n % 5) * 0.3) + n * 0.37) % 1;
    const a = n * 2.399 + t * 2;
    const p = new THREE.Vector3(centro.x + Math.cos(a) * tam.x * 0.55, caixa.min.y + fase * tam.y * 1.4, centro.z + Math.sin(a) * tam.z * 0.5);
    brilho(w, `faisca:${modelo.uuid}:${n}`, p, 0.18 + 0.12 * Math.sin(n), k * Math.sin(fase * Math.PI), n % 3 ? cor : "#ffffff");
  }
}

/** Curva de pista vista de cima (arco), para o carro fazer: centro na origem, `raio` e `largura` em metros, `angulo` em
 *  radianos; com rótulos ENTRADA / MEIO / SAÍDA opcionais. Use `naCurva(curva, f)` para pôr o carro (f 0 a 1). */
export function criarCurva(o: { raio?: number; largura?: number; angulo?: number; rotulos?: string[] } = {}) {
  const raio = o.raio ?? 14;
  const larg = o.largura ?? 4;
  const ang = o.angulo ?? Math.PI * 0.75;
  const g = new THREE.Group();
  const asfalto = new THREE.Mesh(new THREE.RingGeometry(raio - larg / 2, raio + larg / 2, 64, 1, 0, ang), new THREE.MeshStandardMaterial({ color: "#59606e", roughness: 0.9 }));
  asfalto.rotation.x = -Math.PI / 2;
  asfalto.position.y = 0.01;
  asfalto.receiveShadow = true;
  g.add(asfalto);
  for (const r of [raio - larg / 2 - 0.25, raio + larg / 2 + 0.25]) {
    const zebra = new THREE.Mesh(new THREE.RingGeometry(r - 0.25, r + 0.25, 48, 1, 0, ang), new THREE.MeshStandardMaterial({ color: "#e8e8ea", roughness: 0.7 }));
    zebra.rotation.x = -Math.PI / 2;
    zebra.position.y = 0.012;
    g.add(zebra);
  }
  g.userData.curva = { raio, ang };
  (o.rotulos ?? []).forEach((txt, n, todos) => {
    const p = naCurva(g, todos.length === 1 ? 0.5 : n / (todos.length - 1));
    const s = rotulo(txt, { altura: 1.1 });
    s.position.set(p.x * 1.25, 1.2, p.z * 1.25);
    g.add(s);
  });
  return g;
}

/** Ponto e giro do carro na curva (f 0 = entrada, 0,5 = meio, 1 = saída): poe(w, k, p.x, p.z, p.giro). */
export function naCurva(curva: THREE.Object3D, f: number) {
  const { raio, ang } = curva.userData.curva as { raio: number; ang: number };
  curva.updateMatrixWorld(true);
  // RingGeometry deitado: o ângulo θ vai de +x para -z (rotation.x = -π/2 leva y da forma para -z do mundo)
  const th = ang * Math.max(0, Math.min(1, f));
  const local = new THREE.Vector3(Math.cos(th) * raio, 0, -Math.sin(th) * raio);
  const p = curva.localToWorld(local.clone());
  const dir = new THREE.Vector3(-Math.sin(th), 0, -Math.cos(th)).transformDirection(curva.matrixWorld);
  // esterço das rodas dianteiras para essa curva (entre-eixos 3,4 m; positivo = para a esquerda)
  return { x: p.x, z: p.z, giro: Math.atan2(-dir.x, -dir.z), esterco: Math.atan(3.4 / raio) };
}

/** Vira as rodas dianteiras do carro (radianos; positivo = para a esquerda), só neste quadro: na curva use naCurva(...).esterco. */
export function estercar(carro: THREE.Object3D, angulo: number) {
  for (const nome of ["roda_dianteira_esquerda", "roda_dianteira_direita"]) {
    const roda = achar(carro, nome)?.children[0];
    if (roda) girarPeca(roda, 0, Math.max(-0.6, Math.min(0.6, angulo)), 0);
  }
}