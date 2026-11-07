// Cenas 3D do horizontal: estúdio (carro oficial com a palavra atrás) e pista (respiro: helicóptero, POV, passagem).
// O carro nunca fica parado na tela: toda câmera tem movimento (órbita, aproximação, deslize).
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { staticFile } from "remotion";
import { carregar, Cena, Cores, corSobre, entra, Fundo, sai, suave, useCores, useTres, type Tres } from "./base";
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

export type CameraEstudio = {
  tipo: "orbita" | "aproximar" | "deslizar" | "chegada" | "frente" | "traseira" | "perfil" | "cima" | "baixo" | "detalhe" | "passagem" | "atravessar";
  de?: number; // graus de onde a câmera começa (positivo: frente para a esquerda; negativo: para a direita; ~180: de trás)
  vel?: number;
  sentido?: 1 | -1; // para que lado a câmera gira
  enquadre?: "esquerda" | "centro" | "direita"; // onde o carro fica na tela (o resto fica livre para texto)
  alvo?: "asa_dianteira" | "roda_dianteira" | "cockpit" | "asa_traseira" | "roda_traseira"; // detalhe
};

/** Câmera do estúdio no instante t, em coordenadas em volta do carro (ângulo, distância, altura, alvo). Função pura:
 *  serve também para saber onde a cena ANTERIOR terminou e continuar dali (a câmera gira de uma peça para outra). */
type Pose = { a: number; d: number; h: number; alvo: THREE.Vector3; pan: number; carroZ: number; andou: number };
function poseEstudio(camera: CameraEstudio, t: number, fz: number): Pose {
  const s = camera.sentido ?? 1;
  const a0 = ((camera.de ?? 39) * Math.PI) / 180;
  let d = 10.2, h = 1.5, a = a0 + (camera.vel ?? 0.066) * s * t, pan = 0, carroZ = 0, andou = 0; // parado = rodas paradas
  const alvo = new THREE.Vector3(0, 0.5, 0);
  switch (camera.tipo) {
    case "aproximar": d = 12.5 - 4 * suave(t, 0, 4); a = a0 + 0.03 * s * t; break;
    case "deslizar": a = a0; pan = (-0.6 + 0.3 * t) * s; break;
    case "frente": d = 7.6; h = 0.85; a = a0 + 0.05 * s * t; alvo.y = 0.35; break;
    case "traseira": d = 7.8; h = 1.0; a = Math.PI + a0 * 0.4 + 0.05 * s * t; alvo.y = 0.55; break;
    case "perfil": d = 11; h = 0.9; a = (a0 < 0 ? -1 : 1) * Math.PI / 2 + 0.02 * s * t; alvo.y = 0.55; break;
    case "cima": d = 2.6; h = 13 - 0.35 * t; a = a0 + 0.04 * s * t; alvo.y = 0; break;
    case "baixo": d = 8.4 - 0.3 * t; h = 0.22; alvo.y = 0.75; a = a0 + 0.03 * s * t; break;
    case "detalhe": {
      const pontos = { asa_dianteira: [0, 0.2, 2.45], roda_dianteira: [0.72, 0.36, 1.8], cockpit: [0, 0.85, 0.1], asa_traseira: [0, 0.9, -2.45], roda_traseira: [0.72, 0.36, -1.75] };
      const [px, py, pz] = pontos[camera.alvo ?? "asa_dianteira"];
      alvo.set(px * Math.sign(Math.sin(a0) || 1), py, pz * fz);
      d = 3.8 - 0.15 * t; h = py + 0.5; a = a0 + 0.05 * s * t;
      break;
    }
    case "chegada": {
      const falta = (1 - suave(t, 0, 1.8)) * 9;
      carroZ = -fz * falta;
      andou = 9 - falta;
      break;
    }
    case "passagem": {
      // o carro entra a ~250 km/h (rastro forte) e freia até parar no meio da tela: serve para cena de qualquer duração
      const z = -40 * (1 - entra(t / 0.9));
      carroZ = fz * z;
      andou = z + 40;
      d = 10.5; h = 0.7; a = Math.PI / 2 * (a0 < 0 ? -1 : 1); alvo.y = 0.45;
      break;
    }
    case "atravessar":
      // a câmera passa direto: o carro sai por um lado da tela e entra pelo outro (com rastro), e fica
      a = a0 + 0.03 * s * t;
      pan = (t < 0.35 ? 6.6 * sai(t / 0.35) : t < 0.7 ? -6.6 * (1 - entra((t - 0.35) / 0.35)) : 0) * s;
      break;
  }
  return { a, d, h, alvo, pan, carroZ, andou };
}

const misturaAngulo = (a: number, b: number, k: number) => {
  let d = (b - a) % (2 * Math.PI);
  if (d > Math.PI) d -= 2 * Math.PI;
  if (d < -Math.PI) d += 2 * Math.PI;
  return a + d * k;
};

export type EstudioP = {
  carro: string;
  continua?: { camera: CameraEstudio; dur: number }; // a cena anterior (mesmo estúdio): a câmera sai de onde ela parou
  modo?: "claro" | "cheio" | "escuro" | "tecnico";
  camera?: CameraEstudio;
  palavra?: PalavraP;
  anotacoes?: Anotacao[];
  extra?: ReactNode; // contador, rótulos (por cima do carro)
};

/** Estúdio: fundo → palavra gigante → carro 3D → anotações. */
export const Estudio: React.FC<EstudioP> = ({ carro, modo = "claro", camera = { tipo: "orbita" }, palavra, anotacoes, extra, continua }) => {
  const c = useCores();
  const escuro = modo === "escuro" || modo === "tecnico";
  const passagem = camera.tipo === "passagem";
  const perto = camera.tipo === "detalhe" || camera.tipo === "baixo";
  const fundoCor = modo === "claro" ? c.claro : modo === "cheio" ? c.destaque : c.escuro;
  const corPalavra = corSobre(fundoCor, palavra?.cor ?? (modo === "cheio" ? "#ffffff" : c.destaque));
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
      const fz = p.frenteZ;
      const atual = poseEstudio(camera, t, fz);
      let { a, d, h, pan } = atual;
      const alvo = atual.alvo.clone();
      if (continua) {
        // gira de onde a cena anterior parou até o novo ângulo/peça em ~1,1 s (o carro não sai do lugar)
        const antes = poseEstudio(continua.camera, continua.dur, fz);
        const k = entra(t / 1.1);
        a = misturaAngulo(antes.a, atual.a, k);
        d = antes.d + (atual.d - antes.d) * k;
        h = antes.h + (atual.h - antes.h) * k;
        pan = antes.pan + (atual.pan - antes.pan) * k;
        alvo.lerpVectors(antes.alvo, atual.alvo, k);
      }
      const andou = atual.andou;
      p.g.position.set(0, 0, atual.carroZ);
      for (const rd of p.rodas) rd.pivo.children[0].rotation.x = (andou / p.raio) * fz;
      const pos = new THREE.Vector3(alvo.x + Math.sin(a) * d, h, alvo.z + Math.cos(a) * d * fz);
      // enquadre: anda a câmera para o lado (o carro vai para o lado oposto da tela)
      const enq = (cm: CameraEstudio) => (cm.tipo === "detalhe" ? 0 : cm.enquadre === "esquerda" ? 1 : cm.enquadre === "direita" ? -1 : 0); // close fica centrado
      const k = (continua ? enq(continua.camera) + (enq(camera) - enq(continua.camera)) * entra(t / 1.1) : enq(camera)) + pan;
      if (k) {
        const lado = new THREE.Vector3().subVectors(alvo, pos).cross(new THREE.Vector3(0, 1, 0)).normalize().multiplyScalar(k * d * 0.1);
        pos.add(lado);
        alvo.add(lado);
      }
      x.cam.position.copy(pos);
      x.cam.lookAt(alvo);
    },
    passagem ? { borrao: 1, amostras: 8 } : camera.tipo === "atravessar" ? { borrao: 0.8, amostras: 5 } : {},
  );
  return (
    <Cena fundo={<Fundo modo={modo} />}>
      {palavra && !perto && <Palavra {...palavra} cor={corPalavra} />}
      {tela}
      {/* close: o carro enche a tela e taparia a palavra; ela vem por cima, menor, no alto */}
      {palavra && perto && <Palavra {...palavra} tam={Math.min(palavra.tam ?? 300, 300)} topo={60} cor={corPalavra} />}
      {/* no fundo escuro, anotação e rótulo são claros */}
      <Cores.Provider value={{ ...c, tinta: corSobre(fundoCor, escuro ? "#f1efe9" : c.tinta, 4.5), destaque: corSobre(fundoCor, modo === "cheio" ? c.tinta : c.destaque) }}>
        {extra}
        {anotacoes && <Anotacoes itens={anotacoes} />}
      </Cores.Provider>
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
      {palavra && <Palavra {...palavra} cor={corSobre(c.claro, palavra.cor ?? c.destaque)} />}
      {extra}
      {anotacoes && <Anotacoes itens={anotacoes} />}
    </Cena>
  );
};
