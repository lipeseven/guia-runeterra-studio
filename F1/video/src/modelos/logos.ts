// Logos e texturas de ARQUIVO (2026-11-14): o Felipe põe o arquivo licenciado em F1/arte/logos/ (nome = chave: fia.png =
// "logo:fia"); o Python copia os citados para <trabalho>/logos/ (a pasta pública do render) e passa o mapa nas props
// (`logos`). O Vertical.tsx chama carregarLogos antes de desenhar. Logo sem arquivo vira um cartão cinza com o nome do
// arquivo que falta (o diretor também avisa no card qual arquivo colocar).
import * as THREE from "three";
import { staticFile } from "remotion";

type Item = { img: HTMLImageElement | null; canvas: HTMLCanvasElement; tex: THREE.CanvasTexture; pronto: boolean };
const ITENS = new Map<string, Item>();
let MAPA: Record<string, string> = {};

const chaveDe = (nome: string) => nome.replace(/^logo:/i, "").trim().toLowerCase();

/** Logos disponíveis neste vídeo (chaves). */
export const logosDisponiveis = () => Object.keys(MAPA);

function desenhar(it: Item, chave: string) {
  const cv = it.canvas;
  const g = cv.getContext("2d")!;
  if (it.img && it.img.naturalWidth > 0) {
    const L = 1024;
    const r = it.img.naturalWidth / it.img.naturalHeight;
    cv.width = r >= 1 ? L : Math.max(2, Math.round(L * r));
    cv.height = r >= 1 ? Math.max(2, Math.round(L / r)) : L;
    g.clearRect(0, 0, cv.width, cv.height);
    g.drawImage(it.img, 0, 0, cv.width, cv.height);
    it.pronto = true;
  } else {
    cv.width = 512;
    cv.height = 256;
    g.fillStyle = "#c9ccd2";
    g.fillRect(0, 0, 512, 256);
    g.fillStyle = "#3a3d44";
    g.font = "700 40px 'Segoe UI', sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(`FALTA ${chave}.png`, 256, 128);
  }
  it.tex.image = cv;
  it.tex.needsUpdate = true;
}

function item(chave: string): Item {
  let it = ITENS.get(chave);
  if (!it) {
    const canvas = document.createElement("canvas");
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
    it = { img: null, canvas, tex, pronto: false };
    ITENS.set(chave, it);
    desenhar(it, chave);
  }
  return it;
}

/** Carrega as imagens do mapa {chave: caminho na pasta pública}. Resolve quando todas decodificaram (ou falharam). */
export function carregarLogos(mapa: Record<string, string> = {}): Promise<void> {
  MAPA = { ...MAPA, ...Object.fromEntries(Object.entries(mapa).map(([k, v]) => [chaveDe(k), v])) };
  return Promise.all(
    Object.entries(MAPA).map(async ([k, arq]) => {
      const it = item(k);
      if (it.pronto) return;
      const img = new Image();
      img.src = arq.startsWith("data:") || arq.startsWith("http") ? arq : staticFile(arq);
      try {
        await img.decode();
        it.img = img;
      } catch {
        console.warn(`logo não carregou: ${k} (${arq})`);
      }
      desenhar(it, k);
    }),
  ).then(() => undefined);
}

/** Textura do logo ("fia" ou "logo:fia"). A mesma textura serve o vídeo inteiro. */
export function logo(nome: string): THREE.Texture {
  return item(chaveDe(nome)).tex;
}

/** Proporção largura/altura do logo (1 enquanto não carregou). */
export function proporcaoLogo(nome: string): number {
  const it = item(chaveDe(nome));
  return it.pronto ? it.canvas.width / it.canvas.height : 2;
}

/** Põe o logo como textura numa malha que já existe (painel, placa, capa de qualquer objeto). */
export function aplicarLogo(malha: THREE.Mesh, nome: string, o: { transparente?: boolean } = {}): THREE.Mesh {
  malha.material = new THREE.MeshStandardMaterial({ map: logo(nome), transparent: o.transparente ?? true, roughness: 0.6, metalness: 0.05 });
  return malha;
}

/** Painel com o logo: placa de fundo (cor) com moldura e o logo por cima, de frente para +z. `largura` em metros;
 *  a altura sai da proporção do logo (ou `altura`). Centro do painel na origem; pendure-o com `.position`. */
export function criarPainelLogo(nome: string, o: { largura?: number; altura?: number; fundo?: string; moldura?: string; margem?: number; espessura?: number } = {}): THREE.Group {
  const g = new THREE.Group();
  g.name = `painel_${chaveDe(nome)}`;
  const L = o.largura ?? 2;
  const H = o.altura ?? L / proporcaoLogo(nome);
  const m = o.margem ?? 0.08;
  const e = o.espessura ?? 0.06;
  const fundo = new THREE.Mesh(new THREE.BoxGeometry(L * (1 + m * 2), H + L * m * 2, e), new THREE.MeshStandardMaterial({ color: o.fundo ?? "#ffffff", roughness: 0.7 }));
  fundo.name = "fundo";
  g.add(fundo);
  if (o.moldura) {
    const mold = new THREE.Mesh(new THREE.BoxGeometry(L * (1 + m * 2) + 0.06, H + L * m * 2 + 0.06, e * 0.8), new THREE.MeshStandardMaterial({ color: o.moldura, roughness: 0.5 }));
    mold.position.z = -e * 0.2;
    mold.name = "moldura";
    g.add(mold);
  }
  const face = new THREE.Mesh(new THREE.PlaneGeometry(L, H), new THREE.MeshStandardMaterial({ map: logo(nome), transparent: true, roughness: 0.6, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
  face.position.z = e / 2 + 0.004;
  face.name = "logo";
  g.add(face);
  return g;
}

/** Livro (ex.: livro de regras da FIA) com capa dura colorida, páginas brancas na lateral e o logo na capa (+z = capa,
 *  deitado com `rotation.x = -Math.PI / 2`). Medidas em metros (padrão 0,6 × 0,85 × 0,12: livro grande de cena). */
export function criarLivro(o: { capa?: string; cor?: string; titulo?: string; corTitulo?: string; largura?: number; altura?: number; espessura?: number } = {}): THREE.Group {
  const g = new THREE.Group();
  g.name = "livro";
  const L = o.largura ?? 0.6;
  const H = o.altura ?? 0.85;
  const E = o.espessura ?? 0.12;
  const capaMat = new THREE.MeshStandardMaterial({ color: o.cor ?? "#16306b", roughness: 0.55 });
  const tampa = 0.012;
  for (const z of [E / 2 - tampa / 2, -E / 2 + tampa / 2]) {
    const c = new THREE.Mesh(new THREE.BoxGeometry(L, H, tampa), capaMat);
    c.position.z = z;
    c.name = z > 0 ? "capa" : "contracapa";
    g.add(c);
  }
  const lombada = new THREE.Mesh(new THREE.BoxGeometry(tampa, H, E), capaMat);
  lombada.position.x = -L / 2 + tampa / 2;
  lombada.name = "lombada";
  g.add(lombada);
  const paginas = new THREE.Mesh(new THREE.BoxGeometry(L - 0.02, H - 0.02, E - tampa * 2), new THREE.MeshStandardMaterial({ color: "#f3f1ea", roughness: 0.9 }));
  paginas.position.x = 0.005;
  paginas.name = "paginas";
  g.add(paginas);
  const frente = E / 2 + 0.003;
  if (o.capa) {
    const r = proporcaoLogo(o.capa);
    const lw = Math.min(L * 0.7, H * 0.45 * r);
    const lg = new THREE.Mesh(new THREE.PlaneGeometry(lw, lw / r), new THREE.MeshStandardMaterial({ map: logo(o.capa), transparent: true, roughness: 0.6, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
    lg.position.set(0, o.titulo ? H * 0.12 : 0, frente);
    lg.name = "logo";
    g.add(lg);
  }
  if (o.titulo) {
    const cv = document.createElement("canvas");
    cv.width = 1024;
    cv.height = 256;
    const x = cv.getContext("2d")!;
    x.fillStyle = o.corTitulo ?? "#ffffff";
    x.font = "800 92px 'Segoe UI', sans-serif";
    x.textAlign = "center";
    x.textBaseline = "middle";
    x.fillText(o.titulo, 512, 128, 980);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    const tt = new THREE.Mesh(new THREE.PlaneGeometry(L * 0.86, L * 0.86 / 4), new THREE.MeshStandardMaterial({ map: tex, transparent: true, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
    tt.position.set(0, o.capa ? -H * 0.3 : 0, frente);
    tt.name = "titulo";
    g.add(tt);
  }
  return g;
}
