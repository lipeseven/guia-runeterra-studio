// Piloto "Como funciona o freio de um F1?". Cada cena começa numa palavra do roteiro; o 3D só entra na ênfase da peça.
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, staticFile, useVideoConfig } from "remotion";
import { Autodromo, CarroLado, Disco, Fumaca, Legenda, Placa, entra, noTrecho, suave, useTempo, type Palavra } from "./kit";

type Props = { palavras: Palavra[] };
const CHAVES = ["carbono", "calor", "seis", "pastilhas", "furinhos", "assistência", "defeito"];

const Abertura: React.FC<{ marca: Record<string, number> }> = ({ marca }) => {
  const t = useTempo();
  const freia = suave(t, marca.sai - 0.2, marca.hora);
  const vel = 1.6 - freia * 1.2;
  const zoom = 1 + suave(t, marca.forca, marca.fim) * 0.5;
  return (
    <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: "50% 62%" }}>
      <Autodromo velocidade={vel} />
      <Fumaca x={760} y={1270} forca={freia} sentido={-1} />
      <CarroLado x={540} y={1060} escala={1.08} freada={freia} giro={t * 900 * (1 - freia * 0.85)} calor={freia * 0.7} />
      <Placa de={300} ate={95} unidade="km/h" inicio={marca.sai} dur={marca.hora - marca.sai} x={540} y={700} />
      <Placa de={0} ate={3} unidade="s" inicio={marca.tres} dur={1.6} x={540} y={840} cor="#7fdcff" tam={62} />
      <Placa ate={5} prefixo="+" unidade="vezes o peso" inicio={marca.cinco} x={540} y={1460} cor="#ff6a3d" />
    </AbsoluteFill>
  );
};

const Carbono: React.FC<{ marca: Record<string, number> }> = ({ marca }) => {
  const t = useTempo();
  const aco = entra(t, marca.aco, 0.3);
  const volta = entra(t, marca.aqui, 0.4);
  const lado = (1 - volta) * aco;
  return (
    <AbsoluteFill>
      <Autodromo topo="#05070e" base="#101a2c" velocidade={0.15} horizonte={1560} />
      <Disco x={540 - lado * 230} y={950} raio={330 - lado * 130} calor={0} giro={t * 40} />
      {lado > 0.01 && (
        <div style={{ opacity: lado }}>
          <svg width={460} height={460} viewBox="-115 -115 230 230" style={{ position: "absolute", left: 540 + 20, top: 720 }}>
            <circle r={105} fill="#b7bcc6" stroke="#2a2d33" strokeWidth={4} />
            <circle r={50} fill="#5b616c" />
            {Array.from({ length: 12 }, (_, k) => <circle key={k} cx={Math.cos(k * 0.5236) * 80} cy={Math.sin(k * 0.5236) * 80} r={6} fill="#40444c" />)}
          </svg>
          <Placa texto="AÇO" inicio={marca.aco} x={790} y={1230} cor="#d6dbe4" tam={52} />
          <div />
        </div>
      )}
      <Placa ate={278} unidade="mm" inicio={marca.prato} x={540} y={1450} />
      {t > marca.frio && <Placa texto="FRIO: QUASE NÃO FREIA" inicio={marca.frio} x={540} y={1570} cor="#7fdcff" tam={50} />}
    </AbsoluteFill>
  );
};

const Maos: React.FC<{ marca: Record<string, number> }> = ({ marca }) => {
  const t = useTempo();
  const esfrega = suave(t, marca.esfregue, marca.esfregue + 0.5);
  const quente = suave(t, marca.esfregue, marca.freioFaz);
  const vai = Math.sin(t * 18) * 70 * esfrega;
  const aDisco = suave(t, marca.freioFaz, marca.freioFaz + 0.6);
  const mao = (dir: number, dx: number) => (
    <g transform={`translate(${540 + dx} ${dir < 0 ? 1050 : 1160}) scale(${dir} 1)`}>
      <path d="M-420 -30 L-120 -60 Q-10 -70 110 -56 Q190 -46 190 -20 Q190 0 120 2 L190 14 Q230 22 220 44 Q210 66 130 60 L-120 90 L-420 80 Z" fill={`rgb(${226 + quente * 29},${172 - quente * 50},${132 - quente * 70})`} stroke="#6b3a24" strokeWidth={6} />
      <path d="M-30 -60 Q40 -130 110 -100 Q130 -84 100 -66" fill={`rgb(${226 + quente * 29},${172 - quente * 50},${132 - quente * 70})`} stroke="#6b3a24" strokeWidth={6} />
    </g>
  );
  return (
    <AbsoluteFill style={{ background: "linear-gradient(#2c1436, #a33e32 42%, #f0813c 70%, #55243b)" }}>
      <svg width={1080} height={1920} style={{ position: "absolute", opacity: 1 - aDisco, transform: "scale(1.25)", transformOrigin: "50% 57%" }}>
        <circle cx={540} cy={1100} r={120 + quente * 300} fill="#ffe08a" opacity={0.25 + quente * 0.45} style={{ filter: "blur(50px)" }} />
        {mao(1, -vai)}
        {mao(-1, vai)}
      </svg>
      <Placa de={24} ate={45} unidade="°C" inicio={marca.esfregue + 0.8} dur={1.5} x={540} y={1450} cor="#fff" />
      {aDisco > 0 && (
        <div style={{ position: "absolute", inset: 0, opacity: aDisco, background: "#06080f" }}>
          <Disco x={540} y={1000} raio={350} calor={aDisco * 0.65} giro={t * 90} />
        </div>
      )}
    </AbsoluteFill>
  );
};

const Limite: React.FC<{ marca: Record<string, number> }> = ({ marca }) => {
  const t = useTempo();
  const alvo = t < marca.quente ? 0.12 : t < marca.equipes ? 0.92 : 0.52;
  const antes = t < marca.quente ? 0.5 : t < marca.equipes ? 0.12 : 0.92;
  const inicioTroca = t < marca.quente ? marca.inicio : t < marca.equipes ? marca.quente : marca.equipes;
  const n = antes + (alvo - antes) * suave(t, inicioTroca, inicioTroca + 0.5);
  const pista = t > marca.monaco ? "MÔNACO" : t > marca.monza ? "MONZA" : null;
  return (
    <AbsoluteFill>
      <Autodromo topo="#0a0612" base="#2a1430" velocidade={0.3} horizonte={1640} />
      <Disco x={540} y={860} raio={330} calor={n} giro={t * 70} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 1290, height: 38, borderRadius: 20, background: "linear-gradient(90deg,#3b82f6 0%,#3b82f6 22%,#34d399 40%,#34d399 62%,#f97316 78%,#ef4444 100%)", border: "3px solid rgba(255,255,255,.3)" }} />
      <div style={{ position: "absolute", left: 120 + n * 840 - 16, top: 1268, width: 32, height: 82, borderRadius: 10, background: "#fff", boxShadow: "0 0 18px #fff" }} />
      <div style={{ position: "absolute", left: 120, top: 1360, color: "#9cc7ff", fontSize: 44, fontWeight: 800, fontFamily: "'Trebuchet MS',sans-serif" }}>FRIO</div>
      <div style={{ position: "absolute", right: 120, top: 1360, color: "#ff8a6a", fontSize: 44, fontWeight: 800, fontFamily: "'Trebuchet MS',sans-serif" }}>QUENTE</div>
      {pista && <Placa key={pista} texto={pista} inicio={pista === "MÔNACO" ? marca.monaco : marca.monza} x={540} y={1530} cor="#ffd21f" tam={84} />}
    </AbsoluteFill>
  );
};

const Pedal: React.FC<{ marca: Record<string, number> }> = ({ marca }) => {
  const t = useTempo();
  const f = suave(t, marca.empurra, marca.empurra + 0.7) * (t > marca.leg ? 0.9 + 0.1 * Math.sin(t * 7) : 1);
  const a = 18 - f * 22;
  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 58%, #2b3346, #070a12 70%)" }}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", transform: "scale(1.3)", transformOrigin: "62% 62%" }}>
        <g transform={`translate(760 1420) rotate(${a})`}>
          <rect x={-26} y={-430} width={52} height={460} rx={16} fill="#c8ccd3" stroke="#14161c" strokeWidth={5} />
          <rect x={-90} y={-470} width={120} height={70} rx={14} fill="#14161c" stroke="#ffd21f" strokeWidth={6} />
        </g>
        <circle cx={760} cy={1420} r={36} fill="#3a3f4b" stroke="#c8ccd3" strokeWidth={8} />
        <g transform={`translate(${f * 96} ${-f * 24})`}>
          <path d="M-60 930 L420 900 Q560 900 620 960 L650 1040 Q640 1090 560 1078 L400 1060 L-60 1140 Z" fill="#c7281c" stroke="#3e0b07" strokeWidth={6} />
          <path d="M540 880 L664 926 Q690 940 680 975 L650 1080 Q640 1100 610 1090 L520 1040 Z" fill="#14161c" />
        </g>
      </svg>
      <Placa de={0} ate={100} prefixo="+" unidade="kg" inicio={marca.cem} dur={0.7} x={340} y={1320} tam={108} />
      {t > marca.nenhuma && t < marca.empurra && <Placa texto="SEM ASSISTÊNCIA" inicio={marca.nenhuma} x={540} y={1500} cor="#ff6a3d" tam={60} />}
    </AbsoluteFill>
  );
};

const Fim: React.FC<{ inicio: number }> = ({ inicio }) => {
  const t = useTempo();
  return (
    <AbsoluteFill style={{ background: "#06080f" }}>
      <Disco x={540} y={1050} raio={430} calor={0.95 + Math.sin(t * 3) * 0.05} giro={t * 60} />
      <Placa ate={1000} prefixo="+" unidade="°C" inicio={inicio + 0.3} x={540} y={1580} />
    </AbsoluteFill>
  );
};

export const FreioF1: React.FC<Props> = ({ palavras }) => {
  const { fps } = useVideoConfig();
  const em = (trecho: string, apos = 0) => noTrecho(palavras, trecho, apos);
  const c1 = em("O segredo"), c2 = em("Frear é"), c3 = em("Quando o piloto"), c4 = em("Mas o limite"), c5 = em("E esse pedal"), c6 = em("Por isso quando");
  const fim = palavras[palavras.length - 1].f + 0.5;
  const trecho = (de: number, ate: number, no: React.ReactNode) => (
    <Sequence from={Math.round(de * fps)} durationInFrames={Math.round((ate - de) * fps)} layout="none">
      <div style={{ position: "absolute", inset: 0 }}>{no}</div>
    </Sequence>
  );
  return (
    <AbsoluteFill style={{ background: "#06080f" }}>
      <Audio src={staticFile("f1-freio/voz.wav")} />
      <Cena de={0} ate={c1}><Abertura marca={{ sai: em("ele sai"), hora: em("hora"), tres: em("três segundos"), forca: em("A força"), cinco: em("cinco vezes"), fim: c1 }} /></Cena>
      <Cena de={c1} ate={c2}><Carbono marca={{ prato: em("prato"), aco: em("aço"), aqui: em("Aqui é"), frio: em("frio o carbono") }} /></Cena>
      <Cena de={c2} ate={c3}><Maos marca={{ esfregue: em("Esfregue"), freioFaz: em("O freio faz") }} /></Cena>
      {trecho(c3, c4, <OffthreadVideo src={staticFile("f1-freio/freio3d.mp4")} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />)}
      <Cena de={em("seis pistões")} ate={em("O carbono")}><Placa ate={6} unidade="pistões" inicio={em("seis pistões")} x={540} y={1650} cor="#7fdcff" /></Cena>
      <Cena de={em("mil graus")} ate={em("E mais")}><Placa de={200} ate={1000} prefixo="+" unidade="°C" inicio={em("mil graus")} dur={1.4} x={540} y={1650} /></Cena>
      <Cena de={em("mil furinhos")} ate={c4}><Placa ate={1000} prefixo="+" unidade="furinhos" inicio={em("mil furinhos")} x={540} y={1650} cor="#7fdcff" /></Cena>
      <Cena de={c4} ate={c5}><Limite marca={{ inicio: c4, quente: em("Quente demais"), equipes: em("as equipes"), monza: em("Monza"), monaco: em("Mônaco") }} /></Cena>
      <Cena de={c5} ate={c6}><Pedal marca={{ nenhuma: em("nenhuma"), empurra: em("empurra"), cem: em("cem quilos"), leg: em("leg press") }} /></Cena>
      <Cena de={c6} ate={fim}><Fim inicio={c6} /></Cena>
      <Legenda palavras={palavras} chaves={CHAVES} />
    </AbsoluteFill>
  );
};

/** Mostra a cena só no trecho dela, sem zerar o tempo: tudo na cena é preso às palavras no tempo do vídeo inteiro. */
const Cena: React.FC<{ de: number; ate: number; children: React.ReactNode }> = ({ de, ate, children }) => {
  const t = useTempo();
  return t >= de && t < ate ? <>{children}</> : null;
};
