// Entrada de UM item (lista / tela dividida / mosaico) escolhida à mão no storyboard. Sem escolha, cada cena usa a
// entrada que o diretor sorteou para ela. Importado só por linhas `impressao:ignorar`: não muda o cache dos blocos.
import type React from "react";
import { estiloEntradaImagem } from "../efeitos";

export type EntradaItem = "nenhuma" | "fade" | "deslizar" | "revelar" | "pop";

export const entradaManual = (nome: EntradaItem, frame: number, fps: number, inicio: number): React.CSSProperties => {
  switch (nome) {
    case "nenhuma":
      return {};
    case "fade":
      return estiloEntradaImagem(frame, fps, inicio, { efeito: "fade", quadros: 14 });
    case "deslizar":
      return estiloEntradaImagem(frame, fps, inicio, { efeito: "deslizar_cima", quadros: 14 });
    case "revelar":
      return estiloEntradaImagem(frame, fps, inicio, { efeito: "revelar_esq", quadros: 16 });
    case "pop":
      return estiloEntradaImagem(frame, fps, inicio, { efeito: "pop", quadros: 14 });
  }
};
