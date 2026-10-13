import { Img, staticFile } from "remotion";
import { cor } from "../estilo";
import type { Icone as TIcone } from "../tipos";

/** Retrato redondo com borda preta, recortado no ponto de foco da imagem. */
export const Icone: React.FC<{ icone: TIcone; tamanho: number; borda?: number }> = ({
  icone,
  tamanho,
  borda = Math.max(4, Math.round(tamanho * 0.028)),
}) => {
  const { w, h } = icone.midia;
  const escala = tamanho / (icone.diametro * Math.min(w, h));
  const largura = w * escala;
  const altura = h * escala;
  return (
    <div
      style={{
        width: tamanho,
        height: tamanho,
        borderRadius: "50%",
        overflow: "hidden",
        position: "relative",
        boxShadow: `0 0 0 ${borda}px ${cor.bordaIcone}`,
        background: "#ddd",
      }}
    >
      <Img
        src={staticFile(icone.midia.arquivo)}
        style={{
          position: "absolute",
          width: largura,
          height: altura,
          maxWidth: "none",
          left: tamanho / 2 - icone.foco[0] * largura,
          top: tamanho / 2 - icone.foco[1] * altura,
        }}
      />
    </div>
  );
};
