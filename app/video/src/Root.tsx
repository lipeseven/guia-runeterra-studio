import { Composition } from "remotion";
import { ALTURA, LARGURA } from "./estilo";
import { Montagem, duracaoDoTrecho } from "./Montagem";
import type { Trecho } from "./tipos";
import { Carro3D } from "./vertical/Carro3D";
import { TesteRegras } from "./vertical/TesteRegras";

const fps = 60;

// Composição usada pelo diretor: a direção chega por --props (arquivo JSON gerado em projetos/<vídeo>/trabalho/).
const vazio: Trecho = { audio: "", palavras: [{ t: "", i: 0, f: 1 }], cenas: [] };

export const Root: React.FC = () => (
  <>
  <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
  <Composition
    id="TesteRegras"
    component={TesteRegras}
    defaultProps={{ palavras: [{ t: "", i: 0, f: 1 }] }}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil((props.palavras[props.palavras.length - 1].f + 0.6) * 30) })}
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
