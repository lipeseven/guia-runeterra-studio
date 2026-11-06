import { Composition } from "remotion";
import { Carro3D } from "./modelos/Carro3D";
import { DURACAO_VITRINE, Vitrine } from "./modelos/Vitrine";
import { TesteEstudio } from "./TesteEstudio";
import { Vertical, type PropsVertical } from "./Vertical";

// Projeto Remotion só do Explicando F1. Não importa nada de app/video nem de outro canal.
export const Root: React.FC = () => (
  <>
    <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition id="Modelos" component={Vitrine} durationInFrames={DURACAO_VITRINE} fps={30} width={1080} height={1920} />
    <Composition id="TesteEstudio" component={TesteEstudio} durationInFrames={240} fps={30} width={1920} height={1080}
      defaultProps={{ arquivo: "ferrari_sf26.glb", palavra: "FERRARI", cor: "#f2c230", nota: "mais branco que nos últimos anos" }} />
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
  </>
);
