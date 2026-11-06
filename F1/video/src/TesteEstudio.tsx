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
import { preparar, type Roda } from "./horizontal/carro";
export { preparar };
type Mundo = { r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; carro: THREE.Group; rodas: Roda[]; raio: number; frenteZ: number };

const suave = (t: number, a: number, b: number) => {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
};
const sorteio = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};


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
