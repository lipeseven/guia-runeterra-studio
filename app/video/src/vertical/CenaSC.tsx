// Cena de bandeira amarela e Safety Car. A câmera segue o sentimento da fala: cada plano começa numa palavra.
// Batida: aproximação tremida. Bandeira: close girando. Freada: perseguição rasante que sobe até a vista de cima.
// Safety Car: contra-plongée vindo de frente. Fila: drone recuando. Vantagem: vista de cima se abrindo.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { PINTURAS, caixa, carro, degradeRadial, plano, texturaPista } from "./Carro3D";
import { FONTE, Legenda, Placa, entra, noTrecho, suave, type Palavra } from "./kit";
import { vantage } from "./Vantage";

type V = [number, number, number];
type Marcas = Record<string, number>;

const N = 8;
const Z_BATIDA = -900;
const Z_BANDEIRA = -1000;

/** Distância percorrida pelo pelotão: rápido até "reduz", depois em ritmo de bandeira. Soma tabelada, função pura de t. */
const distancia = (t: number, m: Marcas) => {
  let d = 0;
  for (let u = 0; u < t; u += 1 / 60) {
    const v = 78 - 46 * suave(u, m.reduz - 0.1, m.serio) - 8 * suave(u, m.sc, m.fila);
    d += v / 60;
  }
  return d;
};

const posCarro = (k: number, t: number, m: Marcas): V => {
  const aperta = suave(t, m.fila, m.vant + 0.9);
  const gap = 15 - aperta * 8.6;
  return [(k % 2 ? -1 : 1) * (2.3 - aperta * 0.7), 0, -distancia(t, m) + k * gap];
};

const lerp = (a: V, b: V, k: number): V => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];

/** O plano ativo a cada instante: [posição, para onde olha, lente, inclinação]. */
function plano_(t: number, m: Marcas): [V, V, number, number] {
  const lid = posCarro(0, t, m);
  const dois = posCarro(1, t, m);
  if (t < m.primeiro) {
    const k = suave(t, 0, m.primeiro);
    const treme = Math.sin(t * 61) * 0.05 + Math.sin(t * 37) * 0.04;
    return [[6.4 + k * 1.1 + treme, 1.05 + treme, Z_BATIDA + 9 - k * 3.4], [9.4, 0.7, Z_BATIDA], 38, Math.sin(t * 43) * 0.012];
  }
  if (t < m.reduz) {
    const k = suave(t, m.primeiro, m.reduz);
    const a = 1.15 - k * 0.5; // gira em volta da bandeira, olhando de baixo
    const r = 7.2 - k * 2.2;
    return [[-9.9 + Math.cos(a) * r * 0.5, 1.5 + k * 0.4, Z_BANDEIRA + Math.sin(a) * r], [-9.9, 3.45, Z_BANDEIRA], 42, 0];
  }
  if (t < m.serio) {
    const sobe = suave(t, m.ninguem - 0.1, m.serio - 0.15);
    const baixo: V = [dois[0] + 0.9, 0.85, dois[2] + 5.3];
    const alto: V = [lid[0] * 0.1, 44, lid[2] + 10];
    const olhaBaixo: V = [dois[0], 0.5, dois[2] - 28];
    const olhaAlto: V = [lid[0] * 0.1, 0, lid[2] + 9];
    return [lerp(baixo, alto, sobe), lerp(olhaBaixo, olhaAlto, sobe), 54 - sobe * 12, Math.sin(t * 34) * 0.006 * (1 - sobe)];
  }
  if (t < m.sc - 0.25) {
    const k = suave(t, m.serio, m.sc);
    return [[4.2 + k * 2, 2 - k * 0.7, Z_BATIDA + 15 - k * 7], [9.4, 0.6, Z_BATIDA], 34, 0];
  }
  if (t < m.fila) {
    const k = suave(t, m.sc - 0.25, m.fila);
    const sc = posSc(t, m);
    return [[sc[0] + 3.2 - k * 1.5, 0.55 + k * 0.3, sc[2] - 12.5 + k * 3.2], [sc[0] + 0.25, 0.8, sc[2] + 0.3], 40, 0.03 - k * 0.03];
  }
  if (t < m.vant) {
    const k = suave(t, m.fila, m.vant);
    return [[3.4, 8 + k * 9, lid[2] + 30 + k * 20], [0, 0, lid[2] + 8], 42, 0];
  }
  const k = suave(t, m.vant, m.vant + 1.8);
  return [[0, 50 + k * 28, lid[2] + 20], [0, 0, lid[2] + 19], 36, 0];
}

const posSc = (t: number, m: Marcas): V => {
  const lid = posCarro(0, t, m);
  const entrada = suave(t, m.sc - 0.5, m.sc + 0.9);
  return [8.2 - entrada * 8.2, 0, lid[2] - 17 + (1 - entrada) * -18];
};

function ceu(): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 8;
  c.height = 512;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, "#0e2a52");
  g.addColorStop(0.32, "#3f6f96");
  g.addColorStop(0.46, "#e8b286");
  g.addColorStop(0.52, "#f6c98c");
  g.addColorStop(1, "#f6c98c");
  x.fillStyle = g;
  x.fillRect(0, 0, 8, 512);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

type Mundo = {
  r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; sol: THREE.DirectionalLight;
  carros: THREE.Group[]; sc: THREE.Group; rodasSc: THREE.Group[]; luzes: THREE.MeshStandardMaterial[]; pano: THREE.Mesh;
  fumaca: THREE.Sprite[]; amarelo: THREE.MeshBasicMaterial;
};

function montar(canvas: HTMLCanvasElement): Mundo {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  r.setSize(1080, 1920, false);
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.ACESFilmicToneMapping;
  r.toneMappingExposure = 0.96;
  r.shadowMap.enabled = true;
  r.shadowMap.type = THREE.PCFSoftShadowMap;
  const cena = new THREE.Scene();
  cena.background = ceu();
  cena.fog = new THREE.Fog("#f0c08a", 90, 240);
  cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
  cena.environmentIntensity = 0.32;
  cena.add(new THREE.HemisphereLight("#ffe9d2", "#2a2433", 0.85));
  const sol = new THREE.DirectionalLight("#fff0dc", 2.1);
  sol.castShadow = true;
  sol.shadow.mapSize.set(4096, 4096);
  sol.shadow.radius = 5;
  sol.shadow.bias = -0.0004;
  Object.assign(sol.shadow.camera, { left: -45, right: 45, top: 90, bottom: -90, near: 1, far: 120 });
  cena.add(sol, sol.target);

  const mapa = texturaPista();
  const comp = 1800;
  mapa.repeat.set(1, comp / 60);
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(48, comp), new THREE.MeshStandardMaterial({ map: mapa, roughness: 0.92 }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.z = -600;
  chao.receiveShadow = true;
  cena.add(chao);
  for (const s of [-1, 1]) {
    const longe = new THREE.Mesh(new THREE.PlaneGeometry(500, comp), new THREE.MeshStandardMaterial({ color: "#25663b", roughness: 1 }));
    longe.rotation.x = -Math.PI / 2;
    longe.position.set(s * 274, -0.01, -600);
    cena.add(longe);
  }
  const amarelo = new THREE.MeshBasicMaterial({ color: "#ffd400", transparent: true, opacity: 0 });
  for (const s of [-1, 1]) cena.add(plano(0.34, comp, s * 6.26, -600, amarelo, 0.03));

  const sombra = new THREE.MeshBasicMaterial({ map: degradeRadial("rgba(0,0,0,.74)"), transparent: true, depthWrite: false });
  const fazer = (mod: THREE.Group) => {
    const g = new THREE.Group();
    const c = mod.clone();
    c.scale.set(0.7, 0.9, 1.1);
    g.add(c, plano(2.5, 7.2, 0, 0, sombra));
    cena.add(g);
    return g;
  };
  const modelos = PINTURAS.map(carro);
  const carros = Array.from({ length: N }, (_, k) => fazer(modelos[k % modelos.length]));

  // Safety Car com barra de luzes no teto
  const sc = new THREE.Group();
  const { carro: modeloSc, rodas: rodasSc } = vantage();
  sc.add(modeloSc, plano(2.7, 5.6, 0, 0, sombra));
  cena.add(sc);
  sc.add(caixa(1.05, 0.05, 0.2, 0, 1.3, 0.42, "#101116"));
  const luzes = [0, 1].map(() => new THREE.MeshStandardMaterial({ color: "#3a2a00", emissive: "#ffae00", emissiveIntensity: 0 }));
  luzes.forEach((mat, k) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.06, 0.16), mat);
    m.position.set(k ? 0.27 : -0.27, 1.355, 0.42);
    sc.add(m);
  });

  // carro batido na área de escape, de lado
  const batido = fazer(modelos[3]);
  batido.position.set(9.4, 0, Z_BATIDA);
  batido.rotation.y = 0.95;
  batido.rotation.z = 0.05;
  const fumaca = Array.from({ length: 26 }, () => {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: degradeRadial("rgba(225,225,228,.72)"), transparent: true, depthWrite: false }));
    cena.add(sp);
    return sp;
  });

  // posto de bandeira: mastro e pano que ondula
  const mastro = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 4.6, 12), new THREE.MeshStandardMaterial({ color: "#e4e7ec", metalness: 0.6, roughness: 0.3 }));
  mastro.position.set(-11, 2.3, Z_BANDEIRA);
  cena.add(mastro);
  const pano = new THREE.Mesh(new THREE.PlaneGeometry(2.1, 1.35, 42, 16), new THREE.MeshStandardMaterial({ color: "#ffcf00", roughness: 0.55, side: THREE.DoubleSide }));
  pano.position.set(-9.93, 3.75, Z_BANDEIRA);
  pano.castShadow = true;
  cena.add(pano);
  const cam = new THREE.PerspectiveCamera(40, 1080 / 1920, 0.1, 500);
  return { r, cena, cam, sol, carros, sc, rodasSc, luzes, pano, fumaca, amarelo };
}

export const CenaSC: React.FC<{ palavras: Palavra[] }> = ({ palavras }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const quadro = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = quadro / fps;
  const em = (x: string) => noTrecho(palavras, x);
  const m: Marcas = { primeiro: em("Primeiro"), amarela: em("bandeira amarela"), reduz: em("reduz"), ninguem: em("ninguém"), serio: em("Se for"), sc: em("safety car"), fila: em("A fila"), vant: em("a vantagem") };
  const fim = palavras[palavras.length - 1].f;
  const [alca] = useState(() => delayRender("desenhando o quadro 3D"));
  useLayoutEffect(() => {
    const w = mundo.current ?? (mundo.current = montar(ref.current!));
    w.carros.forEach((c, k) => c.position.set(...posCarro(k, t, m)));
    w.sc.position.set(...posSc(t, m));
    w.sc.visible = t >= m.sc - 0.6;
    w.rodasSc.forEach((r) => (r.rotation.x = w.sc.position.z / 0.355));
    const pisca = Math.sin(t * 26) > 0;
    w.luzes[0].emissiveIntensity = pisca ? 3.5 : 0.2;
    w.luzes[1].emissiveIntensity = pisca ? 0.2 : 3.5;
    w.amarelo.opacity = entra(t, m.amarela, 0.25) * (1 - suave(t, m.fila, m.vant)) * 0.95;
    // pano ondulando
    const pos = w.pano.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i) + 1.05;
      pos.setZ(i, Math.sin(x * 3.6 - t * 10 + pos.getY(i) * 0.7) * 0.11 * (0.3 + x));
    }
    pos.needsUpdate = true;
    w.pano.geometry.computeVertexNormals();
    w.fumaca.forEach((f, k) => {
      const vida = (t * (0.3 + (k % 5) * 0.05) + k * 0.137) % 1;
      f.position.set(9.4 + Math.sin(k * 7) * 1.2 + vida * 2.2, 0.4 + vida * 5.5, Z_BATIDA + Math.cos(k * 3) * 1.2);
      const e = 0.9 + vida * 4.4;
      f.scale.set(e, e, 1);
      (f.material as THREE.SpriteMaterial).opacity = (1 - vida) * 0.62;
    });
    const [pc, olha, lente, rolar] = plano_(t, m);
    w.cam.position.set(...pc);
    w.cam.fov = lente;
    w.cam.updateProjectionMatrix();
    w.cam.up.set(Math.sin(rolar), Math.cos(rolar), 0);
    if (pc[1] > 30) w.cam.up.set(0, 0, -1);
    w.cam.lookAt(...olha);
    w.sol.position.set(pc[0] * 0.2 - 16, 52, olha[2] - 24);
    w.sol.target.position.set(olha[0], 0, olha[2]);
    w.sol.target.updateMatrixWorld();
    w.r.render(w.cena, w.cam);
    continueRender(alca);
  });
  const vant = 12.4 - 11.6 * suave(t, m.vant, m.vant + 0.9);
  const kmh = 300 - 150 * suave(t, m.reduz - 0.1, m.serio - 0.5);
  return (
    <AbsoluteFill style={{ background: "#0b0c11" }}>
      <Audio src={staticFile("f1-teste/voz.wav")} />
      <canvas ref={ref} width={1080} height={1920} style={{ position: "absolute", width: 1080, height: 1920 }} />
      <AbsoluteFill style={{ background: "#ffd400", opacity: (1 - entra(t, m.amarela, 0.4)) * (t >= m.amarela ? 0.5 : 0) }} />
      {t >= m.reduz && t < m.serio && <Placa texto={kmh.toFixed(0)} unidade="km/h" inicio={m.reduz} x={540} y={1660} cor={kmh < 200 ? "#ffd400" : "#fff"} />}
      {t >= m.ninguem + 0.3 && t < m.serio && <Placa texto="NÃO ULTRAPASSE" inicio={m.ninguem + 0.3} x={540} y={540} cor="#ffd400" tam={62} />}
      {t >= m.sc && t < m.fila && (
        <div style={{ position: "absolute", left: "50%", top: 500, transform: `translateX(-50%) scale(${0.7 + entra(t, m.sc, 0.25) * 0.3})`, opacity: entra(t, m.sc, 0.15), background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00" }}>SC</div>
      )}
      {t >= m.fila + 0.2 && <Placa texto={vant.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} unidade="s de vantagem" inicio={m.fila + 0.2} x={540} y={1680} cor={vant < 2 ? "#ff5a4a" : "#fff"} />}
      <Legenda palavras={palavras} chaves={["amarela", "ultrapassa", "safety", "vantagem"]} />
      <AbsoluteFill style={{ background: "#000", opacity: suave(t, fim + 0.15, fim + 0.55), fontFamily: FONTE, zIndex: 99 }} />
    </AbsoluteFill>
  );
};
