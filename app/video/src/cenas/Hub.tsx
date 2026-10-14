import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Icone } from "../componentes/Icone";
import { fonte } from "../estilo";
import { useCores } from "../tema";
import { iconeDaCapa, type CenaHub } from "../tipos";
import { Capa } from "./Capa";

const TAM = 340; // diâmetro do ícone na esteira
const PASSO = TAM + 110;

/**
 * Transição de seção (guia de estilo §10.2): os ícones da capa voltam e a câmera fecha no personagem da
 * próxima seção. "grade" = a própria capa com zoom; "esteira" = fileira de ícones que desliza até ele.
 */
export const Hub: React.FC<{ cena: CenaHub; duracao: number }> = ({ cena, duracao }) => {
  if (cena.variante === "grade") return <Capa cena={{ ...cena, tipo: "capa" }} duracao={duracao} />;
  return <Esteira cena={cena} duracao={duracao} />;
};

const Esteira: React.FC<{ cena: CenaHub; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const cores = useCores();
  const icones = cena.circulos.map((c) => iconeDaCapa(cena.midia, c));
  const alvo = cena.destaque;
  const origem = Math.max(0, alvo - 2); // começa alguns ícones antes e desliza até o alvo
  const meio = Math.max(8, duracao * 0.55);
  const desliza = interpolate(frame, [0, meio], [origem, alvo], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const zoom = interpolate(frame, [meio, Math.max(meio + 1, duracao)], [1, 1.7], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.quad),
  });
  const deslocamento = 960 - TAM / 2 - desliza * PASSO;
  return (
    <AbsoluteFill style={{ background: cores.fundo, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})`, transformOrigin: "960px 500px" }}>
        {icones.map((ic, k) => (
          <div key={k} style={{ position: "absolute", left: deslocamento + k * PASSO, top: 330, width: TAM, textAlign: "center" }}>
            <Icone icone={ic} tamanho={TAM} />
            <div
              style={{
                marginTop: 26,
                fontFamily: fonte.rotulo,
                fontWeight: 700,
                fontSize: 54,
                color: cores.texto,
                whiteSpace: "nowrap",
                marginLeft: -60,
                marginRight: -60,
              }}
            >
              {ic.nome}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
