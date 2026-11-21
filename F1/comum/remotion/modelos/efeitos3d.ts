// Efeitos 3D dos vídeos informativos: destacar uma peça (ela sai do modelo com brilho), brilho num ponto (ex.: a força
// de frenagem andando de um eixo ao outro), aura elétrica em volta do carro (Boost) e a curva de pista para o carro
// fazer de verdade (entrada, meio e saída). Tudo é refeito a cada quadro.
import * as THREE from "three";
import { achar, aoRestaurar as aoRestaurarEfeitos, deslocar, girarPeca, girarPecaEixo } from "./desmonte";
import { obj, rotulo } from "./extras";
import type { Mundo } from "./mundo";
import { NOMES_FREIOS, girarDisco } from "./freio";

let texBrilho: THREE.CanvasTexture | null = null;
function brilhoTex() {
  if (texBrilho) return texBrilho;
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.25, "rgba(255,255,255,0.55)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
  texBrilho = new THREE.CanvasTexture(c);
  return texBrilho;
}
const sprite = (cor: string) =>
  new THREE.Sprite(new THREE.SpriteMaterial({ map: brilhoTex(), color: cor, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));

/** Brilho (luz colorida) num ponto do mundo: `chave` identifica o brilho; `tam` em metros; `k` 0 a 1 = intensidade. */
export function brilho(w: Mundo, chave: string, pos: THREE.Vector3 | [number, number, number], tam: number, k = 1, cor = "#2ec4b6") {
  const s = obj(w, `brilho:${chave}`, () => sprite(cor));
  s.position.copy(Array.isArray(pos) ? new THREE.Vector3(...pos) : pos);
  s.scale.setScalar(tam);
  (s.material as THREE.SpriteMaterial).opacity = Math.max(0, Math.min(1, k));
  (s.material as THREE.SpriteMaterial).color.set(cor);
  s.renderOrder = 25;
  return s;
}

/** Destaca peças: elas saem para a frente do modelo (+z, `distancia` em metros), crescem um pouco e ganham brilho
 *  atrás. O resto do modelo fica normal (nada de fantasma). k 0 a 1 (anime com suave). */
export function destacar(w: Mundo, modelo: THREE.Object3D, nomes: string | string[], k = 1, distancia = 0.05, cor = "#2ec4b6") {
  for (const nome of Array.isArray(nomes) ? nomes : [nomes]) {
    const p = achar(modelo, nome);
    if (!p) continue;
    deslocar(p, new THREE.Vector3(0, 0, distancia * k), 1 + 0.18 * k);
    modelo.updateMatrixWorld(true);
    const caixa = new THREE.Box3().setFromObject(p);
    const tam = caixa.getSize(new THREE.Vector3()).length();
    const centro = caixa.getCenter(new THREE.Vector3());
    const atras = modelo.localToWorld(modelo.worldToLocal(centro.clone()).add(new THREE.Vector3(0, 0, -0.01)));
    brilho(w, `${modelo.uuid}:${nome}`, atras, tam * 2.4, 0.85 * k, cor);
  }
}

/** Aura elétrica em volta do modelo (ex.: carro no Boost): brilho azul pulsando e faíscas em volta. */
export function aura(w: Mundo, modelo: THREE.Object3D, t: number, k = 1, cor = "#3d9bff") {
  modelo.updateMatrixWorld(true);
  const caixa = new THREE.Box3().setFromObject(modelo);
  const centro = caixa.getCenter(new THREE.Vector3());
  const tam = caixa.getSize(new THREE.Vector3());
  const pulso = 0.75 + 0.25 * Math.sin(t * 9);
  brilho(w, `aura:${modelo.uuid}`, centro, Math.max(tam.x, tam.z) * 1.5, 0.7 * k * pulso, cor);
  for (let n = 0; n < 16; n++) {
    const fase = (t * (1.6 + (n % 5) * 0.3) + n * 0.37) % 1;
    const a = n * 2.399 + t * 2;
    const p = new THREE.Vector3(centro.x + Math.cos(a) * tam.x * 0.55, caixa.min.y + fase * tam.y * 1.4, centro.z + Math.sin(a) * tam.z * 0.5);
    brilho(w, `faisca:${modelo.uuid}:${n}`, p, 0.18 + 0.12 * Math.sin(n), k * Math.sin(fase * Math.PI), n % 3 ? cor : "#ffffff");
  }
}

/** Curva de pista vista de cima (arco), para o carro fazer: centro na origem, `raio` e `largura` em metros, `angulo` em
 *  radianos; com rótulos ENTRADA / MEIO / SAÍDA opcionais. Use `naCurva(curva, f)` para pôr o carro (f 0 a 1). */
export function criarCurva(o: { raio?: number; largura?: number; angulo?: number; rotulos?: string[] } = {}) {
  const raio = o.raio ?? 14;
  const larg = o.largura ?? 4;
  const ang = o.angulo ?? Math.PI * 0.75;
  const g = new THREE.Group();
  const asfalto = new THREE.Mesh(new THREE.RingGeometry(raio - larg / 2, raio + larg / 2, 64, 1, 0, ang), new THREE.MeshStandardMaterial({ color: "#59606e", roughness: 0.9 }));
  asfalto.rotation.x = -Math.PI / 2;
  asfalto.position.y = 0.01;
  asfalto.receiveShadow = true;
  g.add(asfalto);
  for (const r of [raio - larg / 2 - 0.25, raio + larg / 2 + 0.25]) {
    const zebra = new THREE.Mesh(new THREE.RingGeometry(r - 0.25, r + 0.25, 48, 1, 0, ang), new THREE.MeshStandardMaterial({ color: "#e8e8ea", roughness: 0.7 }));
    zebra.rotation.x = -Math.PI / 2;
    zebra.position.y = 0.012;
    g.add(zebra);
  }
  g.userData.curva = { raio, ang };
  (o.rotulos ?? []).forEach((txt, n, todos) => {
    const p = naCurva(g, todos.length === 1 ? 0.5 : n / (todos.length - 1));
    const s = rotulo(txt, { altura: 1.1 });
    s.position.set(p.x * 1.25, 1.2, p.z * 1.25);
    g.add(s);
  });
  return g;
}

/** Ponto e giro do carro na curva (f 0 = entrada, 0,5 = meio, 1 = saída): poe(w, k, p.x, p.z, p.giro). */
export function naCurva(curva: THREE.Object3D, f: number) {
  const { raio, ang } = curva.userData.curva as { raio: number; ang: number };
  curva.updateMatrixWorld(true);
  // RingGeometry deitado: o ângulo θ vai de +x para -z (rotation.x = -π/2 leva y da forma para -z do mundo)
  const th = ang * Math.max(0, Math.min(1, f));
  const local = new THREE.Vector3(Math.cos(th) * raio, 0, -Math.sin(th) * raio);
  const p = curva.localToWorld(local.clone());
  const dir = new THREE.Vector3(-Math.sin(th), 0, -Math.cos(th)).transformDirection(curva.matrixWorld);
  // esterço das rodas dianteiras para essa curva (entre-eixos 3,4 m; positivo = para a esquerda)
  return { x: p.x, z: p.z, giro: Math.atan2(-dir.x, -dir.z), esterco: Math.atan(3.4 / raio) };
}

/** Vira as rodas dianteiras do carro (radianos; positivo = para a esquerda), só neste quadro: na curva use naCurva(...).esterco.
 *  Mexe só no eixo do esterço: a rolagem (rolarRodas) continua, em qualquer ordem de chamada. */
export function estercar(carro: THREE.Object3D, angulo: number) {
  for (const nome of ["roda_dianteira_esquerda", "roda_dianteira_direita"]) {
    const roda = achar(carro, nome)?.children[0];
    if (roda) girarPecaEixo(roda, "y", Math.max(-0.6, Math.min(0.6, angulo)));
  }
  // o conjunto do freio (disco, pinça, tomada de ar) vai preso ao montante: esterça junto com a roda
  for (const nome of ["freio_dianteiro_esquerdo", "freio_dianteiro_direito"]) {
    const f = achar(carro, nome);
    if (f) girarPecaEixo(f, "y", Math.max(-0.6, Math.min(0.6, angulo)));
  }
}

/** Giro das rodas no vídeo (30 q/s): a roda de liga tem 10 raios (um a cada 36°). Acima de ~V_RODA m/s a roda passa de
 *  ~13° por quadro e o desenho (raios, PIRELLI, xadrez) "serrilha": os raios parecem parados ou girando para trás enquanto
 *  a borracha anda (calota "solta" do pneu), ou tudo lê como marcha à ré. O sentido já é o certo; o que muda é a velocidade
 *  VISTA, limitada a V_RODA (13,3° por quadro = 37% do passo dos raios: pneu, aro e calota giram juntos, para a frente).
 *  V_RODA é em m/s (giro por SEGUNDO, ~400°/s): a 60 q/s (vertical) dá 6,7° por quadro, o mesmo giro visto no tempo e
 *  ainda mais longe do serrilhado; não mude para valor por quadro. */
export const V_RODA = 2.5;
/** Segundo do vídeo no quadro que está sendo desenhado (o Vertical.tsx põe antes de cada cena): base do giro das rodas rápidas. */
let tempoAtual: number | null = null;
export const definirTempo = (t: number | null) => {
  tempoAtual = t;
};
const R_RODA = 0.36;
const NOMES_RODAS = ["roda_dianteira_esquerda", "roda_dianteira_direita", "roda_traseira_esquerda", "roda_traseira_direita"];

/** As 4 rodas de um carro da biblioteca rolando (pneu, aro e calota como uma peça só): `metros` = distância andada para a
 *  frente (proporcional: carro parado = rodas paradas). `velocidade` (m/s, opcional): com ela o giro visto fica limitado a
 *  V_RODA. Mexe só no eixo da rolagem: o esterço das dianteiras continua. Chame a cada quadro. */
export function rolarRodas(car: THREE.Object3D, metros: number, velocidade = 0) {
  // Carro rápido: o giro visto é V_RODA m/s, ou seja, uma função do TEMPO do vídeo (não da distância): fica igual quer o
  // carro freie, acelere ou mantenha a velocidade. Antes era distância TOTAL × V_RODA/velocidade: com a velocidade mudando
  // a cada quadro (frenagem), a roda saltava dezenas de graus por quadro (2026-11-13). Não dá para "guardar o giro" do
  // quadro anterior: o Remotion desenha os quadros fora de ordem, em 3 abas. Abaixo de V_RODA = distância real (pit lane).
  const ang = velocidade > V_RODA && tempoAtual !== null ? V_RODA * tempoAtual : velocidade > V_RODA ? (metros * V_RODA) / velocidade : metros;
  for (const nome of NOMES_RODAS) {
    const r = achar(car, nome)?.children[0];
    if (r) girarPecaEixo(r, "x", -ang / R_RODA);
  }
  // Safety Car (e qualquer modelo que guarde as rodas em userData.rodasGiro): o aro e os raios giram com o mesmo ângulo de rolagem
  // (raio de roda de rua 0,355 m). Antes o pedido "as rodas do Safety Car devem girar" era 'atendido' com rolarRodas(w.sc) que não achava nada.
  const rg = (car.userData as { rodasGiro?: THREE.Object3D[] }).rodasGiro;
  if (rg) for (const r of rg) r.rotation.x = -ang / 0.355;
  // o disco gira com a roda (a pinça e as pastilhas não)
  for (const nome of NOMES_FREIOS) {
    const f = achar(car, nome)?.getObjectByName("conjunto_freio");
    if (f) girarDisco(f, -ang / R_RODA);
  }
}
// ---------------------------------------------------------------------------------------------- rodas rápidas (v7)
// Felipe: "o giro das rodas não transmite 300 km/h". A 300 km/h a roda dá ~37 voltas/s: em 60 q/s qualquer desenho
// serrilha (parece parada ou para trás). Como numa câmera de verdade, a face da roda vira um DISCO BORRADO (borrão de
// movimento radial: raios e letras PIRELLI viram anéis contínuos) que gira devagar só para ter vida. Opt-in: só aparece
// no quadro em que o plano chama `rodasRapidas`; nos outros nada muda.
let texBorrao: THREE.CanvasTexture | null = null;
function borraoTex() {
  if (texBorrao) return texBorrao;
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const x = c.getContext("2d")!;
  const m = 256;
  const anel = (r0: number, r1: number, cor: string) => {
    x.beginPath();
    x.arc(m, m, r1 * m, 0, Math.PI * 2);
    x.arc(m, m, r0 * m, 0, Math.PI * 2, true);
    x.fillStyle = cor;
    x.fill();
  };
  anel(0.7, 1.0, "rgba(14,15,18,0.97)"); // flanco do pneu
  anel(0.79, 0.86, "rgba(196,150,40,0.55)"); // letras PIRELLI amarelas viram um anel
  anel(0.9, 0.93, "rgba(196,150,40,0.25)");
  anel(0.0, 0.7, "rgba(40,42,48,0.92)"); // aro: raios borrados viram um disco cinza
  for (let k = 0; k < 40; k++) anel(0.06 + k * 0.016, 0.065 + k * 0.016, `rgba(${k % 2 ? 90 : 20},${k % 2 ? 93 : 22},${k % 2 ? 100 : 26},0.35)`);
  anel(0.0, 0.17, "rgba(12,13,16,0.95)"); // cubo
  // riscos curtos em arco (borrão de movimento)
  x.lineCap = "round";
  for (let k = 0; k < 140; k++) {
    const r = (0.2 + ((k * 37) % 50) / 100) * m;
    const a = (k * 2.399) % (Math.PI * 2);
    x.strokeStyle = `rgba(150,155,165,${0.08 + ((k * 13) % 10) / 100})`;
    x.lineWidth = 2;
    x.beginPath();
    x.arc(m, m, r, a, a + 0.9);
    x.stroke();
  }
  texBorrao = new THREE.CanvasTexture(c);
  texBorrao.colorSpace = THREE.SRGBColorSpace;
  return texBorrao;
}
const discosBorrao = new Set<THREE.Object3D>();
let restauraBorrao = false;
/** Rodas de carro rápido com borrão de movimento (a partir de ~25 m/s, cresce até ~60 m/s). Chame depois de
 *  poeNoCircuito/rolarRodas, a cada quadro. `v` em m/s. */
export function rodasRapidas(car: THREE.Object3D, v: number) {
  if (!restauraBorrao) {
    restauraBorrao = true;
    aoRestaurarEfeitos(() => {
      discosBorrao.forEach((d) => (d.visible = false));
      discosBorrao.clear();
    });
  }
  const k = Math.max(0, Math.min(1, (v - 25) / 35));
  if (k <= 0) return;
  for (const nome of NOMES_RODAS) {
    const roda = achar(car, nome)?.children[0];
    if (!roda) continue;
    let d = roda.getObjectByName("borrao");
    if (!d) {
      d = new THREE.Group();
      d.name = "borrao";
      const s = Math.sign(roda.position.x) || 1;
      const larg = nome.includes("traseira") ? 0.38 : 0.28;
      for (const lado of [1, -1]) {
        const m = new THREE.Mesh(new THREE.CircleGeometry(0.352, 64), new THREE.MeshBasicMaterial({ map: borraoTex(), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
        m.rotation.y = lado * s > 0 ? Math.PI / 2 : -Math.PI / 2;
        m.position.x = lado * s * (larg / 2 + 0.006);
        m.renderOrder = 3;
        d.add(m);
      }
      roda.add(d);
    }
    d.visible = true;
    d.traverse((o) => {
      const mm = (o as THREE.Mesh).material as THREE.MeshBasicMaterial | undefined;
      if (mm) mm.opacity = k;
    });
    discosBorrao.add(d);
  }
}

// ---------------------------------------------------------------------------------------------- realce de peça
// Pedido do Felipe (2026-11-18): "ao invés de uma luz em cima da peça, a peça poderia emitir um brilho". O destaque é a
// PRÓPRIA peça acendendo (material emissivo) com um contorno luminoso (casca empurrada pela normal, só o lado de trás),
// nunca um sprite de luz solto por cima. Volta ao normal sozinho a cada quadro.
const realcados = new Set<THREE.Mesh>();
const emis0 = new WeakMap<THREE.Mesh, { cor: THREE.Color; forca: number }>();
const proprio = new WeakSet<THREE.Mesh>();
const contornos = new WeakMap<THREE.Mesh, THREE.Mesh>();
const VERT_CONTORNO = "uniform float esp; void main(){ vec3 p = position + normal * esp; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }";
const FRAG_CONTORNO = "uniform vec3 cor; uniform float op; void main(){ gl_FragColor = vec4(cor, op); }";
let restauraRealce = false;

/** Acende peças do modelo no lugar: `nomes` = nomes de peça (`peca`, ex.: "halo", "banco", "apoio_cabeca",
 *  "retrovisor_esquerdo") ou de malha ("halo_pilar", "borda_cockpit"); `null` = o modelo inteiro (ex.: o volante).
 *  `k` 0 a 1 (anime com suave); `contorno` = espessura da borda luminosa em metros (0 = só o brilho). */
export function realcar(modelo: THREE.Object3D, nomes: string | string[] | null, k = 1, cor = "#ffd23f", contorno = 0.012) {
  if (!restauraRealce) {
    restauraRealce = true;
    aoRestaurarEfeitos(() => {
      for (const m of realcados) {
        const mt = m.material as THREE.MeshStandardMaterial;
        const e = emis0.get(m);
        if (e && mt.emissive) {
          mt.emissive.copy(e.cor);
          mt.emissiveIntensity = e.forca;
        }
        const c = contornos.get(m);
        if (c) c.visible = false;
      }
      realcados.clear();
    });
  }
  const kk = Math.max(0, Math.min(1, k));
  if (kk <= 0) return;
  const quero = nomes === null ? null : new Set(Array.isArray(nomes) ? nomes : [nomes]);
  const malhas: THREE.Mesh[] = [];
  const junta = (o: THREE.Object3D) => o.traverse((x) => {
    if ((x as THREE.Mesh).isMesh) malhas.push(x as THREE.Mesh);
  });
  if (!quero) junta(modelo);
  else modelo.traverse((o) => {
    if (quero.has(o.userData.peca) || quero.has(o.name)) junta(o);
  });
  const c3 = new THREE.Color(cor);
  for (const m of [...new Set(malhas)]) {
    if (m.userData.contorno) continue;
    const mt0 = m.material as THREE.MeshStandardMaterial;
    if (!mt0 || !mt0.emissive) continue;
    if (!proprio.has(m)) {
      // material próprio (os carros da mesma equipe são clones e acenderiam juntos)
      m.material = mt0.clone();
      proprio.add(m);
    }
    const mt = m.material as THREE.MeshStandardMaterial;
    if (!emis0.has(m)) emis0.set(m, { cor: mt.emissive.clone(), forca: mt.emissiveIntensity });
    mt.emissive.copy(c3);
    mt.emissiveIntensity = 0.85 * kk;
    realcados.add(m);
    if (contorno > 0 && m.geometry.attributes.normal) {
      let ct = contornos.get(m);
      if (!ct) {
        ct = new THREE.Mesh(m.geometry, new THREE.ShaderMaterial({ uniforms: { esp: { value: contorno }, cor: { value: c3.clone() }, op: { value: 1 } }, vertexShader: VERT_CONTORNO, fragmentShader: FRAG_CONTORNO, side: THREE.BackSide, transparent: true, depthWrite: false }));
        ct.userData.contorno = true;
        ct.renderOrder = 5;
        m.add(ct);
        contornos.set(m, ct);
      }
      const u = (ct.material as THREE.ShaderMaterial).uniforms;
      u.esp.value = contorno / Math.max(1e-6, m.getWorldScale(new THREE.Vector3()).x);
      u.cor.value.copy(c3);
      u.op.value = kk;
      ct.visible = true;
    }
  }
}

// ---------------------------------------------------------------------------------------------- campo de visão
let texLeque: THREE.CanvasTexture | null = null;
function lequeTex() {
  if (texLeque) return texLeque;
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, "rgba(255,255,255,0.75)");
  g.addColorStop(0.55, "rgba(255,255,255,0.35)");
  g.addColorStop(0.92, "rgba(255,255,255,0.12)");
  g.addColorStop(1, "rgba(255,255,255,0.0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 256, 256);
  texLeque = new THREE.CanvasTexture(c);
  return texLeque;
}

/** Campo de visão em 3D (pedido do Felipe, 2026-11-18: nada de "feixe de bolinhas"): leque translúcido com degradê (forte
 *  perto do olho, some no fim), bordas e arco luminosos e o volume do olhar (pirâmide de vidro do olho até o arco).
 *  `origem` = olho/espelho no mundo; `para` = ponto no mundo para onde o centro do leque aponta; `graus` = abertura;
 *  `alcance` em metros; `k` 0 a 1 = o leque cresce do olho; `chao` = altura do leque (padrão: a do olho; 0.03 = projetado
 *  no chão, com a linha-guia descendo do olho). `texto` = rótulo curto no fim do leque (só palavra da fala). */
export function campoDeVisao(w: Mundo, chave: string, origem: THREE.Vector3, para: THREE.Vector3, graus: number, alcance: number, k = 1, o: { cor?: string; chao?: number; texto?: string; volume?: boolean } = {}) {
  const kk = Math.max(0, Math.min(1, k));
  const cor = new THREE.Color(o.cor ?? "#38c6ff");
  const g = obj(w, `visao:${chave}`, () => {
    const gr = new THREE.Group();
    const leque = new THREE.Mesh(new THREE.CircleGeometry(1, 64, 0, 1), new THREE.MeshBasicMaterial({ map: lequeTex(), transparent: true, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4, fog: false }));
    leque.name = "leque";
    const borda = new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, fog: false });
    const e1 = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 8), borda);
    e1.name = "e1";
    const e2 = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 8), borda);
    e2.name = "e2";
    const arco = new THREE.Mesh(new THREE.TorusGeometry(1, 1, 6, 64, 1), borda);
    arco.name = "arco";
    const vol = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    vol.name = "vol";
    const guia = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 8), borda);
    guia.name = "guia";
    gr.add(leque, e1, e2, arco, vol, guia);
    gr.traverse((x) => (x.renderOrder = 20));
    return gr;
  });
  if (kk <= 0) {
    g.visible = false;
    return g;
  }
  const altura = o.chao ?? origem.y;
  const ap = new THREE.Vector3(origem.x, altura, origem.z);
  const dir = new THREE.Vector3(para.x - origem.x, 0, para.z - origem.z).normalize();
  const yaw = Math.atan2(-dir.x, -dir.z);
  const meia = ((graus * Math.PI) / 180) / 2;
  const R = alcance * (0.15 + 0.85 * kk);
  const esp = Math.max(0.012, alcance * 0.004);
  const local = (a: number, r: number) => new THREE.Vector3(-Math.sin(yaw + a) * r, 0, -Math.cos(yaw + a) * r).add(ap);
  // leque: setor do círculo (frente = -z), deitado na altura `altura`
  const leque = g.getObjectByName("leque") as THREE.Mesh;
  leque.geometry.dispose();
  const geo = new THREE.CircleGeometry(1, 64, Math.PI / 2 - meia, meia * 2);
  geo.rotateX(-Math.PI / 2);
  leque.geometry = geo;
  leque.position.copy(ap);
  leque.rotation.set(0, yaw, 0);
  leque.scale.set(R, 1, R);
  (leque.material as THREE.MeshBasicMaterial).color.copy(cor);
  (leque.material as THREE.MeshBasicMaterial).opacity = 0.55 * kk;
  // bordas e arco luminosos
  const tubo = (m: THREE.Object3D, a: THREE.Vector3, b: THREE.Vector3, r: number) => {
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    m.scale.set(r, a.distanceTo(b), r);
  };
  tubo(g.getObjectByName("e1")!, ap, local(meia, R), esp);
  tubo(g.getObjectByName("e2")!, ap, local(-meia, R), esp);
  const arco = g.getObjectByName("arco") as THREE.Mesh;
  arco.geometry.dispose();
  // arco: pontos do setor no fim do leque (tubo pela curva)
  const pa: THREE.Vector3[] = [];
  for (let i = 0; i <= 32; i++) pa.push(local(-meia + (2 * meia * i) / 32, R));
  arco.geometry = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pa), 64, esp, 6, false);
  arco.position.set(0, 0, 0);
  arco.quaternion.identity();
  arco.scale.setScalar(1);
  const borda = (g.getObjectByName("e1") as THREE.Mesh).material as THREE.MeshBasicMaterial;
  borda.color.copy(cor).lerp(new THREE.Color("#ffffff"), 0.35);
  borda.opacity = kk;
  // linha-guia do olho até o vértice do leque (quando o leque está no chão)
  const guia = g.getObjectByName("guia")!;
  guia.visible = Math.abs(origem.y - altura) > 0.05;
  if (guia.visible) tubo(guia, origem, ap, esp * 0.8);
  // volume do olhar: pirâmide de vidro do olho até o arco (bem leve)
  const vol = g.getObjectByName("vol") as THREE.Mesh;
  vol.visible = o.volume !== false;
  if (vol.visible) {
    const pts: number[] = [];
    const N = 16;
    for (let i = 0; i < N; i++) {
      const p0 = local(-meia + (2 * meia * i) / N, R), p1 = local(-meia + (2 * meia * (i + 1)) / N, R);
      pts.push(origem.x, origem.y, origem.z, p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
    }
    vol.geometry.dispose();
    const vg = new THREE.BufferGeometry();
    vg.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    vol.geometry = vg;
    (vol.material as THREE.MeshBasicMaterial).color.copy(cor);
    (vol.material as THREE.MeshBasicMaterial).opacity = 0.1 * kk;
  }
  if (o.texto) {
    const r = obj(w, `visao:${chave}:rot`, () => rotulo(o.texto!, { altura: Math.max(0.12, alcance * 0.06), cor: "#ffffff", fundo: "rgba(12,40,80,0.9)" }));
    r.position.copy(local(0, R * 0.92)).setY(altura + Math.max(0.15, alcance * 0.05));
    (r.material as THREE.SpriteMaterial).opacity = kk;
  }
  return g;
}

/** DRS / modo reta: a aba móvel da asa traseira abre (a borda da frente sobe, articulando na de trás) e volta sozinha no
 *  quadro seguinte. `k` 0 fechada (padrão: inclinada para carga aerodinâmica), 1 aberta (~24° a mais: o flap quase deita e abre a
 *  fresta). Combine com `brilho`/`aura` na peça "asa_traseira" para destacar. Não faz nada em carro sem a aba. */
export function drs(car: THREE.Object3D, k: number) {
  const aba = car.getObjectByName("aba_drs");
  if (!aba || k <= 0) return;
  girarPecaEixo(aba, "x", 0.42 * Math.min(1, k));
}
