// Teste: carro de F1 em 3D de verdade (Three.js), com luz e sombra reais, numa pista com a mesma câmera do modelo.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

type Pintura = { base: string; clara: string; escura: string; faixa: string; acento: string };
const C = (h: string) => new THREE.Color(h);

type Secao = [z: number, largura: number, topo: number, base: number];

/** Liga seções em forma de "superelipse" ao longo do comprimento; `cor` pinta cada vértice. */
function casco(secoes: Secao[], cor: (x: number, y: number, z: number) => THREE.Color, dx = 0, voltas = 64, passos = 90): THREE.Mesh {
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
      const x = Math.sign(c) * Math.pow(Math.abs(c), 0.72) * w + dx;
      const y = meio + Math.sign(n) * Math.pow(Math.abs(n), 0.72) * alt;
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

const caixa = (l: number, a: number, c: number, x: number, y: number, z: number, cor: string, rough = 0.4) => {
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
const lamina = (y: number, z: number, prof: number, cor: string) => {
  const f = new THREE.Shape();
  const volta = 0.3;
  f.moveTo(-1.02, z + volta);
  f.lineTo(-0.2, z);
  f.lineTo(0.2, z);
  f.lineTo(1.02, z + volta);
  f.lineTo(1.02, z + volta + prof);
  f.lineTo(0.2, z + prof);
  f.lineTo(-0.2, z + prof);
  f.lineTo(-1.02, z + volta + prof);
  f.closePath();
  const g = new THREE.ExtrudeGeometry(f, { depth: 0.035, bevelEnabled: false });
  g.rotateX(Math.PI / 2);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: cor, roughness: 0.32 }));
  m.position.y = y;
  m.castShadow = true;
  return m;
};

function roda(x: number, z: number, r: number, l: number, friso: string) {
  const g = new THREE.Group();
  const perfil: THREE.Vector2[] = [];
  for (let k = 0; k <= 16; k++) {
    const a = -Math.PI / 2 + (k / 16) * Math.PI;
    const rx = l / 2;
    const q = 0.09;
    perfil.push(new THREE.Vector2(r - q + Math.cos(a) * q, Math.sin(a) * rx));
  }
  const pneu = new THREE.Mesh(new THREE.LatheGeometry([new THREE.Vector2(0.001, -l / 2), ...perfil, new THREE.Vector2(0.001, l / 2)], 48), new THREE.MeshStandardMaterial({ color: "#16171c", roughness: 0.62 }));
  pneu.rotation.z = Math.PI / 2;
  pneu.castShadow = true;
  pneu.receiveShadow = true;
  g.add(pneu);
  for (const s of [-1, 1]) {
    const faixa = new THREE.Mesh(new THREE.TorusGeometry(r - 0.012, 0.012, 8, 56), new THREE.MeshStandardMaterial({ color: friso, roughness: 0.4 }));
    faixa.rotation.y = Math.PI / 2;
    faixa.position.x = s * l * 0.37;
    g.add(faixa);
    const aro = new THREE.Mesh(new THREE.CircleGeometry(0.17, 28), new THREE.MeshStandardMaterial({ color: "#8c929c", metalness: 0.8, roughness: 0.35, side: THREE.DoubleSide }));
    aro.rotation.y = Math.PI / 2;
    aro.position.x = s * (l / 2 + 0.001);
    g.add(aro);
  }
  g.position.set(x, r, z);
  return g;
}

function carro(p: Pintura): THREE.Group {
  const g = new THREE.Group();
  const base = C(p.base);
  const clara = C(p.clara);
  const escura = C(p.escura);
  const faixa = C(p.faixa);
  const acento = C(p.acento);
  const corpo = (x: number, y: number, z: number) => {
    if (Math.abs(x) < 0.055 + Math.max(0, -z) * 0.004 && y > 0.3) return faixa;
    if (y < 0.2) return escura;
    return base.clone().lerp(clara, Math.max(0, Math.min(0.6, (y - 0.42) * 0.9)));
  };
  const lateral = (x: number, y: number, z: number) => {
    const fora = Math.abs(x);
    if (z > 0.35 && z < 1.0 && y > 0.38 && fora < 0.13) return acento;
    if (y < 0.2) return escura;
    return base.clone().lerp(clara, Math.max(0, Math.min(0.55, (y - 0.3) * 0.9)));
  };

  // piso preto angular
  const piso = new THREE.Shape();
  [[-0.26, -0.75], [-0.8, -0.1], [-0.88, 1.5], [-0.72, 2.45], [0.72, 2.45], [0.88, 1.5], [0.8, -0.1], [0.26, -0.75]].forEach(([x, z], i) => (i ? piso.lineTo(x, z) : piso.moveTo(x, z)));
  piso.closePath();
  const gp = new THREE.ExtrudeGeometry(piso, { depth: 0.05, bevelEnabled: false });
  gp.rotateX(Math.PI / 2);
  const mp = new THREE.Mesh(gp, new THREE.MeshStandardMaterial({ color: "#0c0d11", roughness: 0.5 }));
  mp.position.y = 0.11;
  mp.castShadow = true;
  g.add(mp);

  g.add(casco([[-2.85, 0.05, 0.3, 0.2], [-2.3, 0.1, 0.36, 0.17], [-1.5, 0.17, 0.46, 0.15], [-0.85, 0.27, 0.6, 0.11], [-0.25, 0.36, 0.73, 0.1], [0.45, 0.37, 0.8, 0.1], [0.95, 0.31, 0.95, 0.1], [1.6, 0.24, 0.76, 0.1], [2.3, 0.12, 0.52, 0.12], [2.78, 0.04, 0.4, 0.17]], corpo));
  for (const s of [-1, 1]) {
    g.add(casco([[-0.3, 0.03, 0.32, 0.14], [0.05, 0.22, 0.56, 0.1], [0.75, 0.3, 0.55, 0.1], [1.55, 0.22, 0.42, 0.1], [2.25, 0.05, 0.25, 0.1]], lateral, s * 0.55));
    // boca da entrada de ar
    const boca = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.2, 0.03), new THREE.MeshStandardMaterial({ color: "#050507", roughness: 0.6 }));
    boca.position.set(s * 0.56, 0.42, -0.02);
    g.add(boca);
    // pneus
    g.add(roda(s * 0.94, -1.8, 0.36, 0.3, p.acento));
    g.add(roda(s * 0.96, 1.95, 0.37, 0.42, p.acento));
    // suspensão
    for (const [zc, zb, xb] of [[-1.72, -1.15, 0.17], [-1.88, -1.5, 0.15], [1.9, 1.4, 0.32], [2.05, 1.95, 0.25]] as const) {
      g.add(haste(new THREE.Vector3(s * 0.8, 0.4, zc), new THREE.Vector3(s * xb, 0.42, zb), 0.018, "#17181d"));
    }
    // placas das asas
    g.add(caixa(0.035, 0.26, 0.62, s * 1.02, 0.19, -2.65, "#0e0f13"));
    g.add(caixa(0.012, 0.13, 0.5, s * 1.04, 0.2, -2.65, p.acento));
    g.add(caixa(0.035, 0.48, 0.62, s * 0.62, 0.72, 2.72, "#0e0f13"));
    g.add(caixa(0.012, 0.24, 0.5, s * 0.64, 0.86, 2.72, p.acento));
    // aletas das entradas e espelhos
    g.add(caixa(0.1, 0.05, 0.06, s * 0.5, 0.74, -0.32, "#17181d"));
  }
  g.add(lamina(0.25, -3.0, 0.14, p.acento));
  g.add(lamina(0.2, -2.85, 0.1, p.faixa));
  g.add(lamina(0.15, -2.74, 0.18, p.base));
  g.add(caixa(1.25, 0.04, 0.26, 0, 0.92, 2.62, p.base, 0.3));
  g.add(caixa(1.25, 0.045, 0.14, 0, 1.0, 2.82, p.acento, 0.3));
  g.add(caixa(0.06, 0.4, 0.12, 0, 0.72, 2.66, "#0e0f13"));
  const luz = caixa(0.14, 0.05, 0.03, 0, 0.42, 2.98, "#ff2d20");
  (luz.material as THREE.MeshStandardMaterial).emissive = C("#ff2d20");
  g.add(luz);

  // cockpit, capacete e halo
  const cabine = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), new THREE.MeshStandardMaterial({ color: "#050507", roughness: 0.55 }));
  cabine.scale.set(0.25, 0.1, 0.56);
  cabine.position.set(0, 0.73, 0.02);
  g.add(cabine);
  const capacete = new THREE.Mesh(new THREE.SphereGeometry(0.135, 32, 24), new THREE.MeshStandardMaterial({ color: "#f5c518", roughness: 0.2, metalness: 0.15 }));
  capacete.position.set(0, 0.84, 0.08);
  capacete.castShadow = true;
  g.add(capacete);
  const curva = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.27, 0.78, 0.42), new THREE.Vector3(-0.25, 0.98, 0.05), new THREE.Vector3(0, 1.03, -0.28), new THREE.Vector3(0.25, 0.98, 0.05), new THREE.Vector3(0.27, 0.78, 0.42)]);
  const halo = new THREE.Mesh(new THREE.TubeGeometry(curva, 48, 0.028, 10), new THREE.MeshStandardMaterial({ color: "#2a2c33", roughness: 0.4 }));
  halo.castShadow = true;
  g.add(halo);
  g.add(haste(new THREE.Vector3(0, 1.03, -0.28), new THREE.Vector3(0, 0.66, -0.5), 0.028, "#2a2c33"));
  return g;
}

function texturaPista(): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 4096;
  const x = c.getContext("2d")!;
  // escape, grama e faixas: 32 m de largura, 120 m de comprimento
  x.fillStyle = "#27613a";
  x.fillRect(0, 0, 1024, 4096);
  const m = (v: number) => 512 + v * 32;
  x.fillStyle = "#c7a678";
  x.fillRect(m(-8.6), 0, m(8.6) - m(-8.6), 4096);
  x.fillStyle = "#4a434f";
  x.fillRect(m(-6), 0, m(6) - m(-6), 4096);
  const faixas = x.createLinearGradient(0, 0, 0, 4096);
  [0, 0.14, 0.27, 0.38, 0.52, 0.66, 0.78, 0.9, 1].forEach((o, k) => faixas.addColorStop(o, k % 2 ? "rgba(255,175,135,.1)" : "rgba(26,18,48,.34)"));
  x.fillStyle = faixas;
  x.fillRect(m(-6), 0, m(6) - m(-6), 4096);
  for (let k = 0; k < 420; k++) {
    x.fillStyle = `rgba(${k % 2 ? "255,255,255" : "0,0,0"},${0.012 + Math.random() * 0.03})`;
    x.fillRect(m(-6) + Math.random() * 384, Math.random() * 4096, 1 + Math.random() * 2, 8 + Math.random() * 60);
  }
  for (let s = 0; s < 2; s++) {
    const xk = s ? m(6) : m(-7.1);
    for (let y = 0; y < 4096; y += 34) {
      x.fillStyle = Math.floor(y / 34) % 2 ? "#f3f3f3" : "#dd2c35";
      x.fillRect(xk, y, 36, 34);
    }
    x.fillStyle = "#f3f3f3";
    x.fillRect(s ? m(5.86) : m(-6), 0, 5, 4096);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  return t;
}

function sombraMacia(): THREE.Mesh {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(128, 128, 20, 128, 128, 128);
  g.addColorStop(0, "rgba(0,0,0,.72)");
  g.addColorStop(0.65, "rgba(0,0,0,.5)");
  g.addColorStop(1, "rgba(0,0,0,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 256, 256);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 7.4), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.012;
  return m;
}

const PINTURAS: Pintura[] = [
  { base: "#0f8f80", clara: "#2fd4bd", escura: "#06433f", faixa: "#f3ecd8", acento: "#ff5a3c" },
  { base: "#d9571a", clara: "#ff9445", escura: "#742a05", faixa: "#14202e", acento: "#f6e7c8" },
  { base: "#2547c4", clara: "#5f8bff", escura: "#0f2170", faixa: "#ffd21f", acento: "#f4f4f4" },
];

export const Carro3D: React.FC = () => {
  const ref = useRef<HTMLCanvasElement>(null);
  const [alca] = useState(() => delayRender("montando o 3D"));
  useLayoutEffect(() => {
    const r = new THREE.WebGLRenderer({ canvas: ref.current!, antialias: true, preserveDrawingBuffer: true });
    r.setSize(1080, 1920, false);
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 0.92;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    const cena = new THREE.Scene();
    cena.background = C("#223a58");
    cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
    cena.environmentIntensity = 0.3;
    cena.add(new THREE.HemisphereLight("#ffe9d2", "#2a2433", 0.85));
    const sol = new THREE.DirectionalLight("#fff0dc", 2.1);
    sol.position.set(-7, 15, -8);
    sol.target.position.set(0, 0, -6);
    sol.castShadow = true;
    sol.shadow.mapSize.set(4096, 4096);
    sol.shadow.radius = 5;
    sol.shadow.bias = -0.0004;
    Object.assign(sol.shadow.camera, { left: -14, right: 14, top: 22, bottom: -22, near: 1, far: 50 });
    cena.add(sol, sol.target);

    const chao = new THREE.Mesh(new THREE.PlaneGeometry(32, 120), new THREE.MeshStandardMaterial({ map: texturaPista(), roughness: 0.92 }));
    chao.rotation.x = -Math.PI / 2;
    chao.position.z = -40;
    chao.receiveShadow = true;
    cena.add(chao);

    [[1.7, 0], [-1.9, -7.5], [1.7, -15], [-1.9, -22.5], [1.7, -30]].forEach(([x, z], k) => {
      const c = carro(PINTURAS[k % 3]);
      c.position.set(x, 0, z);
      c.scale.set(0.72, 0.85, 1.08);
      c.add(sombraMacia());
      cena.add(c);
    });

    const cam = new THREE.PerspectiveCamera(25, 1080 / 1920, 0.1, 300);
    cam.position.set(0.2, 15.5, 20.5);
    cam.lookAt(0, 0, -11);
    r.render(cena, cam);
    continueRender(alca);
    return () => r.dispose();
  }, [alca]);
  return (
    <AbsoluteFill>
      <canvas ref={ref} width={1080} height={1920} style={{ width: 1080, height: 1920 }} />
    </AbsoluteFill>
  );
};
