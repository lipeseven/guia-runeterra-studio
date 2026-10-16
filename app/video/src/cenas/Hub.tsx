import type { CenaHub } from "../tipos";
import { Capa } from "./Capa";

/**
 * Transição de seção (guia de estilo §10.2): a PRÓPRIA capa, com continuidade — a câmera parte do ícone em que a
 * transição anterior parou, afasta até a capa inteira e fecha no personagem da próxima seção.
 * O layout da capa nunca é alterado (a antiga variante "esteira", que enfileirava os ícones, foi aposentada).
 */
export const Hub: React.FC<{ cena: CenaHub; duracao: number }> = ({ cena, duracao }) => (
  <Capa cena={{ ...cena, tipo: "capa" }} duracao={duracao} />
);
