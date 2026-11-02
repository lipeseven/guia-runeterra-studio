// Vitrine dos modelos da biblioteca (Remotion Studio, composição "Modelos"): 1 s por modelo, para conferir a aparência.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, useCurrentFrame } from "remotion";
import { bracos, criarAlfinete, criarEscada, criarKart, criarMapa, criarPiloto, criarPodio, esconderExtras, numeroNoCarro, obj, pontoNoMapa, topoDoPodio } from "./extras";
import { camera, montar, poe, preparar, Z_POLE, type Mundo } from "./mundo";

const VITRINE: ((w: Mundo, s: number) => void)[] = [
  (w, s) => {
    preparar(w, "claro", "estudio");
    const a = obj(w, "pil:capacete", () => criarPiloto({ equipe: "mercedes", traje: "capacete" }));
    a.position.set(-0.75, 0, 0);
    const b = obj(w, "pil:bone", () => criarPiloto({ equipe: "mercedes", traje: "bone" }));
    b.position.set(0, 0, 0);
    bracos(b, 0, 1);
    const d = obj(w, "pil:vermelho", () => criarPiloto({ traje: "bone", pele: "negra", cabelo: "preto", macacao: "#c8102e", detalhe: "#ffffff", faixa: "#ffd200", bone: "#c8102e", logo: "#ffd200" }));
    d.position.set(0.75, 0, 0);    camera(w, [Math.sin(s) * 1.2, 1.15, 5.2], [0, 0.95, 0], 36);
  },
  (w, s) => {
    preparar(w, "tarde", "pista");
    const k = obj(w, "kart", () => criarKart({ cor: "#ffd21f", numero: "1" }));
    k.position.set(0, 0, -200);
    camera(w, [2.4 * Math.cos(s), 1.2, -200 - 2.4 * Math.sin(s + 1)], [0, 0.3, -200], 36);
  },
  (w) => {
    preparar(w, "claro", "estudio");
    const p = obj(w, "podio", () => criarPodio());
    p.position.set(0, 0, 0);
    p.updateMatrixWorld();
    ([1, 2, 3] as const).forEach((n) => {
      const pi = obj(w, `pod:${n}`, () => criarPiloto({ traje: "bone", pele: n === 2 ? "negra" : "clara" }));
      pi.position.copy(topoDoPodio(p, n));
      bracos(pi, n === 1 ? 1 : 0, n === 1 ? 1 : 0.4);
    });
    camera(w, [0, 2.6, 9], [0, 1.4, 0], 36);
  },
  (w) => {
    preparar(w, "vazio", "estudio");
    obj(w, "escada", () => criarEscada(["F4", "REGIONAL", "F3", "F2", "F1"], { pulados: [2] })).position.set(0, 0, 0);
    camera(w, [2, 6, 15], [0, 2, 0], 40);
  },
  (w) => {
    preparar(w, "claro", "livre");
    const m = obj(w, "mapa:ITA", () => criarMapa("ITA"));
    m.position.set(0, 0, 0);
    m.updateMatrixWorld();
    obj(w, "pin:bolonha", () => criarAlfinete("BOLONHA")).position.copy(pontoNoMapa(m, 44.49, 11.34));
    camera(w, [0, 30, 9], [0, 0, -0.5], 40);
  },
  (w, s) => {
    preparar(w, "tarde", "pista");
    numeroNoCarro(w, 12, "12");
    poe(w, 12, 0, Z_POLE);
    camera(w, [Math.sin(2.3 + s) * 6, 2.2, Z_POLE + Math.cos(2.3 + s) * 6], [0, 0.5, Z_POLE], 34);
  },
];
// close das cabeças (boné e capacete)
VITRINE.push((w, s) => {
  VITRINE[0](w, 0);
  bracos(obj(w, "pil:bone", () => criarPiloto({ equipe: "mercedes", traje: "bone" })), 0, 0);
  const x = s < 0.5 ? 0 : -0.75;
  camera(w, [x + 0.35, 1.74, 0.95], [x, 1.66, 0], 34);
});
export const DURACAO_VITRINE = VITRINE.length * 30;

export const Vitrine: React.FC = () => {
  const ref = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const q = useCurrentFrame();
  const [alca] = useState(() => delayRender("vitrine"));
  useLayoutEffect(() => {
    const w = mundo.current ?? (mundo.current = montar(ref.current!));
    esconderExtras(w);
    VITRINE[Math.min(VITRINE.length - 1, Math.floor(q / 30))](w, (q % 30) / 30);
    w.r.render(w.cena, w.cam);
    continueRender(alca);
  });
  return (
    <AbsoluteFill style={{ background: "#0b0c11" }}>
      <canvas ref={ref} width={1080} height={1920} style={{ width: 1080, height: 1920 }} />
    </AbsoluteFill>
  );
};
