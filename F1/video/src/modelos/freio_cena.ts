// Ajudantes de cena para o freio (2026-11-12): calor com halo, termômetro 3D, medidor de faixa de temperatura (sem
// números: a faixa ideal muda com material, pista e equipe), partículas que correm por um caminho (ar no duto, energia
// até a bateria), ventilação do disco e o esquema do sistema híbrido de 2026 (MGU-K, bateria, eixo traseiro).
import * as THREE from "three";
import { deslocar, peca } from "./desmonte";
import { brilho } from "./efeitos3d";
import { criarPiloto, obj, rotulo } from "./extras";
import { neutro } from "./boneco";
import { calorNosDiscos, corDoCalor, texFibra } from "./freio";
import type { Mundo } from "./mundo";

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

/** Piloto articulado sentado no cockpit (reclinado, braços no volante) com o pé ESQUERDO no pedal de freio. A perna é
 *  resolvida por IK de duas articulações (coxa 0,43 m, canela 0,40 m) até a sapata do pedal; `k` = quanto o pedal afunda
 *  (o mesmo de `poePedais`). O pé direito fica apoiado no acelerador, solto. Use com raioX do monocoque/tampa/sidepods. */
export function poePilotoNoCarro(w: Mundo, car: THREE.Object3D, k = 0, o: { chave?: string; cores?: { macacao?: string; detalhe?: string; faixa?: string; capacete?: string } } = {}) {
  const p = obj(w, o.chave ?? "piloto:cockpit", () => criarPiloto({ traje: "capacete", macacao: o.cores?.macacao ?? "#1d3f9e", detalhe: o.cores?.detalhe ?? "#f2c232", faixa: o.cores?.faixa ?? "#f2c232", capacete: o.cores?.capacete ?? "#f5c518" }));
  neutro(p);
  const j = p.userData.juntas as Record<string, THREE.Object3D>;
  const QUADRIL = { y: 0.17, z: -0.62 }; // quadril no assento (espaço do carro), cabeça cai no lugar do capacete
  car.updateMatrixWorld(true);
  p.position.copy(car.localToWorld(new THREE.Vector3(0, QUADRIL.y - 0.92, QUADRIL.z)));
  p.quaternion.copy(car.quaternion);
  p.rotateY(Math.PI); // o boneco olha para +z; o carro anda para -z
  p.scale.setScalar(car.scale.x);
  j.coluna.rotation.x = 0.78; // tronco reclinado para trás (~45°)
  j.pescoco.rotation.x = -0.55; // olhando para a frente
  // braços para o volante (diante do peito)
  for (const l of ["E", "D"]) {
    j[`ombro${l}`].rotation.x = 0.72; // a coluna reclinada já soma 0,78: o braço sai para a frente, na altura do volante
    j[`ombro${l}`].rotation.z = l === "E" ? -0.25 : 0.25;
    j[`cotovelo${l}`].rotation.x = 0.55;
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
  return p;
}
