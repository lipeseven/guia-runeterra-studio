// Cena do teste VHE (ver index.html): decupagem em assets/cfg.js (preparar.py). desenhar(T) é determinístico em T
// (segundos de cena): nada depende do quadro anterior, então o render pode pular/repetir quadros.
import { cameraSeguindo, criarAmostrador, faixa } from "./assets/kit/gps/src/gps.js";
import { ajustarPista, aplicarPose, criarRastro, prepararCarro } from "./assets/kit/gps/src/gps_three.js";

const fmt = (v, c = 1) => v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
const tempoVolta = (s) => `${Math.floor(s / 60)}:${fmt(s % 60, 3).padStart(6, "0")}`;

export function montar(THREE, { cfg, ideal, livre, pista, carro, canvas }) {
  const W = 1920, H = 1080;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;
  const cena = new THREE.Scene();
  cena.background = new THREE.Color(0xecebe6);
  cena.fog = new THREE.Fog(0xecebe6, 600, 2600);
  cena.add(new THREE.HemisphereLight(0xffffff, 0x8a8f7a, 2.3));
  const sol = new THREE.DirectionalLight(0xfff4e2, 1.8);
  sol.position.set(-300, 800, 250);
  cena.add(sol);
  ajustarPista(pista);
  cena.add(pista);

  const am = criarAmostrador(ideal), amGps = criarAmostrador(livre);
  const cor = new THREE.Color(cfg.titulo.cor);
  const corHex = cfg.titulo.cor;

  // carro (Ferrari SF-26 do projeto)
  const car = prepararCarro(THREE, carro);
  cena.add(car);

  // linha do GPS do OpenF1 (volta inteira, sem correção lateral): fita azul-clara com contorno escuro, rente ao chão
  const C = livre.caminho;
  const ptsGps = C.x.map((x, i) => [x, C.y[i] + 0.04, C.z[i]]);
  const fita = (pts, largura, corFita, ordem, opac = 1) => {
    const f = faixa(pts, { largura, afinar: false });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(f.posicoes, 3));
    g.setIndex(new THREE.BufferAttribute(f.indices, 1));
    const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: corFita, transparent: opac < 1, opacity: opac, depthWrite: false,
      side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }));
    m.renderOrder = ordem;
    m.frustumCulled = false;
    return m;
  };
  const gpsFino = new THREE.Group();
  gpsFino.add(fita(ptsGps, 0.75, 0x11324a, 3), fita(ptsGps.map((p) => [p[0], p[1] + 0.005, p[2]]), 0.42, 0x8fd3ff, 4));
  const gpsGrosso = fita(ptsGps, 5, 0x8fd3ff, 3);
  cena.add(gpsFino, gpsGrosso);
  // rastro do carro: fino (recortes) e grosso (mapa)
  const rastro = criarRastro(THREE, corHex, { largura: 0.9 });
  const rastroMapa = criarRastro(THREE, corHex, { largura: 9, opacidade: 1 });
  cena.add(rastro, rastroMapa);
  // marcador do carro no mapa (disco na cor da equipe com aro branco)
  const marca = new THREE.Group();
  const aro = new THREE.Mesh(new THREE.CircleGeometry(19, 40), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false }));
  const disco = new THREE.Mesh(new THREE.CircleGeometry(14, 40), new THREE.MeshBasicMaterial({ color: cor, depthTest: false }));
  aro.rotation.x = disco.rotation.x = -Math.PI / 2;
  disco.position.y = 0.1;
  aro.renderOrder = 20; disco.renderOrder = 21;
  marca.add(aro, disco);
  cena.add(marca);

  const cam = new THREE.PerspectiveCamera(30, W / H, 1, 6000);
  const v3 = new THREE.Vector3();
  // altura do chão perto de (x, z): ponto mais próximo do caminho
  const Ci = ideal.caminho;
  const yPerto = (x, z) => {
    let b = Infinity, y = 0;
    for (let i = 0; i < Ci.x.length; i += 2) { const d = (Ci.x[i] - x) ** 2 + (Ci.z[i] - z) ** 2; if (d < b) { b = d; y = Ci.y[i]; } }
    return y;
  };
  // enquadramento do mapa: caixa do caminho, eixo longo na horizontal da tela (rotação, nunca espelho)
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (let i = 0; i < Ci.x.length; i++) { x0 = Math.min(x0, Ci.x[i]); x1 = Math.max(x1, Ci.x[i]); z0 = Math.min(z0, Ci.z[i]); z1 = Math.max(z1, Ci.z[i]); }
  const tanV = Math.tan(THREE.MathUtils.degToRad(15));
  const ALTURA_CIMA = 70;   // m: ~37 m de pista na vertical da tela (carro ~5,6 m = ~160 px)
  const mapa = (() => {
    const cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
    const largo = z1 - z0 > x1 - x0;  // eixo z mais longo: z na horizontal
    const ext = largo ? [z1 - z0, x1 - x0] : [x1 - x0, z1 - z0];   // [horizontal, vertical] na tela
    const h = Math.max(ext[1] / 2 / tanV, ext[0] / 2 / (tanV * (W / H))) * 1.12;
    return { pos: [cx + 0.01, h, cz], alvo: [cx, 0, cz], up: largo ? [-1, 0, 0] : [0, 0, -1] };
  })();

  // elementos do HUD
  const $ = (q) => document.querySelector(q);
  const tit = $("#titulo"), rot = $("#rotulo"), vel = $("#vel"), lat = $("#lat"), zeb = $("#zebra"), fora = $("#fora");
  tit.querySelector(".barra").style.background = corHex;
  tit.querySelector(".nome").textContent = cfg.titulo.piloto;
  tit.querySelector(".equipe").textContent = cfg.titulo.equipe;
  tit.querySelector(".sessao").textContent = `Melhor volta · ${cfg.titulo.sessao}`;
  tit.querySelector(".tempo").textContent = `Volta ${cfg.titulo.volta} · ${tempoVolta(cfg.titulo.tempo)}`;
  lat.querySelector(".cq").style.background = corHex;
  const PXM = 46;              // px por metro na barra lateral
  const LB = 1120;             // largura útil da barra (px)
  const barra = { asf: lat.querySelector(".asf"), be: lat.querySelector(".be"), bd: lat.querySelector(".bd"),
                  car: lat.querySelector(".carro"), gps: lat.querySelector(".gps"),
                  e: lat.querySelector(".topo .e"), d: lat.querySelector(".topo .d"), m: lat.querySelector(".topo .m") };
  barra.car.style.background = corHex;

  const segDe = (T) => cfg.segmentos.find((s) => T >= s.T0 && T < s.T1) || cfg.segmentos[cfg.segmentos.length - 1];

  return function desenhar(T) {
    const sg = segDe(T);
    // tempo de volta
    let t;
    if (sg.tipo === "mapa") {
      const u = Math.max(0, T - sg.segura) / (sg.T1 - sg.T0 - sg.segura);
      t = sg.t0 + (sg.t1 - sg.t0) * Math.min(1, u);
    } else t = sg.t0 + (T - sg.T0) * sg.fator;
    const p = am.pose(t);
    aplicarPose(car, p);
    const frente = [Math.sin(p.yaw), Math.cos(p.yaw)], esq = [Math.cos(p.yaw), -Math.sin(p.yaw)];
    // câmera
    cam.up.set(0, 1, 0);
    if (sg.tipo === "mapa") {
      cam.fov = 30;
      cam.up.set(...mapa.up);
      cam.position.set(...mapa.pos);
      cam.lookAt(...mapa.alvo);
      cena.fog.near = 5000; cena.fog.far = 9000;
    } else if (sg.tipo === "cima") {
      // de cima, seguindo o carro: rumo médio (±0,9 s) para cima da tela -> esquerda da tela = esquerda do carro
      cam.fov = 30;
      let fx = 0, fz = 0;
      for (let k = -6; k <= 6; k++) { const q = am.pose(t + k * 0.15); fx += Math.sin(q.yaw); fz += Math.cos(q.yaw); }
      const l = Math.hypot(fx, fz) || 1; fx /= l; fz /= l;
      // centro da tela 2 m atrás do carro: o carro fica acima do painel lateral e o rastro aparece embaixo
      const h = ALTURA_CIMA, cx = p.x - fx * 2, cz = p.z - fz * 2;
      cam.position.set(cx - fx * h * 0.18, p.y + h, cz - fz * h * 0.18);
      cam.up.set(fx, 0, fz);
      cam.lookAt(cx, p.y, cz);
      cena.fog.near = 2000; cena.fog.far = 6000;
    } else {
      cam.fov = 40;
      const c = cameraSeguindo(am, t, { atras: 16, altura: 9, adiante: 2, janela: 0.5 });
      cam.position.set(...c.pos);
      cam.lookAt(...c.alvo);
      cena.fog.near = 400; cena.fog.far = 1600;
    }
    cam.updateProjectionMatrix();
    // rastro / linhas
    const noMapa = sg.tipo === "mapa";
    gpsGrosso.visible = noMapa; gpsFino.visible = !noMapa;
    rastroMapa.visible = noMapa; rastro.visible = !noMapa; marca.visible = noMapa; car.visible = !noMapa;
    if (noMapa) {
      rastroMapa.atualizar(am.rastro(Math.max(am.tIni, sg.t0), t, { passo: 4, elev: 0.3 }));
      marca.position.set(p.x, p.y + 1, p.z);
    } else rastro.atualizar(am.rastro(Math.max(sg.t0 - 1.5, t - 3.0), t, { passo: 1, elev: 0.06 }));
    renderer.render(cena, cam);

    // HUD
    tit.style.display = noMapa && T < sg.segura ? "flex" : "none";
    rot.style.display = noMapa && T < sg.segura ? "none" : "block";
    vel.querySelector(".n").textContent = String(Math.round(p.vel * 3.6));
    const tv = Math.min(Math.max(t, 0), ideal.duracao);
    if (noMapa) {
      rot.querySelector(".curva").textContent = "Volta inteira";
      rot.querySelector(".ritmo").textContent = `acelerada ${fmt((sg.t1 - sg.t0) / (sg.T1 - sg.T0 - sg.segura), 1)}× · ${tempoVolta(tv)}`;
    } else {
      rot.querySelector(".curva").textContent = sg.nome;
      rot.querySelector(".ritmo").textContent = `${sg.fator === 1 ? "tempo real" : `acelerado ${fmt(sg.fator, 1)}×`} · ` +
        `${sg.tipo === "cima" ? "câmera de cima, seguindo" : "câmera atrás"} · ${tempoVolta(tv)}`;
    }
    const L = am.lateral(t);
    const mostraLat = !noMapa && L && isFinite(L.bordaEsq) && isFinite(L.bordaDir);
    lat.style.display = mostraLat ? "block" : "none";
    zeb.style.display = mostraLat && L.zebra >= 0.1 ? "block" : "none";
    fora.style.display = mostraLat && L.foraAsfalto >= 0.1 ? "block" : "none";
    if (mostraLat) {
      const largura = L.bordaEsq + L.bordaDir;
      // a barra mostra a pista como o carro vê: esquerda à esquerda; o centro da barra = centro do asfalto
      const meio = LB / 2;
      const xm = (off) => meio + (off - (L.bordaEsq - L.bordaDir) / 2) * -PXM; // off = m à esquerda do centro do carro
      const xe = xm(L.bordaEsq), xd = xm(-L.bordaDir);
      barra.asf.style.left = `${xe}px`; barra.asf.style.width = `${xd - xe}px`;
      barra.be.style.left = `${xe - 2}px`; barra.bd.style.left = `${xd - 2}px`;
      barra.car.style.left = `${xm(1.0)}px`; barra.car.style.width = `${2.0 * PXM}px`;
      // linha do GPS: deslocamento lateral do ponto do OpenF1 no mesmo instante, na esquerda do carro
      const g = amGps.pos(t);
      const dg = (g[0] - p.x) * esq[0] + (g[2] - p.z) * esq[1];
      barra.gps.style.left = `${xm(dg)}px`;
      barra.gps.style.display = Math.abs(dg) < 12 ? "block" : "none";
      const pe = L.bordaEsq - 1.0, pd = L.bordaDir - 1.0;   // do pneu (lado do carro) à borda
      barra.e.innerHTML = `◄ pneu esq. → borda: <b>${fmt(pe)} m</b>`;
      barra.d.innerHTML = `pneu dir. → borda: <b>${fmt(pd)} m</b> ►`;
      barra.m.innerHTML = `asfalto ${fmt(largura)} m`;
      fora.textContent = `${Math.round(L.foraAsfalto * 100)}% do carro fora do asfalto`;
    }
    return { t, s: p.s };
  };
}
