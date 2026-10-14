import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Credito, sombraTexto } from "../componentes/CabecalhoSecao";
import { EntradaTexto, estiloEntradaImagem, transformMovimento } from "../efeitos";
import { fonte } from "../estilo";
import type { CenaTelaCheia } from "../tipos";
import { variar } from "../tempo";

/** Arte ocupando a tela inteira, com o movimento de câmera escolhido pela direção.
 * Opcional: nome grande + subtítulo pequeno sobre a arte ("Raum" / "o demônio dos segredos"). */
export const TelaCheia: React.FC<{ cena: CenaTelaCheia; duracao: number; quadro: (palavra: number) => number }> = ({
  cena,
  duracao,
  quadro,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  const origem = `${cena.foco[0] * 100}% ${cena.foco[1] * 100}%`;
  // o nome fica do lado oposto ao rosto (foco), para não cobrir o personagem
  const nomeNaDireita = cena.foco[0] < 0.5;
  const desde = cena.rotulo_em !== undefined ? Math.max(0, quadro(cena.rotulo_em)) : 0;
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
      {cena.rotulo && (
        <div
          style={{
            position: "absolute",
            bottom: variar(cena.semente ?? "tc", 90, 170),
            [nomeNaDireita ? "right" : "left"]: 110,
            textAlign: nomeNaDireita ? "right" : "left",
            color: "#fff",
            fontFamily: fonte.rotulo,
            textShadow: sombraTexto,
          }}
        >
          <EntradaTexto
            texto={cena.rotulo}
            desde={desde}
            entrada={cena.entrada_rotulo}
            style={{ fontSize: 120, fontWeight: 700, lineHeight: 1.05 }}
          />
          {cena.subrotulo && (
            <EntradaTexto
              texto={cena.subrotulo}
              desde={desde + 8}
              entrada={cena.entrada_rotulo}
              style={{ fontSize: 52, lineHeight: 1.2 }}
            />
          )}
        </div>
      )}
      <Credito texto={cena.midia.credito} />
    </AbsoluteFill>
  );
};
