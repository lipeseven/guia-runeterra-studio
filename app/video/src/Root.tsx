import { AbsoluteFill, Audio, Composition, staticFile } from "remotion";
import { Citacao } from "./cenas/Citacao";
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

export const Root: React.FC = () => (
  <>
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
      id="YoneCitacao"
      component={CitacaoComAudio}
      durationInFrames={duracaoDoTrecho(yone, fps)}
      fps={fps}
      width={LARGURA}
      height={ALTURA}
    />
  </>
);
