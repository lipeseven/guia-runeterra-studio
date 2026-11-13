// Movimento de câmera da cena inteira (ação direta do storyboard, fase 7b): o mesmo cálculo nos dois motores.
// Remotion: remotion/cena/index.tsx importa daqui; HyperFrames: montador/hyperframes/gps.html recebe uma cópia em assets/.
// m = { tipo, intensidade?, foco?: [x, y] } (spec.json → cena.movimento); p = progresso 0..1 da parte pura da cena.
// Devolve { escala, tx, ty, ox, oy }: CSS  transform-origin: ox% oy%;  transform: translate(tx%, ty%) scale(escala).
export const MOVIMENTOS = ["parado", "aproximar", "afastar", "pan_esq", "pan_dir", "subir", "descer"];
export const INTENSIDADE_PADRAO = 0.08;

export function movimento(m, p) {
  const fixo = { escala: 1, tx: 0, ty: 0, ox: 50, oy: 50 };
  if (!m || !m.tipo || m.tipo === "parado") return fixo;
  const k = Math.min(0.3, Math.max(0.01, Number(m.intensidade ?? INTENSIDADE_PADRAO)));
  const t = Math.min(1, Math.max(0, p));
  const e = 0.5 - 0.5 * Math.cos(Math.PI * t);          // suave na entrada e na saída
  const foco = Array.isArray(m.foco) ? m.foco : [0.5, 0.5];
  const ox = 100 * Math.min(1, Math.max(0, foco[0])), oy = 100 * Math.min(1, Math.max(0, foco[1]));
  const meio = (100 * k) / 2;                             // com escala 1+k sobra k/2 de cada lado
  switch (m.tipo) {
    case "aproximar": return { escala: 1 + k * e, tx: 0, ty: 0, ox, oy };
    case "afastar": return { escala: 1 + k * (1 - e), tx: 0, ty: 0, ox, oy };
    // pan: a câmera vai para a esquerda = o quadro desliza para a direita
    case "pan_esq": return { escala: 1 + k, tx: -meio + 2 * meio * e, ty: 0, ox: 50, oy: 50 };
    case "pan_dir": return { escala: 1 + k, tx: meio - 2 * meio * e, ty: 0, ox: 50, oy: 50 };
    case "subir": return { escala: 1 + k, tx: 0, ty: -meio + 2 * meio * e, ox: 50, oy: 50 };
    case "descer": return { escala: 1 + k, tx: 0, ty: meio - 2 * meio * e, ox: 50, oy: 50 };
    default: return fixo;
  }
}

export function transformCss(v) {
  return {
    transformOrigin: `${v.ox}% ${v.oy}%`,
    transform: `translate(${v.tx.toFixed(4)}%, ${v.ty.toFixed(4)}%) scale(${v.escala.toFixed(5)})`,
  };
}
