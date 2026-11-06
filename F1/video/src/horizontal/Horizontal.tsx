// Composição do horizontal: plano em JSON (lista de cenas com duração em segundos e entrada) → vídeo 1920×1080.
// Regras e medidas: F1/docs/folha_horizontal.md. O diretor do horizontal (a fazer) gera este plano preso às palavras.
import { AbsoluteFill, type CalculateMetadataFunction } from "remotion";
import { Cores, PALETA, type Paleta } from "./base";
import { Estudio, Pista, type CameraEstudio, type CameraPista, type CarroNaPista } from "./cenas3d";
import { Capitulo, Pessoa, Solta, type PessoaP } from "./cartoes";
import { Contador, Rotulo, type PalavraP } from "./textos";
import type { Anotacao } from "./anotacoes";
import { duracao, Linha, type Entrada, type Item } from "./linha";

type Sobre = {
  palavra?: PalavraP;
  anotacoes?: Anotacao[];
  contador?: React.ComponentProps<typeof Contador>;
  rotulos?: React.ComponentProps<typeof Rotulo>[];
};
export type CenaH = { dur: number; entrada?: Entrada } & (
  | ({ tipo: "estudio"; modo?: "claro" | "cheio" | "escuro" | "tecnico"; camera?: CameraEstudio; carro?: string } & Sobre)
  | ({ tipo: "pista"; carros: CarroNaPista[]; camera: CameraPista; carro?: string } & Sobre)
  | ({ tipo: "pessoa" } & PessoaP)
  | { tipo: "capitulo"; n: number; titulo: string; circuito?: string }
  | { tipo: "solta"; texto: string; modo?: "escuro" | "cheio"; sub?: string }
);
export type PropsHorizontal = { paleta?: Partial<Paleta>; carro: string; cenas: CenaH[] };

const extras = (s: Sobre) => (
  <>
    {s.contador && <Contador {...s.contador} />}
    {s.rotulos?.map((r, i) => <Rotulo key={i} {...r} />)}
  </>
);

function cena(c: CenaH, carro: string) {
  switch (c.tipo) {
    case "estudio":
      return <Estudio carro={c.carro ?? carro} modo={c.modo} camera={c.camera} palavra={c.palavra} anotacoes={c.anotacoes} extra={extras(c)} />;
    case "pista":
      return <Pista carro={c.carro ?? carro} carros={c.carros} camera={c.camera} palavra={c.palavra} anotacoes={c.anotacoes} extra={extras(c)} />;
    case "pessoa":
      return <Pessoa {...c} />;
    case "capitulo":
      return <Capitulo n={c.n} titulo={c.titulo} circuito={c.circuito} />;
    case "solta":
      return <Solta texto={c.texto} modo={c.modo} sub={c.sub} />;
  }
}

export const Horizontal: React.FC<PropsHorizontal> = ({ paleta, carro, cenas }) => {
  const itens: Item[] = cenas.map((c) => ({ dur: c.dur, entrada: c.entrada, cena: cena(c, carro) }));
  return (
    <Cores.Provider value={{ ...PALETA, ...paleta }}>
      <AbsoluteFill>
        <Linha itens={itens} />
      </AbsoluteFill>
    </Cores.Provider>
  );
};

export const medirHorizontal: CalculateMetadataFunction<PropsHorizontal> = ({ props }) => ({
  durationInFrames: Math.max(1, duracao(props.cenas.map((c) => ({ dur: c.dur, cena: null })), 30)),
});

/** Demonstração de ~50 s com todos os recursos (sem narração; textos de exemplo, nenhuma citação real). */
export const DEMO_HORIZONTAL: PropsHorizontal = {
  paleta: { destaque: "#f2c230" },
  carro: "ferrari_sf26.glb",
  cenas: [
    {
      tipo: "estudio", dur: 5, camera: { tipo: "chegada" },
      palavra: { texto: "FERRARI", em: 0.3 },
      anotacoes: [
        { tipo: "nota", texto: "mais branco que nos últimos anos", x: 1300, y: 250, largura: 500, em: 2.6 },
        { tipo: "seta", de: [1360, 420], para: [1150, 470], curva: -0.2, em: 3.6 },
      ],
    },
    {
      tipo: "estudio", dur: 4.5, entrada: { tipo: "empurrar", dir: "esq" }, camera: { tipo: "frente", de: 30 },
      palavra: { texto: "ASA", em: 0.4, tam: 520 },
      anotacoes: [{ tipo: "circulo", centro: [330, 640], rx: 330, ry: 105, em: 1.6 }, { tipo: "nota", texto: "nova!", x: 220, y: 760, em: 2.4 }],
    },
    {
      tipo: "estudio", dur: 4.5, entrada: { tipo: "corte" }, modo: "cheio", camera: { tipo: "deslizar", de: 60 },
      palavra: { texto: "TEMPO", em: 0.2 },
      anotacoes: [{ tipo: "corrigido", antes: "+0.15s", depois: "+0.015s", x: 1250, y: 180, tam: 70, em: 1.4 }],
    },
    { tipo: "capitulo", dur: 4, entrada: { tipo: "cor" }, n: 1, titulo: "O carro de 2026" },
    {
      tipo: "estudio", dur: 5.5, entrada: { tipo: "glitch" }, modo: "tecnico", camera: { tipo: "orbita", de: 70, vel: 0.12 },
      contador: { valor: 50, unidade: "%", rotulo: "POTÊNCIA ELÉTRICA (EXEMPLO)", x: 140, y: 120, em: 0.8 },
      rotulos: [{ texto: "Bateria", de: [980, 700], para: [1240, 560], em: 2 }],
    },
    {
      tipo: "pessoa", dur: 5, entrada: { tipo: "cortina" }, nome: "Nome Sobrenome", cargo: "Exemplo de cargo",
      citacao: "Texto de exemplo: a citação aparece palavra por palavra junto com a fala.",
    },
    {
      tipo: "pista", dur: 6, entrada: { tipo: "empurrar", dir: "dir" }, camera: { tipo: "helicoptero" },
      carros: [{ u0: 0.034, km: 262, ladoAte: { valor: -3.2, de: 2.2, ate: 4.6 } }, { u0: 0.04, km: 250, lado: 0.4 }],
      palavra: { texto: "ATAQUE", em: 3.2, ate: 5.3, topo: 60, tam: 300 },
    },
    { tipo: "pista", dur: 2.5, entrada: { tipo: "corte" }, camera: { tipo: "passagem" }, carros: [{ u0: 0.2, km: 300 }] },
    { tipo: "pista", dur: 5, entrada: { tipo: "corte" }, camera: { tipo: "pov" }, carros: [{ u0: 0.84, km: 280 }] },
    { tipo: "solta", dur: 2.5, entrada: { tipo: "corte" }, texto: "DECISÃO", sub: "em uma volta" },
    { tipo: "estudio", dur: 5, entrada: { tipo: "cor", cor: "#101113" }, modo: "escuro", camera: { tipo: "orbita", de: 200, vel: 0.1 } },
  ],
};
