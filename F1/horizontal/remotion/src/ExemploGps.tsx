// Exemplo mínimo do kit/gps no Remotion: a cena é a mesma do HyperFrames (kit/gps/exemplo/cena_exemplo.js);
// aqui só se cria o canvas, carregam-se os .glb (public/, ver preparar.mjs) e desenha-se o quadro atual.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { montarCena } from "../../kit/gps/exemplo/cena_exemplo.js";
import lec from "../../kit/gps/voltas/11412_16_51.json";
import ant from "../../kit/gps/voltas/11412_12_55.json";
import lecMonza from "../../kit/gps/voltas/9908_16_16.json";
import hamMonza from "../../kit/gps/voltas/9908_44_16.json";
import monzaPlana from "../../kit/gps/pista/Monza_plana.json";

// Conjuntos de exemplo (2ª pista da fase 2b: Monza 2025, classificação, SEM modelo 3D -> pista plana pelo GPS).
const CONJUNTOS = {
  interlagos: { voltas: [lec, ant], glb: "interlagos_sao_paulo.glb", plana: null },
  monza: { voltas: [lecMonza, hamMonza], glb: null, plana: monzaPlana },
} as const;

type Props = {
  fator: number; inicio: number; camera: "fixa" | "perseguicao"; rastro?: number; hud?: boolean; distancia?: number;
  nCarros?: number; conjunto?: keyof typeof CONJUNTOS;
};
type Hud = { sigla: string; cor: string; kmh: number; t: number }[];

// modelo do carro por equipe; equipe sem modelo usa o da Ferrari (o carro é ilustrativo, o movimento é o do GPS)
const CARRO: Record<string, string> = { Ferrari: "ferrari_sf26.glb", Mercedes: "2026_mercedes_w17.glb" };

export const ExemploGps: React.FC<Props> = ({ fator, inicio, camera, rastro = 2.5, hud: mostrarHud = true, distancia = 0.5, nCarros = 2, conjunto = "interlagos" }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const tela = useRef<HTMLCanvasElement>(null);
  const cena = useRef<{ desenhar: (t: number) => Hud } | null>(null);
  const [espera] = useState(() => delayRender("carregando pista e carros"));
  const [pronto, setPronto] = useState(false);
  const [hud, setHud] = useState<Hud>([]);

  useEffect(() => {
    const ld = new GLTFLoader();
    const cj = CONJUNTOS[conjunto];
    const voltas = cj.voltas.slice(0, nCarros);
    Promise.all([
      cj.glb ? ld.loadAsync(staticFile(cj.glb)) : Promise.resolve(null),
      ...voltas.map((v) => ld.loadAsync(staticFile(CARRO[v.equipe] ?? CARRO.Ferrari))),
    ]).then(([pista, ...carros]) => {
      cena.current = montarCena(THREE, {
        canvas: tela.current!, largura: width, altura: height, pista: pista?.scene, pistaPlana: cj.plana,
        carros: carros.map((c, i) => ({ cena: c.scene, volta: voltas[i] })), fator, inicio, camera, rastro, distancia,
      });
      setPronto(true);
      continueRender(espera);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    if (pronto && cena.current) setHud(cena.current.desenhar(frame / fps));
  }, [frame, fps, pronto]);

  return (
    <AbsoluteFill style={{ background: "#e9e9e6" }}>
      <canvas ref={tela} width={width} height={height} style={{ width, height }} />
      {mostrarHud && <div style={{ position: "absolute", left: 24, top: 20, fontFamily: "Segoe UI, sans-serif", fontSize: 22, color: "#151515" }}>
        <b>REMOTION</b> · kit/gps · GPS OpenF1 · {fator === 1 ? "tempo real" : `acelerado ${String(fator).replace(".", ",")}x`} · quadro {frame}
        {hud.map((h) => (
          <div key={h.sigla} style={{ marginTop: 6 }}>
            <span style={{ display: "inline-block", width: 14, height: 14, background: h.cor, marginRight: 8 }} />
            {h.sigla} {h.kmh} km/h · t volta {h.t.toFixed(2)} s
          </div>
        ))}
      </div>}
    </AbsoluteFill>
  );
};
