import { Composition } from "remotion";
import { ALTURA, LARGURA } from "./estilo";
import { Montagem, duracaoDoTrecho } from "./Montagem";
import type { Trecho } from "./tipos";

const fps = 60;

// Composição usada pelo diretor: a direção chega por --props (arquivo JSON gerado em projetos/<vídeo>/trabalho/).
const vazio: Trecho = { audio: "", palavras: [{ t: "", i: 0, f: 1 }], cenas: [] };

export const Root: React.FC = () => (
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
);
