import { Composition } from "remotion";
import { Carro3D } from "./Carro3D";
import { CenaSC } from "./CenaSC";
import { DURACAO_PILOTO, Piloto } from "./Piloto";
import { Vertical, type PropsVertical } from "./Vertical";

// Projeto Remotion só do Explicando F1. Não importa nada de app/video nem de outro canal.
export const Root: React.FC = () => (
  <>
    <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition id="Piloto" component={Piloto} durationInFrames={DURACAO_PILOTO} fps={30} width={1080} height={1920} />
    <Composition
      id="Vertical"
      component={Vertical}
      defaultProps={{ palavras: [{ t: "", i: 0, f: 1 }], planos: [{ id: "a", i: 0, tipo: "voo_grid" }], audio: "voz.wav" } as PropsVertical}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil((props.palavras[props.palavras.length - 1].f + 0.35) * 30) })}
      durationInFrames={30}
      fps={30}
      width={1080}
      height={1920}
    />
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
