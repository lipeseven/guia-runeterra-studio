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
    {/* 2ª pista (fase 2b): Monza 2025, classificação (9908), LEC x HAM, pista plana traçada pelo GPS (sem modelo 3D) */}
    <Composition id="ExemploGpsMonza" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 1, inicio: 7.5, camera: "fixa" as const, conjunto: "monza" as const }} />
    <Composition id="ExemploGpsMonzaPerseguicao" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 2.2, inicio: 14, camera: "perseguicao" as const, conjunto: "monza" as const }} />
    <Composition id="ExemploGpsFolhaMonza" component={ExemploGps} durationInFrames={240} fps={60} width={1280} height={720}
      defaultProps={{ fator: 1, inicio: 8, camera: "fixa" as const, rastro: 0, hud: false, distancia: 0.3, nCarros: 1, conjunto: "monza" as const }} />
  </>
);
