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
import { estercar, rodasRapidas, rolarRodas, tempoDoVideo } from "./efeitos3d";
import { afastarNevoa, camera, poe, type Mundo } from "./mundo";
import { texturaPulso } from "./neon_vegas";
import { marcarCamera, marcarCarro, velocidadeMarcada } from "./velocidade";

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
  // Lusail (Catar), sentido horário: direita = por dentro (boxes à direita da reta), arquibancadas por fora (à esquerda). Deserto sem
  // cidade; à noite, holofotes (sem neon). Posições aproximadas (sem planta oficial): reta dos boxes, T1, T16 e o miolo.
  lusail: {
    deserto: true,
    arquibancadas: [
      { f0: 0.935, f1: 1.07, coberta: true, dist: -62 }, { f0: 0.108, f1: 0.14, dist: -84 }, { f0: 0.86, f1: 0.9, dist: -78 },
      { f0: 0.27, f1: 0.34, dist: -80 }, { f0: 0.64, f1: 0.73, dist: -84 },
    ],
    boxes: { f0: 0.975, f1: 1.04, dist: 44 },
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

/** Silverstone (Arena, 5,891 km, 18 curvas): nomes conferidos na Wikipedia ("A lap in a Formula One car", 2026-11-14):
 *  1 Abbey, 2 Farm, 3 Village, 4 The Loop, 5 Aintree, 6 Brooklands, 7 Luffield, 8 Woodcote, 9 Copse, 10-13 Maggotts e
 *  Becketts, 14 Chapel, 15 Stowe, 16 Vale, 17-18 Club. f = posição da curva no circuitos.json (MultiViewer). */
export const TRECHOS_SILVERSTONE: { texto: string; f: number }[] = [
  { texto: "ABBEY", f: 0.0775 }, { texto: "FARM", f: 0.1044 }, { texto: "VILLAGE", f: 0.1478 }, { texto: "THE LOOP", f: 0.1775 },
  { texto: "AINTREE", f: 0.2103 }, { texto: "BROOKLANDS", f: 0.3359 }, { texto: "LUFFIELD", f: 0.3743 }, { texto: "WOODCOTE", f: 0.4342 },
  { texto: "COPSE", f: 0.5237 }, { texto: "MAGGOTTS E BECKETTS", f: 0.651 }, { texto: "CHAPEL", f: 0.7093 }, { texto: "STOWE", f: 0.8552 },
  { texto: "VALE", f: 0.9321 }, { texto: "CLUB", f: 0.9614 },
];

/** Mônaco atual: vazio de propósito. A numeração oficial curva a curva (19) não foi conferida numa fonte (a Wikipedia só
 *  numera a 1 Sainte-Dévote e a 11 Nouvelle Chicane): nomear de memória arriscaria nome na curva errada. */
export const TRECHOS_MONACO: { texto: string; f: number }[] = [];

export const TRECHOS: Record<string, { texto: string; f: number }[]> = {
  interlagos: TRECHOS_INTERLAGOS, lasvegas: TRECHOS_LASVEGAS, silverstone: TRECHOS_SILVERSTONE, monaco: TRECHOS_MONACO,
};

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
export function criarCircuito(nome = "interlagos", o: { largura?: number; rotulos?: { texto: string; f: number }[]; cenario?: boolean; noite?: boolean; neon?: boolean } = {}) {
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
  const deserto = !!CENARIOS[nome]?.deserto;
  const holofote = deserto && !!o.cenario && !!o.noite; // noite de autódromo no deserto: pista acesa pelos holofotes, sem neon
  let bordas = { fora: (_: number) => larg, dentro: (_: number) => larg };
  const fatorEscape = rua && o.cenario ? 0.62 : o.cenario ? 0.95 : 1.6;
  const escape = faixa(-larg * fatorEscape, larg * fatorEscape, 0.012, () => new THREE.Color(rua && o.cenario ? (o.noite ? "#3b3f48" : "#b3b6bb") : holofote ? "#555b65" : o.cenario ? "#9aa0a6" : "#c9ccd2"), 1);
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
    const areia = new THREE.Color(holofote ? "#7a6a4c" : "#d8bd8a"), terra = new THREE.Color(holofote ? "#5e4a33" : "#a98559");
    // vira à esquerda (curvatura positiva) = o lado de fora é a direita = distância positiva
    const fora = (i: number) => largura(i, 1), dentro = (i: number) => largura(i, -1);
    bordas = { fora, dentro };
    g.add(faixa(larg * 0.9, fora, 0.006, () => areia, 0.5), faixa((i) => -dentro(i), -larg * 0.9, 0.006, () => areia, 0.5));
    g.add(faixa(larg * 0.9, (i) => fora(i) * 0.72, 0.009, (i) => (fora(i) > larg * 2 ? terra : null), 0.7),
      faixa((i) => -dentro(i) * 0.72, -larg * 0.9, 0.009, (i) => (dentro(i) > larg * 2 ? terra : null), 0.7));
  }
  // Las Vegas à noite em NEON é o padrão (pedido do Felipe, 2026-11-21); `neon: false` volta ao noturno antigo
  const neon = rua && !!o.cenario && !!o.noite && (o.neon ?? true);
  if (rua && o.cenario && o.noite) {
    // à noite a rua iluminada desenha o traçado: a faixa junto ao muro acende como a luz dos postes
    // (neon: a faixa vira o traçado em neon rosa; o brilho sobe com a altura da câmera em pos_neon.ts, de perto é só um tom)
    const m = escape.material as THREE.MeshStandardMaterial;
    m.emissive.set(neon ? "#ff2d6f" : "#ffcf8a");
    m.emissiveIntensity = neon ? 0.15 : 0.75;
    if (neon) m.color.set("#5a4a66");
  }
  if (holofote) {
    // escape e pista claros sob os holofotes (acesos por dentro, como a faixa da rua iluminada): o traçado se lê à noite
    const m = escape.material as THREE.MeshStandardMaterial;
    m.color.set("#3b3f47");
    m.emissive.set("#ffe9c4");
    m.emissiveIntensity = 0.12;
  }
  g.add(escape);
  const pista = faixa(-larg / 2, larg / 2, 0.02, () => asfalto, 2);
  if (holofote) {
    const m = pista.material as THREE.MeshStandardMaterial;
    m.color.set("#2f333a"); // asfalto escuro, como nas fotos do GP à noite (a luz dos holofotes é que o clareia)
    m.emissive.set("#fff0d6");
    m.emissiveIntensity = 0.07;
    // fios de luz ciano nas duas margens (o traçado aceso visto do alto, como nas fotos do GP) e, na reta dos boxes, a faixa
    // azul com borda vermelha da pit lane/grid (lado de dentro = direita no sentido horário)
    const ciano = new THREE.Color("#5ff0e0");
    for (const sg of [-1, 1]) {
      const t: THREE.Mesh = faixa(sg * (larg * 0.95 - 0.8), sg * (larg * 0.95 - 0.25), 0.034, () => ciano, 4);
      const mt = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -8, polygonOffsetUnits: -16 });
      mt.color.setScalar(0.9);
      t.material = mt;
      g.add(t);
    }
    const naReta = (i: number) => i / N >= 0.945 || i / N <= 0.075;
    const azul = new THREE.Color("#2f5fc4"), vermelho = new THREE.Color("#d8404f");
    const e0 = larg * 0.95 + 0.4;
    g.add(faixa(e0, e0 + 11, 0.03, (i) => (naReta(i) ? azul : null), 2), faixa(e0, e0 + 1.8, 0.035, (i) => (naReta(i) ? vermelho : null), 3));
  }
  if (neon) (pista.material as THREE.MeshStandardMaterial).color.set("#8e88a6"); // asfalto um pouco mais escuro e frio (fosco, sem reflexo)
  g.add(pista);
  const pulsos: THREE.MeshBasicMaterial[] = [];
  if (neon) {
    // tubo de neon nas duas margens (entre o escape e o muro) e o pulso de luz que percorre a volta por cima dele;
    // o pulso largo (escape inteiro) só aparece na vista do alto (pos_neon.ts), para o traçado do mapa ter luz andando
    const borda = larg * fatorEscape;
    const rosa = new THREE.Color("#ff2d6f");
    for (const s of [-1, 1]) {
      const t: THREE.Mesh = faixa(s * (borda - 0.9), s * (borda - 0.25), 0.032, () => rosa, 4);
      const mt = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -8, polygonOffsetUnits: -16 });
      mt.color.setScalar(1.6);
      t.material = mt;
      g.add(t);
    }
    const fita = (d0: number, d1: number, y: number, forca: number) => {
      const f: THREE.Mesh = faixa(d0, d1, y, () => rosa, 5);
      const pos = f.geometry.getAttribute("position");
      const uv: number[] = [];
      for (let k = 0; k < pos.count; k++) uv.push(((Math.floor(k / 4) + (k % 4 >= 2 ? 1 : 0)) / N) * 7, k % 2); // 7 pulsos na volta
      f.geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
      const m = new THREE.MeshBasicMaterial({ map: texturaPulso().clone(), color: "#ffd0ec", transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -10, polygonOffsetUnits: -20 });
      m.map!.wrapS = THREE.RepeatWrapping;
      m.map!.needsUpdate = true;
      m.color.multiplyScalar(forca);
      f.material = m;
      f.userData.semSombra = true;
      g.add(f);
      pulsos.push(m);
      return f;
    };
    fita(-(borda - 0.9), -(borda - 0.25), 0.036, 2.2);
    fita(borda - 0.9, borda - 0.25, 0.036, 2.2);
    fita(-borda, borda, 0.04, 4).name = "pulso_largo";
  }
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
  g.userData.vestido = { larg, bordas: o.cenario ? bordas : null }; // velocidade.ts (postes e painéis junto ao muro) e pelotao/filmar
  if (o.cenario) vestirCircuito(g, pontos, comp, { ...(CENARIOS[nome] ?? { arquibancadas: [] }), noite: o.noite, neon }, bordas);
  // pos_neon.ts acha este circuito visível e liga bloom, cor, névoa roxa e as luzes traseiras dos carros
  if (neon) g.userData.neon = { escape: escape.material, pulsos, centro: new THREE.Box3().setFromPoints(pontos).getCenter(new THREE.Vector3()) };
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
  const i = Math.floor(u) % N, fr = u - Math.floor(u), a = pontos[i], b = pontos[(i + 1) % N];
  const p = a.clone().lerp(b, fr);
  // direção em janela de ~30 m (sem isso o carro treme nos pontos do traçado), INTERPOLADA entre o ponto i e o i+1:
  // calculada só no ponto i, o giro mudava em degraus a cada ponto do traçado e a câmera presa ao carro dava um
  // tranco a cada ponto (medido no "freios", 2026-11-13: saltos periódicos de 12 a 34 quadros conforme a velocidade)
  const tg = (j: number) => pontos[(j + 4) % N].clone().sub(pontos[(j - 4 + N) % N]).normalize();
  const t = tg(i).lerp(tg(i + 1), fr).normalize();
  // esterço: curvatura média em ~28 m, um pouco À FRENTE do carro (as rodas viram antes de a traseira entrar na curva);
  // Ackermann (entre-eixos 3,4 m) e curva de visibilidade: curva lenta ~20-25°, rápida 5-10°, reta 0 (sem tremer)
  const passo = info.comprimento / N;
  const W = Math.max(2, Math.round(14 / passo)), A = Math.round(4 / passo);
  const media = (j: number) => {
    let s = 0;
    for (let d = -W; d <= W; d++) s += curvatura[(j + A + d + N * 2) % N] / (2 * W + 1);
    return s;
  };
  const cv = media(i) * (1 - fr) + media(i + 1) * fr;
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

/** Altura do asfalto (m): a pista de `criarCircuito` é um plano a 0,02; o carro assenta nela (antes ficava em 0 e os pneus afundavam 2 cm). */
const ALTURA_ASFALTO = 0.02;

/** Carro na volta do circuito: esterço das dianteiras E as 4 rodas rolando com a distância (f a f). `v` = velocidade real
 *  em m/s (só para limitar o giro visto; padrão 80). `escala` > 1 só para vista de longe (senão o carro some). */
export function poeNoCircuito(w: Mundo, k: number, circ: THREE.Object3D, f: number, o: { lado?: number; escala?: number; v?: number; velocidade?: boolean } = {}) {
  const q = noCircuito(circ, f, o.lado ?? 0);
  poe(w, k, q.x, q.z, q.giro);
  w.carros[k].position.y = ALTURA_ASFALTO; // a pista é um plano a 2 cm do chão: com o carro em y=0 os pneus afundavam nela
  w.carros[k].scale.setScalar(o.escala ?? 1);
  estercar(w.carros[k], q.esterco);
  rolarRodas(w.carros[k], metrosNaVolta(circ, f), o.v ?? 80);
  if (o.velocidade !== false) marcarCarro(circ, o.v ?? 80, o.escala ?? 1); // sistema de velocidade (velocidade.ts)
  return q;
}

/** Carro com pintura própria na volta (ex.: as cores de um carro antigo). A chave guarda o modelo. */
export function poePinturaNoCircuito(w: Mundo, chave: string, pintura: Pintura, circ: THREE.Object3D, f: number, o: { lado?: number; escala?: number; v?: number; velocidade?: boolean } = {}) {
  const c = obj(w, `carro:${chave}`, () => carro(pintura));
  const q = noCircuito(circ, f, o.lado ?? 0);
  c.position.set(q.x, ALTURA_ASFALTO, q.z);
  c.rotation.y = q.giro;
  c.scale.setScalar(o.escala ?? 1);
  estercar(c, q.esterco);
  rolarRodas(c, metrosNaVolta(circ, f), o.v ?? 80);
  if (o.velocidade !== false) marcarCarro(circ, o.v ?? 80, o.escala ?? 1);
  return q;
}

/** Câmera atrás do carro na fração f, olhando a pista à frente: a curva aparece antes de o carro virar. Usa pontos da
 *  própria linha do traçado, sem tremer. `atras`, `alto` e `frente` em metros. */
export function perseguir(w: Mundo, circ: THREE.Object3D, f: number, o: { atras?: number; alto?: number; frente?: number; lente?: number; rolar?: number; velocidade?: boolean } = {}) {
  const { comprimento } = infoDe(circ);
  const a = noCircuito(circ, f - (o.atras ?? 15) / comprimento);
  const b = noCircuito(circ, f + (o.frente ?? 22) / comprimento);
  camera(w, [a.x, o.alto ?? 5.5, a.z], [b.x, 0.5, b.z], o.lente ?? 46, o.rolar ?? 0);
  if (o.velocidade !== false) {
    const c = noCircuito(circ, f);
    marcarCamera(circ, c.x, c.z);
  }
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
  // repertório novo (2026-11-21, pedido do Felipe: "câmera do alto → atrás → alto → atrás o vídeo todo cansa"): linguagem de
  // TV de F1 e de jogo de corrida. Câmera BAIXA e perto = mais velocidade (câmera de zebra/meio-fio da TV; câmera aberta e
  // longe faz o carro parecer lento).
  /** câmera baixa ao lado da roda dianteira, olhando para a frente: o pneu e o asfalto correndo */
  rodaFrente: { tras: -0.9, lado: 1.85, alto: 0.32, olha: 10, lente: 64 },
  /** 3/4 frontal baixa: o carro vindo na direção da lente, de lado */
  tresQuartos: { tras: -9, lado: 4.2, alto: 0.75, olha: -1, lente: 44 },
  /** travelling lateral: a câmera corre junto, de lado e baixa, a uns 5 m */
  travelling: { tras: 0.4, lado: 5.4, alto: 1, olha: 1.5, lente: 50 },
  /** câmera no nariz (bico) olhando para a frente: a pista vindo por baixo */
  nariz: { tras: -0.6, lado: 0, alto: 1.02, olha: 26, lente: 72 },
  /** sobre o ombro / acima do halo (T-cam): halo e bico no quadro, a pista à frente */
  halo: { tras: 1.25, lado: 0.42, alto: 1.42, olha: 24, lente: 64 },
  /** helicóptero alto e longe, lente fechada, acompanhando o pelotão de lado */
  helicoptero: { tras: 75, lado: 38, alto: 58, olha: 28, lente: 26 },
};
export type Rig = { tras: number; lado: number; alto: number; olha: number; lente: number; fixa?: number };
export type NomeCamera = keyof typeof CAMERAS;
/** Tomadas que mudam ao longo do próprio trecho (u local 0 a 1): drone orbitando o carro e grua que sobe. */
const DINAMICAS = {
  drone: (u: number): Rig => {
    // acima do alambrado (7 m): mais baixo, o drone passava rente ao muro e ao tubo de neon
    const a = 0.45 + u * 1.9;
    return { tras: 12 * Math.cos(a), lado: 12 * Math.sin(a), alto: 9.5 + 2 * u, olha: 0, lente: 44 };
  },
  grua: (u: number): Rig => {
    const s = u * u * (3 - 2 * u);
    return { tras: 9 + 6 * s, lado: 2.6, alto: 0.8 + 17 * s, olha: 8 + 10 * s, lente: 46 - 8 * s };
  },
};
export type NomeTomada = NomeCamera | keyof typeof DINAMICAS | "passagem";
/** Família de cada tomada (para não repetir a mesma linguagem em cenas seguidas). */
export const TIPO_CAMERA: Record<NomeTomada, string> = {
  atras: "atras", curva: "atras", rasante: "baixa", lado: "lateral", ladoesq: "lateral", travelling: "lateral", frente: "frente",
  tresQuartos: "frente", alto: "alto", heli: "heli", helicoptero: "heli", roda: "roda", rodaFrente: "roda", nariz: "onboard",
  halo: "onboard", drone: "orbita", grua: "grua", passagem: "fixa",
};

/** Câmera que transita entre posições ao longo do plano, sempre em movimento e sem tranco. `u` = 0 a 1 no plano (c.k);
 *  `lista` = posições em ordem. Referencial = direção da pista suavizada em ~50 m, então a câmera não sacode nas curvas.
 *  "passagem" = câmera FIXA na beira da pista (pan-by): o carro vem de longe (lente fechada), passa colado e vai embora,
 *  com a câmera girando atrás dele; o carro passa por ela no meio do trecho dela (`dur` = c.fim e `v` em m/s acertam o
 *  ponto; sem eles, 3 s e a velocidade do carro posto no quadro). `espelho` troca o lado das tomadas laterais. */
export function filmar(w: Mundo, circ: THREE.Object3D, f: number, u: number, lista: (NomeTomada | Rig)[], o: { lado?: number; dur?: number; v?: number; espelho?: boolean; velocidade?: boolean } = {}) {
  const { comprimento } = infoDe(circ);
  const n = lista.length;
  const pos = Math.max(0, Math.min(0.9999, u)) * n;
  const seg = Math.floor(pos);
  const local = pos - seg;
  // cada posição fica um tempo e a passagem para a próxima ocupa o último 45% do trecho, com leve deriva durante a parada
  const mix = Math.max(0, (local - 0.55) / 0.45);
  const m = mix * mix * (3 - 2 * mix);
  const c = noCircuito(circ, f, o.lado ?? 0);
  const p0 = noCircuito(circ, f - 25 / comprimento), p1 = noCircuito(circ, f + 25 / comprimento);
  const L = Math.hypot(p1.x - p0.x, p1.z - p0.z) || 1;
  const tx = (p1.x - p0.x) / L, tz = (p1.z - p0.z) / L;
  const dir = { x: -tz, z: tx };
  const esp = o.espelho ? -1 : 1;
  const rig = (x: NomeTomada | Rig, l: number): Rig => {
    if (typeof x !== "string") return x;
    if (x === "passagem") return passagem(circ, f, c, tx, tz, dir, (0.5 - l) * ((o.dur ?? 3) / n) * (o.v ?? velocidadeMarcada() ?? 85), esp);
    const r = x in DINAMICAS ? DINAMICAS[x as keyof typeof DINAMICAS](l) : CAMERAS[x as NomeCamera];
    return { ...r, lado: r.lado * esp };
  };
  const a = rig(lista[seg], local), b = rig(lista[Math.min(n - 1, seg + 1)], seg + 1 < n ? 0 : local);
  const v = (k: "tras" | "lado" | "alto" | "olha" | "lente") => a[k] + (b[k] - a[k]) * m;
  const fixa = (a.fixa ?? 0) + ((b.fixa ?? 0) - (a.fixa ?? 0)) * m; // 1 = câmera presa ao chão (sem deriva nem puxada)
  const deriva = 1 + 0.1 * (u - 0.5) * (1 - fixa);
  let px = c.x - tx * v("tras") * deriva + dir.x * v("lado") * deriva;
  let pz = c.z - tz * v("tras") * deriva + dir.z * v("lado") * deriva;
  // no caminho entre duas posições baixas a câmera não atravessa o carro (rodaFrente → nariz passava dentro do pneu):
  // em cima da planta do carro ela fica pelo menos a 1 m do chão (acima das rodas)
  let alto = v("alto");
  const T = v("tras") * deriva, Lt = v("lado") * deriva;
  if (fixa < 0.5 && T > -3.1 && T < 3 && Math.abs(Lt) < 1.3) alto = Math.max(alto, 1);
  // abaixo do alto do alambrado, a câmera não sai da pista: o muro fica a 19 m do centro e não pode passar na frente do carro
  const { pontos } = infoDe(circ);
  // distância da câmera ao traçado contínua (segmentos inteiros): pontos de 2 em 2 a partir do ponto do carro mudavam
  // em degraus e davam tranco na câmera baixa a cada ponto do traçado (2026-11-13)
  const N = pontos.length, i0 = Math.floor((((f % 1) + 1) % 1) * N), janela = Math.ceil((120 / comprimento) * N);
  let d = Infinity;
  for (let k = -janela; k < janela; k++) {
    const q = pontos[(i0 + k + N * 2) % N], r = pontos[(i0 + k + 1 + N * 2) % N];
    const sx = r.x - q.x, sz = r.z - q.z, L2 = sx * sx + sz * sz || 1;
    const h = Math.max(0, Math.min(1, ((px - q.x) * sx + (pz - q.z) * sz) / L2));
    d = Math.min(d, Math.hypot(q.x + sx * h - px, q.z + sz * h - pz));
  }
  const baixa = Math.max(0, Math.min(1, (9 - alto) / 2)) * (1 - fixa);
  const puxa = 1 + (Math.min(1, 14 / Math.max(d, 0.01)) - 1) * baixa;
  px = c.x + (px - c.x) * puxa;
  pz = c.z + (pz - c.z) * puxa;
  camera(w, [px, alto, pz], [c.x + tx * v("olha"), 0.55, c.z + tz * v("olha")], v("lente"));
  if (o.velocidade !== false) marcarCamera(circ, c.x, c.z);
}

/** Pan-by: câmera fixa na beira da pista, logo por dentro do muro, a 2,9 m do chão; `dist` = metros que o carro ainda anda até
 *  passar por ela (negativo = já passou). Devolve a posição como Rig no referencial do carro (para misturar com as outras).
 *  Lente fecha com a distância (carro longe = teleobjetiva, colado = grande-angular), como o cinegrafista de pista. */
function passagem(circ: THREE.Object3D, f: number, c: { x: number; z: number }, tx: number, tz: number, dir: { x: number; z: number }, dist: number, esp: number): Rig {
  const info = infoDe(circ);
  const fa = f + dist / info.comprimento;
  const a = noCircuito(circ, fa);
  const ves = circ.userData.vestido as { larg: number; bordas: { fora: (i: number) => number; dentro: (i: number) => number } | null } | undefined;
  const i = Math.floor((((fa % 1) + 1) % 1) * info.pontos.length);
  const muro = ves?.bordas ? (esp > 0 ? ves.bordas.fora(i) : ves.bordas.dentro(i)) + 3 : (ves?.larg ?? 13) / 2 + 5;
  // logo por dentro do muro e acima dele (2,9 m), como a câmera de pista atrás do alambrado: mais baixa, a zebra enchia o quadro
  const lado = (muro - 0.7) * esp;
  // normal da pista no ponto da câmera (a mesma convenção de filmar: posição = ponto + dir * lado)
  const b = noCircuito(circ, fa + 4 / info.comprimento), q = noCircuito(circ, fa - 4 / info.comprimento);
  const Lq = Math.hypot(b.x - q.x, b.z - q.z) || 1;
  const nx = -(b.z - q.z) / Lq, nz = (b.x - q.x) / Lq;
  const X = a.x + nx * lado, Z = a.z + nz * lado;
  const rx = X - c.x, rz = Z - c.z;
  const d = Math.hypot(rx, rz);
  const k = Math.max(0, Math.min(1, 1 - (d - 8) / 110));
  return { tras: -(rx * tx + rz * tz), lado: rx * dir.x + rz * dir.z, alto: 2.9, olha: 0, lente: 16 + 32 * k * k, fixa: 1 };
}

/** Vários carros andando na volta. `v` em frações de volta por segundo. */
export function transito(w: Mundo, circ: THREE.Object3D, t: number, ks: number[], o: { v?: number; escala?: number; ini?: number; velocidade?: boolean } = {}) {
  const vm = (o.v ?? 0.014) * infoDe(circ).comprimento;
  ks.forEach((k, i) => poeNoCircuito(w, k, circ, (o.ini ?? 0) + i / ks.length + t * (o.v ?? 0.014), { escala: o.escala ?? 3, lado: i % 2 ? 2 : -2, v: vm, velocidade: o.velocidade }));
}

const acaso = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Pelotão: `n` carros (até 22, 11 equipes × 2, pintura de cada equipe) andando juntos na volta, sem se sobrepor. O carro
 *  `foco` (padrão 0) fica em f, na faixa `lado`; os outros em volta dele conforme `forma`:
 *  "pelotao" (padrão: grupos de 2 a 4 carros colados, com buracos entre os grupos), "fila" (um atrás do outro),
 *  "duelo" (pares lado a lado) ou "espalhado" (longe uns dos outros). `posicao`: "meio" (padrão: ~40% à frente do foco, o
 *  resto atrás; a câmera de trás vê carros à frente), "lider" (foco na frente) ou "fim" (foco por último).
 *  `v` = m/s de todos (padrão 85, ~300 km/h); as distâncias "respiram" devagar com o tempo (aproximam e afastam, sem
 *  ultrapassar). `carros` = quais carros usar (padrão: os 22 numa ordem tirada da `semente`, sem o foco). Já põe as rodas
 *  rápidas (borrão) em todos. Devolve [{k, f, lado}] na ordem da pista (o primeiro é o da frente). Custo medido: ver
 *  api_cenas.md ("Pelotão"). */
export function pelotao(w: Mundo, circ: THREE.Object3D, f: number, n = 8, o: { foco?: number; lado?: number; carros?: number[]; v?: number; forma?: "pelotao" | "fila" | "duelo" | "espalhado"; posicao?: "meio" | "lider" | "fim"; semente?: number; t?: number; escala?: number; velocidade?: boolean } = {}) {
  const info = infoDe(circ);
  const foco = o.foco ?? 0;
  const sem = o.semente ?? 1;
  const r = (j: number) => acaso(sem * 97 + j * 13.7);
  const v = o.v ?? 85;
  const ves = circ.userData.vestido as { larg: number } | undefined;
  const maxLado = (ves?.larg ?? 13) / 2 - 1.4;
  const outros = (o.carros ?? Array.from({ length: 22 }, (_, k) => k).sort((a, b) => acaso(sem + a * 3.1) - acaso(sem + b * 3.1))).filter((k) => k !== foco);
  const total = Math.max(1, Math.min(22, n, outros.length + 1));
  // vagas: distância (m) a partir do primeiro carro (0, -d1, -d2...) e faixa
  const forma = o.forma ?? "pelotao";
  const vagas: { d: number; lado: number }[] = [];
  let d = 0, grupo = 0, tamGrupo = 2 + Math.floor(r(0) * 3);
  for (let j = 0; j < total; j++) {
    let lado = (r(j + 50) - 0.5) * 2 * maxLado * 0.8;
    if (j > 0) {
      if (forma === "fila") {
        d -= 10 + 6 * r(j);
        lado = (j % 2 ? 1 : -1) * (0.4 + 0.8 * r(j + 9));
      } else if (forma === "duelo") {
        const par = j % 2 === 1;
        d -= par ? 1.5 * r(j) : 12 + 10 * r(j);
        lado = (par ? 1 : -1) * Math.min(maxLado, 2.5);
      } else if (forma === "espalhado") d -= 22 + 30 * r(j);
      else {
        grupo++;
        if (grupo >= tamGrupo) {
          grupo = 0;
          tamGrupo = 2 + Math.floor(r(j + 30) * 3);
          d -= 16 + 18 * r(j); // buracos curtos: de perto e do alto o pelotão aparece junto no quadro
        } else d -= 8 + 4 * r(j);
      }
    } else if (forma === "duelo") lado = -Math.min(maxLado, 2.5);
    vagas.push({ d, lado });
  }
  const iFoco = o.posicao === "lider" ? 0 : o.posicao === "fim" ? total - 1 : Math.floor(total * 0.4);
  const base = vagas[iFoco];
  const t = o.t ?? tempoDoVideo();
  const lista = vagas.map((g, j) => {
    const eFoco = j === iFoco;
    const k = eFoco ? foco : outros[j < iFoco ? j : j - 1];
    const off = g.d - base.d + (eFoco ? 0 : 2.2 * Math.sin(0.5 * t + 1.9 * j));
    const lado = eFoco ? (o.lado ?? 0) : Math.max(-maxLado, Math.min(maxLado, g.lado + 0.5 * Math.sin(0.37 * t + j)));
    return { k, off, lado, eFoco, vaga: g.d - base.d };
  });
  // ninguém em cima de ninguém: na mesma faixa (menos de 2,3 m de lado), pelo menos 7,5 m entre os centros.
  // Sem salto (2026-11-26, card 26 cena 21: carro se teletransportava): a ordem vem da vaga fixa (não da "respiração",
  // que trocava a ordem com o tempo e jogava o carro 15 m de um lado ao outro) e o empurrão entra aos poucos entre 2,6 e
  // 2,3 m de distância lateral (antes ligava de uma vez ao cruzar 2,3 m e o carro pulava 7 m). Abaixo de 2,3 m: igual a antes.
  lista.sort((a, b) => b.vaga - a.vaga);
  for (let j = 1; j < lista.length; j++) {
    for (let i = 0; i < j; i++) {
      const a = lista[i], b = lista[j];
      const peso = Math.max(0, Math.min(1, (2.6 - Math.abs(a.lado - b.lado)) / 0.3));
      if (peso > 0) {
        if (b.eFoco) a.off += peso * (Math.max(a.off, b.off + 7.5) - a.off); // o foco não sai do lugar: quem anda é o outro
        else b.off += peso * (Math.min(b.off, a.off - 7.5) - b.off);
      }
    }
  }
  lista.sort((a, b) => b.off - a.off); // devolve na ordem da pista (o primeiro é o da frente)
  return lista.map((q) => {
    const fq = f + q.off / info.comprimento;
    poeNoCircuito(w, q.k, circ, fq, { lado: q.lado, v, escala: o.escala, velocidade: o.velocidade });
    rodasRapidas(w.carros[q.k], v);
    return { k: q.k, f: fq, lado: q.lado };
  });
}

/** Combinações de tomadas para `filmarVariado`: duas seguidas nunca têm família de câmera em comum. */
const REPERTORIO: NomeTomada[][] = [
  ["passagem"], ["rodaFrente", "rasante"], ["drone"], ["tresQuartos", "travelling"], ["grua", "helicoptero"],
  ["nariz", "halo"], ["travelling", "roda"], ["rasante", "drone"], ["halo", "tresQuartos"], ["helicoptero", "curva"],
];

/** Câmera de pista escolhida do repertório pela `semente` (use o número do plano, `c.n`): planos seguidos (n, n+1) NUNCA
 *  repetem a família de câmera, e cada um varia ângulo, distância e lente (±12%) e o lado. `evitar`: famílias que não
 *  servem nesta cena (ex.: ["onboard"] com dois carros lado a lado). Devolve as tomadas usadas. */
export function filmarVariado(w: Mundo, circ: THREE.Object3D, f: number, k: number, semente: number | string, o: { lado?: number; dur?: number; v?: number; evitar?: string[]; velocidade?: boolean } = {}) {
  const s = typeof semente === "number" ? Math.round(semente) : [...semente].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 100003, 7);
  const L = REPERTORIO.length;
  let idx = ((s % L) + L) % L;
  for (let i = 0; i < L && REPERTORIO[idx].some((x) => o.evitar?.includes(TIPO_CAMERA[x])); i++) idx = (idx + 1) % L;
  const combo = REPERTORIO[idx];
  const r = (j: number) => acaso(s * 7.3 + j);
  const varia = (x: NomeTomada, j: number): NomeTomada | Rig => {
    if (!(x in CAMERAS)) return x;
    const c = CAMERAS[x as NomeCamera];
    const e = (q: number) => 0.88 + 0.24 * r(j * 5 + q);
    return { tras: c.tras * e(1), lado: c.lado * e(2), alto: Math.max(0.3, c.alto * e(3)), olha: c.olha * e(4), lente: c.lente * e(5) };
  };
  filmar(w, circ, f, k, combo.map(varia), { lado: o.lado, dur: o.dur, v: o.v, espelho: r(99) < 0.5, velocidade: o.velocidade });
  return combo;
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