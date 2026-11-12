// Gráficos informativos (2D, por cima da cena 3D): reforçam a fala, um por vez, entrando na palavra.
// Linguagem fixa: título no alto (branco + subtítulo verde-água), um gráfico no centro, fundo azul-marinho e um só
// destaque de cor. Os rótulos vêm da fala (o diretor não inventa texto). Ver F1/docs/api_cenas.md.
import type { ReactNode } from "react";
import { FONTE, entra, suave } from "./kit";
import { ICONES } from "./modelos/icones";
import { Dinamicos } from "./InfograficosDinamicos";

export const COR = { fundo: "rgba(9,19,38,.86)", borda: "rgba(46,196,182,.55)", destaque: "#2ec4b6", texto: "#ffffff", suave: "#8fa4bf", alerta: "#ff5a4e", ouro: "#ffc93a" };

export type TituloV = { texto: string; sub?: string; i?: number };
export type GraficoV = {
  tipo: "icone" | "regua" | "bateria" | "seletor" | "numero" | "etapas" | "alerta" | "frase" | "palavra" | "ano" | "linhatempo" | "minimapa" | "perfil" | "torre" | "relogio" | "sentido";
  palavras?: { t: string; i?: number; brasil?: boolean }[]; // frase: cada palavra entra na sua hora
  marcos?: { rotulo: string; nome?: string; cor?: string; i?: number }[]; // linha do tempo
  trecho?: [number, number]; // minimapa: trecho aceso (fração da volta)
  circuito?: string; // minimapa: chave do circuito ("interlagos" padrão, "lasvegas")
  n?: number; // torre: quantos carros
  horas?: { h: number; m?: number; texto?: string; i?: number }[]; // relógio
  i?: number; i1?: number; // palavra em que entra / em que o movimento termina
  texto?: string; icone?: string; cor?: string;
  esquerda?: string; direita?: string; de?: number; ate?: number; // régua (0 = esquerda, 1 = direita), bateria (0 a 1)
  segmentos?: number; cliques?: number; valor?: number; max?: number; unidade?: string; // bateria / seletor / número
  itens?: string[]; itens_i?: number[]; // etapas (cada uma acende na sua palavra)
  pos?: "meio" | "baixo";
};

const Icone = ({ nome, lado, cor = COR.texto }: { nome: string; lado: number; cor?: string }) => (
  <svg width={lado} height={lado} viewBox="0 0 24 24" fill="none" stroke={cor} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    {(ICONES[nome] ?? ICONES.engrenagem).map((d, k) => <path key={k} d={d} />)}
  </svg>
);

const Rotulo = ({ texto, cor = COR.texto, tam = 40 }: { texto?: string; cor?: string; tam?: number }) =>
  texto ? <div style={{ marginTop: 22, fontFamily: FONTE, fontWeight: 800, fontSize: tam, letterSpacing: 2, color: cor, textAlign: "center", textShadow: "0 2px 12px rgba(0,0,0,.7)" }}>{texto}</div> : null;

/** Título da troca de assunto, no alto (abaixo da legenda): "RÁDIO — COMUNICAÇÃO" + subtítulo em destaque. */
export function Titulo({ t, titulo, inicio }: { t: number; titulo: TituloV; inicio: number }): ReactNode {
  if (t < inicio) return null;
  const e = entra(t, inicio, 0.3);
  return (
    <div style={{ position: "absolute", top: 560, left: 90, right: 90, textAlign: "center", zIndex: 45, fontFamily: FONTE, opacity: e, transform: `translateY(${(1 - e) * 14}px)` }}>
      <div style={{ fontSize: 44, fontWeight: 900, letterSpacing: 3, color: COR.texto, textShadow: "0 3px 16px rgba(0,0,0,.75)" }}>{titulo.texto}</div>
      {titulo.sub && <div style={{ marginTop: 4, fontSize: 32, fontWeight: 800, letterSpacing: 2, color: COR.destaque, textShadow: "0 3px 16px rgba(0,0,0,.75)" }}>{titulo.sub}</div>}
    </div>
  );
}

/** Um gráfico informativo. `tempo(i)` = segundo da palavra i; `ini`/`fim` = início e duração do plano. */
export function Grafico({ g, t, tempo, ini, fim, foco }: { g: GraficoV; t: number; tempo: (i?: number) => number; ini: number; fim: number; foco?: boolean }): ReactNode {
  const a = g.i !== undefined ? tempo(g.i) : ini + 0.15;
  if (t < a - 0.01) return null;
  const b = g.i1 !== undefined ? tempo(g.i1) : ini + fim * 0.85;
  const k = suave(t, a + 0.15, Math.max(a + 0.4, b)); // movimento do gráfico (marcador, bateria, cliques)
  const e = entra(t, a, 0.3);
  const cor = g.cor === "alerta" ? COR.alerta : g.cor === "ouro" ? COR.ouro : COR.destaque;
  const centro = foco || g.pos === "meio" ? 1040 : 1490; // baixo: abaixo do assunto 3D (que fica no meio do quadro)
  let corpo: ReactNode = null;
  const dinamico = Dinamicos({ g, t, tempo, ini, fim, a, k, e, cor });
  if (dinamico) return dinamico;

  if (g.tipo === "icone") {
    const r = 120;
    corpo = (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: r * 2, height: r * 2, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
          background: `radial-gradient(circle, ${cor}33 0%, rgba(9,19,38,.92) 62%)`, border: `10px solid ${cor}`,
          boxShadow: `0 0 0 22px rgba(46,196,182,.10), 0 0 60px ${cor}88` }}>
          <Icone nome={g.icone ?? "engrenagem"} lado={120} cor={COR.texto} />
        </div>
        <Rotulo texto={g.texto} />
      </div>
    );
  } else if (g.tipo === "regua") {
    const p = (g.de ?? 0.5) + ((g.ate ?? 0.5) - (g.de ?? 0.5)) * k;
    corpo = (
      <div style={{ width: 760, padding: "34px 44px", borderRadius: 26, background: COR.fundo, border: `2px solid ${COR.borda}`, fontFamily: FONTE }}>
        <div style={{ position: "relative", height: 34 }}>
          <div style={{ position: "absolute", top: 15, left: 0, right: 0, height: 4, borderRadius: 2, background: "#3a4a63" }} />
          <div style={{ position: "absolute", top: 0, left: `calc(${p * 100}% - 17px)`, width: 34, height: 34, borderRadius: "50%", background: COR.ouro, boxShadow: `0 0 20px ${COR.ouro}` }} />
        </div>
        <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", fontSize: 36, fontWeight: 800, letterSpacing: 2, color: COR.texto }}>
          <span>{g.esquerda ?? ""}</span>
          <span>{g.direita ?? ""}</span>
        </div>
      </div>
    );
  } else if (g.tipo === "bateria") {
    const n = g.segmentos ?? 5;
    const nivel = (g.de ?? 1) + ((g.ate ?? 0.4) - (g.de ?? 1)) * k;
    const baixa = nivel < 0.25;
    corpo = (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 12, padding: 16, width: 470, height: 160, borderRadius: 26, border: `8px solid ${baixa ? COR.alerta : "#c9d4e3"}`, background: COR.fundo }}>
            {Array.from({ length: n }, (_, s) => (
              <div key={s} style={{ flex: 1, borderRadius: 10, background: s < Math.round(nivel * n) ? (baixa ? COR.alerta : COR.ouro) : "rgba(255,255,255,.06)" }} />
            ))}
          </div>
          <div style={{ width: 22, height: 70, marginLeft: 6, borderRadius: 6, background: baixa ? COR.alerta : "#c9d4e3" }} />
        </div>
        <Rotulo texto={g.texto} cor={baixa ? COR.alerta : COR.texto} />
      </div>
    );
  } else if (g.tipo === "seletor") {
    const n = Math.max(2, g.cliques ?? 3);
    const passo = Math.round((g.de ?? 0) + ((g.ate ?? n - 1) - (g.de ?? 0)) * k);
    const ang = -120 + (passo / (n - 1)) * 240;
    corpo = (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <svg width={330} height={330} viewBox="-210 -210 420 420">
          <circle r={196} fill="none" stroke="rgba(46,196,182,.18)" strokeWidth={14} />
          {Array.from({ length: n }, (_, s) => {
            const q = ((-120 + (s / (n - 1)) * 240 - 90) * Math.PI) / 180;
            return <circle key={s} cx={Math.cos(q) * 176} cy={Math.sin(q) * 176} r={11} fill={s === passo ? COR.destaque : "#3a4a63"} />;
          })}
          <circle r={140} fill="#c9d4e3" stroke={cor} strokeWidth={12} />
          <circle r={112} fill="#dfe6ef" />
          <line x1={0} y1={0} x2={0} y2={-98} stroke="#1a2333" strokeWidth={16} strokeLinecap="round" transform={`rotate(${ang})`} />
        </svg>
        <Rotulo texto={g.texto ?? `${passo + 1} de ${n} cliques`} cor={COR.ouro} tam={36} />
      </div>
    );
  } else if (g.tipo === "numero") {
    const v = (g.de ?? 0) + ((g.valor ?? 0) - (g.de ?? 0)) * k;
    const max = g.max ?? (g.valor ?? 1) * 1.1;
    const barras = 14;
    corpo = (
      <div style={{ display: "flex", alignItems: "flex-end", gap: 34, padding: "26px 40px", borderRadius: 26, background: COR.fundo, border: `2px solid ${COR.borda}`, fontFamily: FONTE }}>
        <div>
          <div style={{ fontSize: 28, fontWeight: 700, color: COR.suave, letterSpacing: 2 }}>{g.unidade ?? ""}</div>
          <div style={{ fontSize: 130, lineHeight: 1, fontWeight: 900, color: COR.texto, fontVariantNumeric: "tabular-nums" }}>{Math.round(v)}</div>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 7, height: 130 }}>
          {Array.from({ length: barras }, (_, s) => (
            <div key={s} style={{ width: 16, height: 24 + s * 7.5, borderRadius: 4, background: s / barras < v / max ? (s > barras * 0.75 ? COR.ouro : COR.destaque) : "rgba(255,255,255,.08)" }} />
          ))}
        </div>
      </div>
    );
  } else if (g.tipo === "etapas") {
    const itens = g.itens ?? [];
    corpo = (
      <div style={{ display: "flex", flexDirection: "column", gap: 18, width: 720 }}>
        {itens.map((txt, s) => {
          const quando = g.itens_i?.[s] !== undefined ? tempo(g.itens_i[s]) : a + (s / Math.max(1, itens.length)) * Math.max(0.6, b - a);
          const ei = entra(t, quando, 0.3);
          const ativo = t >= quando && (s === itens.length - 1 || t < (g.itens_i?.[s + 1] !== undefined ? tempo(g.itens_i[s + 1]) : a + ((s + 1) / itens.length) * Math.max(0.6, b - a)));
          return (
            <div key={s} style={{ opacity: t >= quando ? 0.35 + 0.65 * (ativo ? 1 : 0.4) * ei : 0.18, padding: "22px 34px", borderRadius: 22, background: COR.fundo,
              border: `3px solid ${ativo ? COR.destaque : "rgba(255,255,255,.12)"}`, fontFamily: FONTE, fontSize: 44, fontWeight: 900, letterSpacing: 3,
              color: ativo ? COR.destaque : COR.texto, transform: `translateX(${(1 - ei) * -30}px)` }}>
              {txt}
            </div>
          );
        })}
      </div>
    );
  } else if (g.tipo === "alerta") {
    corpo = (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <Icone nome="alerta" lado={230} cor={COR.alerta} />
        <Rotulo texto={g.texto} cor={COR.alerta} tam={52} />
      </div>
    );
  }
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: centro, display: "flex", justifyContent: "center", zIndex: 42, opacity: e,
      transform: `translateY(-50%) scale(${0.92 + 0.08 * e})`, filter: `blur(${(1 - e) * 5}px)` }}>
      {corpo}
    </div>
  );
}
