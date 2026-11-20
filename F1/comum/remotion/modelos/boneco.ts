// Poses e movimentos do boneco articulado (criarPiloto: pilotos e mecânicos). Pedido do Felipe (2026-11-12): bonecos
// "parecendo 2 pedaços de pau" deslizando → cadeia de verdade: raiz > coluna (gira no quadril) > pescoço > cabeça;
// coluna > ombro > cotovelo > pulso > mão; raiz > quadril > joelho > tornozelo > bota.
// Ângulos no espaço do modelo (ele é modelado olhando para -z): rotation.x positivo em quadril/ombro = membro para a
// FRENTE; joelho negativo = dobra para trás; coluna negativa = inclina para a frente. Cada função começa do repouso
// (`neutro`), então chame UMA por quadro, depois de posicionar o boneco (o grupo de fora: .position e .rotation.y).
import * as THREE from "three";

type J = Record<string, THREE.Object3D>;
const jt = (p: THREE.Object3D): J | null => (p.userData.juntas as J) ?? null;
const COXA = 0.43, CANELA = 0.4, PE = 0.075, ALT = COXA + CANELA + PE;
const lim = (x: number) => Math.max(0, Math.min(1, x));

/** Volta todas as articulações ao repouso (de pé, braços ao lado do corpo). */
export function neutro(p: THREE.Object3D) {
  const j = jt(p);
  if (!j) return;
  for (const [k, o] of Object.entries(j)) {
    if (k === "raiz") continue;
    o.rotation.set(0, 0, 0);
  }
  j.ombroE.rotation.z = -0.1;
  j.ombroD.rotation.z = 0.1;
  j.raiz.position.set(0, 0, 0);
  j.raiz.rotation.set(0, Math.PI, 0);
}

/** Perna: quadril a, joelho b; o tornozelo deixa a sola paralela ao chão. Devolve [altura do quadril, pé à frente]. */
function perna(j: J, l: "E" | "D", a: number, b: number): [number, number] {
  j[`quadril${l}`].rotation.x = a;
  j[`joelho${l}`].rotation.x = b;
  j[`tornozelo${l}`].rotation.x = -(a + b);
  return [COXA * Math.cos(a) + CANELA * Math.cos(a + b) + PE, COXA * Math.sin(a) + CANELA * Math.sin(a + b)];
}

/** Assenta o boneco: o pé de apoio (o mais baixo) fica no chão e no lugar. */
function assentar(j: J, e: [number, number], d: [number, number]) {
  const apoio = e[0] >= d[0] ? e : d;
  j.raiz.position.y = apoio[0] - ALT;
  j.raiz.position.z = -apoio[1]; // frente do modelo = +z do grupo (a raiz está girada 180°)
}

/** Fase do passo para quem andou `metros` (um ciclo = 2 passos ≈ 1,5 m): os pés não escorregam. */
export const faseDoPasso = (metros: number) => (metros / 1.5) * Math.PI * 2;

/** Andar: pernas alternadas com joelho dobrando no balanço, braços balançando ao contrário, tronco girando de leve.
 *  `fase` = faseDoPasso(distância percorrida). `modo`: "livre" (padrão), "carregar" (caixa à frente, com as duas mãos),
 *  "empurrar" (braços esticados à frente, tronco inclinado). */
export function andar(p: THREE.Object3D, fase: number, ampl = 1, modo: string = "livre") {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const s = Math.sin(fase);
  const a = 0.42 * ampl;
  const pe = perna(j, "E", a * s, -(0.12 + 0.75 * Math.max(0, Math.cos(fase + 0.6))) * ampl);
  const pd = perna(j, "D", -a * s, -(0.12 + 0.75 * Math.max(0, Math.cos(fase + 0.6 + Math.PI))) * ampl);
  assentar(j, pe, pd);
  j.raiz.position.z = 0;
  j.coluna.rotation.y = 0.07 * s * ampl;
  j.pescoco.rotation.y = -0.05 * s * ampl;
  if (modo === "carregar") segurar(j, 1);
  else if (modo === "empurrar") {
    j.coluna.rotation.x = -0.28;
    for (const l of ["E", "D"]) {
      j[`ombro${l}`].rotation.x = 1.25;
      j[`cotovelo${l}`].rotation.x = 0.35;
    }
  } else {
    j.ombroE.rotation.x = -0.45 * s * ampl;
    j.ombroD.rotation.x = 0.45 * s * ampl;
    j.cotoveloE.rotation.x = (0.25 + 0.2 * Math.max(0, -s)) * ampl;
    j.cotoveloD.rotation.x = (0.25 + 0.2 * Math.max(0, s)) * ampl;
  }
}

function segurar(j: J, k: number) {
  j.ombroE.rotation.set(0.6 * k, 0, -0.1 + 0.32 * k);
  j.ombroD.rotation.set(0.6 * k, 0, 0.1 - 0.32 * k);
  j.cotoveloE.rotation.x = 1.0 * k;
  j.cotoveloD.rotation.x = 1.0 * k;
  j.pulsoE.rotation.z = 0.3 * k;
  j.pulsoD.rotation.z = -0.3 * k;
}

/** Parado segurando uma caixa à frente (k 0 = braços soltos, 1 = segurando). Ponto entre as mãos: `maos(p)`. */
export function carregar(p: THREE.Object3D, k = 1) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  segurar(j, lim(k));
}

/** Agachar (k 0 de pé → 1 de cócoras), tronco à frente e braços para a frente (mexer em algo no chão ou na roda). */
export function agachar(p: THREE.Object3D, k: number) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const u = lim(k);
  const e = perna(j, "E", 1.45 * u, -2.15 * u);
  const d = perna(j, "D", 1.3 * u, -2.0 * u);
  assentar(j, e, d);
  j.coluna.rotation.x = -0.45 * u;
  j.pescoco.rotation.x = 0.25 * u;
  for (const l of ["E", "D"]) {
    j[`ombro${l}`].rotation.x = 0.9 * u;
    j[`cotovelo${l}`].rotation.x = 0.5 * u;
  }
}

/** Abaixar para pegar algo no chão (k 0 → 1 = mãos perto do chão) e erguer de volta com a caixa (`comCaixa`). */
export function abaixar(p: THREE.Object3D, k: number, comCaixa = false) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const u = lim(k);
  const e = perna(j, "E", 0.75 * u, -1.25 * u);
  const d = perna(j, "D", 0.75 * u, -1.25 * u);
  assentar(j, e, d);
  j.coluna.rotation.x = -1.0 * u;
  j.pescoco.rotation.x = 0.5 * u;
  if (comCaixa) segurar(j, 1);
  else
    for (const l of ["E", "D"]) {
      j[`ombro${l}`].rotation.x = 0.35 * u;
      j[`cotovelo${l}`].rotation.x = 0.15 * u;
    }
}

/** Apontar com um braço (k 0 → 1): braço esticado para a frente e um pouco para cima, cabeça olhando junto. */
export function apontar(p: THREE.Object3D, lado: "esq" | "dir" = "dir", k = 1, altura = 0.3) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const u = lim(k);
  const l = lado === "esq" ? "E" : "D";
  j[`ombro${l}`].rotation.x = (1.45 + altura) * u;
  j[`ombro${l}`].rotation.z = (l === "E" ? 0.15 : -0.15) * u;
  j[`cotovelo${l}`].rotation.x = 0.08 * u;
  j[`pulso${l}`].rotation.x = 0.1 * u;
  j.coluna.rotation.y = (l === "E" ? -0.2 : 0.2) * u;
  j.pescoco.rotation.x = -0.1 * u;
}

/** Acenar (t = segundo do vídeo; k 0 → 1 levanta o braço): braço para o alto e antebraço balançando. */
export function acenar(p: THREE.Object3D, t: number, lado: "esq" | "dir" = "dir", k = 1) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const u = lim(k);
  const l = lado === "esq" ? "E" : "D";
  const s = l === "E" ? -1 : 1;
  j[`ombro${l}`].rotation.z = s * (0.1 + 2.3 * u);
  j[`ombro${l}`].rotation.x = 0.25 * u;
  j[`cotovelo${l}`].rotation.z = s * (0.3 + 0.45 * Math.sin(t * 9)) * u;
  j[`pulso${l}`].rotation.z = s * 0.25 * Math.sin(t * 9 + 0.6) * u;
  j.pescoco.rotation.z = -s * 0.08 * u;
}

/** Empurrar parado (k 0 → 1): braços à frente, tronco inclinado e uma perna atrás fazendo força. Andando: andar(p, fase, 0.7, "empurrar"). */
export function empurrar(p: THREE.Object3D, k = 1) {
  const j = jt(p);
  if (!j) return;
  neutro(p);
  const u = lim(k);
  const e = perna(j, "E", 0.35 * u, -0.45 * u);
  const d = perna(j, "D", -0.45 * u, -0.1 * u);
  assentar(j, e, d);
  j.raiz.position.z = 0;
  j.coluna.rotation.x = -0.4 * u;
  for (const l of ["E", "D"]) {
    j[`ombro${l}`].rotation.x = 1.3 * u;
    j[`cotovelo${l}`].rotation.x = 0.3 * u;
  }
}

/** Ponto no mundo entre as duas mãos (para pôr a caixa que ele carrega). */
export function maos(p: THREE.Object3D): THREE.Vector3 {
  const j = jt(p);
  if (!j) return p.getWorldPosition(new THREE.Vector3());
  p.updateMatrixWorld(true);
  const a = j.pulsoE.localToWorld(new THREE.Vector3(0, -0.05, 0));
  const b = j.pulsoD.localToWorld(new THREE.Vector3(0, -0.05, 0));
  return a.add(b).multiplyScalar(0.5);
}

/** Cabeça olhando (giro para os lados, inclinação para cima/baixo), por cima de qualquer pose. */
export function olhar(p: THREE.Object3D, giro: number, incl = 0) {
  const j = jt(p);
  if (!j) return;
  j.pescoco.rotation.y += giro;
  j.pescoco.rotation.x += incl;
}
