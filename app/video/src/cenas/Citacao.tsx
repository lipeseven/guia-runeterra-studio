import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Credito } from "../componentes/CabecalhoSecao";
import { transformMovimento } from "../efeitos";
import { cor, fonte } from "../estilo";
import type { CenaCitacao, Palavra } from "../tipos";

/**
 * Citação em serifa itálica sobre arte, com faixas escuras por linha e o autor embaixo.
 * As palavras-chave acendem em vermelho no instante em que são ditas.
 */
export const Citacao: React.FC<{
  cena: CenaCitacao;
  palavras: Palavra[];
  quadro: (palavra: number) => number;
  duracao: number;
}> = ({ cena, palavras, quadro, duracao }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  const fala = palavras.slice(cena.de, cena.ate + 1);
  const tam = Math.max(50, Math.min(96, 118 - fala.length * 2.4));
  const origem = `${cena.foco[0] * 100}% ${cena.foco[1] * 100}%`;
  const faixa: React.CSSProperties = {
    background: cor.faixaCitacao,
    padding: "2px 18px",
    borderRadius: 10,
    boxDecorationBreak: "clone",
    WebkitBoxDecorationBreak: "clone",
  };
  const caixa: React.CSSProperties =
    cena.lado === "centro"
      ? { left: 200, width: 1520, bottom: 90 }
      : cena.lado === "esq"
        ? { left: 60, width: 940, top: 200 }
        : { right: 60, width: 940, top: 200 };
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
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
      <div
        style={{
          position: "absolute",
          ...caixa,
          textAlign: "center",
          fontFamily: fonte.citacao,
          fontStyle: "italic",
          fontSize: tam,
          lineHeight: 1.22,
          color: "#fff",
        }}
      >
        <span style={faixa}>
          {"“"}
          {fala.map((w, k) => {
            const indice = cena.de + k;
            const acesa = cena.destaques.includes(indice) && frame >= quadro(indice);
            return (
              <span key={indice} style={{ color: acesa ? "#ff4a4a" : "#fff" }}>
                {w.t}
                {k < fala.length - 1 ? " " : ""}
              </span>
            );
          })}
          {"”"}
        </span>
        {cena.autor && (
          <div style={{ marginTop: 16, fontSize: Math.round(tam * 0.55) }}>
            <span style={faixa}>{cena.autor}</span>
          </div>
        )}
      </div>
      <Credito texto={cena.midia.credito} />
    </AbsoluteFill>
  );
};
