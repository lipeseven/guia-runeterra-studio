import { Composition } from "remotion";
import { ALTURA, LARGURA } from "./estilo";
import { Montagem, duracaoDoTrecho } from "./Montagem";
import type { Trecho } from "./tipos";
import { FreioF1 } from "./vertical/FreioF1";

const fps = 60;

// Composição usada pelo diretor: a direção chega por --props (arquivo JSON gerado em projetos/<vídeo>/trabalho/).
const vazio: Trecho = { audio: "", palavras: [{ t: "", i: 0, f: 1 }], cenas: [] };

const QUADROS_VERTICAIS = (palavras: { f: number }[]) => Math.ceil((palavras[palavras.length - 1].f + 0.5) * 30);

export const Root: React.FC = () => (
  <>
  <Composition
    id="FreioF1"
    component={FreioF1}
    defaultProps={{ palavras: [{ t: "", i: 0, f: 1 }] }}
    calculateMetadata={({ props }) => ({ durationInFrames: QUADROS_VERTICAIS(props.palavras) })}
    durationInFrames={30}
    fps={30}
    width={1080}
    height={1920}
  />
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
  </>
);
