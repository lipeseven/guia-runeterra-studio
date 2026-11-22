// Caesars Palace (Las Vegas) com a cara dele e o circuito de 1981/82 montado no estacionamento do hotel.
// Pedido do Felipe (2026-11-21): "o Caesars Palace é um bloco bege horrível, sem detalhe" e "a TAG 'estacionamento'
// está totalmente descentralizada". Conferido em fotos do Wikimedia Commons ("Caesars Palace and fountains, Las Vegas -
// April 2026", "Las Vegas, Caesars Palace 01") e na Wikipedia (Caesars Palace; 1981 Caesars Palace Grand Prix):
//  - hoje: torres cor de calcário/creme com pilastras verticais, FRONTÃO triangular no topo com medalhão dourado (coroa de
//    louros) e "CAESARS PALACE" em letras vermelhas com filete dourado; prédio baixo da frente com colunata de colunas
//    brancas de capitel dourado e frontão; lagos turquesa com fontes redondas, ciprestes italianos, estátua de César;
//    letreiro-pilar na esquina da Strip (letras vermelhas, capitéis dourados).
//  - 1981 (original de 1966): torre CURVA (convexa para a frente), 14 andares, recuada da Strip, com alas em arcada
//    curvando para a frente, alameda de ciprestes e fontes no meio (as torres altas com frontão são de 1997 em diante).
// O circuito do estacionamento segue o mesmo desenho do plano do vídeo (o Felipe vai trazer um modelo de referência:
// quando o arquivo chegar em F1/dados/modelos3d, ele substitui o traçado/terreno aqui, pela regra "material vira peça").
import * as THREE from "three";
import CIRCUITOS from "./geo/circuitos.json";
import { obj, rotulo } from "./extras";
import type { Mundo } from "./mundo";

const CREME = "#e9dcc2";
const BRANCO = "#f3eee3";
const OURO = "#c9a24a";
const VERMELHO = "#c41a2b";
const VIDRO = "#4b5a6c";
const AGUA = "#38c4cf";
const CIPRESTE = "#2c4a2c";

const mat = (cor: string, extra: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.75, metalness: 0, ...extra });
const caixa = (l: number, a: number, p: number, m: THREE.Material, x = 0, y = 0, z = 0) => {
  const o = new THREE.Mesh(new THREE.BoxGeometry(l, a, p), m);
  o.position.set(x, y, z);
  return o;
};
const canvas = (l: number, a: number) => {
  const cv = document.createElement("canvas");
  cv.width = l;
  cv.height = a;
  return [cv, cv.getContext("2d")!] as const;
};
const textura = (cv: HTMLCanvasElement, rx = 1, ry = 1) => {
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rx, ry);
  return t;
};

/** "CAESARS PALACE" em letras romanas vermelhas com filete dourado (fundo transparente ou da cor dada). */
function texturaLetreiro(texto = "CAESARS PALACE", fundo = "") {
  const [cv, g] = canvas(2048, 256);
  if (fundo) {
    g.fillStyle = fundo;
    g.fillRect(0, 0, 2048, 256);
  }
  let tam = 190;
  const fonte = () => `700 ${tam}px 'Trajan Pro', 'Cinzel', 'Times New Roman', Georgia, serif`;
  g.font = fonte();
  while (g.measureText(texto).width > 1900 && tam > 40) { tam -= 6; g.font = fonte(); }
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.lineJoin = "round";
  g.strokeStyle = OURO;
  g.lineWidth = tam * 0.09;
  g.strokeText(texto, 1024, 132);
  g.fillStyle = VERMELHO;
  g.fillText(texto, 1024, 132);
  return textura(cv);
}

/** Medalhão dourado com coroa de louros (o "C" do Caesars dentro). */
function texturaMedalhao() {
  const [cv, g] = canvas(256, 256);
  g.fillStyle = OURO;
  g.beginPath(); g.arc(128, 128, 120, 0, Math.PI * 2); g.fill();
  g.strokeStyle = "#8a6a22"; g.lineWidth = 8;
  g.beginPath(); g.arc(128, 128, 104, 0, Math.PI * 2); g.stroke();
  g.fillStyle = "#f1d58a";
  for (let i = 0; i < 18; i++) { // folhas de louro em volta
    const a = Math.PI * 0.62 + (i / 17) * Math.PI * 1.76;
    g.save(); g.translate(128 + Math.cos(a) * 84, 128 + Math.sin(a) * 84); g.rotate(a + Math.PI / 2);
    g.beginPath(); g.ellipse(0, 0, 7, 16, 0.5, 0, Math.PI * 2); g.fill(); g.restore();
  }
  g.fillStyle = VERMELHO; g.font = "700 110px 'Times New Roman', Georgia, serif"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText("C", 128, 134);
  return textura(cv);
}

/** Fachada das torres de hoje: pilastras creme entre faixas de janelas de vidro azulado (uma célula = 1 andar × 1 vão). */
function texturaTorre(noite: boolean) {
  const [cv, g] = canvas(128, 128);
  g.fillStyle = CREME; g.fillRect(0, 0, 128, 128);
  g.fillStyle = noite ? "#f4c77a" : VIDRO; g.fillRect(26, 22, 76, 84);
  g.fillStyle = noite ? "#c98c3a" : "#3a4757"; g.fillRect(26, 22, 76, 10);
  g.fillStyle = "#d8c9ab"; g.fillRect(0, 110, 128, 18); // peitoril
  g.fillStyle = "#f6eedd"; g.fillRect(0, 0, 14, 128); g.fillRect(114, 0, 14, 128); // pilastras
  return cv;
}

/** Fachada da torre original (1966): parede branca com janelas em ARCO, andar por andar. */
function texturaArcos(noite: boolean) {
  const [cv, g] = canvas(128, 128);
  g.fillStyle = BRANCO; g.fillRect(0, 0, 128, 128);
  g.fillStyle = noite ? "#f0c27a" : "#3d4a5c";
  g.beginPath(); g.moveTo(24, 118); g.lineTo(24, 52); g.arc(64, 52, 40, Math.PI, 0); g.lineTo(104, 118); g.closePath(); g.fill();
  g.strokeStyle = "#d9d1c0"; g.lineWidth = 6; g.stroke();
  g.fillStyle = "#e2dacb"; g.fillRect(0, 120, 128, 8);
  return cv;
}

/** Frontão triangular (prisma) com medalhão e cornija; base de largura `l`, altura `a`, profundidade `p`. */
function frontao(l: number, a: number, p: number, cor = CREME, medalhao = true) {
  const g = new THREE.Group();
  const s = new THREE.Shape([new THREE.Vector2(-l / 2, 0), new THREE.Vector2(l / 2, 0), new THREE.Vector2(0, a)]);
  const tri = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: p, bevelEnabled: false }), mat(cor));
  tri.position.z = -p / 2;
  g.add(tri, caixa(l * 1.04, a * 0.12, p * 1.06, mat("#f5ecd8"), 0, -a * 0.06, 0));
  if (medalhao) {
    const m = new THREE.Mesh(new THREE.CircleGeometry(a * 0.3, 40), new THREE.MeshStandardMaterial({ map: texturaMedalhao(), metalness: 0.5, roughness: 0.35 }));
    m.position.set(0, a * 0.42, p / 2 + 0.05);
    g.add(m);
  }
  return g;
}

/** Placa com o letreiro (plano vertical) de largura `l`. */
function letreiro(l: number, fundo = "") {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(l, l / 8), new THREE.MeshStandardMaterial({ map: texturaLetreiro("CAESARS PALACE", fundo), transparent: !fundo, roughness: 0.5, emissive: "#ffffff", emissiveMap: texturaLetreiro("CAESARS PALACE", fundo), emissiveIntensity: 0.25 }));
  return m;
}

/** Torre de hoje: bloco creme com faixas de janelas, coroa recuada e frontão com medalhão e letreiro nas duas faces. */
function torre(l: number, alt: number, p: number, noite: boolean, comLetreiro = true) {
  const g = new THREE.Group();
  const andares = Math.round(alt / 3.4), vaos = Math.round(l / 3.6), vaosP = Math.round(p / 3.6);
  const fr = new THREE.MeshStandardMaterial({ map: textura(texturaTorre(noite), vaos, andares), roughness: 0.7, emissive: noite ? "#ffffff" : "#000000", emissiveMap: noite ? textura(texturaTorre(true), vaos, andares) : null, emissiveIntensity: noite ? 0.35 : 0 });
  const la = new THREE.MeshStandardMaterial({ map: textura(texturaTorre(noite), vaosP, andares), roughness: 0.7 });
  const liso = mat(CREME);
  const corpo = new THREE.Mesh(new THREE.BoxGeometry(l, alt, p), [la, la, liso, liso, fr, fr]);
  corpo.position.y = alt / 2;
  g.add(corpo);
  // pilastras salientes nas quinas e no meio (a leitura "romana" de longe)
  for (const x of [-l / 2, -l / 6, l / 6, l / 2]) for (const z of [-1, 1]) g.add(caixa(l * 0.06, alt, 0.8, mat("#f6eedd"), x, alt / 2, z * (p / 2 + 0.3)));
  // coroa: andar recuado liso + cornija + frontão
  const hc = alt * 0.1;
  g.add(caixa(l * 0.92, hc, p * 0.92, liso, 0, alt + hc / 2, 0), caixa(l * 1.02, 1.2, p * 1.04, mat("#f5ecd8"), 0, alt + 0.6, 0));
  const f = frontao(l * 0.92, l * 0.26, p * 0.9);
  f.position.y = alt + hc;
  g.add(f);
  if (comLetreiro) for (const s of [-1, 1]) {
    const lt = letreiro(l * 0.7);
    lt.position.set(0, alt + hc * 0.5, s * (p * 0.46 + 0.08));
    if (s < 0) lt.rotation.y = Math.PI;
    g.add(lt);
  }
  return g;
}

/** Colunata: `n` colunas brancas de capitel dourado em linha (x), altura `a`, sobre a frente (z). */
function colunata(n: number, passo: number, a: number) {
  const g = new THREE.Group();
  const mc = mat(BRANCO, { roughness: 0.5 });
  const mo = mat(OURO, { metalness: 0.6, roughness: 0.35 });
  const col = new THREE.CylinderGeometry(a * 0.045, a * 0.052, a, 16);
  for (let i = 0; i < n; i++) {
    const x = (i - (n - 1) / 2) * passo;
    const c = new THREE.Mesh(col, mc);
    c.position.set(x, a / 2, 0);
    g.add(c, caixa(a * 0.15, a * 0.08, a * 0.15, mo, x, a - a * 0.04, 0), caixa(a * 0.14, a * 0.04, a * 0.14, mc, x, a * 0.02, 0));
  }
  return g;
}

/** Cipreste italiano (cone alongado verde-escuro). */
function cipreste(h: number) {
  const g = new THREE.Group();
  const c = new THREE.Mesh(new THREE.CapsuleGeometry(h * 0.1, h * 0.75, 4, 10), mat(CIPRESTE, { roughness: 0.95 }));
  c.scale.set(1, 1, 1);
  c.position.y = h * 0.55;
  g.add(c);
  return g;
}

/** Lago com fontes: espelho d'água turquesa, borda de pedra, bacias redondas com jatos brancos. */
function fontes(l: number, p: number, nBacias: number, h: number) {
  const g = new THREE.Group();
  g.add(caixa(l + 1.2, 0.5, p + 1.2, mat("#e8e1d2"), 0, 0.25, 0));
  const agua = caixa(l, 0.12, p, new THREE.MeshStandardMaterial({ color: AGUA, roughness: 0.15, metalness: 0.1, emissive: AGUA, emissiveIntensity: 0.25 }), 0, 0.52, 0);
  g.add(agua);
  const jato = new THREE.MeshStandardMaterial({ color: "#ffffff", transparent: true, opacity: 0.78, roughness: 0.3, emissive: "#dff7ff", emissiveIntensity: 0.35 });
  for (let i = 0; i < nBacias; i++) {
    const x = (i - (nBacias - 1) / 2) * (l / nBacias);
    const r = Math.min(p * 0.36, (l / nBacias) * 0.32);
    const bacia = new THREE.Mesh(new THREE.TorusGeometry(r, 0.18, 8, 40), mat("#5a5f66"));
    bacia.rotation.x = Math.PI / 2;
    bacia.position.set(x, 0.65, 0);
    g.add(bacia);
    const cj = new THREE.Mesh(new THREE.ConeGeometry(r * 0.32, h, 16, 1, true), jato);
    cj.position.set(x, 0.6 + h / 2, 0);
    g.add(cj);
    for (let k = 0; k < 8; k++) { // anel de jatos menores
      const a = (k / 8) * Math.PI * 2;
      const j = new THREE.Mesh(new THREE.ConeGeometry(r * 0.08, h * 0.45, 8, 1, true), jato);
      j.position.set(x + Math.cos(a) * r * 0.7, 0.6 + h * 0.225, Math.sin(a) * r * 0.7);
      g.add(j);
    }
  }
  return g;
}

/** Estátua de César num pedestal (silhueta branca com o braço erguido). */
function estatua(h: number) {
  const g = new THREE.Group();
  const m = mat("#f1efe9", { roughness: 0.6 });
  g.add(caixa(h * 0.45, h * 0.5, h * 0.45, mat("#e2dccd"), 0, h * 0.25, 0));
  const corpo = new THREE.Mesh(new THREE.CapsuleGeometry(h * 0.09, h * 0.32, 4, 10), m);
  corpo.position.y = h * 0.5 + h * 0.25;
  const cab = new THREE.Mesh(new THREE.SphereGeometry(h * 0.065, 14, 10), m);
  cab.position.y = h * 0.5 + h * 0.5;
  const braco = new THREE.Mesh(new THREE.CapsuleGeometry(h * 0.025, h * 0.22, 4, 8), m);
  braco.position.set(h * 0.1, h * 0.5 + h * 0.48, 0);
  braco.rotation.z = -0.5;
  g.add(corpo, cab, braco);
  return g;
}

/** Letreiro-pilar da esquina da Strip: torre fina creme, capitéis dourados, "CAESARS PALACE" nas duas faces. */
function pilarLetreiro(h: number) {
  const g = new THREE.Group();
  const l = h * 0.32;
  g.add(caixa(l, h, l * 0.35, mat(CREME), 0, h / 2, 0));
  g.add(caixa(l * 1.1, h * 0.05, l * 0.42, mat("#f5ecd8"), 0, h * 0.975, 0));
  for (const x of [-1, 1]) g.add(caixa(l * 0.12, h * 0.06, l * 0.4, mat(OURO, { metalness: 0.6, roughness: 0.35 }), x * l * 0.47, h * 0.92, 0));
  const md = new THREE.Mesh(new THREE.CircleGeometry(l * 0.11, 32), new THREE.MeshStandardMaterial({ map: texturaMedalhao(), metalness: 0.5, roughness: 0.35 }));
  for (const s of [-1, 1]) {
    const lt = letreiro(l * 0.95, "#f3ead6");
    lt.position.set(0, h * 0.82, s * (l * 0.175 + 0.05));
    if (s < 0) lt.rotation.y = Math.PI;
    const m2 = md.clone();
    m2.position.set(0, h * 1.03, s * (l * 0.21 + 0.06));
    if (s < 0) m2.rotation.y = Math.PI;
    g.add(lt, m2);
  }
  g.add(caixa(l * 0.86, h * 0.22, 0.2, mat("#1d2433", { emissive: "#24324d", emissiveIntensity: 0.6 }), 0, h * 0.55, l * 0.18)); // telão
  return g;
}

/** Trecho curvo de prédio (cilindro aberto) com a textura de arcos: raio `r`, ângulo `ang` (rad, centrado em +z), altura `h`. */
function curvo(r: number, ang: number, h: number, esp: number, noite: boolean, andares: number) {
  const g = new THREE.Group();
  const vaos = Math.round((r * ang) / 4.2);
  const fr = new THREE.MeshStandardMaterial({ map: textura(texturaArcos(noite), vaos, andares), roughness: 0.7, side: THREE.DoubleSide, emissive: noite ? "#ffffff" : "#000000", emissiveMap: noite ? textura(texturaArcos(true), vaos, andares) : null, emissiveIntensity: noite ? 0.3 : 0 });
  const t0 = -ang / 2; // three: theta 0 = +z
  for (const rr of [r, r - esp]) {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(rr, rr, h, 48, 1, true, t0, ang), fr);
    c.position.y = h / 2;
    g.add(c);
  }
  // anel no plano XY deitado (rotation.x = -90°): y negativo vira +z, então o arco da frente começa em -90° - ang/2
  const teto = new THREE.Mesh(new THREE.RingGeometry(r - esp, r, 48, 1, -Math.PI / 2 - ang / 2, ang), mat(BRANCO, { side: THREE.DoubleSide }));
  teto.rotation.x = -Math.PI / 2;
  teto.position.y = h;
  g.add(teto);
  for (const s of [-1, 1]) { // tampas das pontas
    const a = s * ang / 2;
    const tp = caixa(esp, h, 0.6, mat(BRANCO), Math.sin(a) * (r - esp / 2), h / 2, Math.cos(a) * (r - esp / 2));
    tp.rotation.y = a + Math.PI / 2;
    g.add(tp);
  }
  return g;
}

export type CaesarsPalace = THREE.Group & { userData: { topo: THREE.Vector3; frente: THREE.Vector3; largura: number } };

/** Caesars Palace com a cara real (ver o cabeçalho do arquivo). Frente para +z (a Strip), chão em y = 0, metros.
 *  `epoca`: "atual" (torres com frontão, colunata, lagos e fontes, letreiro-pilar) ou "1981" (torre original curva de
 *  14 andares com janelas em arco, alas em arcada, alameda de ciprestes e fontes; sem as torres de 1997+).
 *  `noite`: janelas acesas. userData: `topo` (ponto alto, para o rótulo), `frente` (meio da fachada), `largura`. */
export function criarCaesarsPalace(o: { epoca?: "atual" | "1981"; noite?: boolean } = {}): CaesarsPalace {
  const g = new THREE.Group() as CaesarsPalace;
  const noite = !!o.noite;
  const piso = mat("#d6cdb9", { roughness: 0.95 });
  if (o.epoca === "1981") {
    g.add(caixa(52, 0.2, 88, piso, 0, 0.1, 52)); // alameda de pedra clara entre a torre e a rua
    // torre original: curva convexa para a frente, 14 andares (~45 m), recuada; alas baixas em arcada curvando para a frente
    const t = curvo(95, 1.15, 45, 17, noite, 14);
    t.position.z = -95 + 10;
    g.add(t);
    const coroa = new THREE.Mesh(new THREE.CylinderGeometry(95.6, 95.6, 1.6, 48, 1, true, -0.58, 1.16), mat("#e6dfcf", { side: THREE.DoubleSide }));
    coroa.position.set(0, 45.8, -85);
    g.add(coroa);
    for (const s of [-1, 1]) {
      const ala = curvo(60, 0.9, 9, 10, noite, 2);
      ala.position.set(s * 62, 0, -28);
      ala.rotation.y = s * 0.95;
      g.add(ala);
    }
    // torre de 1970 (Centurion) atrás, à direita: lâmina reta de 14 andares
    const lam = new THREE.Mesh(new THREE.BoxGeometry(60, 45, 16), new THREE.MeshStandardMaterial({ map: textura(texturaArcos(noite), 14, 14), roughness: 0.7 }));
    lam.position.set(58, 22.5, -48);
    lam.rotation.y = -0.5;
    g.add(lam, caixa(61, 1.4, 17, mat("#e6dfcf"), 58, 45.7, -48));
    g.children[g.children.length - 1].rotation.y = -0.5;
    // pórtico de entrada com colunata e frontão (sob a curva)
    const port = colunata(8, 3.6, 10);
    port.position.set(0, 0, 14);
    g.add(port, caixa(30, 2, 8, mat(BRANCO), 0, 11, 12));
    const fp = frontao(30, 6, 8, BRANCO, true);
    fp.position.set(0, 12, 12);
    g.add(fp);
    const lt = letreiro(24);
    lt.position.set(0, 11, 16.1);
    g.add(lt);
    // alameda central com fontes e ciprestes até a rua
    const f = fontes(18, 70, 4, 7);
    f.rotation.y = Math.PI / 2;
    f.position.set(0, 0, 52);
    g.add(f);
    for (let i = 0; i < 9; i++) for (const s of [-1, 1]) {
      const c = cipreste(11);
      c.position.set(s * 14, 0, 22 + i * 8.5);
      g.add(c);
    }
    const est = estatua(9);
    est.position.set(0, 0, 24);
    g.add(est);
    const pl = pilarLetreiro(26);
    pl.position.set(70, 0, 70);
    pl.rotation.y = -0.35;
    g.add(pl);
    g.userData = { topo: new THREE.Vector3(0, 52, -85 + 95 - 8), frente: new THREE.Vector3(0, 12, 16), largura: 190 };
    return g;
  }
  // hoje: Palace Tower (centro), Augustus (direita), torre média com colunata (esquerda), prédio da frente com colunata
  g.add(caixa(180, 0.2, 60, piso, -5, 0.1, 44)); // praça das fontes
  const t1 = torre(34, 95, 20, noite);
  t1.position.set(-12, 0, -32);
  const t2 = torre(30, 88, 18, noite);
  t2.position.set(48, 0, -42);
  t2.rotation.y = -0.25;
  const t3 = torre(44, 40, 18, noite, false);
  t3.position.set(-62, 0, -18);
  t3.rotation.y = 0.2;
  g.add(t1, t2, t3);
  const frente = caixa(110, 16, 26, mat(CREME), -10, 8, 2);
  g.add(frente, caixa(112, 1.6, 28, mat("#f5ecd8"), -10, 16.8, 2), caixa(100, 10, 0.4, mat(VIDRO), -10, 7, 15.3));
  const col = colunata(16, 6.4, 13);
  col.position.set(-10, 0, 17.5);
  g.add(col, caixa(104, 1.6, 3, mat("#f5ecd8"), -10, 13.8, 17.5));
  const fp = frontao(34, 8, 6);
  fp.position.set(-10, 17.6, 15);
  g.add(fp);
  const lt = letreiro(30);
  lt.position.set(-10, 15.3, 19.1);
  g.add(lt);
  const f = fontes(120, 26, 4, 10);
  f.position.set(-5, 0, 46);
  g.add(f);
  for (let i = 0; i < 11; i++) { const c = cipreste(12); c.position.set(-70 + i * 13, 0, 63); g.add(c); }
  for (const x of [-75, 65]) for (let i = 0; i < 4; i++) { const c = cipreste(12); c.position.set(x, 0, 30 + i * 9); g.add(c); }
  const est = estatua(8);
  est.position.set(-40, 0, 28);
  g.add(est);
  const pl = pilarLetreiro(34);
  pl.position.set(78, 0, 66);
  pl.rotation.y = -0.4;
  g.add(pl);
  g.userData = { topo: new THREE.Vector3(-12, 128, -32), frente: new THREE.Vector3(-10, 14, 19), largura: 190 };
  return g;
}

// ------------------------------------------------------------------------------------------------ estacionamento 1981/82
export type EstacionamentoCaesars = THREE.Group & {
  userData: { cur: THREE.CatmullRomCurve3; pista: THREE.Mesh; bar: THREE.InstancedMesh; NB: number; N: number; hotel: CaesarsPalace;
    alvos: { estacionamento: THREE.Vector3; pista: THREE.Vector3; hotel: THREE.Vector3 } };
};

/** Estacionamento do Caesars Palace com o circuito de 1981/82 (mesmo traçado do plano do vídeo de Las Vegas: retas em
 *  zigue-zague, muretas brancas, vagas pintadas, postes) e o hotel ao lado com a cara real (`criarCaesarsPalace`, época
 *  1981, frente virada para o estacionamento). Medidas no grupo: chão 260 × 180; escale o grupo (o plano usa 0,3).
 *  `revelarEstacionamento(g, k)` desenha pista e muretas até a fração k. `userData.alvos` (local) = centros para
 *  câmera e rótulo: `estacionamento` (meio do traçado, no chão), `pista`, `hotel` (pórtico da frente). Use com `rotuloEm`. */
export function criarEstacionamentoCaesars(o: { epocaHotel?: "1981" | "atual"; entorno?: boolean } = {}): EstacionamentoCaesars {
  const G = new THREE.Group() as EstacionamentoCaesars;
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(260, 180), new THREE.MeshStandardMaterial({ color: "#5a5d63", roughness: 0.95 }));
  chao.rotation.x = -Math.PI / 2;
  G.add(chao);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(1, 1, 1), P = new THREE.Vector3(), E = new THREE.Euler();
  const st = new THREE.InstancedMesh(new THREE.BoxGeometry(0.5, 0.02, 5), new THREE.MeshStandardMaterial({ color: "#eeeadc", polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }), 1100);
  let n = 0;
  for (let z = -72; z <= 72; z += 12) for (let x = -120; x <= 120; x += 3.2) { M.makeTranslation(x, 0.03, z); st.setMatrixAt(n++, M); }
  st.count = n;
  G.add(st);
  // traçado REAL de 1981 (14 curvas, desenho do Felipe: geo/circuitos.json 'caesars_1981'; f 0 = linha de chegada): cabe no estacionamento
  const real = (CIRCUITOS as unknown as Record<string, { pontos: [number, number][] }>).caesars_1981.pontos.slice(0, -1);
  const lat0 = real.reduce((a, q) => a + q[1], 0) / real.length, lon0 = real.reduce((a, q) => a + q[0], 0) / real.length;
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const xy = real.map((q) => [(q[0] - lon0) * kx, -(q[1] - lat0) * 110540]);  // x leste, z sul
  const xs = xy.map((q) => q[0]), zs = xy.map((q) => q[1]);
  const esc = Math.min(215 / (Math.max(...xs) - Math.min(...xs)), 150 / (Math.max(...zs) - Math.min(...zs)));
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cz = (Math.max(...zs) + Math.min(...zs)) / 2;
  const pts = xy.filter((_, i) => i % 2 === 0).map((q) => new THREE.Vector3((q[0] - cx) * esc, 0, (q[1] - cz) * esc));
  const cur = new THREE.CatmullRomCurve3(pts, true, "centripetal");
  const N = 420;
  const pos: number[] = [], idx: number[] = [];
  for (let i = 0; i <= N; i++) {
    const u = i / N, p = cur.getPointAt(u), t = cur.getTangentAt(u), nx = -t.z, nz = t.x;
    pos.push(p.x + nx * 6, 0.06, p.z + nz * 6, p.x - nx * 6, 0.06, p.z - nz * 6);
    if (i < N) { const a = 2 * i; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const gg = new THREE.BufferGeometry();
  gg.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  gg.setIndex(idx);
  gg.computeVertexNormals();
  const pista = new THREE.Mesh(gg, new THREE.MeshStandardMaterial({ color: "#2b2d33", roughness: 0.9, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6 }));
  G.add(pista);
  const NB = 230;
  const bar = new THREE.InstancedMesh(new THREE.BoxGeometry(0.7, 0.9, 2.3), new THREE.MeshStandardMaterial({ color: "#dcd8cc", roughness: 0.8 }), NB * 2);
  for (let j = 0; j < NB; j++) {
    const u = j / (NB - 1), p = cur.getPointAt(u), t = cur.getTangentAt(u), nx = -t.z, nz = t.x;
    Q.setFromEuler(E.set(0, Math.atan2(t.x, t.z), 0));
    for (let s = 0; s < 2; s++) { const sg = s ? 1 : -1; P.set(p.x + nx * 7.6 * sg, 0.45, p.z + nz * 7.6 * sg); M.compose(P, Q, S); bar.setMatrixAt(2 * j + s, M); }
  }
  G.add(bar);
  const mp = new THREE.MeshStandardMaterial({ color: "#8a8d93", roughness: 0.6 });
  const ml = new THREE.MeshStandardMaterial({ color: "#fff6d8", emissive: "#fff1c0", emissiveIntensity: 0.6 });
  for (const x of [-100, -30, 40, 110]) for (const z of [-62, 66]) {
    const po = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.4, 14, 10), mp);
    po.position.set(x, 7, z);
    const la = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.5, 1.2), ml);
    la.position.set(x, 14.2, z);
    G.add(po, la);
  }
  // o hotel a oeste do estacionamento, com a frente (curva, fontes, ciprestes) virada para ele (+x)
  const hotel = criarCaesarsPalace({ epoca: o.epocaHotel ?? "1981" });
  hotel.rotation.y = Math.PI / 2;
  hotel.position.set(-205, 0, 0);
  hotel.scale.setScalar(0.85);
  G.add(hotel);
  hotel.updateMatrix();
  const frenteHotel = hotel.userData.frente.clone().applyMatrix4(hotel.matrix);
  if (o.entorno !== false) entornoDoEstacionamento(G);
  // centro do traçado (caixa dos pontos da curva): é aqui que o rótulo "ESTACIONAMENTO" se ancora
  const bb = new THREE.Box3().setFromPoints(cur.getSpacedPoints(200));
  const meio = bb.getCenter(new THREE.Vector3());
  G.userData = { cur, pista, bar, NB, N, hotel, alvos: { estacionamento: new THREE.Vector3(meio.x, 0, meio.z), pista: meio.clone(), hotel: frenteHotel } };
  return G;
}


/** Entorno do estacionamento (2026-11-21, Felipe: "o Caesars está jogado no meio do nada"): terreno de deserto até o
 *  horizonte, calçada e meio-fio, cerca, carros estacionados nas bordas, a Strip (avenida de 6 faixas com carros) ao sul,
 *  prédios vizinhos de Las Vegas ao norte/leste (janelas acesas, aresta de neon), palmeiras, montanhas ao fundo. Tudo em
 *  coordenadas do grupo (chão 260 × 180); instanciado para ser leve. `entorno: false` volta ao chão solto de antes. */
function entornoDoEstacionamento(G: THREE.Group) {
  let sem = 7;
  const rnd = () => ((sem = (sem * 16807) % 2147483647) / 2147483647);
  // deserto até o horizonte (por baixo do chão do estacionamento)
  const deserto = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), mat("#7f6e55", { roughness: 1 }));
  deserto.rotation.x = -Math.PI / 2;
  deserto.position.y = -0.15;
  G.add(deserto);
  // calçada e meio-fio em volta do estacionamento
  const cal = mat("#b9b5aa");
  G.add(caixa(272, 0.5, 6, cal, 0, 0.1, -93), caixa(272, 0.5, 6, cal, 0, 0.1, 93), caixa(6, 0.5, 186, cal, 133, 0.1, 0));
  // cerca baixa de tela ao norte e a leste
  const cerca = mat("#7c8088", { metalness: 0.5 });
  for (const [x, z, l, r] of [[0, -97, 262, 0], [136, 0, 190, Math.PI / 2]] as const) {
    const f = caixa(l, 3.2, 0.2, cerca, x, 1.7, z); f.rotation.y = r; G.add(f);
  }
  // Strip: avenida a sul (z 118..160) com faixas e carros em movimento parado no quadro
  const av = mat("#25272c", { roughness: 0.9 });
  G.add(caixa(1800, 0.1, 44, av, 0, 0.0, 128));
  const marca = mat("#e9e4cf");
  for (let x = -880; x < 880; x += 12) for (const zz of [117, 122.5, 128, 133.5, 139]) G.add(caixa(5, 0.06, 0.35, marca, x, 0.06, zz));
  const amar = mat("#e0b83a");
  G.add(caixa(1800, 0.07, 0.4, amar, 0, 0.07, 126.6), caixa(1800, 0.07, 0.4, amar, 0, 0.07, 129.4));
  // carros: instâncias de uma carroceria simples, em cores variadas (estacionados e na Strip)
  const cores = ["#c8c8cc", "#1f2430", "#9b1c26", "#2c4f8f", "#e8e4da", "#3b3f46", "#d9a521"];
  const carro = (n: number) => {
    const m = new THREE.InstancedMesh(new THREE.BoxGeometry(4.6, 1.3, 1.9), mat("#ffffff", { roughness: 0.4, metalness: 0.3 }), n);
    const t = new THREE.InstancedMesh(new THREE.BoxGeometry(2.4, 0.9, 1.7), mat("#222a35", { roughness: 0.2 }), n);
    return { m, t, i: 0 };
  };
  const C = carro(260), M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(1, 1, 1), P = new THREE.Vector3(), E = new THREE.Euler(), cor = new THREE.Color();
  const poe = (x: number, z: number, ang: number) => {
    if (C.i >= 260) return;
    Q.setFromEuler(E.set(0, ang, 0));
    M.compose(P.set(x, 0.85, z), Q, S); C.m.setMatrixAt(C.i, M);
    M.compose(P.set(x - Math.cos(ang) * 0.2, 1.75, z + Math.sin(ang) * 0.2), Q, S); C.t.setMatrixAt(C.i, M);
    C.m.setColorAt(C.i, cor.set(cores[Math.floor(rnd() * cores.length)]));
    C.i++;
  };
  for (let x = -124; x <= 124; x += 3.2) { if (rnd() < 0.62) poe(x, -86 + (rnd() - 0.5), Math.PI / 2); if (rnd() < 0.62) poe(x, 86 + (rnd() - 0.5), Math.PI / 2); }
  for (let z = -78; z <= 78; z += 6) if (rnd() < 0.7) poe(124.5, z, 0);
  for (let x = -860; x < 860; x += 17 + rnd() * 20) poe(x, 123 + rnd() * 3.5, rnd() < 0.5 ? 0 : 0);
  for (let x = -860; x < 860; x += 17 + rnd() * 20) poe(x, 132 + rnd() * 3.5, Math.PI);
  C.m.count = C.t.count = C.i;
  G.add(C.m, C.t);
  // prédios vizinhos (janelas acesas e aresta de neon) ao norte, leste e do outro lado da Strip
  const jan = (() => {
    const c = document.createElement("canvas"); c.width = 64; c.height = 128;
    const x = c.getContext("2d")!; x.fillStyle = "#2a2f3c"; x.fillRect(0, 0, 64, 128);
    for (let j = 0; j < 16; j++) for (let i = 0; i < 8; i++) { x.fillStyle = rnd() < 0.55 ? (rnd() < 0.5 ? "#ffd98a" : "#9fd0ff") : "#171b25"; x.fillRect(i * 8 + 1, j * 8 + 1, 5, 5); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const neons = ["#ff3d9a", "#35e0ff", "#ffd23f", "#9b5cff"];
  const predio = (x: number, z: number, l: number, a: number, p: number) => {
    const t = jan.clone(); t.needsUpdate = true; t.repeat.set(Math.max(1, Math.round(l / 28)), Math.max(1, Math.round(a / 32)));
    const b = caixa(l, a, p, new THREE.MeshStandardMaterial({ map: t, emissiveMap: t, emissive: "#ffffff", emissiveIntensity: 0.75, roughness: 0.8 }), x, a / 2, z);
    G.add(b);
    const ne = new THREE.MeshBasicMaterial({ color: neons[Math.floor(rnd() * neons.length)] });
    G.add(caixa(l + 0.6, 0.9, p + 0.6, ne, x, a + 0.45, z));
  };
  for (let x = -700; x <= 760; x += 70 + rnd() * 50) predio(x, -260 - rnd() * 160, 46 + rnd() * 34, 30 + rnd() * 70, 40 + rnd() * 20);
  for (let z = -170; z <= 100; z += 60 + rnd() * 40) predio(270 + rnd() * 50, z, 38 + rnd() * 24, 25 + rnd() * 55, 40 + rnd() * 20);
  for (let x = -760; x <= 760; x += 80 + rnd() * 60) if (Math.abs(x) > 40) predio(x, 215 + rnd() * 40, 50 + rnd() * 30, 25 + rnd() * 60, 44 + rnd() * 20);
  const tronco = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.45, 0.7, 14, 8), mat("#7a5c3a"), 260);
  const copa = new THREE.InstancedMesh(new THREE.ConeGeometry(5.2, 3.6, 8), mat("#3c6b34"), 260 * 2);
  let k = 0;
  const palmeira = (x: number, z: number) => {
    if (k >= 260) return;
    const h = 0.8 + rnd() * 0.4;
    M.compose(P.set(x, 7 * h, z), Q.identity(), S.set(1, h, 1)); tronco.setMatrixAt(k, M);
    M.compose(P.set(x, 14.5 * h, z), Q.identity(), S.set(1.1, 1, 1.1)); copa.setMatrixAt(2 * k, M);
    M.compose(P.set(x, 16 * h, z), Q.identity(), S.set(0.7, 1, 0.7)); copa.setMatrixAt(2 * k + 1, M);
    S.set(1, 1, 1); k++;
  };
  // atrás do hotel (oeste): outros resorts da Strip e uma avenida paralela
  G.add(caixa(46, 0.1, 1400, av, -420, 0.0, 0));
  for (let z = -640; z <= 640; z += 14) G.add(caixa(0.35, 0.06, 6, marca, -420, 0.06, z));
  for (let z = -640; z <= 660; z += 90 + rnd() * 50) { predio(-560 - rnd() * 40, z, 60 + rnd() * 30, 45 + rnd() * 50, 50 + rnd() * 20); predio(-340 - rnd() * 30, z + 40, 40 + rnd() * 20, 18 + rnd() * 30, 40); }
  for (let z = -640; z <= 640; z += 70) { palmeira(-398, z); palmeira(-442, z); }
  // palmeiras ao longo das calçadas e da Strip
  for (let x = -250; x <= 130; x += 24) { palmeira(x, 98 + rnd() * 2); palmeira(x, 106 + rnd() * 2); }
  for (let x = -840; x <= 840; x += 48) if (x < -250 || x > 130) palmeira(x, 106);
  tronco.count = k; copa.count = k * 2;
  G.add(tronco, copa);
  // montanhas do vale ao fundo (silhuetas baixas, marrom-arroxeadas)
  for (let i = 0; i < 22; i++) {
    const a = (i / 22) * Math.PI * 2, r = 880 + rnd() * 60, h = 90 + rnd() * 120, w = 190 + rnd() * 160;
    const mt = new THREE.Mesh(new THREE.ConeGeometry(w, h, 5), mat(i % 2 ? "#6b5a52" : "#7b655a", { roughness: 1 }));
    mt.position.set(Math.cos(a) * r, h / 2 - 2, Math.sin(a) * r);
    mt.rotation.y = rnd() * 3; G.add(mt);
  }
}

/** Desenha a pista e as muretas do estacionamento até a fração `k` (0 a 1) e devolve o ponto (local) da cabeça. */
export function revelarEstacionamento(g: THREE.Object3D, k: number) {
  const u = (g as EstacionamentoCaesars).userData;
  u.bar.count = Math.max(1, Math.floor(u.NB * 2 * k));
  u.pista.geometry.setDrawRange(0, Math.floor(u.N * k) * 6);
  return u.cur.getPointAt(Math.min(0.999, Math.max(0, k)));
}

// ------------------------------------------------------------------------------------------------ rótulo ancorado
/** Rótulo 3D ANCORADO no alvo: fica centralizado em cima dele (no mundo), não em coordenada escrita à mão. `alvo` = um
 *  objeto (centro da caixa dele) ou um ponto LOCAL de `em` (ex.: `g.userData.alvos.estacionamento` com `em: g`, já com
 *  a escala do grupo). `acima` = metros acima do alvo. Cria uma vez por `chave` (como `obj`). A cada quadro,
 *  `conferirRotulos(w)` (chamado pelo Vertical antes de desenhar) confere que o centro projetado do rótulo está a menos
 *  de `margem` (fração da largura do quadro, padrão 0,06) do centro projetado do alvo; senão avisa no console
 *  ("ERRO_ROTULO ...", aparece nos quadros de conferência). Causa do bug de 2026-11-21: o rótulo "ESTACIONAMENTO"
 *  estava em (25, 3, 6) no MUNDO enquanto o traçado estava num grupo encolhido a 0,3 (centro real ≈ (-1, 0, 2)). */
export function rotuloEm(w: Mundo, chave: string, texto: string, alvo: THREE.Object3D | THREE.Vector3, o: { em?: THREE.Object3D; acima?: number; altura?: number; cor?: string; fundo?: string; margem?: number } = {}) {
  const s = obj(w, `rotulo:${chave}`, () => {
    const r = rotulo(texto, { altura: o.altura ?? 2.6, cor: o.cor, fundo: o.fundo });
    r.center.set(0.5, 0); // a base do rótulo fica no ponto (centralizado na horizontal, logo acima do alvo)
    return r;
  });
  const centro = new THREE.Vector3();
  if (alvo instanceof THREE.Vector3) {
    centro.copy(alvo);
    if (o.em) { o.em.updateMatrixWorld(true); o.em.localToWorld(centro); }
  } else {
    alvo.updateMatrixWorld(true);
    new THREE.Box3().setFromObject(alvo).getCenter(centro);
  }
  s.position.copy(centro).add(new THREE.Vector3(0, o.acima ?? 1, 0));
  s.userData.ancora = { alvo: centro.clone(), margem: o.margem ?? 0.06, texto };
  return s;
}

/** Checagem automática: centro projetado de cada rótulo ancorado visível × centro projetado do alvo (na horizontal, em
 *  fração da largura) e rótulo dentro do quadro. Devolve as falhas e escreve "ERRO_ROTULO" no console. */
export function conferirRotulos(w: Mundo): string[] {
  const falhas: string[] = [];
  w.cam.updateMatrixWorld();
  for (const s of w.cena.children) {
    if (!s.visible || !s.userData.ancora) continue;
    const a = s.userData.ancora as { alvo: THREE.Vector3; margem: number; texto: string };
    const pa = a.alvo.clone().project(w.cam);
    const ps = s.position.clone().project(w.cam);
    if (pa.z > 1 || ps.z > 1) continue; // atrás da câmera
    const dx = Math.abs(ps.x - pa.x) / 2; // NDC (-1..1) → fração da largura
    if (dx > a.margem) falhas.push(`"${a.texto}" a ${(dx * 100).toFixed(1)}% da largura do centro do alvo (margem ${(a.margem * 100).toFixed(0)}%)`);
    if (Math.abs(ps.x) > 1 || Math.abs(ps.y) > 1) falhas.push(`"${a.texto}" fora do quadro`);
  }
  for (const f of falhas) console.error(`ERRO_ROTULO ${f}`);
  return falhas;
}
