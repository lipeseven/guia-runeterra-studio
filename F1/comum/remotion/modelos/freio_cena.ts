// Ajudantes de cena para o freio (2026-11-12): calor com halo, termômetro 3D, medidor de faixa de temperatura (sem
// números: a faixa ideal muda com material, pista e equipe), partículas que correm por um caminho (ar no duto, energia
// até a bateria), ventilação do disco e o esquema do sistema híbrido de 2026 (MGU-K, bateria, eixo traseiro).
import * as THREE from "three";
import { achar, aoRestaurar, deslocar, peca } from "./desmonte";
import { brilho } from "./efeitos3d";
import { criarPiloto, obj, rotulo } from "./extras";
import { neutro } from "./boneco";
import { calorNosDiscos, corDoCalor, texFibra } from "./freio";
import { COCKPIT } from "./Carro3D";
import { CX, CY, PEGA, S, apertar, criarVolante, telaDoVolante } from "./volante";
import { ConvexGeometry } from "three/addons/geometries/ConvexGeometry.js";
import { Reflector } from "three/addons/objects/Reflector.js";
import { camera, type Mundo } from "./mundo";

/** Aquece os discos de `modelo` (freio solto ou carro) a `graus` °C, só neste quadro; com `w`, põe também o halo de luz
 *  em volta de cada disco (o brilho que se vê à noite). `quais` = nomes dos conjuntos do carro (ex.: ["freio_dianteiro_esquerdo"]). */
export function aquecer(modelo: THREE.Object3D, graus: number, w?: Mundo, quais?: string[], halo = 1) {
  calorNosDiscos(modelo, graus, quais);
  if (!w || halo <= 0) return;
  const { cor, forca } = corDoCalor(graus);
  if (forca <= 0) return;
  modelo.updateMatrixWorld(true);
  let n = 0;
  modelo.traverse((x) => {
    if (x.name !== "rotor") return;
    let p: THREE.Object3D | null = x;
    while (p && !(p.userData.peca && String(p.userData.peca).startsWith("freio_"))) p = p.parent;
    if (quais && p && !quais.includes(p.userData.peca)) return;
    const r = ((x.parent?.userData.raio as number) ?? 0.16) * x.getWorldScale(new THREE.Vector3()).x;
    // o halo fica ATRÁS do disco (longe da câmera): o disco o cobre e só a auréola aparece em volta. No centro, o plano do
    // sprite cortava a face na diagonal (meia face clara, meia escura)
    // (a câmera do quadro só existe no fim da cena: o recuo é feito na hora de desenhar, onBeforeRender)
    const c0 = x.getWorldPosition(new THREE.Vector3());
    const sp = brilho(w, `calor:${modelo.uuid}:${n++}`, c0, r * 5.2, Math.min(1, forca / 2.2) * 0.75 * halo, `#${cor.getHexString()}`);
    sp.userData.centro = [c0.x, c0.y, c0.z];
    sp.userData.recuo = r * 1.6;
    if (!sp.userData.atras) {
      sp.userData.atras = true;
      sp.onBeforeRender = (_r, _s, cam) => {
        const [cx, cy, cz] = sp.userData.centro as number[];
        const c = new THREE.Vector3(cx, cy, cz);
        sp.position.copy(c).add(c.clone().sub(cam.position).normalize().multiplyScalar(sp.userData.recuo as number));
        sp.updateMatrixWorld();
      };
    }
  });
}

// ---------------------------------------------------------------------------------------------------- partículas
let texPonto: THREE.CanvasTexture | null = null;
function ponto() {
  if (texPonto) return texPonto;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.4, "rgba(255,255,255,0.6)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 64, 64);
  texPonto = new THREE.CanvasTexture(c);
  return texPonto;
}
const sd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
type V3 = THREE.Vector3 | [number, number, number];
const v3 = (p: V3) => (Array.isArray(p) ? new THREE.Vector3(...p) : p.clone());

/** Partículas correndo por um caminho (pontos no MUNDO): ar entrando no duto, energia indo à bateria. `t` = c.t;
 *  `k` 0 a 1 = intensidade; n até 300; `vel` em voltas do caminho por segundo; `tam` em metros; `espalha` = raio do feixe. */
export function fluxo(w: Mundo, chave: string, pontos: V3[], t: number, k = 1, o: { n?: number; cor?: string; tam?: number; vel?: number; espalha?: number } = {}) {
  const N = Math.min(300, o.n ?? 80);
  const pts = obj(w, `fluxo:${chave}`, () => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(300 * 3), 3));
    const p = new THREE.Points(g, new THREE.PointsMaterial({ map: ponto(), size: 0.05, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: "#7fd8ff" }));
    p.frustumCulled = false;
    p.renderOrder = 24;
    return p;
  });
  const mat = pts.material as THREE.PointsMaterial;
  mat.color.set(o.cor ?? "#7fd8ff");
  mat.size = o.tam ?? 0.05;
  mat.opacity = Math.max(0, Math.min(1, k));
  const curva = new THREE.CatmullRomCurve3(pontos.map(v3));
  const esp = o.espalha ?? 0.02;
  const pos = pts.geometry.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < 300; i++) {
    if (i >= N) {
      pos.setXYZ(i, 0, -1e4, 0);
      continue;
    }
    const u = (sd(i) + t * (o.vel ?? 0.6) * (0.8 + sd(i + 9) * 0.4)) % 1;
    const p = curva.getPointAt(u);
    pos.setXYZ(i, p.x + (sd(i + 1) - 0.5) * esp * 2, p.y + (sd(i + 2) - 0.5) * esp * 2, p.z + (sd(i + 3) - 0.5) * esp * 2);
  }
  pos.needsUpdate = true;
  return pts;
}

/** Ar de refrigeração no freio solto (criarFreio com duto): entra pela boca, desce o duto até o sino e sai pela borda do
 *  disco, pelos canais. k 0 a 1 = intensidade. */
export function ventilar(w: Mundo, freio: THREE.Object3D, t: number, k = 1, cor = "#8fe3ff") {
  const ar = freio.userData.ar as [number, number, number][] | undefined;
  freio.updateMatrixWorld(true);
  const W = (x: number, y: number, z: number) => freio.localToWorld(new THREE.Vector3(x, y, z));
  const esc = freio.getWorldScale(new THREE.Vector3()).x;
  if (ar) fluxo(w, `ar:${freio.uuid}`, ar.map(([x, y, z]) => W(x, y, z)), t, k, { n: 70, cor, tam: 0.03 * esc, vel: 0.7, espalha: 0.018 * esc });
  // saída radial: do miolo para fora, em 10 raios girando com o tempo
  const r = (freio.userData.raio as number) ?? 0.16;
  const pts = obj(w, `arsai:${freio.uuid}`, () => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(160 * 3), 3));
    const p = new THREE.Points(g, new THREE.PointsMaterial({ map: ponto(), size: 0.03, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    p.frustumCulled = false;
    p.renderOrder = 24;
    return p;
  });
  const mt = pts.material as THREE.PointsMaterial;
  mt.color.set(cor);
  mt.size = 0.026 * esc;
  mt.opacity = Math.max(0, Math.min(1, k));
  const pos = pts.geometry.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < 160; i++) {
    const u = (sd(i) + t * 0.9) % 1;
    const a = sd(i + 4) * Math.PI * 2 + t * 1.5;
    const rr = r * (0.55 + u * 0.75);
    const p = W(Math.cos(a) * rr, Math.sin(a) * rr, (sd(i + 5) - 0.5) * 0.02);
    pos.setXYZ(i, p.x, p.y, p.z);
  }
  pos.needsUpdate = true;
}

// ---------------------------------------------------------------------------------------------------- instrumentos
/** Termômetro 3D (altura 1,2 m, de pé, frente +z): tubo de vidro, bulbo e coluna que sobe com a cor do calor; tracinhos a
 *  cada 200 °C (sem números); `marcas` = só os valores FALADOS, ex.: [{ graus: 1000, texto: "1.000 °C" }]. */
export function criarTermometro(o: { max?: number; marcas?: { graus: number; texto: string }[] } = {}) {
  const g = new THREE.Group();
  const max = o.max ?? 1200;
  const H = 1.2;
  const vidro = new THREE.MeshStandardMaterial({ color: "#dbe8ff", transparent: true, opacity: 0.28, roughness: 0.05, metalness: 0.1, depthWrite: false });
  const tubo = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, H, 8, 24), vidro);
  tubo.position.y = H / 2 + 0.14;
  tubo.renderOrder = 12;
  const bulbo = new THREE.Mesh(new THREE.SphereGeometry(0.13, 32, 20), vidro);
  bulbo.position.y = 0.13;
  bulbo.renderOrder = 12;
  const liquido = new THREE.MeshStandardMaterial({ color: "#ff4a1a", emissive: "#ff3a0a", emissiveIntensity: 0.9, roughness: 0.3 });
  const gota = new THREE.Mesh(new THREE.SphereGeometry(0.1, 28, 18), liquido);
  gota.position.y = 0.13;
  const col = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 20), liquido);
  col.name = "coluna";
  g.add(tubo, bulbo, gota, col);
  const traco = new THREE.MeshStandardMaterial({ color: "#f2f4f8", roughness: 0.4 });
  for (let v = 0; v <= max; v += 200) {
    const tr = new THREE.Mesh(new THREE.BoxGeometry(v % 400 === 0 ? 0.09 : 0.06, 0.012, 0.012), traco);
    tr.position.set(0.11, 0.26 + (v / max) * (H - 0.12), 0.02);
    g.add(tr);
  }
  for (const mk of o.marcas ?? []) {
    const y = 0.26 + (mk.graus / max) * (H - 0.12);
    const tr = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.02, 0.02), new THREE.MeshStandardMaterial({ color: "#ffd400", emissive: "#ffb000", emissiveIntensity: 0.6 }));
    tr.position.set(0.12, y, 0.02);
    g.add(tr);
    const r = rotulo(mk.texto, { altura: 0.16, cor: "#ffd400" });
    r.position.set(0, H + 0.42, 0.02); // em cima do tubo (ao lado saía cortado do quadro vertical)
    r.name = "marca";
    g.add(r);
  }
  g.userData.max = max;
  g.userData.H = H;
  return g;
}
/** Nível do termômetro (°C): a coluna sobe e ganha a cor do calor. */
export function medirTemperatura(term: THREE.Object3D, graus: number) {
  const col = term.getObjectByName("coluna") as THREE.Mesh | undefined;
  if (!col) return;
  const max = term.userData.max as number;
  const H = term.userData.H as number;
  const h = Math.max(0.02, (Math.max(0, Math.min(max, graus)) / max) * (H - 0.12)) + 0.13;
  col.scale.y = h;
  col.position.y = 0.13 + h / 2;
  const { cor } = corDoCalor(Math.max(700, graus));
  const m = col.material as THREE.MeshStandardMaterial;
  m.color.copy(cor);
  m.emissive.copy(cor);
}

/** Medidor da faixa de temperatura do freio (sem números): arco com FRIO (azul), faixa ADEQUADA (verde) e QUENTE
 *  (vermelho), ponteiro e miolo; frente +z, ~1,4 m de largura. `rotulos` = palavras faladas, ex.: ["FRIO", "ADEQUADA", "QUENTE"]. */
export function criarMedidorTermico(o: { rotulos?: string[] } = {}) {
  const g = new THREE.Group();
  const cores = ["#2f8cff", "#27c46b", "#ff3b2f"];
  const R = 0.7;
  for (let z = 0; z < 3; z++) {
    const a0 = Math.PI - (z / 3) * Math.PI;
    const a1 = Math.PI - ((z + 1) / 3) * Math.PI;
    const s = new THREE.Shape();
    s.absarc(0, 0, R, a1 + 0.012, a0 - 0.012, false);
    s.absarc(0, 0, R * 0.74, a0 - 0.012, a1 + 0.012, true);
    const m = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.05, bevelEnabled: false, curveSegments: 32 }), new THREE.MeshStandardMaterial({ color: cores[z], emissive: cores[z], emissiveIntensity: 0.25, roughness: 0.4 }));
    m.name = `zona${z}`;
    g.add(m);
    const txt = o.rotulos?.[z];
    if (txt) {
      const a = (a0 + a1) / 2;
      const r = rotulo(txt, { altura: 0.13, cor: "#ffffff", fundo: "rgba(12,16,28,0.86)" });
      r.position.set(Math.cos(a) * R * 1.27, Math.sin(a) * R * 1.27 + 0.03, 0.06);
      r.name = `rotulo${z}`;
      g.add(r);
    }
  }
  const fundo = new THREE.Mesh(new THREE.CircleGeometry(R * 1.08, 48, 0, Math.PI), new THREE.MeshStandardMaterial({ color: "#121a2c", roughness: 0.6 }));
  fundo.position.z = -0.01;
  g.add(fundo);
  const agulha = new THREE.Group();
  agulha.name = "agulha";
  const ag = new THREE.Mesh(new THREE.BoxGeometry(R * 0.86, 0.035, 0.03), new THREE.MeshStandardMaterial({ color: "#ffd400", emissive: "#ffb000", emissiveIntensity: 0.7 }));
  ag.position.x = R * 0.43;
  agulha.add(ag);
  agulha.position.z = 0.08;
  g.add(agulha);
  const miolo = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.06, 24), new THREE.MeshStandardMaterial({ color: "#e8ecf2", roughness: 0.3, metalness: 0.6 }));
  miolo.rotation.x = Math.PI / 2;
  miolo.position.z = 0.09;
  g.add(miolo);
  return g;
}
/** Ponteiro do medidor: k 0 = frio (esquerda), 0,5 = meio da faixa adequada, 1 = quente (direita). A zona do ponteiro acende. */
export function ponteiro(med: THREE.Object3D, k: number) {
  const a = Math.PI * (1 - Math.max(0, Math.min(1, k)));
  const ag = med.getObjectByName("agulha");
  if (ag) ag.rotation.z = a;
  const zona = Math.min(2, Math.floor(Math.max(0, Math.min(0.999, k)) * 3));
  for (let z = 0; z < 3; z++) {
    const m = med.getObjectByName(`zona${z}`) as THREE.Mesh | undefined;
    if (m) (m.material as THREE.MeshStandardMaterial).emissiveIntensity = z === zona ? 1.1 : 0.12;
    const r = med.getObjectByName(`rotulo${z}`) as THREE.Sprite | undefined;
    if (r) (r.material as THREE.SpriteMaterial).opacity = z === zona ? 1 : 0.4;
  }
}

/** Placa de material de carbono trançado (close do material dos discos e pastilhas), 0,6 x 0,4 x 0,03 m. */
export function criarPlacaCarbono() {
  const t = texFibra().clone();
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(3, 2);
  t.needsUpdate = true;
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.4, 0.03), new THREE.MeshStandardMaterial({ map: t, roughness: 0.35, metalness: 0.25 }));
  return m;
}

// ---------------------------------------------------------------------------------------------------- híbrido 2026
/** Esquema do sistema híbrido de 2026 no espaço do CARRO (ponha na mesma posição/giro do carro: `poeHibrido`): motor a
 *  combustão (bloco vermelho), MGU-K (cilindro verde ao lado do motor), bateria (caixa azul sob o tanque), câmbio e eixo
 *  traseiro, cabos laranja de alta tensão. Peças: motor, mgu_k, bateria, cambio, eixo_traseiro. Use com
 *  raioX(carro, ["tampa_do_motor", "monocoque", "sidepod_esquerda", "sidepod_direita"]) para enxergar. */
export function criarHibrido() {
  const g = new THREE.Group();
  const M = (cor: string, emis = 0, metal = 0.5) => new THREE.MeshStandardMaterial({ color: cor, emissive: cor, emissiveIntensity: emis, roughness: 0.4, metalness: metal });
  const bloco = peca(new THREE.Group(), "motor", [0, 0.5, 0], 0);
  const mb = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.36, 0.62), M("#c8452c", 0.2, 0.3));
  mb.position.set(0, 0.38, 1.05);
  bloco.add(mb);
  const mgu = peca(new THREE.Group(), "mgu_k", [-0.4, 0.2, 0], 0);
  const cil = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.085, 0.24, 32), M("#2fc46b", 0.25, 0.3));
  cil.rotation.x = Math.PI / 2;
  cil.position.set(-0.27, 0.26, 0.82);
  mgu.add(cil);
  const bat = peca(new THREE.Group(), "bateria", [0, -0.2, 0], 0);
  const bb = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.12, 0.36), M("#1f6fe0", 0.35, 0.3));
  bb.position.set(0, 0.16, 0.42);
  bat.add(bb);
  const camb = peca(new THREE.Group(), "cambio", [0, 0.3, 0.3], 0);
  const cb = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.22, 0.5), M("#4b505b", 0, 0.6));
  cb.position.set(0, 0.32, 1.62);
  camb.add(cb);
  const eixo = peca(new THREE.Group(), "eixo_traseiro", [0, 0, 0], 0);
  const ex = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 1.42, 16), M("#9aa1ad", 0, 0.8));
  ex.rotation.z = Math.PI / 2;
  ex.position.set(0, 0.36, 1.85);
  eixo.add(ex);
  const cabo = M("#ff7a1a", 0.35, 0.2);
  const c1 = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.27, 0.26, 0.7), new THREE.Vector3(-0.24, 0.2, 0.6), new THREE.Vector3(-0.16, 0.18, 0.54)]);
  const ca = new THREE.Mesh(new THREE.TubeGeometry(c1, 16, 0.014, 8), cabo);
  mgu.add(ca);
  g.add(bloco, mgu, bat, camb, eixo);
  return g;
}
/** Põe o esquema híbrido no carro (mesma posição, giro e escala) e devolve o grupo. */
export function poeHibrido(w: Mundo, car: THREE.Object3D, chave = "hibrido") {
  const h = obj(w, chave, () => criarHibrido());
  car.updateMatrixWorld(true);
  h.position.copy(car.position);
  h.quaternion.copy(car.quaternion);
  h.scale.copy(car.scale);
  h.updateMatrixWorld(true);
  return h;
}
/** Pontos do caminho da energia na frenagem (no mundo): rodas traseiras → eixo → câmbio → MGU-K → bateria. Use com `fluxo`. */
export function caminhoDaEnergia(h: THREE.Object3D, lado: -1 | 1 = -1) {
  h.updateMatrixWorld(true);
  const W = (x: number, y: number, z: number) => h.localToWorld(new THREE.Vector3(x, y, z));
  return [W(lado * 0.7, 0.36, 1.85), W(lado * 0.3, 0.36, 1.85), W(0, 0.34, 1.7), W(-0.1, 0.33, 1.3), W(-0.27, 0.27, 0.95), W(-0.27, 0.24, 0.72), W(-0.12, 0.17, 0.5), W(0, 0.16, 0.42)];
}

/** Centro (no mundo) do disco de uma roda do carro: "dianteiro_esquerdo", "dianteiro_direito", "traseiro_esquerdo",
 *  "traseiro_direito". Para mirar a câmera e pôr `brilho`. */
export function noFreio(car: THREE.Object3D, roda: string) {
  car.updateMatrixWorld(true);
  let alvo: THREE.Object3D | null = null;
  car.traverse((o) => {
    if (!alvo && o.userData.peca === `freio_${roda}`) alvo = o;
  });
  const r = (alvo as THREE.Object3D | null)?.getObjectByName("rotor");
  return r ? r.getWorldPosition(new THREE.Vector3()) : car.getWorldPosition(new THREE.Vector3());
}

/** Escurece a tela INTEIRA por igual (gancho de abertura com texto por cima): k 0 a 1 = opacidade do preto (0,45 é bom).
 *  É um vidro preto colado na frente da câmera: todos os pixels escurecem igual, sem faixa nem degradê. Chame depois da câmera. */
export function escurecer(w: Mundo, k: number) {
  const v = obj(w, "escurecer", () => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: "#000000", transparent: true, depthTest: false, depthWrite: false, fog: false }));
    m.renderOrder = 999;
    m.frustumCulled = false;
    return m;
  });
  const cam = w.cam as THREE.PerspectiveCamera;
  cam.updateMatrixWorld(true);
  const d = Math.max(cam.near * 2, 0.05);
  const h = 2 * d * Math.tan(((cam.fov * Math.PI) / 180) / 2) * 1.2;
  v.position.copy(cam.position).add(cam.getWorldDirection(new THREE.Vector3()).multiplyScalar(d));
  v.quaternion.copy(cam.quaternion);
  v.scale.set(h * cam.aspect * 1.2, h, 1);
  (v.material as THREE.MeshBasicMaterial).opacity = Math.max(0, Math.min(1, k));
}

/** Tomada de ar do freio de uma roda do carro maior ou menor só neste quadro ("mais refrigeração" x aerodinâmica).
 *  roda = "dianteiro_esquerdo" etc.; escala 1 = normal. Devolve o centro da boca no mundo. */
export function tomadaDeAr(car: THREE.Object3D, roda: string, escala = 1) {
  let t: THREE.Object3D | null = null;
  car.traverse((o) => {
    if (!t && o.userData.peca === `tomada_${roda}`) t = o;
  });
  if (!t) return car.getWorldPosition(new THREE.Vector3());
  const tom = t as THREE.Object3D;
  if (escala !== 1) deslocar(tom, new THREE.Vector3(0, 0, 0), escala);
  car.updateMatrixWorld(true);
  const b = (tom.userData.boca as number[]) ?? [0, 0, 0];
  return tom.localToWorld(new THREE.Vector3(b[0], b[1], b[2]));
}

// ---------------------------------------------------------------------------------------------------- pedais e piloto
// F1 de hoje: SÓ dois pedais (embreagem é paddle no volante): acelerador à DIREITA e freio à ESQUERDA, mais largo,
// pisado com o pé ESQUERDO (frenagem com o pé esquerdo; f1chronicle.com "How Formula 1 Pedals Work", flowracers.com,
// conferido em 2026-11-13). Pedais presos embaixo (pivô no assoalho do bico), sapata alta; atrás do pedal de freio,
// dois cilindros-mestres (dianteiro e traseiro) e as linhas de freio até as pinças. Medidas no espaço do CARRO (frente -z).
const PIVO_Z = -1.34, PIVO_Y = 0.1, BRACO = 0.2, INCL = 0.32; // pedal inclinado para trás (para o piloto) em repouso
const X_FREIO = -0.088, X_ACEL = 0.088;

/** Pedais, cilindros-mestres e linhas de freio no espaço do carro (ponha com `poePedais`). Peças: pedal_freio,
 *  pedal_acelerador, cilindros, linhas_freio. */
export function criarPedais() {
  const g = new THREE.Group();
  const metal = new THREE.MeshStandardMaterial({ color: "#b9bec7", roughness: 0.3, metalness: 0.8 });
  const sapata = new THREE.MeshStandardMaterial({ color: "#2a2d33", roughness: 0.6, metalness: 0.4 });
  const mk = (nome: string, x: number, larg: number) => {
    const p = peca(new THREE.Group(), nome, [0, 0.2, 0], 0);
    p.name = nome;
    p.position.set(x, PIVO_Y, PIVO_Z);
    p.rotation.x = INCL; // sapata inclinada para trás, para o pé do piloto
    const braco = new THREE.Mesh(new THREE.BoxGeometry(0.022, BRACO, 0.022), metal);
    braco.position.y = BRACO / 2;
    const pad = new THREE.Mesh(new THREE.BoxGeometry(larg, 0.11, 0.018), sapata);
    pad.position.set(0, BRACO, -0.012);
    p.add(braco, pad);
    g.add(p);
    return p;
  };
  mk("pedal_freio", X_FREIO, 0.1);
  mk("pedal_acelerador", X_ACEL, 0.065);
  // dois cilindros-mestres à frente do pedal de freio (empurrados por uma haste)
  const cil = peca(new THREE.Group(), "cilindros", [0, 0.25, -0.2], 0);
  for (const dx of [-0.025, 0.025]) {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.1, 16), metal);
    c.rotation.x = Math.PI / 2;
    c.position.set(X_FREIO + dx, 0.23, PIVO_Z - 0.17);
    cil.add(c);
  }
  g.add(cil);
  // linhas de freio (tubos finos laranja): cilindro → pinça de cada roda
  const lin = peca(new THREE.Group(), "linhas_freio", [0, 0.3, 0], 0);
  const mat = new THREE.MeshStandardMaterial({ color: "#ff8a2a", emissive: "#ff5a00", emissiveIntensity: 0.25, roughness: 0.4 });
  for (const pts of caminhosLocais()) lin.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 40, 0.006, 6), mat));
  g.add(lin);
  return g;
}
/** Caminhos das linhas no espaço do carro: [dianteiro_esquerdo, dianteiro_direito, traseiro_esquerdo, traseiro_direito]. */
function caminhosLocais() {
  const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
  const ini = V(X_FREIO, 0.23, PIVO_Z - 0.23);
  return [
    [ini, V(-0.2, 0.25, -1.6), V(-0.5, 0.3, -1.6), V(-0.66, 0.3, -1.5)],
    [ini, V(0.1, 0.25, -1.62), V(0.5, 0.3, -1.6), V(0.66, 0.3, -1.5)],
    [ini, V(-0.12, 0.14, -1.0), V(-0.18, 0.12, 0.6), V(-0.4, 0.25, 1.75), V(-0.6, 0.3, 1.9)],
    [ini, V(-0.05, 0.14, -1.0), V(0.18, 0.12, 0.6), V(0.4, 0.25, 1.75), V(0.6, 0.3, 1.9)],
  ];
}
const RODAS_LINHA = ["dianteiro_esquerdo", "dianteiro_direito", "traseiro_esquerdo", "traseiro_direito"];
/** Põe os pedais no carro (mesma posição e giro) e afunda o pedal de freio: k 0 solto, 1 no fundo (~17°). */
export function poePedais(w: Mundo, car: THREE.Object3D, k = 0, chave = "pedais") {
  const p = obj(w, chave, () => criarPedais());
  car.updateMatrixWorld(true);
  p.position.copy(car.position);
  p.quaternion.copy(car.quaternion);
  p.scale.copy(car.scale);
  const f = p.getObjectByName("pedal_freio");
  if (f) f.rotation.x = INCL - 0.3 * Math.max(0, Math.min(1, k)); // pisar = a sapata vai para a frente
  p.updateMatrixWorld(true);
  return p;
}
/** Caminho da pressão do freio no mundo (cilindro-mestre → pinça da roda), para `fluxo`. roda = "dianteiro_esquerdo" etc. */
export function linhaDoFreio(pedais: THREE.Object3D, roda: string) {
  pedais.updateMatrixWorld(true);
  const pts = caminhosLocais()[Math.max(0, RODAS_LINHA.indexOf(roda))];
  return pts.map((q) => pedais.localToWorld(q.clone()));
}

// esconde o piloto simples do carro (capacete/ombros/volante fixos) só neste quadro: o boneco articulado entra no lugar
const cabecasEscondidas = new Set<THREE.Object3D>();
let restauraCabecas = false;
const fixosEscondidos = new Set<THREE.Object3D>();
let restauraFixos = false;
function esconderPilotoFixo(car: THREE.Object3D) {
  const f = car.getObjectByName("piloto_fixo");
  if (!f) return;
  f.visible = false;
  fixosEscondidos.add(f);
  if (!restauraFixos) {
    restauraFixos = true;
    aoRestaurar(() => {
      fixosEscondidos.forEach((x) => (x.visible = true));
      fixosEscondidos.clear();
    });
  }
}
const noCarro = (car: THREE.Object3D, p: readonly number[]) => car.localToWorld(new THREE.Vector3(p[0], p[1], p[2]));

/** Volante de verdade (criarVolante, ~29 cm) montado na coluna do cockpit, na posição de COCKPIT.volante (diante do
 *  peito do piloto, topo inclinado para ele). Devolve o volante (apertar, girar, telaDoVolante funcionam nele). */
export function poeVolanteNoCarro(w: Mundo, car: THREE.Object3D, chave = "volante:cockpit", giro = 0) {
  const v = obj(w, chave, () => criarVolante());
  car.updateMatrixWorld(true);
  v.position.copy(noCarro(car, COCKPIT.volante.pos));
  // `giro` (rad, positivo = virar à esquerda): gira no próprio eixo (a face olha para o piloto, +z do volante)
  v.quaternion.copy(car.quaternion).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), COCKPIT.volante.incl)).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), giro));
  v.scale.setScalar(car.scale.x);
  // v9: sem segunda coluna de direção. O volante já traz a coluna dele (peça "engate_rapido"); com o volante
  // reposicionado na v8 as duas saíam em ângulos diferentes ("uma barra brilhando e uma segunda barra preta").
  v.updateMatrixWorld(true);
  return v;
}

/** Aponta o osso (o filho fica em `local` = [0, -L, 0]) para o ponto `alvo` do mundo. */
function apontarOsso(osso: THREE.Object3D, alvo: THREE.Vector3) {
  osso.updateMatrixWorld(true);
  const o = osso.getWorldPosition(new THREE.Vector3());
  const qw = osso.getWorldQuaternion(new THREE.Quaternion());
  const atual = new THREE.Vector3(0, -1, 0).applyQuaternion(qw);
  const quer = alvo.clone().sub(o).normalize();
  const nova = new THREE.Quaternion().setFromUnitVectors(atual, quer).multiply(qw);
  const qp = osso.parent!.getWorldQuaternion(new THREE.Quaternion());
  osso.quaternion.copy(qp.invert().multiply(nova));
  osso.updateMatrixWorld(true);
}

/** Braço por IK (braço 0,29 m, antebraço+mão 0,30 m): a mão vai até `mao` e o cotovelo dobra para `polo`. */
function braco(j: Record<string, THREE.Object3D>, l: "E" | "D", mao: THREE.Vector3, polo: THREE.Vector3, escala: number) {
  const A = 0.29 * escala, B = 0.3 * escala;
  const s = j[`ombro${l}`].getWorldPosition(new THREE.Vector3());
  const d = mao.clone().sub(s);
  const D = Math.min(A + B - 1e-4, d.length());
  const u = d.clone().normalize();
  const v = polo.clone().sub(u.clone().multiplyScalar(polo.dot(u))).normalize();
  const al = Math.acos(Math.max(-1, Math.min(1, (A * A + D * D - B * B) / (2 * A * D))));
  const cot = s.clone().addScaledVector(u, A * Math.cos(al)).addScaledVector(v, A * Math.sin(al));
  apontarOsso(j[`ombro${l}`], cot);
  apontarOsso(j[`cotovelo${l}`], mao);
}

/** Piloto articulado sentado no cockpit (reclinado ~50°, mãos nas empunhaduras do volante, cotovelos dobrados para baixo
 *  e para fora) com o pé ESQUERDO no pedal de freio. Braços e pernas por IK: mãos no volante (que entra junto, na
 *  coluna: `o.volante = false` tira), perna esquerda até a sapata do pedal (coxa 0,43 m, canela 0,40 m); `k` = quanto o
 *  pedal afunda (o mesmo de `poePedais`). O pé direito fica apoiado no acelerador, solto. O piloto simples do carro
 *  some neste quadro. Com o carro opaco, só o capacete e o alto dos ombros aparecem (como no carro de verdade); para
 *  ver o corpo, raioX do monocoque/tampa/sidepods. O volante fica em `p.userData.volante`. */
export function poePilotoNoCarro(w: Mundo, car: THREE.Object3D, k = 0, o: { chave?: string; volante?: boolean; giro?: number; semCabeca?: boolean; cores?: { macacao?: string; detalhe?: string; faixa?: string; capacete?: string } } = {}) {
  const p = obj(w, o.chave ?? "piloto:cockpit", () => criarPiloto({ traje: "capacete", macacao: o.cores?.macacao ?? "#1d3f9e", detalhe: o.cores?.detalhe ?? "#f2c232", faixa: o.cores?.faixa ?? "#f2c232", capacete: o.cores?.capacete ?? "#f5c518" }));
  neutro(p);
  const j = p.userData.juntas as Record<string, THREE.Object3D>;
  const QUADRIL = COCKPIT.quadril; // quadril no assento (espaço do carro), cabeça cai no lugar do capacete
  car.updateMatrixWorld(true);
  esconderPilotoFixo(car);
  p.position.copy(car.localToWorld(new THREE.Vector3(0, QUADRIL.y - 0.92, QUADRIL.z)));
  p.quaternion.copy(car.quaternion);
  p.rotateY(Math.PI); // o boneco olha para +z; o carro anda para -z
  p.scale.setScalar(car.scale.x);
  j.coluna.rotation.x = 0.915; // tronco reclinado para trás (~52° da vertical): ombros abaixo da borda da abertura
  j.pescoco.rotation.x = -0.75; // queixo para baixo: olhando para a frente, por cima do volante
  // ombros mais juntos que no boneco de pé (a abertura tem ~47 cm de largura; ombros de piloto ~40-45 cm)
  j.ombroE.position.x = -0.165;
  j.ombroD.position.x = 0.165;
  const vol = o.volante === false ? null : poeVolanteNoCarro(w, car, (o.chave ?? "piloto:cockpit") + ":volante", o.giro ?? 0);
  // POV mais afastado: a câmera fica atrás dos olhos, então a cabeça some neste quadro (senão tamparia a vista)
  const cab = j.pescoco;
  cab.visible = !o.semCabeca;
  if (o.semCabeca) {
    cabecasEscondidas.add(cab);
    if (!restauraCabecas) {
      restauraCabecas = true;
      aoRestaurar(() => {
        cabecasEscondidas.forEach((x) => (x.visible = true));
        cabecasEscondidas.clear();
      });
    }
  }
  p.userData.volante = vol;
  p.updateMatrixWorld(true);
  // mãos nas empunhaduras (lados do volante, atrás da face), cotovelos para baixo e um pouco para fora
  const [vx, vy, vz] = COCKPIT.volante.pos;
  const inc = COCKPIT.volante.incl;
  for (const l of ["E", "D"] as const) {
    const s = l === "E" ? -1 : 1;
    // v11: a mão é filha do volante (dedos fechados no cabo, criarMaoNoVolante); o braço vai ao pulso por IK e a mão do
    // boneco some (o punho azul com faixa amarela é orientado pelo antebraço)
    if (vol) {
      vol.updateMatrixWorld(true);
      let mao = vol.getObjectByName(s < 0 ? "mao_E" : "mao_D");
      if (!mao) {
        mao = criarMaoNoVolante(s, new THREE.MeshStandardMaterial({ color: "#eceef2", roughness: 0.7 }), new THREE.MeshStandardMaterial({ color: o.cores?.macacao ?? "#1d3f9e", roughness: 0.9 }), new THREE.MeshStandardMaterial({ color: o.cores?.faixa ?? "#f2c232", roughness: 0.8 }));
        vol.add(mao);
      }
      mao.visible = true;
      const [px, py, pz] = mao.userData.pulso as number[];
      const pulsoW = vol.localToWorld(new THREE.Vector3(px, py, pz));
      const ombro = j[`ombro${l}`].getWorldPosition(new THREE.Vector3());
      const alvo = pulsoW.clone().addScaledVector(pulsoW.clone().sub(ombro).normalize(), 0.05 * car.scale.x); // a IK mira 5 cm além do pulso
      const polo = new THREE.Vector3(s * 0.35, -1, 0.25).applyQuaternion(car.quaternion);
      braco(j, l, alvo, polo, car.scale.x);
      j[`pulso${l}`].visible = false;
      // manga: do pulso para o cotovelo
      const cot = j[`cotovelo${l}`].getWorldPosition(new THREE.Vector3());
      const dir = vol.worldToLocal(cot.clone()).sub(new THREE.Vector3(px, py, pz)).normalize();
      mao.getObjectByName("punho")!.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir);
    } else {
      const mao = noCarro(car, [vx + s * 0.122, vy - 0.012 * Math.cos(inc) - 0.035 * Math.sin(inc), vz - 0.012 * Math.sin(inc) + 0.035 * Math.cos(inc)]);
      const polo = new THREE.Vector3(s * 0.55, -1, 0.2).applyQuaternion(car.quaternion);
      braco(j, l, mao, polo, car.scale.x);
      j[`pulso${l}`].rotation.set(0, 0, 0);
    }
  }
  // pernas: IK no plano de lado (w = para a frente do carro = -z, y = altura)
  const COXA = 0.43, CANELA = 0.4;
  const ik = (l: "E" | "D", padW: number, padY: number) => {
    const f = Math.PI - 0.42; // pé apontando para cima e um pouco para a frente (sola na sapata)
    const dW = Math.sin(f), dY = -Math.cos(f);
    const nW = -dY, nY = dW; // normal da sola (para a frente)
    // tornozelo = sapata - meia espessura da bota (normal) - um pouco ao longo do pé
    const aW = padW - 0.065 * nW - 0.06 * dW, aY = padY - 0.065 * nY - 0.06 * dY;
    const hW = -QUADRIL.z, hY = QUADRIL.y;
    const DW = aW - hW, DY = aY - hY;
    const D = Math.min(COXA + CANELA - 1e-4, Math.hypot(DW, DY));
    const phi = Math.atan2(DW, -DY); // ângulo a partir de "para baixo"
    const alfa = Math.acos((COXA * COXA + D * D - CANELA * CANELA) / (2 * COXA * D));
    const beta = Math.acos((COXA * COXA + CANELA * CANELA - D * D) / (2 * COXA * CANELA));
    const a = phi + alfa; // joelho para cima
    const b = -(Math.PI - beta);
    j[`quadril${l}`].rotation.x = a;
    j[`joelho${l}`].rotation.x = b;
    j[`tornozelo${l}`].rotation.x = f - Math.PI / 2 - (a + b);
  };
  const pad = (ang: number) => ({ w: -PIVO_Z - Math.sin(ang) * BRACO, y: PIVO_Y + Math.cos(ang) * BRACO });
  const fr = pad(INCL - 0.3 * Math.max(0, Math.min(1, k)));
  const ac = pad(INCL);
  ik("E", fr.w, fr.y);
  ik("D", ac.w - 0.03, ac.y); // pé direito encostado no acelerador, sem pisar
  p.updateMatrixWorld(true);
  cintoEmX(w, car, p, o.chave ?? "piloto:cockpit");
  return p;
}

/** Cinto de 6 pontos (arnês) cruzado em X sobre o peito, faixas largas pretas com fivela central prata, presas ao banco;
 *  pedido do Felipe (2026-11-18): "o cinto em X cruzado, branco ou preto". Feito a cada quadro sobre o boneco reclinado. */
function cintoEmX(w: Mundo, car: THREE.Object3D, p: THREE.Object3D, chave: string) {
  // v7 (Felipe: "o cinto está atravessando nosso piloto quando devia passar por cima dos ombros"): o arnês é preso ao
  // TRONCO do boneco (filho do grupo "corpo", que reclina com a coluna) e segue o perfil do macacão por fora: duas alças
  // descem de trás do banco, passam por cima dos ombros e descem pelo peito até a fivela; mais o cinto pélvico.
  const j = p.userData.juntas as Record<string, THREE.Object3D>;
  const corpo = j.coluna.children[0];
  if (!corpo.getObjectByName("arnes")) corpo.add(criarArnes());
  return;
  // (o X antigo abaixo não é mais usado)
  const pos = (o: THREE.Object3D) => o.getWorldPosition(new THREE.Vector3());
  const frente = new THREE.Vector3(0, Math.sin(0.915), -Math.cos(0.915)).applyQuaternion(car.quaternion); // normal do peito
  const esc = car.scale.x;
  const oE = pos(j.ombroE), oD = pos(j.ombroD), qE = pos(j.quadrilE), qD = pos(j.quadrilD);
  const f = (v: THREE.Vector3, d: number) => v.clone().addScaledVector(frente, d * esc);
  const centro = f(oE.clone().add(oD).add(qE).add(qD).multiplyScalar(0.25), 0.115);
  const faixa = (n: string, a: THREE.Vector3, b: THREE.Vector3, larg: number) => {
    const m = obj(w, `${chave}:cinto:${n}`, () => new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: "#111216", roughness: 0.7 })));
    m.position.copy(a).add(b).multiplyScalar(0.5);
    const dir = b.clone().sub(a);
    // base: y ao longo da faixa, z = normal do peito (a faixa fica deitada sobre o macacão), x = largura
    const ey = dir.clone().normalize();
    const ez = frente.clone().addScaledVector(ey, -frente.dot(ey)).normalize();
    const ex = new THREE.Vector3().crossVectors(ey, ez);
    m.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(ex, ey, ez));
    m.scale.set(larg * esc, dir.length(), 0.008 * esc);
  };
  // ombro esquerdo -> quadril direito e ombro direito -> quadril esquerdo (o X), mais a faixa da cintura
  faixa("x1", f(oE, 0.1), f(qD, 0.11), 0.06);
  faixa("x2", f(oD, 0.1), f(qE, 0.11), 0.06);
  faixa("cintura", f(qE.clone().lerp(qD, -0.35), 0.12), f(qE.clone().lerp(qD, 1.35), 0.12), 0.055);
  const fivela = obj(w, `${chave}:cinto:fivela`, () => new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.015, 24), new THREE.MeshStandardMaterial({ color: "#d9dde3", metalness: 0.85, roughness: 0.25 })));
  fivela.position.copy(f(centro, 0.012));
  fivela.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), frente);
  fivela.scale.setScalar(esc);
}

/** Arnês no espaço do tronco do boneco (y para cima, frente -z; perfil do tronco em extras.ts, escala z 0,66). */
function criarArnes() {
  const g = new THREE.Group();
  g.name = "arnes";
  const mat = new THREE.MeshStandardMaterial({ color: "#f1f2f4", roughness: 0.6, side: THREE.DoubleSide }); // faixas brancas: legíveis sobre o macacão
  // raio do tronco na altura y (o mesmo perfil do LatheGeometry), profundidade = raio * 0,66
  const perfil = [[0, 0.88], [0.15, 0.89], [0.163, 0.96], [0.148, 1.05], [0.152, 1.14], [0.18, 1.27], [0.186, 1.35], [0.16, 1.43], [0.09, 1.48], [0.062, 1.5]];
  const raio = (y: number) => {
    for (let i = 1; i < perfil.length; i++) if (y <= perfil[i][1]) {
      const [r0, y0] = perfil[i - 1], [r1, y1] = perfil[i];
      return r0 + ((r1 - r0) * (y - y0)) / (y1 - y0);
    }
    return 0.062;
  };
  // ponto na superfície do tronco (elipse r x 0,66r) na altura y, a x do centro, de frente (-1) ou de costas (+1)
  const sup = (x: number, y: number, lado: -1 | 1, folga = 0.012) => {
    const r = raio(y) + folga;
    const zz = 0.66 * r * Math.sqrt(Math.max(0, 1 - (x / r) ** 2));
    return new THREE.Vector3(x, y, lado * zz);
  };
  // v8 ("tem que ser uma faixa claramente visível, não essa linha medonha"): fita larga deitada sobre o macacão; a
  // largura fica na tangente da superfície (perpendicular à direção da fita e à normal, que sai do eixo do tronco)
  const tira = (pts: THREE.Vector3[], larg: number) => {
    const curva = new THREE.CatmullRomCurve3(pts);
    const N = 60;
    const pos: number[] = [];
    const ind: number[] = [];
    for (let i = 0; i <= N; i++) {
      const u = i / N;
      const pt = curva.getPointAt(u);
      const tg = curva.getTangentAt(u);
      const nrm = new THREE.Vector3(pt.x, 0, pt.z / 0.66);
      if (Math.abs(pt.y - 1.5) < 0.04 || nrm.length() < 1e-3) nrm.set(0, 1, 0); // em cima do ombro: normal para cima
      nrm.normalize();
      const lat = new THREE.Vector3().crossVectors(tg, nrm).normalize().multiplyScalar(larg / 2);
      pos.push(pt.x + lat.x, pt.y + lat.y, pt.z + lat.z, pt.x - lat.x, pt.y - lat.y, pt.z - lat.z);
      if (i < N) ind.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 2, i * 2 + 1, i * 2 + 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setIndex(ind);
    geo.computeVertexNormals();
    return new THREE.Mesh(geo, mat);
  };
  for (const s of [-1, 1]) {
    const x = s * 0.075;
    // de trás (encosto), por cima do ombro (perto do pescoço), descendo pelo peito até a fivela
    const pts = [sup(x * 1.1, 1.22, 1, 0.02), sup(x * 1.05, 1.4, 1, 0.02), new THREE.Vector3(x, 1.5, 0), sup(x, 1.4, -1), sup(x * 0.9, 1.27, -1), sup(x * 0.6, 1.12, -1), sup(s * 0.025, 0.99, -1)];
    g.add(tira(pts, 0.075));
  }
  // cinto pélvico: de um quadril ao outro pela frente, passando pela fivela
  const pel: THREE.Vector3[] = [];
  for (let k = 0; k <= 8; k++) {
    const x = -0.16 + (0.32 * k) / 8;
    pel.push(sup(x, 0.97, -1, 0.014));
  }
  g.add(tira(pel, 0.08));
  const fivela = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.014, 24), new THREE.MeshStandardMaterial({ color: "#d9dde3", metalness: 0.85, roughness: 0.25 }));
  fivela.rotation.x = Math.PI / 2;
  fivela.position.copy(sup(0, 0.99, -1, 0.026));
  g.add(fivela);
  g.traverse((o) => (o.castShadow = true));
  return g;
}

/** Marcha de um F1 de 2026 (8 marchas) pela velocidade em km/h: reta = 7ª/8ª, curva lenta = 2ª-4ª. */
export function marchaDe(kmh: number) {
  const lim = [85, 115, 145, 175, 210, 245, 285];
  return 1 + lim.filter((x) => kmh > x).length;
}

/** Piloto no carro andando na pista: volante gira com o esterço das rodas (`q` = o que poeNoCircuito devolve) e a tela
 *  mostra a marcha e a velocidade coerentes com `v` (m/s). `semCabeca` para a câmera "pov". Devolve o piloto. */
export function cockpitNaPista(w: Mundo, car: THREE.Object3D, q: { esterco: number }, v: number, o: { semCabeca?: boolean } = {}) {
  const giro = Math.max(-1.0, Math.min(1.0, q.esterco * 4)); // volante de F1: até ~±60° nos grampos (as mãos ficam nas empunhaduras)
  const p = poePilotoNoCarro(w, car, 0, { giro, semCabeca: o.semCabeca });
  const kmh = v * 3.6;
  if (p.userData.volante) telaDoVolante(p.userData.volante, { marcha: String(marchaDe(kmh)), velocidade: Math.round(kmh) });
  return p;
}

// ------------------------------------------------------------------------------------------------ câmeras do cockpit
type Ponto = readonly [number, number, number];
/** Tomadas prontas do cockpit, no espaço do carro (frente -z): [de onde, para onde, lente]. Conferidas em quadros
 *  com poePilotoNoCarro (2026-11-17). */
const TOMADAS: Record<string, [Ponto, Ponto, number]> = {
  piloto: [COCKPIT.olhos, [0, 0.28, -5], 74], // visão do piloto: topo do volante embaixo, halo e pilar central, a pista
  // POV um pouco afastado (atrás dos olhos, cabeça escondida: cockpitNaPista(..., { semCabeca: true })): mãos no volante,
  // halo, bico e a pista (v6, pedido do Felipe)
  pov: [[0, 0.92, 0.04], [0, 0.42, -5], 72],
  // v7 (Felipe, ref. onboard do Leclerc): olhos ABAIXO do arco do halo, câmera na espuma ao lado do capacete
  olhos: [[0, 0.715, -0.17], [0, 0.6, -5], 82], // v8: centrado entre os dois olhos (não na câmera do capacete)
  ombro: [[0.21, 0.95, 0.2], [-0.02, 0.5, -0.78], 48], // por cima do ombro direito: capacete, mãos e volante
  rosto: [[0.07, 0.62, -0.78], [0, 0.7, -0.12], 58], // do volante para o rosto: capacete, halo em volta, ombros
  lado: [[4.2, 1.0, -0.45], [0, 0.52, -0.45], 30], // de lado, na altura do cockpit (com raioX vê o corpo inteiro)
  cima: [[0.35, 2.1, -1.55], [0, 0.55, -0.32], 32], // do alto, à frente: a abertura, o halo e o piloto encaixado
};
export type TomadaCockpit = "piloto" | "pov" | "olhos" | "ombro" | "rosto" | "lado" | "cima";

/** Câmera dentro/junto do cockpit de `car` (funciona parado ou andando no circuito: segue o carro). `tipo`: "piloto"
 *  (o que ele vê, por cima do volante e pelo halo), "ombro" (por cima do ombro direito), "rosto" (do volante para o
 *  capacete), "lado" (lateral do cockpit), "cima" (do alto, à frente). `k` 0 a 1 = aproximação lenta (até 12% do
 *  caminho; anime com c.k); `olhar` [x, y, z] no espaço do carro troca o ponto para onde olha (ex.: "piloto" olhando o
 *  retrovisor esquerdo: [-0.5, 0.72, -0.25]); `lente` troca a lente. Use com poePilotoNoCarro. */
export function cameraNoCockpit(w: Mundo, car: THREE.Object3D, tipo: TomadaCockpit = "piloto", o: { k?: number; olhar?: Ponto; lente?: number; rolar?: number } = {}) {
  const [de, para, lente] = TOMADAS[tipo] ?? TOMADAS.piloto;
  car.updateMatrixWorld(true);
  const alvo = noCarro(car, o.olhar ?? para);
  const pos = noCarro(car, de);
  if (tipo !== "piloto" && tipo !== "pov" && tipo !== "olhos") pos.lerp(alvo, 0.12 * Math.max(0, Math.min(1, o.k ?? 0)));
  else pos.add(noCarro(car, [0, 0, -0.02 * (o.k ?? 0)]).sub(noCarro(car, [0, 0, 0])));
  camera(w, [pos.x, pos.y, pos.z], [alvo.x, alvo.y, alvo.z], o.lente ?? lente, o.rolar ?? 0);
}

/** Caixa invisível em volta do cockpit (do pedal ao capacete, da largura da abertura) para `enquadrar`/`orbitar`:
 *  `enquadrar(w, alvoDoCockpit(w, car), [1, 0.35, 0.2], 1.1, 34)`. */
export function alvoDoCockpit(w: Mundo, car: THREE.Object3D, chave = "alvo:cockpit:caixa") {
  const a = obj(w, chave, () => new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.8, 1.55), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false })));
  car.updateMatrixWorld(true);
  a.position.copy(noCarro(car, [0, 0.5, -0.62]));
  a.quaternion.copy(car.quaternion);
  a.scale.setScalar(car.scale.x);
  a.updateMatrixWorld(true);
  return a;
}

/** Espelho de verdade no retrovisor do carro (o do próprio carro, nunca um par novo): um Reflector (three.js) sobre o
 *  vidro, que reflete a cena atrás (pista, carro que se aproxima). `lado` -1 esquerdo, 1 direito. Use nos planos em que a
 *  câmera olha para o retrovisor (POV virando a cabeça: cameraNoCockpit(w, car, "piloto", { olhar: [-0.56, 0.76, -0.42] })). */
export function espelhoReal(w: Mundo, car: THREE.Object3D, lado: -1 | 1 = -1) {
  const m = obj(w, `espelho:real:${lado}`, () => {
    const r = new Reflector(new THREE.PlaneGeometry(0.14, 0.055), { textureWidth: 512, textureHeight: 256, color: 0xdfe8f2, clipBias: 0.003 });
    return r;
  });
  car.updateMatrixWorld(true);
  const g = -lado * 0.6;
  m.position.copy(noCarro(car, [lado * 0.56 + Math.sin(g) * 0.025, 0.76, -0.42 + Math.cos(g) * 0.025]));
  // a face (+z do plano) olha para trás, virada ~35° para o piloto (como o vidro de verdade: ele vê o lado e a traseira)
  m.quaternion.copy(car.quaternion).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -lado * 0.6));
  m.scale.setScalar(car.scale.x);
  return m;
}

// ------------------------------------------------------------------------------------------------ mãos no volante (v11)
// Felipe (v10 reprovada): mãos refeitas com articulação de verdade, presas à EMPUNHADURA do modelo do volante. Cada
// dedo tem 3 falanges e o polegar 2; a pose é calculada encostando cada falange na seção real do cabo (medida no
// contorno PEGA do volante.ts, extrudado em z de -0,0295 a +0,0115): os 4 dedos saem do lado do piloto, passam por FORA
// do cabo e terminam atrás dele; o polegar entra pela fresta (janela do corpo do volante, ao lado do cabo). As mãos são
// filhas do volante (giram com ele) e o antebraço vai ao pulso por IK.
const Z_PEGA = [-0.0295, 0.0115];
/** Lado de fora e de dentro do cabo (metros, volante da esquerda) na altura y (metros). */
function cabo(y: number): { fora: number; dentro: number } {
  const ypx = CY - y / S;
  const xs: number[] = [];
  for (let i = 0; i < PEGA.length; i++) {
    const [x1, y1] = PEGA[i], [x2, y2] = PEGA[(i + 1) % PEGA.length];
    if ((y1 <= ypx && y2 > ypx) || (y2 <= ypx && y1 > ypx)) xs.push(x1 + ((ypx - y1) * (x2 - x1)) / (y2 - y1));
  }
  const a = Math.min(...xs), b = Math.max(...xs);
  return { fora: (a - CX) * S - 0.0025, dentro: (b - CX) * S + 0.0025 };
}
const segmento = (a: THREE.Vector3, b: THREE.Vector3, ra: number, rb: number, m: THREE.Material) => {
  const d = b.clone().sub(a);
  const seg = new THREE.Mesh(new THREE.CylinderGeometry(rb, ra, d.length(), 14, 1, true), m);
  seg.position.copy(a).addScaledVector(d, 0.5);
  seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  return seg;
};
const junta = (p: THREE.Vector3, r: number, m: THREE.Material) => {
  const j = new THREE.Mesh(new THREE.SphereGeometry(r, 14, 10), m);
  j.position.copy(p);
  return j;
};
const POL_L = [0.028, 0.032, 0.026]; // metacarpo visível, falange proximal, falange distal (as duas últimas somam ~0,055: mão adulta de luva)
const POL_R = [0.011, 0.0102, 0.009, 0.0085];
/** Mão `s` (-1 esquerda, 1 direita) no espaço do volante. Devolve o grupo; userData.pulso = posição do pulso.
 *  v12 (Felipe: "é só fazer uma mão normal"): medidas de mão adulta com luva (+10% de espessura): palma ~0,09 x 0,10;
 *  dedos médio 0,088, indicador/anelar ~0,07, mínimo ~0,06 (falanges 4:2,5:2), espessura ~0,02; polegar 0,055 em 2
 *  falanges, saindo da base lateral da palma. Pegada de força na haste lateral: a palma encosta no lado de FORA da haste
 *  e vai para o piloto (o pulso fica à frente do volante); os dedos saem dos nós atrás/por fora, contornam a haste por
 *  trás e por dentro e as pontas aparecem na frente dela, sem passar da borda de dentro; o polegar fica sobre a frente
 *  da haste. Nada cobre a tela/botões. Faixa amarela só no punho. */
function criarMaoNoVolante(s: number, mLuva: THREE.Material, mPunho: THREE.Material, mFaixa: THREE.Material) {
  const g = new THREE.Group();
  g.name = s < 0 ? "mao_E" : "mao_D";
  const cz = (Z_PEGA[0] + Z_PEGA[1]) / 2, b = (Z_PEGA[1] - Z_PEGA[0]) / 2;
  const fal = (tot: number) => [tot * 4 / 8.5, tot * 2.5 / 8.5, tot * 2 / 8.5];
  const dedos = [
    { y: 0.004, L: fal(0.074), r: 0.0098 },
    { y: -0.0175, L: fal(0.084), r: 0.01 },
    { y: -0.039, L: fal(0.078), r: 0.0097 },
    { y: -0.059, L: fal(0.062), r: 0.0088 },
  ];
  const pontosPalma: THREE.Vector3[] = [];
  let foraX = 0, zNos = 0;
  for (const dd of dedos) {
    const c = cabo(dd.y);
    const cx = s * -((c.fora + c.dentro) / 2); // volante da esquerda: x negativo; espelha para a direita
    const a = (c.dentro - c.fora) / 2;
    foraX = Math.max(foraX, Math.abs(cx) + a); // |x| do lado de fora do cabo
    const A = a + dd.r + 0.0008, B = b + dd.r + 0.0008;
    // elipse folgada em volta do cabo: t = 90° frente (piloto), 180° lado de FORA, 270° atrás, 360° lado de dentro
    const Q = (t: number) => new THREE.Vector3(cx - s * A * Math.cos(t), dd.y, cz + B * Math.sin(t));
    let t = (284 * Math.PI) / 180; // nó do dedo: atrás da haste (a palma vem pelo lado de fora)
    const juntas = [Q(t)];
    for (const L of dd.L) {
      // avança na elipse (atrás, dentro, frente) até a corda medir a falange: a falange encosta no cabo
      let t2 = t;
      while (Q(t2).distanceTo(Q(t)) < L && t2 < t + Math.PI) t2 += 0.005;
      juntas.push(Q(t2));
      t = t2;
    }
    for (let k = 0; k < 3; k++) {
      const ra = dd.r * (1 - k * 0.07), rb = dd.r * (1 - (k + 1) * 0.07);
      g.add(segmento(juntas[k], juntas[k + 1], ra, rb, mLuva), junta(juntas[k + 1], rb, mLuva));
    }
    g.add(junta(juntas[0], dd.r, mLuva));
    zNos += juntas[0].z / dedos.length;
    for (let k = 0; k < 8; k++) {
      const ang = (k / 8) * Math.PI * 2;
      pontosPalma.push(juntas[0].clone().add(new THREE.Vector3(Math.cos(ang) * dd.r, Math.sin(ang) * dd.r, 0)));
    }
  }
  // palma (~0,10 dos nós ao pulso) encostada no lado de fora da haste, indo para o piloto e um pouco para baixo
  const pulso = new THREE.Vector3(s * (foraX + 0.016), -0.062, zNos + 0.088);
  for (let k = 0; k < 14; k++) {
    const ang = (k / 14) * Math.PI * 2;
    pontosPalma.push(pulso.clone().add(new THREE.Vector3(Math.cos(ang) * 0.018, Math.sin(ang) * 0.026, 0)));
  }
  // dorso abaulado para fora; face da palma rente ao lado de fora da haste
  pontosPalma.push(new THREE.Vector3(s * (foraX + 0.032), -0.03, zNos + 0.035));
  for (const y of [0.0, -0.03, -0.058]) pontosPalma.push(new THREE.Vector3(s * (foraX + 0.001), y, Z_PEGA[1] + 0.012));
  // eminência tenar: base lateral (de cima) da palma, na frente da haste
  const tenar = new THREE.Vector3(s * (foraX + 0.004), 0.004, Z_PEGA[1] + 0.03);
  for (let k = 0; k < 8; k++) {
    const ang = (k / 8) * Math.PI * 2;
    pontosPalma.push(tenar.clone().add(new THREE.Vector3(Math.cos(ang) * 0.012, Math.sin(ang) * 0.012, 0)));
  }
  const palma = new THREE.Mesh(new ConvexGeometry(pontosPalma), mLuva);
  palma.geometry.computeVertexNormals();
  g.add(palma);
  // polegar (2 falanges, ~0,055): da tenar, deitado sobre a frente da haste, subindo para dentro; a ponta para antes
  // da borda de dentro e abaixo do seletor do canto
  const t1 = new THREE.Vector3(s * (foraX - 0.007), 0.01, Z_PEGA[1] + 0.022);
  const t2 = new THREE.Vector3(s * (foraX - 0.017), 0.01, Z_PEGA[1] + 0.019); // por cima do indicador, abaixo do seletor do canto
  // (2026-11-20) o polegar de repouso fica num grupo próprio: `polegar(p, "ot", k)` o troca pelo polegar articulado que alcança um botão
  const polFixo = new THREE.Group();
  polFixo.name = "polegar_fixo";
  polFixo.add(segmento(tenar, t1, 0.011, 0.0102, mLuva), junta(t1, 0.0102, mLuva), segmento(t1, t2, 0.0102, 0.009, mLuva), junta(t2, 0.009, mLuva));
  g.add(polFixo);
  const polMov = new THREE.Group();
  polMov.name = "polegar_mov";
  polMov.visible = false;
  const polSegs = POL_L.map((_, i) => new THREE.Mesh(new THREE.CylinderGeometry(POL_R[i + 1], POL_R[i], 1, 14, 1, true), mLuva));
  const polJuntas = POL_R.map((r) => new THREE.Mesh(new THREE.SphereGeometry(r, 14, 10), mLuva));
  polMov.add(...polSegs, ...polJuntas);
  g.add(polMov);
  g.userData.polegar = { fixo: polFixo, mov: polMov, segs: polSegs, juntas: polJuntas, base: tenar.clone(), repouso: t2.clone() };
  // punho do macacão (manga azul com faixa amarela na boca): orientado a cada quadro pelo antebraço
  const punho = new THREE.Group();
  punho.name = "punho";
  const manga = new THREE.Mesh(new THREE.CylinderGeometry(0.029, 0.032, 0.05, 18), mPunho);
  manga.position.y = -0.03;
  const faixa = new THREE.Mesh(new THREE.CylinderGeometry(0.0295, 0.0295, 0.01, 18), mFaixa);
  faixa.position.y = -0.008;
  punho.add(manga, faixa);
  punho.position.copy(pulso);
  g.add(punho);
  g.userData.pulso = [pulso.x, pulso.y, pulso.z];
  g.traverse((o) => (o.castShadow = true));
  return g;
}

// ------------------------------------------------------------------------------------------------ polegar até um botão
const suave = (x: number) => {
  const t = Math.max(0, Math.min(1, x));
  return t * t * (3 - 2 * t);
};
const polegaresAtivos = new Set<{ fixo: THREE.Object3D; mov: THREE.Object3D }>();
let restauraPolegar = false;
/** Polegar do piloto até um botão do volante (2026-11-20; pedido: "levar o polegar até o OT"). `p` = o piloto de
 *  `poePilotoNoCarro` / `cockpitNaPista`; `nome` = ot, boost, aero, pl, n, radio, bb_mais, bb_menos; `k` de 0 a 1: de 0 a 0,7
 *  o polegar solta a pegada e vai até o botão (arco, sem atravessar o volante); de 0,7 a 1 ele AFUNDA o botão e o acende (já
 *  chama `apertar`, não use os dois). A mão que alcança é a do lado do botão (OT, BOOST, PL, rádio, BB+ = direita; N, AERO, BB−
 *  = esquerda), a outra segue na empunhadura. Com k 0 nada muda (polegar de repouso). Volta ao normal no quadro seguinte.
 *  Ex.: `const p = poePilotoNoCarro(w, car, 0); polegar(p, "ot", c.k); cameraNoCockpit(w, car, "ombro", { k: c.k });` */
export function polegar(p: THREE.Object3D, nome: string, k = 1) {
  const vol = p.userData.volante as THREE.Object3D | null | undefined;
  if (!vol || k <= 0) return;
  const botao = achar(vol, `botao_${nome}`);
  if (!botao) return;
  vol.updateMatrixWorld(true);
  const centro = vol.worldToLocal(botao.getWorldPosition(new THREE.Vector3()));
  const caixa = new THREE.Box3().setFromObject(botao);
  let topo = -Infinity;
  for (const x of [caixa.min.x, caixa.max.x]) for (const y of [caixa.min.y, caixa.max.y]) for (const z of [caixa.min.z, caixa.max.z])
    topo = Math.max(topo, vol.worldToLocal(new THREE.Vector3(x, y, z)).z);
  const mao = vol.getObjectByName(centro.x < 0 ? "mao_E" : "mao_D");
  const d = mao?.userData.polegar as { fixo: THREE.Object3D; mov: THREE.Object3D; segs: THREE.Mesh[]; juntas: THREE.Mesh[]; base: THREE.Vector3; repouso: THREE.Vector3 } | undefined;
  if (!mao || !d) return;
  const a = suave(k / 0.7); // alcance
  const press = suave((k - 0.7) / 0.3); // afundar
  const alvo = new THREE.Vector3(centro.x, centro.y, topo + POL_R[3] - 0.0025 * press);
  const base = d.base.clone();
  const ponta = d.repouso.clone().lerp(alvo, a);
  ponta.z += 0.016 * Math.sin(Math.PI * a); // arco: o polegar passa por cima da face, não por dentro dela
  const esc = 0.3 + 0.7 * a; // o polegar curvado sobre a empunhadura parece curto: estica ao se abrir
  const L = POL_L.map((x) => x * esc);
  // FABRIK de 3 ossos: base presa na tenar, ponta no alvo, arco para o piloto (+z) como chute inicial
  const J = [0, 1, 2, 3].map((i) => base.clone().lerp(ponta, i / 3).add(new THREE.Vector3(0, 0, 0.03 * Math.sin((Math.PI * i) / 3))));
  for (let it = 0; it < 24; it++) {
    J[3].copy(ponta);
    for (let i = 2; i >= 0; i--) {
      const dir = J[i].clone().sub(J[i + 1]).normalize(); // (calcula a direção ANTES de copiar o vizinho)
      J[i].copy(J[i + 1]).addScaledVector(dir, L[i]);
    }
    J[0].copy(base);
    for (let i = 1; i <= 3; i++) {
      const dir = J[i].clone().sub(J[i - 1]).normalize();
      J[i].copy(J[i - 1]).addScaledVector(dir, L[i - 1]);
    }
  }
  for (let i = 0; i < 3; i++) {
    const seg = d.segs[i];
    const v = J[i + 1].clone().sub(J[i]);
    seg.position.copy(J[i]).addScaledVector(v, 0.5);
    seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v.clone().normalize());
    seg.scale.set(1, v.length(), 1);
  }
  J.forEach((q, i) => d.juntas[i].position.copy(q));
  d.fixo.visible = false;
  d.mov.visible = true;
  polegaresAtivos.add(d);
  if (!restauraPolegar) {
    restauraPolegar = true;
    aoRestaurar(() => {
      polegaresAtivos.forEach((x) => {
        x.fixo.visible = true;
        x.mov.visible = false;
      });
      polegaresAtivos.clear();
    });
  }
  apertar(vol as never, nome, press);
}
