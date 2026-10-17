import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { sombraTexto } from "../componentes/CabecalhoSecao";
import { fonte } from "../estilo";

/** Uma seta com nome: aparece na palavra `de`, aponta do rótulo (`rotulo_xy`) para o alvo (`alvo_xy`), em px. */
export type Seta = { de: number; rotulo: string; alvo_xy: [number, number]; rotulo_xy: [number, number] };
export type ComSetas = { setas?: Seta[]; seta_img?: string; seta_angulo?: number; seta_tema?: "claro" | "escuro" };

/**
 * Setas apontando para personagens conforme os nomes são falados ("em cima é a Lissandra, à esquerda a Serylda…").
 * O desenho da seta é o asset do Felipe (acervo, `seta*.png/avif`, fundo branco removido), pintado de branco com
 * sombra para aparecer sobre qualquer arte. `seta_angulo` = para onde o desenho original aponta (graus, da cauda à
 * ponta). Seta curva apontando para a esquerda é espelhada, para a curva continuar natural. O nome entra seco
 * (texto sem animação); a seta, com um fade curtinho.
 */
export const Setas: React.FC<{ cena: ComSetas; quadro: (palavra: number) => number }> = ({ cena, quadro }) => {
  const frame = useCurrentFrame();
  if (!cena.setas?.length || !cena.seta_img) return null;
  const base = cena.seta_angulo ?? 0;
  // sobre arte (tela cheia): seta e nome brancos com sombra; sobre o fundo branco (recorte): o desenho original, escuro
  const claro = cena.seta_tema === "claro";
  return (
    <>
      {cena.setas.map((s, k) => {
        const desde = Math.max(0, quadro(s.de));
        if (frame < desde) return null;
        const [lx, ly] = s.rotulo_xy;
        const [ax, ay] = s.alvo_xy;
        const dist0 = Math.hypot(ax - lx, ay - ly) || 1;
        // a seta sai da BORDA do nome (não de cima dele) e para um pouco antes do alvo
        const meia = Math.min(Math.abs(((ax - lx) / dist0) * (s.rotulo.length * 19 + 28)) + Math.abs(((ay - ly) / dist0) * 48), dist0 * 0.45);
        const sx = lx + ((ax - lx) / dist0) * meia;
        const sy = ly + ((ay - ly) / dist0) * meia;
        const ex = ax - ((ax - lx) / dist0) * 20;
        const ey = ay - ((ay - ly) / dist0) * 20;
        const dx = ex - sx;
        const dy = ey - sy;
        const dist = Math.hypot(dx, dy);
        const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
        const esquerda = dx < 0;
        // espelhada, a seta original aponta para (180 - base)
        const rot = esquerda ? ang - (180 - base) : ang - base;
        const tam = Math.min(300, Math.max(110, dist * 0.95));
        const op = interpolate(frame, [desde, desde + 6], [0, 1], { extrapolateRight: "clamp" });
        return (
          <div key={k}>
            <Img
              src={staticFile(cena.seta_img!)}
              style={{
                position: "absolute",
                left: (sx + ex) / 2 - tam / 2,
                top: (sy + ey) / 2 - tam / 2,
                width: tam,
                height: tam,
                opacity: op,
                transform: `rotate(${rot}deg)${esquerda ? " scaleX(-1)" : ""}`,
                filter: claro ? "drop-shadow(0 0 3px #fff) drop-shadow(0 0 2px #fff)" : "invert(1) drop-shadow(0 0 6px rgba(0,0,0,0.95)) drop-shadow(0 2px 3px rgba(0,0,0,0.9))",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: lx,
                top: ly,
                transform: "translate(-50%, -50%)",
                color: claro ? "#1b1b1b" : "#fff",
                fontFamily: fonte.rotulo,
                fontWeight: 700,
                fontSize: 68,
                whiteSpace: "nowrap",
                textShadow: claro ? undefined : sombraTexto,
              }}
            >
              {s.rotulo}
            </div>
          </div>
        );
      })}
    </>
  );
};
