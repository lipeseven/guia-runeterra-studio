import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { Capa } from "./cenas/Capa";
import { Cartao } from "./cenas/Cartao";
import { Citacao } from "./cenas/Citacao";
import { Clipe } from "./cenas/Clipe";
import { Dialogo } from "./cenas/Dialogo";
import { Dividida } from "./cenas/Dividida";
import { Hub } from "./cenas/Hub";
import { Lista } from "./cenas/Lista";
import { Meio } from "./cenas/Meio";
import { Mosaico } from "./cenas/Mosaico";
import { Recorte } from "./cenas/Recorte";
import { TelaCheia } from "./cenas/TelaCheia";
import { Texto } from "./cenas/Texto";
import { CORES, TemaCtx } from "./tema";
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
  const tema = trecho.tema ?? "claro";
  const inicio = (k: number) =>
    k === 0 ? 0 : Math.max(0, quadroDaPalavra(palavras, cenas[k].de, fps) - folgaDeCorte(`${k}`));

  return (
    <TemaCtx.Provider value={tema}>
      <AbsoluteFill style={{ background: CORES[tema].fundo }}>
        {cenas.map((cena, k) => {
          const de = inicio(k);
          const ate = k + 1 < cenas.length ? inicio(k + 1) : durationInFrames;
          const quadro = (palavra: number) => quadroDaPalavra(palavras, palavra, fps) - de;
          return (
            <Sequence key={k} from={de} durationInFrames={Math.max(1, ate - de)} name={`${k + 1}. ${cena.tipo}`}>
              <CenaPorTipo cena={cena} trecho={trecho} quadro={quadro} duracao={ate - de} secao={cena.secao ?? secao} />
            </Sequence>
          );
        })}
        <Audio src={staticFile(trecho.audio)} />
        {(trecho.sons ?? []).map((s, k) => (
          // o efeito bate 2 quadros antes da palavra (ataque do som + percepção)
          <Sequence key={`som${k}`} from={Math.max(0, quadroDaPalavra(palavras, s.de, fps) - 2)} name={`som ${s.categoria ?? ""}`}>
            <Audio src={staticFile(s.arquivo)} volume={s.volume} />
          </Sequence>
        ))}
      </AbsoluteFill>
    </TemaCtx.Provider>
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
    case "hub":
      return <Hub cena={cena} duracao={duracao} />;
    case "cartao":
      return <Cartao cena={cena} secao={secao} quadro={quadro} duracao={duracao} />;
    case "telacheia":
      return <TelaCheia cena={cena} duracao={duracao} quadro={quadro} />;
    case "recorte":
      return <Recorte cena={cena} secao={secao} quadro={quadro} />;
    case "dialogo":
      return <Dialogo cena={cena} palavras={trecho.palavras} quadro={quadro} />;
    case "clipe":
      return <Clipe cena={cena} duracao={duracao} />;
    case "mosaico":
      return <Mosaico cena={cena} quadro={quadro} duracao={duracao} />;
    case "dividida":
      return <Dividida cena={cena} quadro={quadro} duracao={duracao} />;
    case "lista":
      return <Lista cena={cena} secao={secao} quadro={quadro} />;
    case "meio":
      return <Meio cena={cena} quadro={quadro} duracao={duracao} />;
    case "texto":
      return <Texto cena={cena} duracao={duracao} />;
    case "citacao":
      return <Citacao cena={cena} palavras={trecho.palavras} quadro={quadro} duracao={duracao} />;
  }
};
