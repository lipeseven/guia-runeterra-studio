import { AbsoluteFill, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { estiloEntradaImagem, transformMovimento } from "../efeitos";
import type { CenaClipe } from "../tipos";

/**
 * Trecho de animação/cinemática em tela cheia. O áudio original fica mudo (a narração manda),
 * a menos que a direção peça um volume baixo. Se a cena for mais longa que a tomada,
 * a tomada é desacelerada (até 0,6x) para cobrir a fala.
 */
export const Clipe: React.FC<{ cena: CenaClipe; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const segundosCena = duracao / fps;
  const velocidade = Math.min(1, Math.max(0.6, cena.duracao_tomada / segundosCena));
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden", ...estiloEntradaImagem(frame, fps, 0, cena.entrada_img) }}>
      <OffthreadVideo
        src={staticFile(cena.arquivo)}
        playbackRate={velocidade}
        volume={cena.volume ?? 0}
        muted={!cena.volume}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: transformMovimento(cena.movimento, p) }}
      />
    </AbsoluteFill>
  );
};
