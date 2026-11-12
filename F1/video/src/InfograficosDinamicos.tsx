// Gráficos que interagem com a cena (decisão do Felipe, 2026-11-04): cartões empilhados ("etapas") cansam; estes mudam com a
// fala e com o carro. frase, palavra, ano, linhatempo, minimapa, perfil, torre, relogio, sentido. Ver F1/docs/api_cenas.md.
import type { CSSProperties, ReactNode } from "react";
import type { GraficoV } from "./Infograficos";
import { FONTE, entra, suave } from "./kit";
import CIRCUITOS from "./modelos/geo/circuitos.json";

const COR = { fundo: "rgba(9,19,38,.86)", borda: "rgba(46,196,182,.55)", destaque: "#2ec4b6", texto: "#ffffff", suave: "#8fa4bf", alerta: "#ff5a4e", ouro: "#ffc93a", subiu: "#2ee59d" };
const PAINEL: CSSProperties = { borderRadius: 30, background: COR.fundo, border: `2px solid ${COR.borda}`, fontFamily: FONTE, boxShadow: "0 18px 60px rgba(0,0,0,.45)" };

const TODOS = CIRCUITOS as unknown as Record<string, { pontos: [number, number][]; alt?: number[] }>;
const interlagos = TODOS.interlagos;

/** Traçado num quadrado de `lado` px, norte para cima. `nome` = chave do circuito (padrão: Interlagos). */
function tracado2D(lado: number, nome = "interlagos") {
  const pts = (TODOS[nome] ?? interlagos).pontos.slice(0, -1);
  const lat = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  const kx = Math.cos((lat * Math.PI) / 180);
  const xs = pts.map((p) => p[0] * kx), ys = pts.map((p) => -p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  const e = (lado - 28) / Math.max(Math.max(...xs) - x0, Math.max(...ys) - y0);
  return pts.map((_, i) => [14 + (xs[i] - x0) * e, 14 + (ys[i] - y0) * e] as [number, number]);
}

const naVolta = (lista: [number, number][], f: number): [number, number] => {
  const u = (((f % 1) + 1) % 1) * lista.length;
  const i = Math.floor(u), a = lista[i], b = lista[(i + 1) % lista.length];
  return [a[0] + (b[0] - a[0]) * (u - i), a[1] + (b[1] - a[1]) * (u - i)];
};

const Rotulo = ({ texto, cor = COR.texto, tam = 40 }: { texto?: string; cor?: string; tam?: number }) =>
  texto ? <div style={{ marginTop: 16, fontFamily: FONTE, fontWeight: 800, fontSize: tam, letterSpacing: 2, color: cor, textAlign: "center", textShadow: "0 2px 12px rgba(0,0,0,.7)" }}>{texto}</div> : null;

const fmtHora = (x: { h: number; m?: number }) => `${x.h}H${x.m ? String(x.m).padStart(2, "0") : ""}`;

type Args = { g: GraficoV; t: number; tempo: (i?: number) => number; ini: number; fim: number; a: number; k: number; e: number; cor: string };

export function Dinamicos({ g, t, tempo, ini, fim, a, k, e, cor }: Args): ReactNode {
  const noPlano = Math.max(0, Math.min(1, (t - ini) / fim));
  const centro = (corpo: ReactNode, top = 1490) => (
    <div style={{ position: "absolute", left: 0, right: 0, top, display: "flex", justifyContent: "center", zIndex: 42, opacity: e, transform: `translateY(-50%) scale(${0.94 + 0.06 * e})` }}>{corpo}</div>
  );

  if (g.tipo === "frase") {
    // a pergunta escrita na tela, palavra por palavra; "Brasil" em verde e amarelo, com um traço que corre embaixo
    return centro(
      <div style={{ width: 960, display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline", textAlign: "center", gap: "6px 30px", fontFamily: FONTE }}>
        {(g.palavras ?? []).map((w, s) => {
          const em = w.i !== undefined ? tempo(w.i) : a + s * 0.25;
          const ew = entra(t, em, 0.2);
          const traco = suave(t, em + 0.1, em + 0.55);
          const brasil: CSSProperties = { backgroundImage: "linear-gradient(100deg, #19c15c 0%, #19c15c 38%, #ffdf00 72%, #ffdf00 100%)", WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", filter: "drop-shadow(0 4px 18px rgba(25,193,92,.45))" };
          return (
            <span key={s} style={{ position: "relative", opacity: t >= em ? ew : 0, transform: `translateY(${(1 - ew) * 26}px)`, fontWeight: 900, fontSize: w.brasil ? 190 : 124, lineHeight: 1.08, textAlign: "center", color: COR.texto, ...(w.brasil ? brasil : { textShadow: "0 4px 22px rgba(0,0,0,.65)" }) }}>
              {w.t}
              {w.brasil && <span style={{ position: "absolute", left: 4, bottom: -8, height: 12, borderRadius: 6, width: `${traco * 97}%`, background: "linear-gradient(90deg, #19c15c, #ffdf00)", boxShadow: "0 0 22px rgba(255,223,0,.55)" }} />}
            </span>
          );
        })}
      </div>,
      860,
    );
  }

  if (g.tipo === "palavra") {
    // uma palavra grande no corte rápido de uma lista falada
    return centro(<div style={{ fontFamily: FONTE, fontWeight: 900, fontSize: 118, letterSpacing: 2, color: COR.texto, textAlign: "center", textShadow: `0 6px 34px rgba(0,0,0,.85), 0 0 42px ${cor}66`, borderBottom: `10px solid ${cor}`, padding: "0 26px 12px", maxWidth: 940, boxSizing: "border-box" }}>{g.texto}</div>, 1620);
  }

  if (g.tipo === "ano") {
    // o ano rola até o valor falado
    const v = Math.round((g.de ?? 2026) + ((g.valor ?? 1973) - (g.de ?? 2026)) * k);
    const chegou = k >= 1;
    return centro(
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", fontFamily: FONTE }}>
        <div style={{ fontSize: 250, lineHeight: 1, fontWeight: 900, fontVariantNumeric: "tabular-nums", letterSpacing: 6, color: chegou ? COR.ouro : COR.texto, textShadow: `0 8px 44px rgba(0,0,0,.75)${chegou ? `, 0 0 60px ${COR.ouro}88` : ""}` }}>{v}</div>
        <Rotulo texto={g.texto} tam={42} />
      </div>,
      1440,
    );
  }

  if (g.tipo === "linhatempo") {
    // o marco atual em destaque com a cor do carro; os anteriores ficam acesos na linha
    const marcos = g.marcos ?? [];
    const em = marcos.map((m, s) => (m.i !== undefined ? tempo(m.i) : a + s));
    let atual = 0;
    em.forEach((q, s) => { if (t >= q) atual = s; });
    const m = marcos[atual];
    const ea = entra(t, em[atual], 0.28);
    const n = Math.max(1, marcos.length - 1);
    return centro(
      <div style={{ ...PAINEL, width: 960, padding: "26px 38px 28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28, minHeight: 124, opacity: ea, transform: `translateX(${(1 - ea) * 26}px)` }}>
          <div style={{ width: 16, height: 112, borderRadius: 8, background: m?.cor ?? COR.destaque }} />
          <div style={{ fontSize: 110, fontWeight: 900, lineHeight: 1, color: COR.ouro, fontVariantNumeric: "tabular-nums" }}>{m?.rotulo}</div>
          <div style={{ fontSize: 48, fontWeight: 800, lineHeight: 1.05, color: COR.texto }}>{m?.nome}</div>
        </div>
        <div style={{ position: "relative", height: 66, marginTop: 18 }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 11, height: 4, background: "#33435c", borderRadius: 2 }} />
          <div style={{ position: "absolute", left: 0, top: 11, height: 4, background: COR.destaque, borderRadius: 2, width: `${((Math.max(0, atual - 1) + (atual ? ea : 0)) / n) * 100}%` }} />
          {marcos.map((x, s) => {
            const on = s <= atual;
            const canto = s === 0 ? "flex-start" : s === marcos.length - 1 ? "flex-end" : "center";
            return (
              <div key={s} style={{ position: "absolute", left: `${(s / n) * 100}%`, top: 0, transform: `translateX(${s === 0 ? 0 : s === marcos.length - 1 ? -100 : -50}%)`, display: "flex", flexDirection: "column", alignItems: canto }}>
                <div style={{ width: 26, height: 26, borderRadius: "50%", background: on ? x.cor ?? COR.destaque : "#22304a", border: `3px solid ${on ? "#fff" : "#44546e"}` }} />
                <div style={{ marginTop: 4, fontSize: 28, fontWeight: 800, color: on ? COR.texto : COR.suave }}>{x.rotulo}</div>
              </div>
            );
          })}
        </div>
      </div>,
      1520,
    );
  }

  if (g.tipo === "minimapa") {
    // o traçado real com o trecho aceso e o ponto do carro; de/ate = fração da volta do início ao fim do plano, a mesma da cena
    const L = 230;
    const pts = tracado2D(L, g.circuito);
    const [x, y] = naVolta(pts, (g.de ?? 0) + ((g.ate ?? 0) - (g.de ?? 0)) * noPlano);
    const [ta, tb] = g.trecho ?? [g.de ?? 0, g.ate ?? 0];
    const m = Math.max(2, Math.ceil((tb - ta) * pts.length) * 2);
    const seg = Array.from({ length: m + 1 }, (_, s) => naVolta(pts, ta + (s / m) * (tb - ta)));
    return (
      <div style={{ ...PAINEL, position: "absolute", right: 32, top: 1500, padding: 14, zIndex: 42, opacity: e, transform: `translateX(${(1 - e) * 60}px)` }}>
        <svg width={L} height={L}>
          <polygon points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke="#50617c" strokeWidth={9} strokeLinejoin="round" />
          <polyline points={seg.map((p) => p.join(",")).join(" ")} fill="none" stroke={COR.ouro} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" />
          <circle cx={x} cy={y} r={10} fill="#fff" stroke={COR.alerta} strokeWidth={5} />
        </svg>
        {g.texto && <div style={{ marginTop: 4, textAlign: "center", fontSize: 26, fontWeight: 900, letterSpacing: 1, color: COR.texto }}>{g.texto}</div>}
      </div>
    );
  }

  if (g.tipo === "perfil") {
    // perfil de altitude real da volta (SRTM 30 m), com o ponto do carro subindo e descendo
    const alt = interlagos.alt ?? [];
    const W = 900, H = 230;
    const lo = Math.min(...alt), hi = Math.max(...alt);
    const px = (fr: number) => 10 + fr * (W - 20);
    const py = (m: number) => H - 22 - ((m - lo) / (hi - lo)) * (H - 56);
    const f = Math.max(0, Math.min(0.999, (g.de ?? 0) + ((g.ate ?? 1) - (g.de ?? 0)) * noPlano));
    const u = f * alt.length, i0 = Math.floor(u);
    const am = alt[i0] + ((alt[(i0 + 1) % alt.length] ?? alt[i0]) - alt[i0]) * (u - i0);
    const linha = alt.map((m, s) => `${px(s / alt.length)},${py(m)}`).join(" ");
    const feita = [...alt.slice(0, i0 + 1).map((m, s) => `${px(s / alt.length)},${py(m)}`), `${px(f)},${py(am)}`].join(" ");
    return centro(
      <div style={{ ...PAINEL, padding: "22px 26px 18px" }}>
        <svg width={W} height={H}>
          <polygon points={`10,${H} ${linha} ${W - 10},${H}`} fill="rgba(46,196,182,.14)" />
          <polyline points={linha} fill="none" stroke="#50617c" strokeWidth={6} strokeLinejoin="round" />
          <polyline points={feita} fill="none" stroke={COR.destaque} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round" />
          <circle cx={px(f)} cy={py(am)} r={15} fill="#fff" stroke={COR.alerta} strokeWidth={6} />
        </svg>
        <Rotulo texto={g.texto} tam={36} />
      </div>,
      1510,
    );
  }

  if (g.tipo === "torre") {
    // torre de classificação sem nomes: a linha acesa cai ou sobe, e quem ela passa troca de lugar com ela
    const n = g.n ?? 6;
    const de = g.de ?? 1, ate = g.ate ?? 4;
    const pos = de + (ate - de) * k;
    const sobe = ate < de;
    const corLinha = sobe ? COR.subiu : COR.alerta;
    const ALT = 60;
    const lugares = Array.from({ length: n }, (_, s) => s).filter((s) => s !== de);
    return centro(
      <div style={{ display: "flex", alignItems: "center", gap: 30, fontFamily: FONTE }}>
        <div style={{ position: "relative", width: 320, height: n * ALT + 24, borderRadius: 24, background: COR.fundo, border: `2px solid ${COR.borda}` }}>
          {lugares.map((s, c) => {
            const passou = sobe ? (s < de && pos <= s ? 1 : s < de && pos < s + 1 ? s + 1 - pos : 0) : (s > de && pos >= s ? 1 : s > de && pos > s - 1 ? pos - (s - 1) : 0);
            const y = s + (sobe ? passou : -passou);
            return (
              <div key={s} style={{ position: "absolute", left: 12, right: 12, top: 12 + y * ALT, height: ALT - 10, borderRadius: 10, background: "#26344c", display: "flex", alignItems: "center", gap: 14, padding: "0 14px" }}>
                <div style={{ width: 12, height: 32, borderRadius: 4, background: ["#d11f4e", "#d9571a", "#0f8f80", "#2547c4", "#7a35c0"][c % 5] }} />
                <div style={{ flex: 1, height: 12, borderRadius: 6, background: "#4c5d78" }} />
              </div>
            );
          })}
          <div style={{ position: "absolute", left: 6, right: 6, top: 9 + pos * ALT, height: ALT - 4, borderRadius: 12, background: corLinha, display: "flex", alignItems: "center", gap: 14, padding: "0 20px", boxShadow: `0 0 30px ${corLinha}` }}>
            <div style={{ width: 12, height: 32, borderRadius: 4, background: "#fff" }} />
            <div style={{ flex: 1, height: 12, borderRadius: 6, background: "rgba(255,255,255,.75)" }} />
          </div>
        </div>
        <div style={{ width: 400, padding: "18px 24px", borderRadius: 24, background: COR.fundo, fontSize: 56, fontWeight: 900, lineHeight: 1.08, color: corLinha }}>
          {g.texto}
          <div style={{ marginTop: 6, fontSize: 88, lineHeight: 1 }}>{sobe ? "▲" : "▼"}</div>
        </div>
      </div>,
      1480,
    );
  }

  if (g.tipo === "relogio") {
    // relógio de ponteiros que gira até a hora falada; cada hora vem com o nome da sessão
    const horas = g.horas ?? [];
    const em = horas.map((h, s) => (h.i !== undefined ? tempo(h.i) : a + s));
    let atual = 0;
    em.forEach((q, s) => { if (t >= q - 0.45) atual = s; });
    const antes = atual > 0 ? horas[atual - 1] : { h: 8, m: 0 };
    const h = horas[atual] ?? { h: 12, m: 0 };
    const gira = suave(t, em[atual] - 0.45, em[atual]);
    const min = (x: { h: number; m?: number }) => x.h * 60 + (x.m ?? 0);
    const mm = min(antes) + (min(h) - min(antes)) * gira;
    const R = 145;
    const passou = t >= em[atual];
    return centro(
      <div style={{ ...PAINEL, display: "flex", alignItems: "center", gap: 34, padding: "26px 40px", width: 960, boxSizing: "border-box" }}>
        <svg width={R * 2} height={R * 2} viewBox={`${-R} ${-R} ${R * 2} ${R * 2}`} style={{ flexShrink: 0 }}>
          <circle r={R - 5} fill="#f4f6fa" stroke={COR.destaque} strokeWidth={10} />
          {Array.from({ length: 12 }, (_, s) => <line key={s} x1={0} y1={-R + 20} x2={0} y2={-R + 40} stroke="#1a2333" strokeWidth={s % 3 ? 4 : 9} strokeLinecap="round" transform={`rotate(${s * 30})`} />)}
          <line x1={0} y1={14} x2={0} y2={-R * 0.48} stroke="#1a2333" strokeWidth={13} strokeLinecap="round" transform={`rotate(${(mm / 720) * 360})`} />
          <line x1={0} y1={18} x2={0} y2={-R * 0.72} stroke={COR.alerta} strokeWidth={8} strokeLinecap="round" transform={`rotate(${(mm / 60) * 360})`} />
          <circle r={11} fill="#1a2333" />
        </svg>
        <div>
          {g.texto && <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: 3, color: COR.suave }}>{g.texto}</div>}
          {(passou || atual > 0) && (
            // enquanto o ponteiro gira, a hora anterior continua escrita; o painel nunca fica vazio
            <div style={{ opacity: passou ? entra(t, em[atual], 0.2) : 1 }}>
              <div style={{ fontSize: 118, lineHeight: 1.02, fontWeight: 900, color: COR.ouro, fontVariantNumeric: "tabular-nums" }}>{fmtHora(passou ? h : antes)}</div>
              <div style={{ fontSize: 38, fontWeight: 800, color: COR.texto }}>{(passou ? h : horas[atual - 1]).texto}</div>
            </div>
          )}
        </div>
      </div>,
      1510,
    );
  }

  if (g.tipo === "sentido") {
    // seta circular girando no sentido da volta
    return centro(
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <svg width={280} height={280} viewBox="-150 -150 300 300" style={{ transform: `rotate(${-t * 110}deg)` }}>
          <circle r={124} fill="rgba(9,19,38,.82)" />
          <path d="M 80 -72 A 108 108 0 1 0 108 0" fill="none" stroke={COR.ouro} strokeWidth={22} strokeLinecap="round" />
          <path d="M 44 -112 L 112 -112 L 88 -46 Z" fill={COR.ouro} />
        </svg>
        <Rotulo texto={g.texto} cor={COR.ouro} tam={58} />
      </div>,
      1470,
    );
  }
  return null;
}
