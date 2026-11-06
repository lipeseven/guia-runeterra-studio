// Cenas 3D do horizontal: estúdio (carro oficial com a palavra atrás) e pista (respiro: helicóptero, POV, passagem).
// O carro nunca fica parado na tela: toda câmera tem movimento (órbita, aproximação, deslize).
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { staticFile } from "remotion";
import { carregar, Cena, Fundo, suave, useCores, useTres, type Tres } from "./base";
import { preparar, type Roda } from "./carro";
import { criarChao, type Chao } from "./chao";
import { Palavra, type PalavraP } from "./textos";
import { Anotacoes, type Anotacao } from "./anotacoes";
import type { ReactNode } from "react";

type CarroPronto = { g: THREE.Group; rodas: Roda[]; raio: number; frenteZ: number };

async function carroDoArquivo(arquivo: string): Promise<CarroPronto> {
  const g = await carregar(arquivo);
  const p = preparar(g.scene.clone(true));
  return { g: p.carro, rodas: p.rodas, raio: p.raio, frenteZ: p.frenteZ };
}

function luzes(x: Tres, sombra: number) {
  const pm = new THREE.PMREMGenerator(x.r);
  x.cena.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  const luz = new THREE.DirectionalLight(0xffffff, 2.2);
  luz.position.set(1.5, 10, 2.5);
  luz.castShadow = true;
  luz.shadow.mapSize.set(4096, 4096);
  luz.shadow.radius = 14;
  Object.assign(luz.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 0.5, far: 30 });
  x.cena.add(luz);
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.ShadowMaterial({ opacity: sombra }));
  chao.rotation.x = -Math.PI / 2;
  chao.receiveShadow = true;
  x.cena.add(chao);
  return luz;
}

// modo técnico: o carro vira planta (arestas na cor de destaque sobre casca escura)
function emPlanta(carro: THREE.Group, cor: string) {
  const linha = new THREE.LineBasicMaterial({ color: cor, transparent: true, opacity: 0.9 });
  const casca = new THREE.MeshBasicMaterial({ color: "#0d0e10", polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const malhas: THREE.Mesh[] = [];
  carro.traverse((o) => { if ((o as THREE.Mesh).isMesh) malhas.push(o as THREE.Mesh); });
  for (const m of malhas) {
    m.material = casca;
    m.castShadow = false;
    m.add(new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry, 28), linha));
  }
}

export type CameraEstudio = { tipo: "orbita" | "aproximar" | "deslizar" | "chegada" | "frente" | "traseira" | "passagem"; de?: number; vel?: number };

export type EstudioP = {
  carro: string;
  modo?: "claro" | "cheio" | "escuro" | "tecnico";
  camera?: CameraEstudio;
  palavra?: PalavraP;
  anotacoes?: Anotacao[];
  extra?: ReactNode; // contador, rótulos (por cima do carro)
};

/** Estúdio: fundo → palavra gigante → carro 3D → anotações. */
export const Estudio: React.FC<EstudioP> = ({ carro, modo = "claro", camera = { tipo: "orbita" }, palavra, anotacoes, extra }) => {
  const c = useCores();
  const escuro = modo === "escuro" || modo === "tecnico";
  const passagem = camera.tipo === "passagem";
  const tela = useTres(
    async (x) => {
      luzes(x, escuro ? 0.5 : modo === "cheio" ? 0.3 : 0.22);
      if (escuro) {
        const contra = new THREE.DirectionalLight(0xffffff, 3);
        contra.position.set(-4, 3, -6);
        x.cena.add(contra);
      }
      const p = await carroDoArquivo(carro);
      if (modo === "tecnico") emPlanta(p.g, c.destaque);
      x.cena.add(p.g);
      x.cam.fov = 22;
      x.cam.updateProjectionMatrix();
      return p;
    },
    (p, t, x) => {
      const a0 = ((camera.de ?? 39) * Math.PI) / 180;
      const vel = camera.vel ?? 0.066;
      let d = 10.2, h = 1.5, a = a0 + vel * t, alvoY = 0.5, lado = 0;
      let andou = t * 0.4; // as rodas giram devagar mesmo parado (o carro "respira")
      p.g.position.set(0, 0, 0);
      if (camera.tipo === "aproximar") { d = 12.5 - 4 * suave(t, 0, 4); a = a0 + 0.03 * t; }
      if (camera.tipo === "deslizar") { lado = -1.2 + 0.6 * t; a = a0; }
      if (camera.tipo === "frente") { d = 7.6; h = 0.85; a = a0 + 0.05 * t; alvoY = 0.35; }
      if (camera.tipo === "traseira") { d = 7.8; h = 1.0; a = Math.PI + a0 * 0.4 + 0.05 * t; alvoY = 0.55; }
      if (camera.tipo === "chegada") {
        const falta = (1 - suave(t, 0, 1.8)) * 9;
        p.g.position.z = -p.frenteZ * falta;
        andou = 9 - falta;
      }
      if (camera.tipo === "passagem") {
        // o carro cruza a tela a ~250 km/h diante da câmera parada (22–24 quadros, rastro forte)
        const z = -30 + 70 * t;
        p.g.position.z = -p.frenteZ * -z;
        andou = z + 30;
        d = 7; h = 0.6; a = Math.PI / 2; alvoY = 0.4;
      }
      for (const rd of p.rodas) rd.pivo.children[0].rotation.x = (andou / p.raio) * p.frenteZ;
      x.cam.position.set(Math.sin(a) * d + lado, h, Math.cos(a) * d * p.frenteZ);
      x.cam.lookAt(lado * 0.6, alvoY, 0);
    },
    passagem ? { borrao: 1, amostras: 8 } : {},
  );
  return (
    <Cena fundo={<Fundo modo={modo} />}>
      {palavra && <Palavra {...palavra} cor={palavra.cor ?? (modo === "cheio" ? "#ffffff" : undefined)} />}
      {tela}
      {extra}
      {anotacoes && <Anotacoes itens={anotacoes} />}
    </Cena>
  );
};

// ---------------- pista ----------------

type PistaPronta = { linha: THREE.CatmullRomCurve3; comp: number; chao: Chao; carros: CarroPronto[]; luz: THREE.DirectionalLight };
const ASFALTO = new Set(["mesh2_7", "mesh2_11"]);
const ESCAPE = new Set(["mesh2_4"]);
const MANTER = new Set(["mesh2_8", "mesh2_9", "mesh2_6", "mesh2_17", "mesh2_15", "mesh2_19", "mesh2_12", "mesh2_14", "mesh2_3"]);
let chaoInterlagos: Chao | null = null;

export type CarroNaPista = { u0: number; km: number; lado?: number; ladoAte?: { valor: number; de: number; ate: number } };
export type CameraPista = { tipo: "helicoptero" | "pov" | "lado" | "passagem" | "drone"; alvo?: number };

export type PistaP = { pista?: string; alinhamento?: string; carro: string; carros: CarroNaPista[]; camera: CameraPista; palavra?: PalavraP; anotacoes?: Anotacao[]; extra?: ReactNode };

/** Respiro na pista real (Interlagos .glb, no estilo do estúdio: asfalto escuro, zebras originais, resto apagado). */
export const Pista: React.FC<PistaP> = ({ pista = "interlagos_sao_paulo.glb", alinhamento = "alinhamento_interlagos.json", carro, carros, camera, palavra, anotacoes, extra }) => {
  const c = useCores();
  const up = new THREE.Vector3(0, 1, 0);
  const tela = useTres<PistaPronta>(
    async (x) => {
      x.cena.background = new THREE.Color(c.claro);
      x.cena.fog = new THREE.Fog(c.claro, 220, 800);
      x.cena.environment = new THREE.PMREMGenerator(x.r).fromScene(new RoomEnvironment(), 0.04).texture;
      x.cena.add(new THREE.HemisphereLight(0xffffff, 0x888888, 0.6));
      const luz = new THREE.DirectionalLight(0xffffff, 2.4);
      luz.castShadow = true;
      luz.shadow.mapSize.set(4096, 4096);
      Object.assign(luz.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, near: 1, far: 200 });
      x.cena.add(luz, luz.target);
      x.cam.near = 0.3;
      const [al, gp] = await Promise.all([fetch(staticFile(alinhamento)).then((r) => r.json()), carregar(pista)]);
      const sup = gp.scene.getObjectByName("surface_2")!.clone(true);
      const fundo = new THREE.MeshStandardMaterial({ color: c.claro, roughness: 1 });
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
        else if (!MANTER.has(nome)) m.material = fundo;
        m.receiveShadow = true;
      });
      x.cena.add(sup);
      x.cena.updateMatrixWorld(true);
      chaoInterlagos ??= criarChao(piso);
      const linha = new THREE.CatmullRomCurve3((al.linha as number[][]).map(([a, b, d]) => new THREE.Vector3(a, b, d)), true, "centripetal");
      const prontos = await Promise.all(carros.map(() => carroDoArquivo(carro)));
      prontos.forEach((p) => x.cena.add(p.g));
      return { linha, comp: linha.getLength(), chao: chaoInterlagos, carros: prontos, luz };
    },
    (m, t, x) => {
      const naVolta = (u: number, lado: number) => {
        const uu = ((u % 1) + 1) % 1;
        const p = m.linha.getPointAt(uu);
        const tg = m.linha.getTangentAt(uu);
        return { p: p.add(new THREE.Vector3().crossVectors(tg, up).normalize().multiplyScalar(lado)), tg };
      };
      const noChao = (q: THREE.Vector3) => {
        const y = m.chao(q.x, q.z, q.y);
        if (y !== null) q.y = y;
        return q;
      };
      const us = carros.map((cp) => cp.u0 + (cp.km / 3.6 / m.comp) * t);
      carros.forEach((cp, i) => {
        const car = m.carros[i];
        const lado = cp.ladoAte ? (cp.lado ?? 0) + (cp.ladoAte.valor - (cp.lado ?? 0)) * suave(t, cp.ladoAte.de, cp.ladoAte.ate) : cp.lado ?? 0;
        const { p, tg } = naVolta(us[i], lado);
        const fr = tg.clone().setY(0).normalize();
        const di = new THREE.Vector3().crossVectors(fr, up).normalize();
        const roda = (a: number, b: number) => noChao(p.clone().addScaledVector(fr, a).addScaledVector(di, b));
        const fe = roda(1.8, -0.8), fd = roda(1.8, 0.8), te = roda(-1.8, -0.8), td = roda(-1.8, 0.8);
        const frente = new THREE.Vector3().addVectors(fe, fd).sub(te).sub(td).normalize();
        const direita = new THREE.Vector3().addVectors(fd, td).sub(fe).sub(te).normalize();
        const cima = new THREE.Vector3().crossVectors(direita, frente).normalize();
        const z = frente.clone().multiplyScalar(car.frenteZ);
        const xx = new THREE.Vector3().crossVectors(cima, z).normalize();
        car.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xx, new THREE.Vector3().crossVectors(z, xx), z));
        car.g.position.copy(fe).add(fd).add(te).add(td).multiplyScalar(0.25);
        const t2 = naVolta(us[i] + 8 / m.comp, lado).tg;
        const curva = new THREE.Vector3().crossVectors(tg, t2).y;
        const andou = (us[i] - cp.u0) * m.comp;
        for (const rd of car.rodas) {
          rd.pivo.rotation.y = rd.frente ? Math.max(-0.35, Math.min(0.35, curva * 4)) : 0;
          rd.pivo.children[0].rotation.x = (andou / car.raio) * car.frenteZ;
        }
        car.g.visible = !(camera.tipo === "pov" && i === (camera.alvo ?? 0));
      });
      // câmera
      const k = camera.alvo ?? 0;
      const alvo = m.carros[k].g.position.clone();
      const u = us[k];
      const dirMedia = naVolta(u + 25 / m.comp, 0).p.sub(naVolta(u - 25 / m.comp, 0).p).setY(0).normalize();
      const lat = new THREE.Vector3().crossVectors(dirMedia, up).normalize();
      const cam = x.cam;
      if (camera.tipo === "helicoptero") {
        cam.fov = 30;
        cam.position.copy(alvo).addScaledVector(dirMedia, -24 + 4 * suave(t, 0, 8)).addScaledVector(lat, 8 - 12 * suave(t, 0, 7)).add(new THREE.Vector3(0, 9, 0));
        cam.lookAt(alvo.clone().addScaledVector(dirMedia, 6));
      } else if (camera.tipo === "drone") {
        cam.fov = 34;
        cam.position.copy(alvo).addScaledVector(dirMedia, -45).add(new THREE.Vector3(0, 32, 0));
        cam.lookAt(alvo.clone().addScaledVector(dirMedia, 20));
      } else if (camera.tipo === "lado") {
        cam.fov = 26;
        cam.position.copy(alvo).addScaledVector(lat, -9).add(new THREE.Vector3(0, 1.1, 0)).addScaledVector(dirMedia, -1 + 0.4 * t);
        cam.lookAt(alvo.clone().add(new THREE.Vector3(0, 0.5, 0)));
      } else if (camera.tipo === "passagem") {
        // câmera parada à beira da pista; o carro passa (rastro pelo borrão)
        const fixo = naVolta(carros[k].u0 + (carros[k].km / 3.6 / m.comp) * 1.0, -8).p;
        cam.fov = 40;
        cam.position.copy(noChao(fixo)).add(new THREE.Vector3(0, 0.9, 0));
        cam.lookAt(alvo.clone().add(new THREE.Vector3(0, 0.4, 0)));
      } else {
        // POV de cockpit: olho do piloto, olhando o asfalto à frente (o carro dele fica escondido)
        cam.fov = 68;
        const olho = alvo.clone().add(new THREE.Vector3(0, 0.95, 0)).addScaledVector(dirMedia, 0.2);
        cam.position.copy(olho);
        cam.lookAt(noChao(naVolta(u + 30 / m.comp, 0).p).add(new THREE.Vector3(0, 0.6, 0)));
      }
      cam.updateProjectionMatrix();
      m.luz.position.copy(alvo).add(new THREE.Vector3(20, 60, 15));
      m.luz.target.position.copy(alvo);
    },
    camera.tipo === "passagem" ? { borrao: 1, amostras: 8 } : camera.tipo === "pov" ? { borrao: 0.6, amostras: 4 } : {},
  );
  return (
    <Cena fundo={<div style={{ position: "absolute", inset: 0, background: c.claro }} />}>
      {tela}
      {palavra && <Palavra {...palavra} />}
      {extra}
      {anotacoes && <Anotacoes itens={anotacoes} />}
    </Cena>
  );
};
