import { AbsoluteFill, Audio, Composition, staticFile } from "remotion";
import { Citacao } from "./cenas/Citacao";
import { Mostruario, POR_EFEITO, totalMostruario } from "./cenas/Mostruario";
import fiddle from "./dados/fiddle.json";
import dados from "./dados/prototipo.json";
import { ALTURA, LARGURA } from "./estilo";
import { Montagem, duracaoDoTrecho } from "./Montagem";
import type { Trecho } from "./tipos";

const fps = dados.fps;
const abertura = dados.abertura as unknown as Trecho;
const yone = dados.yone as unknown as Trecho;
const citacao = dados.yone.citacao as {
  autor: string;
  fundo: { arquivo: string; w: number; h: number };
  foco: [number, number];
  destaques: number[];
};

const CitacaoComAudio: React.FC = () => (
  <AbsoluteFill>
    <Citacao palavras={yone.palavras} {...citacao} />
    <Audio src={staticFile(yone.audio)} />
  </AbsoluteFill>
);

// Demo da ressincronização: mesma direção, dois áudios (tools/prototipo/fiddlesticks.py).
const fiddleGuia = fiddle.guia as unknown as Trecho;
const fiddleReal = fiddle.real as unknown as Trecho;

// Composição genérica usada pelo diretor: a direção chega por --props (arquivo JSON).
const vazio: Trecho = { audio: "", palavras: [{ t: "", i: 0, f: 1 }], cenas: [] };

export const Root: React.FC = () => (
  <>
    <Composition
      id="Video"
      component={Montagem}
      defaultProps={{ trecho: vazio }}
      calculateMetadata={({ props }) => ({ durationInFrames: duracaoDoTrecho(props.trecho, fps) })}
      durationInFrames={60}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="FiddleGuia"
      component={Montagem}
      defaultProps={{ trecho: fiddleGuia }}
      durationInFrames={duracaoDoTrecho(fiddleGuia, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="FiddleReal"
      component={Montagem}
      defaultProps={{ trecho: fiddleReal }}
      durationInFrames={duracaoDoTrecho(fiddleReal, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="Abertura"
      component={Montagem}
      defaultProps={{ trecho: abertura }}
      durationInFrames={duracaoDoTrecho(abertura, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="YoneDialogo"
      component={Montagem}
      defaultProps={{ trecho: yone }}
      durationInFrames={duracaoDoTrecho(yone, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="Mostruario"
      component={Mostruario}
      defaultProps={dados.mostruario}
      durationInFrames={totalMostruario * POR_EFEITO}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
    <Composition
      id="YoneCitacao"
      component={CitacaoComAudio}
      durationInFrames={duracaoDoTrecho(yone, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
  </>
);
