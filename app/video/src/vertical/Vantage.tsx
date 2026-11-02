// Safety Car: Aston Martin Vantage da F1 (2024) em medidas reais, 4,50 x 2,04 x 1,28 m e entre-eixos de 2,70 m. Sem logotipos.
// Verde-azulado metálico, friso lima no splitter e nas saias, grade larga de lâminas, asa traseira e barra de luzes.
import * as THREE from "three";
import { C, caixa } from "./Carro3D";

/** Corte transversal: largura e altura de cada ponto do contorno, da base até o centro do teto. */
type Secao = [z: number, base: number, sAia: number, largura: number, yLargura: number, ombro: number, yOmbro: number, topo: number];

const CARROCERIA: Secao[] = [
  [-2.27, 0.24, 0.5, 0.6, 0.4, 0.5, 0.5, 0.53],
  [-2.2, 0.19, 0.66, 0.76, 0.4, 0.66, 0.55, 0.6],
  [-2.0, 0.16, 0.78, 0.9, 0.46, 0.8, 0.62, 0.68],
  [-1.4, 0.15, 0.84, 1.01, 0.56, 0.88, 0.75, 0.79],
  [-0.7, 0.15, 0.84, 0.98, 0.54, 0.82, 0.82, 0.88],
  [-0.2, 0.15, 0.84, 0.96, 0.52, 0.8, 0.86, 0.93],
  [0.6, 0.15, 0.84, 0.97, 0.52, 0.8, 0.88, 0.93],
  [1.3, 0.16, 0.86, 1.02, 0.58, 0.86, 0.9, 0.93],
  [1.85, 0.2, 0.82, 0.96, 0.62, 0.78, 0.92, 0.95],
  [2.2, 0.3, 0.72, 0.82, 0.68, 0.62, 0.94, 0.96],
  [2.27, 0.38, 0.62, 0.7, 0.72, 0.5, 0.9, 0.92],
];

const CABINE: Secao[] = [
  [-0.42, 0.8, 0.5, 0.52, 0.86, 0.46, 0.9, 0.92],
  [-0.05, 0.8, 0.64, 0.68, 0.88, 0.54, 1.08, 1.13],
  [0.35, 0.8, 0.7, 0.73, 0.9, 0.56, 1.22, 1.275],
  [0.85, 0.8, 0.72, 0.75, 0.92, 0.56, 1.2, 1.25],
  [1.35, 0.8, 0.66, 0.7, 0.92, 0.48, 1.1, 1.14],
  [1.85, 0.8, 0.52, 0.56, 0.92, 0.36, 0.97, 0.99],
  [2.1, 0.8, 0.34, 0.38, 0.9, 0.24, 0.93, 0.94],
];

const catmull = (a: number, b: number, c: number, d: number, t: number) =>
  0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t * t * t);

const secaoEm = (tab: Secao[], z: number): Secao => {
  let k = 0;
  while (k < tab.length - 2 && z > tab[k + 1][0]) k++;
  const t = Math.max(0, Math.min(1, (z - tab[k][0]) / (tab[k + 1][0] - tab[k][0])));
  const p = (i: number) => tab[Math.max(0, Math.min(tab.length - 1, i))];
  return tab[k].map((_, j) => catmull(p(k - 1)[j], p(k)[j], p(k + 1)[j], p(k + 2)[j], t)) as Secao;
};

const contorno = ([, base, saia, larg, yLarg, ombro, yOmbro, topo]: Secao, n: number) =>
  new THREE.CatmullRomCurve3(
    [[0, base], [saia, base], [larg * 0.97, (base + yLarg) / 2], [larg, yLarg], [ombro, yOmbro], [ombro * 0.55, topo - 0.01], [0, topo]].map(([x, y]) => new THREE.Vector3(x, y, 0)),
    false,
    "catmullrom",
    0.5,
  ).getPoints(n);

/** A lateral da carroceria na altura `y`: é onde faróis, lanternas e letreiros encostam. */
const ladoEm = (tab: Secao[], y: number, z: number) => {
  const pts = contorno(secaoEm(tab, z), 90);
  const k = pts.findIndex((p) => p.y >= y);
  if (k <= 0) return pts[Math.max(0, k)].x;
  const f = (y - pts[k - 1].y) / Math.max(1e-6, pts[k].y - pts[k - 1].y);
  return pts[k - 1].x + (pts[k].x - pts[k - 1].x) * f;
};

type Abertura = { z: number; y: number; r: number };

/** Liga os cortes ao longo do comprimento, fecha as pontas e abre as caixas de roda. */
function loft(tab: Secao[], mat: THREE.Material, passos = 320, n = 90, aberturas: Abertura[] = []) {
  const voltas = 2 * n;
  const pos: number[] = [];
  const ind: number[] = [];
  const dentro = (x: number, y: number, z: number) => Math.abs(x) > 0.45 && aberturas.some((a) => Math.hypot(z - a.z, y - a.y) < a.r);
  const empurra = (x: number, y: number, z: number): [number, number] => {
    if (Math.abs(x) < 0.45) return [y, z];
    for (const a of aberturas) {
      const d = Math.hypot(z - a.z, y - a.y);
      if (Math.abs(d - a.r) < 0.018) return [a.y + ((y - a.y) / d) * a.r, a.z + ((z - a.z) / d) * a.r];
    }
    return [y, z];
  };
  const z0 = tab[0][0];
  const z1 = tab[tab.length - 1][0];
  for (let i = 0; i <= passos; i++) {
    const zb = z0 + ((z1 - z0) * i) / passos;
    const pts = contorno(secaoEm(tab, zb), n);
    const anel = [...pts, ...pts.slice(1, -1).reverse().map((p) => new THREE.Vector3(-p.x, p.y, 0))];
    for (const p of anel) {
      const [y, z] = empurra(p.x, p.y, zb);
      pos.push(p.x, y, z);
    }
  }
  const v = (i: number, j: number) => i * voltas + (j % voltas);
  for (let i = 0; i < passos; i++) {
    for (let j = 0; j < voltas; j++) {
      for (const [a, b, c] of [[v(i, j), v(i + 1, j), v(i, j + 1)], [v(i, j + 1), v(i + 1, j), v(i + 1, j + 1)]]) {
        const cx = (pos[a * 3] + pos[b * 3] + pos[c * 3]) / 3;
        const cy = (pos[a * 3 + 1] + pos[b * 3 + 1] + pos[c * 3 + 1]) / 3;
        const cz = (pos[a * 3 + 2] + pos[b * 3 + 2] + pos[c * 3 + 2]) / 3;
        if (!dentro(cx, cy, cz)) ind.push(a, b, c);
      }
    }
  }
  // tampas das pontas
  for (const i of [0, passos]) {
    const zb = i ? z1 : z0;
    const s = secaoEm(tab, zb);
    const c = pos.length / 3;
    pos.push(0, (s[1] + s[7]) / 2, zb);
    for (let j = 0; j < voltas; j++) ind.push(c, v(i, j), v(i, j + 1));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

const vec3 = (h: string) => {
  const c = C(h);
  return `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`;
};

/** Pinta por pixel, conforme a posição no carro: vidros e saídas de ar saem com a borda limpa em qualquer distância. */
function pintar(mat: THREE.MeshStandardMaterial, glsl: string) {
  mat.onBeforeCompile = (s) => {
    s.vertexShader = s.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vCarro;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvCarro = position;");
    s.fragmentShader = s.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vCarro;").replace("#include <color_fragment>", `#include <color_fragment>\nvec3 p = vCarro; float ax = abs(p.x); vec3 brilho = vec3(0.0);\n${glsl}`).replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += brilho;");
  };
  mat.customProgramCacheKey = () => glsl;
  return mat;
}

/** Fita colada na lateral: de um corte a outro, com altura e espessura que variam. Serve a faróis e lanternas. */
function fita(pontos: [z: number, y: number, h: number][], s: number, mat: THREE.Material) {
  const curva = new THREE.CatmullRomCurve3(pontos.map(([z, y, h]) => new THREE.Vector3(z, y, h))).getPoints(40);
  const pos: number[] = [];
  const ind: number[] = [];
  curva.forEach(({ x: z, y, z: h }, i) => {
    for (const yy of [y - h / 2, y + h / 2]) pos.push(s * (ladoEm(CARROCERIA, yy, z) + 0.006), yy, z);
    if (i) ind.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i, 2 * i - 1, 2 * i + 1);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(ind);
  g.computeVertexNormals();
  return new THREE.Mesh(g, mat);
}

const placa = (pontos: [number, number][], y: number, alt: number, cor: string, rough = 0.4) => {
  const f = new THREE.Shape();
  pontos.forEach(([x, z], i) => (i ? f.lineTo(x, z) : f.moveTo(x, z)));
  f.closePath();
  const g = new THREE.ExtrudeGeometry(f, { depth: alt, bevelEnabled: false });
  g.rotateX(Math.PI / 2);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: cor, roughness: rough }));
  m.position.y = y;
  m.castShadow = true;
  return m;
};

/** Friso que acompanha a carroceria na altura `y`. */
const friso = (zs: number[], y: number, s: number, r: number, cor: string) => {
  const curva = new THREE.CatmullRomCurve3(zs.map((z) => new THREE.Vector3(s * (ladoEm(CARROCERIA, y, z) + 0.004), y, z)));
  const m = new THREE.Mesh(new THREE.TubeGeometry(curva, 40, r, 8), new THREE.MeshStandardMaterial({ color: cor, roughness: 0.4 }));
  m.castShadow = true;
  return m;
};

function letreiro(texto: string) {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 160;
  const x = c.getContext("2d")!;
  x.font = "800 italic 112px 'Segoe UI', sans-serif";
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillStyle = "#f6f7f4";
  x.fillText(texto, 512, 84);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  return new THREE.MeshStandardMaterial({ map: t, transparent: true, depthWrite: false, roughness: 0.4, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2 });
}

const RAIO_RODA = 0.355;

/** Roda de rua: aro preto de dez raios, disco de freio e pneu baixo. `giro` é o grupo que o movimento faz rodar. */
function rodaRua(s: number, x: number, z: number, l: number) {
  const g = new THREE.Group();
  const giro = new THREE.Group();
  const pneu = new THREE.Mesh(new THREE.CylinderGeometry(RAIO_RODA, RAIO_RODA, l, 56), new THREE.MeshStandardMaterial({ color: "#121318", roughness: 0.7 }));
  pneu.rotation.z = Math.PI / 2;
  pneu.castShadow = true;
  g.add(pneu);
  const fora = s * (l / 2 + 0.002);
  const borda = new THREE.Mesh(new THREE.TorusGeometry(RAIO_RODA - 0.06, 0.016, 10, 64), new THREE.MeshStandardMaterial({ color: "#3b3e46", metalness: 0.8, roughness: 0.3 }));
  borda.rotation.y = Math.PI / 2;
  borda.position.x = fora;
  const fundo = new THREE.Mesh(new THREE.CircleGeometry(RAIO_RODA - 0.065, 40), new THREE.MeshStandardMaterial({ color: "#07080b", roughness: 0.8, side: THREE.DoubleSide }));
  fundo.rotation.y = Math.PI / 2;
  fundo.position.x = fora - s * 0.006;
  const disco = new THREE.Mesh(new THREE.CircleGeometry(0.17, 36), new THREE.MeshStandardMaterial({ color: "#75797f", metalness: 0.85, roughness: 0.35, side: THREE.DoubleSide }));
  disco.rotation.y = Math.PI / 2;
  disco.position.x = fora - s * 0.004;
  g.add(fundo, disco);
  giro.add(borda);
  for (let k = 0; k < 10; k++) {
    const a = (k / 10) * Math.PI * 2;
    const raio = caixa(0.02, 0.27, 0.042, fora, Math.cos(a) * 0.155, Math.sin(a) * 0.155, "#50535b", 0.3);
    raio.rotation.x = a;
    giro.add(raio);
  }
  const cubo = new THREE.Mesh(new THREE.CircleGeometry(0.04, 20), new THREE.MeshStandardMaterial({ color: "#2b2d33", metalness: 0.7, roughness: 0.3, side: THREE.DoubleSide }));
  cubo.rotation.y = Math.PI / 2;
  cubo.position.x = fora + s * 0.002;
  giro.add(cubo);
  g.add(giro);
  g.position.set(x, RAIO_RODA, z);
  return { g, giro };
}

export function vantage() {
  const g = new THREE.Group();
  const VERDE = vec3("#066a60");
  const CLARO = vec3("#14a998");
  const PRETO = vec3("#07080b");
  const lima = "#cfe82e";
  const eixos = [-1.38, 1.32];

  const pintura = pintar(new THREE.MeshStandardMaterial({ roughness: 0.34, metalness: 0.5, side: THREE.DoubleSide }), `
    diffuseColor.rgb = mix(${VERDE}, ${CLARO}, clamp((p.y - 0.25) * 1.4, 0.0, 1.0));
    bool preto = p.y < 0.215 // saia
      || (p.z > 2.2 && p.y < 0.4) // difusor
      || (p.z < -2.22 && p.y < 0.53 && ax < 0.6) // boca da grade
      || (p.z > -2.2 && p.z < -2.1 && p.y > 0.25 && p.y < 0.46 && ax > 0.64) // tomadas verticais nos cantos
      || (p.y > 0.72 && p.z > -1.25 && p.z < -0.82 && ax > 0.2 && ax < 0.44 && fract((p.z + 1.25) / 0.085) < 0.45) // saídas de ar do capô
      || (ax > 0.82 && p.z > -0.86 && p.z < -0.5 && p.y > 0.46 + (p.z + 0.86) * 0.12 && p.y < 0.56 - (p.z + 0.86) * 0.05); // respiro atrás da roda
    if (preto) diffuseColor.rgb = ${PRETO};
    // farol fino e puxado para trás: carcaça escura com a luz diurna em lâmina
    float tf = (p.z + 2.17) / 0.47;
    if (tf > 0.0 && tf < 1.0 && ax > 0.42) {
      float yf = 0.565 + 0.125 * tf;
      if (abs(p.y - yf) < 0.05 * (1.0 - tf * tf) + 0.004) diffuseColor.rgb = vec3(0.012, 0.016, 0.022);
      if (abs(p.y - yf - 0.012) < 0.009 * (1.0 - tf) + 0.002) brilho = vec3(3.2);
    }
  `);
  g.add(loft(CARROCERIA, pintura, 320, 90, eixos.map((z) => ({ z, y: RAIO_RODA, r: 0.415 }))));

  const vidro = pintar(new THREE.MeshStandardMaterial({ roughness: 0.16, metalness: 0.45, side: THREE.DoubleSide }), `
    diffuseColor.rgb = mix(${VERDE}, ${CLARO}, 0.6);
    float linhaTeto = 1.2 - (p.z - 0.5) * (p.z - 0.5) * 0.34;
    bool parabrisa = p.z < 0.2 && ax < 0.5 - (p.z + 0.4) * 0.14;
    bool lateral = ax > 0.5 && p.y < linhaTeto && p.y > 0.9 && p.z > 0.08 + (p.y - 0.9) * 0.9 && p.z < 1.48 - (p.y - 0.9) * 1.9;
    bool traseiro = ax < 0.4 - (p.z - 1.2) * 0.2 && p.z > 1.22 && p.z < 1.86;
    if (parabrisa || lateral || traseiro) diffuseColor.rgb = vec3(0.004, 0.007, 0.01);
  `);
  g.add(loft(CABINE, vidro, 200, 60));

  // grade: lâminas horizontais de metal, mais largas embaixo
  const zGrade = -2.28;
  const lamina = new THREE.MeshStandardMaterial({ color: "#e8ebef", metalness: 0.6, roughness: 0.2 });
  for (let k = 0; k < 6; k++) {
    const y = 0.265 + k * 0.042;
    const larg = 1.12 - k * 0.05;
    const m = new THREE.Mesh(new THREE.BoxGeometry(larg, 0.007, 0.04), lamina);
    m.position.set(0, y, zGrade - 0.012);
    m.rotation.x = -0.35;
    g.add(m);
  }
  const fundoGrade = caixa(1.14, 0.27, 0.006, 0, 0.375, zGrade + 0.012, "#040507", 0.8);
  g.add(fundoGrade);

  // splitter: base preta com o friso lima por fora
  const pts: [number, number][] = [[-0.98, -1.86], [-0.88, -2.12], [-0.62, -2.31], [0.62, -2.31], [0.88, -2.12], [0.98, -1.86]];
  g.add(placa(pts, 0.135, 0.022, lima, 0.45));
  g.add(placa(pts.map(([x, z]) => [x * 0.97, z + 0.02] as [number, number]), 0.16, 0.024, "#0a0b0f", 0.5));

  const lanterna = new THREE.MeshBasicMaterial({ color: "#ff2016", toneMapped: false, side: THREE.DoubleSide });
  const rodas: THREE.Group[] = [];

  for (const s of [-1, 1]) {
    // caixas de roda e rodas
    for (const [z, l] of [[eixos[0], 0.27], [eixos[1], 0.32]] as const) {
      const poco = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.46, 40), new THREE.MeshStandardMaterial({ color: "#040507", roughness: 0.9 }));
      poco.rotation.z = Math.PI / 2;
      poco.position.set(s * 0.62, RAIO_RODA, z);
      g.add(poco);
      const x = ladoEm(CARROCERIA, RAIO_RODA + 0.15, z) - l / 2 - 0.012;
      const r = rodaRua(s, s * x, z, l);
      g.add(r.g);
      rodas.push(r.giro);
      // borda do para-lama, para o recorte sair limpo
      const arco = new THREE.CatmullRomCurve3(Array.from({ length: 25 }, (_, k) => {
        const a = -0.45 + (k / 24) * (Math.PI + 0.9);
        const yy = RAIO_RODA + Math.sin(a) * 0.415;
        const zz = z + Math.cos(a) * 0.415;
        return new THREE.Vector3(s * (ladoEm(CARROCERIA, yy, zz) - 0.002), yy, zz);
      }));
      g.add(new THREE.Mesh(new THREE.TubeGeometry(arco, 72, 0.007, 8), new THREE.MeshStandardMaterial({ color: "#05272a", roughness: 0.5 })));
    }
    // lanterna em lâmina que dá a volta na traseira
    g.add(fita([[1.95, 0.76, 0.03], [2.1, 0.79, 0.042], [2.24, 0.81, 0.05]], s, lanterna));
    const fundoTras = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.03, 0.012), lanterna);
    fundoTras.position.set(s * 0.34, 0.8, 2.275);
    g.add(fundoTras);
    // saia com friso lima entre as rodas
    g.add(friso([-0.92, -0.3, 0.3, 0.86], 0.205, s, 0.011, lima));
    g.add(caixa(0.05, 0.06, 1.72, s * 0.93, 0.15, -0.03, "#0a0b0f", 0.5));
    // retrovisor
    const espelho = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), new THREE.MeshStandardMaterial({ color: "#0d0e13", roughness: 0.35 }));
    espelho.scale.set(0.1, 0.055, 0.05);
    espelho.position.set(s * 0.87, 0.97, 0.02);
    espelho.castShadow = true;
    g.add(espelho, caixa(0.14, 0.02, 0.03, s * 0.78, 0.95, 0.02, "#0d0e13"));
    // letreiro na porta
    const z = 0.27;
    const xp = ladoEm(CARROCERIA, 0.52, z) + 0.012;
    const texto = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.156), letreiro("SAFETY CAR"));
    texto.position.set(s * xp, 0.58, z);
    texto.rotation.y = s * (Math.PI / 2);
    g.add(texto);
    // escapamento quádruplo
    for (const dx of [0.38, 0.52]) {
      const cano = new THREE.Mesh(new THREE.CylinderGeometry(0.048, 0.048, 0.08, 20, 1, true), new THREE.MeshStandardMaterial({ color: "#b6bac0", metalness: 0.8, roughness: 0.3, side: THREE.DoubleSide }));
      cano.rotation.x = Math.PI / 2;
      cano.position.set(s * dx, 0.31, 2.29);
      g.add(cano);
    }
    // asa traseira: braços e placas de ponta lima
    g.add(caixa(0.025, 0.12, 0.1, s * 0.36, 1.0, 1.98, "#0b0c10"));
    g.add(caixa(0.016, 0.09, 0.24, s * 0.7, 1.07, 2.02, lima, 0.45));
  }
  g.add(caixa(1.4, 0.016, 0.22, 0, 1.07, 2.02, "#0b0c10", 0.3));
  g.add(caixa(1.4, 0.02, 0.02, 0, 1.08, 2.13, lima, 0.45)); // borda da asa
  g.add(caixa(1.25, 0.2, 0.1, 0, 0.3, 2.22, "#090a0d", 0.6)); // difusor
  return { carro: g, rodas };
}
