// Cartões 2D do horizontal: pessoa (foto P&B em papel, nome em marca-texto, citação palavra a palavra), capítulo
// (identidade própria do canal: traçado do circuito desenhado + número + título), palavra solta em tela escura.
import { Img, staticFile } from "remotion";
import { Cena, FONTE, Fundo, MAO, entra, suave, useCores, useTempo } from "./base";
import { decodificar } from "./textos";
import circuitos from "../modelos/geo/circuitos.json";

export type PessoaP = {
  nome: string;
  cargo?: string;
  foto?: string; // arquivo no public dir (foto livre/licenciada); sem foto = silhueta
  citacao?: string;
  palavras?: number[]; // segundo (da cena) em que cada palavra da citação aparece; sem isso, uma a cada 0,28 s
  em?: number;
  lado?: "esq" | "dir";
};

const Silhueta: React.FC = () => (
  <svg viewBox="0 0 400 480" width="100%" height="100%">
    <rect width="400" height="480" fill="#c9c7c2" />
    <circle cx="200" cy="190" r="92" fill="#8d8b87" />
    <path d="M 40 480 C 50 340, 130 300, 200 300 C 270 300, 350 340, 360 480 Z" fill="#8d8b87" />
  </svg>
);

/** Pessoa na primeira menção: cartão de papel inclinado com sombra; a citação acompanha a fala, palavra a palavra. */
export const Pessoa: React.FC<PessoaP> = ({ nome, cargo, foto, citacao, palavras, em = 0, lado = "esq" }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  const k = entra(((t - em) * fps) / 14);
  const marca = suave(t, em + 0.35, em + 0.75);
  const ws = citacao ? citacao.split(/\s+/) : [];
  const quando = (i: number) => palavras?.[i] ?? em + 0.9 + i * 0.28;
  const x = lado === "esq" ? 180 : 1040;
  return (
    <Cena fundo={<Fundo modo="claro" />}>
      <div style={{ position: "absolute", left: x, top: 150, width: 560, height: 700, transform: `translateY(${(1 - k) * 80}px) rotate(${-4 + (1 - k) * 6}deg)`, opacity: k, background: "#fbfaf6", boxShadow: "0 30px 60px #0000003a, 0 6px 14px #00000026", padding: 26 }}>
        <div style={{ width: "100%", height: 520, overflow: "hidden", filter: "grayscale(1) contrast(1.15)" }}>
          {foto ? <Img src={staticFile(foto)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : <Silhueta />}
        </div>
        <div style={{ position: "relative", marginTop: 22, display: "inline-block", fontFamily: FONTE, fontStretch: "condensed", fontWeight: 700, fontSize: 64, color: c.tinta, lineHeight: 1 }}>
          <div style={{ position: "absolute", left: -10, right: -10, top: 12, bottom: -4, background: c.destaque, opacity: 0.85, transform: `skewX(-8deg) scaleX(${marca})`, transformOrigin: "left", zIndex: 0 }} />
          <span style={{ position: "relative" }}>{nome.toUpperCase()}</span>
        </div>
        {cargo && <div style={{ fontFamily: FONTE, fontSize: 28, letterSpacing: 2, color: "#55534f", marginTop: 8 }}>{cargo.toUpperCase()}</div>}
      </div>
      {citacao && (
        <div style={{ position: "absolute", left: lado === "esq" ? 860 : 160, top: 300, width: 880, fontFamily: FONTE, fontWeight: 700, fontSize: 66, lineHeight: 1.15, color: c.tinta }}>
          <span style={{ fontFamily: MAO, fontSize: 140, color: c.destaque, position: "absolute", left: -70, top: -70 }}>“</span>
          {ws.map((w, i) => (
            <span key={i} style={{ opacity: t >= quando(i) ? 1 : 0.12, color: t >= quando(i) && t < quando(i) + 0.35 ? c.destaque : c.tinta }}>
              {w}{" "}
            </span>
          ))}
        </div>
      )}
    </Cena>
  );
};

type Circuito = { pontos: number[][] };
function contorno(chave: string, caixa: number): string {
  const pts = (circuitos as unknown as Record<string, Circuito>)[chave].pontos;
  const lat0 = pts[0][1];
  const xy = pts.map(([lon, lat]) => [lon * Math.cos((lat0 * Math.PI) / 180), -lat]);
  const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  const s = caixa / Math.max(Math.max(...xs) - x0, Math.max(...ys) - y0);
  return xy.map(([x, y], i) => `${i ? "L" : "M"} ${((x - x0) * s).toFixed(1)} ${((y - y0) * s).toFixed(1)}`).join(" ") + " Z";
}

export type CapituloP = { n: number; titulo: string; circuito?: string; cor?: string };

/** Capítulo (identidade própria, não o "CHAPTER N" das referências): traçado do circuito se desenhando na cor do
 *  vídeo, "PARTE 0N" decodificando e o título entrando por baixo. Entra antes da fala da seção (3–5 s). */
export const Capitulo: React.FC<CapituloP> = ({ n, titulo, circuito = "interlagos", cor }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  const tinta = cor ?? c.destaque;
  const desenho = suave(t, 0.1, 1.6);
  const sobe = entra(((t - 0.6) * fps) / 14);
  return (
    <Cena fundo={<Fundo modo="escuro" />}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <g transform={`translate(1060 170) rotate(${-6 + t * 0.8} 370 370)`}>
          <path d={contorno(circuito, 740)} fill="none" stroke={tinta} strokeWidth={14} strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - desenho} opacity={0.95} />
        </g>
      </svg>
      <div style={{ position: "absolute", left: 160, top: 360, fontFamily: FONTE, fontWeight: 700, fontSize: 46, letterSpacing: 10, color: tinta }}>
        {decodificar(`PARTE ${String(n).padStart(2, "0")}`, (t - 0.2) * fps, n)}
      </div>
      <div style={{ position: "absolute", left: 160, top: 420, width: 900, overflow: "hidden" }}>
        <div style={{ fontFamily: FONTE, fontStretch: "condensed", fontWeight: 700, fontSize: 150, lineHeight: 0.95, color: "#ffffff", transform: `translateY(${(1 - sobe) * 110}%)` }}>{titulo.toUpperCase()}</div>
      </div>
      <div style={{ position: "absolute", left: 160, top: 400, height: 6, width: 220 * suave(t, 0.3, 0.9), background: tinta }} />
    </Cena>
  );
};

/** Palavra solta em tela escura (momento dramático), com decodificação; ou em cor cheia (virada de argumento). */
export const Solta: React.FC<{ texto: string; modo?: "escuro" | "cheio"; em?: number; sub?: string }> = ({ texto, modo = "escuro", em = 0.15, sub }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  const cor = modo === "cheio" ? "#ffffff" : c.destaque;
  return (
    <Cena fundo={<Fundo modo={modo} />}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", fontFamily: FONTE, fontStretch: "condensed", fontWeight: 700, fontSize: 340, lineHeight: 1, color: cor, transform: `scale(${1 + t * 0.012})` }}>
        {decodificar(texto.toUpperCase(), (t - em) * fps, 9)}
      </div>
      {sub && <div style={{ position: "absolute", left: 0, right: 0, top: 700, textAlign: "center", fontFamily: FONTE, fontWeight: 700, fontSize: 44, letterSpacing: 6, color: modo === "cheio" ? "#ffffffcc" : "#ffffffb0", opacity: suave(t, em + 0.5, em + 0.8) }}>{sub.toUpperCase()}</div>}
    </Cena>
  );
};
