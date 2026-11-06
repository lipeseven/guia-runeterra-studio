import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { preparar } from "./TesteEstudio";
import { criarChao, type Chao } from "./horizontal/chao";

// Teste do horizontal: pista real do .glb (só a superfície, no estilo do estúdio: asfalto escuro, zebras, resto apagado),
// duas Ferraris disputando no S do Senna e a linha na cor de destaque atrás de quem ataca.
// Trajetória = traçado real alinhado ao .glb (alinhamento_interlagos.json: x, altura, z a cada ~3,6 m; f 0 = chegada).
const W = 1920;
const H = 1080;
const FPS = 30;
const ASFALTO = new Set(["mesh2_7", "mesh2_11"]);
const ESCAPE = new Set(["mesh2_4"]);
// textura original: zebras verde/amarela/branca de Interlagos (mesh2_8, mesh2_9), linhas brancas, amarelas e vermelhas,
// faixas pintadas e grelhas
const MANTER = new Set(["mesh2_8", "mesh2_9", "mesh2_6", "mesh2_17", "mesh2_15", "mesh2_19", "mesh2_12", "mesh2_14", "mesh2_3"]);

type Carro = { g: THREE.Group; rodas: { pivo: THREE.Group; frente: boolean }[]; raio: number; frenteZ: number };
type Mundo = { r: THREE.WebGLRenderer; cena: THREE.Scene; cam: THREE.PerspectiveCamera; luz: THREE.DirectionalLight; linha: THREE.CatmullRomCurve3; comp: number; a: Carro; b: Carro; rastro: THREE.Mesh; chao: Chao };


const suave = (t: number, a: number, b: number) => {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
};

export const TesteCorrida: React.FC<{ pista: string; carro: string; fundo: string; destaque: string }> = ({ pista, carro, fundo, destaque }) => {
  const f = useCurrentFrame();
  const tela = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const [pronto, setPronto] = useState(false);
  const [espera] = useState(() => delayRender("carregando pista e carros"));

  useEffect(() => {
    const r = new THREE.WebGLRenderer({ canvas: tela.current!, antialias: true, preserveDrawingBuffer: true });
    r.setSize(W, H, false);
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.0;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    const cena = new THREE.Scene();
    cena.background = new THREE.Color(fundo);
    cena.fog = new THREE.Fog(fundo, 220, 800); // o que está longe some no fundo
    cena.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
    cena.add(new THREE.HemisphereLight(0xffffff, 0x888888, 0.6));
    const luz = new THREE.DirectionalLight(0xffffff, 2.4);
    luz.castShadow = true;
    luz.shadow.mapSize.set(4096, 4096);
    luz.shadow.radius = 8;
    Object.assign(luz.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, near: 1, far: 200 });
    cena.add(luz, luz.target);
    const cam = new THREE.PerspectiveCamera(30, W / H, 0.5, 3000);
    const loader = new GLTFLoader();
    Promise.all([
      fetch(staticFile("alinhamento_interlagos.json")).then((x) => x.json()),
      loader.loadAsync(staticFile(pista)),
      loader.loadAsync(staticFile(carro)),
      loader.loadAsync(staticFile(carro)),
    ]).then(([al, gp, ga, gb]) => {
      const sup = gp.scene.getObjectByName("surface_2")!;
      const corFundo = new THREE.MeshStandardMaterial({ color: fundo, roughness: 1 });
      const asfalto = new THREE.MeshStandardMaterial({ color: "#1b1c1f", roughness: 0.9 });
      const escape = new THREE.MeshStandardMaterial({ color: "#2c2d31", roughness: 0.95 });
      const piso: THREE.Mesh[] = [];
      sup.traverse((o) => {
        const m = o as THREE.Mesh;
        if (!m.isMesh) return;
        const nome = (m.material as THREE.Material).name;
        if (ASFALTO.has(nome) || nome === "mesh2_8" || nome === "mesh2_9") piso.push(m);
        if (nome === "mesh2_0") m.visible = false;
        else if (ASFALTO.has(nome)) m.material = asfalto;
        else if (ESCAPE.has(nome)) m.material = escape;
        else if (!MANTER.has(nome)) m.material = corFundo;
        m.receiveShadow = true;
      });
      cena.add(sup);
      cena.updateMatrixWorld(true);
      const chao = criarChao(piso);
      const pts = (al.linha as number[][]).map(([x, y, z]) => new THREE.Vector3(x, y, z));
      const linha = new THREE.CatmullRomCurve3(pts, true, "centripetal");
      const prep = (g: { scene: THREE.Group }): Carro => {
        const p = preparar(g.scene);
        cena.add(p.carro);
        return { g: p.carro, rodas: p.rodas, raio: p.raio, frenteZ: p.frenteZ };
      };
      const rastro = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ color: destaque, transparent: true, opacity: 0.95, polygonOffset: true, polygonOffsetFactor: -4 }));
      rastro.renderOrder = 5;
      cena.add(rastro);
      mundo.current = { r, cena, cam, luz, linha, comp: linha.getLength(), a: prep(ga), b: prep(gb), rastro, chao };
      setPronto(true);
      continueRender(espera);
    });
    return () => r.dispose();
  }, [pista, carro, fundo, destaque, espera]);

  useLayoutEffect(() => {
    const m = mundo.current;
    if (!pronto || !m) return;
    const t = f / FPS;
    const up = new THREE.Vector3(0, 1, 0);
    // posição na volta (fração f) com deslocamento lateral em metros (positivo = direita do sentido da corrida)
    const naVolta = (u: number, lado: number) => {
      const uu = ((u % 1) + 1) % 1;
      const p = m.linha.getPointAt(uu);
      const tg = m.linha.getTangentAt(uu);
      const dir = new THREE.Vector3().crossVectors(tg, up).normalize();
      return { p: p.add(dir.multiplyScalar(lado)), tg };
    };
    const vel = (km: number) => km / 3.6 / m.comp; // fração da volta por segundo
    // B (à frente) mantém ~250 km/h por fora; A vem no vácuo a ~262 km/h e mergulha por dentro na freada do S
    const uB = 0.04 + vel(250) * t;
    const uA = 0.034 + vel(262) * t;
    const ladoA = -3.2 * suave(t, 2.2, 4.6);
    const ladoB = 0.4;
    // ponto no asfalto real (a linha do alinhamento só dá a altura do centro, a cada ~3,6 m)
    const noChao = (q: THREE.Vector3) => {
      const y = m.chao(q.x, q.z, q.y);
      if (y !== null) q.y = y;
      return q;
    };
    // apoia o carro nas 4 rodas: altura e inclinação (subida, descida e lado) seguem a superfície
    const EIXO = 1.8;
    const BITOLA = 0.8;
    const poe = (c: Carro, u: number, lado: number, prev: number) => {
      const { p, tg } = naVolta(u, lado);
      const fr = tg.clone().setY(0).normalize();
      const di = new THREE.Vector3().crossVectors(fr, up).normalize();
      const roda = (a: number, b: number) => noChao(p.clone().addScaledVector(fr, a).addScaledVector(di, b));
      const fe = roda(EIXO, -BITOLA), fd = roda(EIXO, BITOLA), te = roda(-EIXO, -BITOLA), td = roda(-EIXO, BITOLA);
      const frente = new THREE.Vector3().addVectors(fe, fd).sub(te).sub(td).normalize();
      const direita = new THREE.Vector3().addVectors(fd, td).sub(fe).sub(te).normalize();
      const cima = new THREE.Vector3().crossVectors(direita, frente).normalize();
      const z = frente.clone().multiplyScalar(c.frenteZ);
      const x = new THREE.Vector3().crossVectors(cima, z).normalize();
      c.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, new THREE.Vector3().crossVectors(z, x), z));
      c.g.position.copy(fe).add(fd).add(te).add(td).multiplyScalar(0.25);
      const andou = (u - prev) * m.comp;
      const t2 = naVolta(u + 8 / m.comp, lado).tg;
      const curva = new THREE.Vector3().crossVectors(tg, t2).y; // >0 = curva à esquerda
      for (const rd of c.rodas) {
        rd.pivo.rotation.y = rd.frente ? Math.max(-0.35, Math.min(0.35, curva * 4)) : 0;
        rd.pivo.children[0].rotation.x = (andou / c.raio) * c.frenteZ;
      }
    };
    poe(m.a, uA, ladoA, 0.034);
    poe(m.b, uB, ladoB, 0.04);
    // linha atrás de A: do início da manobra até o carro, na mesma trajetória
    const ini = 0.034 + vel(262) * 1.2;
    const fim = uA - 3.5 / m.comp;
    const n = 160;
    const pos: number[] = [];
    if (fim > ini) {
      for (let i = 0; i <= n; i++) {
        const u = ini + ((fim - ini) * i) / n;
        const tt = (u - 0.034) / vel(262);
        const { p, tg } = naVolta(u, -3.2 * suave(tt, 2.2, 4.6));
        const dir = new THREE.Vector3().crossVectors(tg, up).normalize().multiplyScalar(0.28);
        const e = noChao(p.clone().sub(dir));
        const d = noChao(p.clone().add(dir));
        pos.push(e.x, e.y + 0.06, e.z, d.x, d.y + 0.06, d.z);
      }
    }
    const idx: number[] = [];
    for (let i = 0; i < pos.length / 6 - 1; i++) idx.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
    m.rastro.geometry.dispose();
    m.rastro.geometry = new THREE.BufferGeometry();
    m.rastro.geometry.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    m.rastro.geometry.setIndex(idx);
    // câmera: helicóptero baixo atrás e ao lado dos dois, deslizando para o lado de dentro
    const meio = new THREE.Vector3().addVectors(m.a.g.position, m.b.g.position).multiplyScalar(0.5);
    // direção da pista média em ±25 m: a câmera não sacode com cada pontinho da linha
    const um = (uA + uB) / 2;
    const tg = naVolta(um + 25 / m.comp, 0).p.sub(naVolta(um - 25 / m.comp, 0).p).setY(0).normalize();
    const lat = new THREE.Vector3().crossVectors(tg, up).normalize();
    const atras = 26 - 6 * suave(t, 0, 8);
    const ladoCam = 10 - 18 * suave(t, 1, 7);
    m.cam.position.copy(meio).addScaledVector(tg, -atras).addScaledVector(lat, ladoCam).add(new THREE.Vector3(0, 9 - 2 * suave(t, 0, 8), 0));
    m.cam.lookAt(meio.clone().addScaledVector(tg, 6).add(new THREE.Vector3(0, 0.5, 0)));
    m.luz.position.copy(meio).add(new THREE.Vector3(20, 60, 15));
    m.luz.target.position.copy(meio);
    m.r.render(m.cena, m.cam);
  }, [f, pronto]);

  return (
    <AbsoluteFill style={{ background: fundo }}>
      <canvas ref={tela} width={W} height={H} style={{ position: "absolute", inset: 0, width: W, height: H }} />
    </AbsoluteFill>
  );
};
