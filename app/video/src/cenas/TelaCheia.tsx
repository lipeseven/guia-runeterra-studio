import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import type { CenaTelaCheia } from "../tipos";
import { variar } from "../tempo";

/** Arte ocupando a tela inteira com Ken Burns (zoom + leve deslocamento). */
export const TelaCheia: React.FC<{ cena: CenaTelaCheia; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duracao], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  const zoom = cena.zoom[0] + (cena.zoom[1] - cena.zoom[0]) * p;
  const deriva = variar(cena.semente ?? "tc", -1, 1) * 30 * p;
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <Img
        src={staticFile(cena.midia.arquivo)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: `${cena.foco[0] * 100}% ${cena.foco[1] * 100}%`,
          transformOrigin: `${cena.foco[0] * 100}% ${cena.foco[1] * 100}%`,
          transform: `translateX(${deriva}px) scale(${zoom})`,
        }}
      />
    </AbsoluteFill>
  );
};
