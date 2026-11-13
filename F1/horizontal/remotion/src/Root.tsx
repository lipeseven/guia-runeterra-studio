import { Composition } from "remotion";
import { ExemploGps } from "./ExemploGps";

// 60 q/s em tudo (decisão do Felipe). Exemplo curto do kit/gps.
export const Root: React.FC = () => (
  <>
    <Composition id="ExemploGps" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 1, inicio: 2.5, camera: "fixa" as const }} />
    <Composition id="ExemploGpsPerseguicao" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 2.2, inicio: 14, camera: "perseguicao" as const }} />
    <Composition id="ExemploGpsFolha" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 1, inicio: 4.5, camera: "fixa" as const, rastro: 0, hud: false, distancia: 0.3, nCarros: 1 }} />
  </>
);
