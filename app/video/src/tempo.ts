import { random } from "remotion";
import type { Palavra } from "./tipos";

/** Quadro em que a palavra começa a ser falada. */
export const quadroDaPalavra = (palavras: Palavra[], indice: number, fps: number) =>
  Math.round(palavras[Math.min(indice, palavras.length - 1)].i * fps);

/**
 * "Imperfeição humana" no corte: um editor não corta sempre no quadro exato do início da palavra.
 * Antecipa o corte de 0 a 4 quadros (determinístico pela semente, para o render ser reproduzível).
 */
export const folgaDeCorte = (semente: string) => Math.round(random(`corte-${semente}`) * 4);

/** Valor determinístico entre a e b para variar movimentos sem parecer carimbo. */
export const variar = (semente: string | number, a: number, b: number) =>
  a + random(`var-${semente}`) * (b - a);
