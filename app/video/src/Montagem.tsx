import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { Cartao } from "./cenas/Cartao";
import { Clipe } from "./cenas/Clipe";
import { Mosaico } from "./cenas/Mosaico";
import { Dialogo } from "./cenas/Dialogo";
import { Capa } from "./cenas/Capa";
import { Recorte } from "./cenas/Recorte";
import { TelaCheia } from "./cenas/TelaCheia";
import { folgaDeCorte, quadroDaPalavra } from "./tempo";
import type { Cena, Trecho } from "./tipos";

/** Duração da composição: até o fim da última palavra + meio segundo. */
export const duracaoDoTrecho = (trecho: Trecho, fps: number) =>
  Math.ceil((trecho.palavras[trecho.palavras.length - 1].f + 0.5) * fps);

/**
 * Converte a direção (ancorada em palavras) em sequências no tempo.
 * Cada cena começa na sua palavra inicial (com folga humana) e termina onde a próxima começa.
 */
export const Montagem: React.FC<{ trecho: Trecho }> = ({ trecho }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const { palavras, cenas, secao } = trecho;
  const inicio = (k: number) =>
    k === 0 ? 0 : Math.max(0, quadroDaPalavra(palavras, cenas[k].de, fps) - folgaDeCorte(`${k}`));

  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {cenas.map((cena, k) => {
        const de = inicio(k);
        const ate = k + 1 < cenas.length ? inicio(k + 1) : durationInFrames;
        const quadro = (palavra: number) => quadroDaPalavra(palavras, palavra, fps) - de;
        return (
          <Sequence key={k} from={de} durationInFrames={Math.max(1, ate - de)} name={`${k + 1}. ${cena.tipo}`}>
            <CenaPorTipo cena={cena} trecho={trecho} quadro={quadro} duracao={ate - de} secao={secao} />
          </Sequence>
        );
      })}
      <Audio src={staticFile(trecho.audio)} />
    </AbsoluteFill>
  );
};

const CenaPorTipo: React.FC<{
  cena: Cena;
  trecho: Trecho;
  quadro: (palavra: number) => number;
  duracao: number;
  secao: Trecho["secao"];
}> = ({ cena, trecho, quadro, duracao, secao }) => {
  switch (cena.tipo) {
    case "capa":
      return <Capa cena={cena} duracao={duracao} />;
    case "cartao":
      return <Cartao cena={cena} secao={secao} quadro={quadro} duracao={duracao} />;
    case "telacheia":
      return <TelaCheia cena={cena} duracao={duracao} />;
    case "recorte":
      return <Recorte cena={cena} secao={secao} quadro={quadro} />;
    case "dialogo":
      return <Dialogo cena={cena} palavras={trecho.palavras} quadro={quadro} />;
    case "clipe":
      return <Clipe cena={cena} duracao={duracao} />;
    case "mosaico":
      return <Mosaico cena={cena} quadro={quadro} duracao={duracao} />;
  }
};
