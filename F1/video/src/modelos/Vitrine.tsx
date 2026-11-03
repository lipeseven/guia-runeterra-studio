// Vitrine dos modelos da biblioteca (Remotion Studio, composição "Modelos"): 1 s por modelo, para conferir a aparência.
import { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, useCurrentFrame } from "remotion";
import { bracos, criarAlfinete, criarEscada, criarKart, criarMapa, criarPiloto, criarPodio, esconderExtras, numeroNoCarro, obj, pontoNoMapa, topoDoPodio } from "./extras";
import { camera, enquadrar, montar, poe, preparar, Z_POLE, type Mundo } from "./mundo";
import { trocarComposto } from "./Carro3D";
import { cortar, explodir, isolar, raioX, restaurar } from "./desmonte";
import { apertar, criarVolante, girar, luzesDeTroca, puxar, telaDoVolante } from "./volante";

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
    enquadrar(w, k, [Math.cos(s), 0.45, -Math.sin(s + 1)], 1.15);
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
    const e = obj(w, "escada", () => criarEscada(["F4", "REGIONAL", "F3", "F2", "F1"], { pulados: [2] }));
    e.position.set(0, 0, 0);
    enquadrar(w, e, [0.35, 0.3, 1], 1.15);
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
// carro de cima, de lado, de trás e em 3/4 (para comparar com desenhos de referência)
const VISTAS: [number, number, number, number][] = [[0, 14, 0.01, 26], [22, 0.6, 0, 30], [0, 1, 12, 22], [6, 2.4, -7, 34]];
VISTAS.forEach(([x, y, z, lente]) =>
  VITRINE.push((w) => {
    preparar(w, "claro", "estudio");
    numeroNoCarro(w, 12, "12");
    poe(w, 12, 0, 0);
    camera(w, [x, y, z], [0, 0.45, 0], lente, 0, y > 10);
  }),
);
// close das rodas: um carro em cada composto
VITRINE.push((w, s) => {
  preparar(w, "claro", "estudio");
  ["macio", "medio", "duro"].forEach((c, i) => {
    trocarComposto(w.carros[i * 2], c);
    poe(w, i * 2, 0, -i * 6.5);
  });
  const z = -Math.min(2, Math.floor(s * 3)) * 6.5;
  camera(w, [2.3, 0.55, z - 0.7], [0.8, 0.36, z - 1.55], 34);
});
// desmonte do carro: explodir, isolar a roda, raio-X da tampa, corte ao meio
VITRINE.push((w, s) => {
  preparar(w, "claro", "estudio");
  poe(w, 12, 0, 0);
  const car = w.carros[12];
  const f = Math.floor(s * 4);
  if (f === 0) explodir(car, 1);
  if (f === 1) isolar(car, "roda_dianteira_esquerda");
  if (f === 2) raioX(car, ["tampa_do_motor", "sidepod_esquerda", "sidepod_direita"]);
  if (f === 3) cortar(car, [1, 0, 0]);
  enquadrar(w, car, [0.75, 0.55, -0.9], f === 0 ? 1.05 : 1.15);
});
// volante: frente com comandos acionados, 3/4 de trás (paddles), explodido e close dos seletores
VITRINE.push((w, s) => {
  preparar(w, "claro", "estudio");
  const v = obj(w, "volante", () => criarVolante());
  v.position.set(0, 1, 0);
  const f = Math.floor(s * 4);
  if (f === 0) {
    apertar(v, "ot");
    luzesDeTroca(v, 0.7);
    telaDoVolante(v, { marcha: "7", modo: "OT", delta: "-0.214", velocidade: 318 });
    enquadrar(w, v, [0, 0.08, 1], 1.08, 30);
  } else if (f === 1) {
    puxar(v, "marcha_direita");
    enquadrar(w, v, [0.7, 0.25, -1], 1.08, 30);
  } else if (f === 2) {
    explodir(v, 1);
    enquadrar(w, v, [0.85, 0.3, 1], 1.05, 30);
  } else {
    girar(v, "central", 7);
    camera(w, [0.04, 0.96, 0.16], [0, 0.955, 0], 30);
  }
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
    restaurar();
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
