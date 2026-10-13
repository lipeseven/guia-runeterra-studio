import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CabecalhoSecao, Legenda } from "../componentes/CabecalhoSecao";
import { cor } from "../estilo";
import type { CenaRecorte, Secao } from "../tipos";
import { variar } from "../tempo";

/** Personagem recortado sobre o fundo branco; a legenda entra quando a palavra é falada. */
export const Recorte: React.FC<{
  cena: CenaRecorte;
  secao?: Secao;
  quadro: (palavra: number) => number;
}> = ({ cena, secao, quadro }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame, fps, config: { damping: 15, stiffness: 160 } });
  const quandoLegenda = quadro(cena.legenda_em);
  const pop = spring({ frame: frame - quandoLegenda, fps, config: { damping: 10, stiffness: 260 } });
  const altura = 760;
  const largura = (cena.midia.w / cena.midia.h) * altura;
  const lado = variar(cena.semente ?? "rec", -260, 260); // não fica sempre no mesmo lugar
  return (
    <AbsoluteFill style={{ background: cor.fundo }}>
      <Img
        src={staticFile(cena.midia.arquivo)}
        style={{
          position: "absolute",
          height: altura,
          width: largura,
          left: (1920 - largura) / 2 + lado,
          top: 160 + (1 - entrada) * 80,
          opacity: entrada,
        }}
      />
      {frame >= quandoLegenda && <Legenda texto={cena.legenda} escala={0.8 + 0.2 * pop} />}
      {secao && <CabecalhoSecao secao={secao} />}
    </AbsoluteFill>
  );
};
