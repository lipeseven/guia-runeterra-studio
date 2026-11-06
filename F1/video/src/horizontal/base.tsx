// Base do horizontal (estilo das referências, F1/docs/folha_horizontal.md): tempo, cor do vídeo, cena com fundo fixo,
// carregamento dos .glb (uma vez por aba) e o 3D desenhado num canvas 2D, com borrão de movimento opcional.
import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { GLTFLoader, type GLTF } from "three/examples/jsm/loaders/GLTFLoader.js";

export const W = 1920;
export const H = 1080;
export const FONTE = "Bahnschrift";
export const MAO = "Ink Free";

export const suave = (t: number, a: number, b: number) => {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
};
export const entra = (x: number) => 1 - Math.pow(1 - Math.max(0, Math.min(1, x)), 3); // ease-out
export const sai = (x: number) => Math.pow(Math.max(0, Math.min(1, x)), 3); // ease-in
export const sorteio = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Cores do vídeo: destaque (da equipe/tema), fundo claro e escuro. */
export type Paleta = { destaque: string; claro: string; escuro: string; tinta: string };
export const PALETA: Paleta = { destaque: "#f2c230", claro: "#e9e7e2", escuro: "#101113", tinta: "#1d1d1d" };
export const Cores = createContext<Paleta>(PALETA);
export const useCores = () => useContext(Cores);

/** Movimento que a linha do tempo aplica à cena (transições): no todo (máscara) e só no conteúdo (o fundo fica parado). */
export type Mov = { todo: CSSProperties; conteudo: CSSProperties; antes: number };
export const Movimento = createContext<Mov>({ todo: {}, conteudo: {}, antes: 0 });

/** Quadro e segundos dentro da cena (0 = começo da cena, sem contar a entrada que começa antes). */
export function useTempo() {
  const { fps } = useVideoConfig();
  const q = useCurrentFrame() - useContext(Movimento).antes;
  return { q, t: q / fps, fps };
}

/** Cena = fundo parado + conteúdo que as transições movem. */
export const Cena: React.FC<{ fundo: ReactNode; children: ReactNode }> = ({ fundo, children }) => {
  const m = useContext(Movimento);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", ...m.todo }}>
      {fundo}
      <div style={{ position: "absolute", inset: 0, ...m.conteudo }}>{children}</div>
    </div>
  );
};

/** Fundos: estúdio claro (luz no centro, grade de pontos fraca), cor cheia e escuro granulado com vinheta. */
export const Fundo: React.FC<{ modo: "claro" | "cheio" | "escuro" | "tecnico"; cor?: string }> = ({ modo, cor }) => {
  const c = useCores();
  const { q } = useTempo();
  if (modo === "claro")
    return (
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 60%, #f8f7f3 0%, ${c.claro} 65%, #d6d3cc 100%)` }}>
        <div style={{ position: "absolute", inset: 0, opacity: 0.35, backgroundImage: "radial-gradient(#b9b5ad 1.4px, transparent 1.6px)", backgroundSize: "34px 34px" }} />
      </div>
    );
  if (modo === "cheio") return <div style={{ position: "absolute", inset: 0, background: cor ?? c.destaque }} />;
  return (
    <div style={{ position: "absolute", inset: 0, background: c.escuro }}>
      {modo === "tecnico" && (
        <div style={{ position: "absolute", inset: 0, opacity: 0.5, backgroundImage: "linear-gradient(#ffffff10 1px, transparent 1px), linear-gradient(90deg, #ffffff10 1px, transparent 1px)", backgroundSize: "60px 60px" }} />
      )}
      <Grao semente={q} />
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 50%, transparent 45%, #000000c0 100%)" }} />
    </div>
  );
};

/** Grão de filme (muda a cada quadro). */
export const Grao: React.FC<{ semente: number; forca?: number }> = ({ semente, forca = 0.13 }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0, opacity: forca, mixBlendMode: "screen" }}>
    <filter id={`grao${semente}`}>
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={semente % 97} />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <rect width={W} height={H} filter={`url(#grao${semente})`} />
  </svg>
);

// .glb carregado uma vez por aba (cada cena clona: a geometria é compartilhada)
const arquivos = new Map<string, Promise<GLTF>>();
export function carregar(arquivo: string): Promise<GLTF> {
  if (!arquivos.has(arquivo)) arquivos.set(arquivo, new GLTFLoader().loadAsync(staticFile(arquivo)));
  return arquivos.get(arquivo)!;
}

export type Tres = { r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera };

/**
 * 3D da cena num canvas 2D. `iniciar` monta o mundo (pode carregar arquivos); `pose(mundo, t)` põe tudo no instante t
 * (segundos da cena). Com `borrao` (fração do quadro em que o obturador fica aberto, ex. 0,8) o quadro é a média de
 * `amostras` instantes: passagem rápida do carro com rastro, como nas referências.
 */
export function useTres<M>(iniciar: (x: Tres) => Promise<M>, pose: (m: M, t: number, x: Tres) => void, opcoes: { borrao?: number; amostras?: number } = {}) {
  const tela = useRef<HTMLCanvasElement>(null);
  const estado = useRef<{ x: Tres; m: M } | null>(null);
  const [pronto, setPronto] = useState(false);
  const liberado = useRef(false);
  const [espera] = useState(() => delayRender("montando o 3D", { timeoutInMilliseconds: 240000 }));
  const { t, fps } = useTempo();

  useEffect(() => {
    const gl = document.createElement("canvas");
    gl.width = W;
    gl.height = H;
    const r = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setSize(W, H, false);
    r.setClearColor(0x000000, 0);
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.2;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    const x: Tres = { r, cena: new THREE.Scene(), cam: new THREE.PerspectiveCamera(30, W / H, 0.1, 3000) };
    let vivo = true;
    iniciar(x).then((m) => {
      if (!vivo) return;
      estado.current = { x, m };
      setPronto(true);
    });
    return () => {
      vivo = false;
      r.dispose();
      r.forceContextLoss();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    const e = estado.current;
    if (!pronto || !e) return;
    const ctx = tela.current!.getContext("2d")!;
    ctx.clearRect(0, 0, W, H);
    const n = opcoes.borrao ? Math.max(2, opcoes.amostras ?? 6) : 1;
    for (let i = 0; i < n; i++) {
      const dt = n > 1 ? (opcoes.borrao! * i) / (n - 1) / fps : 0;
      pose(e.m, t - dt, e.x);
      e.x.r.render(e.x.cena, e.x.cam);
      ctx.globalAlpha = 1 / (i + 1);
      ctx.drawImage(e.x.r.domElement, 0, 0);
    }
    ctx.globalAlpha = 1;
    if (!liberado.current) {
      liberado.current = true;
      continueRender(espera);
    }
  });

  return <canvas ref={tela} width={W} height={H} style={{ position: "absolute", inset: 0, width: W, height: H }} />;
}
