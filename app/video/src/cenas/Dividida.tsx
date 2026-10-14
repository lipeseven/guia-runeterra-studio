import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Figura } from "../componentes/Figura";
import { Credito, sombraTexto } from "../componentes/CabecalhoSecao";
import { transformMovimento } from "../efeitos";
import { fonte } from "../estilo";
import type { CenaDividida } from "../tipos";

/**
 * Tela dividida (guia de estilo §10.2): 2 ou 3 imagens em altura total lado a lado, cada uma entrando
 * quando o seu assunto é falado, com o nome embaixo ("Tryndamere | Ashe").
 */
export const Dividida: React.FC<{ cena: CenaDividida; quadro: (palavra: number) => number; duracao: number }> = ({
  cena,
  quadro,
  duracao,
}) => {
  const frame = useCurrentFrame();
  const n = cena.pecas.length;
  const larg = (1920 - cena.separador * (n - 1)) / n;
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      {cena.pecas.map((peca, k) => {
        const inicio = k === 0 ? 0 : Math.max(0, quadro(peca.de));
        if (frame < inicio) return null;
        const e = interpolate(frame, [inicio, inicio + 14], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        const entrada: React.CSSProperties =
          cena.entrada === "deslizar"
            ? { transform: `translateY(${(k % 2 === 0 ? -1 : 1) * 1080 * (1 - e)}px)` }
            : cena.entrada === "revelar"
              ? { clipPath: `inset(0 0 ${100 * (1 - e)}% 0)` }
              : {};
        return (
          <div
            key={k}
            style={{ position: "absolute", top: 0, left: k * (larg + cena.separador), width: larg, height: 1080, overflow: "hidden", ...entrada }}
          >
            <Figura
              midia={peca.midia}
              largura={larg}
              altura={1080}
              foco={peca.foco ?? [0.5, 0.4]}
              style={{ transform: transformMovimento(cena.movimento, p) }}
            />
            {peca.rotulo && (
              <div
                style={{
                  position: "absolute",
                  bottom: 70,
                  width: "100%",
                  textAlign: "center",
                  color: "#fff",
                  fontFamily: fonte.rotulo,
                  fontWeight: 700,
                  fontSize: n === 3 ? 66 : 84,
                  textShadow: sombraTexto,
                  opacity: interpolate(frame, [inicio + 6, inicio + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              >
                {peca.rotulo}
              </div>
            )}
            <Credito texto={peca.midia.credito} direita={16} baixo={10} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
