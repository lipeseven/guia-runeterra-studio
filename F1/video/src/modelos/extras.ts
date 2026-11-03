// Modelos da biblioteca criados sob demanda (piloto, kart, pódio, escada de categorias, mapa, número no carro).
// Cada um nasce uma vez por chave (`obj`) e fica escondido nos quadros em que a cena não o pede (`esconderExtras`).
// Unidades em metros, como o carro (5,6 m). A aparência é fixada na criação: aparência diferente = chave diferente.
import * as THREE from "three";
import type { Mundo } from "./mundo";
import PAISES from "./paises.json";

const REG = new WeakMap<Mundo, Map<string, THREE.Object3D>>();

/** Objeto da cena com essa chave (criado na primeira vez) e visível neste quadro. */
export function obj<T extends THREE.Object3D>(w: Mundo, chave: string, criar: () => T): T {
  let m = REG.get(w);
  if (!m) REG.set(w, (m = new Map()));
  let o = m.get(chave) as T | undefined;
  if (!o) {
    o = criar();
    o.traverse((x) => {
      if ((x as THREE.Mesh).isMesh) x.castShadow = x.receiveShadow = true;
    });
    w.cena.add(o);
    m.set(chave, o);
  }
  o.visible = true;
  return o;
}

export function esconderExtras(w: Mundo) {
  REG.get(w)?.forEach((o) => (o.visible = false));
}

const mat = (cor: string, rough = 0.55, metal = 0) => new THREE.MeshStandardMaterial({ color: cor, roughness: rough, metalness: metal });
const malha = (g: THREE.BufferGeometry, m: THREE.Material, x = 0, y = 0, z = 0) => {
  const o = new THREE.Mesh(g, m);
  o.position.set(x, y, z);
  return o;
};

/** Textura de texto (rótulo, número). */
export function texturaTexto(texto: string, cor = "#ffffff", fundo = "", larg = 512, alt = 256, peso = 800): THREE.CanvasTexture {
  const cv = document.createElement("canvas");
  cv.width = larg;
  cv.height = alt;
  const g = cv.getContext("2d")!;
  if (fundo) {
    g.fillStyle = fundo;
    g.beginPath();
    g.roundRect(4, 4, larg - 8, alt - 8, alt * 0.2);
    g.fill();
  }
  let tam = alt * 0.62;
  g.font = `${peso} ${tam}px 'Segoe UI', 'Inter', sans-serif`;
  while (g.measureText(texto).width > larg * 0.86 && tam > 10) {
    tam -= 4;
    g.font = `${peso} ${tam}px 'Segoe UI', 'Inter', sans-serif`;
  }
  g.fillStyle = cor;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(texto, larg / 2, alt / 2 + tam * 0.04);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** Rótulo que sempre olha para a câmera. `altura` em metros. */
export function rotulo(texto: string, o: { cor?: string; fundo?: string; altura?: number } = {}): THREE.Sprite {
  const larg = Math.max(256, Math.min(1024, 120 + texto.length * 70));
  const t = texturaTexto(texto, o.cor ?? "#ffffff", o.fundo ?? "rgba(12,14,20,0.82)", larg, 192);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  const h = o.altura ?? 0.6;
  s.scale.set((h * larg) / 192, h, 1);
  s.renderOrder = 10;
  return s;
}

// ------------------------------------------------------------------------------------------------ piloto
export const PELES: Record<string, string> = { clara: "#e9c19d", media: "#c48a60", morena: "#93603d", negra: "#4d3121" };
export const CABELOS: Record<string, string> = { castanho: "#3b2719", preto: "#17120e", loiro: "#b2884d", ruivo: "#86391b", grisalho: "#8e8b87" };

/** Cores de equipe conferidas (fonte e data no comentário). Equipe que não está aqui: passe as cores, depois de conferir. */
export const EQUIPES_PILOTO: Record<string, { macacao: string; detalhe: string; faixa: string; bone: string; logo: string; capacete: string }> = {
  // Mercedes 2025-2026: macacão preto com detalhes prata e verde Petronas; boné preto (formula1.com, planetf1.com, nov/2026)
  mercedes: { macacao: "#15161a", detalhe: "#c3c8cf", faixa: "#00a19b", bone: "#15161a", logo: "#d6dae0", capacete: "#e9ebee" },
};

export type OpcoesPiloto = {
  equipe?: string; macacao?: string; detalhe?: string; faixa?: string; bone?: string; logo?: string; capacete?: string;
  pele?: string; cabelo?: string; traje?: "capacete" | "bone"; crianca?: boolean; sentado?: boolean;
};

const tecido = (cor: string) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.9, metalness: 0 });

/** Piloto: uma pessoa (pele, cabelo, nariz e orelhas, sem olhos nem boca) vestindo macacão de corrida com faixas e
 *  emblemas, botas e luvas. traje "capacete" (no carro) ou "bone" (pódio, entrevista, box). Cores pela `equipe`
 *  (EQUIPES_PILOTO) ou uma a uma. Pés em y = 0, de frente para +z. Braços: `bracos(p, esq, dir)`. */
export function criarPiloto(o: OpcoesPiloto = {}): THREE.Group {
  const eq = EQUIPES_PILOTO[o.equipe ?? ""] ?? EQUIPES_PILOTO.mercedes;
  const cor = o.macacao ?? eq.macacao;
  const detalhe = o.detalhe ?? eq.detalhe;
  const faixa = o.faixa ?? eq.faixa;
  const pele = mat(PELES[o.pele ?? "clara"] ?? o.pele ?? PELES.clara, 0.78);
  const cabelo = tecido(CABELOS[o.cabelo ?? "castanho"] ?? o.cabelo ?? CABELOS.castanho);
  const capacete = o.traje !== "bone";
  const mTerno = tecido(cor);
  const mFaixa = tecido(faixa);
  const mDetalhe = tecido(detalhe);
  const mBota = mat("#121315", 0.6);
  const mMao = capacete ? mat("#1c1e22", 0.85) : pele;
  const g = new THREE.Group();
  const corpo = new THREE.Group();
  g.add(corpo);

  // tronco (perfil humano: quadril, cintura, peito, ombros), zíper, cinto, emblemas
  const perfil = [[0, 0.88], [0.15, 0.89], [0.163, 0.96], [0.148, 1.05], [0.152, 1.14], [0.18, 1.27], [0.186, 1.35], [0.16, 1.43], [0.09, 1.48], [0.062, 1.5], [0, 1.5]];
  const tronco = new THREE.Mesh(new THREE.LatheGeometry(perfil.map(([r, y]) => new THREE.Vector2(r, y)), 32), mTerno);
  tronco.scale.z = 0.66;
  corpo.add(tronco);
  corpo.add(malha(new THREE.CylinderGeometry(0.06, 0.07, 0.045, 20), mTerno, 0, 1.505, 0));
  corpo.add(malha(new THREE.CylinderGeometry(0.0605, 0.0605, 0.01, 20), mFaixa, 0, 1.526, 0));
  corpo.add(malha(new THREE.BoxGeometry(0.008, 0.42, 0.006), mat("#0c0c0e", 0.5), 0, 1.24, -0.124));
  const cinto = malha(new THREE.TorusGeometry(0.152, 0.014, 6, 32), mFaixa, 0, 1.03, 0);
  cinto.rotation.x = Math.PI / 2;
  cinto.scale.y = 0.66;
  corpo.add(cinto);
  corpo.add(malha(new THREE.BoxGeometry(0.075, 0.04, 0.006), mDetalhe, 0.08, 1.3, -0.12));
  const selo = malha(new THREE.CylinderGeometry(0.025, 0.025, 0.006, 20), mDetalhe, -0.08, 1.31, -0.119);
  selo.rotation.x = Math.PI / 2;
  corpo.add(selo);
  for (const lado of [-1, 1]) {
    // faixa lateral do tronco (do sovaco ao quadril)
    const lat = malha(new THREE.BoxGeometry(0.02, 0.36, 0.05), mFaixa, lado * 0.162, 1.12, 0);
    lat.rotation.z = lado * -0.05;
    corpo.add(lat);
  }

  // pernas: quadril → joelho → bota
  for (const lado of [-1, 1]) {
    const quadril = new THREE.Group();
    quadril.position.set(lado * 0.088, 0.92, 0);
    quadril.add(malha(new THREE.CapsuleGeometry(0.08, 0.34, 6, 14), mTerno, 0, -0.2, 0));
    quadril.add(malha(new THREE.BoxGeometry(0.012, 0.34, 0.05), mFaixa, lado * 0.078, -0.2, 0));
    const joelho = new THREE.Group();
    joelho.position.y = -0.43;
    joelho.add(malha(new THREE.CapsuleGeometry(0.064, 0.34, 6, 14), mTerno, 0, -0.2, 0));
    joelho.add(malha(new THREE.BoxGeometry(0.012, 0.3, 0.045), mFaixa, lado * 0.062, -0.18, 0));
    joelho.add(malha(new THREE.BoxGeometry(0.1, 0.09, 0.24), mBota, 0, -0.43, -0.045));
    joelho.add(malha(new THREE.BoxGeometry(0.104, 0.02, 0.25), mat("#e7e7e7", 0.7), 0, -0.47, -0.045));
    quadril.add(joelho);
    if (o.sentado) {
      quadril.rotation.x = Math.PI / 2 - 0.1;
      joelho.rotation.x = -0.25;
    }
    corpo.add(quadril);
  }

  // braços: ombro → cotovelo → mão (luva no carro, mão de fora)
  const bracos: THREE.Group[] = [];
  const cotovelos: THREE.Group[] = [];
  for (const lado of [-1, 1]) {
    const ombro = new THREE.Group();
    ombro.position.set(lado * 0.2, 1.41, 0);
    ombro.add(malha(new THREE.SphereGeometry(0.07, 16, 12), mTerno));
    ombro.add(malha(new THREE.CapsuleGeometry(0.056, 0.22, 6, 12), mTerno, 0, -0.14, 0));
    ombro.add(malha(new THREE.BoxGeometry(0.012, 0.2, 0.04), mDetalhe, lado * 0.055, -0.13, 0));
    const cotovelo = new THREE.Group();
    cotovelo.position.y = -0.29;
    cotovelo.add(malha(new THREE.CapsuleGeometry(0.049, 0.2, 6, 12), mTerno, 0, -0.12, 0));
    cotovelo.add(malha(new THREE.CylinderGeometry(0.052, 0.052, 0.03, 14), mFaixa, 0, -0.235, 0));
    const mao = malha(new THREE.SphereGeometry(0.048, 14, 10), mMao, 0, -0.3, 0);
    mao.scale.set(0.8, 1.25, 0.62);
    cotovelo.add(mao);
    ombro.add(cotovelo);
    ombro.rotation.z = lado * 0.1;
    corpo.add(ombro);
    bracos.push(ombro);
    cotovelos.push(cotovelo);
  }

  // pescoço e cabeça: crânio, queixo, nariz, orelhas, cabelo
  corpo.add(malha(new THREE.CylinderGeometry(0.047, 0.052, 0.1, 14), pele, 0, 1.56, 0));
  const cabeca = new THREE.Group();
  cabeca.position.set(0, 1.68, 0);
  const cranio = malha(new THREE.SphereGeometry(0.104, 28, 20), pele);
  cranio.scale.set(0.88, 1.14, 0.98);
  cabeca.add(cranio);
  const nariz = malha(new THREE.SphereGeometry(0.017, 10, 8), pele, 0, -0.008, -0.103);
  nariz.scale.set(0.9, 1.3, 1);
  cabeca.add(nariz);
  for (const lado of [-1, 1]) {
    const orelha = malha(new THREE.SphereGeometry(0.022, 10, 8), pele, lado * 0.093, -0.005, 0.005);
    orelha.scale.set(0.5, 1, 0.8);
    cabeca.add(orelha);
  }
  if (!capacete) {
    // cabelo: topo, lados e nuca (a testa fica livre)
    const cab = malha(new THREE.SphereGeometry(0.109, 28, 16, Math.PI * 1.78, Math.PI * 1.44, 0, Math.PI * 0.6), cabelo, 0, 0.008, 0.004);
    cab.scale.set(0.92, 1.06, 1.02);
    cabeca.add(cab);
    const franja = malha(new THREE.SphereGeometry(0.109, 20, 8, Math.PI * 1.2, Math.PI * 0.6, 0, Math.PI * 0.2), cabelo, 0, 0.008, 0.004);
    franja.scale.set(0.92, 1.06, 1.02);
    cabeca.add(franja);
    // boné: copa sobre o topo, emblema, botão e aba curta só na frente
    const mBone = tecido(o.bone ?? eq.bone);
    const copa = malha(new THREE.SphereGeometry(0.113, 28, 14, 0, Math.PI * 2, 0, Math.PI * 0.46), mBone, 0, 0.022, 0);
    copa.scale.set(0.95, 0.84, 1.03);
    cabeca.add(copa);
    cabeca.add(malha(new THREE.SphereGeometry(0.011, 8, 6), mBone, 0, 0.118, 0));
    const emblema = malha(new THREE.CircleGeometry(0.022, 20), mat(o.logo ?? eq.logo, 0.4, 0.5), 0, 0.075, -0.093);
    emblema.rotation.x = -0.55;
    emblema.rotation.y = Math.PI;
    cabeca.add(emblema);
    const d = new THREE.Shape();
    d.moveTo(-0.088, 0);
    d.quadraticCurveTo(-0.09, 0.075, 0, 0.082);
    d.quadraticCurveTo(0.09, 0.075, 0.088, 0);
    d.lineTo(-0.088, 0);
    const aba = new THREE.Mesh(new THREE.ExtrudeGeometry(d, { depth: 0.008, bevelEnabled: false, curveSegments: 16 }), mBone);
    aba.rotation.x = -Math.PI / 2 - 0.2;
    aba.position.set(0, 0.03, -0.088);
    cabeca.add(aba);
  } else {
    const mCasco = mat(o.capacete ?? eq.capacete, 0.22, 0.05);
    const casco = malha(new THREE.SphereGeometry(0.145, 28, 20), mCasco, 0, 0.005, 0.004);
    casco.scale.set(0.98, 1.05, 1.12);
    cabeca.add(casco);
    const listra = malha(new THREE.SphereGeometry(0.1465, 28, 6, 0, Math.PI * 2, Math.PI * 0.3, Math.PI * 0.08), mFaixa, 0, 0.005, 0.004);
    listra.scale.copy(casco.scale);
    cabeca.add(listra);
    const viseira = malha(new THREE.SphereGeometry(0.148, 28, 12, Math.PI * 1.15, Math.PI * 0.7, Math.PI * 0.4, Math.PI * 0.17), mat("#0a0c10", 0.06, 0.7), 0, 0.005, 0.004);
    viseira.scale.copy(casco.scale);
    cabeca.add(viseira);
  }
  corpo.add(cabeca);
  corpo.rotation.y = Math.PI; // modelado olhando para -z; de pé, fica de frente para +z
  g.userData = { bracos, cotovelos, corpo };
  if (o.crianca) g.scale.setScalar(0.72);
  return g;
}

/** Braços do piloto: 0 = ao lado do corpo, 1 = erguido (comemoração = bracos(p, 1, 1)). */
export function bracos(p: THREE.Object3D, esq = 0, dir = 0) {
  const [e, d] = (p.userData.bracos ?? []) as THREE.Group[];
  const [ce, cd] = (p.userData.cotovelos ?? []) as THREE.Group[];
  if (e) e.rotation.z = -0.1 - esq * 2.55;
  if (d) d.rotation.z = 0.1 + dir * 2.55;
  if (ce) ce.rotation.z = esq * 0.35;
  if (cd) cd.rotation.z = -dir * 0.35;
}
// ------------------------------------------------------------------------------------------------ kart
/** Kart de competição (1,8 m), frente para -z. Com `piloto`, vem com um piloto criança sentado de capacete. */
export function criarKart(o: { cor?: string; faixa?: string; numero?: string; piloto?: OpcoesPiloto | false } = {}): THREE.Group {
  const cor = o.cor ?? "#ffd21f";
  const g = new THREE.Group();
  const tubo = mat("#c8ccd2", 0.35, 0.8);
  const borracha = mat("#17181b", 0.85);
  for (const lado of [-1, 1]) g.add(malha(new THREE.BoxGeometry(0.04, 0.04, 1.5), tubo, lado * 0.28, 0.08, 0));
  g.add(malha(new THREE.BoxGeometry(0.6, 0.03, 0.05), tubo, 0, 0.08, -0.5));
  g.add(malha(new THREE.BoxGeometry(0.6, 0.03, 0.05), tubo, 0, 0.08, 0.5));
  const roda = (x: number, z: number, r: number, l: number) => {
    const p = malha(new THREE.CylinderGeometry(r, r, l, 24), borracha, x, r, z);
    p.rotation.z = Math.PI / 2;
    g.add(p);
    const aro = malha(new THREE.CylinderGeometry(r * 0.6, r * 0.6, l + 0.004, 20), mat("#d9dde3", 0.3, 0.7), x, r, z);
    aro.rotation.z = Math.PI / 2;
    g.add(aro);
  };
  roda(-0.5, -0.55, 0.13, 0.12);
  roda(0.5, -0.55, 0.13, 0.12);
  roda(-0.56, 0.58, 0.14, 0.2);
  roda(0.56, 0.58, 0.14, 0.2);
  const carenagem = mat(cor, 0.35);
  const bico = malha(new THREE.BoxGeometry(0.62, 0.16, 0.34), carenagem, 0, 0.16, -0.86);
  bico.rotation.x = -0.25;
  g.add(bico);
  g.add(malha(new THREE.BoxGeometry(0.3, 0.2, 0.3), carenagem, 0, 0.2, -0.6));
  for (const lado of [-1, 1]) g.add(malha(new THREE.BoxGeometry(0.16, 0.12, 0.62), carenagem, lado * 0.44, 0.17, 0.02));
  g.add(malha(new THREE.BoxGeometry(0.9, 0.08, 0.1), mat(o.faixa ?? "#17181b", 0.5), 0, 0.15, 0.82));
  g.add(malha(new THREE.BoxGeometry(0.34, 0.3, 0.3), mat("#202227", 0.8), 0, 0.26, 0.12));
  g.add(malha(new THREE.BoxGeometry(0.2, 0.2, 0.22), mat("#7b8088", 0.5, 0.6), 0.3, 0.22, 0.42));
  const volante = malha(new THREE.TorusGeometry(0.12, 0.016, 8, 24), mat("#111", 0.6), 0, 0.42, -0.32);
  volante.rotation.x = -1.05;
  g.add(volante);
  if (o.numero) {
    const placa = malha(new THREE.PlaneGeometry(0.34, 0.2), new THREE.MeshStandardMaterial({ map: texturaTexto(o.numero, "#111", "#f4f4f4", 256, 160), roughness: 0.5 }), 0, 0.24, -1.02);
    placa.rotation.y = Math.PI;
    placa.rotation.x = 0.25;
    g.add(placa);
  }
  if (o.piloto !== false) {
    const p = criarPiloto({ ...(o.piloto || {}), traje: "capacete", crianca: true, sentado: true });
    p.position.set(0, -0.46, 0.14);
    p.userData.corpo.rotation.y = 0; // no kart, olha para a frente do kart (-z)
    bracos(p, 0.08, 0.08);
    (p.userData.bracos as THREE.Group[]).forEach((b) => (b.rotation.x = 1.05));
    g.add(p);
  }
  return g;
}

// ------------------------------------------------------------------------------------------------ pódio
/** Pódio de 3 degraus (2º à esquerda, 1º no meio, 3º à direita, vistos de +z), com os números na frente (+z). `topo(n)` = onde fica o pé. */
export function criarPodio(o: { cor?: string; numeros?: string; largura?: number } = {}): THREE.Group {
  const g = new THREE.Group();
  const L = o.largura ?? 1.6;
  const alturas = [0.95, 1.35, 0.7];
  const xs = [-L, 0, L];
  const tops: THREE.Vector3[] = [];
  ["2", "1", "3"].forEach((n, i) => {
    const h = alturas[i];
    g.add(malha(new THREE.BoxGeometry(L, h, 1.2), mat(o.cor ?? "#eef0f3", 0.45), xs[i], h / 2, 0));
    g.add(malha(new THREE.BoxGeometry(L + 0.02, 0.06, 1.22), mat(n === "1" ? "#d9a520" : n === "2" ? "#aeb4bd" : "#b06a35", 0.35, 0.5), xs[i], h - 0.03, 0));
    const num = malha(new THREE.PlaneGeometry(0.7, 0.7), new THREE.MeshStandardMaterial({ map: texturaTexto(n, o.numeros ?? "#14161c", "", 256, 256), transparent: true }), xs[i], h * 0.48, 0.605);
    g.add(num);
    tops.push(new THREE.Vector3(xs[i], h, 0));
  });
  g.userData = { topos: tops };
  return g;
}

/** Ponto em cima do degrau (1, 2 ou 3) do pódio, em coordenadas do mundo. */
export function topoDoPodio(podio: THREE.Object3D, lugar: 1 | 2 | 3): THREE.Vector3 {
  const t = (podio.userData.topos as THREE.Vector3[])[lugar === 1 ? 1 : lugar === 2 ? 0 : 2];
  return podio.localToWorld(t.clone());
}

// ------------------------------------------------------------------------------------------------ escada de categorias
/** Escada subindo para a direita, um degrau por item ("F4", "REGIONAL", "F3", "F2", "F1"). `pulados` = índices
 *  que ficam cinza e vazados (etapa não disputada). `degrau(i)` = ponto em cima do degrau i. */
export function criarEscada(itens: string[], o: { cor?: string; pulados?: number[]; passo?: number; alturaDegrau?: number } = {}): THREE.Group {
  const g = new THREE.Group();
  const passo = o.passo ?? 2.6;
  const h0 = o.alturaDegrau ?? 0.7;
  const tops: THREE.Vector3[] = [];
  itens.forEach((nome, i) => {
    const pulado = o.pulados?.includes(i);
    const h = h0 * (i + 1);
    const x = (i - (itens.length - 1) / 2) * passo;
    const m = pulado ? new THREE.MeshStandardMaterial({ color: "#59606b", roughness: 0.8, transparent: true, opacity: 0.35 }) : mat(o.cor ?? "#e9ecf1", 0.5);
    g.add(malha(new THREE.BoxGeometry(passo * 0.96, h, 2), m, x, h / 2, 0));
    const r = rotulo(nome, { altura: 0.62, cor: pulado ? "#9aa1ad" : "#ffffff" });
    r.position.set(x, h + 0.7, 0);
    g.add(r);
    tops.push(new THREE.Vector3(x, h, 0));
  });
  g.userData = { topos: tops };
  return g;
}

export function degrau(escada: THREE.Object3D, i: number): THREE.Vector3 {
  const tops = escada.userData.topos as THREE.Vector3[];
  return escada.localToWorld(tops[Math.max(0, Math.min(tops.length - 1, i))].clone());
}

// ------------------------------------------------------------------------------------------------ mapa
type Pais = { nome: string; aneis: [number, number][][] };
const BASE = PAISES as unknown as Record<string, Pais>;

export type Mapa = THREE.Group & { userData: { ponto: (lat: number, lon: number) => THREE.Vector3 } };

/** Mapa geograficamente correto (Natural Earth 1:50m, domínio público) de um país pelo código ISO de 3 letras
 *  ("ITA", "BRA", "MEX", "GBR"…). Deitado no chão, norte para -z, maior lado = `tamanho` metros, centro na origem.
 *  `ponto(lat, lon)` (via `pontoNoMapa`) dá a posição de uma cidade em cima do mapa. Vizinhos aparecem mais claros. */
export function criarMapa(iso: string, o: { tamanho?: number; cor?: string; vizinhos?: boolean; corVizinhos?: string; mar?: string } = {}): Mapa {
  const pais = BASE[iso.toUpperCase()];
  if (!pais) throw new Error(`país desconhecido: ${iso}`);
  const area = (a: [number, number][]) => a.reduce((s, [x, y], i) => { const [x2, y2] = a[(i + 1) % a.length]; return s + x * y2 - x2 * y; }, 0) / 2;
  const principal = [...pais.aneis].sort((a, b) => Math.abs(area(b)) - Math.abs(area(a)))[0];
  const caixa = (anel: [number, number][]) => {
    const xs = anel.map((p) => p[0]);
    const ys = anel.map((p) => p[1]);
    return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
  };
  // caixa do país = anéis perto do principal (sem territórios do outro lado do mundo)
  const cp = caixa(principal);
  const raio = Math.max(cp.x1 - cp.x0, cp.y1 - cp.y0) * 1.6;
  const cx0 = (cp.x0 + cp.x1) / 2;
  const cy0 = (cp.y0 + cp.y1) / 2;
  const perto = pais.aneis.filter((a) => { const c = caixa(a); return Math.abs((c.x0 + c.x1) / 2 - cx0) < raio && Math.abs((c.y0 + c.y1) / 2 - cy0) < raio; });
  const cx = perto.map(caixa);
  const lon0 = (Math.min(...cx.map((c) => c.x0)) + Math.max(...cx.map((c) => c.x1))) / 2;
  const lat0 = (Math.min(...cx.map((c) => c.y0)) + Math.max(...cx.map((c) => c.y1))) / 2;
  const kx = Math.cos((lat0 * Math.PI) / 180);
  const larg = (Math.max(...cx.map((c) => c.x1)) - Math.min(...cx.map((c) => c.x0))) * kx;
  const alt = Math.max(...cx.map((c) => c.y1)) - Math.min(...cx.map((c) => c.y0));
  const S = (o.tamanho ?? 20) / Math.max(larg, alt);
  const proj = (lon: number, lat: number) => new THREE.Vector2((lon - lon0) * kx * S, (lat - lat0) * S);
  const forma = (anel: [number, number][]) => new THREE.Shape(anel.map(([x, y]) => proj(x, y)));

  const g = new THREE.Group() as Mapa;
  const plano = new THREE.Group();
  plano.rotation.x = -Math.PI / 2;
  g.add(plano);
  const geo = new THREE.ExtrudeGeometry(perto.map(forma), { depth: 0.35, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05, bevelSegments: 2 });
  plano.add(new THREE.Mesh(geo, mat(o.cor ?? "#3fae6a", 0.6)));
  if (o.vizinhos !== false) {
    const lim = { x0: lon0 - (raio * 1.4) / kx, x1: lon0 + (raio * 1.4) / kx, y0: lat0 - raio * 1.4, y1: lat0 + raio * 1.4 };
    const formas: THREE.Shape[] = [];
    for (const [cod, p] of Object.entries(BASE)) {
      if (cod === iso.toUpperCase()) continue;
      for (const a of p.aneis) {
        const c = caixa(a);
        if (c.x1 < lim.x0 || c.x0 > lim.x1 || c.y1 < lim.y0 || c.y0 > lim.y1) continue;
        formas.push(forma(a));
      }
    }
    if (formas.length) plano.add(new THREE.Mesh(new THREE.ExtrudeGeometry(formas, { depth: 0.08, bevelEnabled: false }), mat(o.corVizinhos ?? "#c9cdc4", 0.8)));
  }
  const mar = malha(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ color: o.mar ?? "#8cc6ea", roughness: 1, emissive: o.mar ?? "#8cc6ea", emissiveIntensity: 0.45 }), 0, -0.02, 0);
  mar.rotation.x = -Math.PI / 2;
  g.add(mar);
  g.userData = { ponto: (lat: number, lon: number) => { const p = proj(lon, lat); return new THREE.Vector3(p.x, 0.45, -p.y); } };
  return g;
}

/** Posição (no mundo) de uma latitude/longitude em cima do mapa. */
export function pontoNoMapa(mapa: THREE.Object3D, lat: number, lon: number): THREE.Vector3 {
  return mapa.localToWorld((mapa as Mapa).userData.ponto(lat, lon));
}

/** Alfinete com rótulo (cidade, circuito). Ponta em y = 0; coloque-o com `.position.copy(pontoNoMapa(...))`. */
export function criarAlfinete(nome: string, cor = "#e8312f"): THREE.Group {
  const g = new THREE.Group();
  const m = mat(cor, 0.35);
  const cone = malha(new THREE.ConeGeometry(0.16, 0.7, 20), m, 0, 0.35, 0);
  cone.rotation.x = Math.PI;
  g.add(cone);
  g.add(malha(new THREE.SphereGeometry(0.3, 24, 16), m, 0, 0.85, 0));
  if (nome) {
    const r = rotulo(nome, { altura: 0.75 });
    r.position.set(0, 1.75, 0);
    g.add(r);
  }
  return g;
}

// ------------------------------------------------------------------------------------------------ número no carro
/** Número do piloto no bico e nas laterais da tampa do motor do carro `k` (w.carros[k]). */
export function numeroNoCarro(w: Mundo, k: number, numero: string, cor = "#ffffff") {
  const car = w.carros[k];
  const chave = `numero:${numero}`;
  if (car.getObjectByName(chave)) return;
  const m = new THREE.MeshBasicMaterial({ map: texturaTexto(numero, cor, "", 256, 256), transparent: true, depthWrite: false });
  const g = new THREE.Group();
  g.name = chave;
  const bico = malha(new THREE.PlaneGeometry(0.3, 0.3), m, 0, 0.42, -1.85);
  bico.rotation.x = -Math.PI / 2 + 0.22;
  bico.rotation.z = Math.PI;
  g.add(bico);
  for (const lado of [-1, 1]) {
    const p = malha(new THREE.PlaneGeometry(0.26, 0.26), m, lado * 0.155, 0.8, 0.45);
    p.rotation.y = (lado * Math.PI) / 2;
    g.add(p);
  }
  car.add(g);
}
