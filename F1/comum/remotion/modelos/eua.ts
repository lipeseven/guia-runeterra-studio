// Mapa dos Estados Unidos com os 48 estados contíguos + DC (us-atlas 3.0.1 = US Census Bureau, domínio público; dados em
// ./geo/eua.json, gerado por ./geo/preparar_eua.py). Pedido do Felipe (2026-11-21, GP de Las Vegas): "uma chapa azul sem
// detalhe. Cadê os estados? Se der zoom, cadê o mapa?". Projeção cônica de Albers (a dos mapas oficiais dos EUA), estados
// com cores sóbrias (vizinhos nunca com a mesma cor), bordas finas, estado destacado mais alto e com contorno branco,
// condados de Nevada, nomes dos estados que importam, cidades e o zoom do país ao estado e ao ponto (`zoomNoMapa`).
import * as THREE from "three";
import EUA from "./geo/eua.json";
import PAISES from "./paises.json";
import { camera, type Mundo } from "./mundo";

type Anel = [number, number][];
type Estado = { nome: string; aneis: Anel[]; cor: number };
const DADOS = EUA as unknown as { estados: Record<string, Estado>; condados_nv: Record<string, { nome: string; aneis: Anel[] }> };

/** Paleta sóbria (terra, sálvia, areia, cinza-azulado): 4 cores bastam (coloração por vizinhança no preparar_eua.py). */
const PALETA = ["#d9cfb8", "#b9c9a8", "#e6d9c0", "#c7c2b6", "#cdb9a0"];
const PALETA_NOITE = ["#2c3550", "#33405c", "#283049", "#3a3f58", "#30384f"];

/** Nomes em português dos estados (código FIPS) que o mapa pode escrever, e onde (lat, lon) o nome fica. */
export const ESTADOS_EUA: Record<string, { nome: string; lat: number; lon: number }> = {
  "32": { nome: "NEVADA", lat: 39.0, lon: -116.45 },
  "06": { nome: "CALIFÓRNIA", lat: 37.0, lon: -119.75 },
  "41": { nome: "OREGON", lat: 43.95, lon: -120.6 },
  "16": { nome: "IDAHO", lat: 43.75, lon: -114.7 },
  "49": { nome: "UTAH", lat: 39.35, lon: -111.6 },
  "04": { nome: "ARIZONA", lat: 34.35, lon: -111.65 },
  "48": { nome: "TEXAS", lat: 31.3, lon: -99.3 },
  "12": { nome: "FLÓRIDA", lat: 28.4, lon: -81.7 },
  "36": { nome: "NOVA YORK", lat: 42.9, lon: -75.5 },
};

/** Cidades com coordenadas conferidas (Wikipedia/GNIS). `destaque` = a cidade do vídeo. */
export const CIDADES_EUA: Record<string, { nome: string; lat: number; lon: number; estado: string }> = {
  lasvegas: { nome: "LAS VEGAS", lat: 36.1716, lon: -115.1391, estado: "32" },
  reno: { nome: "RENO", lat: 39.5296, lon: -119.8138, estado: "32" },
  carson: { nome: "CARSON CITY", lat: 39.1638, lon: -119.7674, estado: "32" },
  losangeles: { nome: "LOS ANGELES", lat: 34.0522, lon: -118.2437, estado: "06" },
  phoenix: { nome: "PHOENIX", lat: 33.4484, lon: -112.074, estado: "04" },
  saltlake: { nome: "SALT LAKE CITY", lat: 40.7608, lon: -111.891, estado: "49" },
};

export type MapaEUA = THREE.Group & {
  userData: {
    ponto: (lat: number, lon: number) => THREE.Vector3;
    areas: Record<string, { centro: THREE.Vector3; tamanho: number }>;
    alfinete?: THREE.Object3D;
  };
};

/** Texto deitado no mapa (lê de cima, norte para cima). Canvas grande: não borra no zoom. */
function textoNoChao(texto: string, altura: number, o: { cor?: string; contorno?: string; peso?: number; opacidade?: number; espaco?: number } = {}) {
  const H = 160;
  const cv = document.createElement("canvas");
  const g0 = cv.getContext("2d")!;
  const fonte = `${o.peso ?? 800} ${H * 0.62}px 'Segoe UI', 'Inter', sans-serif`;
  g0.font = fonte;
  const esp = (o.espaco ?? 0.12) * H * 0.62;
  const larg = Math.ceil([...texto].reduce((s, ch) => s + g0.measureText(ch).width + esp, 0) + H * 0.5);
  cv.width = Math.min(4096, larg);
  cv.height = H;
  const g = cv.getContext("2d")!;
  g.font = fonte;
  g.textBaseline = "middle";
  g.lineJoin = "round";
  let x = H * 0.25;
  for (const ch of texto) {
    if (o.contorno) {
      g.strokeStyle = o.contorno;
      g.lineWidth = H * 0.1;
      g.strokeText(ch, x, H / 2 + H * 0.03);
    }
    g.fillStyle = o.cor ?? "#ffffff";
    g.fillText(ch, x, H / 2 + H * 0.03);
    x += g.measureText(ch).width + esp;
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry((altura * cv.width) / H, altura),
    new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: o.opacidade ?? 1, depthWrite: false, toneMapped: false }),
  );
  m.rotation.x = -Math.PI / 2;
  m.renderOrder = 6;
  return m;
}

/** Mapa dos EUA (48 estados contíguos + DC) com os estados de verdade. Deitado no chão, norte para -z, largura do país =
 *  `tamanho` m, centro na origem. `estado` (FIPS, "32" = Nevada) fica destacado (mais alto, cor do canal, contorno branco,
 *  condados desenhados); `cidade` (chave de CIDADES_EUA) ganha o marcador amarelo. `nomes` = estados com nome escrito
 *  (padrão: o destacado e os vizinhos do oeste). `areas`: "pais", "estado", "cidade" (para `zoomNoMapa`/`areaNoMapa`).
 *  `pontoNoMapa(mapa, lat, lon)` funciona nele. */
export function criarMapaEUA(o: {
  tamanho?: number; estado?: string; cidade?: string; nomes?: string[]; cidades?: string[]; corEstado?: string;
  noite?: boolean; mar?: string; nomePais?: boolean;
} = {}): MapaEUA {
  const T = o.tamanho ?? 30;
  const destaque = o.estado ?? "32";
  const cidade = o.cidade ?? "lasvegas";
  // Albers equivalente (paralelos 29,5° e 45,5°, centro 96° O, 37,5° N) = projeção dos mapas do USGS/Census
  const rad = Math.PI / 180;
  const f1 = 29.5 * rad, f2 = 45.5 * rad, l0 = -96 * rad, p0 = 37.5 * rad;
  const n = (Math.sin(f1) + Math.sin(f2)) / 2;
  const C = Math.cos(f1) ** 2 + 2 * n * Math.sin(f1);
  const r0 = Math.sqrt(C - 2 * n * Math.sin(p0)) / n;
  const albers = (lon: number, lat: number): [number, number] => {
    const r = Math.sqrt(C - 2 * n * Math.sin(lat * rad)) / n;
    const th = n * (lon * rad - l0);
    return [r * Math.sin(th), r0 - r * Math.cos(th)];
  };
  // escala e centro pelo contorno dos 48 estados
  let x0 = 9, x1 = -9, y0 = 9, y1 = -9;
  for (const e of Object.values(DADOS.estados)) for (const a of e.aneis) for (const [lo, la] of a) {
    const [x, y] = albers(lo, la);
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  const S = T / (x1 - x0);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const proj = (lon: number, lat: number) => { const [x, y] = albers(lon, lat); return new THREE.Vector2((x - cx) * S, (y - cy) * S); };
  const forma = (a: Anel) => new THREE.Shape(a.map(([x, y]) => proj(x, y)));

  const H = T * 0.004; // espessura dos estados
  const HD = H * 2.4; // estado destacado
  const noite = !!o.noite;
  const g = new THREE.Group() as MapaEUA;
  const plano = new THREE.Group();
  plano.rotation.x = -Math.PI / 2; // forma em x/y → chão em x/-z (norte para -z)
  g.add(plano);
  const linha = (a: Anel, cor: string, z: number, opac = 1) => {
    const pts = a.map(([x, y]) => { const p = proj(x, y); return new THREE.Vector3(p.x, p.y, z); });
    const l = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: cor, transparent: opac < 1, opacity: opac }));
    l.renderOrder = 3;
    plano.add(l);
  };
  const mat = (cor: string, extra: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.85, metalness: 0, ...extra });
  const pal = noite ? PALETA_NOITE : PALETA;
  for (const [cod, e] of Object.entries(DADOS.estados)) {
    const eh = cod === destaque;
    const geo = new THREE.ExtrudeGeometry(e.aneis.map(forma), { depth: eh ? HD : H, bevelEnabled: false, curveSegments: 1 });
    plano.add(new THREE.Mesh(geo, mat(eh ? (o.corEstado ?? "#2ec4b6") : pal[e.cor % pal.length], eh ? { emissive: o.corEstado ?? "#2ec4b6", emissiveIntensity: 0.12 } : {})));
    for (const a of e.aneis) linha(a, eh ? "#ffffff" : noite ? "#7d89a8" : "#7b7466", (eh ? HD : H) + T * 0.0002, eh ? 1 : 0.85);
  }
  // condados de Nevada (linhas finas em cima do estado): detalhe que aparece no zoom
  if (destaque === "32") for (const c of Object.values(DADOS.condados_nv)) for (const a of c.aneis) linha(a, "#e9fffb", HD + T * 0.0003, 0.45);
  // Canadá e México (Natural Earth) mais baixos e neutros; o mar por baixo
  const base = PAISES as unknown as Record<string, { aneis: Anel[] }>;
  const viz: THREE.Shape[] = [];
  for (const iso of ["CAN", "MEX", "CUB", "BHS"]) for (const a of base[iso]?.aneis ?? []) {
    const c = a[0];
    if (c[1] < 15 || c[1] > 62 || c[0] < -135 || c[0] > -55) continue;
    viz.push(forma(a));
  }
  if (viz.length) plano.add(new THREE.Mesh(new THREE.ExtrudeGeometry(viz, { depth: H * 0.4, bevelEnabled: false, curveSegments: 1 }), mat(noite ? "#20263a" : "#e9e7e1")));
  const corMar = o.mar ?? (noite ? "#0f1a33" : "#9cc9e6");
  const mar = new THREE.Mesh(new THREE.PlaneGeometry(T * 12, T * 12), mat(corMar, { emissive: corMar, emissiveIntensity: noite ? 0.2 : 0.35, roughness: 1 }));
  mar.rotation.x = -Math.PI / 2;
  mar.position.y = -0.01;
  mar.userData.foraDoEnquadro = true;
  g.add(mar);

  const ponto = (lat: number, lon: number, alt = H) => { const p = proj(lon, lat); return new THREE.Vector3(p.x, alt, -p.y); };
  const topo = (cod: string) => (cod === destaque ? HD : H);
  // nomes: estado destacado grande; vizinhos e países menores; oceano em itálico claro
  const nomes = o.nomes ?? ["32", "06", "41", "16", "49", "04"];
  for (const cod of nomes) {
    const info = ESTADOS_EUA[cod];
    if (!info) continue;
    const eh = cod === destaque;
    const t = textoNoChao(info.nome, T * (eh ? 0.034 : 0.019), { cor: eh ? "#ffffff" : noite ? "#c9d2ea" : "#4d4639", contorno: eh ? "#0d5f58" : undefined, peso: eh ? 900 : 800, opacidade: eh ? 1 : 0.9 });
    t.position.copy(ponto(info.lat, info.lon, topo(cod) + T * 0.0006));
    g.add(t);
  }
  const extra = (texto: string, lat: number, lon: number, alt: number, cor: string, opac = 0.8, peso = 700) => {
    const t = textoNoChao(texto, alt, { cor, opacidade: opac, peso, espaco: 0.3 });
    t.position.copy(ponto(lat, lon, H + T * 0.0006));
    g.add(t);
  };
  if (o.nomePais !== false) extra("ESTADOS UNIDOS", 39.6, -96.8, T * 0.032, noite ? "#aab4d0" : "#6f6656", 0.55, 900);
  extra("CANADÁ", 51.5, -104, T * 0.022, noite ? "#7f88a6" : "#9a978d", 0.8);
  extra("MÉXICO", 27.5, -104.5, T * 0.022, noite ? "#7f88a6" : "#9a978d", 0.8);
  extra("OCEANO PACÍFICO", 35.0, -127.2, T * 0.016, noite ? "#6f8fc4" : "#3f7fae", 0.85, 600);

  // cidades: ponto branco com aro escuro e nome; a do vídeo em amarelo, maior, com halo
  const areas: MapaEUA["userData"]["areas"] = {};
  const lista = o.cidades ?? Object.keys(CIDADES_EUA);
  for (const chave of lista) {
    const c = CIDADES_EUA[chave];
    if (!c) continue;
    const eh = chave === cidade;
    const r = T * (eh ? 0.0042 : 0.0024);
    const p = ponto(c.lat, c.lon, topo(c.estado));
    const aro = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.45, r * 1.45, T * 0.0006, 32), new THREE.MeshBasicMaterial({ color: eh ? "#16306b" : "#3a3a3a", toneMapped: false }));
    aro.position.copy(p).add(new THREE.Vector3(0, T * 0.0003, 0));
    const miolo = new THREE.Mesh(new THREE.CylinderGeometry(r, r, T * 0.0012, 32), new THREE.MeshBasicMaterial({ color: eh ? "#ffd23f" : "#ffffff", toneMapped: false }));
    miolo.position.copy(p).add(new THREE.Vector3(0, T * 0.0006, 0));
    g.add(aro, miolo);
    if (eh) {
      const halo = new THREE.Mesh(new THREE.RingGeometry(r * 1.75, r * 2.05, 48), new THREE.MeshBasicMaterial({ color: "#ffd23f", transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false }));
      halo.rotation.x = -Math.PI / 2;
      halo.position.copy(p).add(new THREE.Vector3(0, T * 0.0007, 0));
      g.add(halo);
      // nível "cidade": o sul de Nevada com as divisas de Califórnia e Arizona e as cidades grandes em volta (Los Angeles,
      // Phoenix): perto o bastante para Las Vegas ser o assunto, longe o bastante para o mapa continuar mapa
      areas.cidade = { centro: p.clone(), tamanho: T * 0.16 };
    } else {
      const t = textoNoChao(c.nome, T * 0.0085, { cor: noite ? "#ffffff" : "#2b2b2b", contorno: noite ? "#000000" : "#ffffffcc", peso: 800 });
      const lt = (t.geometry as THREE.PlaneGeometry).parameters.width;
      t.position.copy(p).add(new THREE.Vector3(lt / 2 + r * 2.2, T * 0.0009, 0)); // nome à direita do ponto (Reno e Carson City ficam a 40 km)
      g.add(t);
    }
  }
  // áreas para a câmera: país, estado destacado e a cidade
  const caixa = (aneis: Anel[], alt: number) => {
    const ps = aneis.flat().map(([x, y]) => proj(x, y));
    const a0 = Math.min(...ps.map((v) => v.x)), a1 = Math.max(...ps.map((v) => v.x)), b0 = Math.min(...ps.map((v) => v.y)), b1 = Math.max(...ps.map((v) => v.y));
    return { centro: new THREE.Vector3((a0 + a1) / 2, alt, -(b0 + b1) / 2), tamanho: Math.max(a1 - a0, b1 - b0) };
  };
  areas.pais = caixa(Object.values(DADOS.estados).flatMap((e) => e.aneis), H);
  areas.estado = caixa(DADOS.estados[destaque]?.aneis ?? [], HD);
  areas.cidade ??= { ...areas.estado };
  g.userData = { ponto: (lat: number, lon: number) => ponto(lat, lon, HD + T * 0.0012), areas };
  return g;
}

/** Câmera que vai de uma área do mapa a outra (país → estado → cidade) sem "pular": `k` de 0 a 1 percorre a lista
 *  `niveis` (padrão ["pais", "estado", "cidade"]); o tamanho enquadrado muda em escala logarítmica (zoom constante) e o
 *  centro desliza junto. `de` = direção da câmera (padrão: de cima, levemente de frente). Devolve a largura (m) que está
 *  no quadro: use para escalar o alfinete (`pino.scale.setScalar(largura * 0.035)`). Funciona com `criarMapaEUA` e
 *  `criarMapaBrasil`. */
export function zoomNoMapa(w: Mundo, mapa: THREE.Object3D, k: number, niveis: string[] = ["pais", "estado", "cidade"], o: { de?: [number, number, number]; lente?: number; folga?: number } = {}) {
  mapa.updateMatrixWorld(true);
  const ar = (mapa as MapaEUA).userData.areas;
  const lista = niveis.map((n) => ar[n] ?? ar.pais);
  const u = Math.max(0, Math.min(1, k)) * (lista.length - 1);
  const i = Math.min(lista.length - 2, Math.floor(u));
  const s = lista.length > 1 ? u - i : 0;
  const a = lista[Math.max(0, i)], b = lista[Math.min(lista.length - 1, i + 1)];
  const sv = s * s * (3 - 2 * s);
  const tam = Math.exp(Math.log(a.tamanho) + (Math.log(b.tamanho) - Math.log(a.tamanho)) * sv);
  // o centro anda na proporção do zoom (o ponto de destino não escapa do quadro no meio do caminho)
  const den = Math.log(b.tamanho) - Math.log(a.tamanho);
  const sc = Math.abs(den) > 1e-6 ? (Math.log(tam) - Math.log(a.tamanho)) / den : sv;
  const centro = mapa.localToWorld(a.centro.clone().lerp(b.centro, sc));
  const larg = tam * mapa.scale.x * (o.folga ?? 1.25);
  const lente = o.lente ?? 40;
  const dir = new THREE.Vector3(...(o.de ?? [0, 1, 0.32])).normalize();
  const tv = Math.tan((lente * Math.PI) / 360);
  const d = larg / 2 / (tv * w.cam.aspect);
  const p = centro.clone().addScaledVector(dir, d);
  camera(w, [p.x, p.y, p.z], [centro.x, centro.y, centro.z], lente);
  return larg;
}
