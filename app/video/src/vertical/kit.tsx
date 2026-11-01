// Kit dos vídeos verticais (1080×1920), na linguagem de F1/docs/folha_de_estilos.md, com cores e pinturas do canal.
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export type Palavra = { t: string; i: number; f: number };

const limpa = (t: string) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");

/** Tempo em que uma sequência de palavras começa. Direção presa à palavra, não ao segundo. */
export const noTrecho = (palavras: Palavra[], trecho: string, apos = 0): number => {
  const alvo = trecho.split(" ").map(limpa);
  for (let k = 0; k <= palavras.length - alvo.length; k++) {
    if (palavras[k].i >= apos && alvo.every((a, j) => limpa(palavras[k + j].t) === a)) return palavras[k].i;
  }
  throw new Error(`trecho não encontrado no roteiro: ${trecho}`);
};

export const useTempo = () => useCurrentFrame() / useVideoConfig().fps;
export const suave = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.65, 0, 0.35, 1) });
export const entra = (t: number, a: number, dur = 0.35) =>
  interpolate(t, [a, a + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });

export const FONTE = "'Segoe UI', 'Inter', sans-serif";

/** Só aparecem as palavras já faladas: a atual em branco e negrito, as anteriores em cinza; termo-chave com caixa própria do canal. */
export const Legenda: React.FC<{ palavras: Palavra[]; chaves?: string[]; limite?: number }> = ({ palavras, chaves = [], limite = 5 }) => {
  const t = useTempo();
  const blocos: Palavra[][] = [];
  let atual: Palavra[] = [];
  palavras.forEach((p, k) => {
    atual.push(p);
    const pausa = palavras[k + 1] && palavras[k + 1].i - p.f > 0.3;
    if (atual.length >= limite || /[.?!:,]$/.test(p.t) || pausa) {
      blocos.push(atual);
      atual = [];
    }
  });
  if (atual.length) blocos.push(atual);
  const bloco = blocos.find((b, k) => t < (blocos[k + 1]?.[0].i ?? 1e9)) ?? blocos[blocos.length - 1];
  const destaque = chaves.map(limpa);
  const faladas = bloco.filter((p) => p.i <= t);
  const fala = faladas[faladas.length - 1];
  return (
    <div style={{ position: "absolute", top: 300, left: 60, right: 60, textAlign: "center", fontFamily: FONTE, fontSize: 62, lineHeight: 1.24, zIndex: 50, textShadow: "0 2px 14px rgba(0,0,0,.85)" }}>
      {faladas.map((p, k) => {
        const chave = destaque.includes(limpa(p.t));
        return (
          <span key={k} style={{ color: p === fala ? "#fff" : "#b4b8c2", opacity: p === fala ? entra(t, p.i, 0.12) * 0.25 + 0.75 : 1, fontWeight: p === fala ? 700 : 500, marginRight: 5, display: "inline-block", padding: "0 7px", borderRadius: 10, background: chave ? "rgba(255,196,0,.22)" : "none", boxShadow: chave ? "inset 0 -5px 0 #ffc400" : "none" }}>
            {p.t}
          </span>
        );
      })}
    </div>
  );
};

/** Placa de vidro escuro: número ou texto grande, unidade pequena. */
export const Placa: React.FC<{ texto: string; unidade?: string; inicio: number; x: number; y: number; cor?: string; tam?: number; ate?: number }> = ({ texto, unidade, inicio, x, y, cor = "#fff", tam = 84, ate = 1e9 }) => {
  const t = useTempo();
  const e = entra(t, inicio, 0.25) * (1 - entra(t, ate, 0.2));
  if (e <= 0) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 40, transform: `translate(-50%,-50%) scale(${0.9 + e * 0.1})`, opacity: e, filter: `blur(${(1 - e) * 6}px)`, background: "rgba(14,17,24,.84)", boxShadow: "0 10px 34px rgba(0,0,0,.5), inset 0 0 0 2px rgba(255,255,255,.08)", borderRadius: 24, padding: "8px 30px 12px", fontFamily: FONTE, whiteSpace: "nowrap" }}>
      <span style={{ color: cor, fontSize: tam, fontWeight: 800, letterSpacing: -1, textShadow: `0 0 22px ${cor}66` }}>{texto}</span>
      {unidade && <span style={{ color: cor, fontSize: tam * 0.42, fontWeight: 700, marginLeft: 10 }}>{unidade}</span>}
    </div>
  );
};

export type Pintura = { base: string; escuro: string; faixa: string; asa?: string };

/** Carro visto de cima, nariz para cima. Mede 110×290 antes da escala. Desenho e pinturas do canal. */
export const CarroCima: React.FC<{ p: Pintura; id: string; capacete?: string }> = ({ p, id, capacete = "#ffd21f" }) => (
  <svg width={150} height={320} viewBox="-75 -160 150 320" style={{ overflow: "visible", display: "block" }}>
    <defs>
      <linearGradient id={`${id}c`} x1="0" x2="1"><stop offset="0" stopColor={p.escuro} /><stop offset="0.5" stopColor={p.base} /><stop offset="1" stopColor={p.escuro} /></linearGradient>
      <radialGradient id={`${id}s`}><stop offset="0" stopColor="#000" stopOpacity="0.55" /><stop offset="1" stopColor="#000" stopOpacity="0" /></radialGradient>
    </defs>
    <ellipse cx={4} cy={10} rx={78} ry={165} fill={`url(#${id}s)`} />
    {[[-52, -86], [52, -86], [-56, 86], [56, 86]].map(([x, y], k) => (
      <g key={k}>
        <rect x={x - 14} y={y - 28} width={28} height={56} rx={7} fill="#0c0d11" />
        <rect x={x - 3} y={y - 28} width={6} height={56} fill="#2b2e36" />
      </g>
    ))}
    <path d="M-44 -86 L44 -86 M-48 80 L48 80" stroke="#15171c" strokeWidth={6} />
    {/* asa dianteira */}
    <path d="M-68 -150 Q0 -132 68 -150 L68 -128 Q0 -112 -68 -128 Z" fill={`url(#${id}c)`} stroke="#0a0a0d" strokeWidth={2.5} />
    <path d="M-68 -140 Q0 -122 68 -140" stroke={p.faixa} strokeWidth={5} fill="none" />
    {/* corpo */}
    <path d="M-9 -128 Q0 -146 9 -128 L14 -52 Q42 -22 44 26 L36 96 L14 122 L-14 122 L-36 96 L-44 26 Q-42 -22 -14 -52 Z" fill={`url(#${id}c)`} stroke="#0a0a0d" strokeWidth={2.5} />
    <path d="M-4 -128 L4 -128 L7 -52 L10 96 L-10 96 L-7 -52 Z" fill={p.faixa} />
    <path d="M-40 18 Q-30 -12 -20 -28 L-20 62 L-36 70 Z M40 18 Q30 -12 20 -28 L20 62 L36 70 Z" fill={p.escuro} stroke="#0a0a0d" strokeWidth={1.5} />
    <path d="M-34 18 L-24 -6 L-24 44 Z M34 18 L24 -6 L24 44 Z" fill={p.faixa} opacity={0.9} />
    {/* cockpit, halo e capacete */}
    <path d="M-14 -38 Q0 -50 14 -38 L13 10 L-13 10 Z" fill="#0b0d12" />
    <circle cy={-14} r={11} fill={capacete} stroke="#161616" strokeWidth={2} />
    <path d="M0 -50 L0 -22 M-15 -16 Q0 -30 15 -16 L14 16 M-15 -16 L-14 16" stroke="#2a2d34" strokeWidth={5} fill="none" />
    {/* asa traseira */}
    <rect x={-54} y={124} width={108} height={24} rx={4} fill={p.asa ?? p.base} stroke="#0a0a0d" strokeWidth={2.5} />
    <rect x={-54} y={131} width={108} height={8} fill={p.faixa} />
    <circle cy={154} r={4} fill="#ff3b30" />
  </svg>
);
