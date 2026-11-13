// Freio de F1 (2026) e freio de carro de rua, para os vídeos sobre frenagem ("pq os freios de um F1 ficam incandescentes?",
// 2026-11-12). Medidas conferidas na Brembo (brembo.com/en/motorsport/formula1/ventilation-holes, nov/2026): disco de
// carbono-carbono de 328 mm na frente e 280 mm atrás, 32 mm de espessura, ~1.050 furos radiais de ventilação (mínimo 3 mm)
// na borda, em fileiras; picos acima de 1.000 °C na frenagem forte. Pinça monobloco de 6 pistões (alumínio, NÃO carbono),
// presa ao montante; pastilhas de carbono. A tomada de ar do freio fica do lado de dentro da roda, virada para a frente.
// Aparência: disco preto-grafite fosco (o carbono fica cinza-chumbo com o uso), borda com as fileiras de furinhos, sino de
// titânio no meio; pinça escura anodizada (sem marca).
//
// Quadro de referência do conjunto (`F`): eixo do disco em z, +z = lado de FORA da roda (de quem olha a roda de fora).
// Ninguém precisa girar o conjunto no estúdio: a câmera em +z vê a face do disco e a pinça.
// No carro (Carro3D), cada roda ganha um conjunto `freio_<eixo>_<lado>` (peça do desmonte) virado para fora, com o
// disco dentro do aro (atrás dos raios: aparece pelas janelas da roda) e a tomada de ar do lado de dentro.
import * as THREE from "three";
import { aoRestaurar, girarPecaEixo, peca } from "./desmonte";

export type TipoFreio = "f1" | "rua";
export type OpcoesFreio = {
  tipo?: TipoFreio; // f1 (carbono, padrão) ou rua (ferro fundido ventilado por aletas)
  eixo?: "dianteiro" | "traseiro"; // só o tamanho do disco F1 (328 / 280 mm)
  duto?: boolean; // tomada de ar e duto até o freio (padrão: sim no estúdio)
  canais?: boolean; // canais internos de ventilação (aparecem com raioX no disco; padrão: sim no estúdio)
  pinca?: number; // ângulo da pinça em graus no plano do disco (0 = direita, 90 = em cima); padrão -25
  carro?: boolean; // versão leve para o carro (sem canais internos)
};

const mats = new Map<string, THREE.Material>();
const m = (chave: string, criar: () => THREE.Material) => mats.get(chave) ?? (mats.set(chave, criar()), mats.get(chave)!);

// ---------------------------------------------------------------------------------------------------- texturas
const texs = new Map<string, THREE.CanvasTexture>();
function tex(chave: string, w: number, h: number, pintar: (x: CanvasRenderingContext2D) => void, repetir = true) {
  if (texs.has(chave)) return texs.get(chave)!;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  pintar(c.getContext("2d")!);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  if (repetir) t.wrapS = THREE.RepeatWrapping;
  t.anisotropy = 16;
  texs.set(chave, t);
  return t;
}
const ruido = (i: number) => {
  const x = Math.sin(i * 91.7 + 13.3) * 43758.5453;
  return x - Math.floor(x);
};

/** Borda do disco F1: 4 fileiras desencontradas de furos radiais (~260 por fileira = ~1.050 no disco). u = volta, v = espessura. */
const texBordaF1 = () =>
  tex("borda_f1", 2048, 64, (x) => {
    x.fillStyle = "#2b2b2e";
    x.fillRect(0, 0, 2048, 64);
    for (let k = 0; k < 2048; k++) {
      x.fillStyle = `rgba(255,255,255,${0.02 + ruido(k) * 0.04})`;
      x.fillRect(k, 0, 1, 64);
    }
    x.fillStyle = "#050506";
    [10, 25, 39, 54].forEach((y, fila) => {
      for (let k = 0; k < 262; k++) {
        x.beginPath();
        x.arc(((k + (fila % 2) * 0.5) * 2048) / 262, y, 3.1, 0, Math.PI * 2);
        x.fill();
      }
    });
  });
/** Face de atrito do carbono: grafite fosco com anéis finos de desgaste (centro da textura = centro do disco). */
const texFaceF1 = () =>
  tex("face_f1", 512, 512, (x) => {
    x.fillStyle = "#303033";
    x.fillRect(0, 0, 512, 512);
    for (let r = 120; r < 256; r += 2) {
      x.strokeStyle = `rgba(${ruido(r) > 0.5 ? "255,255,255" : "0,0,0"},${0.03 + ruido(r + 7) * 0.07})`;
      x.lineWidth = 1 + ruido(r + 3) * 2;
      x.beginPath();
      x.arc(256, 256, r, 0, Math.PI * 2);
      x.stroke();
    }
    for (let k = 0; k < 900; k++) {
      const a = ruido(k) * Math.PI * 2;
      const r = 130 + ruido(k + 1) * 125;
      x.fillStyle = `rgba(0,0,0,${0.15 + ruido(k + 2) * 0.2})`;
      x.fillRect(256 + Math.cos(a) * r, 256 + Math.sin(a) * r, 2, 2);
    }
  }, false);
/** Disco de rua: ferro fundido cinza com riscos circulares de uso. */
const texFaceRua = () =>
  tex("face_rua", 512, 512, (x) => {
    x.fillStyle = "#8d9096";
    x.fillRect(0, 0, 512, 512);
    for (let r = 100; r < 256; r += 1.5) {
      x.strokeStyle = `rgba(${ruido(r) > 0.5 ? "255,255,255" : "40,40,40"},${0.05 + ruido(r + 9) * 0.12})`;
      x.lineWidth = 1;
      x.beginPath();
      x.arc(256, 256, r, 0, Math.PI * 2);
      x.stroke();
    }
  }, false);
/** Borda do disco de rua: duas placas e as aletas internas aparecendo como fendas. */
const texBordaRua = () =>
  tex("borda_rua", 1024, 64, (x) => {
    x.fillStyle = "#7d8086";
    x.fillRect(0, 0, 1024, 64);
    x.fillStyle = "#1b1c1f";
    for (let k = 0; k < 36; k++) x.fillRect((k * 1024) / 36, 20, 1024 / 36 - 8, 24);
  });
/** Fibra de carbono trançada (para o close do material). */
export const texFibra = () =>
  tex("fibra", 256, 256, (x) => {
    x.fillStyle = "#151517";
    x.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 16; i++)
      for (let j = 0; j < 16; j++) {
        const g = x.createLinearGradient(i * 16, j * 16, i * 16 + ((i + j) % 2 ? 16 : 0), j * 16 + ((i + j) % 2 ? 0 : 16));
        g.addColorStop(0, "#1d1d21");
        g.addColorStop(0.5, "#4a4a52");
        g.addColorStop(1, "#1d1d21");
        x.fillStyle = g;
        x.fillRect(i * 16 + 1, j * 16 + 1, 14, 14);
      }
  });

// ---------------------------------------------------------------------------------------------------- geometria
/** Anel deitado no plano XY (virado para +z) com textura polar: u,v vêm da posição (centro da textura = centro). */
function anel(ri: number, ro: number, mat: THREE.Material, z: number, virado = false) {
  const g = new THREE.RingGeometry(ri, ro, 96, 2);
  const pos = g.attributes.position;
  const uv = g.attributes.uv;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5 + pos.getX(i) / (2 * ro), 0.5 + pos.getY(i) / (2 * ro));
  const o = new THREE.Mesh(g, mat);
  o.position.z = z;
  if (virado) o.rotation.y = Math.PI;
  return o;
}
/** Cilindro aberto com eixo em z (raio r, comprimento l), centrado em z. */
function tubo(r: number, l: number, mat: THREE.Material, z = 0, seg = 96) {
  const g = new THREE.CylinderGeometry(r, r, l, seg, 1, true);
  g.rotateX(Math.PI / 2);
  const o = new THREE.Mesh(g, mat);
  o.position.z = z;
  return o;
}
/** Setor de anel (r1 a r2, de a0 a a1 rad) extrudado em z de z0 a z1. */
function setor(r1: number, r2: number, a0: number, a1: number, z0: number, z1: number, mat: THREE.Material, chanfro = 0.004) {
  const s = new THREE.Shape();
  s.absarc(0, 0, r2, a0, a1, false);
  s.absarc(0, 0, r1, a1, a0, true);
  s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: Math.max(0.001, z1 - z0 - chanfro * 2), bevelEnabled: chanfro > 0, bevelSize: chanfro, bevelThickness: chanfro, bevelSegments: 2, curveSegments: 24 });
  const o = new THREE.Mesh(g, mat);
  o.position.z = z0 + chanfro;
  return o;
}

/** Discos com material próprio (para aquecer um sem aquecer os outros): marcados em userData.aquece = fração do brilho. */
const marcar = (o: THREE.Mesh, fracao: number) => {
  o.userData.aquece = fracao;
  return o;
};

/** O conjunto de freio no quadro F (eixo z, +z para fora). Devolve o grupo; peças: disco_freio, canais, pastilhas, pinca,
 *  sino, tomada_freio (com duto). userData.rotor = grupo que gira; userData.pastilhas = [de dentro, de fora]. */
export function criarFreio(o: OpcoesFreio = {}): THREE.Group {
  const tipo = o.tipo ?? "f1";
  const f1 = tipo === "f1";
  const ro = f1 ? (o.eixo === "traseiro" ? 0.14 : 0.164) : 0.15; // raio do disco (m)
  const e = f1 ? 0.032 : 0.028; // espessura
  const ri = f1 ? ro - 0.058 : ro - 0.05; // fim da pista de atrito (as pastilhas cobrem ~55 mm)
  const g = new THREE.Group();
  g.name = f1 ? "freio_f1" : "freio_rua";
  const rotor = new THREE.Group();
  rotor.name = "rotor";
  g.add(rotor);
  g.userData.raio = ro;

  // disco: duas faces de atrito, borda com os furos (F1) ou as fendas das aletas (rua) e a borda de dentro
  const disco = peca(new THREE.Group(), "disco_freio", [0, 0, 0.22], 1);
  rotor.add(disco);
  const face = m(`face_${tipo}`, () => new THREE.MeshStandardMaterial({ map: f1 ? texFaceF1() : texFaceRua(), color: f1 ? "#ffffff" : "#e8ecf2", roughness: f1 ? 0.78 : 0.3, metalness: f1 ? 0.05 : 0.35, side: THREE.DoubleSide }));
  const bordaTex = f1 ? texBordaF1() : texBordaRua();
  const borda = m(`borda_${tipo}`, () => new THREE.MeshStandardMaterial({ map: bordaTex, emissiveMap: bordaTex, roughness: 0.7, metalness: f1 ? 0.05 : 0.35, side: THREE.DoubleSide }));
  const dentro = m(`dentro_${tipo}`, () => new THREE.MeshStandardMaterial({ color: f1 ? "#222225" : "#6f7278", roughness: 0.8, metalness: f1 ? 0 : 0.6, side: THREE.DoubleSide }));
  const rFace = f1 ? ri - 0.012 : ri - 0.006;
  disco.add(marcar(anel(rFace, ro, face, e / 2), 1), marcar(anel(rFace, ro, face, -e / 2, true), 1), marcar(tubo(ro, e, borda), 1.15), marcar(tubo(rFace, e, dentro), 0.7));
  if (f1) {
    // abas de arraste do sino (o disco de carbono "flutua" preso por abas na borda de dentro)
    for (let k = 0; k < 12; k++) {
      const a = (k / 12) * Math.PI * 2;
      disco.add(marcar(setor(rFace - 0.016, rFace + 0.001, a - 0.09, a + 0.09, -e / 2 + 0.004, e / 2 - 0.004, dentro, 0.002), 0.5));
    }
  }
  // sino (chapéu) no meio: titânio no F1, o próprio ferro fundido no de rua
  const sino = peca(new THREE.Group(), "sino", [0, 0, 0.4], 0);
  rotor.add(sino);
  const tit = m(`sino_${tipo}`, () => new THREE.MeshStandardMaterial({ color: f1 ? "#7a7c80" : "#8a8d93", roughness: 0.35, metalness: 0.85, side: THREE.DoubleSide }));
  const rs = rFace - (f1 ? 0.016 : 0);
  const prof = f1 ? 0.06 : 0.05;
  sino.add(tubo(rs, prof, tit, e / 2 + prof / 2 - 0.004));
  const tampa = anel(f1 ? 0.034 : 0.035, rs, tit, e / 2 + prof - 0.004);
  sino.add(tampa);
  const furo = m("furo", () => new THREE.MeshStandardMaterial({ color: "#0b0b0d", roughness: 0.6, metalness: 0.4 }));
  const nPar = f1 ? 12 : 5;
  for (let k = 0; k < nPar; k++) {
    const a = (k / nPar) * Math.PI * 2;
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.01, 12), furo);
    p.rotation.x = Math.PI / 2;
    p.position.set(Math.cos(a) * (rs * 0.68), Math.sin(a) * (rs * 0.68), e / 2 + prof - 0.002);
    sino.add(p);
  }
  if (!f1) {
    // aletas internas do disco de rua (entre as duas placas)
    for (let k = 0; k < 36; k++) {
      const a = ((k + 0.5) / 36) * Math.PI * 2;
      disco.add(marcar(setor(rFace + 0.004, ro - 0.002, a - 0.03, a + 0.03, -e / 2 + 0.008, e / 2 - 0.008, dentro, 0), 0.8));
    }
  }
  // canais internos (centenas de canais radiais, em 4 camadas): só aparecem com raioX(freio, "disco_freio")
  if (f1 && o.canais !== false && !o.carro) {
    const n = 90;
    const ger = new THREE.CylinderGeometry(0.0022, 0.0022, ro - rFace - 0.004, 6);
    ger.rotateZ(Math.PI / 2);
    const canal = new THREE.InstancedMesh(ger, m("canal", () => new THREE.MeshBasicMaterial({ color: "#7fd8ff", transparent: true, opacity: 0.85 })), n * 4);
    const q = new THREE.Object3D();
    let i = 0;
    [-0.011, -0.004, 0.004, 0.011].forEach((z, camada) => {
      for (let k = 0; k < n; k++) {
        const a = ((k + (camada % 2) * 0.5) / n) * Math.PI * 2;
        const r = (rFace + ro) / 2;
        q.position.set(Math.cos(a) * r, Math.sin(a) * r, z);
        q.rotation.set(0, 0, a);
        q.updateMatrix();
        canal.setMatrixAt(i++, q.matrix);
      }
    });
    const gc = peca(new THREE.Group(), "canais", [0, 0, 0.22], 1);
    gc.add(canal);
    rotor.add(gc);
  }

  // pinça (não gira): monobloco de 6 pistões em F1, flutuante de 1 pistão no de rua
  const ang = ((o.pinca ?? -25) * Math.PI) / 180;
  const meia = f1 ? 0.42 : 0.36; // meia abertura da pinça (rad): ~135 mm de corpo no disco dianteiro
  const folga = 0.004; // pastilha solta até o freio apertar
  const pastE = f1 ? 0.019 : 0.016; // pastilha + placa
  const corpo = m(`pinca_${tipo}`, () => new THREE.MeshStandardMaterial({ color: f1 ? "#4a505b" : "#3a3d44", roughness: 0.32, metalness: 0.55 }));
  const pinca = peca(new THREE.Group(), "pinca", [Math.cos(ang) * 0.3, Math.sin(ang) * 0.3, 0.1], 0);
  g.add(pinca);
  const zi = e / 2 + folga + pastE; // começo do corpo da pinça (face interna)
  const corpoE = f1 ? 0.034 : 0.03;
  const rIn = ri - 0.006;
  const rOut = ro + 0.026;
  for (const s of [-1, 1]) pinca.add(setor(rIn, rOut, ang - meia, ang + meia, s > 0 ? zi : -zi - corpoE, s > 0 ? zi + corpoE : -zi, corpo, 0.012));
  // ponte por cima da borda do disco (une as duas metades)
  pinca.add(setor(ro + 0.006, rOut, ang - meia * 0.92, ang + meia * 0.92, -zi, zi, corpo, 0.004));
  // tampas dos pistões na face de fora (3 de cada lado em F1)
  const tamp = m("pistao", () => new THREE.MeshStandardMaterial({ color: "#3a3e46", roughness: 0.3, metalness: 0.9 }));
  const nPist = f1 ? 3 : 1;
  for (let k = 0; k < nPist; k++) {
    const a = ang + (nPist === 1 ? 0 : (k / (nPist - 1) - 0.5) * meia * 1.25);
    const r = (rIn + rOut) / 2;
    const p = new THREE.Mesh(new THREE.CylinderGeometry(f1 ? 0.014 : 0.024, f1 ? 0.014 : 0.024, 0.006, 24), tamp);
    p.rotation.x = Math.PI / 2;
    p.position.set(Math.cos(a) * r, Math.sin(a) * r, zi + corpoE + 0.002);
    pinca.add(p);
  }
  // pastilhas: placa metálica + material de atrito (carbono no F1), uma de cada lado do disco
  const atrito = m(`pastilha_${tipo}`, () => new THREE.MeshStandardMaterial({ color: f1 ? "#1a1a1c" : "#3b3a38", roughness: 0.9 }));
  const placa = m("placa_pastilha", () => new THREE.MeshStandardMaterial({ color: "#8c9097", roughness: 0.4, metalness: 0.8 }));
  const pastilhas = peca(new THREE.Group(), "pastilhas", [Math.cos(ang) * 0.18, Math.sin(ang) * 0.18, 0.05], 0);
  g.add(pastilhas);
  const lados: THREE.Group[] = [];
  for (const s of [-1, 1]) {
    const lado = new THREE.Group();
    const pa = setor(ri + 0.002, ro - 0.003, ang - meia * 0.82, ang + meia * 0.82, 0, pastE * 0.7, atrito, 0.001);
    const pl = setor(ri, ro, ang - meia * 0.86, ang + meia * 0.86, pastE * 0.7, pastE, placa, 0.001);
    marcar(pa as THREE.Mesh, 0.55);
    lado.add(pa, pl);
    lado.position.z = e / 2 + folga;
    if (s < 0) {
      lado.scale.z = -1;
      lado.position.z = -(e / 2 + folga);
    }
    lado.name = s < 0 ? "pastilha_dentro" : "pastilha_fora";
    pastilhas.add(lado);
    lados.push(lado);
  }
  g.userData.folga = folga;
  g.userData.e = e;

  // tomada de ar e duto (do lado de dentro, -z): boca virada para a frente (+x no quadro F do estúdio), curva até o sino
  if (o.duto ?? !o.carro) {
    const duto = peca(new THREE.Group(), "tomada_freio", [0.25, 0, -0.25], 0);
    g.add(duto);
    const carb = m("duto", () => new THREE.MeshStandardMaterial({ map: texFibra(), color: "#9aa0aa", roughness: 0.45, metalness: 0.2, side: THREE.DoubleSide }));
    const curva = new THREE.CatmullRomCurve3([new THREE.Vector3(ro + 0.2, -0.02, -0.11), new THREE.Vector3(ro + 0.05, -0.01, -0.11), new THREE.Vector3(0.05, 0, -0.1), new THREE.Vector3(0, 0, -0.045)]);
    duto.add(new THREE.Mesh(new THREE.TubeGeometry(curva, 40, 0.042, 20, false), carb));
    const boca = new THREE.Mesh(new THREE.TorusGeometry(0.044, 0.007, 10, 28), m("boca", () => new THREE.MeshStandardMaterial({ color: "#2c3038", roughness: 0.4, metalness: 0.4 })));
    boca.rotation.y = Math.PI / 2;
    boca.scale.setScalar(1.7);
    boca.position.set(ro + 0.25, -0.02, -0.11);
    duto.add(boca);
    // boca em funil (a tomada é mais larga que o duto)
    const funil = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.042, 0.07, 28, 1, true), carb);
    funil.rotation.z = Math.PI / 2;
    funil.position.set(ro + 0.215, -0.02, -0.11);
    duto.add(funil);
    g.userData.ar = curva.getPoints(12).map((p) => [p.x, p.y, p.z]); // caminho do ar (no quadro F), números: userData vira JSON no clone
  }
  g.traverse((x) => {
    if ((x as THREE.Mesh).isMesh) x.castShadow = x.receiveShadow = true;
  });
  return g;
}

/** Gira o disco (o rotor: disco, sino e canais; a pinça e as pastilhas ficam). `ang` em radianos (some no próximo quadro). */
export function girarDisco(freio: THREE.Object3D, ang: number) {
  const r = freio.getObjectByName("rotor");
  if (r) girarPecaEixo(r, "z", ang * ((freio.userData.sinal as number) ?? 1));
}

/** A pinça aperta as pastilhas contra as duas faces do disco: k 0 = soltas (folga de 4 mm), 1 = encostadas. */
export function apertarFreio(freio: THREE.Object3D, k: number) {
  const lados = [freio.getObjectByName("pastilha_dentro"), freio.getObjectByName("pastilha_fora")];
  if (!lados[0] || !lados[1]) return;
  const e = freio.userData.e as number;
  const folga = (freio.userData.folga as number) * (1 - Math.max(0, Math.min(1, k)));
  lados[0]!.position.z = -(e / 2 + folga);
  lados[1]!.position.z = e / 2 + folga;
}

/** Cor da incandescência do carbono pela temperatura (°C), como o olho vê no escuro: nada até ~450 °C, vermelho escuro
 *  ~550, vermelho-cereja ~750, laranja ~900, laranja-amarelo ~1.000, amarelo-claro acima de 1.150. Devolve cor e força. */
export function corDoCalor(graus: number): { cor: THREE.Color; forca: number } {
  const pts: [number, string, number][] = [
    [450, "#2a0400", 0], [550, "#6a0c02", 0.45], [700, "#b81a04", 0.95], [850, "#ff3a06", 1.45], [1000, "#ff7414", 1.9], [1150, "#ffb648", 2.3], [1300, "#ffe6a8", 2.7],
  ];
  if (graus <= pts[0][0]) return { cor: new THREE.Color("#000000"), forca: 0 };
  for (let i = 1; i < pts.length; i++)
    if (graus <= pts[i][0]) {
      const k = (graus - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0]);
      return { cor: new THREE.Color(pts[i - 1][1]).lerp(new THREE.Color(pts[i][1]), k), forca: pts[i - 1][2] + (pts[i][2] - pts[i - 1][2]) * k };
    }
  return { cor: new THREE.Color(pts[pts.length - 1][1]), forca: pts[pts.length - 1][2] };
}

const proprios = new WeakSet<THREE.Mesh>();
const aquecidos = new Set<THREE.MeshStandardMaterial>();
const cor0 = new WeakMap<THREE.MeshStandardMaterial, THREE.Color>();
/** Aquece os discos (e um pouco as pastilhas; a pinça nunca) dentro de `modelo`: freio solto, conjunto do carro ou o carro
 *  inteiro (as 4 rodas; `quais` filtra pelo nome do conjunto, ex.: ["freio_dianteiro_esquerdo"]). Só neste quadro. */
export function calorNosDiscos(modelo: THREE.Object3D, graus: number, quais?: string[]) {
  const { cor, forca } = corDoCalor(graus);
  modelo.traverse((x) => {
    const mesh = x as THREE.Mesh;
    if (!mesh.isMesh || mesh.userData.aquece === undefined) return;
    if (quais) {
      let p: THREE.Object3D | null = mesh;
      while (p && !(p.userData.peca && String(p.userData.peca).startsWith("freio_"))) p = p.parent;
      if (p && !quais.includes(p.userData.peca)) return;
    }
    if (!proprios.has(mesh)) {
      // material próprio na 1ª vez: os carros da mesma equipe são clones e dividiriam o calor
      mesh.material = (mesh.material as THREE.Material).clone();
      proprios.add(mesh);
    }
    const mt = mesh.material as THREE.MeshStandardMaterial;
    if (!cor0.has(mt)) cor0.set(mt, mt.color.clone());
    mt.emissive.copy(cor);
    mt.emissiveIntensity = forca * (mesh.userData.aquece as number);
    // quente, a luz da cena quase não conta: a cor vem do próprio disco (a sombra da pinça dividia a face em meia amarela e
    // meia laranja, 2026-11-12)
    mt.color.copy(cor0.get(mt)!).multiplyScalar(Math.max(0.03, 1 - forca * 0.6));
    aquecidos.add(mt);
  });
}
/** Esfria tudo (chamado no restaurar de cada quadro). */
export function esfriarDiscos() {
  for (const mt of aquecidos) {
    mt.emissive.setRGB(0, 0, 0);
    mt.emissiveIntensity = 0;
    const c0 = cor0.get(mt);
    if (c0) mt.color.copy(c0);
  }
  aquecidos.clear();
}
aoRestaurar(esfriarDiscos);

/** Conjunto de freio de uma roda do carro, no lugar dela (posição = centro da roda). `s` = lado (-1 esquerda, 1 direita). */
export function freioDoCarro(s: number, dianteiro: boolean, x: number, y: number, z: number): THREE.Group {
  // pinça atrás e embaixo do disco na frente, à frente e embaixo atrás (no quadro F: +x local aponta para trás no lado
  // esquerdo e para a frente no direito, por causa do giro de ±90°)
  const atras = s < 0 ? -25 : 205;
  const frente = s < 0 ? 205 : -25;
  const f = criarFreio({ eixo: dianteiro ? "dianteiro" : "traseiro", carro: true, duto: false, pinca: dianteiro ? atras : frente });
  const nome = `freio_${dianteiro ? "dianteiro" : "traseiro"}_${s < 0 ? "esquerdo" : "direito"}`;
  const g = peca(new THREE.Group(), nome, [s * 0.5, 0, 0], 1);
  // o disco fica dentro do aro, para dentro (atrás dos raios); +z do conjunto aponta para fora do carro
  f.position.z = dianteiro ? -0.07 : -0.085;
  g.add(f);
  g.position.set(x, y, z);
  g.rotation.order = "YXZ";
  g.rotation.y = s < 0 ? -Math.PI / 2 : Math.PI / 2;
  // rolar: o disco gira com a roda (no quadro F o eixo z vira ±x do carro)
  f.userData.sinal = s < 0 ? 1 : -1;
  f.name = "conjunto_freio";
  // tomada de ar do freio do lado de dentro da roda, boca virada para a frente do carro (-z)
  const carb = m("duto_carro", () => new THREE.MeshStandardMaterial({ color: "#1a1b20", roughness: 0.5 }));
  const fr = s < 0 ? -1 : 1; // +x local = para trás (esq) / para a frente (dir)
  const tom = peca(new THREE.Group(), `tomada_${nome.slice(6)}`, [s * 0.2, 0, 0], 0);
  const forma = new THREE.Shape();
  const rr = (w: number, h: number, r: number, p: THREE.Path | THREE.Shape, dir = false) => {
    const pts: [number, number][] = [];
    for (let k = 0; k < 4; k++) {
      const cx = (k === 0 || k === 3 ? 1 : -1) * (w / 2 - r);
      const cy = (k < 2 ? 1 : -1) * (h / 2 - r);
      for (let j = 0; j <= 4; j++) {
        const a = (k * Math.PI) / 2 + (j / 4) * (Math.PI / 2);
        pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
      }
    }
    if (dir) pts.reverse();
    pts.forEach(([a, b], i) => (i ? p.lineTo(a, b) : p.moveTo(a, b)));
  };
  const hw = dianteiro ? 0.1 : 0.08;
  const hh = dianteiro ? 0.16 : 0.12;
  rr(hw, hh, 0.025, forma);
  const vao = new THREE.Path();
  rr(hw - 0.022, hh - 0.022, 0.016, vao, true);
  forma.holes.push(vao);
  const boca = new THREE.Mesh(new THREE.ExtrudeGeometry(forma, { depth: 0.16, bevelEnabled: false }), carb);
  // extrusão em z da forma -> eixo x local (para a frente do carro); fica do lado de dentro da roda
  boca.rotation.y = Math.PI / 2;
  const zIn = dianteiro ? -0.215 : -0.25;
  boca.position.set(fr > 0 ? 0.04 : -0.2, -0.03, zIn);
  const fundo = new THREE.Mesh(new THREE.PlaneGeometry(hw - 0.02, hh - 0.02), m("fundo_duto", () => new THREE.MeshBasicMaterial({ color: "#020203" })));
  fundo.rotation.y = Math.PI / 2;
  fundo.position.set(fr * 0.05, -0.03, zIn);
  tom.add(boca, fundo);
  tom.userData.boca = [fr * 0.2, -0.03, zIn];
  g.add(tom);
  g.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) o.castShadow = true;
  });
  return g;
}

export const NOMES_FREIOS = ["freio_dianteiro_esquerdo", "freio_dianteiro_direito", "freio_traseiro_esquerdo", "freio_traseiro_direito"];
