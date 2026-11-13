import { Composition } from "remotion";
import { Carro3D } from "./modelos/Carro3D";
import { DURACAO_VITRINE, Vitrine } from "./modelos/Vitrine";
import { TesteEstudio } from "./TesteEstudio";
import { TestePista } from "./TestePista";
import { TesteCorrida } from "./TesteCorrida";
import { DEMO_HORIZONTAL, Horizontal, medirHorizontal } from "./horizontal/Horizontal";
import { Vertical, type PropsVertical } from "./Vertical";

export const VERTICAL_FPS = 60;

// Projeto Remotion só do Explicando F1. Não importa nada de app/video nem de outro canal.
export const Root: React.FC = () => (
  <>
    <Composition id="Carro3D" component={Carro3D} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition id="Modelos" component={Vitrine} durationInFrames={DURACAO_VITRINE} fps={30} width={1080} height={1920} />
    <Composition id="TesteEstudio" component={TesteEstudio} durationInFrames={240} fps={30} width={1920} height={1080}
      defaultProps={{ arquivo: "ferrari_sf26.glb", palavra: "FERRARI", cor: "#f2c230", nota: "mais branco que nos últimos anos" }} />
    <Composition id="TestePista" component={TestePista} durationInFrames={1} fps={30} width={2000} height={2000}
      defaultProps={{ arquivo: "interlagos_sao_paulo.glb", grupo: "tracksplit_0" }} />
    <Composition id="TesteCorrida" component={TesteCorrida} durationInFrames={240} fps={30} width={1920} height={1080}
      defaultProps={{ pista: "interlagos_sao_paulo.glb", carro: "ferrari_sf26.glb", fundo: "#dcd9d2", destaque: "#f2c230" }} />
    <Composition id="Horizontal" component={Horizontal} durationInFrames={1500} fps={30} width={1920} height={1080}
      defaultProps={DEMO_HORIZONTAL} calculateMetadata={medirHorizontal} />
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
