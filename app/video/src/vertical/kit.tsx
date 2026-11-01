// Kit dos vídeos verticais animados (1080×1920): peças que se repetem entre vídeos. Tudo vem do quadro atual e dos
// tempos por palavra da narração; o desenho específico de cada tema fica no arquivo do vídeo.
import { Easing, interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";

export type Palavra = { t: string; i: number; f: number };

const limpa = (t: string) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");

/** Tempo em que uma sequência de palavras começa, depois de `apos` segundos. Direção presa à palavra, não ao segundo. */
export const noTrecho = (palavras: Palavra[], trecho: string, apos = 0): number => {
  const alvo = trecho.split(" ").map(limpa);
  for (let k = 0; k <= palavras.length - alvo.length; k++) {
    if (palavras[k].i >= apos && alvo.every((a, j) => limpa(palavras[k + j].t) === a)) return palavras[k].i;
  }
  throw new Error(`trecho não encontrado no roteiro: ${trecho}`);
};

export const useTempo = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

export const suave = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.65, 0, 0.35, 1) });
export const entra = (t: number, a: number, dur = 0.35) =>
  interpolate(t, [a, a + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });

const FONTE = "'Trebuchet MS', 'Segoe UI', sans-serif";

/** Legenda em blocos curtos: a palavra falada acende em amarelo; os termos-chave ganham sublinhado. */
export const Legenda: React.FC<{ palavras: Palavra[]; chaves?: string[]; limite?: number }> = ({ palavras, chaves = [], limite = 5 }) => {
  const t = useTempo();
  const blocos: Palavra[][] = [];
  let atual: Palavra[] = [];
  palavras.forEach((p, k) => {
    atual.push(p);
    const fimDeFrase = /[.?!:,]$/.test(p.t);
    const pausa = palavras[k + 1] && palavras[k + 1].i - p.f > 0.35;
    if (atual.length >= limite || fimDeFrase || pausa) {
      blocos.push(atual);
      atual = [];
    }
  });
  if (atual.length) blocos.push(atual);
  const bloco = blocos.find((b, k) => t < (blocos[k + 1]?.[0].i ?? 1e9)) ?? blocos[blocos.length - 1];
  const destaque = chaves.map(limpa);
  return (
    <div style={{ position: "absolute", top: 250, left: 70, right: 70, textAlign: "center", fontFamily: FONTE, fontSize: 66, fontWeight: 800, lineHeight: 1.18, textShadow: "0 3px 18px rgba(0,0,0,.9)" }}>
      {bloco.map((p, k) => {
        const falada = t >= p.i;
        const chave = destaque.includes(limpa(p.t));
        return (
          <span key={k} style={{ color: t >= p.i && t < p.f + 0.1 ? "#ffd21f" : falada ? "#fff" : "rgba(255,255,255,.34)", borderBottom: chave && falada ? "7px solid #ff5a1f" : "7px solid transparent", marginRight: 16, display: "inline-block" }}>
            {p.t.replace(/[.,:]$/, "")}
          </span>
        );
      })}
    </div>
  );
};

/** Placa de número: conta até o valor e entra com leve subida. */
export const Placa: React.FC<{ texto?: string; de?: number; ate?: number; casas?: number; unidade?: string; prefixo?: string; inicio: number; dur?: number; x: number; y: number; cor?: string; tam?: number }> = ({ texto, de, ate = 0, casas = 0, unidade, prefixo = "", inicio, dur = 0.8, x, y, cor = "#ffb21f", tam = 92 }) => {
  const t = useTempo();
  const e = entra(t, inicio);
  if (e <= 0) return null;
  const v = de === undefined ? ate : de + (ate - de) * suave(t, inicio, inicio + dur);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) translateY(${(1 - e) * 24}px)`, opacity: e, background: "rgba(8,11,18,.86)", border: "2px solid rgba(255,255,255,.14)", borderRadius: 24, padding: "12px 30px", fontFamily: FONTE, whiteSpace: "nowrap" }}>
      <span style={{ color: cor, fontSize: tam, fontWeight: 800, textShadow: `0 0 26px ${cor}88` }}>{texto ?? `${prefixo}${v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })}`}</span>
      {unidade && <span style={{ color: "#fff", fontSize: tam * 0.42, fontWeight: 700, marginLeft: 12 }}>{unidade}</span>}
    </div>
  );
};

/** Noite de autódromo: céu em degradê, luzes desfocadas e asfalto em movimento. */
export const Autodromo: React.FC<{ topo?: string; base?: string; velocidade?: number; horizonte?: number }> = ({ topo = "#060a16", base = "#17324a", velocidade = 1, horizonte = 1180 }) => {
  const t = useTempo();
  return (
    <div style={{ position: "absolute", inset: 0, background: `linear-gradient(${topo}, ${base} ${horizonte}px)` }}>
      {Array.from({ length: 22 }, (_, k) => {
        const x = (random(`lx${k}`) * 1400 - t * 60 * velocidade * (0.4 + random(`lv${k}`))) % 1400;
        return <div key={k} style={{ position: "absolute", left: x < 0 ? x + 1400 - 150 : x - 150, top: horizonte - 90 - random(`ly${k}`) * 300, width: 26 + random(`ls${k}`) * 40, height: 26 + random(`ls${k}`) * 40, borderRadius: "50%", background: ["#7fdcff", "#ffd21f", "#ff6a3d", "#ffffff"][k % 4], filter: "blur(9px)", opacity: 0.1 + 0.24 * Math.min(1, velocidade) }} />;
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: horizonte, bottom: 0, background: "linear-gradient(#1a1d26, #0c0e14)" }} />
      <svg width={1080} height={1920 - horizonte} style={{ position: "absolute", top: horizonte, left: 0 }}>
        {Array.from({ length: 14 }, (_, k) => {
          const x = ((k * 170 - t * 900 * velocidade) % 2380 + 2380) % 2380 - 300;
          return <rect key={k} x={x} y={30 + (k % 3) * 8} width={90} height={5} fill="#fff" opacity={0.2} />;
        })}
        <rect x={0} y={0} width={1080} height={16} fill="#d81e2c" />
        {Array.from({ length: 16 }, (_, k) => <rect key={k} x={((k * 150 - t * 900 * velocidade) % 2400 + 2400) % 2400 - 150} y={0} width={75} height={16} fill="#f3f3f3" />)}
      </svg>
    </div>
  );
};

/** Disco de freio em 2D: `calor` de 0 a 1 vai do cinza ao laranja-dourado. */
export const Disco: React.FC<{ x: number; y: number; raio: number; calor: number; giro: number }> = ({ x, y, raio, calor, giro }) => {
  const c = Math.max(0, Math.min(1, calor));
  const base = c < 0.5 ? `rgb(${50 + c * 2 * 150},${48 + c * 2 * 10},${50 - c * 2 * 40})` : `rgb(${200 + (c - 0.5) * 2 * 55},${58 + (c - 0.5) * 2 * 120},${10 + (c - 0.5) * 2 * 40})`;
  return (
    <svg width={raio * 2.6} height={raio * 2.6} viewBox="-130 -130 260 260" style={{ position: "absolute", left: x - raio * 1.3, top: y - raio * 1.3, filter: c > 0.3 ? `drop-shadow(0 0 ${c * 44}px rgba(255,110,20,${c}))` : undefined }}>
      <g transform={`rotate(${giro})`}>
        <circle r={100} fill={base} stroke="#0a0a0c" strokeWidth={3} />
        {[92, 86, 80, 74, 68].map((r) => <circle key={r} r={r} fill="none" stroke="rgba(0,0,0,.2)" strokeWidth={0.8} />)}
        <circle r={60} fill="#8e95a0" stroke="#0a0a0c" strokeWidth={2} />
        {Array.from({ length: 10 }, (_, k) => <circle key={k} cx={Math.cos(k * 0.628) * 42} cy={Math.sin(k * 0.628) * 42} r={6} fill="#14161c" />)}
        {Array.from({ length: 10 }, (_, k) => <circle key={k} cx={Math.cos(k * 0.628 + 0.3) * 54} cy={Math.sin(k * 0.628 + 0.3) * 54} r={2.6} fill="#c98a35" />)}
        <circle r={24} fill="#0b0d12" />
      </g>
    </svg>
  );
};

/** Carro de lado, desenho próprio do canal. `freada` inclina o bico e solta fumaça na roda da frente. */
export const CarroLado: React.FC<{ x: number; y: number; escala?: number; freada?: number; giro: number; calor?: number; cor?: string }> = ({ x, y, escala = 1, freada = 0, giro, calor = 0, cor = "#e5311d" }) => (
  <svg width={1000 * escala} height={300 * escala} viewBox="0 0 1000 300" style={{ position: "absolute", left: x - 500 * escala, top: y - 150 * escala, overflow: "visible", transform: `rotate(${freada * 1.5}deg)` }}>
    <path d="M40 190 L120 130 L140 130 L150 180 L290 170 L410 120 L480 80 L560 78 L590 130 L780 165 L960 190 L965 212 L60 218 Z" fill={cor} stroke="#16080a" strokeWidth={4} />
    <path d="M60 218 L965 212 L985 226 L40 232 Z" fill="#14161c" />
    <path d="M400 124 L480 86 L556 84 L574 128 Z" fill="#0d1018" />
    <circle cx={500} cy={98} r={26} fill="#ffd21f" stroke="#1a1a1a" strokeWidth={4} />
    <path d="M28 90 L146 90 L146 108 L28 108 Z" fill={cor} stroke="#16080a" strokeWidth={4} />
    <path d="M880 188 L990 196 L990 212 L880 208 Z" fill="#14161c" />
    <path d="M660 150 L780 165 L780 184 L660 186 Z" fill="#fff" opacity={0.9} />
    {[200, 800].map((cx) => (
      <g key={cx} transform={`translate(${cx} 212) rotate(${giro})`}>
        <circle r={72} fill="#111216" stroke="#000" strokeWidth={4} />
        <circle r={52} fill="none" stroke="#ffd21f" strokeWidth={5} strokeDasharray="60 28" />
        <circle r={36} fill={calor > 0 ? `rgb(${60 + calor * 195},${50 + calor * 60},40)` : "#3a3d45"} />
        {Array.from({ length: 6 }, (_, k) => <rect key={k} x={-3} y={-36} width={6} height={36} fill="#c8ccd3" transform={`rotate(${k * 60})`} />)}
      </g>
    ))}
  </svg>
);

/** Partículas de fumaça ou faísca soltas de um ponto: função pura do tempo. */
export const Fumaca: React.FC<{ x: number; y: number; forca: number; semente?: string; cor?: string; sentido?: number }> = ({ x, y, forca, semente = "f", cor = "rgba(210,215,225,.5)", sentido = -1 }) => {
  const t = useTempo();
  if (forca <= 0) return null;
  return (
    <>
      {Array.from({ length: 26 }, (_, k) => {
        const vida = (t * (0.8 + random(`${semente}v${k}`)) + random(`${semente}p${k}`)) % 1;
        const r = 30 + vida * 130;
        return <div key={k} style={{ position: "absolute", left: x + sentido * vida * (240 + random(`${semente}a${k}`) * 300) - r / 2, top: y - vida * 90 - r / 2 + (random(`${semente}b${k}`) - 0.5) * 60, width: r, height: r, borderRadius: "50%", background: cor, filter: "blur(16px)", opacity: (1 - vida) * forca }} />;
      })}
    </>
  );
};
