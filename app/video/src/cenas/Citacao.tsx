import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { cor, fonte } from "../estilo";
import type { Midia, Palavra } from "../tipos";

/** Citação em serifa itálica sobre arte, com faixas escuras por linha (estilo do canal). */
export const Citacao: React.FC<{
  palavras: Palavra[];
  autor: string;
  fundo: Midia;
  foco: [number, number];
  destaques: number[];
}> = ({ palavras, autor, fundo, foco, destaques }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.08]);
  const faixa: React.CSSProperties = {
    background: cor.faixaCitacao,
    padding: "2px 18px",
    borderRadius: 10,
    boxDecorationBreak: "clone",
    WebkitBoxDecorationBreak: "clone",
  };
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <Img
        src={staticFile(fundo.arquivo)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: `${foco[0] * 100}% ${foco[1] * 100}%`,
          transform: `scale(${zoom})`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 50,
          top: 230,
          width: 900,
          textAlign: "center",
          fontFamily: fonte.citacao,
          fontStyle: "italic",
          fontSize: 104,
          lineHeight: 1.22,
          color: "#fff",
        }}
      >
        <span style={faixa}>
          "
          {palavras.map((p, k) => {
            const acesa = destaques.includes(k) && frame >= Math.round(p.i * fps);
            return (
              <span key={k} style={{ color: acesa ? "#ff4a4a" : "#fff" }}>
                {p.t}
                {k < palavras.length - 1 ? " " : ""}
              </span>
            );
          })}
          "
        </span>
        <div style={{ marginTop: 18, fontSize: 84 }}>
          <span style={faixa}>{autor}</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
