import { Composition } from "remotion";
import { Carro3D } from "../../../comum/remotion/modelos/Carro3D";
import { DURACAO_VITRINE, Vitrine } from "../../../comum/remotion/modelos/Vitrine";
import { Vertical, type PropsVertical } from "./Vertical";

export const VERTICAL_FPS = 60;

// Projeto Remotion do VERTICAL do Explicando F1. A biblioteca de modelos 3D e o kit (F1/comum/remotion) são compartilhados com o
// horizontal; o horizontal v1 tem o projeto dele em F1/horizontal/v1. Não importa nada de app/video nem de outro canal.
export const Root: React.FC = () => (
  <>
    <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition id="Modelos" component={Vitrine} durationInFrames={DURACAO_VITRINE} fps={30} width={1080} height={1920} />
    {/* vertical a 60 fps (decisão do Felipe, 2026-11-12); igual a [vertical] fps no F1/canal.toml */}
    <Composition
      id="Vertical"
      component={Vertical}
      defaultProps={{ palavras: [{ t: "", i: 0, f: 1 }], planos: [{ id: "a", i: 0, tipo: "voo_grid" }], audio: "voz.wav" } as PropsVertical}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil((props.palavras[props.palavras.length - 1].f + 0.35) * VERTICAL_FPS) })}
      durationInFrames={VERTICAL_FPS}
      fps={VERTICAL_FPS}
      width={1080}
      height={1920}
    />
  </>
);
