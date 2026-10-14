import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Figura } from "../componentes/Figura";
import { Credito } from "../componentes/CabecalhoSecao";
import { EntradaTexto, estiloEntradaImagem, transformMovimento } from "../efeitos";
import { fonte } from "../estilo";
import { useCores } from "../tema";
import type { CenaMeio } from "../tipos";

/** Meio a meio (guia de estilo §10.2): arte em metade da tela + frase curta na outra metade. */
export const Meio: React.FC<{ cena: CenaMeio; quadro: (palavra: number) => number; duracao: number }> = ({
  cena,
  quadro,
  duracao,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cores = useCores();
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  const imgEsq = cena.lado === "esq";
  const tam = cena.texto.length > 40 ? 76 : cena.texto.length > 22 ? 92 : 112;
  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: imgEsq ? 0 : 960,
          width: 960,
          height: 1080,
          overflow: "hidden",
          ...estiloEntradaImagem(frame, fps, 0, cena.entrada_img),
        }}
      >
        <Figura
          midia={cena.midia}
          largura={960}
          altura={1080}
          foco={cena.foco}
          style={{ transform: transformMovimento(cena.movimento, p) }}
        />
        <Credito texto={cena.midia.credito} direita={16} baixo={10} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: imgEsq ? 960 : 0,
          width: 960,
          height: 1080,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 90px",
        }}
      >
        <EntradaTexto
          texto={cena.texto}
          desde={Math.max(0, quadro(cena.texto_em))}
          entrada={cena.entrada_texto}
          style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: tam, lineHeight: 1.2, color: cores.texto, textAlign: "center" }}
        />
      </div>
    </AbsoluteFill>
  );
};
