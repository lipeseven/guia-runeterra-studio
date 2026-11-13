// Cena mínima do kit/gps, IDÊNTICA nos dois motores (Remotion e HyperFrames só criam o canvas, carregam os .glb e
// chamam desenhar(tCena) a cada quadro). Dois carros pelo GPS real (podem se sobrepor), rastro na cor da equipe
// (2º carro da mesma equipe: cor2). Pista: o .glb do circuito sem transformação (o.pista) OU, sem modelo 3D, a pista
// plana traçada pelo GPS (o.pistaPlana = JSON de kit/gps/pista/<circuito>_plana.json).
import { cameraSeguindo, criarAmostrador, relogioComparacao } from "../src/gps.js";
import { ajustarPista, aplicarPose, criarPistaPlana, criarRastro, prepararCarro } from "../src/gps_three.js";

/** Parâmetros padrão do exemplo: Leclerc (volta 51) x Antonelli (volta 55), corrida do GP de São Paulo 2026,
 *  freada do S do Senna em tempo real. */
export const EXEMPLO = {
  voltas: ["11412_16_51", "11412_12_55"],
  inicio: 2.5,   // tempo de volta no 1º quadro (s)
  duracao: 4,    // duração da cena (s)
  fator: 1,      // 1 = tempo real; 2.2 = acelerado 2,2x
  rastro: 2.5,   // segundos de rastro atrás do carro
  camera: "fixa", // "fixa" (câmera parada no alto, o carro atravessa o quadro) ou "perseguicao"
};

/**
 * @param THREE módulo three
 * @param o { canvas, largura, altura, pista (gltf.scene) ou pistaPlana (JSON), carros: [{ cena (gltf.scene), volta (JSON) }],
 *            inicio, fator, rastro, camera }
 */
export function montarCena(THREE, o) {
  const p = { ...EXEMPLO, ...o };
  const renderer = new THREE.WebGLRenderer({ canvas: p.canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(p.largura, p.altura, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const cena = new THREE.Scene();
  cena.background = new THREE.Color(0xe9e9e6);
  cena.fog = new THREE.Fog(0xe9e9e6, 700, 2400);
  cena.add(new THREE.HemisphereLight(0xffffff, 0x7d7f76, 2.2));
  const sol = new THREE.DirectionalLight(0xfff2e0, 2.0);
  sol.position.set(-300, 700, 300);
  cena.add(sol);
  if (p.pistaPlana) cena.add(criarPistaPlana(THREE, p.pistaPlana));
  else {
    ajustarPista(p.pista);
    cena.add(p.pista);
  }

  const relogio = relogioComparacao({ fator: p.fator, inicio: p.inicio });
  const equipes = [];
  const itens = p.carros.map(({ cena: c, volta }) => {
    const am = criarAmostrador(volta);
    const carro = prepararCarro(THREE, c);
    const cor = equipes.includes(am.info.equipe) ? am.info.cor2 : am.info.cor;
    equipes.push(am.info.equipe);
    am.info.cor = cor;
    const rastro = criarRastro(THREE, cor);
    cena.add(carro, rastro);
    return { am, carro, rastro };
  });
  const cam = new THREE.PerspectiveCamera(p.camera === "fixa" ? 30 : 45, p.largura / p.altura, 0.3, 6000);

  // câmera fixa: no alto, ao lado do trecho percorrido pelo 1º carro na cena, mirando o centro do trecho
  let fixa = null;
  if (p.camera === "fixa") {
    const a = itens[0].am;
    const pts = [];
    for (let k = 0; k <= 40; k++) pts.push(a.pos(relogio((p.duracao * k) / 40)));
    const c = pts.reduce((m, q) => [m[0] + q[0] / pts.length, m[1] + q[1] / pts.length, m[2] + q[2] / pts.length], [0, 0, 0]);
    const d = [pts[40][0] - pts[0][0], pts[40][2] - pts[0][2]];
    const l = Math.hypot(d[0], d[1]) || 1;
    const n = [-d[1] / l, d[0] / l];
    const R = Math.max(40, l * (p.distancia ?? 0.5));
    fixa = { pos: [c[0] + n[0] * R, c[1] + R * 0.6, c[2] + n[1] * R], alvo: c };
  }

  function desenhar(tCena) {
    const t = relogio(tCena);
    for (const it of itens) {
      aplicarPose(it.carro, it.am.pose(t));
      it.rastro.visible = p.rastro > 0;
      if (p.rastro > 0) it.rastro.atualizar(it.am.rastro(t - p.rastro * p.fator, t, { passo: 1, elev: 0.08 }));
    }
    const v = fixa ?? cameraSeguindo(itens.map((i) => i.am), t, { atras: 16, altura: 6 });
    cam.position.set(...v.pos);
    cam.lookAt(...v.alvo);
    renderer.render(cena, cam);
    return itens.map((i) => ({ sigla: i.am.info.sigla, cor: i.am.info.cor, kmh: Math.round(i.am.vel(t) * 3.6), t }));
  }
  return { desenhar, renderer, itens };
}
