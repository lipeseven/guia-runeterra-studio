// Volante de F1 genérico (2026), em metros reais: ~29 cm de largura com as empunhaduras (diâmetro dos volantes atuais:
// 260 a 280 mm, Fanatec). Sem nome nem equipe. Referência: desenhos de frente e de trás de um volante de 2026.
// Comandos principais são peças próprias (apertar, girar, explodir): tela, luzes de troca, paddles de marcha e de
// embreagem, OT (modo de ultrapassagem), BOOST (energia extra, botão próprio: the-race.com), AERO (modo reta da asa
// ativa, acionado pelo piloto: silverstone.co.uk), PL (limitador do pit), N (neutro), rádio, BB+/BB- (balanço de freio)
// e 3 seletores giratórios. O resto da face é complemento (forma e cor da referência, sem função).
// Frente do volante para +z (o piloto olha para -z). Tudo volta ao normal a cada quadro (desmonte.restaurar).
import * as THREE from "three";
import { aoRestaurar, peca } from "./desmonte";

type V = [number, number, number];
// DoubleSide: as formas espelhadas (lado esquerdo) saem com as faces invertidas
const mat = (cor: string, rough = 0.5, metal = 0) => new THREE.MeshStandardMaterial({ color: cor, roughness: rough, metalness: metal, side: THREE.DoubleSide });

let texCarbono: THREE.CanvasTexture | null = null;
function carbono() {
  if (texCarbono) return texCarbono;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const x = c.getContext("2d")!;
  for (let i = 0; i < 8; i++)
    for (let j = 0; j < 8; j++) {
      x.fillStyle = (i + j) % 2 ? "#3a3c42" : "#2a2c31";
      x.fillRect(i * 8, j * 8, 8, 8);
      x.fillStyle = "rgba(255,255,255,.05)";
      x.fillRect(i * 8, j * 8, (i + j) % 2 ? 8 : 3, (i + j) % 2 ? 3 : 8);
    }
  texCarbono = new THREE.CanvasTexture(c);
  texCarbono.colorSpace = THREE.SRGBColorSpace;
  texCarbono.wrapS = texCarbono.wrapT = THREE.RepeatWrapping;
  texCarbono.repeat.set(90, 90); // as coordenadas da forma estão em metros: um quadrinho ≈ 1,4 mm
  return texCarbono;
}

const rotuloTex = (texto: string, fundo: string, cor = "#ffffff") => {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = fundo;
  x.beginPath();
  x.arc(64, 64, 64, 0, Math.PI * 2);
  x.fill();
  x.fillStyle = cor;
  x.font = `800 ${texto.length > 3 ? 30 : texto.length > 2 ? 40 : 54}px 'Segoe UI', sans-serif`;
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillText(texto, 64, 68);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
};

/** Botão redondo: aro escuro + tampa colorida com o rótulo. `tampa` é o que afunda quando aperta. */
function botao(texto: string, cor: string, r = 0.0068) {
  const g = new THREE.Group();
  const aro = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.25, r * 1.25, 0.002, 28), mat("#101114", 0.6));
  aro.rotation.x = Math.PI / 2;
  g.add(aro);
  const tampa = new THREE.Group();
  const corpo = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.005, 28), mat(cor, 0.4));
  corpo.rotation.x = Math.PI / 2;
  corpo.position.z = 0.0025;
  const topo = new THREE.Mesh(new THREE.CircleGeometry(r * 0.98, 28), new THREE.MeshStandardMaterial({ map: rotuloTex(texto, cor), roughness: 0.4, emissive: "#ffffff", emissiveIntensity: 0 }));
  topo.position.z = 0.0051;
  tampa.add(corpo, topo);
  g.add(tampa);
  g.userData.tampa = tampa;
  g.userData.luz = topo.material;
  return g;
}

/** Seletor giratório serrilhado com a escala colorida em volta e um ponteiro. */
function seletor(cores: string[]) {
  const g = new THREE.Group();
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  x.fillStyle = "#15161a";
  x.beginPath();
  x.arc(128, 128, 128, 0, Math.PI * 2);
  x.fill();
  for (let k = 0; k < 12; k++) {
    const a = ((-150 + k * (300 / 11)) * Math.PI) / 180 - Math.PI / 2;
    x.strokeStyle = cores[k % cores.length];
    x.lineWidth = 14;
    x.beginPath();
    x.arc(128, 128, 112, a - 0.09, a + 0.09);
    x.stroke();
  }
  const esc = new THREE.CanvasTexture(c);
  esc.colorSpace = THREE.SRGBColorSpace;
  const escala = new THREE.Mesh(new THREE.CircleGeometry(0.017, 40), new THREE.MeshStandardMaterial({ map: esc, roughness: 0.6 }));
  escala.position.z = 0.0012; // acima do painel de baixo
  g.add(escala);
  const giro = new THREE.Group();
  const botaoG = new THREE.Mesh(new THREE.CylinderGeometry(0.0115, 0.0115, 0.009, 24, 1), mat("#2b2d33", 0.45, 0.4));
  botaoG.rotation.x = Math.PI / 2;
  botaoG.position.z = 0.0045;
  const ponteiro = new THREE.Mesh(new THREE.BoxGeometry(0.0022, 0.009, 0.001), new THREE.MeshStandardMaterial({ color: "#ffffff", emissive: "#ffffff", emissiveIntensity: 0.3 }));
  ponteiro.position.set(0, 0.006, 0.0095);
  giro.add(botaoG, ponteiro);
  g.add(giro);
  g.userData.giro = giro;
  return g;
}

const extrudar = (forma: THREE.Shape, prof: number, bisel: number, material: THREE.Material) => {
  const geo = new THREE.ExtrudeGeometry(forma, { depth: prof, bevelEnabled: bisel > 0, bevelThickness: bisel, bevelSize: bisel, bevelSegments: 3, curveSegments: 18 });
  const m = new THREE.Mesh(geo, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
};

/** Contorno da placa central (frente achatada, cantos de cima arredondados, base mais estreita). */
function contorno(escala = 1) {
  const s = new THREE.Shape();
  const p = (x: number, y: number) => [x * escala, y * escala] as const;
  s.moveTo(...p(-0.112, 0.07));
  s.quadraticCurveTo(...p(-0.112, 0.088), ...p(-0.094, 0.088));
  s.lineTo(...p(0.094, 0.088));
  s.quadraticCurveTo(...p(0.112, 0.088), ...p(0.112, 0.07));
  s.lineTo(...p(0.112, -0.03));
  s.quadraticCurveTo(...p(0.11, -0.062), ...p(0.078, -0.076));
  s.lineTo(...p(-0.078, -0.076));
  s.quadraticCurveTo(...p(-0.11, -0.062), ...p(-0.112, -0.03));
  s.closePath();
  return s;
}

/** Empunhadura (lado s = -1 esquerda, 1 direita): sobe acima da placa e desce curvando para dentro. */
function empunhadura(s: number) {
  const f = new THREE.Shape();
  const p = (x: number, y: number) => [s * x, y] as const;
  f.moveTo(...p(0.106, 0.07));
  f.quadraticCurveTo(...p(0.11, 0.092), ...p(0.128, 0.09));
  f.lineTo(...p(0.137, 0.087));
  f.quadraticCurveTo(...p(0.148, 0.08), ...p(0.147, 0.058));
  f.lineTo(...p(0.145, -0.06));
  f.quadraticCurveTo(...p(0.14, -0.102), ...p(0.12, -0.106));
  f.lineTo(...p(0.113, -0.104));
  f.quadraticCurveTo(...p(0.104, -0.094), ...p(0.107, -0.072));
  f.closePath();
  const m = extrudar(f, 0.034, 0.006, mat("#3d3f45", 0.85));
  m.position.z = -0.022;
  return m;
}

/** Paddle atrás do volante; gira no eixo x a partir de `pivo` (k 0 solto, 1 puxado contra o volante). */
function paddle(s: number, y0: number, y1: number, x0: number, x1: number, cor: string) {
  const piv = new THREE.Group();
  const f = new THREE.Shape();
  f.moveTo(s * x0, 0);
  f.lineTo(s * x1, 0);
  f.lineTo(s * (x1 - 0.008), y1 - y0);
  f.lineTo(s * x0, y1 - y0);
  f.closePath();
  const m = extrudar(f, 0.004, 0.0012, mat(cor, 0.35, 0.3));
  piv.add(m);
  piv.position.set(0, y0, -0.034);
  return piv;
}

export type Volante = THREE.Group;

const LED_CORES = ["#18e05a", "#18e05a", "#18e05a", "#18e05a", "#18e05a", "#ff2a2a", "#ff2a2a", "#ff2a2a", "#ff2a2a", "#ff2a2a", "#3d6bff", "#3d6bff", "#3d6bff"];

/** Volante genérico de 2026 (frente para +z). Peças para o desmonte e comandos para animar: ver api_cenas.md. */
export function criarVolante(): Volante {
  const v = new THREE.Group();
  const add = (o: THREE.Object3D, nome: string, sai: V, camada: number) => {
    v.add(peca(o, nome, sai, camada));
    return o;
  };
  const fibra = new THREE.MeshStandardMaterial({ map: carbono(), roughness: 0.5, metalness: 0.15 });

  // carcaça de fibra (atrás), placa de circuitos e a frente
  const carc = new THREE.Group();
  const corpo = extrudar(contorno(), 0.02, 0.003, fibra);
  corpo.position.z = -0.022;
  carc.add(corpo);
  add(carc, "carcaca", [0, 0, 0], 3);
  const pcb = new THREE.Group();
  const placa = extrudar(contorno(0.93), 0.002, 0, mat("#0f5a3a", 0.6));
  placa.position.z = 0.0005;
  pcb.add(placa);
  for (let k = 0; k < 14; k++) {
    const chip = new THREE.Mesh(new THREE.BoxGeometry(0.008 + (k % 3) * 0.004, 0.006 + (k % 2) * 0.004, 0.002), mat(k % 4 ? "#18191c" : "#c9a54a", 0.5, k % 4 ? 0 : 0.7));
    chip.position.set(-0.08 + (k % 7) * 0.027, k < 7 ? 0.035 : -0.035, 0.0035);
    pcb.add(chip);
  }
  add(pcb, "placa_de_circuitos", [0, 0, 0.02], 2);

  const frente = new THREE.Group();
  const capa = extrudar(contorno(), 0.004, 0.0015, fibra);
  capa.position.z = 0.006;
  frente.add(capa);
  // painel de baixo (onde ficam os seletores), um pouco mais escuro
  const baixo = new THREE.Shape();
  baixo.moveTo(-0.058, -0.028);
  baixo.lineTo(0.058, -0.028);
  baixo.quadraticCurveTo(0.064, -0.028, 0.062, -0.04);
  baixo.lineTo(0.054, -0.066);
  baixo.lineTo(-0.054, -0.066);
  baixo.lineTo(-0.062, -0.04);
  baixo.quadraticCurveTo(-0.064, -0.028, -0.058, -0.028);
  const pb = extrudar(baixo, 0.001, 0, mat("#1b1c20", 0.55));
  pb.position.z = 0.0115;
  frente.add(pb);
  // complemento: forma e cor da referência, sem função própria
  for (const [x, y, t, c] of [[-0.097, 0.066, "", "#f2c400"], [-0.071, 0.064, "+10", "#7a3fd0"], [0.097, 0.066, "", "#e0262f"],
    [-0.085, -0.021, "×", "#e0262f"]] as const) {
    const b = botao(t, c, 0.0062);
    b.position.set(x, y, 0.0115);
    frente.add(b);
  }
  for (const s of [-1, 1]) {
    // rodinhas douradas ao lado da tela e os seletores das pontas
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.0065, 0.0065, 0.016, 20), mat("#c9a54a", 0.35, 0.7));
    rod.position.set(s * 0.067, 0.018, 0.016);
    frente.add(rod);
    for (let k = 0; k < 3; k++) {
      const luz = new THREE.Mesh(new THREE.BoxGeometry(0.008, 0.002, 0.001), new THREE.MeshStandardMaterial({ color: "#8fe0a0", emissive: "#3fdc6a", emissiveIntensity: 0.4 }));
      luz.position.set(s * 0.1, -0.003 - k * 0.0035, 0.0118);
      frente.add(luz);
    }
  }
  add(frente, "frente", [0, 0, 0.045], 1);

  // tela
  const tela = new THREE.Group();
  const moldura = new THREE.Mesh(new THREE.BoxGeometry(0.118, 0.074, 0.006), mat("#0a0a0c", 0.4));
  moldura.position.set(0, 0.026, 0.014);
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 320;
  const texTela = new THREE.CanvasTexture(c);
  texTela.colorSpace = THREE.SRGBColorSpace;
  const vidro = new THREE.Mesh(new THREE.PlaneGeometry(0.106, 0.064), new THREE.MeshBasicMaterial({ map: texTela, toneMapped: false }));
  vidro.position.set(0, 0.026, 0.0172);
  tela.add(moldura, vidro);
  add(tela, "tela", [0, 0.015, 0.07], 0);

  // luzes de troca de marcha
  const leds = new THREE.Group();
  const lmats = LED_CORES.map((cor) => new THREE.MeshStandardMaterial({ color: "#222", emissive: cor, emissiveIntensity: 0 }));
  LED_CORES.forEach((_, k) => {
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.0026, 12, 8), lmats[k]);
    l.position.set(-0.054 + k * 0.009, 0.072, 0.012);
    leds.add(l);
  });
  add(leds, "luzes", [0, 0.03, 0.06], 0);

  // comandos principais
  const botoes: Record<string, THREE.Group> = {};
  for (const [nome, t, cor, x, y] of [["ot", "OT", "#e8e8ea", 0.085, 0.002], ["boost", "BOOST", "#7a3fd0", 0.071, 0.064], ["aero", "AERO", "#f08a1c", -0.085, 0.002],
    ["pl", "PL", "#e8e8ea", 0.085, 0.042], ["n", "N", "#1f8f5a", -0.085, 0.042], ["radio", "RÁDIO", "#25b14f", 0.085, -0.021],
    ["bb_mais", "BB+", "#8d929b", 0.09, -0.05], ["bb_menos", "BB−", "#8d929b", -0.09, -0.05]] as const) {
    const b = botao(t, cor);
    b.position.set(x, y, 0.0115);
    botoes[nome] = b;
    add(b, `botao_${nome}`, [x * 0.5, y * 0.4, 0.09], 0);
  }
  const seletores: Record<string, THREE.Group> = {};
  for (const [nome, x, cores] of [["esquerdo", -0.034, ["#2fd47a", "#e8e8ea", "#3b8ee0", "#f2c400"]], ["central", 0, ["#e8e8ea", "#f08a1c", "#9aa0a8"]],
    ["direito", 0.034, ["#e0262f", "#f08a1c", "#e8e8ea"]]] as const) {
    const s = seletor([...cores]);
    s.position.set(x, -0.047, 0.0118);
    seletores[nome] = s;
    add(s, `seletor_${nome}`, [x * 0.6, -0.02, 0.1], 0);
  }

  // empunhaduras e paddles
  for (const s of [-1, 1]) {
    const lado = s < 0 ? "esquerda" : "direita";
    add(empunhadura(s), `empunhadura_${lado}`, [s * 0.06, 0, 0], 1);
  }
  const paddles: Record<string, THREE.Group> = {};
  for (const s of [-1, 1]) {
    const lado = s < 0 ? "esquerda" : "direita";
    paddles[`marcha_${lado}`] = add(paddle(s, 0.022, 0.07, 0.03, 0.118, "#2a2c31"), `paddle_marcha_${lado}`, [s * 0.02, 0.02, -0.06], 1) as THREE.Group;
    paddles[`embreagem_${lado}`] = add(paddle(s, -0.075, -0.02, 0.028, 0.1, "#9aa0a8"), `embreagem_${lado}`, [s * 0.02, -0.03, -0.07], 1) as THREE.Group;
  }
  // engate rápido e coluna
  const eng = new THREE.Group();
  const cubo = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.024, 0.026, 28), mat("#9aa0a8", 0.35, 0.8));
  cubo.rotation.x = Math.PI / 2;
  cubo.position.z = -0.048;
  const coluna = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.22, 20), mat("#2a2c31", 0.4, 0.5));
  coluna.rotation.x = Math.PI / 2;
  coluna.position.z = -0.17;
  eng.add(cubo, coluna);
  add(eng, "engate_rapido", [0, 0, -0.12], 2);

  // estado dos comandos (tudo volta ao normal antes de cada quadro)
  const est = { marcha: "N", modo: "", delta: "+0.000", bateria: 0.62, velocidade: 0 };
  let ultima = "";
  const desenhar = () => {
    const chave = JSON.stringify(est);
    if (chave === ultima) return; // redesenha a tela só quando o que ela mostra muda
    ultima = chave;
    const x = c.getContext("2d")!;
    x.fillStyle = "#06070a";
    x.fillRect(0, 0, 512, 320);
    x.fillStyle = "#11131a";
    x.fillRect(12, 12, 150, 296);
    x.fillRect(350, 12, 150, 296);
    x.textAlign = "center";
    x.textBaseline = "middle";
    x.fillStyle = "#ffffff";
    x.font = "800 190px 'Segoe UI', sans-serif";
    x.fillText(est.marcha, 256, 140);
    x.font = "700 26px 'Consolas', monospace";
    x.fillStyle = "#8a90a0";
    x.fillText("DELTA", 87, 50);
    x.fillText("KM/H", 425, 50);
    x.fillText("BATERIA", 87, 200);
    x.font = "800 44px 'Consolas', monospace";
    x.fillStyle = est.delta.startsWith("-") ? "#18e05a" : "#ff4a4a";
    x.fillText(est.delta, 87, 100);
    x.fillStyle = "#ffffff";
    x.fillText(String(Math.round(est.velocidade)), 425, 100);
    x.fillStyle = "#2a2d36";
    x.fillRect(32, 230, 110, 40);
    x.fillStyle = est.bateria > 0.25 ? "#3d9bff" : "#ff4a4a";
    x.fillRect(32, 230, 110 * Math.max(0, Math.min(1, est.bateria)), 40);
    if (est.modo) {
      x.fillStyle = "#ffc400";
      x.fillRect(176, 262, 160, 44);
      x.fillStyle = "#06070a";
      x.font = "800 32px 'Segoe UI', sans-serif";
      x.fillText(est.modo, 256, 285);
    }
    texTela.needsUpdate = true;
  };
  desenhar();
  v.userData.volante = { botoes, seletores, paddles, lmats, est, desenhar };
  aoRestaurar(() => {
    for (const b of Object.values(botoes)) {
      (b.userData.tampa as THREE.Group).position.z = 0;
      (b.userData.luz as THREE.MeshStandardMaterial).emissiveIntensity = 0;
    }
    for (const s of Object.values(seletores)) (s.userData.giro as THREE.Group).rotation.z = 0;
    for (const p of Object.values(paddles)) p.rotation.x = 0;
    for (const m of lmats) m.emissiveIntensity = 0;
    Object.assign(est, { marcha: "N", modo: "", delta: "+0.000", bateria: 0.62, velocidade: 0 });
    desenhar();
  });
  return v;
}

type Estado = { botoes: Record<string, THREE.Group>; seletores: Record<string, THREE.Group>; paddles: Record<string, THREE.Group>; lmats: THREE.MeshStandardMaterial[]; est: Record<string, unknown>; desenhar: () => void };
const de = (v: Volante) => v.userData.volante as Estado;

/** Aperta um botão (ot, boost, aero, pl, n, radio, bb_mais, bb_menos): k 0 solto, 1 afundado e aceso. */
export function apertar(v: Volante, nome: string, k = 1) {
  const b = de(v).botoes[nome];
  if (!b) throw new Error(`botão desconhecido: ${nome}`);
  (b.userData.tampa as THREE.Group).position.z = -0.003 * k;
  (b.userData.luz as THREE.MeshStandardMaterial).emissiveIntensity = 0.55 * k;
}

/** Gira um seletor (esquerdo, central, direito) até a posição 0 a 11 (aceita fração, para animar). */
export function girar(v: Volante, nome: string, posicao: number) {
  const s = de(v).seletores[nome];
  if (!s) throw new Error(`seletor desconhecido: ${nome}`);
  (s.userData.giro as THREE.Group).rotation.z = -((-150 + posicao * (300 / 11)) * Math.PI) / 180;
}

/** Puxa um paddle (marcha_esquerda, marcha_direita, embreagem_esquerda, embreagem_direita): k 0 solto, 1 puxado. */
export function puxar(v: Volante, nome: string, k = 1) {
  const p = de(v).paddles[nome];
  if (!p) throw new Error(`paddle desconhecido: ${nome}`);
  p.rotation.x = -0.22 * k;
}

/** Luzes de troca de marcha: f 0 apagadas, 1 todas acesas (verde → vermelho → azul). */
export function luzesDeTroca(v: Volante, f: number) {
  const n = Math.round(Math.max(0, Math.min(1, f)) * LED_CORES.length);
  de(v).lmats.forEach((m, k) => (m.emissiveIntensity = k < n ? 2.2 : 0));
}

/** O que a tela mostra: marcha ("N", "1" a "8"), modo (ex.: "OT", "BOOST", "AERO"), delta ("-0.214"), bateria 0 a 1, km/h. */
export function telaDoVolante(v: Volante, dados: { marcha?: string; modo?: string; delta?: string; bateria?: number; velocidade?: number }) {
  const e = de(v);
  Object.assign(e.est, dados);
  e.desenhar();
}
