// Kit dos vídeos verticais (1080×1920), na linguagem analisada em F1/docs/analise_vertical.md.
// Tudo é função do tempo e das palavras da narração; o desenho específico de cada tema fica no arquivo do vídeo.
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

export const useTempo = () => useCurrentFrame() / useVideoConfig().fps;

export const suave = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.65, 0, 0.35, 1) });
export const entra = (t: number, a: number, dur = 0.35) =>
  interpolate(t, [a, a + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });

export const FONTE = "'Segoe UI', 'Inter', sans-serif";

/** Mostra a cena só no trecho dela, sem zerar o tempo: tudo é preso às palavras no tempo do vídeo inteiro. */
export const Cena: React.FC<{ de: number; ate: number; children: React.ReactNode }> = ({ de, ate, children }) => {
  const t = useTempo();
  return t >= de && t < ate ? <>{children}</> : null;
};

/** Só aparecem as palavras já faladas: a atual em branco e negrito, as anteriores em cinza; termo-chave com caixa fina. */
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
    <div style={{ position: "absolute", top: 325, left: 60, right: 60, textAlign: "center", fontFamily: FONTE, fontSize: 66, lineHeight: 1.22, zIndex: 50, textShadow: "0 2px 12px rgba(0,0,0,.75)" }}>
      {faladas.map((p, k) => (
        <span key={k} style={{ color: p === fala ? "#fff" : "#9a9ea8", fontWeight: p === fala ? 700 : 500, marginRight: 5, display: "inline-block", padding: "0 6px", borderRadius: 8, border: destaque.includes(limpa(p.t)) ? "3px solid #ff8a2a" : "3px solid transparent", background: destaque.includes(limpa(p.t)) ? "rgba(255,138,42,.16)" : "none" }}>
          {p.t}
        </span>
      ))}
    </div>
  );
};

/** Placa de vidro escuro sobre a peça: número grande e unidade pequena. `valor` já vem calculado pela cena. */
export const Placa: React.FC<{ valor?: number; texto?: string; casas?: number; unidade?: string; prefixo?: string; inicio: number; x: number; y: number; cor?: string; tam?: number }> = ({ valor = 0, texto, casas = 0, unidade, prefixo = "", inicio, x, y, cor = "#fff", tam = 90 }) => {
  const t = useTempo();
  const e = entra(t, inicio, 0.3);
  if (e <= 0) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 30, transform: `translate(-50%,-50%) scale(${0.92 + e * 0.08})`, opacity: e, background: "rgba(26,27,31,.8)", boxShadow: "0 8px 30px rgba(0,0,0,.45), inset 0 0 0 2px rgba(255,255,255,.07)", borderRadius: 26, padding: "10px 32px 14px", fontFamily: FONTE, whiteSpace: "nowrap" }}>
      <span style={{ color: cor, fontSize: tam, fontWeight: 800, letterSpacing: -1 }}>
        {texto ?? `${prefixo}${valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })}`}
      </span>
      {unidade && <span style={{ color: cor, fontSize: tam * 0.42, fontWeight: 700, marginLeft: 11 }}>{unidade}</span>}
    </div>
  );
};

/** Fundo quase preto com linhas de velocidade de ponta luminosa, zebra da pista e asfalto. */
export const FundoPista: React.FC<{ velocidade?: number; matiz?: string }> = ({ velocidade = 1, matiz = "#0b0c11" }) => {
  const t = useTempo();
  return (
    <div style={{ position: "absolute", inset: 0, background: matiz, overflow: "hidden" }}>
      {Array.from({ length: 34 }, (_, k) => {
        const comp = 70 + random(`c${k}`) * 340;
        const v = 500 + random(`v${k}`) * 1000;
        const x = 1300 - ((t * v * velocidade + random(`x${k}`) * 1700) % 1700);
        const cor = ["#b9c4d6", "#e2505a", "#5aa2ff", "#e8c27a", "#ffffff"][k % 5];
        return (
          <div key={k} style={{ position: "absolute", left: x, top: 40 + random(`y${k}`) * 1460, width: comp, height: 3, borderRadius: 2, opacity: 0.32 + random(`o${k}`) * 0.5, background: `linear-gradient(90deg, ${cor}, ${cor}00)`, boxShadow: `-1px 0 9px ${cor}` }} />
        );
      })}
      <svg width={1080} height={420} style={{ position: "absolute", top: 1510, left: 0 }}>
        {Array.from({ length: 12 }, (_, k) => (
          <rect key={k} x={((k * 180 - t * 700 * velocidade) % 2160 + 2160) % 2160 - 180} y={18} width={180} height={62} fill={k % 2 ? "#e9c7c8" : "#c3414a"} opacity={0.62} />
        ))}
        <rect x={0} y={80} width={1080} height={340} fill="#0d0e12" />
      </svg>
    </div>
  );
};

const QUENTE: [number, number[]][] = [[0, [132, 148, 168]], [0.22, [86, 58, 54]], [0.48, [165, 66, 18]], [0.74, [205, 104, 22]], [1, [232, 148, 34]]];
export const corDoCalor = (c: number, mais = 0) => {
  const h = Math.max(0, Math.min(1, c));
  let k = 0;
  while (k < QUENTE.length - 2 && h > QUENTE[k + 1][0]) k++;
  const [a, ca] = QUENTE[k];
  const [b, cb] = QUENTE[k + 1];
  const u = (h - a) / (b - a);
  return `rgb(${ca.map((v, j) => Math.min(255, Math.round(v + (cb[j] - v) * u + mais))).join(",")})`;
};

/** Faíscas saindo de um ponto, em leque. Função pura do tempo. */
export const Faiscas: React.FC<{ x: number; y: number; forca: number; angulo?: number; alcance?: number; n?: number; semente?: string }> = ({ x, y, forca, angulo = 0.75, alcance = 420, n = 48, semente = "s" }) => {
  const t = useTempo();
  if (forca <= 0.02) return null;
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, zIndex: 20, pointerEvents: "none" }}>
      {Array.from({ length: n }, (_, k) => {
        const vida = (t * (0.9 + random(`${semente}v${k}`) * 1.3) + random(`${semente}p${k}`)) % 1;
        const a = angulo + (random(`${semente}a${k}`) - 0.5) * 0.9;
        const d = 8 + vida * alcance * (0.4 + random(`${semente}d${k}`) * 0.8);
        const px = x + Math.cos(a) * d;
        const py = y + Math.sin(a) * d + vida * vida * 110;
        const c = 16 + (1 - vida) * 24;
        return <line key={k} x1={px} y1={py} x2={px - Math.cos(a) * c} y2={py - Math.sin(a) * c} stroke={k % 3 ? "#ffd67a" : "#ff9a2e"} strokeWidth={2.4} opacity={(1 - vida) * forca} />;
      })}
    </svg>
  );
};

/** Disco de freio chapado em 2D: veios do carbono, borda furada deslocada, sino metálico e pinça que não gira. */
export const Disco: React.FC<{ x: number; y: number; raio: number; calor: number; giro: number; pinca?: boolean; id?: string }> = ({ x, y, raio, calor, giro, pinca = true, id = "d" }) => {
  const c = Math.max(0, Math.min(1, calor));
  const face = corDoCalor(c);
  const clara = corDoCalor(c, 26);
  const borda = c > 0.45 ? corDoCalor(c, 25) : "#16181e";
  const furo = c > 0.45 ? "#3a1b08" : "#050507";
  const lado = 2.7 * raio;
  const metal = c > 0.5 ? ["#6e5d4c", "#d8ccba", "#f6efe2", "#b0a290", "#6e5d4c"] : ["#5a616c", "#b9c0ca", "#f0f3f7", "#8d95a1", "#4b515b"];
  return (
    <svg width={lado} height={lado} viewBox="-135 -135 270 270" style={{ position: "absolute", left: x - lado / 2, top: y - lado / 2, overflow: "visible", filter: c > 0.3 ? `drop-shadow(0 0 ${14 + c * 46}px rgba(255,120,24,${c * 0.55}))` : "drop-shadow(0 18px 30px rgba(0,0,0,.6))" }}>
      <defs>
        <radialGradient id={`${id}f`}>
          <stop offset="0.58" stopColor={face} />
          <stop offset="0.82" stopColor={clara} />
          <stop offset="1" stopColor={face} />
        </radialGradient>
        <linearGradient id={`${id}m`} x1="0" x2="1" y1="0.1" y2="0.9">
          {metal.map((m, k) => <stop key={k} offset={k / 4} stopColor={m} />)}
        </linearGradient>
        <radialGradient id={`${id}h`}>
          <stop offset="0" stopColor={c > 0.5 ? "#a9a29a" : "#333b4a"} />
          <stop offset="0.5" stopColor={c > 0.5 ? "#7a5a3a" : "#1e2430"} />
          <stop offset="1" stopColor={c > 0.5 ? "#5e3f1f" : "#141823"} />
        </radialGradient>
        <linearGradient id={`${id}p`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#d4282a" />
          <stop offset="0.6" stopColor="#a30f14" />
          <stop offset="1" stopColor="#7d0a0e" />
        </linearGradient>
        <filter id={`${id}v`} x="0" y="0" width="1" height="1">
          <feTurbulence type="turbulence" baseFrequency="0.028" numOctaves="3" seed="8" />
          <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -4 0 0 0 1.05" />
        </filter>
        <filter id={`${id}n`} x="0" y="0" width="1" height="1">
          <feTurbulence type="fractalNoise" baseFrequency="0.016" numOctaves="4" seed="21" />
          <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 0.78  0 0 0 0 0.3  1.7 0 0 0 -0.72" />
        </filter>
        <filter id={`${id}c`} x="0" y="0" width="1" height="1">
          <feTurbulence type="fractalNoise" baseFrequency="0.03 0.1" numOctaves="3" seed="4" />
          <feColorMatrix type="matrix" values="0 0 0 0 0.25  0 0 0 0 0  0 0 0 0 0  1.3 0 0 0 -0.55" />
        </filter>
        <clipPath id={`${id}a`}><circle r={100} /></clipPath>
      </defs>
      {/* segunda cópia deslocada: é ela que vira a borda com furos */}
      <circle cx={8} cy={1} r={100} fill={borda} />
      {Array.from({ length: 62 }, (_, k) => {
        const a = (k / 62) * 2.9 - 1.45 + giro * 0.003;
        return [0, 1, 2].map((f) => (
          <ellipse key={`${k}-${f}`} cx={Math.cos(a) * (100.7 + f * 2.8) + 1.4 + f * 1.7} cy={Math.sin(a) * 101 + 1} rx={0.72} ry={1.15} fill={furo} />
        ));
      })}
      <g transform={`rotate(${giro})`}>
        <circle r={100} fill={`url(#${id}f)`} stroke={c > 0.45 ? "#ffb54a" : "#c9d3df"} strokeWidth={0.9} />
        <g clipPath={`url(#${id}a)`}>
          <rect x={-100} y={-100} width={200} height={200} filter={`url(#${id}v)`} opacity={0.42 + c * 0.1} />
          <rect x={-100} y={-100} width={200} height={200} filter={`url(#${id}n)`} opacity={c * 0.62} />
        </g>
        <circle r={61} fill={`url(#${id}m)`} stroke="#22252b" strokeWidth={0.9} />
        <circle r={38} fill={`url(#${id}h)`} stroke="#14161b" strokeWidth={0.6} />
        {Array.from({ length: 12 }, (_, k) => {
          const a = (k / 12) * Math.PI * 2;
          return (
            <g key={k} transform={`translate(${Math.cos(a) * 50} ${Math.sin(a) * 50})`}>
              <circle r={3.2} fill={c > 0.5 ? "#4f3d2a" : "#2a2e38"} />
              <circle cx={-0.9} cy={-1} r={1} fill="#fff" opacity={0.55} />
            </g>
          );
        })}
      </g>
      {pinca && (
        <g>
          <path d="M-33 -106 Q0 -113 37 -104 L24 -53 Q0 -60 -20 -54 Z" fill="#6e090d" transform="translate(5 2)" />
          <path d="M-37 -102 Q0 -113 37 -102 L20 -52 Q0 -60 -20 -52 Z" fill={`url(#${id}p)`} stroke="#f27174" strokeWidth={0.7} />
          <path d="M-37 -102 Q0 -113 37 -102 L20 -52 Q0 -60 -20 -52 Z" filter={`url(#${id}c)`} opacity={0.75} />
          <path d="M-33 -100 Q0 -110 33 -100 L31 -92 Q0 -102 -31 -92 Z" fill="#ffb3b0" opacity={0.42} />
          {[-24, -16, -8, 0, 8, 16, 24].map((p) => <line key={p} x1={p * 1.13} y1={-104 + Math.abs(p) * 0.17} x2={p * 1.03} y2={-91 + Math.abs(p) * 0.15} stroke="#2a0507" strokeWidth={0.8} />)}
          {[-21, 21].map((p) => (
            <g key={p} transform={`translate(${p} -68)`}>
              <circle r={4.1} fill="#e8ebef" stroke="#3a0a0c" strokeWidth={0.5} />
              <circle r={1.7} fill="#3c4048" />
            </g>
          ))}
          {c > 0.35 && [-25, 25].map((p) => <circle key={p} cx={p * 1.25} cy={-66} r={5 + c * 9} fill="#fff1b8" opacity={c * 0.75} style={{ filter: "blur(4px)" }} />)}
        </g>
      )}
    </svg>
  );
};
