// kit/gps — núcleo independente de motor (JS puro, ES module; tipos em gps.d.ts).
// Lê uma volta preparada por py/preparar_volta.py (voltas/<sessao>_<piloto>_<volta>.json) e devolve um AMOSTRADOR:
//   s(t)          distância ao longo do caminho (m), sempre crescente (cúbica monotônica de Fritsch–Carlson)
//   pos(t)        [x, y, z] no sistema da pista da volta (three.js, Y para cima, metros), já apoiado no asfalto:
//                 o do .glb do circuito (modo "glb") ou o da pista plana traçada pelo GPS (modo "plana", y ≈ 0)
//   pose(t)       posição + yaw/pitch/roll + frente + velocidade
//   rastro(t0,t1) pontos do caminho percorrido entre dois tempos (linha atrás do carro)
// t = segundos desde o início da volta (0 = linha de chegada no início da volta; duracao = fim da volta).
// Fora do trecho com dados (margem de ~4 s antes/depois), o carro fica parado no último ponto: nunca some.

/** Cria o amostrador a partir do JSON da volta (objeto já carregado). */
export function criarAmostrador(volta) {
  const R = volta.relogio;
  const C = volta.caminho;
  const S = Float64Array.from(R.s);
  const nT = S.length;
  const dt = R.dt;
  const t0 = R.t0;
  const tFim = t0 + (nT - 1) * dt;
  // derivadas de Fritsch–Carlson (garantem s(t) monotônico entre os nós)
  const del = new Float64Array(nT - 1);
  for (let i = 0; i < nT - 1; i++) del[i] = (S[i + 1] - S[i]) / dt;
  const m = new Float64Array(nT);
  m[0] = del[0];
  m[nT - 1] = del[nT - 2];
  for (let i = 1; i < nT - 1; i++) {
    const a = del[i - 1], b = del[i];
    m[i] = a * b <= 0 ? 0 : (2 * a * b) / (a + b); // média harmônica: nunca ultrapassa
  }
  const X = Float64Array.from(C.x), Y = Float64Array.from(C.y), Z = Float64Array.from(C.z);
  const YAW = Float64Array.from(C.yaw), PIT = Float64Array.from(C.pitch), ROL = Float64Array.from(C.roll);
  const nP = X.length;
  const ds = C.ds;
  const sMax = (nP - 1) * ds;

  const limT = (t) => Math.min(tFim, Math.max(t0, t));

  /** distância ao longo do caminho no tempo t (m) */
  function s(t) {
    const tt = limT(t);
    const x = (tt - t0) / dt;
    const i = Math.min(nT - 2, Math.max(0, Math.floor(x)));
    const u = x - i;
    const h00 = (1 + 2 * u) * (1 - u) * (1 - u), h10 = u * (1 - u) * (1 - u), h01 = u * u * (3 - 2 * u), h11 = u * u * (u - 1);
    return Math.min(sMax, Math.max(0, h00 * S[i] + h10 * dt * m[i] + h01 * S[i + 1] + h11 * dt * m[i + 1]));
  }
  /** velocidade (m/s) no tempo t (0 fora do trecho com dados) */
  function vel(t) {
    if (t < t0 || t > tFim) return 0;
    const x = (t - t0) / dt;
    const i = Math.min(nT - 2, Math.max(0, Math.floor(x)));
    const u = x - i;
    const d00 = 6 * u * u - 6 * u, d10 = 3 * u * u - 4 * u + 1, d01 = -6 * u * u + 6 * u, d11 = 3 * u * u - 2 * u;
    return (d00 * S[i] + d10 * dt * m[i] + d01 * S[i + 1] + d11 * dt * m[i + 1]) / dt;
  }
  function noCaminho(sv, arr) {
    const x = Math.min(nP - 1, Math.max(0, sv / ds));
    const i = Math.min(nP - 2, Math.floor(x));
    const f = x - i;
    return arr[i] + (arr[i + 1] - arr[i]) * f;
  }
  /** [x, y, z] na distância sv */
  function posEmS(sv) {
    return [noCaminho(sv, X), noCaminho(sv, Y), noCaminho(sv, Z)];
  }
  /** [x, y, z] no tempo t */
  function pos(t) {
    return posEmS(s(t));
  }
  /** pose completa no tempo t. yaw = rotação em Y (three.js) para um modelo cuja frente é +Z local. */
  function pose(t) {
    const sv = s(t);
    const yaw = noCaminho(sv, YAW), pitch = noCaminho(sv, PIT), roll = noCaminho(sv, ROL);
    const cp = Math.cos(pitch);
    return {
      t, s: sv, x: noCaminho(sv, X), y: noCaminho(sv, Y), z: noCaminho(sv, Z),
      yaw, pitch, roll,
      frente: [Math.sin(yaw) * cp, Math.sin(pitch), Math.cos(yaw) * cp],
      vel: vel(t), // m/s
      comDados: t >= t0 && t <= tFim,
    };
  }
  /** Pontos do caminho entre t0 e t1 (rastro). passo em metros; elev = altura extra acima do asfalto. */
  function rastro(ta, tb, { passo = 2, elev = 0.05 } = {}) {
    const sa = s(Math.min(ta, tb)), sb = s(Math.max(ta, tb));
    const pts = [];
    const ponto = (sv) => { const p = posEmS(sv); p[1] += elev; pts.push(p); };
    ponto(sa);
    for (let sv = Math.ceil(sa / passo) * passo; sv < sb; sv += passo) if (sv > sa) ponto(sv);
    if (sb > sa) ponto(sb);
    return { pontos: pts, cor: volta.cor, s0: sa, s1: sb };
  }
  return {
    info: {
      sessao: volta.sessao, sessaoNome: volta.sessao_nome, piloto: volta.piloto, sigla: volta.sigla, nome: volta.nome,
      equipe: volta.equipe, cor: volta.cor, cor2: volta.cor2, volta: volta.volta, duracao: volta.duracao,
      setores: volta.setores, fonte: volta.fonte, pista: volta.pista,
      // voltas antigas (antes da fase 2b) não têm estes campos: eram Interlagos com o modelo 3D
      circuito: volta.circuito ?? "Interlagos", modoPista: volta.modo_pista ?? "glb", ano: volta.ano,
    },
    duracao: volta.duracao,
    tIni: t0,
    tFim,
    s, vel, pos, posEmS, pose, rastro,
  };
}

/** Busca o JSON da volta e cria o amostrador. base = URL/pasta onde estão os JSON (padrão "voltas/").
 *  Em Node, passe opcoes.ler = (nomeArquivo) => conteúdo (string). */
export async function carregarVolta(sessao, piloto, volta, opcoes = {}) {
  const nome = `${sessao}_${piloto}_${volta}.json`;
  let dados;
  if (opcoes.ler) dados = JSON.parse(await opcoes.ler(nome));
  else {
    const base = opcoes.base ?? "voltas/";
    const r = await (opcoes.fetch ?? fetch)(base.replace(/\/?$/, "/") + nome);
    if (!r.ok) throw new Error(`kit/gps: não achei ${nome} em ${base} (rode py/preparar_volta.py)`);
    dados = await r.json();
  }
  return criarAmostrador(dados);
}

/** Relógio de comparação: tempo da CENA (s) -> tempo de VOLTA (s).
 *  fator = quantas vezes mais rápido que o real (2.2 = "acelerado 2,2x"); inicio = tempo de volta no 1º quadro.
 *  Use o MESMO relógio para os dois carros: os dois largam juntos da linha e cada um anda pelo próprio GPS. */
export function relogioComparacao({ fator = 1, inicio = 0 } = {}) {
  return (tCena) => inicio + tCena * fator;
}

/** Faixa (fita) para desenhar um rastro como malha: devolve posições (x,y,z por vértice), alfa por vértice e índices.
 *  largura em metros; afinar=true deixa a ponta antiga fina e transparente. */
export function faixa(pontos, { largura = 1.2, afinar = true } = {}) {
  const n = pontos.length;
  const posicoes = new Float32Array(Math.max(0, n) * 6);
  const alfa = new Float32Array(Math.max(0, n) * 2);
  const indices = [];
  for (let k = 0; k < n; k++) {
    const a = pontos[Math.max(0, k - 1)], b = pontos[Math.min(n - 1, k + 1)];
    let dx = b[0] - a[0], dz = b[2] - a[2];
    const l = Math.hypot(dx, dz) || 1;
    dx /= l; dz /= l;
    const f = n > 1 ? k / (n - 1) : 1;
    const w = (largura / 2) * (afinar ? 0.35 + 0.65 * f : 1);
    const p = pontos[k];
    posicoes.set([p[0] - dz * w, p[1], p[2] + dx * w, p[0] + dz * w, p[1], p[2] - dx * w], k * 6);
    alfa.set(afinar ? [f, f] : [1, 1], k * 2);
    if (k < n - 1) { const o = k * 2; indices.push(o, o + 1, o + 2, o + 1, o + 3, o + 2); }
  }
  return { posicoes, alfa, indices: Uint32Array.from(indices) };
}

/** Câmera de perseguição suave (sem herdar tremor do carro): direção = média da frente nos últimos 'janela' s.
 *  Devolve { pos: [x,y,z], alvo: [x,y,z] }. Para seguir dois carros, passe vários amostradores (alvo = ponto médio). */
export function cameraSeguindo(amostradores, t, { atras = 14, altura = 5, adiante = 6, janela = 0.6, lado = 0 } = {}) {
  const lista = Array.isArray(amostradores) ? amostradores : [amostradores];
  let fx = 0, fz = 0;
  const N = 12;
  for (let k = 0; k < N; k++) {
    const p = lista[0].pose(t - (janela * k) / (N - 1));
    fx += Math.sin(p.yaw); fz += Math.cos(p.yaw);
  }
  const l = Math.hypot(fx, fz) || 1;
  fx /= l; fz /= l;
  const c = [0, 0, 0];
  for (const a of lista) { const p = a.pos(t); c[0] += p[0] / lista.length; c[1] += p[1] / lista.length; c[2] += p[2] / lista.length; }
  // lado > 0 desloca a câmera para a esquerda do carro (+X local)
  return {
    pos: [c[0] - fx * atras + fz * lado, c[1] + altura, c[2] - fz * atras - fx * lado],
    alvo: [c[0] + fx * adiante, c[1] + 0.8, c[2] + fz * adiante],
  };
}

/** Converte cor "#RRGGBB" em número (0xRRGGBB), útil no three.js. */
export const corNumero = (hex) => parseInt(String(hex).replace("#", ""), 16);
