// Geografia real: o Brasil com os estados (IBGE) e uma cidade destacada, e circuitos com o traçado de verdade
// (bacinger/f1-circuits, MIT). Dados em ./geo/*.json. Circuito em METROS reais: o carro (5,4 m) anda nele em escala.
import * as THREE from "three";
import BRASIL from "./geo/brasil.json";
import CIRCUITOS from "./geo/circuitos.json";
import LASVEGAS from "./geo/lasvegas.json";
import PAISES from "./paises.json";
import { carro, type Pintura } from "./Carro3D";
import { vestirCircuito, type Cenario, type CidadeReal } from "./cenario";
import { aoRestaurar } from "./desmonte";
import { obj, rotulo } from "./extras";
import { estercar, rolarRodas } from "./efeitos3d";
import { afastarNevoa, camera, poe, type Mundo } from "./mundo";

type Anel = [number, number][];
const mat = (cor: string, rough = 0.6, extra: THREE.MeshStandardMaterialParameters = {}) =>
  new THREE.MeshStandardMaterial({ color: cor, roughness: rough, ...extra });

// ------------------------------------------------------------------------------------------------ mapa do Brasil
const NOME_UF: Record<string, string> = { "35": "SÃO PAULO", "33": "RIO DE JANEIRO", "31": "MINAS GERAIS", "41": "PARANÁ" };
const CIDADES: Record<string, { nome: string }> = { "3550308": { nome: "SÃO PAULO" } };

export type MapaBrasil = THREE.Group & {
  userData: { ponto: (lat: number, lon: number) => THREE.Vector3; areas: Record<string, { centro: THREE.Vector3; tamanho: number }> };
};

/** Brasil com os 27 estados (IBGE), o `estado` destacado (código do IBGE: "35" = SP) e a `cidade` destacada por cima
 *  ("3550308" = São Paulo). Deitado no chão, norte para -z, maior lado = `tamanho` metros. `areaNoMapa(mapa, "estado" |
 *  "cidade" | "pais")` dá o centro e o tamanho de cada área, para a câmera chegar até ela. */
export function criarMapaBrasil(o: { tamanho?: number; estado?: string; cidade?: string; cor?: string; corEstado?: string; corCidade?: string } = {}): MapaBrasil {
  const ufs = (BRASIL as unknown as { uf: Record<string, Anel[]> }).uf;
  const muni = (BRASIL as unknown as { municipio: Record<string, Anel[]> }).municipio;
  const todos = Object.values(ufs).flat();
  const xs = todos.flat().map((p) => p[0]);
  const ys = todos.flat().map((p) => p[1]);
  const lon0 = (Math.min(...xs) + Math.max(...xs)) / 2;
  const lat0 = (Math.min(...ys) + Math.max(...ys)) / 2;
  const kx = Math.cos((lat0 * Math.PI) / 180);
  const S = (o.tamanho ?? 20) / Math.max((Math.max(...xs) - Math.min(...xs)) * kx, Math.max(...ys) - Math.min(...ys));
  const proj = (lon: number, lat: number) => new THREE.Vector2((lon - lon0) * kx * S, (lat - lat0) * S);
  const forma = (a: Anel) => new THREE.Shape(a.map(([x, y]) => proj(x, y)));
  const g = new THREE.Group() as MapaBrasil;
  const plano = new THREE.Group();
  plano.rotation.x = -Math.PI / 2; // forma em x/y → chão em x/-z (norte para -z)
  g.add(plano);
  const contorno = (a: Anel, cor: string, z: number) => {
    const l = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(a.map(([x, y]) => { const p = proj(x, y); return new THREE.Vector3(p.x, p.y, z); })),
      new THREE.LineBasicMaterial({ color: cor }));
    plano.add(l);
  };
  const destaque = o.estado ?? "35";
  for (const [cod, aneis] of Object.entries(ufs)) {
    const eh = cod === destaque;
    const prof = eh ? 0.55 : 0.3;
    plano.add(new THREE.Mesh(new THREE.ExtrudeGeometry(aneis.map(forma), { depth: prof, bevelEnabled: false }), mat(eh ? (o.corEstado ?? "#2ec4b6") : (o.cor ?? "#3d7a5a"), 0.65)));
    for (const a of aneis) contorno(a, eh ? "#ffffff" : "#a8c9b4", prof + 0.002);
  }
  // cidade em cima do estado, mais alta e em amarelo
  const areas: MapaBrasil["userData"]["areas"] = {};
  const caixa = (aneis: Anel[]) => {
    const p = aneis.flat().map(([x, y]) => proj(x, y));
    const x0 = Math.min(...p.map((v) => v.x)), x1 = Math.max(...p.map((v) => v.x)), y0 = Math.min(...p.map((v) => v.y)), y1 = Math.max(...p.map((v) => v.y));
    return { centro: new THREE.Vector3((x0 + x1) / 2, 0.6, -(y0 + y1) / 2), tamanho: Math.max(x1 - x0, y1 - y0) };
  };
  areas.pais = caixa(todos);
  areas.estado = caixa(ufs[destaque] ?? todos);
  const cod = o.cidade ?? "3550308";
  if (muni[cod]) {
    // fina, em cima do estado (o estado tem 0,55 de altura): uma camada amarela, não uma torre
    const cid = new THREE.Mesh(new THREE.ExtrudeGeometry(muni[cod].map(forma), { depth: 0.03, bevelEnabled: false }), mat(o.corCidade ?? "#ffc93a", 0.45, { emissive: "#ffc93a", emissiveIntensity: 0.35 }));
    cid.position.z = 0.552;
    plano.add(cid);
    for (const a of muni[cod]) contorno(a, "#ffffff", 0.585);
    areas.cidade = caixa(muni[cod]);
  }
  // países vizinhos (Natural Earth) mais claros e o mar
  const base = PAISES as unknown as Record<string, { aneis: Anel[] }>;
  const viz: THREE.Shape[] = [];
  for (const [iso, p] of Object.entries(base)) {
    if (iso === "BRA") continue;
    for (const a of p.aneis) {
      const c = a[0];
      if (Math.abs(c[0] - lon0) < 30 && Math.abs(c[1] - lat0) < 30) viz.push(forma(a));
    }
  }
  if (viz.length) plano.add(new THREE.Mesh(new THREE.ExtrudeGeometry(viz, { depth: 0.08, bevelEnabled: false }), mat("#c9cdc4", 0.85)));
  const mar = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), mat("#8cc6ea", 1, { emissive: "#8cc6ea", emissiveIntensity: 0.45 }));
  mar.rotation.x = -Math.PI / 2;
  mar.position.y = -0.02;
  mar.userData.foraDoEnquadro = true;
  g.add(mar);
  if (NOME_UF[destaque]) areas.estado.centro.y = 0.6;
  g.userData = { ponto: (lat: number, lon: number) => { const p = proj(lon, lat); return new THREE.Vector3(p.x, 0.6, -p.y); }, areas };
  void CIDADES;
  return g;
}

/** Centro (no mundo) e tamanho (metros) de uma área do mapa do Brasil: "pais", "estado" ou "cidade". */
export function areaNoMapa(mapa: THREE.Object3D, area: "pais" | "estado" | "cidade") {
  mapa.updateMatrixWorld(true);
  const a = (mapa as MapaBrasil).userData.areas[area] ?? (mapa as MapaBrasil).userData.areas.pais;
  return { centro: mapa.localToWorld(a.centro.clone()), tamanho: a.tamanho * mapa.scale.x };
}

// ------------------------------------------------------------------------------------------------ circuito real
type InfoCircuito = { pontos: THREE.Vector3[]; comprimento: number; curvatura: number[]; pista: THREE.Mesh; escape: THREE.Mesh; total: number; faixas: THREE.Mesh[] };

// Onde fica cada coisa no circuito (f = fração da volta; dist positiva = à direita do sentido da corrida, que em Interlagos,
// anti-horário, é por fora). Boxes à esquerda da reta (por dentro), como na pista real.
const CENARIOS: Record<string, Cenario> = {
  interlagos: {
    arquibancadas: [
      { f0: 0.945, f1: 1.04, coberta: true, dist: 62 }, { f0: 1.045, f1: 1.1, dist: 86 }, { f0: 0.118, f1: 0.17, dist: 88 },
      { f0: 0.18, f1: 0.3, dist: 56 }, { f0: 0.315, f1: 0.365, dist: 88 }, { f0: 0.733, f1: 0.757, dist: 92, coberta: true },
      { f0: 0.78, f1: 0.935, dist: 62 },
    ],
    boxes: { f0: 0.983, f1: 1.045, dist: -42 },
    lagos: [{ f: 0.33, dist: 900, r: 420 }, { f: 0.6, dist: -1100, r: 480 }],
  },
  // Las Vegas, anti-horário: esquerda = por dentro (boxes e Grand Prix Plaza à esquerda da reta, pit lane do OSM).
  // Arquibancadas aproximadas (sem planta oficial): reta dos boxes por fora, em volta da Sphere e na Harmon.
  lasvegas: {
    rua: true,
    arquibancadas: [
      { f0: 0.945, f1: 1.02, coberta: true, dist: 44 }, { f0: 0.255, f1: 0.29, dist: -40 }, { f0: 0.3, f1: 0.33, dist: 42 },
      { f0: 0.86, f1: 0.9, dist: 40 }, { f0: 0.53, f1: 0.56, dist: -38 },
    ],
    real: LASVEGAS as unknown as CidadeReal,
  },
};

/** Circuitos de rua: muro colado na pista (sem caixa de brita), escape estreito. */
const DE_RUA = new Set(["lasvegas"]);

/** Nomes reais dos trechos de Interlagos (f = meio do trecho), pela numeração oficial: 1-2 S do Senna, 3 Curva do Sol,
 *  4-5 Descida do Lago, 6-7 Ferradura, 8 Laranjinha, 9 Pinheirinho, 10 Bico de Pato, 11 Mergulho, 12 Junção. */
export const TRECHOS_INTERLAGOS: { texto: string; f: number }[] = [
  { texto: "S DO SENNA", f: 0.09 }, { texto: "CURVA DO SOL", f: 0.146 }, { texto: "RETA OPOSTA", f: 0.24 }, { texto: "DESCIDA DO LAGO", f: 0.34 },
  { texto: "FERRADURA", f: 0.476 }, { texto: "LARANJINHA", f: 0.53 }, { texto: "PINHEIRINHO", f: 0.559 }, { texto: "BICO DE PATO", f: 0.627 },
  { texto: "MERGULHO", f: 0.675 }, { texto: "JUNÇÃO", f: 0.743 }, { texto: "SUBIDA DOS BOXES", f: 0.86 },
];

/** Trechos reais de Las Vegas (f = meio do trecho; ruas conferidas no OpenStreetMap ao longo do traçado): reta dos boxes
 *  (17→1), grampo da 1, Koval Lane (4→5), a volta da Sphere (5-9), Sands Avenue (9→12, curvas 10-11 rápidas), a Strip =
 *  Las Vegas Boulevard (12→14, curva 13 de pé embaixo), 14-16 no Planet Hollywood, Harmon Avenue (16→17). */
export const TRECHOS_LASVEGAS: { texto: string; f: number }[] = [
  { texto: "RETA DOS BOXES", f: 0.005 }, { texto: "CURVA 1", f: 0.044 }, { texto: "KOVAL LANE", f: 0.18 }, { texto: "SPHERE", f: 0.305 },
  { texto: "SANDS AVENUE", f: 0.44 }, { texto: "LAS VEGAS STRIP", f: 0.68 }, { texto: "PLANET HOLLYWOOD", f: 0.843 }, { texto: "HARMON AVENUE", f: 0.91 },
];

export const TRECHOS: Record<string, { texto: string; f: number }[]> = { interlagos: TRECHOS_INTERLAGOS, lasvegas: TRECHOS_LASVEGAS };

/** Marcos reais de Las Vegas (centro do contorno no OpenStreetMap) para câmera e rótulos: sphere, high_roller, eiffel,
 *  plaza (Grand Prix Plaza = prédio dos boxes), fontes (Bellagio), campanile, bellagio, venetian, palazzo, caesars, wynn,
 *  cosmopolitan, planet_hollywood, flamingo, paris, fashion_show, treasure_island, harrahs, linq. */
export function marcoNoCircuito(circ: THREE.Object3D, chave: string, altura = 0) {
  const real = (CENARIOS[circ.userData.nome as string] ?? {}).real;
  const m = real?.marcos[chave];
  if (!m) throw new Error(`marco desconhecido: ${chave}`);
  circ.updateMatrixWorld(true);
  return circ.localToWorld(new THREE.Vector3(m.xn[0], altura, -m.xn[1]));
}

/** Circuito com o traçado real, em metros (Interlagos: 4,309 km), sentido da corrida = sentido dos pontos (f 0 = linha
 *  de chegada, f 1 = volta completa). Asfalto, linhas brancas, zebras nas curvas fortes, linha de chegada quadriculada,
 *  grama em volta. `rotulos`: [{texto, f}] marcando trechos (ex.: S do Senna). */
export function criarCircuito(nome = "interlagos", o: { largura?: number; rotulos?: { texto: string; f: number }[]; cenario?: boolean; noite?: boolean } = {}) {
  const dados = (CIRCUITOS as unknown as Record<string, { pontos: [number, number][]; comprimento: number }>)[nome];
  if (!dados) throw new Error(`circuito desconhecido: ${nome}`);
  const lon0 = dados.pontos.reduce((s, p) => s + p[0], 0) / dados.pontos.length;
  const lat0 = dados.pontos.reduce((s, p) => s + p[1], 0) / dados.pontos.length;
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const brutos = dados.pontos.slice(0, -1).map(([x, y]) => new THREE.Vector3((x - lon0) * kx, 0, -(y - lat0) * 110540));
  const curva = new THREE.CatmullRomCurve3(brutos, true, "centripetal");
  curva.arcLengthDivisions = 16000; // o padrão (200) deixa os pontos irregulares: o carro "pulsava", acelerando e freando
  const N = 1600;
  const pontos = curva.getSpacedPoints(N).slice(0, N);
  const comp = curva.getLength();
  const larg = o.largura ?? (o.cenario ? 16 : 13); // com cenário, um pouco mais larga: de longe a pista ainda se lê
  const g = new THREE.Group();
  // grama (com cenário, o relevo faz esse papel)
  if (!o.cenario) {
    const grama = new THREE.Mesh(new THREE.PlaneGeometry(5000, 5000), mat("#2f6a3c", 1));
    grama.rotation.x = -Math.PI / 2;
    grama.receiveShadow = true;
    grama.userData.foraDoEnquadro = true;
    g.add(grama);
  }
  const faixas: THREE.Mesh[] = [];
  // faixas ao longo do traçado: d0..d1 = distância do centro (negativo = à esquerda), y = altura
  // `camada`: ordem de desenho das faixas sobrepostas (escape < asfalto < zebras/linhas), sem briga de profundidade de longe
  const faixa = (d0: number | ((i: number) => number), d1: number | ((i: number) => number), y: number, cor: (i: number) => THREE.Color | null, camada = 1) => {
    const pos: number[] = [];
    const cores: number[] = [];
    const ind: number[] = [];
    for (let i = 0; i <= N; i++) {
      const a = pontos[i % N];
      const b = pontos[(i + 1) % N];
      const t = b.clone().sub(a).normalize();
      const nx = -t.z, nz = t.x; // normal à esquerda
      const c = cor(i % N);
      if (i === N || !c) continue;
      // 4 vértices por segmento: a cor fica nítida (zebra sem degradê)
      const ta = pontos[(i + 2) % N].clone().sub(b).normalize();
      const v = pos.length / 3;
      for (const [q, ux, uz] of [[a, nx, nz], [b, -ta.z, ta.x]] as [THREE.Vector3, number, number][]) {
        for (const dd of [d0, d1]) {
          const d = typeof dd === "function" ? dd(q === a ? i % N : (i + 1) % N) : dd;
          pos.push(q.x + ux * d, y, q.z + uz * d);
        }
      }
      for (let k = 0; k < 4; k++) cores.push(c.r, c.g, c.b);
      ind.push(v, v + 1, v + 2, v + 1, v + 3, v + 2);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(cores, 3));
    geo.setIndex(ind);
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -camada * 2, polygonOffsetUnits: -camada * 4 }));
    m.receiveShadow = true;
    faixas.push(m);
    return m;
  };
  // curvatura (para zebras e esterço): ângulo entre segmentos por metro
  const passo = comp / N;
  const curvatura = pontos.map((_, i) => {
    const a = pontos[(i - 3 + N) % N], b = pontos[i], c = pontos[(i + 3) % N];
    const t1 = b.clone().sub(a).normalize(), t2 = c.clone().sub(b).normalize();
    const ang = Math.atan2(t1.x * t2.z - t1.z * t2.x, t1.dot(t2)); // positivo = virando à direita (no plano x/z, z para o sul)
    return -ang / (passo * 3);
  });
  const asfalto = new THREE.Color("#4a4f59");
  // área de escape clara em volta do asfalto: deixa o traçado legível visto do alto (a pista sozinha some a 1 km)
  const rua = DE_RUA.has(nome);
  let bordas = { fora: (_: number) => larg, dentro: (_: number) => larg };
  const fatorEscape = rua && o.cenario ? 0.62 : o.cenario ? 0.95 : 1.6;
  const escape = faixa(-larg * fatorEscape, larg * fatorEscape, 0.012, () => new THREE.Color(rua && o.cenario ? (o.noite ? "#3b3f48" : "#b3b6bb") : o.cenario ? "#9aa0a6" : "#c9ccd2"), 1);
  if (o.cenario && rua) {
    // rua: muro de concreto logo depois do escape estreito (o muro fica a bordas + 3 m do centro)
    bordas = { fora: () => larg * fatorEscape - 3 + 0.6, dentro: () => larg * fatorEscape - 3 + 0.6 };
  } else if (o.cenario) {
    // areia e terra por fora das curvas: a largura segue a curvatura suavizada, como nas fotos aéreas
    const K = 36;
    const suavizada = curvatura.map((_, i) => {
      let s = 0;
      for (let d = -K; d <= K; d++) s += curvatura[(i + d + N) % N];
      return s / (2 * K + 1);
    });
    const largura = (i: number, sinal: number) => {
      const c = suavizada[i] * sinal;
      return c > 0 ? Math.min(62, larg + c * 4200) : larg;
    };
    const areia = new THREE.Color("#d8bd8a"), terra = new THREE.Color("#a98559");
    // vira à esquerda (curvatura positiva) = o lado de fora é a direita = distância positiva
    const fora = (i: number) => largura(i, 1), dentro = (i: number) => largura(i, -1);
    bordas = { fora, dentro };
    g.add(faixa(larg * 0.9, fora, 0.006, () => areia, 0.5), faixa((i) => -dentro(i), -larg * 0.9, 0.006, () => areia, 0.5));
    g.add(faixa(larg * 0.9, (i) => fora(i) * 0.72, 0.009, (i) => (fora(i) > larg * 2 ? terra : null), 0.7),
      faixa((i) => -dentro(i) * 0.72, -larg * 0.9, 0.009, (i) => (dentro(i) > larg * 2 ? terra : null), 0.7));
  }
  if (rua && o.cenario && o.noite) {
    // à noite a rua iluminada desenha o traçado: a faixa junto ao muro acende como a luz dos postes
    const m = escape.material as THREE.MeshStandardMaterial;
    m.emissive.set("#ffcf8a");
    m.emissiveIntensity = 0.75;
  }
  g.add(escape);
  const pista = faixa(-larg / 2, larg / 2, 0.02, () => asfalto, 2);
  g.add(pista);
  const branco = new THREE.Color("#f2f2f2");
  g.add(faixa(-larg / 2, -larg / 2 + 0.35, 0.03, () => branco, 3), faixa(larg / 2 - 0.35, larg / 2, 0.03, () => branco, 3));
  const zebra = (i: number) => (Math.abs(curvatura[i]) > (o.cenario ? 0.0035 : 0.006) ? (Math.floor(i / 2) % 2 ? new THREE.Color("#d92b2b") : branco) : null);
  const zb = o.cenario ? 2.8 : 1.4; // com cenário, zebra mais larga: é ela que desenha as curvas vistas de longe
  g.add(faixa(-larg / 2 - zb, -larg / 2, 0.025, zebra, 3), faixa(larg / 2, larg / 2 + zb, 0.025, zebra, 3));
  // linha de chegada quadriculada em f = 0
  const p0 = pontos[0], t0 = pontos[1].clone().sub(p0).normalize();
  const tex = document.createElement("canvas");
  tex.width = 256;
  tex.height = 32;
  const x = tex.getContext("2d")!;
  for (let i = 0; i < 32; i++) for (let j = 0; j < 4; j++) {
    x.fillStyle = (i + j) % 2 ? "#111" : "#fff";
    x.fillRect(i * 8, j * 8, 8, 8);
  }
  const chegada = new THREE.Mesh(new THREE.PlaneGeometry(larg, 1.6), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(tex) }));
  chegada.rotation.x = -Math.PI / 2;
  chegada.rotation.z = Math.atan2(t0.x, -t0.z) + Math.PI / 2;
  chegada.position.set(p0.x, 0.04, p0.z);
  g.add(chegada);
  for (const r of o.rotulos ?? []) {
    const s = rotulo(r.texto, { altura: 60 });
    const p = pontos[Math.floor((((r.f % 1) + 1) % 1) * N)];
    s.position.set(p.x, 70, p.z);
    g.add(s);
  }
  const info: InfoCircuito = { pontos, comprimento: comp, curvatura, pista, escape, total: (pista.geometry.index?.count ?? 0), faixas };
  g.userData.circuito = info;
  g.userData.nome = nome;
  g.userData.curvas = (dados as { curvas?: { n: number; f: number }[] }).curvas ?? []; // numerarCurvas: as curvas DESTE circuito
  if (o.cenario) vestirCircuito(g, pontos, comp, { ...(CENARIOS[nome] ?? { arquibancadas: [] }), noite: o.noite }, bordas);
  aoRestaurar(() => {
    for (const m of faixas) m.geometry.setDrawRange(0, m.geometry.index?.count ?? 0);
  });
  return g;
}

const infoDe = (c: THREE.Object3D) => c.userData.circuito as InfoCircuito;

/** Posição e giro do carro na volta (f 0 a 1) e o esterço das rodas: poe(w, k, q.x, q.z, q.giro); estercar(carro, q.esterco).
 *  `lado` desloca do centro da pista (metros; positivo = à esquerda). */
export function noCircuito(circ: THREE.Object3D, f: number, lado = 0) {
  const info = infoDe(circ);
  const { pontos, curvatura } = info;
  const N = pontos.length;
  const u = (((f % 1) + 1) % 1) * N;
  const i = Math.floor(u), a = pontos[i], b = pontos[(i + 1) % N];
  const p = a.clone().lerp(b, u - i);
  // direção em janela de ~30 m: sem isso o carro treme nos pontos do traçado
  const t = pontos[(i + 4) % N].clone().sub(pontos[(i - 4 + N) % N]).normalize();
  // esterço: curvatura média em ~28 m, um pouco À FRENTE do carro (as rodas viram antes de a traseira entrar na curva);
  // Ackermann (entre-eixos 3,4 m) e curva de visibilidade: curva lenta ~20-25°, rápida 5-10°, reta 0 (sem tremer)
  const passo = info.comprimento / N;
  const W = Math.max(2, Math.round(14 / passo)), A = Math.round(4 / passo);
  let cv = 0;
  for (let d = -W; d <= W; d++) cv += curvatura[(i + A + d + N) % N] / (2 * W + 1);
  const ack = Math.atan(3.4 * cv);
  const esterco = Math.sign(ack) * 0.45 * (1 - Math.exp(-Math.max(0, Math.abs(ack) - 0.0025) / 0.05));
  p.x += -t.z * lado;
  p.z += t.x * lado;
  circ.updateMatrixWorld(true);
  const w = circ.localToWorld(p);
  return { x: w.x, z: w.z, giro: Math.atan2(-t.x, -t.z), esterco };
}

/** Distância (m) que a fração f da volta representa: para `rolarRodas` de um carro na volta. */
const metrosNaVolta = (circ: THREE.Object3D, f: number) => f * infoDe(circ).comprimento;

/** Carro na volta do circuito: esterço das dianteiras E as 4 rodas rolando com a distância (f a f). `v` = velocidade real
 *  em m/s (só para limitar o giro visto; padrão 80). `escala` > 1 só para vista de longe (senão o carro some). */
export function poeNoCircuito(w: Mundo, k: number, circ: THREE.Object3D, f: number, o: { lado?: number; escala?: number; v?: number } = {}) {
  const q = noCircuito(circ, f, o.lado ?? 0);
  poe(w, k, q.x, q.z, q.giro);
  w.carros[k].scale.setScalar(o.escala ?? 1);
  estercar(w.carros[k], q.esterco);
  rolarRodas(w.carros[k], metrosNaVolta(circ, f), o.v ?? 80);
  return q;
}

/** Carro com pintura própria na volta (ex.: as cores de um carro antigo). A chave guarda o modelo. */
export function poePinturaNoCircuito(w: Mundo, chave: string, pintura: Pintura, circ: THREE.Object3D, f: number, o: { lado?: number; escala?: number; v?: number } = {}) {
  const c = obj(w, `carro:${chave}`, () => carro(pintura));
  const q = noCircuito(circ, f, o.lado ?? 0);
  c.position.set(q.x, 0, q.z);
  c.rotation.y = q.giro;
  c.scale.setScalar(o.escala ?? 1);
  estercar(c, q.esterco);
  rolarRodas(c, metrosNaVolta(circ, f), o.v ?? 80);
  return q;
}

/** Câmera atrás do carro na fração f, olhando a pista à frente: a curva aparece antes de o carro virar. Usa pontos da
 *  própria linha do traçado, sem tremer. `atras`, `alto` e `frente` em metros. */
export function perseguir(w: Mundo, circ: THREE.Object3D, f: number, o: { atras?: number; alto?: number; frente?: number; lente?: number; rolar?: number } = {}) {
  const { comprimento } = infoDe(circ);
  const a = noCircuito(circ, f - (o.atras ?? 15) / comprimento);
  const b = noCircuito(circ, f + (o.frente ?? 22) / comprimento);
  camera(w, [a.x, o.alto ?? 5.5, a.z], [b.x, 0.5, b.z], o.lente ?? 46, o.rolar ?? 0);
}

/** Posições de câmera em volta do carro (metros, no referencial dele): `tras` atrás (negativo = à frente do carro), `lado`
 *  (positivo = direita), `alto`, `olha` = quanto à frente do carro ela mira, `lente`. */
export const CAMERAS = {
  atras: { tras: 14, lado: 0, alto: 4.5, olha: 12, lente: 46 },
  curva: { tras: 17, lado: 0, alto: 6.5, olha: 20, lente: 50 },
  rasante: { tras: 8, lado: 1, alto: 0.9, olha: 16, lente: 62 },
  lado: { tras: 1, lado: 13, alto: 1.8, olha: 0, lente: 52 },
  ladoesq: { tras: 1, lado: -13, alto: 1.8, olha: 0, lente: 52 },
  frente: { tras: -17, lado: 2, alto: 1.7, olha: 0, lente: 40 },
  alto: { tras: 24, lado: -6, alto: 20, olha: 2, lente: 44 },
  heli: { tras: 46, lado: 30, alto: 46, olha: 2, lente: 40 },
  roda: { tras: 2.6, lado: 2.1, alto: 0.45, olha: 8, lente: 56 },
};
type Rig = (typeof CAMERAS)["atras"];
type NomeCamera = keyof typeof CAMERAS;

/** Câmera que transita entre posições ao longo do plano, sempre em movimento e sem tranco. `u` = 0 a 1 no plano (c.k);
 *  `lista` = posições em ordem. Referencial = direção da pista suavizada em ~50 m, então a câmera não sacode nas curvas. */
export function filmar(w: Mundo, circ: THREE.Object3D, f: number, u: number, lista: (NomeCamera | Rig)[], o: { lado?: number } = {}) {
  const { comprimento } = infoDe(circ);
  const n = lista.length;
  const pos = Math.max(0, Math.min(0.9999, u)) * n;
  const seg = Math.floor(pos);
  const local = pos - seg;
  // cada posição fica um tempo e a passagem para a próxima ocupa o último 45% do trecho, com leve deriva durante a parada
  const mix = Math.max(0, (local - 0.55) / 0.45);
  const m = mix * mix * (3 - 2 * mix);
  const rig = (x: NomeCamera | Rig) => (typeof x === "string" ? CAMERAS[x] : x);
  const a = rig(lista[seg]), b = rig(lista[Math.min(n - 1, seg + 1)]);
  const v = (k: keyof Rig) => a[k] + (b[k] - a[k]) * m;
  const deriva = 1 + 0.1 * (u - 0.5);
  const c = noCircuito(circ, f, o.lado ?? 0);
  const p0 = noCircuito(circ, f - 25 / comprimento), p1 = noCircuito(circ, f + 25 / comprimento);
  const L = Math.hypot(p1.x - p0.x, p1.z - p0.z) || 1;
  const tx = (p1.x - p0.x) / L, tz = (p1.z - p0.z) / L;
  const dir = { x: -tz, z: tx };
  let px = c.x - tx * v("tras") * deriva + dir.x * v("lado") * deriva;
  let pz = c.z - tz * v("tras") * deriva + dir.z * v("lado") * deriva;
  // abaixo do alto do alambrado, a câmera não sai da pista: o muro fica a 19 m do centro e não pode passar na frente do carro
  const { pontos } = infoDe(circ);
  const N = pontos.length, i0 = Math.floor((((f % 1) + 1) % 1) * N), janela = Math.ceil((120 / comprimento) * N);
  let d = Infinity;
  for (let k = -janela; k <= janela; k += 2) {
    const q = pontos[(i0 + k + N * 2) % N];
    d = Math.min(d, Math.hypot(q.x - px, q.z - pz));
  }
  const baixa = Math.max(0, Math.min(1, (9 - v("alto")) / 2));
  const puxa = 1 + (Math.min(1, 14 / Math.max(d, 0.01)) - 1) * baixa;
  px = c.x + (px - c.x) * puxa;
  pz = c.z + (pz - c.z) * puxa;
  camera(w, [px, v("alto"), pz], [c.x + tx * v("olha"), 0.55, c.z + tz * v("olha")], v("lente"));
}

/** Vários carros andando na volta. `v` em frações de volta por segundo. */
export function transito(w: Mundo, circ: THREE.Object3D, t: number, ks: number[], o: { v?: number; escala?: number; ini?: number } = {}) {
  const vm = (o.v ?? 0.014) * infoDe(circ).comprimento;
  ks.forEach((k, i) => poeNoCircuito(w, k, circ, (o.ini ?? 0) + i / ks.length + t * (o.v ?? 0.014), { escala: o.escala ?? 3, lado: i % 2 ? 2 : -2, v: vm }));
}

/** Câmera panorâmica: a pista inteira em diagonal, como de um helicóptero. `az` = azimute em radianos, `alto` = 0 (rasante) a 1 (de cima). */
export function panorama(w: Mundo, circ: THREE.Object3D, az = 0.3, alto = 0.55, folga = 1, lente = 34) {
  const caixa = new THREE.Box3().setFromPoints(infoDe(circ).pontos);
  const c = caixa.getCenter(new THREE.Vector3());
  const d = (caixa.getSize(new THREE.Vector3()).length() * 0.5 * folga) / Math.tan((lente * Math.PI) / 360) / (1080 / 1920);
  const h = Math.sin((alto * Math.PI) / 2), l = Math.cos((alto * Math.PI) / 2);
  camera(w, [c.x + Math.sin(az) * l * d, h * d, c.z + Math.cos(az) * l * d], [c.x, 0, c.z], lente);
  afastarNevoa(w, d);
}

/** Nomes dos trechos reais em cima do circuito, entrando um a um com k (vista de longe). */
export function nomearTrechos(w: Mundo, circ: THREE.Object3D, k = 1, o: { tam?: number; altura?: number } = {}) {
  const lista = TRECHOS[circ.userData.nome as string] ?? TRECHOS_INTERLAGOS;
  lista.forEach((n, i) => {
    if (k * lista.length <= i) return;
    const s = obj(w, `nome:${circ.uuid}:${n.texto}`, () => rotulo(n.texto, { altura: o.tam ?? 44 }));
    s.position.copy(pontoNoCircuito(circ, n.f, o.altura ?? 45));
  });
}

/** Ponto do circuito no mundo (f 0 a 1), para câmera e rótulos. */
export function pontoNoCircuito(circ: THREE.Object3D, f: number, altura = 0) {
  const q = noCircuito(circ, f);
  return new THREE.Vector3(q.x, altura, q.z);
}

/** Desenha o traçado aos poucos (k 0 = nada, 1 = a volta inteira), como um traço sendo revelado. */
export function revelarCircuito(circ: THREE.Object3D, k: number) {
  const info = infoDe(circ);
  for (const m of info.faixas) m.geometry.setDrawRange(0, Math.floor(((m.geometry.index?.count ?? 0) / 6) * Math.max(0, Math.min(1, k))) * 6);
}

/** Acende um trecho do traçado (de/ate em fração da volta) com brilho, ex.: o S do Senna. `largura` em metros: ~40 para
 *  ver do alto (a pista inteira de longe), ~10 de perto. */
export function destacarTrecho(w: Mundo, circ: THREE.Object3D, de: number, ate: number, k = 1, cor = "#ffc93a", largura = 40) {
  const info = infoDe(circ);
  const chave = `trecho:${circ.uuid}:${de}:${ate}:${largura}`;
  const m = obj(w, chave, () => {
    const N = info.pontos.length;
    const pts: THREE.Vector3[] = [];
    for (let i = Math.floor(de * N); i <= Math.floor(ate * N); i++) pts.push(info.pontos[((i % N) + N) % N].clone().setY(0.06));
    const tubo = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length, largura / 2, 6, false),
      new THREE.MeshBasicMaterial({ color: cor, transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
    tubo.scale.y = 0.05;
    tubo.renderOrder = 20; // por cima da pista (as faixas da pista são puxadas para a frente na profundidade)
    return tubo;
  });
  circ.updateMatrixWorld(true);
  m.position.setFromMatrixPosition(circ.matrixWorld);
  (m.material as THREE.MeshBasicMaterial).opacity = 0.85 * k;
  return m;
}

let texNum: Map<string, THREE.CanvasTexture> | null = null;
/** Número de curva num círculo (azul-marinho com borda verde-água). */
function texturaNumero(n: string) {
  texNum ??= new Map();
  let t = texNum.get(n);
  if (t) return t;
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = "rgba(9,19,38,0.95)";
  x.beginPath();
  x.arc(64, 64, 56, 0, Math.PI * 2);
  x.fill();
  x.strokeStyle = "#2ec4b6";
  x.lineWidth = 9;
  x.stroke();
  x.fillStyle = "#ffffff";
  x.font = `900 ${n.length > 1 ? 58 : 66}px 'Segoe UI', sans-serif`;
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillText(n, 64, 68);
  t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  texNum.set(n, t);
  return t;
}

/** Curvas numeradas do circuito (posições reais de cada curva na volta, MultiViewer): um número num círculo, fora da
 *  pista, ligado por uma linha fina ao ponto da curva. Elas entram uma a uma ao longo de k (0 a 1); `destaque` = número
 *  de uma curva que fica maior e amarela. `tam` = diâmetro do círculo em metros (60 serve à vista do alto). */
export function numerarCurvas(w: Mundo, circ: THREE.Object3D, k = 1, o: { destaque?: number; tam?: number; distancia?: number } = {}) {
  const dados = (CIRCUITOS as unknown as Record<string, { curvas?: { n: number; f: number }[] }>)["interlagos"];
  const curvas = circ.userData.curvas as { n: number; f: number }[] | undefined ?? dados.curvas ?? [];
  const info = infoDe(circ);
  const N = info.pontos.length;
  // centro do traçado: o número vai para fora, longe do centro
  const centro = info.pontos.reduce((s, p) => s.add(p), new THREE.Vector3()).multiplyScalar(1 / N);
  circ.updateMatrixWorld(true);
  const tam = o.tam ?? 60;
  curvas.forEach((cv, i) => {
    const e = Math.max(0, Math.min(1, k * curvas.length - i)); // uma a uma
    if (e <= 0) return;
    const p = info.pontos[Math.floor(cv.f * N) % N].clone();
    const fora = p.clone().sub(centro).setY(0).normalize();
    const alvo = p.clone().addScaledVector(fora, o.distancia ?? 95).setY(30);
    const grande = cv.n === o.destaque;
    const s = obj(w, `curva:${circ.uuid}:${cv.n}`, () => new THREE.Sprite(new THREE.SpriteMaterial({ map: texturaNumero(String(cv.n)), transparent: true, depthTest: false })));
    s.position.copy(circ.localToWorld(alvo.clone()));
    s.scale.setScalar(tam * (grande ? 1.5 : 1) * (0.6 + 0.4 * e));
    (s.material as THREE.SpriteMaterial).opacity = e;
    (s.material as THREE.SpriteMaterial).color.set(grande ? "#ffc93a" : "#ffffff");
    s.renderOrder = 31;
    const l = obj(w, `curva:${circ.uuid}:${cv.n}:linha`, () => new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: "#2ec4b6", transparent: true, depthTest: false })));
    const ini = circ.localToWorld(p.clone().setY(1));
    const fim = circ.localToWorld(alvo.clone().addScaledVector(fora, -tam * 0.45));
    (l.geometry as THREE.BufferGeometry).setFromPoints([ini, fim]);
    (l.material as THREE.LineBasicMaterial).opacity = e;
    l.renderOrder = 30;
  });
}