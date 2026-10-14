// Biblioteca de efeitos. Quem escolhe qual efeito usar em cada momento é o diretor
// (tools/direcao/variacao.py), que evita repetições ao longo do vídeo inteiro.
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const EFEITOS_TEXTO = [
  "corte", "fade", "subir", "descer", "esquerda", "direita",
  "maquina", "palavras", "pop", "desfoque", "revelar", "espacar",
] as const;
export const EFEITOS_IMAGEM = [
  "corte", "fade", "deslizar_esq", "deslizar_dir", "deslizar_cima",
  "assentar", "revelar_esq", "revelar_dir", "desfoque", "pop", "giro", "clarao",
] as const;
export const MOVIMENTOS = [
  "aproximar", "afastar", "pan_esq", "pan_dir", "subir", "descer", "parado", "aproximar_pan",
] as const;

export type EfeitoTexto = (typeof EFEITOS_TEXTO)[number];
export type EfeitoImagem = (typeof EFEITOS_IMAGEM)[number];
export type TipoMovimento = (typeof MOVIMENTOS)[number];

export type Entrada<E> = { efeito: E; quadros: number };
export type Movimento = { tipo: TipoMovimento; intensidade: number };

const suave = Easing.out(Easing.cubic);
const progresso = (frame: number, desde: number, quadros: number) =>
  interpolate(frame, [desde, desde + Math.max(1, quadros)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: suave,
  });

/** Texto que entra com o efeito indicado a partir do quadro `desde` (relativo à cena). */
export const EntradaTexto: React.FC<{
  texto: string;
  entrada?: Entrada<EfeitoTexto>;
  desde: number;
  style?: React.CSSProperties;
}> = ({ texto, entrada = { efeito: "corte", quadros: 1 }, desde, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < desde) return null;
  const p = progresso(frame, desde, entrada.quadros);
  let conteudo: React.ReactNode = texto;
  let extra: React.CSSProperties = {};

  switch (entrada.efeito) {
    case "fade":
      extra = { opacity: p };
      break;
    case "subir":
    case "descer":
      extra = { opacity: p, transform: `translateY(${(entrada.efeito === "subir" ? 50 : -50) * (1 - p)}px)` };
      break;
    case "esquerda":
    case "direita":
      extra = { opacity: p, transform: `translateX(${(entrada.efeito === "esquerda" ? -80 : 80) * (1 - p)}px)` };
      break;
    case "maquina": {
      const n = Math.ceil(texto.length * interpolate(frame, [desde, desde + entrada.quadros], [0, 1], { extrapolateRight: "clamp" }));
      // reserva o espaço do texto inteiro para não "pular" o alinhamento
      conteudo = (
        <>
          {texto.slice(0, n)}
          <span style={{ visibility: "hidden" }}>{texto.slice(n)}</span>
        </>
      );
      break;
    }
    case "palavras": {
      const palavras = texto.split(" ");
      const visiveis = Math.ceil(palavras.length * interpolate(frame, [desde, desde + entrada.quadros], [0, 1], { extrapolateRight: "clamp" }));
      conteudo = palavras.map((pl, k) => (
        <span key={k} style={{ opacity: k < Math.max(1, visiveis) ? 1 : 0 }}>
          {pl}
          {k < palavras.length - 1 ? " " : ""}
        </span>
      ));
      break;
    }
    case "pop": {
      const s = spring({ frame: frame - desde, fps, config: { damping: 10, stiffness: 260 } });
      extra = { transform: `scale(${0.8 + 0.2 * s})` };
      break;
    }
    case "desfoque":
      extra = { opacity: p, filter: `blur(${14 * (1 - p)}px)` };
      break;
    case "revelar":
      extra = { clipPath: `inset(0 ${100 * (1 - p)}% 0 0)` };
      break;
    case "espacar":
      extra = { opacity: p, letterSpacing: `${0.35 * (1 - p)}em` };
      break;
    case "corte":
      break;
  }
  return <div style={{ ...style, ...extra }}>{conteudo}</div>;
};

/** Estilo de entrada para um bloco de imagem (aplicar no contêiner). */
export const estiloEntradaImagem = (
  frame: number,
  fps: number,
  desde: number,
  entrada: Entrada<EfeitoImagem> = { efeito: "corte", quadros: 1 },
): React.CSSProperties => {
  const p = progresso(frame, desde, entrada.quadros);
  switch (entrada.efeito) {
    case "fade":
      return { opacity: p };
    case "deslizar_esq":
      return { transform: `translateX(${-140 * (1 - p)}px)`, opacity: Math.min(1, p * 2) };
    case "deslizar_dir":
      return { transform: `translateX(${140 * (1 - p)}px)`, opacity: Math.min(1, p * 2) };
    case "deslizar_cima":
      return { transform: `translateY(${110 * (1 - p)}px)`, opacity: Math.min(1, p * 2) };
    case "assentar":
      return { transform: `scale(${1.14 - 0.14 * p})`, opacity: Math.min(1, p * 3) };
    case "revelar_esq":
      return { clipPath: `inset(0 ${100 * (1 - p)}% 0 0)` };
    case "revelar_dir":
      return { clipPath: `inset(0 0 0 ${100 * (1 - p)}%)` };
    case "desfoque":
      return { filter: `blur(${18 * (1 - p)}px)`, opacity: p };
    case "pop": {
      const s = spring({ frame: frame - desde, fps, config: { damping: 14, stiffness: 220 } });
      return { transform: `scale(${0.92 + 0.08 * s})`, opacity: Math.min(1, s * 1.5) };
    }
    case "giro":
      return { transform: `rotate(${-3 * (1 - p)}deg) scale(${0.96 + 0.04 * p})`, opacity: p };
    case "clarao": // estoura em branco e assenta (impacto; guia de estilo §10.2)
      return { filter: `brightness(${1 + 5 * (1 - p) ** 2})` };
    case "corte":
      return {};
  }
};

/** Movimento de câmera dentro do quadro (Ken Burns), de 0 a 1 ao longo da cena. */
export const transformMovimento = (mov: Movimento | undefined, p: number): string => {
  if (!mov) return "none";
  const z = mov.intensidade; // ex.: 0.06 = 6% de zoom/deslocamento
  const px = 1000 * z; // deslocamento máximo em px
  switch (mov.tipo) {
    case "aproximar":
      return `scale(${1 + z * p})`;
    case "afastar":
      return `scale(${1 + z * (1 - p)})`;
    case "pan_esq":
      return `scale(${1 + z}) translateX(${px * (0.5 - p)}px)`;
    case "pan_dir":
      return `scale(${1 + z}) translateX(${px * (p - 0.5)}px)`;
    case "subir":
      return `scale(${1 + z}) translateY(${px * 0.6 * (0.5 - p)}px)`;
    case "descer":
      return `scale(${1 + z}) translateY(${px * 0.6 * (p - 0.5)}px)`;
    case "aproximar_pan":
      return `scale(${1 + z * p}) translateX(${px * 0.5 * (p - 0.5)}px)`;
    case "parado":
      return "none";
  }
};
