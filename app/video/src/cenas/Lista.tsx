import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Figura } from "../componentes/Figura";
import { CabecalhoSecao } from "../componentes/CabecalhoSecao";
import { estiloEntradaImagem } from "../efeitos";
import { fonte } from "../estilo";
import { useCores } from "../tema";
import { variar } from "../tempo";
import type { CenaLista, Secao } from "../tipos";

/**
 * Lista acumulada (guia de estilo §10.2): painéis com legenda entrando lado a lado conforme a narração
 * enumera ("nervos cutucados" → "membros arrancados" → "remédio de teste"). A fileira cresce.
 */
export const Lista: React.FC<{ cena: CenaLista; secao?: Secao; quadro: (palavra: number) => number }> = ({
  cena,
  secao,
  quadro,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cores = useCores();
  const n = cena.pecas.length;
  const gap = 56;
  const larg = Math.min(560, (1780 - gap * (n - 1)) / n);
  const alt = larg * 0.78;
  // a fileira fica centralizada enquanto cresce: desliza suavemente a cada item novo
  const inicios = cena.pecas.map((p, k) => (k === 0 ? 0 : Math.max(0, quadro(p.de))));
  const centro = (v: number) => (1920 - (v * larg + (v - 1) * gap)) / 2;
  let x0 = centro(1);
  inicios.forEach((q, k) => {
    if (k > 0 && frame >= q) x0 = interpolate(frame, [q, q + 14], [centro(k), centro(k + 1)], { extrapolateRight: "clamp" });
  });
  const topo = secao ? 330 : 280;
  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      {cena.pecas.map((peca, k) => {
        const inicio = inicios[k];
        if (frame < inicio) return null;
        const foco = peca.foco ?? [0.5, 0.4];
        const giro = cena.inclinado ? variar(`${cena.semente}-${k}`, -3, 3) : 0;
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: x0 + k * (larg + gap),
              top: topo + (cena.inclinado ? variar(`${cena.semente}-y${k}`, -18, 18) : 0),
              width: larg,
              ...estiloEntradaImagem(frame, fps, inicio, cena.entrada),
            }}
          >
            <div style={{ width: larg, height: alt, overflow: "hidden", transform: `rotate(${giro}deg)`, background: "#222" }}>
              <Figura midia={peca.midia} largura={larg} altura={alt} foco={foco} />
            </div>
            {peca.rotulo && (
              <div
                style={{
                  marginTop: 22,
                  textAlign: "center",
                  fontFamily: fonte.rotulo,
                  fontWeight: 700,
                  fontSize: n >= 4 ? 46 : 58,
                  lineHeight: 1.15,
                  color: cores.texto,
                }}
              >
                {peca.rotulo}
              </div>
            )}
          </div>
        );
      })}
      {secao && <CabecalhoSecao secao={secao} />}
    </AbsoluteFill>
  );
};
