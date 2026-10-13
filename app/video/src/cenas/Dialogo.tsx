import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Icone } from "../componentes/Icone";
import { cor, fonte } from "../estilo";
import type { CenaDialogo, Palavra } from "../tipos";

/** Dois retratos e a fala embaixo; palavras-chave ficam vermelhas no instante em que são ditas. */
export const Dialogo: React.FC<{
  cena: CenaDialogo;
  palavras: Palavra[];
  quadro: (palavra: number) => number;
}> = ({ cena, palavras, quadro }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fala = palavras.slice(cena.de, cena.ate + 1);
  const entrada = (atraso: number) => spring({ frame: frame - atraso, fps, config: { damping: 13, stiffness: 200 } });
  return (
    <AbsoluteFill style={{ background: cor.fundo }}>
      {[cena.esquerda, cena.direita].map((ic, k) => (
        <div
          key={ic.nome}
          style={{ position: "absolute", top: 150, left: k === 0 ? 470 : 1150, transform: `scale(${entrada(k * 4)})` }}
        >
          <Icone icone={ic} tamanho={300} />
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          top: 600,
          left: 160,
          width: 1600,
          textAlign: "center",
          fontFamily: fonte.rotulo,
          fontSize: 70,
          lineHeight: 1.35,
          color: cor.texto,
        }}
      >
        {"“"}
        {fala.map((p, k) => {
          const indice = cena.de + k;
          const destacada = cena.destaques.includes(indice);
          const q = quadro(indice);
          const acesa = destacada ? interpolate(frame, [q, q + 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
          return (
            <span
              key={indice}
              style={{
                color: acesa > 0.5 ? cor.destaque : cor.texto,
                display: "inline-block",
                transform: `scale(${1 + 0.08 * acesa * (1 - interpolate(frame, [q + 4, q + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))})`,
              }}
            >
              {p.t}
              {k < fala.length - 1 ? " " : ""}
            </span>
          );
        })}
        {"”"}
      </div>
    </AbsoluteFill>
  );
};
