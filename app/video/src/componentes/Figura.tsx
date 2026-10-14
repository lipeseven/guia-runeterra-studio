import { Gif } from "@remotion/gif";
import { Img, staticFile } from "remotion";
import type { Midia } from "../tipos";

/**
 * Imagem OU GIF animado num retângulo de tamanho conhecido. GIF em <Img> sai congelado no render
 * (o Chrome do Remotion tira foto quadro a quadro); o <Gif> do Remotion anda junto com a linha do tempo.
 * Limitação: no GIF o "cover" é sempre centralizado (o foco não move o recorte, só a origem do zoom).
 */
export const Figura: React.FC<{
  midia: Midia;
  largura: number;
  altura: number;
  ajuste?: "cover" | "fill" | "contain";
  foco?: [number, number];
  style?: React.CSSProperties;
}> = ({ midia, largura, altura, ajuste = "cover", foco, style }) => {
  const src = staticFile(midia.arquivo);
  const pos = foco ? `${foco[0] * 100}% ${foco[1] * 100}%` : "50% 50%";
  if (midia.arquivo.toLowerCase().endsWith(".gif")) {
    return (
      <Gif
        src={src}
        width={Math.round(largura)}
        height={Math.round(altura)}
        fit={ajuste}
        loopBehavior="loop"
        style={{ display: "block", transformOrigin: pos, ...style }}
      />
    );
  }
  return (
    <Img
      src={src}
      style={{
        display: "block",
        width: largura,
        height: altura,
        maxWidth: "none",
        objectFit: ajuste,
        objectPosition: pos,
        transformOrigin: pos,
        ...style,
      }}
    />
  );
};
