// Volante de F1 genérico (2026), em metros reais: ~29 cm de largura com as empunhaduras (diâmetro dos volantes atuais:
// 260 a 280 mm, Fanatec). Sem nome nem equipe. Contornos, posições e tamanhos MEDIDOS nos desenhos de referência de
// frente e de trás (1 px da referência ≈ 0,68 mm; `P` converte o pixel da frente em metros).
// Comandos principais são peças próprias (apertar, girar, explodir): tela, luzes de troca, paddles de marcha e de
// embreagem, OT (modo de ultrapassagem), BOOST (energia extra, botão próprio: the-race.com), AERO (modo reta da asa
// ativa, acionado pelo piloto: silverstone.co.uk), PL (limitador do pit), N (neutro), rádio, BB+/BB- (balanço de freio)
// e 3 seletores giratórios. O resto da face é complemento (forma e cor da referência, sem função).
// Frente do volante para +z (o piloto olha para -z). Tudo volta ao normal a cada quadro (desmonte.restaurar).
import * as THREE from "three";
import { aoRestaurar, peca } from "./desmonte";

type V = [number, number, number];
const S = 0.00068; // metros por pixel da referência
const CX = 236; // centro da referência da frente (px)
const CY = 120;
/** Pixel da referência da frente → metros (x para a direita, y para cima). */
const P = (x: number, y: number): [number, number] => [(x - CX) * S, (CY - y) * S];
const espelho = (x: number) => 2 * CX - x;

// DoubleSide: as formas espelhadas saem com as faces invertidas
const mat = (cor: string, rough = 0.5, metal = 0) => new THREE.MeshStandardMaterial({ color: cor, roughness: rough, metalness: metal, side: THREE.DoubleSide });

const ZF = 0.0105; // superfície da frente

let texCarbono: THREE.CanvasTexture | null = null;
/** Fibra de carbono em sarja (trama diagonal fina, ~3 mm por repetição). */
function carbono() {
  if (texCarbono) return texCarbono;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const x = c.getContext("2d")!;
  x.fillStyle = "#3c3f46";
  x.fillRect(0, 0, 64, 64);
  for (let i = -4; i < 8; i++)
    for (let j = 0; j < 8; j++) {
      const claro = (i + j) % 2 === 0;
      x.fillStyle = claro ? "#555960" : "#33363c";
      x.beginPath();
      x.moveTo(i * 8 + j * 8, j * 8);
      x.lineTo(i * 8 + j * 8 + 8, j * 8);
      x.lineTo(i * 8 + j * 8 + 16, j * 8 + 8);
      x.lineTo(i * 8 + j * 8 + 8, j * 8 + 8);
      x.fill();
    }
  texCarbono = new THREE.CanvasTexture(c);
  texCarbono.colorSpace = THREE.SRGBColorSpace;
  texCarbono.wrapS = texCarbono.wrapT = THREE.RepeatWrapping;
  texCarbono.repeat.set(300, 300); // as coordenadas da forma estão em metros
  texCarbono.anisotropy = 8;
  return texCarbono;
}

const rotuloTex = (texto: string, fundo: string, cor = "#ffffff") => {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  const g = x.createRadialGradient(54, 50, 8, 64, 64, 66);
  g.addColorStop(0, new THREE.Color(fundo).offsetHSL(0, 0, 0.12).getStyle());
  g.addColorStop(1, fundo);
  x.fillStyle = g;
  x.beginPath();
  x.arc(64, 64, 64, 0, Math.PI * 2);
  x.fill();
  x.fillStyle = cor;
  x.font = `800 ${texto.length > 4 ? 26 : texto.length > 2 ? 38 : 56}px 'Segoe UI', sans-serif`;
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillText(texto, 64, 68);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
};

/** Botão em moldura: anel escuro em relevo + tampa colorida abaulada com o rótulo. `tampa` afunda quando aperta. */
function botao(texto: string, cor: string, rPx = 11, corTexto = "#ffffff") {
  const r = rPx * S;
  const g = new THREE.Group();
  const moldura = new THREE.Mesh(new THREE.TorusGeometry(r * 1.18, r * 0.22, 10, 36), mat("#4a4d54", 0.35, 0.5));
  moldura.position.z = 0.0012;
  const fundo = new THREE.Mesh(new THREE.CircleGeometry(r * 1.2, 32), mat("#0d0e11", 0.7));
  fundo.position.z = 0.0003;
  g.add(fundo, moldura);
  const tampa = new THREE.Group();
  const corpo = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.004, 32), mat(cor, 0.35));
  corpo.rotation.x = Math.PI / 2;
  corpo.position.z = 0.002;
  const topo = new THREE.Mesh(new THREE.CircleGeometry(r * 0.97, 32), new THREE.MeshStandardMaterial({ map: rotuloTex(texto, cor, corTexto), roughness: 0.3, emissive: "#ffffff", emissiveIntensity: 0 }));
  topo.position.z = 0.0041;
  tampa.add(corpo, topo);
  g.add(tampa);
  g.userData.tampa = tampa;
  g.userData.luz = topo.material;
  return g;
}

/** Botão giratório serrilhado (cilindro com frisos). */
function serrilhado(r: number, alt: number, cor: string, frisos = 28) {
  const g = new THREE.Group();
  const nucleo = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.92, r * 0.92, alt, 32), mat(cor, 0.4, 0.3));
  g.add(nucleo);
  for (let k = 0; k < frisos; k++) {
    const a = (k / frisos) * Math.PI * 2;
    const f = new THREE.Mesh(new THREE.BoxGeometry(r * 0.16, alt * 0.96, r * 0.16), mat(cor, 0.4, 0.3));
    f.position.set(Math.cos(a) * r * 0.93, 0, Math.sin(a) * r * 0.93);
    f.rotation.y = -a;
    g.add(f);
  }
  return g;
}

/** Seletor giratório: escala colorida impressa em volta, botão serrilhado com tampa colorida e ponteiro. */
function seletor(rPx: number, cor: string, cores: string[]) {
  const r = rPx * S;
  const g = new THREE.Group();
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  x.fillStyle = "#14151a";
  x.beginPath();
  x.arc(128, 128, 128, 0, Math.PI * 2);
  x.fill();
  x.font = "700 20px 'Consolas', monospace";
  x.textAlign = "center";
  x.textBaseline = "middle";
  for (let k = 0; k < 12; k++) {
    const a = ((-150 + k * (300 / 11)) * Math.PI) / 180 - Math.PI / 2;
    x.fillStyle = cores[k % cores.length];
    x.beginPath();
    x.arc(128, 128, 122, a - 0.11, a + 0.11);
    x.arc(128, 128, 96, a + 0.11, a - 0.11, true);
    x.fill();
    x.fillStyle = "#0c0d10";
    x.fillText(String(k + 1), 128 + Math.cos(a) * 109, 128 + Math.sin(a) * 109);
  }
  const esc = new THREE.CanvasTexture(c);
  esc.colorSpace = THREE.SRGBColorSpace;
  const escala = new THREE.Mesh(new THREE.CircleGeometry(r * 1.75, 48), new THREE.MeshStandardMaterial({ map: esc, roughness: 0.55 }));
  escala.position.z = 0.0008;
  g.add(escala);
  const giro = new THREE.Group();
  const sb = serrilhado(r, 0.008, cor);
  sb.rotation.x = Math.PI / 2;
  sb.position.z = 0.0048;
  const tampa = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.62, r * 0.7, 0.002, 32), mat("#1a1b1f", 0.4, 0.4));
  tampa.rotation.x = Math.PI / 2;
  tampa.position.z = 0.0092;
  const ponteiro = new THREE.Mesh(new THREE.BoxGeometry(r * 0.16, r * 0.8, 0.0012), new THREE.MeshStandardMaterial({ color: "#ffffff", emissive: "#ffffff", emissiveIntensity: 0.25 }));
  ponteiro.position.set(0, r * 0.55, 0.0098);
  giro.add(sb, tampa, ponteiro);
  g.add(giro);
  g.userData.giro = giro;
  return g;
}

/** `bisel` arredonda a borda; `abre` é quanto o bisel alarga a forma para os lados (padrão = bisel). */
const extrudar = (forma: THREE.Shape, prof: number, bisel: number, material: THREE.Material, segs = 3, abre = bisel) => {
  const geo = new THREE.ExtrudeGeometry(forma, { depth: prof, bevelEnabled: bisel > 0, bevelThickness: bisel, bevelSize: abre, bevelSegments: segs, curveSegments: 24 });
  const m = new THREE.Mesh(geo, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
};

/** Forma suave a partir de pontos em pixel da referência (curva que passa pelos pontos, fechada). */
function formaPx(pts: [number, number][], buracos: [number, number][][] = []) {
  const curva = (lista: [number, number][]) => new THREE.CatmullRomCurve3(lista.map(([x, y]) => new THREE.Vector3(...P(x, y), 0)), true, "centripetal").getPoints(lista.length * 10);
  const s = new THREE.Shape(curva(pts).map((v) => new THREE.Vector2(v.x, v.y)));
  for (const b of buracos) s.holes.push(new THREE.Path(curva(b).map((v) => new THREE.Vector2(v.x, v.y))));
  return s;
}
// (ponto no eixo não é repetido: dois pontos iguais estragam a curva)
const simetrico = (metade: [number, number][]) => [...metade, ...[...metade].reverse().filter(([x]) => x !== CX).map(([x, y]) => [espelho(x), y] as [number, number])];

// contorno do corpo (metade esquerda, do topo ao centro de baixo), com as "orelhas" em cima e os recortes junto às empunhaduras
const CORPO: [number, number][] = [[236, 13], [130, 13], [98, 16], [76, 26], [63, 40], [57, 56], [60, 68], [84, 72], [86, 92], [84, 113], [88, 128], [96, 165], [104, 195], [118, 211], [138, 218], [170, 221], [226, 222]];
const JANELAS: [number, number][][] = [
  [[88, 73], [114, 72], [117, 82], [114, 92], [88, 91]],
  [[88, 114], [113, 114], [115, 121], [112, 127], [88, 126]],
];
// empunhadura esquerda (borracha), medida na frente
const PEGA: [number, number][] = [[46, 61], [66, 56], [80, 60], [81, 72], [80, 100], [74, 140], [67, 180], [63, 220], [62, 246], [56, 255], [46, 252], [40, 238], [33, 195], [27, 150], [27, 108], [32, 82], [38, 68]];

export type Volante = THREE.Group;

// luzes de troca: 15 em cima da tela (brancas, vermelhas e azuis como na referência)
const LED_X = Array.from({ length: 15 }, (_, k) => 172 + k * 9.2);
const LED_CORES = LED_X.map((_, k) => (k < 6 ? "#e8f4ff" : k < 11 ? "#ff2a2a" : "#3d6bff"));

/** Volante genérico de 2026 (frente para +z). Peças para o desmonte e comandos para animar: ver api_cenas.md. */
export function criarVolante(): Volante {
  const v = new THREE.Group();
  const add = (o: THREE.Object3D, nome: string, sai: V, camada: number) => {
    v.add(peca(o, nome, sai, camada));
    return o;
  };
  const fibra = new THREE.MeshStandardMaterial({ map: carbono(), roughness: 0.42, metalness: 0.2 });
  const em = (o: THREE.Object3D, x: number, y: number, z = ZF) => {
    o.position.set(...P(x, y), z);
    return o;
  };

  // carcaça (metade de trás do corpo) com o que fica atrás: cubo do engate, parafusos, caixa cilíndrica da embreagem
  const carc = new THREE.Group();
  const tras = extrudar(formaPx(simetrico(CORPO), [...JANELAS, ...JANELAS.map((j) => j.map(([x, y]) => [espelho(x), y] as [number, number]))]), 0.011, 0.0015, fibra);
  tras.position.z = -0.0115;
  carc.add(tras);
  for (const x of [85, espelho(85)]) {
    const boss = new THREE.Mesh(new THREE.CylinderGeometry(0.0075, 0.0075, 0.004, 24), mat("#8f949c", 0.3, 0.8));
    boss.rotation.x = Math.PI / 2;
    em(boss, x, 40, -0.0135);
    carc.add(boss);
  }
  // suporte triangular do cubo (atrás), com parafusos
  const tri = formaPx([[175, 118], [296, 118], [262, 205], [236, 226], [210, 205]]);
  const mtri = extrudar(tri, 0.004, 0.0012, mat("#6c7078", 0.35, 0.6));
  mtri.position.z = -0.0175;
  carc.add(mtri);
  for (const [x, y] of [[190, 128], [282, 128], [200, 158], [272, 158], [236, 214], [236, 133]]) {
    const pf = new THREE.Mesh(new THREE.CylinderGeometry(0.0034, 0.0034, 0.003, 14), mat("#b7bcc4", 0.3, 0.8));
    pf.rotation.x = Math.PI / 2;
    carc.add(em(pf, x, y, -0.0185));
  }
  // caixa cilíndrica embaixo à esquerda (aparece de frente e de trás)
  const caixa = new THREE.Mesh(new THREE.CylinderGeometry(0.0136, 0.0136, 0.042, 28), mat("#4f5258", 0.35, 0.5));
  carc.add(em(caixa, 100, 200, -0.016));
  const topoCx = new THREE.Mesh(new THREE.CylinderGeometry(0.0125, 0.0136, 0.004, 28), mat("#2a2c31", 0.4, 0.4));
  carc.add(em(topoCx, 100, 169, -0.016));
  add(carc, "carcaca", [0, 0, 0], 3);

  // placa de circuitos (dentro da frente: aparece quando a frente sai)
  const pcb = new THREE.Group();
  // fica por dentro das janelas (não aparece por elas)
  const placa = extrudar(formaPx(simetrico([[236, 24], [140, 26], [126, 40], [124, 150], [134, 205], [180, 212], [226, 213]])), 0.0015, 0, mat("#0f5a3a", 0.6));
  placa.position.z = 0.0008;
  pcb.add(placa);
  for (let k = 0; k < 18; k++) {
    const chip = new THREE.Mesh(new THREE.BoxGeometry(0.007 + (k % 3) * 0.004, 0.006 + (k % 2) * 0.004, 0.0018), mat(k % 4 ? "#18191c" : "#c9a54a", 0.5, k % 4 ? 0 : 0.7));
    chip.position.set(-0.075 + (k % 9) * 0.019, k < 9 ? 0.03 : -0.03, 0.0032);
    pcb.add(chip);
  }
  add(pcb, "placa_de_circuitos", [0, 0, 0.022], 2);

  // frente: placa de fibra com as molduras, painel de baixo, tela, rodinhas e o complemento
  const frente = new THREE.Group();
  const capa = extrudar(formaPx(simetrico(CORPO), [...JANELAS, ...JANELAS.map((j) => j.map(([x, y]) => [espelho(x), y] as [number, number]))]), 0.0085, 0.0018, fibra);
  capa.position.z = 0.0002;
  frente.add(capa);
  // queixo: painel mais escuro onde ficam os 3 seletores, com as faixas curvas da referência
  const queixo = extrudar(formaPx(simetrico([[160, 168], [200, 163], [236, 162]]).concat([[322, 212], [236, 216], [150, 212]] as [number, number][])), 0.0006, 0, mat("#17181c", 0.6));
  queixo.position.z = ZF;
  frente.add(queixo);
  for (const [x, cor] of [[178, "#2bb39a"], [292, "#e0522f"]] as const) {
    const arco = new THREE.Mesh(new THREE.RingGeometry(0.0225, 0.0255, 32, 1, Math.PI * 0.28, Math.PI * 0.44), mat(cor, 0.5));
    arco.rotation.z = x < CX ? 0.25 : -0.25;
    frente.add(em(arco, x, 190, ZF + 0.0008));
  }
  // rodinhas douradas ao lado da tela
  for (const x of [118, espelho(118)]) {
    const rod = serrilhado(0.0062, 0.022, "#c9a54a", 22);
    frente.add(em(rod, x, 101, ZF + 0.002));
  }
  // seletores das pontas das orelhas (ENTRY / os da direita), inclinados para fora
  for (const [x, y, cor, s] of [[64, 74, "#c8325e", -1], [espelho(64), 75, "#2f8fd6", 1]] as const) {
    const ponta = serrilhado(0.0085, 0.017, cor, 24);
    ponta.rotation.z = s * 0.95;
    frente.add(em(ponta, x, y, ZF - 0.002));
  }
  // barras de luz verdes ao lado dos botões do meio
  for (const x of [106, espelho(106)])
    for (let k = 0; k < 3; k++) {
      const luz = new THREE.Mesh(new THREE.BoxGeometry(0.009, 0.0032, 0.0012), new THREE.MeshStandardMaterial({ color: "#7fdc96", emissive: "#2fd46a", emissiveIntensity: 0.45 }));
      frente.add(em(luz, x, 141 + k * 7, ZF + 0.0006));
    }
  // complemento: botões com a forma e a cor da referência, sem função própria
  for (const [x, y, t, cor, tc] of [[78, 45, "", "#f2d21a", "#222"], [106, 47, "+10", "#6a37c6", "#fff"], [espelho(80), 45, "", "#e8262c", "#fff"], [128, 162, "✕", "#e0262f", "#fff"]] as const) {
    frente.add(em(botao(t, cor, x === 128 ? 11 : 12, tc), x, y));
  }
  // parafusos da face
  for (const [x, y] of [[147, 207], [325, 207], [98, 36], [espelho(98), 36], [236, 156]]) {
    const pf = new THREE.Mesh(new THREE.CylinderGeometry(0.0022, 0.0022, 0.0014, 12), mat("#9aa0a8", 0.3, 0.8));
    pf.rotation.x = Math.PI / 2;
    frente.add(em(pf, x, y, ZF + 0.0006));
  }
  add(frente, "frente", [0, 0, 0.05], 1);

  // tela: moldura em relevo + vidro com o conteúdo
  const tela = new THREE.Group();
  const rr = new THREE.Shape();
  const [x0, y0] = P(146, 152);
  const [x1, y1] = P(326, 28);
  const raio = 0.008;
  rr.moveTo(x0 + raio, y0);
  rr.lineTo(x1 - raio, y0);
  rr.quadraticCurveTo(x1, y0, x1, y0 + raio);
  rr.lineTo(x1, y1 - raio);
  rr.quadraticCurveTo(x1, y1, x1 - raio, y1);
  rr.lineTo(x0 + raio, y1);
  rr.quadraticCurveTo(x0, y1, x0, y1 - raio);
  rr.lineTo(x0, y0 + raio);
  rr.quadraticCurveTo(x0, y0, x0 + raio, y0);
  const moldura = extrudar(rr, 0.0035, 0.0012, mat("#3b3e45", 0.35, 0.5));
  moldura.position.z = ZF;
  tela.add(moldura);
  const c = document.createElement("canvas");
  c.width = 640;
  c.height = 360;
  const texTela = new THREE.CanvasTexture(c);
  texTela.colorSpace = THREE.SRGBColorSpace;
  const [sx0, sy0] = P(160, 138);
  const [sx1, sy1] = P(312, 56);
  const vidro = new THREE.Mesh(new THREE.PlaneGeometry(sx1 - sx0, sy1 - sy0), new THREE.MeshBasicMaterial({ map: texTela, toneMapped: false }));
  vidro.position.set((sx0 + sx1) / 2, (sy0 + sy1) / 2, ZF + 0.0054); // acima da moldura (3,5 mm + bisel)
  tela.add(vidro);
  add(tela, "tela", [0, 0.012, 0.075], 0);

  // luzes de troca de marcha (na moldura, em cima da tela) e as laterais
  const leds = new THREE.Group();
  const lmats = LED_CORES.map((cor) => new THREE.MeshStandardMaterial({ color: "#d9dde3", roughness: 0.3, emissive: cor, emissiveIntensity: 0 }));
  LED_X.forEach((x, k) => {
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.0029, 14, 10), lmats[k]);
    leds.add(em(l, x, 41, ZF + 0.0048));
  });
  for (const x of [153, espelho(153)])
    for (const y of [54, 66, 78]) {
      const l = new THREE.Mesh(new THREE.SphereGeometry(0.0026, 12, 8), mat("#e8ecf2", 0.3));
      leds.add(em(l, x, y, ZF + 0.0048));
    }
  add(leds, "luzes", [0, 0.03, 0.065], 0);

  // comandos principais (posições e cores da referência; rótulos nossos)
  const botoes: Record<string, THREE.Group> = {};
  for (const [nome, t, cor, tc, x, y, r] of [
    ["n", "N", "#2fa596", "#0d2a26", 122, 66, 10], ["pl", "PL", "#f2d21a", "#222", espelho(122), 66, 11], ["boost", "BOOST", "#6a37c6", "#fff", espelho(106), 47, 12],
    ["aero", "AERO", "#f08a1c", "#2a1200", 130, 135, 11], ["ot", "OT", "#2f7fd6", "#fff", espelho(130), 135, 12],
    ["radio", "RÁDIO", "#27a845", "#fff", espelho(128), 164, 12], ["bb_menos", "BB−", "#5d6169", "#fff", 128, 193, 11], ["bb_mais", "BB+", "#5d6169", "#fff", espelho(126), 193, 11],
  ] as const) {
    const b = botao(t, cor, r, tc);
    em(b, x, y);
    botoes[nome] = b;
    add(b, `botao_${nome}`, [b.position.x * 0.5, b.position.y * 0.4, 0.1], 0);
  }
  const seletores: Record<string, THREE.Group> = {};
  for (const [nome, x, y, r, cor, cores] of [
    ["esquerdo", 180, 191, 15, "#2bb39a", ["#2fd47a", "#f2d21a", "#e8e8ea", "#3b8ee0"]], ["central", 233, 185, 13, "#e8e8ea", ["#e8e8ea", "#f08a1c", "#9aa0a8", "#3b8ee0"]],
    ["direito", 287, 191, 15, "#e0522f", ["#e0262f", "#f08a1c", "#e8e8ea"]],
  ] as const) {
    const s = seletor(r, cor, [...cores]);
    em(s, x, y, ZF + 0.0006);
    seletores[nome] = s;
    add(s, `seletor_${nome}`, [s.position.x * 0.6, -0.02, 0.11], 0);
  }

  // empunhaduras de borracha (grossas, com bisel largo) e parafusos de trás
  const borracha = mat("#4f5259", 0.93);
  for (const s of [-1, 1]) {
    const lado = s < 0 ? "esquerda" : "direita";
    const g = new THREE.Group();
    const pts = s < 0 ? PEGA : PEGA.map(([x, y]) => [espelho(x), y] as [number, number]);
    const m = extrudar(formaPx(pts), 0.026, 0.0075, borracha, 5, 0.0025);
    m.position.z = -0.022;
    g.add(m);
    for (const y of [125, 205]) {
      const pf = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.002, 16), mat("#6b6f77", 0.4, 0.6));
      pf.rotation.x = Math.PI / 2;
      g.add(em(pf, s < 0 ? 45 : espelho(45), y, -0.0305));
    }
    add(g, `empunhadura_${lado}`, [s * 0.065, 0, 0], 1);
  }

  // paddles de marcha (medidos atrás: barra de x 0,012 a 0,105 m, ponta cinza) e de embreagem (assimétricos)
  const paddles: Record<string, THREE.Group> = {};
  const paddle = (nome: string, pts: [number, number][], ponta: [number, number][] | null, cor: string, pivoY: number, z: number) => {
    const piv = new THREE.Group();
    piv.position.set(0, pivoY, z);
    // suporte que prende o paddle à carcaça
    const sup = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.01, -0.013 - z), mat("#2a2c31", 0.4, 0.5));
    sup.position.set(pts[0][0] + Math.sign(pts[0][0] || 1) * 0.006, 0, (-0.013 - z) / 2 + 0.002);
    piv.add(sup);
    const s = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y - pivoY)));
    const m = extrudar(s, 0.004, 0.0012, mat(cor, 0.4, 0.4));
    piv.add(m);
    if (ponta) {
      const sp = new THREE.Shape(ponta.map(([x, y]) => new THREE.Vector2(x, y - pivoY)));
      const mp = extrudar(sp, 0.0045, 0.0012, mat("#585c64", 0.85));
      mp.position.z = -0.0003;
      piv.add(mp);
    }
    paddles[nome] = piv;
    return piv;
  };
  for (const s of [-1, 1]) {
    const lado = s < 0 ? "esquerda" : "direita";
    const pts: [number, number][] = [[s * 0.012, 0.016], [s * 0.104, 0.019], [s * 0.106, 0.004], [s * 0.012, 0.002]];
    const ponta: [number, number][] = [[s * 0.082, 0.0215], [s * 0.106, 0.0215], [s * 0.108, 0.0005], [s * 0.082, 0.0]];
    add(paddle(`marcha_${lado}`, pts, ponta, "#34363c", 0.016, -0.037), `paddle_marcha_${lado}`, [s * 0.02, 0.02, -0.06], 1);
  }
  // embreagem direita: alavanca com suporte em L; esquerda: placa azulada longa
  add(paddle("embreagem_direita", [[0.018, -0.046], [0.074, -0.044], [0.112, -0.03], [0.114, -0.072], [0.074, -0.066], [0.018, -0.062]], null, "#6f747c", -0.044, -0.034),
    "embreagem_direita", [0.02, -0.03, -0.07], 1);
  add(paddle("embreagem_esquerda", [[-0.012, -0.052], [-0.078, -0.05], [-0.078, -0.064], [-0.012, -0.066]], null, "#8fa3b3", -0.05, -0.034),
    "embreagem_esquerda", [-0.02, -0.03, -0.07], 1);

  // engate rápido (estrias + conector verde) e coluna
  const eng = new THREE.Group();
  const cubo = serrilhado(0.017, 0.022, "#a3a8b0", 30);
  cubo.rotation.x = Math.PI / 2;
  cubo.position.set(0.001, -0.037, -0.03);
  const anel = new THREE.Mesh(new THREE.TorusGeometry(0.0185, 0.0025, 10, 40), mat("#6c7078", 0.3, 0.8));
  anel.position.set(0.001, -0.037, -0.041);
  const conector = new THREE.Mesh(new THREE.CircleGeometry(0.0095, 28), mat("#7fae7a", 0.5, 0.2));
  conector.rotation.y = Math.PI;
  conector.position.set(0.001, -0.037, -0.0412);
  const coluna = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.22, 20), mat("#2a2c31", 0.4, 0.5));
  coluna.rotation.x = Math.PI / 2;
  coluna.position.set(0.001, -0.037, -0.152);
  eng.add(cubo, anel, conector, coluna);
  add(eng, "engate_rapido", [0, 0, -0.12], 2);

  // estado dos comandos (tudo volta ao normal antes de cada quadro)
  const est = { marcha: "N", modo: "", delta: "+0.000", bateria: 0.62, velocidade: 0 };
  let ultima = "";
  const desenhar = () => {
    const chave = JSON.stringify(est);
    if (chave === ultima) return; // redesenha a tela só quando o que ela mostra muda
    ultima = chave;
    const x = c.getContext("2d")!;
    x.fillStyle = "#08090c";
    x.fillRect(0, 0, 640, 360);
    // grade de dados, como na referência
    x.strokeStyle = "#2a2e38";
    x.lineWidth = 3;
    x.strokeRect(14, 14, 612, 332);
    for (const xx of [222, 418]) {
      x.beginPath();
      x.moveTo(xx, 14);
      x.lineTo(xx, 346);
      x.stroke();
    }
    for (const yy of [120, 236]) {
      x.beginPath();
      x.moveTo(14, yy);
      x.lineTo(222, yy);
      x.moveTo(418, yy);
      x.lineTo(626, yy);
      x.stroke();
    }
    x.textAlign = "center";
    x.textBaseline = "middle";
    x.fillStyle = "#ffffff";
    x.font = "800 170px 'Segoe UI', sans-serif";
    x.fillText(est.marcha, 320, 120);
    x.font = "700 22px 'Consolas', monospace";
    x.fillStyle = "#7d8494";
    x.fillText("DELTA", 118, 36);
    x.fillText("KM/H", 522, 36);
    x.fillText("BATERIA", 118, 152);
    x.font = "800 50px 'Consolas', monospace";
    x.fillStyle = est.delta.startsWith("-") ? "#2fe06a" : "#ff6a4a";
    x.fillText(est.delta, 118, 80);
    x.fillStyle = "#ffc93a";
    x.fillText(String(Math.round(est.velocidade)), 522, 80);
    x.fillStyle = "#2a2d36";
    x.fillRect(38, 180, 160, 36);
    x.fillStyle = est.bateria > 0.25 ? "#3d9bff" : "#ff4a4a";
    x.fillRect(38, 180, 160 * Math.max(0, Math.min(1, est.bateria)), 36);
    x.fillStyle = "#2fe06a";
    x.fillRect(604, 30, 12, 300 * Math.max(0, Math.min(1, est.bateria)));
    x.fillStyle = est.modo ? "#2f6bd6" : "#1a2a55";
    x.fillRect(240, 224, 160, 46);
    x.fillStyle = "#ffffff";
    x.font = "800 30px 'Segoe UI', sans-serif";
    x.fillText(est.modo || "—", 320, 248);
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
  (b.userData.tampa as THREE.Group).position.z = -0.0025 * k;
  (b.userData.luz as THREE.MeshStandardMaterial).emissiveIntensity = 0.6 * k;
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
  p.rotation.x = -0.28 * k; // a ponta de baixo vem na direção do volante (+z)
}

/** Luzes de troca de marcha: f 0 apagadas, 1 todas acesas (brancas → vermelhas → azuis). */
export function luzesDeTroca(v: Volante, f: number) {
  const n = Math.round(Math.max(0, Math.min(1, f)) * LED_CORES.length);
  de(v).lmats.forEach((m, k) => (m.emissiveIntensity = k < n ? 2.4 : 0));
}

/** O que a tela mostra: marcha ("N", "1" a "8"), modo (ex.: "OT", "BOOST", "AERO"), delta ("-0.214"), bateria 0 a 1, km/h. */
export function telaDoVolante(v: Volante, dados: { marcha?: string; modo?: string; delta?: string; bateria?: number; velocidade?: number }) {
  const e = de(v);
  Object.assign(e.est, dados);
  e.desenhar();
}
