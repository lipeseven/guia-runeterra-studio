// Pneu Pirelli de F1 (2026) redesenhado a partir das fotos oficiais em F1/dados/modelos3d/<composto>*.jpg:
// lateral com as marcações exatas (lateral.ts, extraídas das fotos), sulcos do intermediário e do de chuva,
// aro preto de 10 raios. Usado pelas rodas do Carro3D e pelo pneu do estúdio (mundo.tsx).
import * as THREE from "three";
import { ALTURA, CHUVA, LARGURA, RAIO, SLICK } from "./lateral";

/** Cores das marcações, tiradas das fotos (um pouco mais claras: a luz da cena escurece). */
export const CORES_PIRELLI: Record<string, string> = { macio: "#e0343a", medio: "#f2c232", duro: "#f2f0ea", intermediario: "#3aae3e", chuva: "#2f68b0" };

/** Composto pelo nome ou pela cor mais parecida (aceita as cores antigas, ex.: pneuCor do mundo). */
export function compostoDe(c: string): string {
  if (CORES_PIRELLI[c]) return c;
  const alvo = new THREE.Color(c);
  let melhor = "medio";
  let dist = Infinity;
  for (const [nome, cor] of Object.entries(CORES_PIRELLI)) {
    const k = new THREE.Color(cor);
    const d = (k.r - alvo.r) ** 2 + (k.g - alvo.g) ** 2 + (k.b - alvo.b) ** 2;
    if (d < dist) [melhor, dist] = [nome, d];
  }
  return melhor;
}

const molhado = (c: string) => c === "intermediario" || c === "chuva";

const texturas: Record<string, THREE.CanvasTexture> = {};
const pronta = (nome: string, c: HTMLCanvasElement, cor = false) => {
  const t = new THREE.CanvasTexture(c);
  if (cor) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = THREE.RepeatWrapping;
  t.anisotropy = 8;
  texturas[nome] = t;
  return t;
};

/** Marcações da lateral (tinta branca, fundo transparente), decodificadas de lateral.ts. */
function texturaLateral(nome: "slick" | "chuva") {
  if (texturas[nome]) return texturas[nome];
  const c = document.createElement("canvas");
  c.width = LARGURA;
  c.height = ALTURA;
  const x = c.getContext("2d")!;
  const img = x.createImageData(LARGURA, ALTURA);
  (nome === "slick" ? SLICK : CHUVA).split(";").forEach((linha, y) => {
    let p = 0;
    let tinta = false;
    for (const v of linha.split(",")) {
      const n = parseInt(v, 36);
      if (tinta) for (let i = p; i < p + n; i++) img.data.fill(255, (y * LARGURA + i) * 4, (y * LARGURA + i) * 4 + 4);
      p += n;
      tinta = !tinta;
    }
  });
  x.putImageData(img, 0, 0);
  return pronta(nome, c);
}

/** Sulcos da banda (u = volta, v = largura), redesenhados das fotos de 3/4. */
function texturaBanda(nome: "intermediario" | "chuva") {
  const chave = `banda_${nome}`;
  if (texturas[chave]) return texturas[chave];
  const W = 2048;
  const H = 320;
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const x = c.getContext("2d")!;
  x.strokeStyle = "#fff";
  x.lineCap = "round";
  const curva = (pts: number[][], larg: number) => {
    for (const d of [-W, 0, W]) {
      x.lineWidth = larg;
      x.beginPath();
      x.moveTo(pts[0][0] + d, pts[0][1]);
      if (pts.length === 4) x.bezierCurveTo(pts[1][0] + d, pts[1][1], pts[2][0] + d, pts[2][1], pts[3][0] + d, pts[3][1]);
      else x.lineTo(pts[1][0] + d, pts[1][1]);
      x.stroke();
    }
  };
  const lados = (f: (lado: (v: number) => number) => void) => [(v: number) => v * H, (v: number) => (1 - v) * H].forEach(f);
  if (nome === "intermediario") {
    // ganchos longos que saem do ombro e varrem para o centro, alternados entre os lados
    const P = W / 18;
    for (let k = 0; k < 18; k++)
      lados((V) => {
        const u = k * P + (V(0) === 0 ? 0 : P / 2);
        curva([[u, V(0.0)], [u + P * 0.55, V(0.12)], [u + P * 0.95, V(0.3)], [u + P * 1.25, V(0.47)]], 7);
        curva([[u + P * 1.25, V(0.47)], [u + P * 1.45, V(0.5)], [u + P * 1.6, V(0.46)], [u + P * 1.62, V(0.4)]], 7);
        curva([[u + P * 0.5, V(0.0)], [u + P * 0.8, V(0.05)], [u + P * 1.0, V(0.12)], [u + P * 1.1, V(0.2)]], 6);
      });
  } else {
    // chuva extrema: canal central ondulado, sulcos diagonais densos e cortes que formam blocos
    const P = W / 40;
    x.lineWidth = 8;
    x.beginPath();
    for (let u = 0; u <= W; u += 8) x.lineTo(u, H * 0.5 + Math.sin((u / P) * Math.PI) * 4);
    x.stroke();
    for (let k = 0; k < 40; k++)
      lados((V) => {
        const u = k * P;
        curva([[u, V(0.49)], [u + P * 0.5, V(0.32)], [u + P * 1.0, V(0.14)], [u + P * 1.5, V(-0.02)]], 7);
        for (const f of [0.28, 0.62]) {
          const a = u + P * (0.35 + f * 1.1);
          const b = 0.49 - f * 0.5;
          curva([[a, V(b)], [a + P * 0.62, V(b + 0.04)]], 4);
        }
      });
  }
  return pronta(chave, c);
}

const materiais: Record<string, THREE.Material> = {};
const material = (chave: string, criar: () => THREE.Material) => materiais[chave] ?? (materiais[chave] = criar());
const matLateral = (c: string) =>
  material(`lat_${c}`, () => new THREE.MeshStandardMaterial({ color: CORES_PIRELLI[c], map: texturaLateral(molhado(c) ? "chuva" : "slick"), alphaTest: 0.5, roughness: 0.55, side: THREE.DoubleSide }));
const matBanda = (c: string) =>
  material(`banda_${c}`, () => new THREE.MeshStandardMaterial({ color: "#060708", alphaMap: texturaBanda(c as "intermediario" | "chuva"), alphaTest: 0.5, roughness: 0.9 }));

let texAro: THREE.CanvasTexture | null = null;
/** Aro preto de 10 raios retos, borda cinza e cubo escuro com furo (como nas fotos). */
function texturaAro() {
  if (texAro) return texAro;
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const x = c.getContext("2d")!;
  const m = 256;
  x.fillStyle = "#3a3d43";
  x.beginPath();
  x.arc(m, m, 256, 0, Math.PI * 2);
  x.fill();
  x.fillStyle = "#050506";
  x.beginPath();
  x.arc(m, m, 224, 0, Math.PI * 2);
  x.fill();
  x.strokeStyle = "#1f2125";
  x.lineWidth = 9;
  x.beginPath();
  x.arc(m, m, 212, 0, Math.PI * 2);
  x.stroke();
  x.lineCap = "round";
  for (let k = 0; k < 10; k++) {
    const a = (k / 10) * Math.PI * 2;
    for (const [l, cor] of [[26, "#121316"], [12, "#2c2f35"]] as const) {
      x.strokeStyle = cor;
      x.lineWidth = l;
      x.beginPath();
      x.moveTo(m + Math.cos(a) * 62, m + Math.sin(a) * 62);
      x.lineTo(m + Math.cos(a) * 214, m + Math.sin(a) * 214);
      x.stroke();
    }
  }
  x.fillStyle = "#16171a";
  x.beginPath();
  x.arc(m, m, 70, 0, Math.PI * 2);
  x.fill();
  x.fillStyle = "#2a2c31";
  x.beginPath();
  x.arc(m, m, 46, 0, Math.PI * 2);
  x.fill();
  x.fillStyle = "#000";
  x.beginPath();
  x.arc(m, m, 26, 0, Math.PI * 2);
  x.fill();
  texAro = pronta("aro", c, true);
  return texAro;
}

/**
 * Pneu montado no aro, eixo em y (como o LatheGeometry): r = raio externo, l = largura.
 * Peças marcadas: "lateral_pneu" (marcações), "banda_pneu" (sulcos de chuva); trocar com aplicarComposto().
 */
export function pneuPirelli(r: number, l: number, composto = "medio"): THREE.Group {
  const g = new THREE.Group();
  g.name = "pneu_pirelli";
  const h = l / 2;
  const q = Math.min(r * 0.07, h * 0.4); // ombro arredondado
  const ri = r * 0.7; // borda do aro de 18"
  const flanco = (s: number, t: number, fora = 0) => new THREE.Vector2(ri + (r - q - ri) * t, s * (h * (0.84 + 0.16 * Math.sin((t * Math.PI) / 2)) + fora));
  const perfil: THREE.Vector2[] = [];
  for (let k = 0; k <= 10; k++) perfil.push(flanco(-1, k / 10));
  for (let k = 1; k <= 6; k++) {
    const a = (k / 6) * (Math.PI / 2);
    perfil.push(new THREE.Vector2(r - q + q * Math.sin(a), -h + q - q * Math.cos(a)));
  }
  for (let k = 6; k >= 1; k--) {
    const a = (k / 6) * (Math.PI / 2);
    perfil.push(new THREE.Vector2(r - q + q * Math.sin(a), h - q + q * Math.cos(a)));
  }
  for (let k = 10; k >= 0; k--) perfil.push(flanco(1, k / 10));
  const borracha = new THREE.Mesh(new THREE.LatheGeometry(perfil, 96), new THREE.MeshStandardMaterial({ color: "#141518", roughness: 0.72, side: THREE.DoubleSide }));
  borracha.castShadow = true;
  borracha.receiveShadow = true;
  g.add(borracha);
  // marcações: o raio de cada linha da foto vira o mesmo raio no flanco (v = 0 dentro, v = 1 fora)
  const tDe = (rho: number) => Math.min(1, Math.max(0, (rho * r - ri) / (r - q - ri)));
  for (const s of [-1, 1]) {
    const pts = Array.from({ length: 12 }, (_, k) => flanco(s, tDe(RAIO[1] + ((RAIO[0] - RAIO[1]) * k) / 11), r * 0.004));
    const geo = new THREE.LatheGeometry(pts, 192);
    const uv = geo.attributes.uv;
    // as duas laterais leem do lado de fora (uma é o espelho da outra), com o PIRELLI no topo como na foto
    for (let i = 0; i < uv.count; i++) uv.setX(i, s > 0 ? 0.25 - uv.getX(i) : uv.getX(i) + 0.75);
    const lat = new THREE.Mesh(geo, matLateral("medio"));
    lat.name = "lateral_pneu";
    g.add(lat);
    const aro = new THREE.Mesh(new THREE.CircleGeometry(ri, 64), new THREE.MeshStandardMaterial({ map: texturaAro(), metalness: 0.45, roughness: 0.42 }));
    aro.rotation.x = s > 0 ? -Math.PI / 2 : Math.PI / 2;
    aro.position.y = s * h * 0.76;
    g.add(aro);
  }
  const coroa = Array.from({ length: 9 }, (_, k) => new THREE.Vector2(r * 1.002, -(h - q) + ((h - q) * 2 * k) / 8));
  const banda = new THREE.Mesh(new THREE.LatheGeometry(coroa, 192), matBanda("chuva"));
  banda.name = "banda_pneu";
  g.add(banda);
  aplicarComposto(g, composto);
  return g;
}

/** Troca o composto (nome ou cor) de todos os pneus Pirelli dentro de obj. */
export function aplicarComposto(obj: THREE.Object3D, composto: string) {
  const c = compostoDe(composto);
  obj.traverse((o) => {
    if (o.name === "lateral_pneu") (o as THREE.Mesh).material = matLateral(c);
    if (o.name === "banda_pneu") {
      o.visible = molhado(c);
      if (o.visible) (o as THREE.Mesh).material = matBanda(c);
    }
  });
}
