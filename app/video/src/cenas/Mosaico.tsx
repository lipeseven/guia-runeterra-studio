import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Figura } from "../componentes/Figura";
import { transformMovimento } from "../efeitos";
import type { CenaMosaico } from "../tipos";

const FORA = { esq: [-1400, 0], dir: [1400, 0], cima: [0, -900], baixo: [0, 900] } as const;

/**
 * Imagem de fundo em tela cheia sendo coberta por imagens menores que deslizam de fora para dentro,
 * cada uma no momento em que o assunto dela é falado. Layout, direções e rotações vêm da direção.
 */
export const Mosaico: React.FC<{
  cena: CenaMosaico;
  quadro: (palavra: number) => number;
  duracao: number;
}> = ({ cena, quadro, duracao }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <Figura midia={cena.fundo} largura={1920} altura={1080} style={{ transform: transformMovimento(cena.movimento, p) }} />
      {cena.pecas.map((peca, k) => {
        const inicio = Math.max(0, quadro(peca.de));
        const e = interpolate(frame, [inicio, inicio + peca.quadros], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.back(1.1)),
        });
        if (frame < inicio) return null;
        const [fx, fy] = FORA[peca.de_onde];
        const altura = (peca.largura * peca.midia.h) / peca.midia.w;
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: peca.x - peca.largura / 2,
              top: peca.y - altura / 2,
              width: peca.largura,
              height: altura,
              transform: `translate(${fx * (1 - e)}px, ${fy * (1 - e)}px) rotate(${peca.rotacao}deg)`,
              border: `${cena.borda}px solid #fff`,
              boxShadow: "0 12px 40px rgba(0,0,0,0.55)",
              overflow: "hidden",
              background: "#111",
            }}
          >
            <Figura midia={peca.midia} largura={peca.largura} altura={altura} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
