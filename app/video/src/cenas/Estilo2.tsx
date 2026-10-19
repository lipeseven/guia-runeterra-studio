// Recursos visuais da "versão 2" do canal (vídeos a partir de 2026-10-19). Vídeo antigo (estilo 1) não passa por
// aqui: o Montagem só usa este arquivo quando trecho.estilo === 2 — e as linhas que o chamam são marcadas
// `impressao:ignorar`, então o cache dos blocos dos vídeos antigos não muda.
//   - transições entre cenas: a imagem nova entra de fora da tela EMPURRANDO a anterior ou SOBREPONDO-a;
//   - cartão "livre": a imagem não é recortada pela caixa (o fundo é branco, ela tem espaço para andar).
import { createContext, useContext } from "react";
import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame } from "remotion";
import type { Cena } from "../tipos";

export const EstiloCtx = createContext(1);
export const useEstilo = () => useContext(EstiloCtx);

/** Duração da transição (60 fps → 0,3 s). */
export const QUADROS_TRANSICAO = 18;

export type Transicao =
  | "empurrar_esq" | "empurrar_dir" | "empurrar_cima"
  | "sobrepor_esq" | "sobrepor_dir" | "sobrepor_cima";

const transicaoDa = (cena: Cena | undefined): Transicao | undefined =>
  (cena as { transicao?: Transicao } | undefined)?.transicao;

const ease = Easing.inOut(Easing.cubic);
const prog = (frame: number, de: number) =>
  interpolate(frame, [de, de + QUADROS_TRANSICAO], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

/** Deslocamento (px) de quem ENTRA: vem de fora da tela até o lugar. "esq" = vem da direita indo para a esquerda. */
const fora = (t: Transicao, resto: number): string => {
  if (t.endsWith("_cima")) return `translateY(${1080 * resto}px)`;
  return `translateX(${(t.endsWith("_esq") ? 1920 : -1920) * resto}px)`;
};

/** Cena com as transições de entrada (dela) e de saída (empurrada pela próxima, se for "empurrar"). */
export const CenaEstilo2: React.FC<{
  cenas: Cena[];
  k: number;
  de: number;
  ate: number;
  children: React.ReactNode;
}> = ({ cenas, k, de, ate, children }) => {
  const cena = cenas[k];
  const prox = cenas[k + 1];
  // transição só dentro do mesmo bloco (o render por blocos não enxerga a cena do bloco vizinho)
  const entra = k > 0 && cenas[k - 1].bloco === cena.bloco ? transicaoDa(cena) : undefined;
  const sai = prox && prox.bloco === cena.bloco ? transicaoDa(prox) : undefined;
  const dur = Math.max(1, ate - de);
  return (
    <Sequence from={de} durationInFrames={dur + (sai ? QUADROS_TRANSICAO : 0)} name={`${k + 1}. ${cena.tipo}`}>
      <EstiloCtx.Provider value={2}>
        <Animado entra={entra} sai={sai} dur={dur}>
          {children}
        </Animado>
      </EstiloCtx.Provider>
    </Sequence>
  );
};

const Animado: React.FC<{ entra?: Transicao; sai?: Transicao; dur: number; children: React.ReactNode }> = ({
  entra,
  sai,
  dur,
  children,
}) => {
  const frame = useCurrentFrame();
  let transform = "none";
  let sombra: string | undefined;
  if (entra && frame < QUADROS_TRANSICAO) {
    transform = fora(entra, 1 - prog(frame, 0));
    if (entra.startsWith("sobrepor")) sombra = "0 0 60px rgba(0,0,0,0.35)";
  } else if (sai && sai.startsWith("empurrar") && frame >= dur) {
    // empurrada para fora pelo lado oposto ao que a próxima entra
    transform = fora(sai, -prog(frame, dur));
  }
  return <AbsoluteFill style={{ transform, boxShadow: sombra }}>{children}</AbsoluteFill>;
};
