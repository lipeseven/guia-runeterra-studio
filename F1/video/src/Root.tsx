import { Composition } from "remotion";
import { Carro3D } from "./Carro3D";
import { CenaSC } from "./CenaSC";

// Projeto Remotion só do Explicando F1. Não importa nada de app/video nem de outro canal.
export const Root: React.FC = () => (
  <>
    <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition
      id="CenaSC"
      component={CenaSC}
      defaultProps={{ palavras: [{ t: "", i: 0, f: 1 }] }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil((props.palavras[props.palavras.length - 1].f + 0.6) * 30) })}
      durationInFrames={30}
      fps={30}
      width={1080}
      height={1920}
    />
  </>
);
