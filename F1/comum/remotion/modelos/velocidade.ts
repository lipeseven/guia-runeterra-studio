// Sensação de velocidade nas cenas de pista (pedido do Felipe, 2026-11-21: "o carro parece que está a 30 km/h quando devia
// estar a 300. Vale para TODA parte do vídeo que tem pista").
//
// Medido (F1/vertical/docs/api_cenas.md, "Velocidade"): a velocidade do carro era a real (0,014 da volta/s = 87 m/s em Las
// Vegas), mas o quadro quase não se mexia: a câmera acompanha o carro (ele fica parado na tela), o asfalto é uma cor lisa
// (nada nele "corre"), o muro é contínuo e os objetos perto da pista são raros (poste a cada 45 m = um a cada 0,5 s).
// Fluxo óptico médio do quadro ~1-3 px/quadro, contra ~6 da cena POV (a que o Felipe achou mais rápida).
//
// O sistema liga sozinho quando o plano chama `poeNoCircuito`/`transito`/`pelotao` (carro na pista) ou
// `filmar`/`perseguir`/`filmarVariado` (câmera de pista), e só com a câmera a menos de ~90 m do chão:
//  - pistas visuais: postes do alambrado a cada 3 m, painéis vermelho/branco de 2 m no pé do muro, juntas e remendos no
//    asfalto (instanciados: 4 chamadas de desenho para a volta inteira; sem sombra);
//  - lente que abre um pouco e tremor leve, proporcionais à velocidade, só em câmera perto do carro (filmar/perseguir);
//  - borrão de movimento por acúmulo de subquadros (o plano é desenhado de novo em instantes um pouco antes; a média é o
//    quadro, como o obturador de 180° de uma câmera de cinema). Custo = N vezes o desenho do quadro.
// Fora disso (estúdio, mapas, circuito visto do alto) nada muda. Opt-out: `semVelocidade(w)` no plano, ou
// `{ velocidade: false }` nas funções de pista; ajuste fino: `velocidade(w, { borrao, pistas, tremor, lente })`.
import * as THREE from "three";
import { aoRestaurar } from "./desmonte";
import { tempoDoVideo } from "./efeitos3d";
import type { Mundo } from "./mundo";

export type OpcoesVelocidade = {
  /** pistas visuais ao longo da pista (padrão true) */
  pistas?: boolean;
  /** borrão de movimento: false/0/1 = desligado, número = subquadros (padrão 4 acima de 30 m/s) */
  borrao?: boolean | number;
  /** obturador em fração do quadro (padrão 0,5 = 180°) */
  obturador?: number;
  /** força do tremor da câmera (padrão 1; 0 = sem) */
  tremor?: number;
  /** força da lente que abre com a velocidade (padrão 1; 0 = sem) */
  lente?: number;
};

type Estado = {
  circ: THREE.Object3D | null;
  v: number; // maior velocidade (m/s) de carro em pista no quadro
  foco: { x: number; z: number } | null; // carro que a câmera de pista segue (filmar/perseguir)
  camera: boolean; // a câmera veio de filmar/perseguir (lente e tremor só nela)
  desligado: boolean;
  o: OpcoesVelocidade;
};

let atual: Estado | null = null;
const mostradas = new Set<THREE.Object3D>();
aoRestaurar(() => {
  atual = null;
  mostradas.forEach((g) => (g.visible = false));
  mostradas.clear();
});

const novo = (): Estado => ({ circ: null, v: 0, foco: null, camera: false, desligado: false, o: {} });

/** Carro na pista neste quadro (chamado por poeNoCircuito/poePinturaNoCircuito/transito/pelotao). */
export function marcarCarro(circ: THREE.Object3D, v: number, escala = 1) {
  if (escala > 1.5) return; // carro aumentado = vista de longe (mapa): nada de velocidade
  atual ??= novo();
  atual.circ = circ;
  atual.v = Math.max(atual.v, v);
}

/** Maior velocidade (m/s) de carro marcado neste quadro, ou null. */
export const velocidadeMarcada = () => (atual && atual.v > 0 ? atual.v : null);

/** Câmera de pista neste quadro, seguindo o ponto (x, z) do carro (chamado por filmar/perseguir). */
export function marcarCamera(circ: THREE.Object3D, x: number, z: number) {
  atual ??= novo();
  atual.circ = circ;
  atual.camera = true;
  atual.foco = { x, z };
}

/** Desliga o sistema de velocidade neste quadro (cena de pista que deve ficar calma: carro parado, box, explicação). */
export function semVelocidade(_w?: Mundo) {
  atual ??= novo();
  atual.desligado = true;
}

/** Ajusta o sistema de velocidade neste quadro: `{ borrao: 6, obturador: 0.75, tremor: 0, lente: 0, pistas: false }`. */
export function velocidade(_w: Mundo | undefined, o: OpcoesVelocidade) {
  atual ??= novo();
  atual.o = { ...atual.o, ...o };
}

// ------------------------------------------------------------------------------------------------ pistas visuais
type Vestido = { larg: number; bordas: { fora: (i: number) => number; dentro: (i: number) => number } | null };
type InfoCirc = { pontos: THREE.Vector3[]; comprimento: number; pista: THREE.Mesh };

function pistasDe(circ: THREE.Object3D): THREE.Object3D {
  let g = circ.getObjectByName("pistas_velocidade");
  if (g) return g;
  g = criarPistas(circ);
  circ.add(g);
  return g;
}

/** Elementos densos perto da pista para o chão e as laterais "correrem" (paralaxe forte com a câmera baixa). */
function criarPistas(circ: THREE.Object3D) {
  const { pontos, comprimento, pista } = circ.userData.circuito as InfoCirc;
  const ves = (circ.userData.vestido as Vestido | undefined) ?? { larg: 13, bordas: null };
  const N = pontos.length;
  const passo = comprimento / N;
  const amostra = pontos.filter((_, i) => i % 8 === 0);
  const longeDeOutroTrecho = (x: number, z: number, d: number) => {
    let m = Infinity;
    for (const p of amostra) m = Math.min(m, (p.x - x) ** 2 + (p.z - z) ** 2);
    return Math.sqrt(m) > Math.abs(d) * 0.72; // a mesma regra do muro (cenario.ts): nada atravessa outro trecho
  };
  // ponto a `s` metros na volta e `d` metros ao lado (mesma convenção do muro do cenário: x - t.z*d, z + t.x*d)
  const ponto = (s: number, d: (i: number) => number) => {
    const u = s / passo, i = Math.floor(u) % N, fr = u - Math.floor(u);
    const a = pontos[i], b = pontos[(i + 1) % N];
    const t = pontos[(i + 2) % N].clone().sub(pontos[(i - 2 + N) % N]).normalize();
    const dd = d(i);
    return { x: a.x + (b.x - a.x) * fr - t.z * dd, z: a.z + (b.z - a.z) * fr + t.x * dd, giro: Math.atan2(t.x, t.z), dd };
  };
  const g = new THREE.Group();
  g.name = "pistas_velocidade";
  g.visible = false;
  const o3 = new THREE.Object3D();
  const cor = new THREE.Color();
  const inst = (geo: THREE.BufferGeometry, m: THREE.Material, lista: { x: number; y: number; z: number; giro: number; cor?: THREE.Color; sx?: number; sz?: number }[], sombra = false) => {
    const im = new THREE.InstancedMesh(geo, m, Math.max(1, lista.length));
    lista.forEach((q, k) => {
      o3.position.set(q.x, q.y, q.z);
      o3.rotation.set(0, q.giro, 0);
      o3.scale.set(q.sx ?? 1, 1, q.sz ?? 1);
      o3.updateMatrix();
      im.setMatrixAt(k, o3.matrix);
      if (q.cor) im.setColorAt(k, q.cor);
    });
    im.count = lista.length;
    im.castShadow = false;
    im.receiveShadow = sombra;
    im.userData.foraDoEnquadro = true;
    g!.add(im);
    return im;
  };
  const lados: ((i: number) => number)[] = ves.bordas
    ? [(i) => ves.bordas!.fora(i) + 3, (i) => -(ves.bordas!.dentro(i) + 3)]
    : [() => ves.larg * 1.6 / 2 + 3, () => -(ves.larg * 1.6 / 2 + 3)];
  if (ves.bordas) {
    // postes do alambrado a cada 3 m (as linhas verticais perto da câmera são o que mais "passa" na tela)
    const postes: { x: number; y: number; z: number; giro: number }[] = [];
    // painéis de 2 m alternando vermelho e branco no pé do muro (período de 4 m: 87 m/s a 60 q/s = 0,36 período por
    // quadro, abaixo do limite de 0,5 em que o desenho pareceria parado ou andando para trás)
    const paineis: { x: number; y: number; z: number; giro: number; cor: THREE.Color }[] = [];
    const vermelho = new THREE.Color("#c62a2f"), branco = new THREE.Color("#eceae4");
    lados.forEach((d, l) => {
      const s0 = l * 1.3;
      for (let s = s0; s < comprimento; s += 3) {
        const p = ponto(s, (i) => d(i) - Math.sign(d(i)) * 0.18);
        if (longeDeOutroTrecho(p.x, p.z, p.dd)) postes.push({ x: p.x, y: 4.55, z: p.z, giro: p.giro });
      }
      for (let s = 1, k = 0; s < comprimento; s += 2, k++) {
        const p = ponto(s, (i) => d(i) - Math.sign(d(i)) * 0.05);
        if (longeDeOutroTrecho(p.x, p.z, p.dd)) paineis.push({ x: p.x, y: 0.55, z: p.z, giro: p.giro, cor: k % 2 ? branco : vermelho });
      }
    });
    inst(new THREE.BoxGeometry(0.1, 4.1, 0.1), new THREE.MeshStandardMaterial({ color: "#3a3f48", roughness: 0.5, metalness: 0.4 }), postes);
    inst(new THREE.BoxGeometry(0.06, 0.74, 1.94), new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.7 }), paineis);
  } else {
    // circuito sem cenário: balizas brancas e vermelhas na beira do escape, a cada 8 m
    const balizas: { x: number; y: number; z: number; giro: number; cor: THREE.Color }[] = [];
    lados.forEach((d, l) => {
      for (let s = l * 4, k = 0; s < comprimento; s += 8, k++) {
        const p = ponto(s, d);
        if (longeDeOutroTrecho(p.x, p.z, p.dd)) balizas.push({ x: p.x, y: 0.6, z: p.z, giro: p.giro, cor: new THREE.Color(k % 2 ? "#eceae4" : "#c62a2f") });
      }
    });
    inst(new THREE.BoxGeometry(0.22, 1.2, 0.22), new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.6 }), balizas);
  }
  // asfalto: juntas transversais a cada 7 m e remendos (mais escuros e mais claros) a cada ~7 m: é o chão que corre
  const base = new THREE.Color("#4a4f59").multiply((pista.material as THREE.MeshStandardMaterial).color);
  // transparentes: somem aos poucos com a câmera subindo (do alto, remendo e trinca parecem rua estragada)
  const chao = (fator: number, unidades: number) => new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.88, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: fator, polygonOffsetUnits: unidades });
  const juntas: { x: number; y: number; z: number; giro: number; cor: THREE.Color; sx: number }[] = [];
  const escura = base.clone().multiplyScalar(0.4);
  for (let s = 4; s < comprimento; s += 7) {
    const p = ponto(s, () => 0);
    juntas.push({ x: p.x, y: 0.022, z: p.z, giro: p.giro, cor: escura, sx: ves.larg - 0.9 });
  }
  const remendos: { x: number; y: number; z: number; giro: number; cor: THREE.Color; sx: number; sz: number }[] = [];
  let k = 0;
  for (let s = 2; s < comprimento; k++) {
    const r = (n: number) => { const x = Math.sin((k * 7 + n) * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
    const larg = 1.2 + r(1) * 3.6, comp = 0.8 + r(2) * 3.2;
    const lado = (r(3) - 0.5) * Math.max(0, ves.larg - larg - 1.2);
    const p = ponto(s, () => lado);
    remendos.push({ x: p.x, y: 0.021, z: p.z, giro: p.giro, cor: cor.copy(base).multiplyScalar(r(4) < 0.5 ? 0.6 + r(5) * 0.1 : 1.35 + r(5) * 0.25).clone(), sx: larg, sz: comp });
    s += 4 + r(6) * 6;
  }
  const plano = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  inst(plano, chao(-4.5, -9), remendos, true);
  inst(new THREE.PlaneGeometry(1, 0.25).rotateX(-Math.PI / 2), chao(-5, -10), juntas, true);
  // grão do asfalto, selagem de trincas (linhas de betume) e marcas de pneu numa película por cima da pista (a mesma
  // malha da pista com UV ao longo da volta, repetindo a cada 24 m): perto da câmera é isso que "corre" e borra
  const geo = pista.geometry.clone();
  const nv = geo.getAttribute("position").count;
  const uv = new Float32Array(nv * 2);
  for (let v = 0; v < nv; v++) {
    const seg = Math.floor(v / 4), q = v % 4;
    uv[v * 2] = ((seg + (q >= 2 ? 1 : 0)) * passo) / 24;
    uv[v * 2 + 1] = q % 2;
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  geo.deleteAttribute("color");
  const pel = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: texturaAsfalto(), transparent: true, depthWrite: false, roughness: 0.85, polygonOffset: true, polygonOffsetFactor: -4.2, polygonOffsetUnits: -8.5 }));
  pel.receiveShadow = true;
  pel.castShadow = false;
  pel.userData.foraDoEnquadro = true;
  g.add(pel);
  g.userData.chao = g.children.filter((o) => (o as THREE.Mesh).isMesh && ((o as THREE.Mesh).material as THREE.Material).transparent).map((o) => (o as THREE.Mesh).material);
  return g;
}

let texAsfalto: THREE.CanvasTexture | null = null;
/** Película do asfalto (transparente): grão claro e escuro, trincas seladas com betume, manchas de borracha. u = ao longo
 *  da pista (24 m por repetição), v = de uma borda à outra. */
function texturaAsfalto() {
  if (texAsfalto) return texAsfalto;
  const W = 512, H = 2048; // largura = de borda a borda; altura = 24 m (~1,2 cm por pixel)
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const x = c.getContext("2d")!;
  const r = (n: number) => { const s = Math.sin(n * 12.9898 + 78.233) * 43758.5453; return s - Math.floor(s); };
  // grão: pedrinhas claras e escuras
  for (let i = 0; i < 26000; i++) {
    const claro = r(i) < 0.45;
    x.fillStyle = claro ? `rgba(255,255,255,${0.07 + r(i + 1) * 0.13})` : `rgba(0,0,0,${0.18 + r(i + 1) * 0.22})`;
    const e = 2 + r(i + 2) * 4;
    x.fillRect(r(i + 3) * W, r(i + 4) * H, e, e);
  }
  // manchas de borracha e de óleo (ovais largas e suaves)
  for (let i = 0; i < 26; i++) {
    const g = x.createRadialGradient(0, 0, 0, 0, 0, 1);
    g.addColorStop(0, "rgba(0,0,0,0.32)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    x.save();
    x.translate(r(i + 900) * W, r(i + 901) * H);
    x.scale(30 + r(i + 902) * 90, 60 + r(i + 903) * 260);
    x.fillStyle = g;
    x.beginPath();
    x.arc(0, 0, 1, 0, Math.PI * 2);
    x.fill();
    x.restore();
  }
  // trincas seladas: linhas pretas tortas, umas ao longo, outras atravessando (as que mais mostram o chão correndo)
  x.lineCap = "round";
  for (let i = 0; i < 34; i++) {
    const atravessa = i % 3 === 0;
    x.strokeStyle = `rgba(8,8,10,${0.35 + r(i + 500) * 0.25})`;
    x.lineWidth = 2.5 + r(i + 501) * 3.5;
    let px = r(i + 502) * W, py = r(i + 503) * H;
    x.beginPath();
    x.moveTo(px, py);
    const passos = 6 + Math.floor(r(i + 504) * 10);
    for (let k = 0; k < passos; k++) {
      px += atravessa ? 18 + r(i * 31 + k) * 30 : (r(i * 31 + k) - 0.5) * 40;
      py += atravessa ? (r(i * 37 + k) - 0.5) * 30 : 30 + r(i * 37 + k) * 70;
      x.lineTo(px, py);
    }
    x.stroke();
  }
  texAsfalto = new THREE.CanvasTexture(c);
  texAsfalto.colorSpace = THREE.SRGBColorSpace;
  texAsfalto.wrapS = texAsfalto.wrapT = THREE.RepeatWrapping;
  texAsfalto.anisotropy = 8;
  return texAsfalto;
}

// ------------------------------------------------------------------------------------------------ antes de desenhar
const ruido = (t: number, a: number, b: number, c: number) => (Math.sin(t * a) * 0.5 + Math.sin(t * b + 1.7) * 0.3 + Math.sin(t * c + 4.1) * 0.2);

/** Chamado pelo Vertical depois do código do plano e antes de desenhar: mostra as pistas visuais, abre a lente, treme a
 *  câmera e diz quantos subquadros de borrão o quadro leva (`amostras` 1 = sem borrão). */
export function prepararVelocidade(w: Mundo): { amostras: number; obturador: number } {
  const nada = { amostras: 1, obturador: 0 };
  const e = atual;
  if (!e || e.desligado || !e.circ || !e.circ.visible) return nada;
  if (w.cam.position.y > 90) return nada; // circuito visto do alto: nada a fazer
  if (e.o.pistas !== false) {
    const g = pistasDe(e.circ);
    g.visible = true;
    mostradas.add(g);
    // marcas do asfalto: inteiras com a câmera baixa (é aí que elas correm), fracas do alto
    const op = 1 - 0.8 * Math.max(0, Math.min(1, (w.cam.position.y - 3) / 22));
    for (const m of g.userData.chao as THREE.Material[]) m.opacity = op;
  }
  const kv = Math.max(0, Math.min(1, (e.v - 30) / 55)); // 0 abaixo de ~110 km/h, 1 a ~300 km/h
  if (e.camera && e.foco && kv > 0) {
    const cam = w.cam;
    const d = Math.hypot(cam.position.x - e.foco.x, cam.position.y, cam.position.z - e.foco.z);
    const perto = Math.max(0, Math.min(1, (38 - d) / 26)); // câmera perto do carro (alta/heli não treme nem abre)
    const lente = (e.o.lente ?? 1) * 7 * kv * perto;
    if (lente > 0) {
      cam.fov += lente;
      cam.updateProjectionMatrix();
    }
    const tr = (e.o.tremor ?? 1) * kv * perto;
    if (tr > 0) {
      const t = tempoDoVideo();
      cam.rotateX(0.0022 * tr * ruido(t, 61, 83, 131));
      cam.rotateY(0.0016 * tr * ruido(t, 53, 97, 149));
      cam.rotateZ(0.0018 * tr * ruido(t, 47, 71, 113));
    }
  }
  const b = e.o.borrao;
  const amostras = b === false ? 1 : typeof b === "number" ? Math.max(1, Math.round(b)) : e.v > 30 ? 4 : 1;
  return { amostras, obturador: e.o.obturador ?? 0.5 };
}

// ------------------------------------------------------------------------------------------------ borrão de movimento
type Acc = { tex: THREE.FramebufferTexture; rt: THREE.WebGLRenderTarget; cena: THREE.Scene; cam: THREE.OrthographicCamera; soma: THREE.ShaderMaterial; copia: THREE.ShaderMaterial; quad: THREE.Mesh };
const ACC = new WeakMap<Mundo, Acc>();
const VERT = "varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }";

function acc(w: Mundo): Acc {
  let a = ACC.get(w);
  if (a) return a;
  const tam = w.r.getDrawingBufferSize(new THREE.Vector2());
  const tex = new THREE.FramebufferTexture(tam.x, tam.y);
  const rt = new THREE.WebGLRenderTarget(tam.x, tam.y, { type: THREE.HalfFloatType, depthBuffer: false });
  const soma = new THREE.ShaderMaterial({
    uniforms: { mapa: { value: tex }, peso: { value: 1 } }, vertexShader: VERT,
    fragmentShader: "uniform sampler2D mapa; uniform float peso; varying vec2 vUv; void main() { gl_FragColor = vec4(texture2D(mapa, vUv).rgb * peso, 1.0); }",
    depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, transparent: true,
  });
  const copia = new THREE.ShaderMaterial({
    uniforms: { mapa: { value: rt.texture } }, vertexShader: VERT,
    fragmentShader: "uniform sampler2D mapa; varying vec2 vUv; void main() { gl_FragColor = vec4(texture2D(mapa, vUv).rgb, 1.0); }",
    depthTest: false, depthWrite: false,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), soma);
  quad.frustumCulled = false;
  const cena = new THREE.Scene();
  cena.add(quad);
  a = { tex, rt, cena, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1), soma, copia, quad };
  ACC.set(w, a);
  return a;
}

/** Borrão de movimento por acúmulo: o quadro já desenhado na tela + `amostras - 1` subquadros desenhados por
 *  `desenharEm(i)` (o plano refeito um pouco antes no tempo); a média vai para a tela. */
export function borrarMovimento(w: Mundo, amostras: number, desenharEm: (i: number) => void) {
  const a = acc(w);
  const r = w.r;
  const autoClear = r.autoClear;
  const cor = r.getClearColor(new THREE.Color()), alfa = r.getClearAlpha();
  const somar = (i: number) => {
    r.setRenderTarget(null);
    r.copyFramebufferToTexture(a.tex);
    r.setRenderTarget(a.rt);
    if (i === 0) {
      r.setClearColor(0x000000, 0);
      r.clear(true, false, false);
    }
    a.soma.uniforms.peso.value = 1 / amostras;
    a.quad.material = a.soma;
    r.autoClear = false;
    r.render(a.cena, a.cam);
    r.autoClear = autoClear;
    r.setRenderTarget(null);
  };
  somar(0);
  for (let i = 1; i < amostras; i++) {
    desenharEm(i);
    somar(i);
  }
  a.quad.material = a.copia;
  r.setRenderTarget(null);
  r.autoClear = false;
  r.render(a.cena, a.cam);
  r.autoClear = autoClear;
  r.setClearColor(cor, alfa);
}
