// Adaptador three.js do kit/gps (opcional; usado pelos dois motores, que desenham em three.js).
// Não importa o three: recebe o módulo THREE como parâmetro (cada motor usa a própria cópia/versão).
import { corNumero, faixa } from "./gps.js";

/** Envolve a cena de um carro .glb num grupo com frente em +Z, rodas no chão (y = 0) e centro no eixo Y. */
export function prepararCarro(THREE, cenaCarro) {
  cenaCarro.updateMatrixWorld(true);
  const caixa = new THREE.Box3().setFromObject(cenaCarro);
  const c = caixa.getCenter(new THREE.Vector3());
  const g = new THREE.Group();
  cenaCarro.position.sub(new THREE.Vector3(c.x, caixa.min.y, c.z));
  g.add(cenaCarro);
  g.userData.tamanho = caixa.getSize(new THREE.Vector3());
  return g;
}

/** Coloca o objeto na pose do amostrador (yaw/pitch/roll pelo asfalto). */
export function aplicarPose(obj, pose) {
  obj.position.set(pose.x, pose.y, pose.z);
  obj.rotation.order = "YXZ";
  obj.rotation.set(-pose.pitch, pose.yaw, pose.roll);
}

/** Malha do rastro (fita na cor da equipe, ponta antiga transparente). atualizar(rastro) a cada quadro. */
export function criarRastro(THREE, cor, { largura = 1.1, opacidade = 0.95 } = {}) {
  const geo = new THREE.BufferGeometry();
  const mat = new THREE.MeshBasicMaterial({
    vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4,
  });
  const malha = new THREE.Mesh(geo, mat);
  malha.renderOrder = 5;
  malha.frustumCulled = false;
  const rgb = new THREE.Color(corNumero(cor));
  malha.atualizar = (rastro) => {
    const f = faixa(rastro.pontos, { largura });
    const n = f.posicoes.length / 3;
    const cores = new Float32Array(n * 4);
    for (let k = 0; k < n; k++) cores.set([rgb.r, rgb.g, rgb.b, f.alfa[k] * opacidade], k * 4);
    geo.setAttribute("position", new THREE.BufferAttribute(f.posicoes, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(cores, 4));
    geo.setIndex(new THREE.BufferAttribute(f.indices, 1));
    geo.computeBoundingSphere();
  };
  return malha;
}

/** Pista PLANA (modo sem modelo 3D) a partir de pista/<circuito>_plana.json: chão claro, borda branca (zebra), asfalto
 *  e linha de chegada no ponto 0 (início da volta de referência). y = 0, no mesmo sistema das voltas do modo "plana".
 *  As camadas de baixo não escrevem profundidade (sem z-fighting); só o asfalto escreve. */
export function criarPistaPlana(THREE, plana, { corChao = 0xdedfd9, corBorda = 0xf6f6f3, corAsfalto = 0x5d6066, corLinha = 0xffffff } = {}) {
  const c = plana.centro;
  const pts = c.x.map((x, k) => [x, 0, c.z[k]]);
  if (c.fechada) pts.push(pts[0]);
  const g = new THREE.Group();
  g.name = `pista_plana_${plana.circuito}`;
  const camada = (largura, cor, ordem, escreve) => {
    const f = faixa(pts, { largura, afinar: false });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(f.posicoes, 3));
    geo.setIndex(new THREE.BufferAttribute(f.indices, 1));
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: cor, side: THREE.DoubleSide, depthWrite: escreve }));
    m.renderOrder = ordem;
    return m;
  };
  // chão: retângulo em volta da pista
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const p of pts) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[2]); z1 = Math.max(z1, p[2]); }
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0 + 600, z1 - z0 + 600),
    new THREE.MeshLambertMaterial({ color: corChao, depthWrite: false }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.set((x0 + x1) / 2, 0, (z0 + z1) / 2);
  chao.renderOrder = -2;
  g.add(chao, camada(plana.largura_m + 2 * plana.zebra_m, corBorda, -1, false), camada(plana.largura_m, corAsfalto, 0, true));
  // linha de chegada: faixa de 1,2 m atravessando a pista no ponto 0
  const a = pts[0], b = pts[1];
  const ang = Math.atan2(b[0] - a[0], b[2] - a[2]);
  const linha = new THREE.Mesh(new THREE.PlaneGeometry(plana.largura_m, 1.2),
    new THREE.MeshLambertMaterial({ color: corLinha, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  linha.rotation.order = "YXZ";
  linha.rotation.set(-Math.PI / 2, ang, 0);
  linha.position.set(a[0], 0.002, a[2]);
  linha.renderOrder = 1;
  g.add(linha);
  return g;
}

/** Ajusta materiais da pista para render (recorte de alfa em cercas/árvores). */
export function ajustarPista(cenaPista) {
  cenaPista.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (m.map && (m.transparent || m.alphaTest > 0 || m.alphaMap)) { m.alphaTest = 0.5; m.transparent = false; m.depthWrite = true; }
    }
  });
}
