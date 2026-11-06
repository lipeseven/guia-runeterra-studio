// Textos do horizontal: palavra gigante (atrás do carro), decodificação, contador e palavra solta.
// Medidas das referências (24 fps → 30 fps): decodificação 0,52 letra/quadro em ordem aleatória, 2–4 letras-isca que
// trocam por 2–4 quadros; saída inversa em ~12 quadros. A palavra aparece 0–1 s depois da fala.
import { FONTE, sorteio, useCores, useTempo, entra } from "./base";

const LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

/** Texto na tela no instante q (quadros desde `em`): letras assentam em ordem aleatória; algumas iscas trocam antes. */
export function decodificar(texto: string, q: number, semente = 1, sair?: number): string {
  const n = texto.length;
  const ordem = [...Array(n).keys()].sort((a, b) => sorteio(a * 7 + semente) - sorteio(b * 7 + semente));
  const pos = new Array<number>(n);
  ordem.forEach((i, k) => (pos[i] = k));
  const assentadas = Math.max(0, q) * 0.52;
  const fora = sair === undefined ? 0 : Math.max(0, sair) * (n / 12);
  return texto
    .split("")
    .map((ch, i) => {
      if (ch === " ") return " ";
      if (n - pos[i] <= fora) return "";
      if (q < 0) return "";
      if (pos[i] < assentadas) {
        // isca: a letra assenta, troca por 3 quadros e volta
        const isca = sorteio(i * 13 + semente) < 0.25;
        const desde = q - pos[i] / 0.52;
        if (isca && desde > 2 && desde < 5) return LETRAS[Math.floor(sorteio(i + q * 3) * LETRAS.length)];
        return ch;
      }
      return pos[i] < assentadas + 6 ? LETRAS[Math.floor(sorteio(i * 31 + q) * LETRAS.length)] : "";
    })
    .join("");
}

export type PalavraP = { texto: string; em?: number; ate?: number; tam?: number; topo?: number; cor?: string; giro?: number; x?: number };

/** Palavra gigante: 1–3 palavras-chave, condensada ultra-bold, 25–60% da altura. Vai ANTES do canvas 3D (atrás do carro). */
export const Palavra: React.FC<PalavraP> = ({ texto, em = 0, ate, tam = 440, topo = 120, cor, giro = 0, x = 0 }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  const q = (t - em) * fps;
  const sair = ate === undefined ? undefined : (t - ate) * fps;
  // cabe na largura (letra condensada ~0,5 do corpo): palavra longa diminui em vez de sair da tela
  const corpo = Math.min(tam, 1800 / (Math.max(...texto.split("\n").map((l) => l.length)) * 0.5));
  return (
    <div
      style={{
        position: "absolute", left: x, right: -x, top: topo, textAlign: "center", fontFamily: FONTE, fontStretch: "condensed",
        fontWeight: 700, fontSize: corpo, letterSpacing: -corpo * 0.012, lineHeight: 1, color: cor ?? c.destaque, whiteSpace: "pre",
        transform: `rotate(${giro}deg)`,
      }}
    >
      {decodificar(texto.toUpperCase(), q, texto.length, sair)}
    </div>
  );
};

/** Número que sobe até o valor falado (5–7 s parado na tela), com unidade menor ao lado. */
export const Contador: React.FC<{ valor: number; de?: number; casas?: number; unidade?: string; rotulo?: string; em?: number; dur?: number; x: number; y: number; tam?: number; cor?: string }> = ({
  valor, de = 0, casas = 0, unidade = "", rotulo, em = 0, dur = 1.2, x, y, tam = 220, cor,
}) => {
  const c = useCores();
  const { t } = useTempo();
  if (t < em) return null;
  const v = de + (valor - de) * entra((t - em) / dur);
  return (
    <div style={{ position: "absolute", left: x, top: y, fontFamily: FONTE, fontStretch: "condensed", fontWeight: 700, color: cor ?? c.destaque, lineHeight: 0.9 }}>
      <span style={{ fontSize: tam }}>{v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })}</span>
      <span style={{ fontSize: tam * 0.38, marginLeft: tam * 0.06 }}>{unidade}</span>
      {rotulo && <div style={{ fontSize: tam * 0.2, letterSpacing: 2, opacity: 0.85 }}>{rotulo}</div>}
    </div>
  );
};

/** Rótulo pequeno com linha-guia e ponto quadrado (microlegenda técnica). */
export const Rotulo: React.FC<{ texto: string; de: [number, number]; para: [number, number]; em?: number; cor?: string }> = ({ texto, de, para, em = 0, cor }) => {
  const c = useCores();
  const { t, fps } = useTempo();
  const k = entra(((t - em) * fps) / 10);
  if (t < em) return null;
  const px = de[0] + (para[0] - de[0]) * k;
  const py = de[1] + (para[1] - de[1]) * k;
  const tinta = cor ?? c.tinta;
  return (
    <>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <rect x={de[0] - 6} y={de[1] - 6} width={12} height={12} fill={tinta} />
        <line x1={de[0]} y1={de[1]} x2={px} y2={py} stroke={tinta} strokeWidth={2.5} />
      </svg>
      <div style={{ position: "absolute", left: para[0] + 10, top: para[1] - 22, fontFamily: FONTE, fontWeight: 700, fontSize: 34, letterSpacing: 1.5, color: tinta, opacity: k }}>
        {decodificar(texto.toUpperCase(), (t - em) * fps * 2, 3)}
      </div>
    </>
  );
};
