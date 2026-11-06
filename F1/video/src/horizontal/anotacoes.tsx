// Anotação à mão por cima da cena: comenta a fala, não repete ("Por quê?", "Dominou"). Traço de pincel (borda
// irregular), preto ou na cor de destaque, desenhado a ~0,055 da largura por quadro (medida das referências).
import { MAO, sorteio, useCores, useTempo } from "./base";

type P = [number, number];
/** Jeito da mão (o editor de variedade sorteia por cena): letra, traço e marca-texto atrás da nota. */
export type Estilo = { fonte?: "ink" | "print" | "script"; traco?: number; marca?: boolean };
const FONTES = { ink: MAO, print: "Segoe Print", script: "Segoe Script" };
export type Anotacao = ({ estilo?: Estilo }) & (
  | { tipo: "seta"; de: P; para: P; curva?: number; em: number; cor?: string }
  | { tipo: "circulo"; centro: P; rx: number; ry: number; em: number; cor?: string }
  | { tipo: "sublinhado"; de: P; para: P; em: number; cor?: string }
  | { tipo: "riscado"; de: P; para: P; em: number; cor?: string }
  | { tipo: "chave"; de: P; para: P; em: number; cor?: string }
  | { tipo: "nota"; texto: string; x: number; y: number; tam?: number; giro?: number; largura?: number; em: number; cor?: string }
  | { tipo: "corrigido"; antes: string; depois: string; x: number; y: number; tam?: number; em: number; cor?: string }
  | { tipo: "caixa"; centro: P; w: number; h: number; em: number; cor?: string }
  | { tipo: "x" | "check"; centro: P; tam?: number; em: number; cor?: string }
  | { tipo: "marca"; de: P; para: P; altura?: number; em: number; cor?: string });

const VEL = 105; // px por quadro

// caminho em pontos com tremor leve de mão
const tremido = (pts: P[], semente: number, forca = 3): string =>
  pts.map(([x, y], i) => `${i ? "L" : "M"} ${(x + (sorteio(i + semente) - 0.5) * forca).toFixed(1)} ${(y + (sorteio(i * 3 + semente) - 0.5) * forca).toFixed(1)}`).join(" ");

const comprimento = (pts: P[]) => pts.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);

function caminho(a: Anotacao): P[] {
  const pts: P[] = [];
  if (a.tipo === "seta" || a.tipo === "sublinhado" || a.tipo === "riscado") {
    const [x0, y0] = a.de;
    const [x1, y1] = a.para;
    const curva = a.tipo === "seta" ? a.curva ?? 0.25 : a.tipo === "sublinhado" ? 0.04 : 0.02;
    const nx = -(y1 - y0), ny = x1 - x0;
    for (let i = 0; i <= 40; i++) {
      const s = i / 40;
      const b = Math.sin(Math.PI * s) * curva + (a.tipo === "sublinhado" ? Math.sin(s * Math.PI * 5) * 0.008 : 0);
      pts.push([x0 + (x1 - x0) * s + nx * b, y0 + (y1 - y0) * s + ny * b]);
    }
  } else if (a.tipo === "circulo") {
    // volta e meia, começando em cima à direita (como quem circula à mão)
    for (let i = 0; i <= 70; i++) {
      const g = -0.9 + (i / 70) * Math.PI * 2.15;
      const r = 1 + (sorteio(Math.floor(i / 8) + 5) - 0.5) * 0.06;
      pts.push([a.centro[0] + Math.cos(g) * a.rx * r, a.centro[1] + Math.sin(g) * a.ry * r]);
    }
  } else if (a.tipo === "caixa") {
    // retângulo à mão: cantos que passam um pouco e lados levemente tortos
    const [cx, cy] = a.centro;
    const w = a.w / 2, h = a.h / 2;
    const cantos: P[] = [[cx - w - 8, cy - h], [cx + w + 6, cy - h - 4], [cx + w, cy + h + 6], [cx - w + 4, cy + h], [cx - w - 2, cy - h - 10]];
    for (let k = 0; k < cantos.length - 1; k++) for (let i = 0; i < 10; i++) pts.push([cantos[k][0] + (cantos[k + 1][0] - cantos[k][0]) * (i / 10), cantos[k][1] + (cantos[k + 1][1] - cantos[k][1]) * (i / 10)]);
  } else if (a.tipo === "x" || a.tipo === "check") {
    const [cx, cy] = a.centro;
    const s = (a.tam ?? 90) / 2;
    const seg: P[] = a.tipo === "x" ? [[cx - s, cy - s], [cx + s, cy + s]] : [[cx - s, cy], [cx - s * 0.3, cy + s * 0.8], [cx + s, cy - s]];
    for (let k = 0; k < seg.length - 1; k++) for (let i = 0; i <= 12; i++) pts.push([seg[k][0] + (seg[k + 1][0] - seg[k][0]) * (i / 12), seg[k][1] + (seg[k + 1][1] - seg[k][1]) * (i / 12)]);
  } else if (a.tipo === "chave") {
    // chave "}" de de até para (vertical), bico no meio
    const [x, y0] = a.de;
    const y1 = a.para[1];
    const m = (y0 + y1) / 2, l = 26;
    const seg: P[] = [[x, y0], [x + l, y0 + 18], [x + l, m - 22], [x + l * 2, m], [x + l, m + 22], [x + l, y1 - 18], [x, y1]];
    for (let k = 0; k < seg.length - 1; k++) for (let i = 0; i < 8; i++) pts.push([seg[k][0] + (seg[k + 1][0] - seg[k][0]) * (i / 8), seg[k][1] + (seg[k + 1][1] - seg[k][1]) * (i / 8)]);
    pts.push(seg[seg.length - 1]);
  }
  return pts;
}

const Traco: React.FC<{ pts: P[]; k: number; cor: string; largura?: number; semente: number }> = ({ pts, k, cor, largura = 7, semente }) => (
  <path d={tremido(pts, semente)} stroke={cor} strokeWidth={largura} fill="none" strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - k} filter="url(#pincel)" />
);

/** Todas as anotações da cena (cada uma com o seu `em`, em segundos da cena). */
export const Anotacoes: React.FC<{ itens: Anotacao[] }> = ({ itens }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  return (
    <>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <filter id="pincel">
          <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves={2} seed={4} />
          <feDisplacementMap in="SourceGraphic" scale={4} />
        </filter>
        {itens.map((a, i) => {
          if (a.tipo === "nota" || a.tipo === "corrigido" || t < a.em) return null;
          const pts = a.tipo === "marca" ? [a.de, a.para] : caminho(a);
          const q = (t - a.em) * fps;
          const k = Math.min(1, (q * VEL) / comprimento(pts));
          const cor = a.cor ?? c.tinta;
          const larg = a.estilo?.traco ?? (a.tipo === "riscado" ? 9 : 7);
          if (a.tipo === "marca") {
            // marca-texto: faixa larga e translúcida passada por cima do texto
            const [x0, y0] = a.de, [x1, y1] = a.para;
            const km = Math.min(1, q / 8);
            return <line key={i} x1={x0} y1={y0} x2={x0 + (x1 - x0) * km} y2={y0 + (y1 - y0) * km} stroke={a.cor ?? c.destaque} strokeOpacity={0.55} strokeWidth={a.altura ?? 70} strokeLinecap="square" />;
          }
          if (a.tipo === "x") {
            const s = (a.tam ?? 90) / 2, [cx, cy] = a.centro;
            const k2 = Math.min(1, Math.max(0, q - 5) / 5);
            return (
              <g key={i}>
                <Traco pts={pts} k={k} cor={cor} semente={i * 17} largura={larg + 2} />
                {k2 > 0 && <Traco pts={[[cx + s, cy - s], [cx - s, cy + s]]} k={k2} cor={cor} semente={i * 23} largura={larg + 2} />}
              </g>
            );
          }
          if (a.tipo !== "seta") return <Traco key={i} pts={pts} k={k} cor={cor} semente={i * 17} largura={larg} />;
          // ponta da seta depois do traço
          const [x1, y1] = pts[pts.length - 1];
          const [x0, y0] = pts[pts.length - 4];
          const g = Math.atan2(y1 - y0, x1 - x0);
          const p = Math.min(1, Math.max(0, q - comprimento(pts) / VEL) / 4);
          const ponta: P[] = [[x1 + Math.cos(g + 2.6) * 34, y1 + Math.sin(g + 2.6) * 34], [x1, y1], [x1 + Math.cos(g - 2.6) * 34, y1 + Math.sin(g - 2.6) * 34]];
          return (
            <g key={i}>
              <Traco pts={pts} k={k} cor={cor} semente={i * 17} largura={larg} />
              {p > 0 && <Traco pts={ponta} k={p} cor={cor} semente={i * 19} largura={larg} />}
            </g>
          );
        })}
      </svg>
      {itens.map((a, i) => {
        if ((a.tipo !== "nota" && a.tipo !== "corrigido") || t < a.em) return null;
        const q = (t - a.em) * fps;
        const cor = a.cor ?? c.tinta;
        const tam = a.tam ?? 54;
        if (a.tipo === "nota") {
          const largura = a.largura ?? a.texto.length * tam * 0.5;
          const k = Math.min(1, (q * VEL * 0.5) / largura); // letra à mão é mais lenta que traço
          return (
            <div key={i} style={{ position: "absolute", left: a.x, top: a.y, width: largura + 40, fontFamily: FONTES[a.estilo?.fonte ?? "ink"], fontWeight: 700, fontSize: tam, lineHeight: 1.08, color: cor, transform: `rotate(${a.giro ?? -4}deg)`, clipPath: `inset(-20% ${100 - k * 100}% -20% -5%)` }}>
              {a.estilo?.marca && <span style={{ position: "absolute", left: -12, right: 30, top: "18%", bottom: "8%", background: c.destaque, opacity: 0.5, transform: "skewX(-6deg)" }} />}
              <span style={{ position: "relative" }}>{a.texto}</span>
            </div>
          );
        }
        // número corrigido: o antigo é riscado e o novo escrito à mão do lado
        const la = a.antes.length * tam * 0.52;
        const risco = Math.min(1, Math.max(0, q - 6) / 6);
        const novo = Math.min(1, Math.max(0, q - 14) / 14);
        return (
          <div key={i} style={{ position: "absolute", left: a.x, top: a.y, fontFamily: MAO, fontWeight: 700, fontSize: tam, color: cor, whiteSpace: "nowrap" }}>
            <span style={{ position: "relative", opacity: 0.9 }}>
              {a.antes}
              <svg width={la + 20} height={tam} style={{ position: "absolute", left: -10, top: tam * 0.1, overflow: "visible" }}>
                <Traco pts={[[0, tam * 0.55], [la * 0.5, tam * 0.45], [la + 20, tam * 0.5]]} k={risco} cor={c.destaque === cor ? c.tinta : c.destaque} semente={i * 5} largura={8} />
              </svg>
            </span>
            <span style={{ display: "inline-block", marginLeft: 24, color: c.destaque, transform: "rotate(-6deg) translateY(-18px)", clipPath: `inset(-20% ${100 - novo * 100}% -20% -5%)` }}>{a.depois}</span>
          </div>
        );
      })}
    </>
  );
};
