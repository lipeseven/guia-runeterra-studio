// Freio de F1 em 3D: disco de carbono, pinça de 6 pistões e furos de ventilação. Unidades em mm.
// Um valor manda em cada estado: p = pressão no pedal (0 a 1), H = calor no disco (0 a 1). render(t) é função pura do tempo.
// Tempos em segundos dentro do clipe, presos às palavras do roteiro (o clipe começa em "Quando").
import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {runSim} from 'teardown-kit/runtime.js';
import {createStage} from 'teardown-kit/stage3d.js';
import {keyed, prog, rng} from 'teardown-kit/util.js';

const R = 139;           // raio externo do disco (278 mm)
const R_IN = 84;
const ESP = 32;          // espessura do disco
const FOLGA = 5;         // pastilha solta até o disco
const FUROS = 1080;      // 3 fileiras de 360 na borda
const ANG = Math.PI / 3; // centro da pinça
const ABRE = 0.62;       // meia abertura da pinça em radianos

const PRESSAO = [[0, 0], [2.7, 0], [3.7, 1], [13.4, 1]];
const CALOR = [[0, 0], [5.9, 0], [8.2, 1], [11, 1], [13.4, 0.72]];
const RAIOX = [[0, 0], [1.9, 0], [2.6, 1], [5.2, 1], [5.9, 0], [13.4, 0]];
const u = [Math.cos(ANG), Math.sin(ANG)];
const AR = -0.5; // ângulo da borda que a câmera visita
const borda = [R * Math.cos(AR), R * Math.sin(AR)];
const CAMERA = [ // [tempo, posição, alvo, para cima]
  [0, [330, -190, 1520], [12, 26, 0], [0, 1, 0]],
  [1.8, [290, -150, 1400], [16, 30, 0], [0, 1, 0]],
  [3.0, [u[0] * 730, u[1] * 730, 80], [u[0] * 118, u[1] * 118, 0], [0, 0, 1]],
  [5.2, [u[0] * 680, u[1] * 680, 50], [u[0] * 118, u[1] * 118, 0], [0, 0, 1]],
  [6.3, [210, -240, 1620], [8, 26, 0], [0, 1, 0]],
  [8.7, [130, -190, 1440], [8, 26, 0], [0, 1, 0]],
  [10.0, [borda[0] * 2.25, borda[1] * 2.25, 120], [borda[0], borda[1], 0], [0, 0, 1]],
  [13.4, [borda[0] * 2.0, borda[1] * 2.0, 96], [borda[0], borda[1], 0], [0, 0, 1]],
];

function textura(seed) {
  const c = document.createElement('canvas');
  c.width = c.height = 1536;
  const g = c.getContext('2d');
  const s = rng(seed);
  g.fillStyle = '#34363a';
  g.fillRect(0, 0, 1536, 1536);
  for (let i = 0; i < 9; i++) { // manchas largas do carbono, como no disco real
    const a = s() * 6.28;
    g.fillStyle = `rgba(${s() > 0.5 ? '120,122,128' : '12,12,14'},${0.1 + s() * 0.14})`;
    g.beginPath();
    g.moveTo(768, 768);
    g.arc(768, 768, 780, a, a + 0.3 + s() * 0.6);
    g.fill();
  }
  for (let r = 0; r < 770; r += 1.6) { // marcas de pastilha, em círculos
    g.strokeStyle = `rgba(${s() > 0.5 ? '160,162,170' : '6,6,8'},${s() * 0.2})`;
    g.lineWidth = 0.5 + s();
    g.beginPath();
    g.arc(768, 768, r, 0, 6.3);
    g.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** Brilho do calor: quase branco, para a cor não lavar, com as marcas circulares do disco um pouco mais escuras. */
function texturaBrilho(seed) {
  const c = document.createElement('canvas');
  c.width = c.height = 1024;
  const g = c.getContext('2d');
  const s = rng(seed);
  g.fillStyle = '#ffffff';
  g.fillRect(0, 0, 1024, 1024);
  for (let r = 0; r < 520; r += 2) {
    g.strokeStyle = `rgba(40,8,0,${s() * 0.6})`;
    g.lineWidth = 0.6 + s() * 1.4;
    g.beginPath();
    g.arc(512, 512, r, 0, 6.3);
    g.stroke();
  }
  return new THREE.CanvasTexture(c);
}

function anel(externo, interno, buracos = []) {
  const f = new THREE.Shape();
  if (typeof externo === 'number') f.absarc(0, 0, externo, 0, Math.PI * 2, false);
  else externo.forEach(([x, y], i) => (i ? f.lineTo(x, y) : f.moveTo(x, y)));
  const h = new THREE.Path();
  h.absarc(0, 0, interno, 0, Math.PI * 2, true);
  f.holes.push(h);
  buracos.forEach(([x, y, r]) => {
    const b = new THREE.Path();
    b.absarc(x, y, r, 0, Math.PI * 2, true);
    f.holes.push(b);
  });
  return f;
}

function setor(r1, r2, a1, a2, prof, chanfro = 1.5) {
  const f = new THREE.Shape();
  f.absarc(0, 0, r2, a1, a2, false);
  f.absarc(0, 0, r1, a2, a1, true);
  return new THREE.ExtrudeGeometry(f, {depth: prof, bevelEnabled: chanfro > 0, bevelSize: chanfro, bevelThickness: chanfro, bevelSegments: 2, curveSegments: 48});
}

const DEFAULTS = {duration: 13.4, fps: 30, hud: {enabled: false}, director: {enabled: false}, theme: 'dark'};

runSim(DEFAULTS, async ({canvas, capture}) => {
  const hud = {viewport: () => ({top: 300, bottom: 0})}; // deixa o terço de cima livre para a legenda
  const st = createStage(canvas, hud, {capture, bg: '#0a0d15', fov: 24, exposure: 0.85, bloom: {strength: 0.42, radius: 0.5, threshold: 0.72}});
  const {scene, camera, renderer} = st;
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.1;
  const luz = new THREE.DirectionalLight('#ffffff', 1.0);
  luz.position.set(300, 500, 900);
  scene.add(luz);
  const contra = new THREE.DirectionalLight('#6fb7ff', 0.6);
  contra.position.set(-500, -300, -300);
  scene.add(contra);
  const lado = new THREE.DirectionalLight('#ffffff', 1.5);
  lado.position.set(u[0] * 900, u[1] * 900, 200);
  scene.add(lado);

  // ---- parte que gira
  const gira = new THREE.Group();
  scene.add(gira);
  const mapa = textura(278);
  const matDisco = new THREE.MeshStandardMaterial({map: mapa, roughness: 0.82, metalness: 0.1, emissiveMap: texturaBrilho(279), emissive: '#000000', envMapIntensity: 0.5});
  const geoDisco = new THREE.ExtrudeGeometry(anel(R, R_IN), {depth: ESP, bevelEnabled: true, bevelSize: 0.8, bevelThickness: 0.8, bevelSegments: 2, curveSegments: 160});
  geoDisco.translate(0, 0, -ESP / 2);
  const uv = geoDisco.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, geoDisco.attributes.position.getX(i) / (2 * R) + 0.5, geoDisco.attributes.position.getY(i) / (2 * R) + 0.5);
  gira.add(new THREE.Mesh(geoDisco, matDisco));

  const matFuro = new THREE.MeshBasicMaterial({color: '#050506'});
  const furos = new THREE.InstancedMesh(new THREE.CylinderGeometry(1.15, 1.15, 2, 10), matFuro, FUROS);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const eixoY = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < FUROS; i++) {
    const fileira = i % 3;
    const a = (i / FUROS) * Math.PI * 2 + fileira * 0.004;
    const pos = new THREE.Vector3(Math.cos(a) * (R + 0.2), Math.sin(a) * (R + 0.2), [-9, 0, 9][fileira]);
    q.setFromUnitVectors(eixoY, new THREE.Vector3(Math.cos(a), Math.sin(a), 0));
    m.compose(pos, q, new THREE.Vector3(1, 1, 1));
    furos.setMatrixAt(i, m);
  }
  gira.add(furos);

  // sino de alumínio com bordas recortadas, parafusos e o anel de furos do cubo
  const matMetal = new THREE.MeshStandardMaterial({color: '#8e95a0', metalness: 0.92, roughness: 0.46, envMapIntensity: 0.9});
  const contorno = [];
  for (let i = 0; i <= 240; i++) {
    const a = (i / 240) * Math.PI * 2;
    const r = 90 + 4.5 * Math.cos(a * 12);
    contorno.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  const buracos = [];
  for (let i = 0; i < 12; i++) buracos.push([Math.cos((i / 12) * 6.283) * 52, Math.sin((i / 12) * 6.283) * 52, 7.5]);
  const sino = new THREE.Mesh(new THREE.ExtrudeGeometry(anel(contorno, 34, buracos), {depth: 5, bevelEnabled: true, bevelSize: 0.6, bevelThickness: 0.6, bevelSegments: 2, curveSegments: 24}), matMetal);
  sino.position.z = ESP / 2 + 0.6;
  gira.add(sino);
  const matOuro = new THREE.MeshStandardMaterial({color: '#c98a35', metalness: 0.95, roughness: 0.38});
  for (let i = 0; i < 12; i++) {
    const a = ((i + 0.5) / 12) * Math.PI * 2;
    const base = new THREE.Mesh(new THREE.CylinderGeometry(6, 6.6, 4, 6), matOuro);
    base.rotation.x = Math.PI / 2;
    base.position.set(Math.cos(a) * 80, Math.sin(a) * 80, ESP / 2 + 7.5);
    gira.add(base);
    const cabeca = new THREE.Mesh(new THREE.CylinderGeometry(3.4, 3.4, 3, 12), matMetal);
    cabeca.rotation.x = Math.PI / 2;
    cabeca.position.set(Math.cos(a) * 80, Math.sin(a) * 80, ESP / 2 + 10.4);
    gira.add(cabeca);
  }

  // ---- pinça fixa: duas metades ligadas por pontes fora do disco, 3 pistões de cada lado
  const pinca = new THREE.Group();
  scene.add(pinca);
  const a1 = ANG - ABRE;
  const a2 = ANG + ABRE;
  const matPinca = new THREE.MeshStandardMaterial({color: '#1d7f9e', metalness: 0.72, roughness: 0.42, transparent: true});
  const fora = new THREE.Mesh(setor(R_IN + 2, R + 18, a1, a2, 30), matPinca);
  fora.position.z = ESP / 2 + 20;
  const dentro = fora.clone();
  dentro.position.z = -ESP / 2 - 50;
  const ponte = new THREE.Mesh(setor(R + 5, R + 18, a1 + 0.02, a2 - 0.02, ESP + 42), matPinca);
  ponte.position.z = -ESP / 2 - 21;
  pinca.add(fora, dentro, ponte);

  const matPistao = new THREE.MeshStandardMaterial({color: '#e8ebef', metalness: 0.95, roughness: 0.3});
  const matPastilha = new THREE.MeshStandardMaterial({color: '#191a1d', roughness: 0.9, emissive: '#000000'});
  const matCosta = new THREE.MeshStandardMaterial({color: '#a9262a', metalness: 0.6, roughness: 0.45});
  const moveis = [];
  for (const lado of [1, -1]) {
    const g = new THREE.Group();
    const pastilha = new THREE.Mesh(setor(R_IN + 8, R - 4, a1 + 0.05, a2 - 0.05, 12, 0.6), matPastilha);
    pastilha.position.z = lado > 0 ? 0 : -12;
    const costa = new THREE.Mesh(setor(R_IN + 6, R - 2, a1 + 0.03, a2 - 0.03, 3, 0.4), matCosta);
    costa.position.z = lado > 0 ? 12 : -15;
    g.add(pastilha, costa);
    for (const d of [-0.4, 0, 0.4]) {
      const a = ANG + d;
      const pistao = new THREE.Mesh(new THREE.CylinderGeometry(18, 18, 26, 36), matPistao);
      pistao.rotation.x = Math.PI / 2;
      pistao.position.set(Math.cos(a) * 112, Math.sin(a) * 112, lado * (15 + 13));
      g.add(pistao);
    }
    g.userData.lado = lado;
    moveis.push(g);
    scene.add(g);
  }

  // ---- partículas: tudo calculado a partir do tempo
  const s = rng(44);
  const NF = 90;
  const faisca = Array.from({length: NF}, () => ({fase: s(), a: ANG + (s() - 0.5) * 1.1, z: (s() - 0.5) * ESP * 1.6, v: 130 + s() * 240}));
  const geoF = new THREE.BufferGeometry();
  geoF.setAttribute('position', new THREE.BufferAttribute(new Float32Array(NF * 3), 3));
  const matF = new THREE.PointsMaterial({color: '#ffc46b', size: 3.2, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false});
  scene.add(new THREE.Points(geoF, matF));

  const NA = 420;
  const ar = Array.from({length: NA}, () => ({fase: s(), da: (s() - 0.5) * 0.95, z: (s() - 0.5) * 34, v: 0.7 + s() * 0.8}));
  const geoA = new THREE.BufferGeometry();
  geoA.setAttribute('position', new THREE.BufferAttribute(new Float32Array(NA * 3), 3));
  const matA = new THREE.PointsMaterial({color: '#7fdcff', size: 1.5, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false});
  scene.add(new THREE.Points(geoA, matA));

  const cor = new THREE.Color();
  const v1 = new THREE.Vector3();
  const quente = (h) => { // preto → vermelho escuro → laranja → amarelo
    if (h < 0.4) return cor.set('#000000').lerp(new THREE.Color('#7c1400'), h / 0.4);
    if (h < 0.8) return cor.set('#7c1400').lerp(new THREE.Color('#f03c04'), (h - 0.4) / 0.4);
    return cor.set('#f03c04').lerp(new THREE.Color('#ff7c16'), (h - 0.8) / 0.2);
  };
  const entre = (a, b, k) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
  const suave = (x) => x * x * (3 - 2 * x);

  return {
    render(t) {
      const p = keyed(PRESSAO, t);
      const H = keyed(CALOR, t);
      const x = keyed(RAIOX, t);

      gira.rotation.z = -(2.1 * t - 0.055 * t * t); // desacelerando

      const pinçaOpaca = x < 0.01;
      matPinca.opacity = 1 - x * 0.9;
      matPinca.depthWrite = pinçaOpaca;
      moveis.forEach((g) => {
        g.position.z = g.userData.lado * (ESP / 2 + FOLGA * (1 - p));
      });

      matDisco.emissive.copy(quente(H));
      matDisco.emissiveIntensity = H * 0.62;
      matPastilha.emissive.set('#ff3a00');
      matPastilha.emissiveIntensity = H * 0.35;

      // faíscas saem da pastilha só com o disco quente
      const pf = geoF.attributes.position.array;
      faisca.forEach((f, i) => {
        const vida = (t * 0.9 + f.fase) % 1;
        const r = R - 10 + vida * f.v * 0.5;
        pf[i * 3] = Math.cos(f.a - vida * 0.5) * r;
        pf[i * 3 + 1] = Math.sin(f.a - vida * 0.5) * r - vida * vida * 60;
        pf[i * 3 + 2] = f.z;
      });
      geoF.attributes.position.needsUpdate = true;
      matF.opacity = Math.max(0, (H - 0.45) * 1.8) * (t < 10 ? 1 : 1 - prog(t, 10, 10.6));

      // ar entrando pelos furos da borda
      const pa = geoA.attributes.position.array;
      ar.forEach((f, i) => {
        const vida = (t * f.v + f.fase) % 1;
        const r = R + 1 + (1 - vida) * 150;
        const a = AR + f.da * (1 - vida * 0.25);
        pa[i * 3] = Math.cos(a) * r;
        pa[i * 3 + 1] = Math.sin(a) * r;
        pa[i * 3 + 2] = f.z + (1 - vida) * f.z * 1.5;
      });
      geoA.attributes.position.needsUpdate = true;
      matA.opacity = prog(t, 9.2, 10.2) * 0.95;

      // câmera
      let k = 0;
      while (k < CAMERA.length - 2 && t >= CAMERA[k + 1][0]) k++;
      const A = CAMERA[k];
      const B = CAMERA[k + 1];
      const c = suave(Math.min(1, Math.max(0, (t - A[0]) / (B[0] - A[0]))));
      camera.position.set(...entre(A[1], B[1], c));
      camera.up.copy(v1.set(...entre(A[3], B[3], c)).normalize());
      camera.lookAt(...entre(A[2], B[2], c));
      st.render();
      return {};
    },
    resize() {
      st.resize();
    },
  };
});
