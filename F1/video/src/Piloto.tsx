// Vídeo piloto: as regras básicas da F1. Cada plano começa numa palavra do roteiro (piloto_palavras.json).
// A pista muda de luz com o assunto; pneus, pontos e teto de gastos ganham cenário próprio.
import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { PINTURAS, carro, degradeRadial, plano, texturaPista, type Pintura } from "./Carro3D";
import { FONTE, Legenda, Placa, entra, noTrecho, suave, type Palavra } from "./kit";
import palavras from "./piloto_palavras.json";
import { vantage } from "./Vantage";

type V = [number, number, number];
const PALAVRAS = palavras as Palavra[];
export const DURACAO_PILOTO = Math.ceil(155.33 * 30);

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

type Pneu = { g: THREE.Group; giro: THREE.Group; anel: THREE.MeshStandardMaterial };
function pneu(): Pneu {
  const g = new THREE.Group();
  const giro = new THREE.Group();
  const perfil = [[0.42, -0.42], [0.62, -0.47], [0.92, -0.47], [1, -0.38], [1.03, -0.2], [1.03, 0.2], [1, 0.38], [0.92, 0.47], [0.62, 0.47], [0.42, 0.42]].map(([r, y]) => new THREE.Vector2(r, y));
  const borracha = new THREE.Mesh(new THREE.LatheGeometry(new THREE.SplineCurve(perfil).getPoints(50), 96), mat("#17181c", 0.62));
  const anel = new THREE.MeshStandardMaterial({ color: "#df1f1f", emissive: "#df1f1f", emissiveIntensity: 0.25, roughness: 0.45 });
  for (const s of [-1, 1]) {
    const a = new THREE.Mesh(new THREE.TorusGeometry(0.76, 0.045, 12, 96), anel);
    a.rotation.x = Math.PI / 2;
    a.position.y = s * 0.475;
    giro.add(a);
    for (let k = 0; k < 6; k++) {
      const u = (k / 6) * Math.PI * 2;
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.012, 0.05), mat("#e9e9ee", 0.5));
      m.position.set(Math.cos(u) * 0.88, s * 0.475, Math.sin(u) * 0.88);
      m.rotation.y = -u;
      giro.add(m);
    }
  }
  const aro = new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.43, 0.72, 48), mat("#3a3d44", 0.28, 0.9));
  giro.add(borracha, aro);
  for (let k = 0; k < 10; k++) {
    const raio = bloco(0.38, 0.03, 0.06, Math.cos((k / 10) * 6.283) * 0.2, 0.37, Math.sin((k / 10) * 6.283) * 0.2, mat("#c9ccd4", 0.25, 0.9));
    raio.rotation.y = -(k / 10) * 6.283;
    giro.add(raio);
  }
  const miolo = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.8, 24), mat("#d4213c", 0.3, 0.7));
  giro.add(miolo);
  giro.traverse((o) => (o.castShadow = true));
  g.rotation.z = Math.PI / 2;
  g.add(giro);
  return { g, giro, anel };
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
    c.scale.set(0.7, 0.9, 1.1);
    g.add(c, plano(2.5, 7.2, 0, 0, sombra));
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
  const cam = new THREE.PerspectiveCamera(40, 1080 / 1920, 0.1, 3200);
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
  w.cam.updateProjectionMatrix();
  if (topo) w.cam.up.set(0, 0, -1);
  else w.cam.up.set(Math.sin(rolar), Math.cos(rolar), 0);
  w.cam.lookAt(...olha);
  w.sol.position.set(pos[0] * 0.15 - 18, 60, olha[2] - 24);
  w.sol.target.position.set(olha[0], 0, olha[2]);
  w.sol.target.updateMatrixWorld();
};
export const poe = (w: Mundo, k: number, x: number, z: number, giro = 0) => {
  const c = w.carros[k];
  c.visible = true;
  c.position.set(x, 0, z);
  c.rotation.y = giro;
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
  p.anel.color.set(cor);
  p.anel.emissive.set(cor);
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

type Plano = { em: string; clima: string; set: string; cena: (c: C) => void; ui?: (c: C) => ReactNode };

const PLANOS: Plano[] = [
  // Abertura: voo rasante pelo grid até a pole
  { em: "Neste vídeo", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    grade(w, 22);
    const v = 1 - Math.pow(1 - Math.min(1, s / 2.1), 3);
    const z = gridZ(21) + 30 + (Z_POLE + 12 - gridZ(21) - 30) * v;
    camera(w, [0.2 + Math.sin(s * 1.1) * 0.4, 2.2 + v * 4.6, z + 9 + s * 0.4], [0, 0.5, z - 10], 48, Math.sin(s * 1.6) * 0.02 * (1 - v));
  } },
  { em: "São onze", clima: "tarde", set: "pista", cena: ({ w, s, t, em }) => {
    const n = Math.min(11, Math.floor(1 + (t - em("onze")) * 11 / 0.9));
    for (let k = 0; k < n; k++) poe(w, k * 2, 0, Z_POLE + k * 7.2);
    camera(w, [0, 92 - s * 3, Z_POLE + 36], [0, 0, Z_POLE + 36], 38, 0, true);
  }, ui: ({ em }) => <Placa texto="11" unidade="equipes" inicio={em("onze")} x={540} y={1640} /> },
  { em: "cada uma", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    poe(w, 4, -1.9, Z_POLE);
    poe(w, 5, 1.9, Z_POLE);
    const a = -0.75 + s * 0.28;
    camera(w, [Math.sin(a) * 10, 1.25 + s * 0.2, Z_POLE - 11 + Math.abs(Math.cos(a)) * 0.2], [0, 0.65, Z_POLE], 34);
  }, ui: ({ em }) => <Placa texto="2" unidade="pilotos" inicio={em("dois pilotos")} x={540} y={1640} /> },
  { em: "vinte e dois", clima: "tarde", set: "pista", cena: ({ w, k }) => {
    grade(w, 22);
    const su = suave(k, 0, 1);
    camera(w, [2 - su * 2, 5 + su * 62, Z_POLE - 12 + su * 58], [0, 0, Z_POLE + 46], 42);
  }, ui: ({ t, em }) => {
    const n = Math.round(22 * entra(t, em("vinte"), 1));
    return <Placa texto={String(n)} unidade="carros" inicio={em("vinte")} x={540} y={1640} cor={n === 22 ? "#ffc400" : "#fff"} />;
  } },
  { em: "Em 2026, a Cadillac", clima: "tarde", set: "pista", cena: ({ w, s, t, em }) => {
    poe(w, iCadillac * 2, 0, Z_POLE);
    halo(w, 0, 0, Z_POLE, "#ffd77a", 0.55 * entra(t, em("Cadillac"), 0.5));
    const a = 2.5 + s * 0.3;
    camera(w, [Math.sin(a) * 8, 1.1 + s * 0.14, Z_POLE + Math.cos(a) * 8], [0, 0.6, Z_POLE], 32);
  }, ui: ({ em }) => <Placa texto="CADILLAC" unidade="2026" inicio={em("Cadillac")} x={540} y={1640} tam={84} cor="#ffd77a" /> },

  // O fim de semana: a luz muda com o dia
  { em: "O fim de semana", clima: "manha", set: "circuito", cena: ({ w, s }) => {
    drawRastro(w, 0);
    w.marcador.visible = false;
    camCircuito(w, s);
  }, ui: ({ t, em }) => <Chips itens={["SEX", "SÁB", "DOM"]} ativo={-1} quantos={t < em("três dias") ? 0 : 3} y={1600} /> },
  { em: "Na sexta,", clima: "manha", set: "pista", cena: ({ w, s }) => {
    const z = -80 - 72 * s;
    poe(w, 8, -1.2, z);
    camera(w, [-5.4 + s * 0.9, 1 + s * 0.3, z + 8.5], [-1.2, 0.6, z - 2], 46);
  }, ui: () => <><Chips itens={["SEX", "SÁB", "DOM"]} ativo={0} y={1600} /><Placa texto="treinos livres" inicio={0} x={540} y={1470} tam={62} /></> },
  { em: "No sábado,", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    const z = -80 - 88 * s;
    poe(w, 2, 0, z);
    camera(w, [7.2, 0.8, z - 2 - s * 2.4], [0, 0.6, z], 38);
  }, ui: ({ s }) => {
    const x = 78.2 + s * 2.1;
    return <><Chips itens={["SEX", "SÁB", "DOM"]} ativo={1} y={1600} /><Placa texto={`1:${num(Math.floor(x - 60)).padStart(2, "0")},${String(Math.floor((x % 1) * 1000)).padStart(3, "0")}`} inicio={0} x={540} y={1470} tam={70} /></>;
  } },
  { em: "a classificação, que", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    grade(w, 4);
    halo(w, 0, gridX(0), Z_POLE, "#ffd77a", 0.45);
    camera(w, [gridX(0) + 1, 44 - s * 7, Z_POLE + 2], [gridX(0), 0, Z_POLE + 2], 28, 0, true);
  }, ui: () => <Chips itens={["SEX", "SÁB", "DOM"]} ativo={1} y={1600} /> },
  { em: "E no domingo,", clima: "sol", set: "pista", cena: ({ w, s }) => {
    for (let k = 0; k < 22; k++) poe(w, k, gridX(k), Z_POLE - 86 * s - 1.5 * s * s + k * 6.2);
    const z = Z_POLE - 86 * s - 1.5 * s * s;
    camera(w, [7, 2 + s * 1.8, z - 18 + s * 4], [0, 0.5, z + 12], 42);
  }, ui: () => <Chips itens={["SEX", "SÁB", "DOM"]} ativo={2} y={1600} /> },
  { em: "Em alguns fins", clima: "sol", set: "circuito", cena: ({ w, k, s }) => {
    drawRastro(w, suave(k, 0.15, 0.95) * 0.34);
    camCircuito(w, s, 0.05, 840);
  }, ui: ({ em }) => <Placa texto="sprint" unidade="1/3 da corrida" inicio={em("sprint")} x={540} y={1620} tam={72} cor="#ffb066" /> },

  // Classificação: de 22 para 10
  { em: "A classificação tem", clima: "noite", set: "pista", cena: ({ w, s }) => {
    grade(w, 22);
    camera(w, [10 - s * 2, 15 + s * 3, Z_POLE + 66], [0, 0, Z_POLE + 26], 42);
  }, ui: ({ t, em }) => <Chips itens={["Q1", "Q2", "Q3"]} ativo={-1} quantos={t < em("três fases") ? 0 : 3} /> },
  { em: "No Q1,", clima: "noite", set: "pista", cena: ({ w, s, t, em }) => {
    const m = em("seis carros");
    const sai = suave(t, em("ficam") , em("caminho") + 0.1);
    for (let k = 0; k < 16; k++) poe(w, k, gridX(k), gridZ(k));
    for (let k = 16; k < 22; k++) {
      if (t < m) poe(w, k, gridX(k), gridZ(k));
      else {
        const x = gridX(k) + Math.sign(gridX(k)) * sai * 30;
        poeCinza(w, k, x, gridZ(k));
        halo(w, k, x, gridZ(k), "#ff2a20", 0.95);
      }
    }
    camera(w, [0, 74 - s * 2, Z_POLE + 68], [0, 0, Z_POLE + 46], 40);
  }, ui: ({ t, em }) => {
    const n = t < em("ficam") ? 22 : Math.round(22 - 6 * suave(t, em("ficam"), em("caminho")));
    return <><Chips itens={["Q1", "Q2", "Q3"]} ativo={0} /><Placa texto={String(n)} unidade="carros" inicio={0} x={540} y={1440} cor={n === 16 ? "#ff5a4a" : "#fff"} /></>;
  } },
  { em: "No Q2,", clima: "noite", set: "pista", cena: ({ w, s, t, em }) => {
    const m = em("mais seis");
    const sai = suave(t, m + 0.2, em("eliminados") + 0.2);
    for (let k = 0; k < 10; k++) poe(w, k, gridX(k), gridZ(k));
    for (let k = 10; k < 16; k++) {
      if (t < m) poe(w, k, gridX(k), gridZ(k));
      else {
        const x = gridX(k) + Math.sign(gridX(k)) * sai * 30;
        poeCinza(w, k, x, gridZ(k));
        halo(w, k, x, gridZ(k), "#ff2a20", 0.95);
      }
    }
    camera(w, [-16 + s * 3, 44, Z_POLE + 74], [0, 0, Z_POLE + 28], 36);
  }, ui: ({ t, em }) => {
    const n = Math.round(16 - 6 * suave(t, em("mais seis") + 0.2, em("eliminados")));
    return <><Chips itens={["Q1", "Q2", "Q3"]} ativo={1} /><Placa texto={String(n)} unidade="carros" inicio={0} x={540} y={1440} cor={n === 10 ? "#ff5a4a" : "#fff"} /></>;
  } },
  { em: "E os dez", clima: "noite", set: "pista", cena: ({ w, s }) => {
    const z = -130 - 74 * s;
    for (let k = 0; k < 10; k++) poe(w, k, (k % 2 ? -1 : 1) * 2, z + k * 8);
    camera(w, [5, 1.4 + s * 1.4, z + 86 - s * 12], [0, 0.6, z + 20], 34);
  }, ui: () => <Chips itens={["Q1", "Q2", "Q3"]} ativo={2} /> },
  { em: "pela pole position:", clima: "noite", set: "pista", cena: ({ w, s, t, em }) => {
    grade(w, 4);
    halo(w, 0, gridX(0), Z_POLE, "#ffd77a", 0.75 * entra(t, em("primeira"), 0.4) + 0.2);
    const a = 0.7 + s * 0.22;
    camera(w, [gridX(0) + Math.sin(a) * 9, 3.2 - s * 0.4, Z_POLE + Math.cos(a) * -9], [gridX(0), 0.6, Z_POLE], 30);
  }, ui: ({ em }) => <Placa texto="P1" unidade="pole position" inicio={em("primeira")} x={540} y={1600} cor="#ffd77a" /> },

  // Largada
  { em: "Na largada,", clima: "brasa", set: "pista", cena: ({ w, s, t, em }) => {
    grade(w, 12);
    w.portico.visible = true;
    const a = em("cinco luzes");
    const b = em("acendem") + 0.1;
    for (let n = 0; n < 5; n++) luzGantry(w, n, t >= a + (b - a) * (n / 5));
    camera(w, [Math.sin(s) * 0.4, 1 + s * 0.2, Z_POLE + 12 - s * 0.7], [0, 5.4, Z_PORTICO], 40);
  } },
  { em: "Quando todas", clima: "brasa", set: "pista", cena: ({ w, s, t, em }) => {
    w.portico.visible = true;
    grade(w, 2);
    const off = em("apagam");
    for (let n = 0; n < 5; n++) luzGantry(w, n, t < off);
    camera(w, [0.1, 5.8, Z_PORTICO + 27 - Math.min(s, 2) * 3], [0, 6.2, Z_PORTICO], 30);
  } },
  { em: "começa a corrida!", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    const pulo = (k: number) => Math.max(0, s - k * 0.012);
    for (let k = 0; k < 22; k++) poe(w, k, gridX(k) * (1 - Math.min(1, s * 0.15)), gridZ(k) - 16 * pulo(k) * pulo(k));
    w.portico.visible = true;
    for (let n = 0; n < 5; n++) luzGantry(w, n, false);
    const z = Z_POLE - 16 * s * s;
    camera(w, [4.2 + Math.sin(s * 40) * 0.03, 0.75 + Math.sin(s * 55) * 0.02, z + 12 + s * 3], [0, 0.4, z - 3], 54, Math.sin(s * 3) * 0.015);
  } },

  // Duração
  { em: "A prova tem", clima: "tarde", set: "circuito", cena: ({ w, k, s }) => {
    drawRastro(w, suave(k, 0.25, 0.95) * 0.999);
    camCircuito(w, s, -0.1, 840);
  }, ui: ({ t, em, k }) => <Placa texto={num(Math.round(305 * suave(k, 0.25, 0.95)))} unidade="km" inicio={em("300")} x={540} y={1640} cor={k > 0.93 ? "#ffb066" : "#fff"} /> },
  { em: "e dura,", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    const z = -300;
    for (let k = 0; k < 6; k++) poe(w, k * 3, (k % 2 ? -2 : 2), z + 90 - 84 * s + k * 16);
    camera(w, [10.5 - s * 0.5, 1.2, z - 8], [0, 0.8, z + 5], 40);
  }, ui: ({ k }) => {
    const m = Math.round(180 * suave(k, 0.05, 0.9));
    const fim = m >= 180;
    return <Placa texto={`${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}:00`} unidade="h" inicio={0} x={540} y={1640} cor={fim ? "#ff5a4a" : "#fff"} />;
  } },

  // Pneus: mundo noturno
  { em: "Os pneus têm", clima: "vazio", set: "estudio", cena: ({ w, s, t }) => {
    w.chao.color.set("#0e1528");
    luzesDesfocadas(w, t);
    const q = (d: number) => {
      const u = Math.max(0, s - d);
      return Math.max(1.03, 16 - 42 * u * u) + (u > 0.6 ? Math.abs(Math.sin((u - 0.6) * 9)) * 0.55 * Math.exp(-(u - 0.6) * 4) : 0);
    };
    poePneu(w, 0, -2.45, q(0), 0, pneuCor[0], s * 2.5, -0.15);
    poePneu(w, 1, 0, q(0.18), 0.6, pneuCor[1], s * 2.5);
    poePneu(w, 2, 2.45, q(0.36), 0, pneuCor[2], s * 2.5, 0.15);
    camera(w, [0, 2.2, 25 - s * 0.7], [0, 1.4, 0], 30);
    for (const p of w.pneus) p.g.rotation.y += Math.PI / 2;
  } },
  { em: "o vermelho é", clima: "vazio", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#16101a");
    luzesDesfocadas(w, t);
    poePneu(w, 0, 0, 1.03, 0, pneuCor[0], s * 5, Math.PI / 2);
    const g = em("gasta");
    if (t >= g) {
      const pool = w.parts;
      for (let i = 26; i < 110; i++) {
        const u = ((t - g) * (0.9 + seed(i) * 0.7) + seed(i + 7)) % 1;
        const a = seed(i + 2) * 3.1;
        pool[i].visible = true;
        pool[i].position.set(Math.cos(a) * (1 + u * 3.4), 1.03 + Math.sin(a) * (1 + u * 2.4) - u * u * 1.4, 0.4 + seed(i + 5) * 0.6);
        pool[i].scale.setScalar(0.13 + seed(i + 3) * 0.13);
        (pool[i].material as THREE.SpriteMaterial).color.set("#34302f");
        (pool[i].material as THREE.SpriteMaterial).opacity = 1 - u;
        (pool[i].material as THREE.SpriteMaterial).blending = THREE.NormalBlending;
      }
    }
    const a = -0.5 + s * 0.17;
    camera(w, [Math.sin(a) * 6.6, 2 + Math.sin(s) * 0.2, Math.cos(a) * 6.6], [0, 1.03, 0], 30);
  }, ui: ({ t, em }) => {
    const v = 100 - 78 * suave(t, em("gasta"), em("logo") + 0.8);
    return <><Placa texto="MACIO" inicio={0} x={540} y={1470} cor="#ff5a4a" tam={72} />{t >= em("rápido,") && <Placa texto={num(v)} unidade="% de vida" inicio={em("rápido,")} x={540} y={1640} tam={64} cor={v < 40 ? "#ff5a4a" : "#fff"} />}</>;
  } },
  { em: "o amarelo é", clima: "vazio", set: "estudio", cena: ({ w, s, t }) => {
    w.chao.color.set("#16140d");
    luzesDesfocadas(w, t);
    poePneu(w, 0, 0, 1.03, 0, pneuCor[1], s * 3.6, Math.PI / 2);
    camera(w, [4.6 - s * 0.6, 0.85, 5.2], [0, 1.1, 0], 34, 0.07);
  }, ui: () => <Placa texto="MÉDIO" inicio={0} x={540} y={1470} cor="#ffd21f" tam={72} /> },
  { em: "e o branco", clima: "vazio", set: "estudio", cena: ({ w, s, t }) => {
    w.chao.color.set("#10131c");
    luzesDesfocadas(w, t);
    poePneu(w, 0, 0, 1.03, 0, pneuCor[2], s * 1.8, Math.PI / 2);
    camera(w, [-3.8 + s * 0.4, 3.2 - s * 0.5, 5.6], [0, 1, 0], 32);
  }, ui: ({ k }) => <><Placa texto="DURO" inicio={0} x={540} y={1470} cor="#ffffff" tam={72} /><Placa texto={num(100 - 18 * k)} unidade="% de vida" inicio={0} x={540} y={1640} tam={64} /></> },
  { em: "Verde e azul", clima: "chumbo", set: "estudio", cena: ({ w, s }) => {
    w.chao.color.set("#28303d");
    poePneu(w, 0, -1.25, 1.03, 0, pneuCor[3], s * 2, Math.PI / 2);
    poePneu(w, 1, 1.25, 1.03, 0, pneuCor[4], s * 2, Math.PI / 2);
    camera(w, [s * 0.5, 1.7, 17 - s * 0.8], [0, 1.3, 0], 30);
  }, ui: ({ t }) => (
    <>
      <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, zIndex: 20 }}>
        {Array.from({ length: 90 }, (_, i) => {
          const x = seed(i) * 1200 - 60;
          const y = (seed(i + 3) * 2100 + t * 2400 * (0.8 + seed(i + 5) * 0.4)) % 2100 - 100;
          return <line key={i} x1={x} y1={y} x2={x - 10} y2={y + 66} stroke="#cfe3ff" strokeOpacity={0.42} strokeWidth={3} />;
        })}
      </svg>
      <Placa texto="CHUVA" inicio={0} x={540} y={1640} cor="#7fc4ff" tam={72} />
    </>
  ) },
  { em: "Na pista seca,", clima: "sol", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#454a53");
    const o = em("dois tipos");
    poePneu(w, 0, -1.25, 1.03, 0, pneuCor[0], s * 3, Math.PI / 2);
    if (t >= o) poePneu(w, 1, 1.25, 1.03 + Math.max(0, 3 - (t - o) * 14), 0, pneuCor[2], s * 3, Math.PI / 2);
    camera(w, [-1.8 + s * 0.9, 2.3, 17], [0, 1.3, 0], 30);
  }, ui: ({ em }) => <Placa texto="2" unidade="tipos, obrigatório" inicio={em("dois tipos")} x={540} y={1640} cor="#ffc400" tam={76} /> },
  { em: "e por isso", clima: "sol", set: "pit", cena: ({ w, s, fim }) => {
    const ch = Math.min(1, s / Math.max(0.2, fim * 0.8));
    const z = -130 * Math.pow(1 - ch, 2.2);
    poe(w, 8, 0, z);
    w.equipe.forEach((m, n) => {
      m.visible = true;
      m.position.set((n % 2 ? -1 : 1) * (2.1 + (n % 4 > 1 ? 0.8 : 0)), 0.85, (n < 4 ? -2.1 : 2.1) + (n % 4 > 1 ? 0.8 : 0));
      (m.material as THREE.MeshStandardMaterial).color.set("#d11f4e");
    });
    camera(w, [-6 + s, 11, z + 14 - s], [0, 0.6, z - 1], 40);
  } },
  { em: "trocar os pneus", clima: "sol", set: "pit", cena: ({ w, s, k }) => {
    poe(w, 8, 0, 0);
    const sai = suave(s, 0.25, 0.6) * (1 - suave(s, 0.9, 1.25));
    [[-1, -1.95], [1, -1.95], [-1, 2.1], [1, 2.1]].forEach(([x, z], n) => {
      w.roda[n].visible = sai > 0.03;
      w.roda[n].position.set(x * (2 + sai * 1.6), 0.56, z);
    });
    w.equipe.forEach((m, n) => {
      m.visible = true;
      m.position.set((n % 2 ? -1 : 1) * 2.3, 0.85, (n < 4 ? -2.1 : 2.1) + (n % 4 > 1 ? 0.9 : -0.6));
    });
    camera(w, [0.5, 19 - k * 5, 0.5], [0, 0, 0], 32, 0, true);
  }, ui: ({ s }) => {
    const x = Math.min(2, s * 1.05);
    return <Placa texto={num(x, 1)} unidade="s" inicio={0} x={540} y={1640} cor={x >= 2 ? "#3bd47a" : "#fff"} />;
  } },

  // Pontos
  { em: "Os dez primeiros", clima: "vazio", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#10141f");
    const marcas = [em("vencedor"), em("segundo"), em("terceiro")];
    const a = em("e assim");
    const b = em("décimo");
    w.barras.forEach((bar, n) => {
      const quando = n < 3 ? marcas[n] : a + (b - a) * ((n - 3) / 7);
      const v = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1][n] * 0.3 * entra(t, quando, 0.45);
      const x = n * 3.05;
      bar.m.visible = v > 0.01;
      bar.m.scale.y = Math.max(0.01, v);
      bar.m.position.set(x, v / 2, 0);
      bar.rotulo.visible = v > 0.05;
      bar.rotulo.position.set(x, v + 1.1, 0);
      (bar.rotulo.material as THREE.SpriteMaterial).opacity = entra(t, quando, 0.3);
    });
    const f = suave(t, a - 0.3, b);
    camera(w, [-12 - f * 1, 8 + f * 6, 21 + f * 1], [3.5 + f * 8, 3.2 - f * 1, 0], 38);
  } },
  { em: "No fim do", clima: "vazio", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#14110b");
    w.trofeu.visible = true;
    w.trofeu.position.set(0, 0, 0);
    w.trofeu.rotation.y = s * 0.8;
    const m = em("campeão!");
    if (t >= m) confete(w, t, m, 0, 9);
    camera(w, [Math.sin(s * 0.3) * 5, 1.1 + s * 0.28, 6.6 - s * 0.4], [0, 1.9, 0], 34);
  }, ui: ({ t, em }) => t >= em("campeão!") ? <Placa texto="CAMPEÃO" inicio={em("campeão!")} x={540} y={1620} cor="#ffd77a" tam={84} /> : null },
  { em: "As equipes também", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    poe(w, 6, -2.1, Z_POLE);
    poe(w, 7, 2.1, Z_POLE);
    const a = 2.7 - s * 0.2;
    camera(w, [Math.sin(a) * 11, 3.4, Z_POLE + Math.cos(a) * 11], [0, 0.6, Z_POLE], 30);
  }, ui: ({ em, t }) => <><Placa texto="25" inicio={em("equipes")} x={300} y={1440} tam={64} /><Placa texto="18" inicio={em("equipes") + 0.25} x={780} y={1440} tam={64} /><Placa texto="CONSTRUTORES" unidade={t >= em("título") ? "43 pontos" : ""} inicio={em("construtores.") - 0.4} x={540} y={1620} tam={62} cor="#ffd77a" /></> },

  // Bandeiras
  { em: "As bandeiras mandam", clima: "tarde", set: "pista", cena: ({ w, s, t }) => {
    for (let n = 0; n < 6; n++) bandeira(w, n, -8.5, -400 - n * 5, -0.5, t, 1.15);
    camera(w, [1 - s * 0.5, 2.4, -386 - s * 2], [-8.5, 3.3, -412], 38);
  } },
  { em: "A verde significa", clima: "manha", set: "pista", cena: ({ w, s, t }) => {
    bandeira(w, 0, -8.5, -500, 1.2, t, 1.25);
    for (let k = 0; k < 7; k++) poe(w, k * 3, k % 2 ? -2 : 2, -500 + 110 - 92 * s + k * 16);
    const a = 1.2 + s * 0.16;
    camera(w, [-8.5 - Math.sin(a) * 6.5, 2.4, -500 + Math.cos(a) * 6.5], [-6.6, 3.7, -500], 40);
  } },
  { em: "A amarela avisa", clima: "tarde", set: "pista", cena: ({ w, s, t }) => {
    w.amarelo.opacity = 0.95;
    bandeira(w, 1, -8.5, -700, -0.6, t, 1.25);
    w.batido.visible = true;
    w.batido.position.set(9.4, 0, -722);
    w.batido.rotation.set(0, 0.95, 0.05);
    fumaca(w, t, 9.4, -722);
    for (let k = 0; k < 5; k++) poe(w, k * 4, 2 * (k % 2 ? -1 : 1), -640 - 26 * s + k * 12);
    camera(w, [-14 + s * 0.3, 2.4, -692 - s * 0.3], [-6, 3.3, -702], 38);
  }, ui: ({ em }) => <Placa texto="NÃO ULTRAPASSE" inicio={em("proibido")} x={540} y={1640} cor="#ffd400" tam={62} /> },
  { em: "A azul pede", clima: "tarde", set: "pista", cena: ({ w, s, t }) => {
    
    const lento = -860 - 38 * s;
    const rapido = -815 - 72 * s;
    const lado = suave(s, 1.1, 2);
    poe(w, 14, 0 - lado * 2.6, lento);
    poe(w, 2, 1.7, rapido);
    if (s < 1) {
      bandeira(w, 2, -7.6, lento - 6, -0.35, t, 1.2);
      camera(w, [-11.8, 2.6, lento + 5], [-6.4, 3.5, lento - 6], 38);
    } else camera(w, [2.2, 36, lento - 11], [-1, 0, lento - 12], 34, 0, true);
  } },
  { em: "A vermelha interrompe", clima: "brasa", set: "pista", cena: ({ w, s, t, k }) => {
    bandeira(w, 3, -8.3, -1000, 0.9, t, 1.4);
    const pa = suave(k, 0, 0.9);
    for (let n = 0; n < 8; n++) poe(w, n * 2, n % 2 ? -2 : 2, -1000 + 60 * (1 - pa) + n * 7.4 + 14);
    camera(w, [-14 + s * 0.4, 2.4, -1009 + s * 0.8], [-5.6, 4.1, -994], 40);
  } },
  { em: "A preta desclassifica", clima: "chumbo", set: "pista", cena: ({ w, s, t, k }) => {
    bandeira(w, 4, -3.2, -1104, 0.3, t, 1.1);
    const sai = suave(k, 0.2, 1);
    poeCinza(w, 9, 1 - sai * 3.4, -1100 + 11 - sai * 7);
    halo(w, 0, 1 - sai * 3.4, -1100 + 11 - sai * 7, "#ff2a20", 0.75);
    camera(w, [4.2 - s * 0.6, 2.6, -1100 + 19], [-1.4, 2.6, -1100], 42);
  }, ui: ({ em }) => <Placa texto="DESCLASSIFICADO" inicio={em("desclassifica")} x={540} y={1640} cor="#ff5a4a" tam={58} /> },
  { em: "E a quadriculada,", clima: "sol", set: "pista", cena: ({ w, s, t, em }) => {
    bandeira(w, 5, -8.6, -1300, 1.2, t, 1.6);
    w.linhaChegada.position.z = -1305;
    const m = em("a corrida acabou!");
    const z = t < m ? -1190 - (t - (m - 3)) * 28 : -1305 - (t - m) * 62;
    poe(w, iCadillac * 2 + 2, 0, z);
    if (t >= m) confete(w, t, m, 0, 14);
    const a = 1.2 - s * 0.05;
    camera(w, [-9.2 - Math.sin(a) * 8.5, 2.6, -1300 + Math.cos(a) * 8.5], [-6.3, 4.6, -1300], 40);
  }, ui: () => null },

  // Safety Car
  { em: "Se acontece", clima: "tarde", set: "pista", cena: ({ w, s, t }) => {
    w.batido.visible = true;
    w.batido.position.set(9.4, 0, -300);
    w.batido.rotation.set(0, 0.95, 0.05);
    fumaca(w, t, 9.4, -300);
    const tr = Math.sin(t * 61) * 0.05 + Math.sin(t * 37) * 0.04;
    camera(w, [2.5 + s * 0.7 + tr, 1.7 + tr, -284 - s * 2], [9.4, 1.2, -300], 38, Math.sin(t * 43) * 0.012);
  }, ui: () => <FundoLegenda /> },
  { em: "entra o Safety", clima: "tarde", set: "pista", cena: ({ w, s, t }) => {
    const z = -300 - 24 * s;
    w.sc.visible = true;
    w.sc.position.set(0, 0, z);
    const p = Math.sin(t * 26) > 0;
    w.luzesSc[0].emissiveIntensity = p ? 3.5 : 0.2;
    w.luzesSc[1].emissiveIntensity = p ? 0.2 : 3.5;
    camera(w, [3.2 - s * 1.1, 0.55 + s * 0.18, z - 12 + s * 1.3], [0.25, 0.8, z + 0.3], 40, 0.03 - s * 0.015);
  }, ui: ({ t, em }) => {
    const e = entra(t, em("Safety"), 0.25);
    return <div style={{ position: "absolute", left: "50%", top: 1520, transform: `translateX(-50%) scale(${0.7 + e * 0.3})`, opacity: e, background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00", zIndex: 40 }}>SC</div>;
  } },
  { em: "que lidera", clima: "tarde", set: "pista", cena: ({ w, s, t, k }) => {
    const z = -300 - 32 * s;
    w.sc.visible = true;
    w.sc.position.set(0, 0, z);
    const p = Math.sin(t * 26) > 0;
    w.luzesSc[0].emissiveIntensity = p ? 3.5 : 0.2;
    w.luzesSc[1].emissiveIntensity = p ? 0.2 : 3.5;
    for (let n = 0; n < 10; n++) poe(w, n * 2, n % 2 ? -0.9 : 0.9, z + 14 + n * 7.4);
    camera(w, [4 - k * 3, 9 + k * 34, z + 56 + k * 18], [0, 0, z + 30], 42);
  }, ui: ({ t, em }) => t >= em("sem") ? <Placa texto="NÃO ULTRAPASSE" inicio={em("sem")} x={540} y={1620} cor="#ffd400" tam={60} /> : null },
  { em: "Para perigos", clima: "chumbo", set: "pista", cena: ({ w, s }) => {
    const z = -500 - 60 * s;
    for (let n = 0; n < 4; n++) poe(w, n * 4, n % 2 ? -1 : 1, z + n * 34);
    camera(w, [6, 2, z - 14 + s * 3], [0, 0.8, z + 8], 38);
  }, ui: ({ t, em }) => t >= em("Virtual:") - 0.5 ? (
    <div style={{ position: "absolute", left: "50%", top: 1520, transform: "translateX(-50%)", background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00", zIndex: 40 }}>VSC</div>
  ) : null },
  { em: "todos reduzem", clima: "chumbo", set: "pista", cena: ({ w, s, k }) => {
    const v = 72 - 40 * suave(k, 0, 0.35);
    const z = -500 - v * s;
    const gaps = [0, 30, 66, 96];
    gaps.forEach((g, n) => poe(w, n * 4 + 2, n % 2 ? -1.1 : 1.1, z + g));
    camera(w, [0, 92, z + 46], [0, 0, z + 46], 38, 0, true);
  }, ui: ({ k }) => <Placa texto={num(300 - 150 * suave(k, 0, 0.35))} unidade="km/h" inicio={0} x={540} y={1640} cor={k > 0.3 ? "#ffd400" : "#fff"} /> },

  // Punições
  { em: "Quem desrespeita", clima: "brasa", set: "pista", cena: ({ w, s }) => {
    const z = -300 - 70 * s;
    poe(w, 10, 1, z);
    camera(w, [1.6 - s * 0.5, 1 + s * 0.15, z + 6.8 - s * 0.8], [1, 0.7, z - 1], 38, 0.02);
  }, ui: ({ em }) => <Placa texto="PUNIÇÃO" inicio={em("punição:")} x={540} y={1620} cor="#ff5a4a" tam={84} /> },
  { em: "cinco ou dez", clima: "chumbo", set: "pista", cena: ({ w, s }) => {
    const z = -300 - 70 * s;
    poe(w, 10, -1, z);
    camera(w, [6.2, 1.1, z - 2 - s], [-1, 0.6, z], 36);
  }, ui: ({ em }) => <><Placa texto="+5" unidade="s" inicio={em("cinco")} x={330} y={1560} cor="#ffb066" /><Placa texto="+10" unidade="s" inicio={em("dez")} x={740} y={1560} cor="#ff5a4a" /></> },
  { em: "um drive-through", clima: "manha", set: "pit", cena: ({ w, s }) => {
    const z = 120 - 34 * s * 2;
    poe(w, 10, 0, z);
    camera(w, [-8, 5.5, z - 6 - s * 3], [0, 0.7, z - 1], 42);
  }, ui: () => <><Placa texto="DRIVE-THROUGH" inicio={0} x={540} y={1470} tam={58} /><Placa texto="sem parar" inicio={0.1} x={540} y={1620} tam={62} cor="#3bd47a" /></> },
  { em: "ou um stop", clima: "manha", set: "pit", cena: ({ w, s, fim }) => {
    const u = fim > 0 ? s / fim : 0;
    const zz = u < 0.3 ? 40 * Math.pow(1 - u / 0.3, 2) : u < 0.8 ? 0 : -60 * Math.pow((u - 0.8) / 0.2, 2);
    poe(w, 10, 0, zz);
    camera(w, [7, 8 - u * 2, zz + 12], [0, 0.4, zz - 1], 38);
  }, ui: ({ s, fim }) => <Placa texto="STOP AND GO" unidade={s / fim > 0.3 && s / fim < 0.8 ? "parado" : ""} inicio={0} x={540} y={1620} tam={62} cor="#ffb066" /> },

  // 2026
  { em: "Em 2026, o DRS", clima: "tarde", set: "pista", cena: ({ w, s }) => {
    const z = -200 - 82 * s;
    poe(w, 2, 0, z);
    camera(w, [0.8, 1.45, z + 8 - s * 0.6], [0, 1.1, z - 3], 32);
  }, ui: ({ t, em }) => {
    const r = entra(t, em("aposentou."), 0.35);
    return (
      <div style={{ position: "absolute", left: "50%", top: 1500, transform: "translateX(-50%)", zIndex: 40, fontFamily: FONTE, padding: "6px 44px", borderRadius: 24, background: "rgba(14,17,24,.84)", color: r > 0.5 ? "#9299a6" : "#fff", fontSize: 110, fontWeight: 800 }}>
        DRS
        <div style={{ position: "absolute", left: "6%", top: "50%", width: `${r * 88}%`, height: 11, borderRadius: 6, background: "#ff3b30", transform: "rotate(-12deg)" }} />
      </div>
    );
  } },
  { em: "Agora, quem", clima: "tarde", set: "pista", cena: ({ w, s, k }) => {
    const z = -200 - 80 * s;
    const g = 28 - 12 * suave(k, 0.05, 0.75);
    poe(w, 14, 0, z);
    poe(w, 2, 0, z + g);
    camera(w, [-1.4, 58, z + 11], [0, 0, z + 11], 28, 0, true);
  }, ui: ({ k }) => {
    const v = 1.5 - 0.65 * suave(k, 0.05, 0.75);
    return <Placa texto={num(v, 1)} unidade="s" inicio={0} x={540} y={1640} cor={v < 1 ? "#3bd47a" : "#fff"} />;
  } },
  { em: "pode usar", clima: "noite", set: "pista", cena: ({ w, s, t, em }) => {
    const m = em("empurrão");
    const ant = Math.max(0, t - m);
    const z = -300 - 76 * s - 3.5 * ant * ant;
    const zF = -300 - 76 * s;
    poe(w, 14, -1.9, zF);
    poe(w, 2, 1.9, z + 11);
    solta(w, 80, (i) => {
      const u = (t * 2.4 + seed(i) * 3) % 1;
      return { p: [1.9 + (seed(i + 1) - 0.5) * 1.1, 0.25 + seed(i + 2) * 0.9, z + 11 + 3.5 + u * 22], e: 0.26 + (1 - u) * 0.45, cor: "#4bb2ff", o: t >= em("modo") ? (1 - u) * 0.9 : 0 };
    }, THREE.AdditiveBlending);
    camera(w, [5.4, 1.5, (zF + z) / 2 + 15], [0.6, 0.8, (zF + z) / 2 + 3], 42);
  }, ui: ({ em }) => <Placa texto="MODO ULTRAPASSAGEM" inicio={em("modo")} x={540} y={1620} tam={54} cor="#7fc4ff" /> },
  { em: "As asas abrem", clima: "vazio", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#101726");
    luzesDesfocadas(w, t);
    w.asa.visible = true;
    w.asa.position.set(0, 0, 0);
    const a = em("abrem");
    const f = em("fecham");
    const ab = suave(t, a, a + 0.5) * (1 - suave(t, f, f + 0.5));
    w.flap.rotation.x = 0.25 + ab * 0.95;
    for (let i = 26; i < 86; i++) {
      const u = (t * 1.4 + seed(i)) % 1;
      const pool = w.parts[i];
      pool.visible = true;
      const sobe = (1 - ab) * Math.max(0, 1 - Math.abs(u - 0.5) * 3) * 0.9;
      pool.position.set((seed(i + 1) - 0.5) * 2.6, 1.95 + seed(i + 2) * 0.22 + sobe, -4 + u * 8);
      pool.scale.set(0.09, 0.09, 1);
      (pool.material as THREE.SpriteMaterial).color.set("#6fc2ff");
      (pool.material as THREE.SpriteMaterial).opacity = 0.5;
      (pool.material as THREE.SpriteMaterial).blending = THREE.AdditiveBlending;
    }
    camera(w, [6.4 - s * 0.26, 3.5, 5.4], [0, 1.45, 0], 30);
  }, ui: ({ t, em }) => <Placa texto={t >= em("fecham") ? "curva: fechada" : t >= em("abrem") ? "reta: aberta" : ""} inicio={em("abrem")} x={540} y={1620} tam={62} cor={t >= em("fecham") ? "#ffb066" : "#7fc4ff"} /> },
  { em: "e metade", clima: "noite", set: "pista", cena: ({ w, s }) => {
    const z = -300 - 76 * s;
    poe(w, 2, 0, z);
    camera(w, [1.8 + s * 0.3, 1.6, z + 7], [0, 0.8, z], 34);
  }, ui: ({ k, t, em }) => {
    const a = entra(t, em("metade"), 0.6);
    const c = 2 * Math.PI * 170;
    return (
      <div style={{ position: "absolute", left: 340, top: 1120, width: 400, height: 400, zIndex: 40, fontFamily: FONTE }}>
        <svg width={400} height={400} viewBox="-200 -200 400 400">
          <circle r={170} fill="rgba(10,12,18,.8)" stroke="#272a33" strokeWidth={28} />
          <circle r={170} fill="none" stroke="#ff7a2a" strokeWidth={28} strokeDasharray={`${(c / 2) * a} ${c}`} transform="rotate(-90)" />
          <circle r={170} fill="none" stroke="#2fa6ff" strokeWidth={28} strokeDasharray={`${(c / 2) * a} ${c}`} transform="rotate(90)" />
          <text y={-6} textAnchor="middle" fill="#fff" fontSize={86} fontWeight={800}>50/50</text>
          <text y={50} textAnchor="middle" fill="#7fc4ff" fontSize={34} fontWeight={700}>{k > 0.15 ? "elétrica" : ""}</text>
        </svg>
      </div>
    );
  } },
  { em: "com combustível", clima: "sol", set: "pista", cena: ({ w, s }) => {
    const z = -300 - 40 * s;
    poe(w, 18, -0.5, z);
    camera(w, [5.5 - s, 2, z + 7], [-0.5, 1.1, z], 36);
  }, ui: ({ s }) => {
    const e = entra(s, 0, 0.35);
    return (
      <div style={{ position: "absolute", left: "50%", top: 1400, transform: `translateX(-50%) scale(${0.8 + e * 0.2})`, opacity: e, display: "flex", alignItems: "center", gap: 18, padding: "14px 38px", borderRadius: 24, background: "rgba(14,17,24,.84)", fontFamily: FONTE, zIndex: 40 }}>
        <svg width={70} height={90} viewBox="0 0 70 90"><path d="M35 3 C35 3 66 42 66 58 A31 31 0 1 1 4 58 C4 42 35 3 35 3 Z" fill="#3bd47a" /></svg>
        <span style={{ color: "#3bd47a", fontSize: 58, fontWeight: 800 }}>sustentável</span>
      </div>
    );
  } },
  { em: "Tudo isso", clima: "claro", set: "estudio", cena: ({ w, s, t, em }) => {
    w.chao.color.set("#f3e6cc");
    const m = em("teto");
    const su = suave(t, m - 0.5, em("limites.") - 0.4);
    const LIM = 34;
    const aux = new THREE.Object3D();
    const alturas = [14, 34, 27, 34, 11];
    let i = 0;
    alturas.forEach((h, n) => {
      const q = Math.min(h, Math.round(4 + su * h * 1.2));
      for (let j = 0; j < q && i < 180; j++, i++) {
        aux.position.set((n - 2) * 1.8, 0.1 + j * 0.21, (n % 2) * 0.9);
        aux.rotation.y = j;
        aux.updateMatrix();
        w.moedas.setMatrixAt(i, aux.matrix);
      }
    });
    w.moedas.count = i;
    w.moedas.visible = true;
    w.moedas.instanceMatrix.needsUpdate = true;
    w.teto.visible = t >= m - 0.1;
    w.teto.position.set(0, LIM * 0.21 + 0.1, 0);
    camera(w, [-2 + s * 0.3, 4.2, 27 - s * 0.3], [0, 4.3, 0], 32);
  }, ui: ({ em, t }) => (
    <>
      <FundoLegenda />
      {t >= em("teto") && <Placa texto="TETO DE GASTOS" inicio={em("teto")} x={540} y={1620} cor="#ffcf4a" tam={62} />}
    </>
  ) },
  { em: "Pronto!", clima: "tarde", set: "pista", cena: ({ w, s, k }) => {
    grade(w, 22);
    w.portico.visible = true;
    for (let n = 0; n < 5; n++) luzGantry(w, n, true);
    const u = suave(k, 0, 1);
    camera(w, [7 - u * 7, 12 + u * 6, Z_POLE + 66 - u * 40], [0, 3, Z_POLE - 6], 40);
  } },
  { em: "As luzes se", clima: "tarde", set: "pista", cena: ({ w, s, t, em }) => {
    const off = em("apagaram,");
    for (let n = 0; n < 5; n++) luzGantry(w, n, t < off + n * 0);
    w.portico.visible = true;
    const u = Math.max(0, t - em("boa"));
    for (let k = 0; k < 22; k++) poe(w, k, gridX(k), gridZ(k) - 18 * Math.max(0, u - k * 0.01) ** 2);
    camera(w, [4.5, 1.2 + s * 0.15, Z_POLE - 22 + u * 1.5], [0, 2.2, Z_POLE - 2], 42);
  } },
];

const inicios = (() => {
  let ult = 0;
  return PLANOS.map((p) => (ult = noTrecho(PALAVRAS, p.em, ult)));
})();
inicios[0] = 0;

const CLIMAS_CHAVES = ["Cadillac", "pole", "Safety", "DRS", "Q1", "Q2", "Q3", "pontuam", "campeão", "construtores"];

export const Piloto: React.FC = () => {
  const ref = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const quadro = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = quadro / fps;
  const iPlano = useMemo(() => {
    let i = 0;
    for (let n = 0; n < inicios.length; n++) if (t >= inicios[n]) i = n;
    return i;
  }, [t]);
  const p = PLANOS[iPlano];
  const ini = inicios[iPlano];
  const prox = inicios[iPlano + 1] ?? durationInFrames / fps;
  const ctx = (w: Mundo): C => ({ w, t, s: t - ini, k: (t - ini) / (prox - ini), fim: prox - ini, ini, em: (x) => noTrecho(PALAVRAS, x, ini) });
  const [alca] = useState(() => delayRender("desenhando o quadro 3D"));
  useLayoutEffect(() => {
    const w = mundo.current ?? (mundo.current = montar(ref.current!));
    preparar(w, p.clima, p.set);
    p.cena(ctx(w));
    w.r.render(w.cena, w.cam);
    continueRender(alca);
  });
  const c = mundo.current ? ctx(mundo.current) : ctx({} as Mundo);
  const fim = PALAVRAS[PALAVRAS.length - 1].f;
  return (
    <AbsoluteFill style={{ background: "#0b0c11" }}>
      <Audio src={staticFile("piloto/voz.wav")} />
      <canvas ref={ref} width={1080} height={1920} style={{ position: "absolute", width: 1080, height: 1920 }} />
      {p.ui?.(c)}
      <Legenda palavras={PALAVRAS} chaves={CLIMAS_CHAVES} />
      <AbsoluteFill style={{ background: "#000", opacity: suave(t, fim + 0.05, fim + 0.25), zIndex: 99 }} />
    </AbsoluteFill>
  );
};

/** Zera o mundo a cada quadro: só aparece o que o plano ativo puser. */
export function preparar(w: Mundo, clima: string, set: string) {
    const cl = CLIMAS[clima] ?? CLIMAS.tarde;
    w.cena.background = w.fundos[clima] ?? w.fundos.tarde;
    const nv = w.cena.fog as THREE.Fog;
    nv.color.set(set === "estudio" && clima !== "claro" ? "#0a0e1a" : cl.nevoa);
    nv.near = set === "circuito" ? 2000 : set === "estudio" ? 40 : 90;
    nv.far = set === "circuito" ? 3100 : set === "estudio" ? 120 : 260;
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
