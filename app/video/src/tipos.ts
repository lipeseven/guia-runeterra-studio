// Formato da direção gerada pelo sistema (ver tools/prototipo/preparar.py).
// Cenas são ancoradas em ÍNDICES DE PALAVRAS: trocar a narração só muda os tempos das palavras.
import type { EfeitoImagem, EfeitoTexto, Entrada, Movimento } from "./efeitos";
export type { EfeitoImagem, EfeitoTexto, Entrada, Movimento };

export type Palavra = { t: string; i: number; f: number };

export type Midia = { arquivo: string; w: number; h: number; credito?: string };

export type Icone = {
  nome: string;
  midia: Midia;
  foco: [number, number]; // centro do recorte, em fração da imagem
  diametro: number; // diâmetro do recorte, em fração do menor lado
};

/** Círculo detectado na capa (tools/capa.py): cx/cy em fração da imagem, r em fração do menor lado. */
export type CirculoCapa = { nome: string; cx: number; cy: number; r: number };

type Base = {
  de: number;
  ate: number;
  semente?: number | string;
  secao?: Secao;
  id?: string;
  bloco?: string;
  q?: number; // quadro em que a cena começa (calculado na montagem)
};

export type CenaCapa = Base & {
  tipo: "capa";
  midia: Midia;
  circulos: CirculoCapa[];
  destaque: number;
  zoom: number;
};
export type ItemCartao = {
  de: number;
  midia: Midia;
  legenda: string;
  legenda_em?: number;
  entrada_img?: Entrada<EfeitoImagem>;
  entrada_legenda?: Entrada<EfeitoTexto>;
  movimento?: Movimento;
};
export type CenaCartao = Base & { tipo: "cartao"; itens: ItemCartao[] };
export type CenaTelaCheia = Base & {
  tipo: "telacheia";
  midia: Midia;
  foco: [number, number];
  movimento: Movimento;
  entrada_img?: Entrada<EfeitoImagem>;
  // nome sobre a arte (ex.: "Raum" / "o demônio dos segredos")
  rotulo?: string;
  subrotulo?: string;
  rotulo_em?: number;
  entrada_rotulo?: Entrada<EfeitoTexto>;
};

/** Transição de seção: a grade/esteira de ícones da capa volta e fecha no personagem da próxima seção. */
export type CenaHub = Base & {
  tipo: "hub";
  midia: Midia;
  circulos: CirculoCapa[];
  destaque: number;
  zoom: number;
  variante: "grade" | "esteira";
};

/** Peça de tela dividida / lista acumulada: entra quando a palavra é falada. */
export type PecaPainel = { de: number; midia: Midia; foco?: [number, number]; rotulo?: string };

export type CenaDividida = Base & {
  tipo: "dividida";
  pecas: PecaPainel[];
  separador: number; // px entre os painéis (0 = colados)
  entrada: "corte" | "deslizar" | "revelar";
  movimento?: Movimento;
};

export type CenaLista = Base & {
  tipo: "lista";
  pecas: PecaPainel[];
  entrada: Entrada<EfeitoImagem>;
  inclinado: boolean; // painéis levemente tortos, como fotos coladas
};

export type CenaMeio = Base & {
  tipo: "meio";
  midia: Midia;
  foco: [number, number];
  lado: "esq" | "dir"; // lado da IMAGEM
  texto: string;
  texto_em: number;
  entrada_img?: Entrada<EfeitoImagem>;
  entrada_texto?: Entrada<EfeitoTexto>;
  movimento?: Movimento;
};

export type CenaTexto = Base & {
  tipo: "texto";
  texto: string;
  fundo: "claro" | "escuro";
  entrada_texto?: Entrada<EfeitoTexto>;
};

export type CenaCitacao = Base & {
  tipo: "citacao";
  midia: Midia;
  foco: [number, number];
  autor: string;
  destaques: number[]; // índices de palavras do roteiro que acendem em vermelho
  lado: "esq" | "dir" | "centro";
  movimento?: Movimento;
};
export type CenaRecorte = Base & {
  tipo: "recorte";
  midia: Midia;
  legenda: string;
  legenda_em: number;
  entrada_img?: Entrada<EfeitoImagem>;
  entrada_legenda?: Entrada<EfeitoTexto>;
};
export type CenaDialogo = Base & {
  tipo: "dialogo";
  esquerda: Icone;
  direita: Icone;
  destaques: number[];
};

export type CenaClipe = Base & {
  tipo: "clipe";
  arquivo: string; // tomada já recortada do clipe original
  duracao_tomada: number; // segundos
  volume?: number; // 0 = mudo (padrão)
  movimento?: Movimento;
  entrada_img?: Entrada<EfeitoImagem>;
};

export type PecaMosaico = {
  de: number; // palavra em que a peça entra
  midia: Midia;
  x: number; // centro, em px (tela 1920x1080)
  y: number;
  largura: number;
  rotacao: number;
  de_onde: "esq" | "dir" | "cima" | "baixo";
  quadros: number;
};
export type CenaMosaico = Base & {
  tipo: "mosaico";
  fundo: Midia;
  movimento?: Movimento;
  pecas: PecaMosaico[];
  borda: number;
};

export type Cena =
  | CenaCapa
  | CenaCartao
  | CenaTelaCheia
  | CenaRecorte
  | CenaDialogo
  | CenaClipe
  | CenaMosaico
  | CenaHub
  | CenaDividida
  | CenaLista
  | CenaMeio
  | CenaTexto
  | CenaCitacao;

export type Secao = { titulo: string; icone: Icone };

export type Trecho = {
  audio: string;
  palavras: Palavra[];
  secao?: Secao;
  cenas: Cena[];
  tema?: "claro" | "escuro";
  sons?: Som[];
};

/** Efeito sonoro ancorado numa palavra (raro: guia de estilo §8). Volume relativo (0–1), bem abaixo da voz. */
export type Som = { arquivo: string; de: number; volume: number; categoria?: string };

/** Ícone redondo recortado de dentro de um círculo da capa (sem pegar a borda preta original). */
export const iconeDaCapa = (capa: Midia, c: CirculoCapa): Icone => ({
  nome: c.nome,
  midia: capa,
  foco: [c.cx, c.cy],
  diametro: 2 * c.r * 0.93,
});
