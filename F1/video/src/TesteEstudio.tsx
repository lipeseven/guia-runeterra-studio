import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// Teste do estilo do horizontal (estudo das referências, 2026-11-05): estúdio, palavra gigante ATRÁS do carro
// (camadas: fundo → palavra → carro 3D com fundo transparente → nota à mão). Carro = .glb baixado (public dir).
// O leitor deixa o carro de pé, com 5,4 m, e separa as 4 rodas (peças de pneu/cubo/disco juntas no arquivo) pela posição.
const W = 1920;
const H = 1080;
const RODA = /tyre|tire|wheel_hub|disc|rim/i;

type Roda = { pivo: THREE.Group; frente: boolean };
type Mundo = { r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; carro: THREE.Group; rodas: Roda[]; raio: number; frenteZ: number };

const suave = (t: number, a: number, b: number) => {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
};
const sorteio = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Carro do arquivo → grupo de pé no chão, 5,4 m, comprimento em z; rodas separadas em pivôs que giram no eixo x. */
function preparar(cena: THREE.Group): { carro: THREE.Group; rodas: Roda[]; raio: number; frenteZ: number } {
  cena.updateMatrixWorld(true);
  let caixa = new THREE.Box3().setFromObject(cena);
  let t = caixa.getSize(new THREE.Vector3());
  const giro = new THREE.Matrix4();
  if (t.x > t.z) giro.makeRotationY(Math.PI / 2);
  const malhas: THREE.Mesh[] = [];
  cena.traverse((o) => { if ((o as THREE.Mesh).isMesh) malhas.push(o as THREE.Mesh); });
  // assa as transformações na geometria (sem a hierarquia do arquivo)
  const assadas = malhas.map((m) => {
    const g = m.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(giro, m.matrixWorld));
    return { g, mat: m.material as THREE.Material, roda: RODA.test((m.material as THREE.Material).name) };
  });
  caixa = new THREE.Box3();
  assadas.forEach((a) => { a.g.computeBoundingBox(); caixa.union(a.g.boundingBox!); });
  t = caixa.getSize(new THREE.Vector3());
  const s = 5.4 / t.z;
  const c = caixa.getCenter(new THREE.Vector3());
  const ajuste = new THREE.Matrix4().makeScale(s, s, s).multiply(new THREE.Matrix4().makeTranslation(-c.x, -caixa.min.y, -c.z));
  assadas.forEach((a) => a.g.applyMatrix4(ajuste));
  // frente = ponta mais baixa (a asa traseira é alta)
  const alto = (z0: number, z1: number) => {
    let m = 0;
    assadas.forEach(({ g, roda }) => {
      if (roda) return;
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) { const z = p.getZ(i); if (z > z0 && z < z1) m = Math.max(m, p.getY(i)); }
    });
    return m;
  };
  const frenteZ = alto(-2.7, -2.0) < alto(2.0, 2.7) ? -1 : 1;
  // rodas: cada triângulo vai para o canto do seu centro (x, z)
  const carro = new THREE.Group();
  const cantos: Record<string, { g: THREE.BufferGeometry; mat: THREE.Material }[]> = {};
  assadas.forEach(({ g, mat, roda }) => {
    if (!roda) { const m = new THREE.Mesh(g, mat); m.castShadow = true; m.receiveShadow = true; carro.add(m); return; }
    const ng = g.index ? g.toNonIndexed() : g;
    const p = ng.attributes.position;
    const por: Record<string, number[]> = {};
    for (let i = 0; i < p.count; i += 3) {
      const cx = (p.getX(i) + p.getX(i + 1) + p.getX(i + 2)) / 3;
      const cz = (p.getZ(i) + p.getZ(i + 1) + p.getZ(i + 2)) / 3;
      (por[`${cx > 0 ? "d" : "e"}${cz > 0 ? "+" : "-"}`] ??= []).push(i);
    }
    for (const [k, ids] of Object.entries(por)) {
      const nova = new THREE.BufferGeometry();
      for (const nome of Object.keys(ng.attributes)) {
        const at = ng.attributes[nome] as THREE.BufferAttribute;
        const n = at.itemSize;
        const arr = new Float32Array(ids.length * 3 * n);
        ids.forEach((i, j) => { for (let v = 0; v < 3; v++) for (let q = 0; q < n; q++) arr[(j * 3 + v) * n + q] = at.getComponent(i + v, q); });
        nova.setAttribute(nome, new THREE.BufferAttribute(arr, n));
      }
      (cantos[k] ??= []).push({ g: nova, mat });
    }
  });
  const rodas: Roda[] = [];
  let raio = 0.36;
  for (const [k, geos] of Object.entries(cantos)) {
    const cx = new THREE.Box3();
    geos.forEach(({ g }) => { g.computeBoundingBox(); cx.union(g.boundingBox!); });
    const centro = cx.getCenter(new THREE.Vector3());
    raio = (cx.max.y - cx.min.y) / 2;
    const pivo = new THREE.Group();
    pivo.position.copy(centro);
    const gira = new THREE.Group();
    pivo.add(gira);
    geos.forEach(({ g, mat }) => {
      g.translate(-centro.x, -centro.y, -centro.z);
      const m = new THREE.Mesh(g, mat);
      m.castShadow = true;
      gira.add(m);
    });
    carro.add(pivo);
    rodas.push({ pivo, frente: (k.endsWith("+") ? 1 : -1) === frenteZ });
  }
  return { carro, rodas, raio, frenteZ };
}

export const TesteEstudio: React.FC<{ arquivo: string; palavra: string; cor: string; nota: string; modo?: "claro" | "cheio" }> = ({ arquivo, palavra, cor, nota, modo = "claro" }) => {
  const f = useCurrentFrame();
  const tela = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const [pronto, setPronto] = useState(false);
  const [espera] = useState(() => delayRender("carregando o .glb"));

  useEffect(() => {
    const r = new THREE.WebGLRenderer({ canvas: tela.current!, antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setSize(W, H, false);
    r.setClearColor(0x000000, 0);
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.3;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    const cena = new THREE.Scene();
    cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
    const luz = new THREE.DirectionalLight(0xffffff, 2.2);
    luz.position.set(1.5, 10, 2.5);
    luz.castShadow = true;
    luz.shadow.mapSize.set(4096, 4096);
    luz.shadow.radius = 14;
    Object.assign(luz.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 0.5, far: 30 });
    cena.add(luz);
    const chao = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.ShadowMaterial({ opacity: 0.22 }));
    chao.rotation.x = -Math.PI / 2;
    chao.receiveShadow = true;
    cena.add(chao);
    const cam = new THREE.PerspectiveCamera(22, W / H, 0.1, 200);
    new GLTFLoader().load(staticFile(arquivo), (g) => {
      const p = preparar(g.scene);
      cena.add(p.carro);
      mundo.current = { r, cena, cam, ...p };
      setPronto(true);
      continueRender(espera);
    });
    return () => r.dispose();
  }, [arquivo, espera]);

  // cada quadro: o carro chega rodando e para; as rodas da frente esterçam; a câmera gira devagar em volta
  useLayoutEffect(() => {
    const m = mundo.current;
    if (!pronto || !m) return;
    const falta = (1 - suave(f, 0, 54)) * 9; // metros que o carro ainda anda até o centro
    m.carro.position.z = -m.frenteZ * falta;
    const giro = ((9 - falta) / m.raio) * m.frenteZ;
    const esterco = 0.32 * Math.sin(Math.PI * suave(f, 80, 140));
    for (const rd of m.rodas) {
      rd.pivo.rotation.y = rd.frente ? esterco : 0;
      rd.pivo.children[0].rotation.x = giro;
    }
    const a = 0.68 + f * 0.0022;
    m.cam.position.set(Math.sin(a) * 10.2, 1.5 + f * 0.0012, Math.cos(a) * 10.2 * m.frenteZ);
    m.cam.lookAt(0, 0.5, 0);
    m.r.render(m.cena, m.cam);
  }, [f, pronto]);

  // palavra: letras embaralhadas que travam da esquerda para a direita
  const travadas = Math.floor(Math.max(0, f - 6) * 0.55);
  const letras = palavra.split("").map((ch, i) => (i < travadas ? ch : f < 6 ? "" : "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[Math.floor(sorteio(i * 31 + f) * 26)]));
  const escrita = suave(f, 112, 150);
  const seta = suave(f, 146, 160);
  const cheio = modo === "cheio";
  return (
    <AbsoluteFill style={{ background: cheio ? cor : "radial-gradient(ellipse at 50% 62%, #f7f6f2 0%, #e6e4de 70%, #d9d6cf 100%)" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, textAlign: "center", fontFamily: "Bahnschrift", fontStretch: "condensed", fontWeight: 700, fontSize: 470, letterSpacing: -6, lineHeight: 1, color: cheio ? "#ffffff" : cor }}>
        {letras.join("")}
      </div>
      <canvas ref={tela} width={W} height={H} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <div style={{ position: "absolute", left: 1290, top: 250, width: 520, fontFamily: "Ink Free", fontSize: 50, lineHeight: 1.1, color: "#1d1d1d", transform: "rotate(-4deg)", clipPath: `inset(0 ${100 - escrita * 100}% 0 0)` }}>
        {nota}
      </div>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <path d="M 1360 420 C 1300 470, 1240 480, 1150 470" stroke="#1d1d1d" strokeWidth={5} fill="none" strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - seta} />
        {seta >= 1 && <path d="M 1172 452 L 1148 470 L 1174 486" stroke="#1d1d1d" strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
    </AbsoluteFill>
  );
};
