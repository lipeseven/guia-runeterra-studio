import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { estiloEntradaImagem, transformMovimento } from "../efeitos";
import type { CenaTelaCheia } from "../tipos";

/** Arte ocupando a tela inteira, com o movimento de câmera escolhido pela direção. */
export const TelaCheia: React.FC<{ cena: CenaTelaCheia; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  const origem = `${cena.foco[0] * 100}% ${cena.foco[1] * 100}%`;
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden", ...estiloEntradaImagem(frame, fps, 0, cena.entrada_img) }}>
      <Img
        src={staticFile(cena.midia.arquivo)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: origem,
          transformOrigin: origem,
          transform: transformMovimento(cena.movimento, p),
        }}
      />
    </AbsoluteFill>
  );
};
