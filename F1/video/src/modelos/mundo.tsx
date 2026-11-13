// Mundo 3D do Explicando F1, reaproveitado em todos os vídeos verticais: pista, grid, circuito, estúdio,
// pneus, bandeiras, troféu e os ajudantes de câmera e de cena. Saiu do vídeo piloto (regras básicas, publicado).
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { PINTURAS, carro, degradeRadial, plano, texturaPista, type Pintura } from "./Carro3D";
import { FONTE } from "../kit";
import { vantage } from "./Vantage";
import { aplicarComposto, pneuPirelli } from "./pneus/pneu";

type V = [number, number, number];

const CADILLAC: Pintura = { base: "#1a1b20", clara: "#70747e", escura: "#07080a", faixa: "#f0f0f0", acento: "#d0a92e" };
const EQUIPES: Pintura[] = [...PINTURAS, CADILLAC, { base: "#0c7a3d", clara: "#34c477", escura: "#043d1d", faixa: "#f1f1e6", acento: "#ffd21f" }, { base: "#e8e8ec", clara: "#ffffff", escura: "#8a8e98", faixa: "#1553c9", acento: "#d4213c" }];
const CINZA: Pintura = { base: "#5c5f66", clara: "#83868d", escura: "#2c2e33", faixa: "#44464c", acento: "#44464c" };
export const iCadillac = PINTURAS.length;

type Clima = { ceu: string[]; nevoa: string; sol: string; forca: number; perto?: number; longe?: number };
export const CLIMAS: Record<string, Clima> = {
  tarde: { ceu: ["#0e2a52", "#3f6f96", "#e8b286", "#f6c98c"], nevoa: "#f0c08a", sol: "#fff0dc", forca: 2.1 },
  manha: { ceu: ["#2f6fb8", "#7fb4dd", "#dcecf2", "#eef3ee"], nevoa: "#d9e8ee", sol: "#ffffff", forca: 2.4 },
  sol: { ceu: ["#1459b3", "#4f9be0", "#bfe0f2", "#d8ecf4"], nevoa: "#cfe4ef", sol: "#fff7ea", forca: 2.9 },
  noite: { ceu: ["#04060f", "#0a1226", "#152544", "#1c2d50"], nevoa: "#14213d", sol: "#b8c8f0", forca: 1.5 },
  brasa: { ceu: ["#1a0508", "#4a0e12", "#9c2a18", "#c9552a"], nevoa: "#8a3220", sol: "#ffb39a", forca: 1.7 },
  chumbo: { ceu: ["#15171d", "#2a2d36", "#4a4e58", "#5a5e68"], nevoa: "#4a4e58", sol: "#dfe3ec", forca: 1.5 },
  claro: { ceu: ["#f6ecd8", "#f6ecd8", "#f3e6cc", "#f3e6cc"], nevoa: "#f3e6cc", sol: "#ffffff", forca: 2.4 },
  vazio: { ceu: ["#070a14", "#0a0f1e", "#0e1528", "#0e1528"], nevoa: "#0e1528", sol: "#dbe4ff", forca: 2.2 },
};

export const seed = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

function texturaCeu(cores: string[]): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 8;
  c.height = 512;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 0, 512);
  [0, 0.32, 0.47, 1].forEach((p, k) => g.addColorStop(p, cores[k]));
  x.fillStyle = g;
  x.fillRect(0, 0, 8, 512);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function rotuloTextura(texto: string, cor = "#ffffff"): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 128;
  const x = c.getContext("2d")!;
  x.font = "800 92px 'Segoe UI', sans-serif";
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillStyle = cor;
  x.fillText(texto, 128, 68);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const mat = (cor: string, rough = 0.6, metal = 0) => new THREE.MeshStandardMaterial({ color: cor, roughness: rough, metalness: metal });
const bloco = (l: number, a: number, c: number, x: number, y: number, z: number, m: THREE.Material) => {
  const b = new THREE.Mesh(new THREE.BoxGeometry(l, a, c), m);
  b.position.set(x, y, z);
  b.castShadow = true;
  return b;
};

const CORES_BANDEIRA = ["#17a34a", "#ffcf00", "#1e6fe0", "#df1f1f", "#101114", "quadriculada"];

type Pneu = { g: THREE.Group; giro: THREE.Group };
/** Pneu do estúdio: o mesmo Pirelli das rodas do carro (fotos oficiais), em tamanho de destaque. */
function pneu(): Pneu {
  const g = new THREE.Group();
  const giro = pneuPirelli(1.03, 0.94);
  giro.traverse((o) => (o.castShadow = true));
  g.rotation.z = Math.PI / 2;
  g.add(giro);
  return { g, giro };
}

function trofeu(): THREE.Group {
  const ouro = new THREE.MeshStandardMaterial({ color: "#ffcf4a", emissive: "#5a3c08", roughness: 0.25, metalness: 0.75 });
  const pts = [[0.72, 0], [0.72, 0.14], [0.36, 0.2], [0.14, 0.42], [0.1, 0.95], [0.24, 1.15], [0.62, 1.55], [0.74, 2.3], [0.8, 2.75]].map(([x, y]) => new THREE.Vector2(x, y));
  const g = new THREE.Group();
  const corpo = new THREE.Mesh(new THREE.LatheGeometry(new THREE.SplineCurve(pts).getPoints(50), 64), new THREE.MeshStandardMaterial({ color: "#ffcf4a", emissive: "#5a3c08", roughness: 0.25, metalness: 0.75, side: THREE.DoubleSide }));
  g.add(corpo);
  for (const s of [-1, 1]) {
    const alca = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.06, 12, 40, Math.PI), ouro);
    alca.position.set(s * 0.72, 2.05, 0);
    alca.rotation.z = -s * Math.PI / 2;
    g.add(alca);
  }
  g.traverse((o) => (o.castShadow = true));
  return g;
}

export type Mundo = {
  r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; sol: THREE.DirectionalLight; fundos: Record<string, THREE.Texture>;
  sets: Record<string, THREE.Group>; carros: THREE.Group[]; cinzas: THREE.Group[]; halos: THREE.Mesh[]; parts: THREE.Sprite[];
  sc: THREE.Group; luzesSc: THREE.MeshStandardMaterial[]; batido: THREE.Group; amarelo: THREE.MeshBasicMaterial; linhaChegada: THREE.Group;
  portico: THREE.Group; lampadas: THREE.MeshStandardMaterial[]; brilhos: THREE.Sprite[]; bandeiras: { g: THREE.Group; pano: THREE.Mesh }[];
  rastro: THREE.Mesh; marcador: THREE.Mesh; chao: THREE.MeshStandardMaterial; pneus: Pneu[]; barras: { m: THREE.Mesh; rotulo: THREE.Sprite }[];
  trofeu: THREE.Group; moedas: THREE.InstancedMesh; teto: THREE.Mesh; asa: THREE.Group; flap: THREE.Group; roda: THREE.Mesh[]; equipe: THREE.Mesh[]; circuitoPontos: THREE.Vector3[];
};

function faixaCurva(pts: THREE.Vector3[], largura: number, y: number, m: THREE.Material): THREE.Mesh {
  const pos: number[] = [];
  const ind: number[] = [];
  pts.forEach((p, i) => {
    const a = pts[(i + 1) % pts.length].clone().sub(pts[(i - 1 + pts.length) % pts.length]).normalize();
    const n = new THREE.Vector3(-a.z, 0, a.x).multiplyScalar(largura / 2);
    pos.push(p.x + n.x, y, p.z + n.z, p.x - n.x, y, p.z - n.z);
    if (i < pts.length - 1) ind.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  return new THREE.Mesh(g, m);
}

export function montar(canvas: HTMLCanvasElement): Mundo {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  r.setSize(1080, 1920, false);
  r.localClippingEnabled = true; // corte dos modelos (desmonte.ts)
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.ACESFilmicToneMapping;
  r.toneMappingExposure = 0.96;
  r.shadowMap.enabled = true;
  r.shadowMap.type = THREE.PCFSoftShadowMap;
  const cena = new THREE.Scene();
  cena.fog = new THREE.Fog("#f0c08a", 90, 260);
  cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
  cena.environmentIntensity = 0.32;
  cena.add(new THREE.HemisphereLight("#ffe9d2", "#2a2433", 0.85));
  const sol = new THREE.DirectionalLight("#fff0dc", 2.1);
  sol.castShadow = true;
  sol.shadow.mapSize.set(4096, 4096);
  sol.shadow.radius = 5;
  sol.shadow.bias = -0.0004;
  Object.assign(sol.shadow.camera, { left: -45, right: 45, top: 90, bottom: -90, near: 1, far: 140 });
  cena.add(sol, sol.target);
  const fundos: Record<string, THREE.Texture> = {};
  for (const [nome, c] of Object.entries(CLIMAS)) fundos[nome] = texturaCeu(c.ceu);

  const sets: Record<string, THREE.Group> = { pista: new THREE.Group(), circuito: new THREE.Group(), estudio: new THREE.Group(), pit: new THREE.Group() };
  Object.values(sets).forEach((g) => cena.add(g));

  // pista: reta longa, grama, árvores e arquibancadas para a velocidade aparecer
  const mapa = texturaPista();
  const comp = 2400;
  mapa.repeat.set(1, comp / 60);
  const asfalto = new THREE.Mesh(new THREE.PlaneGeometry(48, comp), new THREE.MeshStandardMaterial({ map: mapa, roughness: 0.92 }));
  asfalto.rotation.x = -Math.PI / 2;
  asfalto.position.z = -900;
  asfalto.receiveShadow = true;
  sets.pista.add(asfalto);
  for (const s of [-1, 1]) {
    const longe = new THREE.Mesh(new THREE.PlaneGeometry(700, comp), mat("#25663b", 1));
    longe.rotation.x = -Math.PI / 2;
    longe.position.set(s * 374, -0.01, -900);
    sets.pista.add(longe);
  }
  const amarelo = new THREE.MeshBasicMaterial({ color: "#ffd400", transparent: true, opacity: 0 });
  for (const s of [-1, 1]) sets.pista.add(plano(0.34, comp, s * 6.26, -900, amarelo, 0.03));
  const arvores = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 12, 10), new THREE.MeshStandardMaterial({ roughness: 1 }), 420);
  const aux = new THREE.Object3D();
  for (let i = 0; i < 420; i++) {
    const s = seed(i) > 0.5 ? 1 : -1;
    const e = 3 + seed(i + 900) * 4;
    aux.position.set(s * (32 + seed(i + 300) * 70), e * 0.9, 250 - seed(i + 600) * 2200);
    aux.scale.setScalar(e);
    aux.updateMatrix();
    arvores.setMatrixAt(i, aux.matrix);
    arvores.setColorAt(i, new THREE.Color().setHSL(0.3 + seed(i + 50) * 0.08, 0.5, 0.2 + seed(i + 70) * 0.14));
  }
  sets.pista.add(arvores);
  const pub = document.createElement("canvas");
  pub.width = 1400;
  pub.height = 180;
  const px = pub.getContext("2d")!;
  px.fillStyle = "#1f242e";
  px.fillRect(0, 0, 1400, 180);
  for (let i = 0; i < 9000; i++) {
    px.fillStyle = `hsl(${seed(i) * 360} 28% ${32 + seed(i + 9) * 26}%)`;
    px.fillRect(seed(i + 1) * 1400, seed(i + 2) * 180, 2, 2);
  }
  const pubT = new THREE.CanvasTexture(pub);
  pubT.colorSpace = THREE.SRGBColorSpace;
  for (let k = 0; k < 16; k++) {
    const a = new THREE.Mesh(new THREE.BoxGeometry(5, 6.5, 100), [new THREE.MeshStandardMaterial({ map: pubT }), new THREE.MeshStandardMaterial({ map: pubT }), mat("#2d3340"), mat("#2d3340"), mat("#2d3340"), mat("#2d3340")]);
    a.position.set((k % 2 ? -1 : 1) * 27, 3.25, 150 - k * 110);
    a.rotation.z = (k % 2 ? 1 : -1) * 0.08;
    sets.pista.add(a);
  }
  const brancoLinha = new THREE.MeshBasicMaterial({ color: "#f4f1ea" });
  const pretoLinha = new THREE.MeshBasicMaterial({ color: "#16171b" });
  const linhaChegada = new THREE.Group();
  for (let i = 0; i < 26; i++) for (let j = 0; j < 3; j++) linhaChegada.add(plano(0.48, 0.48, -6.1 + i * 0.48, j * 0.48, (i + j) % 2 ? brancoLinha : pretoLinha, 0.025));
  sets.pista.add(linhaChegada);

  // pórtico das luzes de largada
  const portico = new THREE.Group();
  const estrutura = mat("#1c1f26", 0.5, 0.6);
  portico.add(bloco(0.45, 8, 0.45, -8.2, 4, 0, estrutura), bloco(0.45, 8, 0.45, 8.2, 4, 0, estrutura), bloco(16.8, 0.5, 0.5, 0, 7.4, 0, estrutura));
  const lampadas: THREE.MeshStandardMaterial[] = [];
  const brilhos: THREE.Sprite[] = [];
  const brilhoT = degradeRadial("rgba(255,40,30,1)");
  for (let k = 0; k < 5; k++) {
    const x = -3.8 + k * 1.9;
    portico.add(bloco(1.3, 2.3, 0.4, x, 6.3, 0.2, mat("#0a0b0e", 0.4)));
    const m = new THREE.MeshStandardMaterial({ color: "#2a0705", emissive: "#ff1a10", emissiveIntensity: 0, roughness: 0.3 });
    lampadas.push(m);
    for (const y of [6.9, 5.8]) {
      const l = new THREE.Mesh(new THREE.CircleGeometry(0.42, 32), m);
      l.position.set(x, y, 0.42);
      portico.add(l);
    }
    const b = new THREE.Sprite(new THREE.SpriteMaterial({ map: brilhoT, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    b.position.set(x, 6.35, 0.6);
    b.scale.set(5, 6, 1);
    portico.add(b);
    brilhos.push(b);
  }
  sets.pista.add(portico);

  // bandeiras
  const xadrez = document.createElement("canvas");
  xadrez.width = 512;
  xadrez.height = 320;
  const xz = xadrez.getContext("2d")!;
  for (let i = 0; i < 8; i++) for (let j = 0; j < 5; j++) {
    xz.fillStyle = (i + j) % 2 ? "#f4f4f4" : "#0c0c0e";
    xz.fillRect(i * 64, j * 64, 64, 64);
  }
  const xt = new THREE.CanvasTexture(xadrez);
  xt.colorSpace = THREE.SRGBColorSpace;
  const bandeiras = CORES_BANDEIRA.map((cor) => {
    const g = new THREE.Group();
    const mastro = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 4.6, 12), mat("#e4e7ec", 0.3, 0.6));
    mastro.position.set(-1.07, 2.3, 0);
    const pano = new THREE.Mesh(new THREE.PlaneGeometry(2.1, 1.35, 42, 16), new THREE.MeshStandardMaterial(cor === "quadriculada" ? { map: xt, roughness: 0.6, side: THREE.DoubleSide } : { color: cor, roughness: 0.55, side: THREE.DoubleSide }));
    pano.position.set(0, 3.75, 0);
    pano.castShadow = true;
    g.add(mastro, pano);
    sets.pista.add(g);
    return { g, pano };
  });

  // carros
  const sombra = new THREE.MeshBasicMaterial({ map: degradeRadial("rgba(0,0,0,.74)"), transparent: true, depthWrite: false });
  const fazer = (mod: THREE.Group, pai: THREE.Object3D = cena) => {
    const g = new THREE.Group();
    const c = mod.clone();
    g.add(c, plano(2.5, 6.2, 0, 0, sombra));
    pai.add(g);
    return g;
  };
  const modelos = EQUIPES.map((p) => carro(p));
  const carros = Array.from({ length: 22 }, (_, k) => fazer(modelos[Math.floor(k / 2)]));
  const mCinza = carro(CINZA);
  const cinzas = Array.from({ length: 22 }, () => fazer(mCinza));
  const halos = Array.from({ length: 22 }, () => {
    const h = plano(9, 13, 0, 0, new THREE.MeshBasicMaterial({ map: degradeRadial("rgba(255,255,255,1)"), transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }), 0.03);
    cena.add(h);
    return h;
  });

  // Safety Car com barra de luzes
  const sc = new THREE.Group();
  const { carro: modeloSc } = vantage();
  sc.add(modeloSc, plano(2.7, 5.6, 0, 0, sombra));
  cena.add(sc);
  sc.add(bloco(1.05, 0.05, 0.2, 0, 1.3, 0.42, mat("#101116", 0.4)));
  const luzesSc = [0, 1].map(() => new THREE.MeshStandardMaterial({ color: "#3a2a00", emissive: "#ffae00", emissiveIntensity: 0 }));
  luzesSc.forEach((m, k) => {
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.06, 0.16), m);
    l.position.set(k ? 0.27 : -0.27, 1.355, 0.42);
    sc.add(l);
  });
  const batido = fazer(modelos[3]);

  // partículas: fumaça, migalhas, confete, luzes desfocadas, ar
  const tPart = degradeRadial("rgba(255,255,255,1)");
  const parts = Array.from({ length: 140 }, () => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tPart, transparent: true, depthWrite: false }));
    cena.add(s);
    return s;
  });

  // circuito visto do alto
  const curva = new THREE.CatmullRomCurve3([[-60, 175], [50, 185], [88, 92], [38, 40], [84, -40], [62, -150], [-10, -178], [-72, -122], [-28, -40], [-92, 30], [-88, 122]].map(([x, z]) => new THREE.Vector3(x, 0, z)), true);
  const circuitoPontos = curva.getSpacedPoints(500);
  const grama = new THREE.Mesh(new THREE.PlaneGeometry(2600, 2600), mat("#2c7440", 1));
  grama.rotation.x = -Math.PI / 2;
  grama.position.y = -0.2;
  sets.circuito.add(grama);
  sets.circuito.add(faixaCurva(circuitoPontos, 15, 0.1, new THREE.MeshStandardMaterial({ color: "#eee9dc", side: THREE.DoubleSide })));
  sets.circuito.add(faixaCurva(circuitoPontos, 12.4, 0.2, new THREE.MeshStandardMaterial({ color: "#3a3d45", roughness: 0.95, side: THREE.DoubleSide })));
  const rastro = faixaCurva(circuitoPontos, 6, 0.32, new THREE.MeshBasicMaterial({ color: "#ff6a1a", side: THREE.DoubleSide }));
  sets.circuito.add(rastro);
  const arvoresC = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 10, 8), new THREE.MeshStandardMaterial({ roughness: 1 }), 500);
  for (let i = 0; i < 500; i++) {
    const a = seed(i + 40) * 6.283;
    const d = 40 + seed(i + 80) * 340;
    const px_ = Math.cos(a) * d;
    const pz = Math.sin(a) * d * 1.3;
    const longeDaPista = circuitoPontos.every((p, k) => k % 8 !== 0 || Math.hypot(p.x - px_, p.z - pz) > 18);
    aux.position.set(px_, longeDaPista ? 3 : -30, pz);
    aux.scale.setScalar(4 + seed(i + 5) * 5);
    aux.updateMatrix();
    arvoresC.setMatrixAt(i, aux.matrix);
    arvoresC.setColorAt(i, new THREE.Color().setHSL(0.31 + seed(i) * 0.07, 0.5, 0.18 + seed(i + 3) * 0.12));
  }
  sets.circuito.add(arvoresC);
  const marcador = new THREE.Mesh(new THREE.SphereGeometry(5, 20, 14), new THREE.MeshBasicMaterial({ color: "#fff6dc" }));
  sets.circuito.add(marcador);

  // estúdio: chão infinito para pneus, pontos, troféu e moedas
  const chao = mat("#0e1528", 0.55);
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(1200, 1200), chao);
  piso.rotation.x = -Math.PI / 2;
  piso.receiveShadow = true;
  sets.estudio.add(piso);
  const pneus = [pneu(), pneu(), pneu()];
  pneus.forEach((p) => sets.estudio.add(p.g));
  const pontos = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1];
  const barras = pontos.map((n, k) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(2.1, 1, 2.1), new THREE.MeshStandardMaterial({ color: k === 0 ? "#f0b92e" : k === 1 ? "#c5ccd8" : k === 2 ? "#d0813f" : "#3b6fd8", roughness: 0.35, metalness: 0.4 }));
    m.castShadow = true;
    const rotulo = new THREE.Sprite(new THREE.SpriteMaterial({ map: rotuloTextura(String(n)), transparent: true, depthWrite: false, depthTest: false }));
    rotulo.scale.set(2.8, 1.4, 1);
    sets.estudio.add(m, rotulo);
    return { m, rotulo };
  });
  const trof = trofeu();
  sets.estudio.add(trof);
  const moedas = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.8, 0.8, 0.2, 40), new THREE.MeshStandardMaterial({ color: "#e0ad2c", roughness: 0.28, metalness: 0.95 }), 180);
  moedas.castShadow = true;
  sets.estudio.add(moedas);
  const teto = new THREE.Mesh(new THREE.PlaneGeometry(40, 16), new THREE.MeshBasicMaterial({ color: "#e0261c", transparent: true, opacity: 0.55, side: THREE.DoubleSide }));
  teto.rotation.x = Math.PI / 2;
  sets.estudio.add(teto);
  const asa = new THREE.Group();
  const pAsa = mat("#d11f4e", 0.35, 0.2);
  const pPreto = mat("#121318", 0.45);
  asa.add(bloco(0.09, 0.95, 1, -1.35, 1.85, 0, pAsa), bloco(0.09, 0.95, 1, 1.35, 1.85, 0, pAsa), bloco(2.7, 0.08, 0.5, 0, 1.55, 0.2, pAsa), bloco(0.1, 1.4, 0.16, -0.25, 0.7, 0.1, pPreto), bloco(0.1, 1.4, 0.16, 0.25, 0.7, 0.1, pPreto));
  const flap = new THREE.Group();
  flap.position.set(0, 1.86, -0.05);
  const lamina = bloco(2.7, 0.07, 0.56, 0, 0, -0.26, new THREE.MeshStandardMaterial({ color: "#f4f1ea", roughness: 0.35 }));
  flap.add(lamina);
  asa.add(flap);
  sets.estudio.add(asa);

  // box: vistos de cima no pit stop, no drive-through e no stop and go
  const pisoPit = new THREE.Mesh(new THREE.PlaneGeometry(90, 700), mat("#4a4e57", 0.95));
  pisoPit.rotation.x = -Math.PI / 2;
  pisoPit.position.z = -120;
  pisoPit.receiveShadow = true;
  sets.pit.add(pisoPit);
  sets.pit.add(plano(0.3, 700, -5.4, -120, brancoLinha, 0.02), plano(0.3, 700, 12, -120, brancoLinha, 0.02));
  for (let k = 0; k < 9; k++) {
    const c = k === 4 ? "#d11f4e" : EQUIPES[k].base;
    sets.pit.add(bloco(13, 6, 16, 19, 3, -112 + k * 28 - 22, mat("#1f2229", 0.6)), bloco(0.3, 5, 15, 12.6, 2.6, -112 + k * 28 - 22, mat(c, 0.45)));
    sets.pit.add(plano(10, 0.14, 7.4, -104 + k * 28 - 22, brancoLinha, 0.02));
  }
  sets.pit.add(plano(3.6, 8, 0, 0, new THREE.MeshBasicMaterial({ color: "#f0d24a", transparent: true, opacity: 0.45 }), 0.021));
  const roda = Array.from({ length: 4 }, () => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.56, 0.56, 0.5, 28), mat("#141519", 0.6));
    m.rotation.z = Math.PI / 2;
    m.castShadow = true;
    sets.pit.add(m);
    return m;
  });
  const equipe = Array.from({ length: 8 }, () => {
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.34, 1, 6, 12), mat("#d11f4e", 0.6));
    m.castShadow = true;
    sets.pit.add(m);
    return m;
  });
  const cam = new THREE.PerspectiveCamera(40, 1080 / 1920, 0.1, 9000);
  return { r, cena, cam, sol, fundos, sets, carros, cinzas, halos, parts, sc, luzesSc, batido, amarelo, linhaChegada, portico, lampadas, brilhos, bandeiras, rastro, marcador, chao, pneus, barras, trofeu: trof, moedas, teto, asa, flap, roda, equipe, circuitoPontos };
}

export type C = { w: Mundo; t: number; s: number; k: number; fim: number; ini: number; em: (x: string) => number };

export const Z_POLE = -100;
export const Z_PORTICO = -111;
export const gridX = (k: number) => (k % 2 ? -1.9 : 1.9);
export const gridZ = (k: number) => Z_POLE + k * 4.4;

export const camera = (w: Mundo, pos: V, olha: V, lente = 40, rolar = 0, topo = false) => {
  w.cam.position.set(...pos);
  w.cam.fov = lente;
  // close de peça pequena (botão do volante): o plano de corte perto da lente acompanha a distância
  // e de muito longe (circuito real visto do alto) ele se afasta, para a profundidade não "brigar" nas camadas da pista
  const dist = Math.hypot(pos[0] - olha[0], pos[1] - olha[1], pos[2] - olha[2]);
  w.cam.near = dist > 300 ? dist * 0.05 : Math.max(0.004, Math.min(0.1, dist * 0.08));
  w.cam.updateProjectionMatrix();
  if (topo) w.cam.up.set(0, 0, -1);
  else w.cam.up.set(Math.sin(rolar), Math.cos(rolar), 0);
  w.cam.lookAt(...olha);
  w.sol.position.set(pos[0] * 0.15 - 18, 60, olha[2] - 24);
  w.sol.target.position.set(olha[0], 0, olha[2]);
  w.sol.target.updateMatrixWorld();
};
/** Câmera que mostra os objetos INTEIROS no quadro vertical (nada cortado), vindo da direção `de` (vetor a partir do
 * centro deles). `folga` > 1 = mais respiro; `alvoY` desloca o ponto para onde olha. Devolve a distância usada. */
export const enquadrar = (w: Mundo, alvo: THREE.Object3D | THREE.Object3D[], de: V = [0.6, 0.35, 1], folga = 1.15, lente = 36, alvoY = 0) => {
  const caixa = new THREE.Box3();
  // Peças que giram no próprio eixo (rotor do freio: userData.giroLivre) entram na caixa PARADAS: a caixa alinhada aos
  // eixos de um disco girando cresce e encolhe (até 41% a 45°) e a câmera se aproximava e se afastava a cada volta,
  // "peça pulando e mudando de tamanho" (freios, 2026-11-13).
  const girando: [THREE.Object3D, THREE.Euler][] = [];
  for (const o of Array.isArray(alvo) ? alvo : [alvo])
    o.traverse((x) => {
      if (x.userData.giroLivre) {
        girando.push([x, x.rotation.clone()]);
        x.rotation.set(0, 0, 0);
      }
    });
  for (const o of Array.isArray(alvo) ? alvo : [alvo]) {
    o.updateMatrixWorld(true);
    // chão grande do modelo (grama do circuito, mar do mapa) não conta: marcado com userData.foraDoEnquadro
    o.traverse((x) => {
      if ((x as THREE.Mesh).isMesh && !x.userData.foraDoEnquadro && !x.parent?.userData.foraDoEnquadro) caixa.union(new THREE.Box3().setFromObject(x, false));
    });
  }
  for (const [x, r] of girando) x.rotation.copy(r);
  for (const o of Array.isArray(alvo) ? alvo : [alvo]) if (girando.length) o.updateMatrixWorld(true);
  if (caixa.isEmpty()) return 0;
  const centro = caixa.getCenter(new THREE.Vector3());
  centro.y += alvoY;
  const dir = new THREE.Vector3(...de).normalize();
  const cima = Math.abs(dir.y) > 0.97 ? new THREE.Vector3(0, 0, -1) : new THREE.Vector3(0, 1, 0);
  const direita = new THREE.Vector3().crossVectors(cima, dir).normalize();
  const alto = new THREE.Vector3().crossVectors(dir, direita);
  const tv = Math.tan((lente * Math.PI) / 360);
  const th = tv * w.cam.aspect;
  let d = 0.5;
  for (const x of [caixa.min.x, caixa.max.x]) for (const y of [caixa.min.y, caixa.max.y]) for (const z of [caixa.min.z, caixa.max.z]) {
    const c = new THREE.Vector3(x, y, z).sub(centro);
    const prof = c.dot(dir);
    d = Math.max(d, prof + (Math.abs(c.dot(direita)) * folga) / th, prof + (Math.abs(c.dot(alto)) * folga) / tv);
  }
  const pos = centro.clone().addScaledVector(dir, d);
  camera(w, [pos.x, pos.y, pos.z], [centro.x, centro.y, centro.z], lente, 0, Math.abs(dir.y) > 0.97);
  if ((Array.isArray(alvo) ? alvo : [alvo]).some((o) => o.userData.circuito)) afastarNevoa(w, d);
  return d;
};
/** Circuito grande visto de longe (Las Vegas: 2 km de ponta a ponta, câmera a mais de 3 km): a névoa recua com a câmera
 *  para o traçado não sumir no branco. Até 3,2 km nada muda (Interlagos fica como estava). */
export const afastarNevoa = (w: Mundo, d: number) => {
  if (d <= 3200) return;
  const nv = w.cena.fog as THREE.Fog;
  nv.near = Math.max(nv.near, d * 1.05);
  nv.far = Math.max(nv.far, d * 2.4);
};
export const poe = (w: Mundo, k: number, x: number, z: number, giro = 0) => {
  const c = w.carros[k];
  c.visible = true;
  c.position.set(x, 0, z);
  c.rotation.y = giro;
  c.scale.setScalar(1); // uma vista de longe pode ter aumentado o carro (poeNoCircuito)
};
export const poeCinza = (w: Mundo, k: number, x: number, z: number) => {
  w.cinzas[k].visible = true;
  w.cinzas[k].position.set(x, 0, z);
};
export const halo = (w: Mundo, n: number, x: number, z: number, cor: string, op = 0.8) => {
  const h = w.halos[n];
  h.visible = true;
  h.position.x = x;
  h.position.z = z;
  (h.material as THREE.MeshBasicMaterial).color.set(cor);
  (h.material as THREE.MeshBasicMaterial).opacity = op;
};
export const grade = (w: Mundo, n: number, dz = 0) => {
  for (let k = 0; k < n; k++) poe(w, k, gridX(k), gridZ(k) + dz);
};
type Part = { p: V; e: number; cor: string; o: number };
export const solta = (w: Mundo, n: number, f: (i: number) => Part, modo: THREE.Blending = THREE.NormalBlending) => {
  for (let i = 0; i < n; i++) {
    const { p, e, cor, o } = f(i);
    const s = w.parts[i];
    s.visible = true;
    s.position.set(...p);
    s.scale.set(e, e, 1);
    const m = s.material as THREE.SpriteMaterial;
    m.color.set(cor);
    m.opacity = o;
    m.blending = modo;
  }
};
export const fumaca = (w: Mundo, t: number, x: number, z: number) =>
  solta(w, 30, (k) => {
    const vida = (t * (0.3 + (k % 5) * 0.05) + k * 0.137) % 1;
    return { p: [x + Math.sin(k * 7) * 1.2 + vida * 2.2, 0.4 + vida * 6, z + Math.cos(k * 3) * 1.2], e: 1 + vida * 5, cor: "#d6d6da", o: (1 - vida) * 0.55 };
  });
export const confete = (w: Mundo, t: number, ini: number, cx = 0, alto = 12) => {
  const cores = ["#ffd21f", "#f4f1ea", "#e8324a", "#35b6ff", "#3bd47a"];
  solta(w, 100, (i) => {
    const s = t - ini;
    const y = alto + seed(i) * 8 - s * (2.2 + seed(i + 3) * 1.8);
    return { p: [cx + (seed(i + 1) - 0.5) * 18 + Math.sin(s * 3 + i) * 0.5, y, (seed(i + 2) - 0.5) * 14], e: 0.2 + seed(i + 4) * 0.16, cor: cores[i % 5], o: s < 0 || y < 0 ? 0 : 1 };
  });
};
const noCircuito = (w: Mundo, u: number) => {
  const pts = w.circuitoPontos;
  const f = (((u % 1) + 1) % 1) * (pts.length - 1);
  return pts[Math.floor(f)];
};
export const drawRastro = (w: Mundo, u: number) => {
  (w.rastro.geometry as THREE.BufferGeometry).setDrawRange(0, Math.floor(u * 499) * 6);
  const p = noCircuito(w, u);
  w.marcador.position.set(p.x, 3, p.z);
};
export const camCircuito = (w: Mundo, s: number, ang = 0.2, d = 840) => {
  const a = ang + s * 0.035;
  camera(w, [Math.sin(a) * d * 0.46, d * 0.86, Math.cos(a) * d * 0.46], [0, 0, 0], 38);
};
export const pneuCor = ["#e6241f", "#ffd21f", "#f2f2f2", "#23b458", "#2b7be8"];
export const poePneu = (w: Mundo, n: number, x: number, y: number, z: number, cor: string, giro: number, frenteY = 0, esc = 1) => {
  const p = w.pneus[n];
  p.g.visible = true;
  p.g.position.set(x, y, z);
  p.g.rotation.set(0, frenteY, Math.PI / 2);
  p.g.scale.setScalar(esc);
  p.giro.rotation.y = giro;
  aplicarComposto(p.giro, cor);
};
export const luzesDesfocadas = (w: Mundo, t: number) =>
  solta(w, 26, (i) => ({ p: [(seed(i) - 0.5) * 34 + Math.sin(t * 0.4 + i) * 0.5, 0.6 + seed(i + 1) * 10, -14 - seed(i + 2) * 14], e: 1.6 + seed(i + 3) * 3, cor: ["#5e8bff", "#ffb35c", "#ff5470", "#7ae0ff"][i % 4], o: 0.28 }), THREE.AdditiveBlending);
export const bandeira = (w: Mundo, n: number, x: number, z: number, ry: number, t: number, esc = 1) => {
  const b = w.bandeiras[n];
  b.g.visible = true;
  b.g.position.set(x, 0, z);
  b.g.rotation.y = ry;
  b.g.scale.setScalar(esc);
  const pos = b.pano.geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const u = pos.getX(i) + 1.05;
    pos.setZ(i, Math.sin(u * 3.6 - t * 10 + pos.getY(i) * 0.7 + n) * 0.11 * (0.3 + u));
  }
  pos.needsUpdate = true;
  b.pano.geometry.computeVertexNormals();
};
export const luzGantry = (w: Mundo, n: number, liga: boolean, sobe = 0) => {
  w.lampadas[n].emissiveIntensity = liga ? 4.5 : 0;
  w.brilhos[n].visible = liga;
  (w.brilhos[n].material as THREE.SpriteMaterial).opacity = liga ? 0.7 + sobe : 0;
};

export const num = (n: number, d = 0) => n.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });

/** Fundo da legenda onde o cenário claro ou a fumaça a apagariam. */
export const FundoLegenda: React.FC = () => <div style={{ position: "absolute", left: 40, right: 40, top: 282, height: 118, borderRadius: 24, background: "rgba(14,17,24,.72)", zIndex: 30 }} />;

export const Chips: React.FC<{ itens: string[]; ativo: number; quantos?: number; y?: number; cor?: string }> = ({ itens, ativo, quantos = itens.length, y = 1560, cor = "#ffc400" }) => (
  <div style={{ position: "absolute", top: y, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 22, fontFamily: FONTE, zIndex: 40 }}>
    {itens.slice(0, quantos).map((x, k) => (
      <div key={x} style={{ padding: "12px 34px", borderRadius: 22, background: k === ativo ? cor : "rgba(14,17,24,.84)", color: k === ativo ? "#10131a" : "#e6e8ee", fontSize: 58, fontWeight: 800, boxShadow: "0 10px 30px rgba(0,0,0,.45)" }}>{x}</div>
    ))}
  </div>
);


/** Zera o mundo a cada quadro: só aparece o que o plano ativo puser. */
export function preparar(w: Mundo, clima: string, set: string) {
    const cl = CLIMAS[clima] ?? CLIMAS.tarde;
    w.cena.background = w.fundos[clima] ?? w.fundos.tarde;
    const nv = w.cena.fog as THREE.Fog;
    nv.color.set(set === "estudio" && clima !== "claro" ? "#0a0e1a" : cl.nevoa);
    // "real" = circuito de verdade e mapa (geografia.ts): nenhum cenário fixo, névoa bem longe
    nv.near = set === "real" ? 2500 : set === "circuito" ? 2000 : set === "estudio" ? 40 : 90;
    nv.far = set === "real" ? 7000 : set === "circuito" ? 3100 : set === "estudio" ? 120 : 260;
    w.sol.color.set(cl.sol);
    w.sol.intensity = cl.forca;
    for (const [n, g] of Object.entries(w.sets)) g.visible = n === set;
    for (const lista of [w.carros, w.cinzas, w.halos, w.parts, w.roda, w.equipe]) for (const o of lista) o.visible = false;
    for (const b of w.bandeiras) b.g.visible = false;
    for (const o of [w.sc, w.batido, w.portico, w.trofeu, w.moedas, w.teto, w.asa]) o.visible = false;
    for (const o of w.pneus) o.g.visible = false;
    for (const b of w.barras) {
      b.m.visible = false;
      b.rotulo.visible = false;
    }
    w.marcador.visible = true;
    w.amarelo.opacity = 0;
    w.linhaChegada.position.z = -600;
    w.portico.position.set(0, 0, Z_PORTICO);
}
