import { Composition } from "remotion";
import { TesteEstudio } from "./TesteEstudio";
import { TestePista } from "./TestePista";
import { TesteCorrida } from "./TesteCorrida";
import { DEMO_HORIZONTAL, Horizontal, medirHorizontal } from "./Horizontal";

// Projeto Remotion do HORIZONTAL v1 do Explicando F1 (vocabulário fixo de cenas). Usa a biblioteca compartilhada em F1/comum/remotion.
export const Root: React.FC = () => (
  <>
    <Composition id="TesteEstudio" component={TesteEstudio} durationInFrames={240} fps={30} width={1920} height={1080}
      defaultProps={{ arquivo: "ferrari_sf26.glb", palavra: "FERRARI", cor: "#f2c230", nota: "mais branco que nos últimos anos" }} />
    <Composition id="TestePista" component={TestePista} durationInFrames={1} fps={30} width={2000} height={2000}
      defaultProps={{ arquivo: "interlagos_sao_paulo.glb", grupo: "tracksplit_0" }} />
    <Composition id="TesteCorrida" component={TesteCorrida} durationInFrames={240} fps={30} width={1920} height={1080}
      defaultProps={{ pista: "interlagos_sao_paulo.glb", carro: "ferrari_sf26.glb", fundo: "#dcd9d2", destaque: "#f2c230" }} />
    <Composition id="Horizontal" component={Horizontal} durationInFrames={1500} fps={30} width={1920} height={1080}
      defaultProps={DEMO_HORIZONTAL} calculateMetadata={medirHorizontal} />
  </>
);
