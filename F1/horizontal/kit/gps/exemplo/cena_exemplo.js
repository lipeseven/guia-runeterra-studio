// Cena mínima do kit/gps, IDÊNTICA nos dois motores (Remotion e HyperFrames só criam o canvas, carregam os .glb e
// chamam desenhar(tCena) a cada quadro). Dois carros pelo GPS real (podem se sobrepor), rastro na cor da equipe
// (2º carro da mesma equipe: cor2). Pista: o .glb do circuito sem transformação (o.pista) OU, sem modelo 3D, a pista
// plana traçada pelo GPS (o.pistaPlana = JSON de kit/gps/pista/<circuito>_plana.json).
import { cameraSeguindo, criarAmostrador, relogioComparacao } from "../src/gps.js";
import { ajustarPista, aplicarPose, criarPistaPlana, criarRastro, prepararCarro } from "../src/gps_three.js";
import { criarMundoPlano, opacidadeCarro } from "../src/gps_mundo.js";

/** Parâmetros padrão do exemplo: Leclerc (volta 51) x Antonelli (volta 55), corrida do GP de São Paulo 2026,
 *  freada do S do Senna em tempo real. */
export const EXEMPLO = {
  voltas: ["11412_16_51", "11412_12_55"],
  inicio: 2.5,   // tempo de volta no 1º quadro (s)
  duracao: 4,    // duração da cena (s)
  fator: 1,      // 1 = tempo real; 2.2 = acelerado 2,2x
  rastro: 2.5,   // segundos de rastro atrás do carro
  camera: "fixa", // "fixa" (câmera parada no alto, o carro atravessa o quadro), "perseguicao" ou "alta" (panorâmica de longe)
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
  if (p.pistaPlana) {
    const pista = criarPistaPlana(THREE, p.pistaPlana);
    cena.add(pista);
    if (p.mundo) {
      // o mundo (chão em ladrilhos, zebras, arquibancadas, prédios, placa da curva) substitui o chão liso da pista plana;
      // céu claro levemente azul e névoa mais perto: a borda do chão não aparece no horizonte
      pista.children[0].visible = false;
      cena.add(criarMundoPlano(THREE, p.pistaPlana, { curvas: p.curvas ?? [] }));
      cena.background = new THREE.Color(0xe3ecf2);
      cena.fog = new THREE.Fog(0xe3ecf2, 450, 1500);
    }
  } else {
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
  const cam = new THREE.PerspectiveCamera(p.camera === "perseguicao" ? 45 : 30, p.largura / p.altura, 0.3, 6000);

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
    const poses = itens.map((it) => it.am.pose(t));
    for (const [k, it] of itens.entries()) {
      aplicarPose(it.carro, poses[k]);
      it.rastro.visible = p.rastro > 0;
      if (p.rastro > 0) it.rastro.atualizar(it.am.rastro(t - p.rastro * p.fator, t, { passo: 1, elev: 0.08 }));
    }
    // carros colados (o GPS real põe um dentro do outro): o de TRÁS vira fantasma (Felipe aceita um sobre o outro,
    // mas precisa ler quem está na frente). Suave: opacidade cai de 1 a 0,4 entre 9 m e 5 m de distância.
    if (p.fantasma !== false && itens.length === 2) {
      const [a, b] = poses;
      const d = Math.hypot(a.x - b.x, a.z - b.z);
      const bFrente = (b.x - a.x) * a.frente[0] + (b.z - a.z) * a.frente[2] > 0;
      const atras = bFrente ? 0 : 1;
      const op = d >= 9 ? 1 : d <= 5 ? 0.4 : 0.4 + (0.6 * (d - 5)) / 4;
      opacidadeCarro(itens[atras].carro, Math.round(op * 20) / 20);
      opacidadeCarro(itens[1 - atras].carro, 1);
    }
    // "alta" = panorâmica alta acompanhando os carros de longe (regra do Felipe: "levantar e ficar panorâmica");
    // janela longa na média do rumo para a câmera não virar junto com cada curva
    const v = fixa ?? cameraSeguindo(itens.map((i) => i.am), t,
      p.camera === "alta" ? { atras: 52, altura: 26, adiante: 8, janela: 1.6 } : { atras: 16, altura: 6 });
    cam.position.set(...v.pos);
    cam.lookAt(...v.alvo);
    renderer.render(cena, cam);
    return itens.map((i, k) => ({ sigla: i.am.info.sigla, cor: i.am.info.cor, kmh: Math.round(i.am.vel(t) * 3.6), t,
                                  pos: [poses[k].x, poses[k].y, poses[k].z] }));
  }
  return { desenhar, renderer, itens, cam };
}
