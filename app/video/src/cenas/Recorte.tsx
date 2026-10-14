import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CabecalhoSecao, Legenda } from "../componentes/CabecalhoSecao";
import { estiloEntradaImagem } from "../efeitos";
import { useCores } from "../tema";
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
  const cores = useCores();
  const altura = 760;
  const largura = (cena.midia.w / cena.midia.h) * altura;
  const lado = variar(cena.semente ?? "rec", -260, 260); // não fica sempre no mesmo lugar
  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      <div
        style={{
          position: "absolute",
          height: altura,
          width: largura,
          left: (1920 - largura) / 2 + lado,
          top: 160,
          ...estiloEntradaImagem(frame, fps, 0, cena.entrada_img),
        }}
      >
        <Img src={staticFile(cena.midia.arquivo)} style={{ width: "100%", height: "100%" }} />
      </div>
      <Legenda texto={cena.legenda} desde={quadro(cena.legenda_em)} entrada={cena.entrada_legenda} />
      {secao && <CabecalhoSecao secao={secao} />}
    </AbsoluteFill>
  );
};
