import { AbsoluteFill } from "remotion";
import { EntradaTexto, type EfeitoTexto, type Entrada } from "../efeitos";
import { cor, fonte } from "../estilo";
import type { Secao } from "../tipos";
import { Icone } from "./Icone";

/** Nome da seção no topo + ícone no canto superior esquerdo (fixos durante a seção). */
export const CabecalhoSecao: React.FC<{ secao: Secao }> = ({ secao }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div style={{ position: "absolute", left: 10, top: 6 }}>
      <Icone icone={secao.icone} tamanho={252} />
    </div>
    <div
      style={{
        position: "absolute",
        top: 14,
        width: "100%",
        textAlign: "center",
        fontFamily: fonte.rotulo,
        fontWeight: 700,
        fontSize: 96,
        color: cor.texto,
        lineHeight: 1.1,
      }}
    >
      {secao.titulo}
    </div>
  </AbsoluteFill>
);

/** Legenda grande embaixo da imagem; o efeito de entrada vem da direção. */
export const Legenda: React.FC<{ texto: string; desde: number; entrada?: Entrada<EfeitoTexto> }> = ({
  texto,
  desde,
  entrada,
}) => (
  <div style={{ position: "absolute", top: 940, width: "100%", display: "flex", justifyContent: "center" }}>
    <EntradaTexto
      texto={texto}
      desde={desde}
      entrada={entrada}
      style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: 92, color: cor.texto, whiteSpace: "nowrap" }}
    />
  </div>
);
