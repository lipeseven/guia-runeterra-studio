// Desenho do quadro do vertical com o pós-processamento da Las Vegas NOTURNA em neon (pedido do Felipe, 2026-11-21).
// `desenhar(w, t)` substitui `w.r.render(cena, cam)`: se nenhum circuito em neon está visível, desenha EXATAMENTE como antes
// (mesma chamada, nada muda nas outras cenas e vídeos). Com o circuito em neon visível (criarCircuito("lasvegas", {
// cenario: true, noite: true }), padrão), aplica só neste quadro e desfaz depois: céu roxo-magenta, névoa roxa mais longe,
// luz ambiente arroxeada, brilho do traçado conforme a altura da câmera, pulso de luz percorrendo a pista, luzes traseiras
// de LED nos carros (luz de chuva + LEDs das placas da asa traseira) e, no fim, bloom + correção de cor (contraste,
// saturação, sombras arroxeadas e vinheta leve).
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { degradeRadial } from "./Carro3D";
import { pinturaDoCarro, type Mundo } from "./mundo";

type Neon = { escape: THREE.MeshStandardMaterial; pulsos: THREE.MeshBasicMaterial[]; centro: THREE.Vector3 };

const COR = {
  // reduz a saturação/contraste do jeito que a referência pede: escuro, mas luminoso
  ceu: ["#05030f", "#140a33", "#3d1458", "#7a2368"],
  nevoa: "#2a1546",
};

const GRADE = {
  uniforms: { tDiffuse: { value: null }, saturacao: { value: 1.22 }, contraste: { value: 1.06 }, vinheta: { value: 0.32 } },
  vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float saturacao; uniform float contraste; uniform float vinheta; varying vec2 vUv;
    void main() {
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float l = dot(c, vec3(0.299, 0.587, 0.114));
      c = mix(vec3(l), c, saturacao);
      c = (c - 0.5) * contraste + 0.5;
      c += vec3(0.03, 0.0, 0.055) * (1.0 - smoothstep(0.0, 0.3, l)); // sombras puxadas para o roxo (sem preto chapado)
      vec2 d = (vUv - 0.5) * vec2(1.0, 1.35);
      c *= 1.0 - vinheta * smoothstep(0.32, 0.9, length(d));
      gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
    }`,
};

type Estado = { composer: EffectComposer; ceu: THREE.Texture; hemi?: THREE.HemisphereLight };
const ESTADOS = new WeakMap<Mundo, Estado>();

function estado(w: Mundo): Estado {
  let e = ESTADOS.get(w);
  if (e) return e;
  const rt = new THREE.WebGLRenderTarget(1080, 1920, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(w.r, rt);
  composer.setPixelRatio(1);
  composer.setSize(1080, 1920);
  composer.addPass(new RenderPass(w.cena, w.cam));
  // limiar 1 (HDR): só o que é luz de verdade (neon, letreiro, lâmpada, LED) ganha halo
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(1080, 1920), 0.6, 0.42, 1.0));
  composer.addPass(new OutputPass());
  composer.addPass(new ShaderPass(GRADE));
  const c = document.createElement("canvas");
  c.width = 8;
  c.height = 512;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 0, 512);
  [0, 0.3, 0.46, 0.5].forEach((p, k) => g.addColorStop(p, COR.ceu[k]));
  g.addColorStop(1, "#2a0f3a");
  x.fillStyle = g;
  x.fillRect(0, 0, 8, 512);
  const ceu = new THREE.CanvasTexture(c);
  ceu.colorSpace = THREE.SRGBColorSpace;
  const hemi = w.cena.children.find((o) => (o as THREE.HemisphereLight).isHemisphereLight) as THREE.HemisphereLight | undefined;
  e = { composer, ceu, hemi };
  ESTADOS.set(w, e);
  return e;
}

/** Circuito em neon visível neste quadro (ou null). */
export function circuitoNeon(w: Mundo): THREE.Object3D | null {
  for (const o of w.cena.children) if (o.visible && o.userData.neon) return o;
  return null;
}

const suave = (x: number, a: number, b: number) => {
  const k = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return k * k * (3 - 2 * k);
};

let halo: THREE.Texture | null = null;
/** Luzes traseiras de LED do carro de F1 (referência: vídeo do Felipe, 2026-11-21): a luz de chuva vermelha no centro da
 *  traseira, na estrutura de impacto abaixo da asa, e as fitas de LED vermelhas na borda de trás das placas laterais da asa
 *  traseira (carros de 2022 em diante), com halo; mais um filete discreto da cor da equipe na borda do assoalho.
 *  Sem farol, sem seta. Criadas só quando o carro aparece numa cena em neon; fora dela ficam escondidas. */
function luzesTraseiras(k: number) {
  halo ??= degradeRadial("rgba(255,60,40,1)");
  const g = new THREE.Group();
  g.name = "luzes_neon";
  const vermelho = new THREE.MeshBasicMaterial({ color: "#ff2414" });
  vermelho.color.multiplyScalar(2.2); // era 7: o bloom devorava a traseira (Felipe: 'luzes muito iluminadas, tomando conta')
  const caixa = (l: number, a: number, p: number, x: number, y: number, z: number, m: THREE.Material) => {
    const b = new THREE.Mesh(new THREE.BoxGeometry(l, a, p), m);
    b.position.set(x, y, z);
    b.userData.foraDoEnquadro = true; // enquadrar() nunca conta as luzes
    g.add(b);
    return b;
  };
  const brilho = (x: number, y: number, z: number, e: number, op: number) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: halo, color: "#ff3a24", transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false }));
    s.position.set(x, y, z);
    s.scale.set(e, e, 1);
    g.add(s);
  };
  // luz de chuva: quadrado de LED na ponta da estrutura de impacto (no eixo, ~34 cm do chão)
  caixa(0.11, 0.07, 0.012, 0, 0.34, 2.656, vermelho);
  brilho(0, 0.34, 2.68, 0.26, 0.28);
  // LEDs das placas da asa traseira: fita vertical na borda de trás de cada placa
  for (const s of [-1, 1]) {
    caixa(0.026, 0.22, 0.012, s * 0.53, 0.92, 2.717, vermelho);
    brilho(s * 0.53, 0.92, 2.74, 0.18, 0.2);
  }
  // filete da cor da equipe na borda do assoalho (discreto, acende pouco)
  const p = pinturaDoCarro(k);
  const fil = new THREE.MeshBasicMaterial({ color: p.clara });
  fil.color.multiplyScalar(1.6);
  for (const s of [-1, 1]) caixa(0.012, 0.012, 1.6, s * 0.745, 0.11, 0.3, fil);
  g.traverse((o) => (o.castShadow = o.receiveShadow = false));
  return g;
}

function luzesDosCarros(w: Mundo, liga: boolean) {
  w.carros.forEach((c, k) => {
    let l = c.getObjectByName("luzes_neon");
    if (!liga || !c.visible) {
      if (l) l.visible = false;
      return;
    }
    if (!l) c.add((l = luzesTraseiras(k)));
    l.visible = true;
  });
}

/** Desenha o quadro: igual a antes sem neon; com neon, o tratamento da Las Vegas noturna. */
export function desenhar(w: Mundo, t: number) {
  const circ = circuitoNeon(w);
  if (!circ) {
    luzesDosCarros(w, false);
    w.r.render(w.cena, w.cam);
    return;
  }
  const e = estado(w);
  const n = circ.userData.neon as Neon;
  if (!circ.userData.neonPronto) {
    // obj() liga sombra em tudo o que cria: cones, poças, pulso e neon dos prédios não fazem sombra
    circ.traverse((o) => {
      if (o.userData.semSombra) o.castShadow = o.receiveShadow = false;
    });
    circ.userData.neonPronto = true;
  }
  const h = w.cam.position.y;
  const alto = suave(h, 160, 1400); // 0 = na pista, 1 = mapa visto do alto
  // céu, névoa e luz ambiente arroxeados
  const fundo = w.cena.background, nv = w.cena.fog as THREE.Fog;
  const nevoa = { cor: nv.color.clone(), near: nv.near, far: nv.far };
  w.cena.background = e.ceu;
  nv.color.set(COR.nevoa);
  if (h < 400) {
    nv.near = Math.max(nv.near, 140);
    nv.far = Math.max(nv.far, 1700);
  }
  const hemi = e.hemi ? { c: e.hemi.color.clone(), g: e.hemi.groundColor.clone(), i: e.hemi.intensity } : null;
  if (e.hemi) {
    e.hemi.color.set("#8f7bff");
    e.hemi.groundColor.set("#ff4fa8");
    e.hemi.intensity = 0.7;
  }
  const sol = { c: w.sol.color.clone(), i: w.sol.intensity };
  w.sol.color.set("#c9b8ff");
  w.sol.intensity *= 0.8;
  // traçado: de perto só um tom rosado na faixa junto ao muro; do alto, o traçado inteiro em neon
  n.escape.emissiveIntensity = 0.15 + 2.6 * alto;
  n.pulsos.forEach((m, i) => {
    m.map!.offset.x = -t * 0.32;
    m.opacity = i < 2 ? 1 : alto;
  });
  const hor = circ.getObjectByName("neon_horizonte") as THREE.Mesh | undefined;
  if (hor) (hor.material as THREE.MeshBasicMaterial).opacity = 0.6 * (1 - suave(h, 500, 1800));
  luzesDosCarros(w, true);
  const exp = w.r.toneMappingExposure;
  w.r.toneMappingExposure = 1.05;
  e.composer.render();
  // desfaz tudo (o próximo quadro pode ser outra cena)
  w.r.toneMappingExposure = exp;
  w.cena.background = fundo;
  nv.color.copy(nevoa.cor);
  nv.near = nevoa.near;
  nv.far = nevoa.far;
  if (e.hemi && hemi) {
    e.hemi.color.copy(hemi.c);
    e.hemi.groundColor.copy(hemi.g);
    e.hemi.intensity = hemi.i;
  }
  w.sol.color.copy(sol.c);
  w.sol.intensity = sol.i;
}
