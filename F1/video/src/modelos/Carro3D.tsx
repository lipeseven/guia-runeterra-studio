// Teste em movimento: grid de carros em 3D (Three.js) com luz e sombra reais; a câmera voa do fundo até a pole.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, Easing, continueRender, delayRender, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { peca } from "./desmonte";
import { CORES_PIRELLI, aplicarComposto, pneuPirelli } from "./pneus/pneu";

/** `desenho`: onde a cor da faixa entra. Sem desenho = faixa fina no meio; "marlboro" = flechas da McLaren MP4/8 (1993):
 *  ponta de flecha no bico à frente do cockpit e flecha que desce pelos sidepods e pela tampa até a traseira. */
export type Pintura = { base: string; clara: string; escura: string; faixa: string; acento: string; desenho?: "marlboro" };
export const C = (h: string) => new THREE.Color(h);

type Secao = [z: number, largura: number, topo: number, base: number];

/** Liga seções em forma de "superelipse" ao longo do comprimento; `cor` pinta cada vértice. */
export function casco(secoes: Secao[], cor: (x: number, y: number, z: number) => THREE.Color, dx = 0, voltas = 64, passos = 90, curva = 0.72): THREE.Mesh {
  const interp = (i: number) => {
    const u = (i / passos) * (secoes.length - 1);
    const k = Math.min(secoes.length - 2, Math.floor(u));
    const t = u - k;
    const s = t * t * (3 - 2 * t);
    return secoes[k].map((v, j) => v + (secoes[k + 1][j] - v) * s) as Secao;
  };
  const pos: number[] = [];
  const cores: number[] = [];
  const ind: number[] = [];
  for (let i = 0; i <= passos; i++) {
    const [z, w, topo, base] = interp(i);
    const meio = (topo + base) / 2;
    const alt = (topo - base) / 2;
    for (let j = 0; j < voltas; j++) {
      const a = (j / voltas) * Math.PI * 2;
      const c = Math.cos(a);
      const n = Math.sin(a);
      const x = Math.sign(c) * Math.pow(Math.abs(c), curva) * w + dx;
      const y = meio + Math.sign(n) * Math.pow(Math.abs(n), curva) * alt;
      pos.push(x, y, z);
      const k = cor(x - dx, y, z);
      cores.push(k.r, k.g, k.b);
    }
  }
  for (let i = 0; i < passos; i++) {
    for (let j = 0; j < voltas; j++) {
      const a = i * voltas + j;
      const b = i * voltas + (j + 1) % voltas;
      const c = a + voltas;
      const d = b + voltas;
      ind.push(a, c, b, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(cores, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.34, metalness: 0.12, side: THREE.DoubleSide }));
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

export const caixa = (l: number, a: number, c: number, x: number, y: number, z: number, cor: string, rough = 0.4) => {
  const m = new THREE.Mesh(new THREE.BoxGeometry(l, a, c), new THREE.MeshStandardMaterial({ color: cor, roughness: rough }));
  m.position.set(x, y, z);
  m.castShadow = true;
  return m;
};

const haste = (a: THREE.Vector3, b: THREE.Vector3, r: number, cor: string) => {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, a.distanceTo(b), 10), new THREE.MeshStandardMaterial({ color: cor, roughness: 0.5 }));
  m.position.copy(a).add(b).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
  m.castShadow = true;
  return m;
};

/** Lâmina da asa dianteira em ângulo: das pontas até um miolo plano. */
const lamina = (y: number, z: number, prof: number, cor: string, meia = 1.02, volta = 0.3) => {
  const f = new THREE.Shape();
  f.moveTo(-meia, z + volta);
  f.lineTo(-0.2, z);
  f.lineTo(0.2, z);
  f.lineTo(meia, z + volta);
  f.lineTo(meia, z + volta + prof);
  f.lineTo(0.2, z + prof);
  f.lineTo(-0.2, z + prof);
  f.lineTo(-meia, z + volta + prof);
  f.closePath();
  const g = new THREE.ExtrudeGeometry(f, { depth: 0.035, bevelEnabled: false });
  g.rotateX(Math.PI / 2);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: cor, roughness: 0.32 }));
  m.position.y = y;
  m.castShadow = true;
  return m;
};

/** Cores das marcações da Pirelli (2026): macio vermelho, médio amarelo, duro branco, intermediário verde, chuva azul. */
export const COMPOSTOS = CORES_PIRELLI;

/** Roda com o pneu Pirelli das fotos oficiais (modelos/pneus/pneu.ts); friso = composto ou cor. */
export function roda(x: number, z: number, r: number, l: number, friso = "medio") {
  const g = new THREE.Group();
  const p = pneuPirelli(r, l, friso);
  p.rotation.z = Math.PI / 2; // o torno gira em torno de y; o eixo da roda fica em x
  g.add(p);
  // a roda inteira (pneu, aro e cubo) é UMA peça: rola em x (eixo da roda) DEPOIS de esterçar em y (ordem YXZ = esterço
  // no carro, rolagem no eixo já virado). rolarRodas e estercar mexem cada um no seu eixo.
  g.rotation.order = "YXZ";
  g.position.set(x, r, z);
  return g;
}

/** Troca o composto dos pneus de um carro (nome ou cor). */
export function trocarComposto(car: THREE.Object3D, composto: string) {
  aplicarComposto(car, composto);
}

export function carro(p: Pintura): THREE.Group {
  const g = new THREE.Group();
  const base = C(p.base);
  const clara = C(p.clara);
  const escura = C(p.escura);
  const faixa = C(p.faixa);
  const marlboro = p.desenho === "marlboro";
  const corpo = (x: number, y: number, z: number) => {
    if (marlboro && y > 0.3 && z > -1.45 && z < -0.45 && Math.abs(x) <= (z + 1.45) * 0.35 + 0.02) return faixa; // flecha do bico
    if (marlboro && y > 0.3 && z > 1.25 && Math.abs(x) > 0.04) return faixa; // fim da flecha na tampa do motor
    if (!marlboro && Math.abs(x) < 0.055 + Math.max(0, -z) * 0.004 && y > 0.3) return faixa;
    if (y < 0.2) return escura;
    return base.clone().lerp(clara, Math.max(0, Math.min(0.6, (y - 0.42) * 0.9)));
  };
  const lateral = (_x: number, y: number, z: number) => {
    if (y < 0.22) return escura;
    if (marlboro && z > 0.45 + (0.55 - y) * 1.4) return faixa; // flecha inclinada no fim do sidepod
    return base.clone().lerp(clara, Math.max(0, Math.min(0.55, (y - 0.3) * 0.9)));
  };
  const preto = "#0c0d11";
  // peças para o desmonte (explodir, isolar, raio-X): camada 0 sai primeiro
  const grupo = (nome: string, sai: [number, number, number], camada: number) => {
    const q = peca(new THREE.Group(), nome, sai, camada);
    g.add(q);
    return q;
  };
  const gAsaD = grupo("asa_dianteira", [0, 0, -1.4], 0);
  const gAsaT = grupo("asa_traseira", [0, 0.8, 1.2], 0);
  const gHalo = grupo("halo", [0, 1, 0], 0);
  const gTampa = grupo("tampa_do_motor", [0, 0.9, 0.5], 1);
  const gMono = grupo("monocoque", [0, 0, 0], 2);
  const gPiso = grupo("assoalho", [0, 0, 0], 2);
  const gSusp = grupo("suspensao", [0, 0, 0], 2);

  // Molde de 2026 em metros reais (regulamento FIA 2026): 1,9 m de largura, 3,4 m entre eixos, rodas de 18".
  // Frente para -z. Eixo dianteiro em z = -1,55; traseiro em z = 1,85.
  // assoalho: estreito na frente, largo no meio, fino antes das rodas traseiras
  const piso = new THREE.Shape();
  [[-0.26, -1.15], [-0.72, -0.55], [-0.74, 1.15], [-0.5, 1.5], [-0.5, 2.2], [0.5, 2.2], [0.5, 1.5], [0.74, 1.15], [0.72, -0.55], [0.26, -1.15]].forEach(([x, z], i) => (i ? piso.lineTo(x, z) : piso.moveTo(x, z)));
  piso.closePath();
  const gp = new THREE.ExtrudeGeometry(piso, { depth: 0.04, bevelEnabled: false });
  gp.rotateX(Math.PI / 2);
  const mp = new THREE.Mesh(gp, new THREE.MeshStandardMaterial({ color: "#2a2c32", roughness: 0.55 }));
  mp.position.y = 0.09;
  mp.castShadow = true;
  gPiso.add(mp);
  // difusor: rampa preta atrás do assoalho
  const dif = caixa(0.96, 0.03, 0.5, 0, 0.13, 2.4, preto, 0.5);
  dif.rotation.x = -0.32;
  gPiso.add(dif);

  // monocoque: bico baixo e fino, sobe até o cockpit e desce pela tampa do motor
  gMono.add(casco([[-2.6, 0.05, 0.24, 0.15], [-2.35, 0.09, 0.29, 0.13], [-1.9, 0.13, 0.39, 0.13], [-1.3, 0.2, 0.52, 0.12], [-0.75, 0.27, 0.6, 0.1], [-0.2, 0.3, 0.64, 0.1], [0.25, 0.27, 0.66, 0.1], [0.85, 0.22, 0.62, 0.1], [1.5, 0.16, 0.52, 0.11], [2.1, 0.12, 0.44, 0.13], [2.45, 0.06, 0.37, 0.18]], corpo));
  // entrada de ar sobre o piloto (santo antônio) e espinha da tampa do motor
  gTampa.add(casco([[-0.02, 0.03, 0.78, 0.6], [0.12, 0.13, 0.98, 0.58], [0.4, 0.15, 0.95, 0.56], [0.9, 0.12, 0.83, 0.5], [1.5, 0.06, 0.63, 0.45], [1.95, 0.02, 0.5, 0.42]], corpo));
  const tomada = new THREE.Mesh(new THREE.CircleGeometry(1, 24), new THREE.MeshStandardMaterial({ color: "#050507", roughness: 0.6 }));
  tomada.scale.set(0.085, 0.07, 1);
  tomada.position.set(0, 0.88, 0.07);
  tomada.rotation.y = Math.PI;
  gTampa.add(tomada);

  for (const s of [-1, 1]) {
    // sidepod: boca larga na frente, com rebaixo embaixo, afinando até a "garrafa de coca" atrás
    const lado = s < 0 ? "esquerda" : "direita";
    const gSide = grupo(`sidepod_${lado}`, [s * 0.9, 0, 0], 1);
    gSide.add(casco([[-0.5, 0.02, 0.5, 0.3], [-0.42, 0.3, 0.54, 0.28], [-0.1, 0.33, 0.55, 0.22], [0.4, 0.26, 0.5, 0.16], [1.0, 0.14, 0.42, 0.13], [1.6, 0.04, 0.32, 0.12]], lateral, s * 0.28, 64, 90, 0.42));
    const boca = caixa(0.22, 0.14, 0.02, s * 0.44, 0.43, -0.45, "#050507", 0.6);
    gSide.add(boca);
    // retrovisor sobre o sidepod
    gSide.add(caixa(0.16, 0.07, 0.04, s * 0.56, 0.76, -0.42, "#17181d"));
    gSide.add(haste(new THREE.Vector3(s * 0.5, 0.74, -0.4), new THREE.Vector3(s * 0.36, 0.62, -0.3), 0.012, "#17181d"));
    // rodas: dianteira mais estreita que a traseira
    grupo(`roda_dianteira_${lado}`, [s * 1.1, 0, 0], 1).add(roda(s * 0.81, -1.55, 0.36, 0.28));
    grupo(`roda_traseira_${lado}`, [s * 1.1, 0, 0], 1).add(roda(s * 0.76, 1.85, 0.36, 0.38));
    // suspensão em braços (dianteira e traseira)
    for (const [xc, yc, zc, xr, yr, zr] of [
      [0.18, 0.32, -1.3, 0.66, 0.3, -1.55], [0.18, 0.32, -1.85, 0.66, 0.3, -1.55], [0.16, 0.5, -1.35, 0.66, 0.46, -1.55], [0.16, 0.5, -1.8, 0.66, 0.46, -1.55],
      [0.14, 0.28, 1.6, 0.56, 0.28, 1.85], [0.14, 0.28, 2.1, 0.56, 0.28, 1.85], [0.14, 0.46, 1.65, 0.56, 0.46, 1.85], [0.14, 0.46, 2.05, 0.56, 0.46, 1.85],
    ] as const) {
      gSusp.add(haste(new THREE.Vector3(s * xc, yc, zc), new THREE.Vector3(s * xr, yr, zr), 0.016, "#17181d"));
    }
    // placas laterais das asas
    gAsaD.add(caixa(0.02, 0.14, 0.4, s * 0.9, 0.17, -2.52, preto));
    gAsaT.add(caixa(0.02, 0.4, 0.4, s * 0.53, 0.8, 2.42, preto));
    gAsaT.add(caixa(0.006, 0.16, 0.32, s * 0.542, 0.88, 2.42, p.acento));
  }
  // asa dianteira: três lâminas, das pontas ao miolo
  gAsaD.add(lamina(0.11, -2.74, 0.14, p.base, 0.9, 0.1));
  gAsaD.add(lamina(0.16, -2.62, 0.1, p.faixa, 0.9, 0.12));
  gAsaD.add(lamina(0.21, -2.52, 0.12, p.acento, 0.9, 0.14));
  // asa traseira: plano principal, flap e pilar central
  gAsaT.add(caixa(1.04, 0.035, 0.3, 0, 0.8, 2.38, p.base, 0.3));
  const flap = caixa(1.04, 0.03, 0.2, 0, 0.93, 2.5, p.acento, 0.3);
  flap.rotation.x = 0.35;
  gAsaT.add(flap);
  gAsaT.add(haste(new THREE.Vector3(0, 0.42, 2.25), new THREE.Vector3(0, 0.8, 2.36), 0.025, preto));
  // estrutura de impacto com a luz de chuva
  gMono.add(caixa(0.12, 0.1, 0.36, 0, 0.34, 2.45, preto));
  const luz = caixa(0.1, 0.06, 0.02, 0, 0.34, 2.64, "#ff2d20");
  (luz.material as THREE.MeshStandardMaterial).emissive = C("#ff2d20");
  gMono.add(luz);

  // cockpit, capacete e halo
  const cabine = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), new THREE.MeshStandardMaterial({ color: "#050507", roughness: 0.55 }));
  cabine.scale.set(0.21, 0.06, 0.42);
  cabine.position.set(0, 0.64, -0.28);
  gMono.add(cabine);
  const capacete = new THREE.Mesh(new THREE.SphereGeometry(0.13, 32, 24), new THREE.MeshStandardMaterial({ color: "#f5c518", roughness: 0.2, metalness: 0.15 }));
  capacete.position.set(0, 0.72, -0.12);
  capacete.castShadow = true;
  gMono.add(capacete);
  const curva = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.26, 0.64, 0.12), new THREE.Vector3(-0.24, 0.84, -0.16), new THREE.Vector3(0, 0.89, -0.44), new THREE.Vector3(0.24, 0.84, -0.16), new THREE.Vector3(0.26, 0.64, 0.12)]);
  const halo = new THREE.Mesh(new THREE.TubeGeometry(curva, 48, 0.026, 10), new THREE.MeshStandardMaterial({ color: "#2a2c33", roughness: 0.4 }));
  halo.castShadow = true;
  gHalo.add(halo);
  gHalo.add(haste(new THREE.Vector3(0, 0.89, -0.44), new THREE.Vector3(0, 0.6, -0.68), 0.026, "#2a2c33"));
  return g;
}

const M_POR_TEXTURA = 60; // metros de pista em cada repetição da textura

export function texturaPista(): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 1536;
  c.height = 2880;
  const x = c.getContext("2d")!;
  const m = (v: number) => 768 + v * 32; // 48 m de largura
  x.fillStyle = "#25663b";
  x.fillRect(0, 0, 1536, 2880);
  for (let y = 0; y < 2880; y += 480) {
    x.fillStyle = "#2c7444";
    x.fillRect(0, y, 1536, 240);
  }
  x.fillStyle = "#c4a174";
  x.fillRect(m(-10.4), 0, m(10.4) - m(-10.4), 2880);
  x.fillStyle = "#4b4450";
  x.fillRect(m(-6.4), 0, m(6.4) - m(-6.4), 2880);
  // faixas largas de luz e sombra atravessando o asfalto
  const faixas = x.createLinearGradient(0, 0, 0, 2880);
  [[0, "rgba(255,178,140,.12)"], [0.2, "rgba(255,178,140,.12)"], [0.28, "rgba(24,16,46,.3)"], [0.44, "rgba(24,16,46,.3)"], [0.52, "rgba(255,178,140,.08)"], [0.62, "rgba(255,178,140,.08)"], [0.7, "rgba(24,16,46,.24)"], [0.82, "rgba(24,16,46,.24)"], [0.9, "rgba(255,178,140,.12)"], [1, "rgba(255,178,140,.12)"]].forEach(([o, cor]) => faixas.addColorStop(o as number, cor as string));
  x.fillStyle = faixas;
  x.fillRect(m(-6.4), 0, m(6.4) - m(-6.4), 2880);
  // linhas longitudinais suaves, como o desgaste da pista
  for (const l of [-3.9, -1.4, 1.4, 3.9]) {
    x.fillStyle = "rgba(0,0,0,.1)";
    x.fillRect(m(l) - 14, 0, 28, 2880);
  }
  for (let k = 0; k < 340; k++) {
    x.fillStyle = `rgba(${k % 2 ? "255,255,255" : "0,0,0"},${0.012 + (k % 9) * 0.004})`;
    x.fillRect(m(-6.4) + ((k * 137) % 410), (k * 397) % 2880, 2, 16 + (k % 7) * 9);
  }
  for (let s = 0; s < 2; s++) {
    const xk = s ? m(6.4) : m(-8.1);
    for (let y = 0; y < 2880; y += 60) {
      x.fillStyle = Math.floor(y / 60) % 2 ? "#f3f3f3" : "#dd2c35";
      x.fillRect(xk, y, 54, 60);
    }
    x.fillStyle = "#f3f3f3";
    x.fillRect(s ? m(6.2) : m(-6.4), 0, 6, 2880);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  t.wrapT = THREE.RepeatWrapping;
  return t;
}

export function degradeRadial(cor: string): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(128, 128, 20, 128, 128, 128);
  g.addColorStop(0, cor);
  g.addColorStop(1, "rgba(0,0,0,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

export const plano = (l: number, c: number, x: number, z: number, mat: THREE.Material, y = 0.013) => {
  // marcação de chão: puxada para a frente na profundidade (não briga com o piso de longe; 2026-11-12, "faixas piscando")
  mat.polygonOffset = true;
  mat.polygonOffsetFactor = -2;
  mat.polygonOffsetUnits = -2;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(l, c), mat);
  m.rotation.x = -Math.PI / 2;
  m.position.set(x, y, z);
  return m;
};

function numero(n: number): THREE.Material {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 128;
  const x = c.getContext("2d")!;
  x.font = "800 104px 'Segoe UI', sans-serif";
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillStyle = "#f4f1ea";
  x.fillText(String(n), 64, 68);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false });
}

export const PINTURAS: Pintura[] = [
  { base: "#d11f4e", clara: "#ff5f88", escura: "#6d0a26", faixa: "#f4f1ea", acento: "#ffc400" }, // pole
  { base: "#d9571a", clara: "#ff9445", escura: "#742a05", faixa: "#14202e", acento: "#f6e7c8" },
  { base: "#0f8f80", clara: "#2fd4bd", escura: "#06433f", faixa: "#f3ecd8", acento: "#ff5a3c" },
  { base: "#2547c4", clara: "#5f8bff", escura: "#0f2170", faixa: "#ffd21f", acento: "#f4f4f4" },
  { base: "#7a35c0", clara: "#a764ea", escura: "#3c1469", faixa: "#46e0c8", acento: "#f3ecd8" },
  { base: "#e6a500", clara: "#ffd04a", escura: "#8a5400", faixa: "#131313", acento: "#d4213c" },
  { base: "#3a3e45", clara: "#ccd1d8", escura: "#111215", faixa: "#00a19b", acento: "#111215" }, // Mercedes W17 (2026): preto e prata com linha verde Petronas (formula1.com)
  { base: "#23262f", clara: "#4a4f5c", escura: "#0a0b0f", faixa: "#b8f000", acento: "#f5f5f5" },
];

const POSICOES = 22;
const passoGrid = 4.4;
const zDaPosicao = (k: number) => -(POSICOES - k) * passoGrid;
const ladoDaPosicao = (k: number) => (k % 2 ? -1.9 : 1.9);

type Cena3D = { r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; sol: THREE.DirectionalLight; luzPole: THREE.Mesh };

function montar(canvas: HTMLCanvasElement): Cena3D {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  r.setSize(1080, 1920, false);
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.ACESFilmicToneMapping;
  r.toneMappingExposure = 0.94;
  r.shadowMap.enabled = true;
  r.shadowMap.type = THREE.PCFSoftShadowMap;
  const cena = new THREE.Scene();
  cena.background = C("#e9b483");
  cena.fog = new THREE.Fog("#e9b483", 55, 150);
  cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
  cena.environmentIntensity = 0.3;
  cena.add(new THREE.HemisphereLight("#ffe9d2", "#2a2433", 0.85));
  const sol = new THREE.DirectionalLight("#fff0dc", 2.1);
  sol.castShadow = true;
  sol.shadow.mapSize.set(4096, 4096);
  sol.shadow.radius = 5;
  sol.shadow.bias = -0.0004;
  Object.assign(sol.shadow.camera, { left: -16, right: 16, top: 34, bottom: -34, near: 1, far: 70 });
  cena.add(sol, sol.target);

  const mapa = texturaPista();
  const comp = 420;
  mapa.repeat.set(1, comp / M_POR_TEXTURA);
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(48, comp), new THREE.MeshStandardMaterial({ map: mapa, roughness: 0.92 }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.z = -130;
  chao.receiveShadow = true;
  cena.add(chao);
  for (const s of [-1, 1]) {
    const longe = new THREE.Mesh(new THREE.PlaneGeometry(400, comp), new THREE.MeshStandardMaterial({ color: "#25663b", roughness: 1 }));
    longe.rotation.x = -Math.PI / 2;
    longe.position.set(s * 224, -0.01, -130);
    cena.add(longe);
  }

  // o mesmo carro por pintura: o grid inteiro fica barato
  const modelos = PINTURAS.map(carro);
  const sombra = new THREE.MeshBasicMaterial({ map: degradeRadial("rgba(0,0,0,.74)"), transparent: true, depthWrite: false });
  const branco = new THREE.MeshBasicMaterial({ color: "#f4f1ea" });
  for (let k = 1; k <= POSICOES; k++) {
    const x = ladoDaPosicao(k);
    const z = zDaPosicao(k);
    const c = modelos[k === 1 ? 0 : 1 + (k * 3) % (PINTURAS.length - 1)].clone();
    c.position.set(x, 0, z);
    cena.add(c, plano(2.5, 6.2, x, z, sombra));
    // colchete da posição
    cena.add(plano(1.9, 0.09, x, z - 3.9, branco, 0.02), plano(0.09, 0.62, x - 0.95, z - 3.62, branco, 0.02), plano(0.09, 0.62, x + 0.95, z - 3.62, branco, 0.02));
    cena.add(plano(1.05, 1.05, x + Math.sign(x) * 1.55, z - 3.35, numero(k), 0.02));
  }
  // linha de largada
  for (let i = 0; i < 26; i++) {
    for (let j = 0; j < 2; j++) cena.add(plano(0.48, 0.48, -6.1 + i * 0.48, zDaPosicao(1) - 6.2 + j * 0.48, (i + j) % 2 ? branco : new THREE.MeshBasicMaterial({ color: "#16171b" })));
  }
  // luz sobre a pole
  const luzPole = plano(3.2, 7.6, ladoDaPosicao(1), zDaPosicao(1), new THREE.MeshBasicMaterial({ map: degradeRadial("rgba(255,214,120,1)"), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }), 0.016);
  cena.add(luzPole);
  const cam = new THREE.PerspectiveCamera(47, 1080 / 1920, 0.1, 400);
  return { r, cena, cam, sol, luzPole };
}

export const Carro3D: React.FC = () => {
  const ref = useRef<HTMLCanvasElement>(null);
  const cena = useRef<Cena3D | null>(null);
  const quadro = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [alca] = useState(() => delayRender("desenhando o quadro 3D"));
  useLayoutEffect(() => {
    const c = cena.current ?? (cena.current = montar(ref.current!));
    const t = quadro / fps;
    // voa do fundo do grid até a pole em 1,7 s, freando, e depois só desliza devagar
    const voo = interpolate(t, [0, 1.7], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.2, 0.05, 0.1, 1) });
    const zFoco = zDaPosicao(POSICOES) + (zDaPosicao(1) - zDaPosicao(POSICOES)) * voo + Math.max(0, t - 1.7) * 0.12;
    const altura = 5.4 + voo * 2.5 + Math.max(0, t - 1.7) * 0.05;
    const recuo = 7.2 + voo * 3.6;
    c.cam.position.set(0.15, altura, zFoco + recuo);
    c.cam.lookAt(0, 0, zFoco - 11);
    c.sol.position.set(-7, 16, zFoco - 6);
    c.sol.target.position.set(0, 0, zFoco - 8);
    c.sol.target.updateMatrixWorld();
    (c.luzPole.material as THREE.MeshBasicMaterial).opacity = interpolate(t, [1.5, 2.1], [0, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * (0.86 + Math.sin(t * 3) * 0.14);
    c.r.render(c.cena, c.cam);
    continueRender(alca);
  }, [quadro, fps, alca]);
  return (
    <AbsoluteFill>
      <canvas ref={ref} width={1080} height={1920} style={{ width: 1080, height: 1920 }} />
    </AbsoluteFill>
  );
};
