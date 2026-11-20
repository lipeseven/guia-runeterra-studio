// Linha do tempo do horizontal: cenas em sequência com as transições medidas nas referências (24 → 30 fps):
// - corte: 0 q (a cena nova já entra com a câmera em movimento);
// - empurrar: sai em ease-in de 10 q com borrão na direção (até ~8% da largura) e esticada 1,2×; a nova entra 9 q
//   depois, em ease-out de 15 q, sem rebote; o fundo não se mexe; mesma direção na saída e na entrada;
// - glitch: 5 q (faixas horizontais, ruído no quadro todo, limpo), sem cor;
// - cortina: sempre de baixo para cima, 15 q, borda reta com borda suave de ~3%;
// - cor: mergulho em cor lisa (fade 8 q, 6 q de cor, fade 8 q), para capítulo ou virada de argumento.
import { Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import { Grao, H, Movimento, W, entra, sai, useCores } from "./base";

export type Entrada =
  | { tipo: "corte" }
  | { tipo: "empurrar"; dir?: "esq" | "dir" | "cima" | "baixo" }
  | { tipo: "glitch" }
  | { tipo: "cortina" }
  | { tipo: "cor"; cor?: string };

export type Item = { dur: number; entrada?: Entrada; cena: ReactNode };

// quadros antes da fronteira em que a cena nova já aparece, e depois em que a antiga ainda aparece
const ANTES: Record<Entrada["tipo"], number> = { corte: 0, empurrar: 1, glitch: 2, cortina: 7, cor: 0 };
const DEPOIS: Record<Entrada["tipo"], number> = { corte: 0, empurrar: 0, glitch: 0, cortina: 8, cor: 0 };

const vetor = (dir: string) => (dir === "esq" ? [-1, 0] : dir === "dir" ? [1, 0] : dir === "cima" ? [0, -1] : [0, 1]);

export function duracao(itens: Item[], fps: number) {
  return Math.round(itens.reduce((s, i) => s + i.dur, 0) * fps);
}

export const Linha: React.FC<{ itens: Item[] }> = ({ itens }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cores = useCores();
  const inicio: number[] = [];
  itens.reduce((s, it, i) => ((inicio[i] = Math.round(s * fps)), s + it.dur), 0);
  const total = duracao(itens, fps);
  const fim = (i: number) => (i + 1 < itens.length ? inicio[i + 1] : total);
  let corPorCima = 0;
  let corDaVez = cores.destaque;
  let ruido = 0;
  const filtros: ReactNode[] = [];

  const cenas = itens.map((it, i) => {
    const e = it.entrada ?? { tipo: "corte" };
    const prox = itens[i + 1]?.entrada ?? { tipo: "corte" as const };
    const pre = i === 0 ? 0 : ANTES[e.tipo];
    const pos = i + 1 < itens.length ? DEPOIS[prox.tipo] : 0;
    const de = inicio[i] - pre;
    const ate = fim(i) + pos;
    const todo: CSSProperties = {};
    const conteudo: CSSProperties = {};
    let borrao = 0;
    // entrada desta cena
    const b = inicio[i];
    if (i > 0 && e.tipo === "empurrar") {
      const [vx, vy] = vetor(e.dir ?? "esq");
      const k = entra((f - (b - 1)) / 15);
      conteudo.transform = `translate(${-vx * W * 0.7 * (1 - k)}px, ${-vy * H * 0.7 * (1 - k)}px)`;
      borrao = 60 * (1 - k);
    }
    if (i > 0 && e.tipo === "glitch" && f < b) {
      todo.transform = `translateX(${(f - b) * 18}px)`;
      todo.maskImage = todo.WebkitMaskImage = "repeating-linear-gradient(0deg, #000 0 26px, transparent 26px 70px)";
    }
    if (i > 0 && e.tipo === "glitch" && f >= b && f < b + 2) ruido = 1 - (f - b) * 0.4;
    if (i > 0 && e.tipo === "cortina") {
      const k = entra((f - (b - 7)) / 15) * 103;
      todo.maskImage = todo.WebkitMaskImage = `linear-gradient(to top, #000 ${k - 3}%, transparent ${k}%)`;
    }
    // saída desta cena (a próxima entra empurrando)
    const bs = fim(i);
    if (i + 1 < itens.length && prox.tipo === "empurrar" && f >= bs - 10) {
      const [vx, vy] = vetor(prox.dir ?? "esq");
      const k = sai((f - (bs - 10)) / 10);
      conteudo.transform = `translate(${-vx * W * 0.7 * k}px, ${-vy * H * 0.7 * k}px) scale(${1 + Math.abs(vx) * 0.2 * k}, ${1 + Math.abs(vy) * 0.2 * k})`;
      borrao = 60 * k;
    }
    // mergulho em cor em volta da fronteira
    if (i > 0 && e.tipo === "cor" && Math.abs(f - b) <= 11) {
      corPorCima = Math.abs(f - b) <= 3 ? 1 : 1 - (Math.abs(f - b) - 3) / 8;
      corDaVez = e.cor ?? cores.destaque;
    }
    if (borrao > 0.5) {
      const vert = (it.entrada?.tipo === "empurrar" && ["cima", "baixo"].includes(it.entrada.dir ?? "")) || (prox.tipo === "empurrar" && ["cima", "baixo"].includes(prox.dir ?? ""));
      const id = `borrao${i}`;
      filtros.push(
        <filter key={id} id={id} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={vert ? `0 ${borrao}` : `${borrao} 0`} />
        </filter>,
      );
      conteudo.filter = `url(#${id})`;
    }
    return (
      <Sequence key={i} from={de} durationInFrames={Math.max(1, ate - de)} layout="none">
        <Movimento.Provider value={{ todo, conteudo, antes: pre }}>{it.cena}</Movimento.Provider>
      </Sequence>
    );
  });

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#000" }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>{filtros}</svg>
      {cenas}
      {ruido > 0 && (
        <div style={{ position: "absolute", inset: 0, opacity: ruido }}>
          <div style={{ position: "absolute", inset: 0, background: "#777" }} />
          <Grao semente={f} forca={1} />
        </div>
      )}
      {corPorCima > 0 && <div style={{ position: "absolute", inset: 0, background: corDaVez, opacity: corPorCima }} />}
    </div>
  );
};
