// Catálogo do horizontal, fase B: 3 gráficos reais (OpenF1, SP 2026 classificação LEC v17 x ANT v22) pelo kit/graficos
// e GPS na pista pelo kit/gps. Só usa os kits/adaptadores existentes; nada do repositório é alterado.
// Render: ver render_dados.ps1 (mesma pasta).
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot } from "remotion";
import { montar, TEMAS, type Dados, type Larguras, type Spec } from "../../kit/graficos/graficos.ts";
import dadosJson from "../../kit/graficos/comparacoes/11408_16-17_12-22.json";
import largJson from "../../kit/graficos/fonte/segoe_larguras.json";
import { CamadaGrafico } from "../../remotion/graficos/CamadaGrafico";
import { ExemploGps } from "../../remotion/src/ExemploGps";

const AREA = { x: 60, y: 40, w: 1800, h: 1000 };
const SPECS: Record<string, Spec> = {
  vel: { id: "vel", tipo: "velocidade", area: AREA, em: 0, ate: 7, dur: 3.6, destaque: "auto", curvas: true, minimapa: true } as unknown as Spec,
  set: { id: "set", tipo: "setores", area: AREA, em: 0, ate: 6 } as unknown as Spec,
  dlt: { id: "dlt", tipo: "delta", area: AREA, em: 0, ate: 7, dur: 4.0, destaque: "auto", curvas: true, minimapa: true } as unknown as Spec,
};

const Grafico: React.FC<{ qual: string; fundo: boolean }> = ({ qual, fundo }) => {
  const m = useMemo(() => montar([{ tema: "claro", ...SPECS[qual] } as Spec], dadosJson as unknown as Dados, largJson as unknown as Larguras), [qual]);
  return (
    <AbsoluteFill style={{ background: fundo ? TEMAS.claro.fundo : "transparent" }}>
      <CamadaGrafico montado={m} largura={1920} altura={1080} />
    </AbsoluteFill>
  );
};

const DUR: Record<string, number> = { vel: 7, set: 6, dlt: 7 };
registerRoot(() => (
  <>
    {Object.keys(SPECS).map((k) => (
      <React.Fragment key={k}>
        <Composition id={`graf-${k}`} component={Grafico} durationInFrames={DUR[k] * 60} fps={60} width={1920} height={1080} defaultProps={{ qual: k, fundo: true }} />
        <Composition id={`graf-${k}-alfa`} component={Grafico} durationInFrames={DUR[k] * 60} fps={60} width={1920} height={1080} defaultProps={{ qual: k, fundo: false }} />
      </React.Fragment>
    ))}
    <Composition id="gps-fixa" component={ExemploGps} durationInFrames={360} fps={60} width={1920} height={1080}
      defaultProps={{ fator: 1, inicio: 2.5, camera: "fixa" as const, hud: false, rastro: 2.5 }} />
    <Composition id="gps-perseguicao" component={ExemploGps} durationInFrames={360} fps={60} width={1920} height={1080}
      defaultProps={{ fator: 2.2, inicio: 14, camera: "perseguicao" as const, hud: false }} />
  </>
));
