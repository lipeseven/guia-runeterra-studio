// Catálogo do horizontal, fase C (montagem): junta os clipes Cycles (fase A), overlays/ícones do HUB e gráficos/GPS (fase B)
// com os componentes do v1 (palavra, contador, rótulo, anotações, cartões, linha de transições), sem alterar o v1.
// Plano em plano.json (um trecho = um bloco de render). Render: render.mjs. Mídias: preparar.sh → oficina/video/_public.
import React, { type CSSProperties } from "react";
import { AbsoluteFill, Composition, Img, Loop, OffthreadVideo, Sequence, registerRoot, staticFile, useCurrentFrame } from "remotion";
import { Cena, FONTE, Fundo, entra, sai, suave, useTempo } from "../../../v1/src/base";
import { Contador, Palavra, Rotulo, type PalavraP } from "../../../v1/src/textos";
import { Anotacoes, type Anotacao } from "../../../v1/src/anotacoes";
import { Capitulo, Pessoa, Solta, type PessoaP } from "../../../v1/src/cartoes";
import { Linha, type Entrada } from "../../../v1/src/linha";
import plano from "./plano.json";

const FPS = 60;
const CHEIO: CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%" };

type Midia = { src: string; de?: number; vel?: number; still?: boolean; alfa?: boolean };
type Kf = [number, number, number, number]; // t, escala, centro x, centro y
type Overlay = { src: string; op: number; de?: number; loop?: number };
type Icone = { src: string; x: number; y: number; w: number; em: number; giro?: number; branco?: boolean };
type ClipeP = {
  midia?: Midia; fundo?: "claro" | "cheio" | "escuro" | "tecnico"; crop?: Kf[]; filtro?: string; lavar?: number;
  overlays?: Overlay[]; palavra?: PalavraP; palavras?: PalavraP[]; anotacoes?: Anotacao[];
  rotulos?: React.ComponentProps<typeof Rotulo>[]; contador?: React.ComponentProps<typeof Contador>; icones?: Icone[];
};
type Trecho = ClipeP & {
  id: string; nome: string; dur: number; tipo: string; n?: number; titulo?: string; texto?: string; modo?: "escuro" | "cheio";
  sub?: string; em?: number; pessoa?: PessoaP; itens?: (ClipeP & { dur: number; entrada?: Entrada })[];
  efeito?: "zoom" | "wipe" | "mascara"; t?: number; centro?: [number, number]; a?: ClipeP; b?: ClipeP;
};
const TRECHOS = (plano as unknown as { trechos: Trecho[] }).trechos;
const QUADROS = TRECHOS.map((t) => Math.round(t.dur * FPS));
const INICIO = QUADROS.map((_, i) => QUADROS.slice(0, i).reduce((s, q) => s + q, 0));
const TOTAL = QUADROS.reduce((s, q) => s + q, 0);

const Fonte: React.FC<{ m: Midia }> = ({ m }) =>
  m.still ? (
    <Img src={staticFile(m.src)} style={{ ...CHEIO, objectFit: "cover" }} />
  ) : (
    <OffthreadVideo src={staticFile(m.src)} trimBefore={Math.round((m.de ?? 0) * FPS) || undefined} playbackRate={m.vel ?? 1}
      transparent={m.alfa || m.src.endsWith(".webm")} muted style={{ ...CHEIO, objectFit: "cover" }} />
  );

// pan-crop: interpola escala e centro entre chaves (suave), sem deixar borda vazia
function enquadrar(kfs: Kf[] | undefined, t: number): CSSProperties {
  if (!kfs?.length) return {};
  let [_, s, cx, cy] = kfs[0];
  for (let i = 0; i < kfs.length; i++) {
    const a = kfs[i], b = kfs[i + 1];
    if (!b) { if (t >= a[0]) [, s, cx, cy] = a; break; }
    if (t >= a[0] && t <= b[0]) {
      const k = suave(t, a[0], b[0]);
      s = a[1] + (b[1] - a[1]) * k; cx = a[2] + (b[2] - a[2]) * k; cy = a[3] + (b[3] - a[3]) * k;
      break;
    }
  }
  cx = Math.min(Math.max(cx, 960 / s), 1920 - 960 / s);
  cy = Math.min(Math.max(cy, 540 / s), 1080 - 540 / s);
  return { transformOrigin: "0 0", transform: `translate(960px, 540px) scale(${s}) translate(${-cx}px, ${-cy}px)` };
}

const Ovl: React.FC<{ o: Overlay }> = ({ o }) => {
  const de = Math.round((o.de ?? 0) * FPS);
  const v = <Fonte m={{ src: o.src, alfa: true, de: de < 0 ? -de / FPS : 0 }} />;
  return (
    <Sequence from={Math.max(0, de)} layout="none">
      <div style={{ ...CHEIO, opacity: o.op }}>{o.loop ? <Loop durationInFrames={o.loop * FPS} layout="none">{v}</Loop> : v}</div>
    </Sequence>
  );
};

const Ic: React.FC<{ i: Icone }> = ({ i }) => {
  const { t } = useTempo();
  if (t < i.em) return null;
  const k = entra(((t - i.em) * FPS) / 9);
  return (
    <Img src={staticFile(i.src)} style={{ position: "absolute", left: i.x - i.w / 2, top: i.y - i.w / 2, width: i.w, height: i.w, opacity: k,
      transform: `rotate(${i.giro ?? 0}deg) scale(${0.6 + 0.4 * k + 0.08 * Math.sin(k * Math.PI)})`, filter: i.branco ? "brightness(0) invert(1)" : undefined }} />
  );
};

const Clipe: React.FC<{ p: ClipeP }> = ({ p }) => {
  const { t } = useTempo();
  return (
    <Cena fundo={<Fundo modo={p.fundo ?? "claro"} />}>
      {p.midia && (
        <div style={{ ...CHEIO, overflow: "hidden" }}>
          <div style={{ ...CHEIO, ...enquadrar(p.crop, t), filter: p.filtro }}><Fonte m={p.midia} /></div>
        </div>
      )}
      {p.lavar ? <div style={{ ...CHEIO, background: "#f3f1ec", opacity: p.lavar }} /> : null}
      {p.overlays?.map((o, i) => <Ovl key={i} o={o} />)}
      {[...(p.palavras ?? []), ...(p.palavra ? [p.palavra] : [])].map((w, i) => <Palavra key={i} {...w} />)}
      {p.anotacoes && <Anotacoes itens={p.anotacoes} />}
      {p.rotulos?.map((r, i) => <Rotulo key={i} {...r} />)}
      {p.contador && <Contador {...p.contador} />}
      {p.icones?.map((ic, i) => <Ic key={i} i={ic} />)}
    </Cena>
  );
};

// transições que o v1 não tem: zoom (punch), wipe com linha, máscara em íris
const Trans: React.FC<{ p: Trecho }> = ({ p }) => {
  const f = useCurrentFrame();
  const T = Math.round((p.t ?? 1) * FPS);
  const dq = (p.efeito === "zoom" ? 0 : p.efeito === "wipe" ? 20 : 28);
  const k = (f - T) / (dq || 1);
  let estA: CSSProperties = {}, estB: CSSProperties = {};
  let linha: React.ReactNode = null;
  if (p.efeito === "zoom") {
    const ka = sai(Math.max(0, (f - (T - 12)) / 12)), kb = 1 - entra((f - T) / 16);
    estA = { transform: `scale(${1 + 1.6 * ka})`, filter: `blur(${12 * ka}px)` };
    estB = { transform: `scale(${1 + 1.6 * kb})`, filter: `blur(${12 * kb}px)` };
  } else if (p.efeito === "wipe") {
    const x = entra(k) * 100;
    estB = { clipPath: `inset(0 ${100 - x}% 0 0)` };
    if (k > 0 && k < 1.05) linha = <div style={{ position: "absolute", top: 0, bottom: 0, left: `calc(${x}% - 5px)`, width: 10, background: "#f2c230", boxShadow: "0 0 30px #f2c230" }} />;
  } else {
    const [cx, cy] = p.centro ?? [960, 540];
    const r = entra(k) * 2300;
    estB = { WebkitMaskImage: `radial-gradient(circle at ${cx}px ${cy}px, #000 ${r}px, transparent ${r + 60}px)`, maskImage: `radial-gradient(circle at ${cx}px ${cy}px, #000 ${r}px, transparent ${r + 60}px)` };
  }
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Sequence durationInFrames={T + dq + 1} layout="none"><div style={{ ...CHEIO, ...estA }}><Clipe p={p.a!} /></div></Sequence>
      <Sequence from={T} layout="none"><div style={{ ...CHEIO, ...estB }}><Clipe p={p.b!} /></div></Sequence>
      {linha}
    </AbsoluteFill>
  );
};

// palavra entre o fundo (render opaco) e o objeto (mesmo render em alfa): a palavra fica atrás do freio
const FreioPalavra: React.FC<{ p: Trecho }> = ({ p }) => (
  <AbsoluteFill>
    <Fonte m={{ src: "c/freio_opaco.mp4" }} />
    <Palavra {...p.palavra!} />
    <Fonte m={{ src: "c/freio_alfa.webm", alfa: true }} />
  </AbsoluteFill>
);

// o ambiente (fundo gradiente, sombra, reflexo) some e sobra só o objeto em fundo liso
const AmbienteSome: React.FC = () => {
  const { t } = useTempo();
  const k = suave(t, 1.8, 4.2);
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, #f8f7f3 0%, #e9e7e2 70%, #d9d6cf 100%)" }}>
      <div style={{ ...CHEIO, opacity: 1 - k }}><Fonte m={{ src: "c/freio_opaco.mp4" }} /></div>
      <Fonte m={{ src: "c/freio_alfa.webm", alfa: true }} />
    </AbsoluteFill>
  );
};

const Selo: React.FC<{ n: number; nome: string }> = ({ n, nome }) => (
  <div style={{ position: "absolute", left: 36, top: 32, padding: "8px 16px 6px", background: "rgba(10,10,12,0.62)", color: "#fff",
    fontFamily: FONTE, fontWeight: 700, fontSize: 28, letterSpacing: 1 }}>
    {String(n).padStart(2, "0")} · {nome}
  </div>
);

function conteudo(p: Trecho) {
  switch (p.tipo) {
    case "capitulo": return <Capitulo n={p.n!} titulo={p.titulo!} />;
    case "solta": return <Solta texto={p.texto!} modo={p.modo} sub={p.sub} em={p.em} />;
    case "pessoa": return <Pessoa {...p.pessoa!} />;
    case "freio_palavra": return <FreioPalavra p={p} />;
    case "ambiente_some": return <AmbienteSome />;
    case "trans": return <Trans p={p} />;
    case "linha": return <Linha itens={p.itens!.map((it) => ({ dur: it.dur, entrada: it.entrada, cena: <Clipe p={it} /> }))} />;
    default: return <Clipe p={p} />;
  }
}

const Catalogo: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    {TRECHOS.map((p, i) => (
      <Sequence key={p.id} from={INICIO[i]} durationInFrames={QUADROS[i]} layout="none">
        <AbsoluteFill>{conteudo(p)}</AbsoluteFill>
        <Selo n={i + 1} nome={p.nome} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

registerRoot(() => <Composition id="catalogo" component={Catalogo} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} />);
