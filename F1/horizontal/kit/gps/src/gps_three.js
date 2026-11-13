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

/** Ajusta materiais da pista para render (recorte de alfa em cercas/árvores). */
export function ajustarPista(cenaPista) {
  cenaPista.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (m.map && (m.transparent || m.alphaTest > 0 || m.alphaMap)) { m.alphaTest = 0.5; m.transparent = false; m.depthWrite = true; }
    }
  });
}
