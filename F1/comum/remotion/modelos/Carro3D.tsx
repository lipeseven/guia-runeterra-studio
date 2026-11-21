// Teste em movimento: grid de carros em 3D (Three.js) com luz e sombra reais; a câmera voa do fundo até a pole.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, Easing, continueRender, delayRender, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { peca } from "./desmonte";
import { freioDoCarro } from "./freio";
import { CORES_PIRELLI, aplicarComposto, pneuPirelli } from "./pneus/pneu";

/** `desenho`: onde a cor da faixa entra. Sem desenho = faixa fina no meio; "marlboro" = flechas da McLaren MP4/8 (1993):
 *  ponta de flecha no bico à frente do cockpit e flecha que desce pelos sidepods e pela tampa até a traseira. */
export type Pintura = { base: string; clara: string; escura: string; faixa: string; acento: string; desenho?: "marlboro" };
export const C = (h: string) => new THREE.Color(h);

type Secao = [z: number, largura: number, topo: number, base: number];

/** Cockpit do molde de 2026 em metros, no espaço do carro (frente -z, y = altura do chão). Medidas conferidas
 *  (2026-11-17, pedido do Felipe: "sem espaço para os braços nem para o volante"): abertura ~0,85 m x ~0,47 m (gabarito
 *  da FIA: borda de trás >= 1,5 m atrás do eixo dianteiro, borda de baixo a 525 mm do plano de referência); piloto
 *  reclinado ~50° (quadril no fundo, pés acima do quadril); volante de ~29 cm na coluna, ~27 cm à frente do peito, com
 *  os cotovelos dobrados; capacete ~0,26 x 0,31 x 0,28 m (largura, comprimento, altura); halo de 3 pontos (dois atrás,
 *  ao lado dos ombros, e o pilar central preso à frente da abertura), com o arco na altura da testa. */
export const COCKPIT = {
  abertura: { z: -0.34, meio: 0.42, larg: 0.235, fundo: 0.15 }, // elipse da abertura (centro z, meio comprimento, meia largura) e fundo
  capacete: [0, 0.735, -0.1] as const, // centro do capacete
  olhos: [0, 0.74, -0.215] as const, // entre os olhos, logo atrás da viseira
  // v8 (Felipe: "volante apoiado na barriga" e "virado para baixo"): na altura do peito/queixo, à frente do peito, face
  // quase vertical com o topo levemente para o piloto (incl negativa = face um pouco para cima)
  volante: { pos: [0, 0.585, -0.56] as const, incl: -0.12 }, // centro do volante e inclinação
  quadril: { y: 0.215, z: -0.61 }, // articulação do quadril no assento
};

type Cava = { z: number; meio: number; larg: number; fundo: number; cor: THREE.Color; todo?: boolean };
/** Afunda os vértices dentro da elipse da abertura do cockpit (só a metade de cima; `todo` = a peça inteira, para o
 *  que atravessa o cockpit por dentro, como o miolo dos sidepods, sumir abaixo do fundo). Devolve [y, pinta de escuro]:
 *  o escuro inclui uma borda logo fora da abertura (o acolchoado da borda), para a parede não sair listrada de branco. */
const cavar = (cv: Cava | undefined, x: number, y: number, z: number, n: number): [number, boolean] => {
  if (!cv || (!cv.todo && n <= 0)) return [y, false];
  const e = (x / cv.larg) ** 2 + ((z - cv.z) / cv.meio) ** 2;
  if (e >= 1) return [y, !cv.todo && e < 1.1];
  const f = Math.min(1, (1 - e) / 0.22);
  const alvo = cv.todo ? cv.fundo - 0.03 : cv.fundo;
  return [y + (alvo - y) * f, true];
};

/** Liga seções em forma de "superelipse" ao longo do comprimento; `cor` pinta cada vértice. `cava` = abertura do cockpit. */
/** `limiteX(z)`: a peça não passa para dentro desta distância do centro do carro (|x| >= limite): o lado de dentro vira
 *  uma parede lisa. Usado nos sidepods (ver abaixo). */
export function casco(secoes: Secao[], cor: (x: number, y: number, z: number) => THREE.Color, dx = 0, voltas = 64, passos = 90, curva = 0.72, cava?: Cava, limiteX?: (z: number) => number): THREE.Mesh {
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
      let x = Math.sign(c) * Math.pow(Math.abs(c), curva) * w + dx;
      if (limiteX) {
        const L = limiteX(z);
        x = dx > 0 ? Math.max(x, L) : Math.min(x, -L);
      }
      const y0 = meio + Math.sign(n) * Math.pow(Math.abs(n), curva) * alt;
      const [y, escuro] = cavar(cava, x, y0, z, n);
      pos.push(x, y, z);
      const k = escuro ? cava!.cor : cor(x - dx, y, z);
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

/** Borda acolchoada da abertura do cockpit: um tubo escuro na elipse da abertura, apoiado no topo do casco (esconde o
 *  serrilhado da malha na beirada). Mesma interpolação das seções que `casco`. */
/** Forro do cockpit: parede lisa e escura logo por dentro da borda da abertura, da borda até o fundo. Esconde os
 *  triângulos esticados da cava (vistos de dentro, no POV, como "dentes" brancos; v6 da "visão do piloto"). */
function forroDoCockpit(secoes: Secao[], curva = 0.72): THREE.Mesh {
  const amostras: Secao[] = [];
  for (let i = 0; i <= 400; i++) {
    const u = (i / 400) * (secoes.length - 1);
    const k = Math.min(secoes.length - 2, Math.floor(u));
    const t = u - k;
    const s = t * t * (3 - 2 * t);
    amostras.push(secoes[k].map((v, j) => v + (secoes[k + 1][j] - v) * s) as Secao);
  }
  const secaoEm = (z: number) => amostras.find((a, i) => i === amostras.length - 1 || amostras[i + 1][0] >= z)!;
  const { z: zc, meio, larg, fundo } = COCKPIT.abertura;
  const N = 96;
  const pos: number[] = [];
  const ind: number[] = [];
  for (let i = 0; i <= N; i++) {
    const a = (i / N) * Math.PI * 2;
    const x = Math.cos(a) * larg * 0.985, z = zc + Math.sin(a) * meio * 0.985;
    const [, w, topo, base] = secaoEm(z);
    const c = Math.min(1, Math.pow(Math.abs(x) / w, 1 / curva));
    const n = Math.sqrt(1 - c * c);
    const yTopo = (topo + base) / 2 + Math.pow(n, curva) * (topo - base) / 2 - 0.006;
    pos.push(x, yTopo, z, x, fundo, z);
  }
  for (let i = 0; i < N; i++) {
    const a = i * 2;
    ind.push(a, a + 1, a + 2, a + 2, a + 1, a + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: "#343b4b", roughness: 0.85, side: THREE.DoubleSide }));
  m.name = "forro_cockpit";
  return m;
}

function bordaDoCockpit(secoes: Secao[], passos = 400, curva = 0.72): THREE.Mesh {
  const amostras: Secao[] = [];
  for (let i = 0; i <= passos; i++) {
    const u = (i / passos) * (secoes.length - 1);
    const k = Math.min(secoes.length - 2, Math.floor(u));
    const t = u - k;
    const s = t * t * (3 - 2 * t);
    amostras.push(secoes[k].map((v, j) => v + (secoes[k + 1][j] - v) * s) as Secao);
  }
  const secaoEm = (z: number) => amostras.find((a, i) => i === amostras.length - 1 || amostras[i + 1][0] >= z)!;
  const { z: zc, meio, larg } = COCKPIT.abertura;
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i < 72; i++) {
    const a = (i / 72) * Math.PI * 2;
    const x = Math.cos(a) * larg * 1.02, z = zc + Math.sin(a) * meio * 1.02;
    const [, w, topo, base] = secaoEm(z);
    const c = Math.min(1, Math.pow(Math.abs(x) / w, 1 / curva));
    const n = Math.sqrt(1 - c * c);
    pts.push(new THREE.Vector3(x, (topo + base) / 2 + Math.pow(n, curva) * (topo - base) / 2 + 0.004, z));
  }
  const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 144, 0.016, 8, true), new THREE.MeshStandardMaterial({ color: "#1a1b20", roughness: 0.8 }));
  m.castShadow = true;
  return m;
}

/** Meia largura do casco na altura y, na posição z (mesma interpolação de `casco`): para prender peças NA superfície
 *  (as hastes da suspensão saíam do ar ao lado do bico, 2026-11-18). */
/** Meia largura máxima do casco na posição z (mesma interpolação de `casco`). */
function meiaLargura(secoes: Secao[], z: number): number {
  let ant = secoes[0];
  for (let i = 0; i <= 200; i++) {
    const u = (i / 200) * (secoes.length - 1);
    const k = Math.min(secoes.length - 2, Math.floor(u));
    const t = u - k;
    const sm = t * t * (3 - 2 * t);
    const q = secoes[k].map((v, j) => v + (secoes[k + 1][j] - v) * sm) as Secao;
    if (q[0] >= z) return q[1];
    ant = q;
  }
  return ant[1];
}

function superficie(secoes: Secao[], z: number, y: number, curva = 0.72): { x: number; y: number } {
  const amostras: Secao[] = [];
  for (let i = 0; i <= 400; i++) {
    const u = (i / 400) * (secoes.length - 1);
    const k = Math.min(secoes.length - 2, Math.floor(u));
    const t = u - k;
    const sm = t * t * (3 - 2 * t);
    amostras.push(secoes[k].map((v, j) => v + (secoes[k + 1][j] - v) * sm) as Secao);
  }
  const sec = amostras.find((q, i) => i === amostras.length - 1 || amostras[i + 1][0] >= z)!;
  const [, w, topo, base] = sec;
  const meio = (topo + base) / 2, alt = (topo - base) / 2;
  const yy = Math.max(base + 0.03, Math.min(topo - 0.04, y));
  const n = Math.pow(Math.min(1, Math.abs(yy - meio) / alt), 1 / curva);
  const c = Math.sqrt(Math.max(0, 1 - n * n));
  return { x: Math.pow(c, curva) * w, y: yy };
}

/** Escava uma entrada de ar NA PRÓPRIA casca (v11, Felipe: "duto de ar é só um buraco, sem argola"): os vértices da
 *  face da frente (normal com componente z forte, z < zMax) dentro da elipse (centro cx, cy; semi-eixos ax, ay) afundam
 *  para dentro do corpo (+z) até `prof` e ficam escuros, com a borda suave. Nada é acrescentado por cima. */
function escavar(m: THREE.Mesh, cx: number, cy: number, ax: number, ay: number, prof: number, zMax: number) {
  const g = m.geometry as THREE.BufferGeometry;
  const pos = g.attributes.position as THREE.BufferAttribute;
  const nor = g.attributes.normal as THREE.BufferAttribute;
  const cor = g.attributes.color as THREE.BufferAttribute;
  const escuro = new THREE.Color("#07080b");
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    if (z > zMax || Math.abs(nor.getZ(i)) < 0.35) continue;
    const e = ((x - cx) / ax) ** 2 + ((y - cy) / ay) ** 2;
    if (e >= 1) continue;
    const f = Math.min(1, (1 - e) / 0.25); // borda suave: 0 na borda, 1 no miolo
    pos.setZ(i, z + prof * Math.sqrt(1 - e));
    const c = new THREE.Color(cor.getX(i), cor.getY(i), cor.getZ(i)).lerp(escuro, Math.min(1, f * 1.2));
    cor.setXYZ(i, c.r, c.g, c.b);
  }
  pos.needsUpdate = true;
  cor.needsUpdate = true;
  g.computeVertexNormals();
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
  const secMono: Secao[] = [[-2.6, 0.05, 0.24, 0.15], [-2.35, 0.09, 0.29, 0.13], [-1.9, 0.13, 0.39, 0.13], [-1.3, 0.2, 0.52, 0.12], [-0.75, 0.27, 0.6, 0.1], [-0.2, 0.3, 0.64, 0.1], [0.25, 0.27, 0.66, 0.1], [0.85, 0.22, 0.62, 0.1], [1.5, 0.16, 0.52, 0.11], [2.1, 0.12, 0.44, 0.13], [2.45, 0.06, 0.37, 0.18]];
  // interior do cockpit em grafite azulado (o preto chapado aparecia como "parte preta nas costas" no corte, v6)
  gMono.add(casco(secMono, corpo, 0, 96, 220, 0.72, { ...COCKPIT.abertura, cor: C("#343b4b") }));
  gMono.add(forroDoCockpit(secMono));
  const borda = bordaDoCockpit(secMono);
  borda.name = "borda_cockpit"; // a abertura do cockpit: realcar(carro, "borda_cockpit") acende o contorno
  gMono.add(borda);
  // entrada de ar sobre o piloto (santo antônio) e espinha da tampa do motor
  // v11: a entrada de ar sobre a cabeça é um BURACO escavado na frente da casca (antes um disco preto que saía acima
  // da casca: "bola preta"; de lado lia como uma linha preta)
  gTampa.add(escavar(casco([[-0.02, 0.05, 0.8, 0.6], [0.12, 0.13, 0.98, 0.58], [0.4, 0.15, 0.95, 0.56], [0.9, 0.12, 0.83, 0.5], [1.5, 0.06, 0.63, 0.45], [1.95, 0.02, 0.5, 0.42]], corpo, 0, 64, 180), 0, 0.79, 0.055, 0.075, 0.09, 0.14));
  // v7 ("uma bola preta em cima do piloto"): a entrada de ar sobre a cabeça ganha borda na cor do carro, para ler como
  // tomada de ar (e não uma esfera preta solta atrás do capacete)
  // (v8: a borda/argola posta na v7 saiu: "essa argola não existe")

  for (const s of [-1, 1]) {
    // sidepod: boca larga na frente, com rebaixo embaixo, afinando até a "garrafa de coca" atrás
    const lado = s < 0 ? "esquerda" : "direita";
    const gSide = grupo(`sidepod_${lado}`, [s * 0.9, 0, 0], 1);
    // sidepod (2026-11-18, v5 da "visão do piloto": "imundice no primeiro frame"): a casca dele cruzava o centro do carro e
    // a cava "todo" puxava os vértices de dentro da abertura até o fundo, esticando triângulos (lascas brancas entre o
    // cockpit e o sidepod). Agora não há cava: o lado de dentro para numa parede lisa em |x| >= limite, escondida dentro
    // do monocoque e fora da abertura do cockpit (meia largura 0,235 m).
    const limiteSide = (z: number) => {
      const { z: zc, meio, larg } = COCKPIT.abertura;
      const naAbertura = Math.max(0, 1 - Math.max(0, Math.abs(z - zc) - meio) / 0.12); // 1 ao lado da abertura, some em 12 cm
      return Math.max(meiaLargura(secMono, z) * 0.82, (larg + 0.03) * naAbertura);
    };
    gSide.add(escavar(casco([[-0.5, 0.02, 0.5, 0.3], [-0.42, 0.3, 0.54, 0.28], [-0.1, 0.33, 0.55, 0.22], [0.4, 0.26, 0.5, 0.16], [1.0, 0.14, 0.42, 0.13], [1.6, 0.04, 0.32, 0.12]], lateral, s * 0.28, 96, 240, 0.42, undefined, limiteSide), s * 0.52, 0.41, 0.06, 0.085, 0.08, -0.38));
    // v11: a boca do sidepod é um buraco escavado na própria casca (sem moldura: "essa argola não existe")
    // retrovisor sobre o sidepod: peça própria ("retrovisor_esquerdo"/"_direito") para ser destacada no lugar (realcar),
    // nunca um par novo por cima; espelho virado para trás
    const gRet = grupo(`retrovisor_${s < 0 ? "esquerdo" : "direito"}`, [s * 0.4, 0.2, 0], 0);
    const carcaca = caixa(0.16, 0.07, 0.04, s * 0.56, 0.76, -0.42, "#17181d");
    const espelho = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 0.055), new THREE.MeshStandardMaterial({ color: "#cfe3ff", metalness: 0.9, roughness: 0.08 }));
    // cabeça do retrovisor virada ~35° para o piloto (como no carro de verdade: o vidro mostra o lado e a traseira)
    const giroRet = -s * 0.6;
    carcaca.rotation.y = giroRet;
    espelho.rotation.y = giroRet;
    espelho.position.set(s * 0.56 + Math.sin(giroRet) * 0.022, 0.76, -0.42 + Math.cos(giroRet) * 0.022);
    // haste por fora e por baixo da cabeça do retrovisor até o sidepod (antes cruzava a frente do vidro na visão do piloto)
    // pilar que NASCE do topo do sidepod e segura a cabeça do retrovisor por baixo (v7: "retrovisores voando"), com base
    const pe = new THREE.Vector3(s * 0.44, 0.49, -0.4);
    const topo = new THREE.Vector3(s * 0.55, 0.735, -0.42);
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.045, 0.06, 16), new THREE.MeshStandardMaterial({ color: "#17181d", roughness: 0.4 }));
    base.position.copy(pe).setY(0.5);
    gRet.add(carcaca, espelho, haste(pe, topo, 0.016, "#17181d"), base);
    // rodas: dianteira mais estreita que a traseira
    grupo(`roda_dianteira_${lado}`, [s * 1.1, 0, 0], 1).add(roda(s * 0.81, -1.55, 0.36, 0.28));
    grupo(`roda_traseira_${lado}`, [s * 1.1, 0, 0], 1).add(roda(s * 0.76, 1.85, 0.36, 0.38));
    // freios (2026-11-12): disco de carbono, pinça e pastilhas dentro do aro, tomada de ar do lado de dentro (modelos/freio.ts)
    g.add(freioDoCarro(s, true, s * 0.81, 0.36, -1.55), freioDoCarro(s, false, s * 0.76, 0.36, 1.85));
    // suspensão em braços (dianteira e traseira): o ponto de dentro fica NA superfície do bico/chassi (2 cm para dentro
    // do casco, sem ponta solta no ar; Felipe, 2026-11-18: "os braços não se encaixam no bico, ficam voando") e o de fora
    // no montante, uma peça vertical dentro da roda que une os dois braços (e a barra de direção na frente)
    for (const [yc, zc, xr, yr, zr] of [
      [0.3, -1.3, 0.66, 0.29, -1.55], [0.3, -1.85, 0.66, 0.29, -1.55], [0.42, -1.35, 0.66, 0.47, -1.55], [0.42, -1.8, 0.66, 0.47, -1.55],
      [0.26, 1.6, 0.57, 0.27, 1.85], [0.26, 2.1, 0.57, 0.27, 1.85], [0.4, 1.65, 0.57, 0.47, 1.85], [0.4, 2.05, 0.57, 0.47, 1.85],
    ] as const) {
      const q = superficie(secMono, zc, yc);
      gSusp.add(haste(new THREE.Vector3(s * Math.max(0.03, q.x - 0.02), q.y, zc), new THREE.Vector3(s * xr, yr, zr), 0.016, "#17181d"));
    }
    for (const [xr, zr] of [[0.665, -1.55], [0.575, 1.85]] as const) {
      gSusp.add(haste(new THREE.Vector3(s * xr, 0.25, zr), new THREE.Vector3(s * xr, 0.51, zr), 0.03, "#26282e"));
    }
    // barra de direção (dianteira) e haste de empuxo (pushrod), também do chassi ao montante
    const qd = superficie(secMono, -1.62, 0.36);
    gSusp.add(haste(new THREE.Vector3(s * (qd.x - 0.02), qd.y, -1.62), new THREE.Vector3(s * 0.665, 0.38, -1.62), 0.012, "#17181d"));
    const qp = superficie(secMono, -1.45, 0.5);
    gSusp.add(haste(new THREE.Vector3(s * (qp.x - 0.02), qp.y, -1.45), new THREE.Vector3(s * 0.64, 0.29, -1.52), 0.012, "#17181d"));
    // placas laterais das asas
    gAsaD.add(caixa(0.02, 0.14, 0.4, s * 0.9, 0.17, -2.52, preto));
    gAsaT.add(caixa(0.02, 0.46, 0.5, s * 0.53, 0.84, 2.46, preto));
    gAsaT.add(caixa(0.006, 0.16, 0.36, s * 0.542, 0.92, 2.46, p.acento));
  }
  // asa dianteira: três lâminas, das pontas ao miolo
  gAsaD.add(lamina(0.11, -2.74, 0.14, p.base, 0.9, 0.1));
  gAsaD.add(lamina(0.16, -2.62, 0.1, p.faixa, 0.9, 0.12));
  gAsaD.add(lamina(0.21, -2.52, 0.12, p.acento, 0.9, 0.14));
  // asa traseira (redesenhada 2026-11-20, referências de F1 real): perfil de ASA, borda da FRENTE (z menor) mais baixa e a de
  // TRÁS mais alta, os dois elementos inclinados assim = carga aerodinâmica (posição padrão, FECHADA). O carro anda para -z.
  // Plano principal inclinado ~10°; flap superior (a aba do DRS) ~22° com uma fresta entre os dois. `drs(carro, k)` (efeitos3d.ts)
  // gira o flap em volta da borda de TRÁS: a da frente sobe e ele fica quase deitado, abrindo a fresta (modo reta).
  const planoP = caixa(1.04, 0.035, 0.3, 0, 0.8, 2.38, p.base, 0.3);
  planoP.rotation.x = -0.18;
  gAsaT.add(planoP);
  const ANG_FECHADA = -0.38;
  const flap = caixa(1.04, 0.03, 0.2, 0, 0, -0.1, p.acento, 0.3); // borda de trás na origem do pivô (z +0,1 do centro)
  const abaDrs = new THREE.Group();
  abaDrs.name = "aba_drs";
  abaDrs.position.set(0, 0.95 - 0.1 * Math.sin(ANG_FECHADA), 2.58 + 0.1 * Math.cos(ANG_FECHADA)); // flap centrado em y 0,95, z 2,58: a borda da frente fica atrás e acima do plano principal (fresta)
  abaDrs.rotation.x = ANG_FECHADA;
  abaDrs.add(flap);
  gAsaT.add(abaDrs);
  // pilar central
  gAsaT.add(haste(new THREE.Vector3(0, 0.42, 2.25), new THREE.Vector3(0, 0.8, 2.36), 0.025, preto));
  // estrutura de impacto com a luz de chuva
  gMono.add(caixa(0.12, 0.1, 0.36, 0, 0.34, 2.45, preto));
  const luz = caixa(0.1, 0.06, 0.02, 0, 0.34, 2.64, "#ff2d20");
  (luz.material as THREE.MeshStandardMaterial).emissive = C("#ff2d20");
  gMono.add(luz);

  // cockpit (2026-11-17): abertura de verdade no monocoque (o casco afunda até o fundo, ver COCKPIT), com o piloto
  // simples dentro (capacete, ombros e volante). poePilotoNoCarro esconde este "piloto_fixo" e põe o boneco articulado.
  const fixo = new THREE.Group();
  fixo.name = "piloto_fixo";
  const [hx, hy, hz] = COCKPIT.capacete;
  const capacete = new THREE.Mesh(new THREE.SphereGeometry(0.13, 32, 24), new THREE.MeshStandardMaterial({ color: "#f5c518", roughness: 0.2, metalness: 0.15 }));
  capacete.scale.set(1, 1.08, 1.18);
  capacete.position.set(hx, hy, hz);
  capacete.castShadow = true;
  const viseira = new THREE.Mesh(new THREE.SphereGeometry(0.1315, 24, 8, Math.PI * 1.2, Math.PI * 0.6, Math.PI * 0.4, Math.PI * 0.15), new THREE.MeshStandardMaterial({ color: "#0a0c10", roughness: 0.06, metalness: 0.7 }));
  viseira.scale.copy(capacete.scale);
  viseira.position.copy(capacete.position);
  const ombros = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), new THREE.MeshStandardMaterial({ color: "#1d2230", roughness: 0.9 }));
  ombros.scale.set(0.2, 0.07, 0.22);
  ombros.position.set(0, 0.5, -0.24);
  const [vx, vy, vz] = COCKPIT.volante.pos;
  const vol = caixa(0.27, 0.11, 0.04, vx, vy, vz, "#26282e");
  vol.rotation.x = COCKPIT.volante.incl;
  fixo.add(capacete, viseira, ombros, vol);
  gMono.add(fixo);
  // apoio de cabeça: almofadas dos lados do capacete (na borda da abertura, até a altura das orelhas) e atrás dele
  const mApoio = new THREE.MeshStandardMaterial({ color: p.escura, roughness: 0.75 });
  const gApoio = grupo("apoio_cabeca", [0, 0.4, 0.3], 0); // só um encosto fino atrás do capacete (Felipe, 2026-11-18: nada de "almofadinha" em volta do pescoço)
  // banco moldado (concha de carbono): assento sob o quadril e encosto reclinado como o piloto; só aparece com o
  // monocoque em raio-X. Peça "banco".
  const gBanco = grupo("banco", [0, 0.3, 0.6], 2);
  const mBanco = new THREE.MeshStandardMaterial({ color: "#5b6476", roughness: 0.55 }); // cinza-azulado (preto chapado nas costas ficava "feio")
  // o encosto segue o tronco reclinado (0,915 rad da vertical, para trás) e fica ATRÁS das costas: antes estava inclinado
  // para o lado errado e atravessava o peito do piloto (v6, 2026-11-18)
  const RECL = 0.915;
  const dirT = new THREE.Vector3(0, Math.cos(RECL), Math.sin(RECL)); // do quadril para os ombros
  const atras = new THREE.Vector3(0, -Math.sin(RECL), Math.cos(RECL)); // perpendicular, para as costas
  const quadril = new THREE.Vector3(0, COCKPIT.quadril.y, COCKPIT.quadril.z);
  const assento = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.03, 0.32), mBanco);
  assento.position.set(0, COCKPIT.quadril.y - 0.105, COCKPIT.quadril.z - 0.06);
  const encosto = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.56, 0.03), mBanco);
  encosto.rotation.x = RECL;
  encosto.position.copy(quadril).addScaledVector(dirT, 0.26).addScaledVector(atras, 0.135);
  gBanco.add(assento, encosto);
  for (const sx of [-1, 1]) {
    // abas laterais da concha, nas costelas (fora do tronco, sem atravessar)
    const aba = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.42, 0.12), mBanco);
    aba.rotation.x = RECL;
    aba.position.copy(quadril).addScaledVector(dirT, 0.22).addScaledVector(atras, 0.07).setX(sx * 0.2);
    gBanco.add(aba);
  }
  const apT = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.12, 0.035), mApoio);
  apT.rotation.x = -0.35;
  apT.position.set(0, 0.7, hz + 0.19); // encosto fino atrás do capacete, na borda de trás da abertura
  gApoio.add(apT);
  // halo de 3 pontos: pernas de trás presas ao lado dos ombros, arco na altura da testa (acima da linha dos olhos) e o
  // pilar central descendo até a frente da abertura, diante do volante
  const curva = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.255, 0.635, 0.06), new THREE.Vector3(-0.245, 0.84, -0.2), new THREE.Vector3(0, 0.875, -0.52), new THREE.Vector3(0.245, 0.84, -0.2), new THREE.Vector3(0.255, 0.635, 0.06)]);
  const halo = new THREE.Mesh(new THREE.TubeGeometry(curva, 48, 0.024, 10), new THREE.MeshStandardMaterial({ color: "#2a2c33", roughness: 0.4 }));
  halo.castShadow = true;
  gHalo.add(halo);
  halo.name = "halo_arco";
  const pilar = haste(new THREE.Vector3(0, 0.875, -0.52), new THREE.Vector3(0, 0.625, -0.8), 0.024, "#2a2c33");
  pilar.name = "halo_pilar";
  gHalo.add(pilar);
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
