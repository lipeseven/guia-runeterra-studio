// Piloto "Como funciona o freio de um F1?". O disco é o objeto que atravessa o vídeo e muda de estado com a fala;
// corte técnico, comparações e pistas entram como explicações à parte. Cada mudança é presa a uma palavra do roteiro.
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { Cena, Disco, FONTE, Faiscas, FundoPista, Legenda, Placa, entra, noTrecho, suave, useTempo, type Palavra } from "./kit";

type Props = { palavras: Palavra[] };
type M = Record<string, number>;
const CHAVES = ["carbono", "calor", "pastilhas", "furinhos", "assistência", "defeito", "brilhar"];

const Heroi: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const abre = 1 - entra(t, 0, 1.4);
  const fecha = suave(t, m.forca, m.segredo);
  const esfria = suave(t, m.segredo, m.segredo + 0.8);
  const compara = suave(t, m.seuCarro, m.seuCarro + 0.5) * (1 - suave(t, m.aqui, m.aqui + 0.5));
  const aquece = suave(t, m.frear, m.esfregue);
  const calor = Math.max(0, (t < m.segredo ? 0.45 + suave(t, m.sai, m.hora) * 0.55 : 1 - esfria) + aquece * 0.72);
  const velocidade = t < m.hora ? 1.6 : t < m.segredo ? 0.8 : 0.45;
  const giro = t * 95;
  const zoom = 1 + abre * 1.05 + fecha * 0.06;
  const raio = 480 - compara * 245;
  const px = 540 + compara * 195 + abre * 290;
  const py = 1110 + abre * 350 + compara * 30;
  const kmh = 300 - (300 - 95) * suave(t, m.sai, m.hora);
  const cels = t < m.segredo ? 450 + (1000 - 450) * suave(t, m.sai, m.hora) : 20 + 700 * aquece;
  return (
    <AbsoluteFill>
      <FundoPista velocidade={velocidade} />
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: "50% 58%" }}>
        {compara > 0.01 && (
          <svg width={500} height={500} viewBox="-125 -125 250 250" style={{ position: "absolute", left: 20 - (1 - compara) * 500, top: 870 }}>
            <defs>
              <linearGradient id="aco" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#f7f9fc" /><stop offset="0.5" stopColor="#a9b1bc" /><stop offset="1" stopColor="#e4e8ee" /></linearGradient>
            </defs>
            <circle r={112} fill="url(#aco)" stroke="#5a616c" strokeWidth={2} />
            {[100, 92, 84, 76].map((r) => <circle key={r} r={r} fill="none" stroke="#8e96a2" strokeWidth={0.8} />)}
            <circle r={58} fill="#c6ccd5" stroke="#6e7581" strokeWidth={2} />
            <circle r={22} fill="#2a2e36" />
            {[0, 1, 2, 3, 4].map((k) => <circle key={k} cx={Math.cos(k * 1.257) * 40} cy={Math.sin(k * 1.257) * 40} r={7} fill="#3c4149" />)}
          </svg>
        )}
        <Disco x={px} y={py} raio={raio} calor={calor} giro={giro} />
        <Faiscas x={px + raio * 0.3} y={py - raio * 0.72} forca={t < m.segredo ? 1 - esfria : aquece * 0.5} alcance={raio * 0.95} />
      </AbsoluteFill>
      {t < m.segredo && t >= m.sai - 0.2 && (
        <>
          <Placa valor={kmh} unidade="km/h" inicio={m.sai - 0.2} x={290} y={1340} />
          <Placa valor={cels} unidade="°C" inicio={m.sai - 0.2} x={785} y={1340} cor="#ffcb5c" />
        </>
      )}
      {t >= m.cinco && t < m.segredo && <Placa texto="+5 vezes" unidade="o peso do corpo" inicio={m.cinco} x={540} y={1650} tam={64} />}
      {t >= m.prato && t < m.seuCarro && <Placa valor={278} unidade="mm" inicio={m.prato} x={540} y={1340} />}
      {compara > 0.6 && <Placa texto="seu carro" inicio={m.aco} x={270} y={1420} tam={46} />}
      {compara > 0.6 && <Placa texto="F1" inicio={m.aco} x={735} y={1420} tam={46} />}
      {t >= m.frio && t < m.frear && <Placa valor={20} unidade="°C" inicio={m.frio} x={540} y={1340} cor="#8cc8ff" />}
      {t >= m.frear && <Placa valor={cels} unidade="°C" inicio={m.frear + 0.4} x={540} y={1340} cor="#ffcb5c" />}
    </AbsoluteFill>
  );
};

const Maos: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const quente = suave(t, m.esfregue + 0.3, m.freioFaz);
  const vai = Math.sin(t * 20) * 92 * entra(t, m.esfregue, 0.4);
  const pele = `rgb(${234 + quente * 18},${178 - quente * 44},${140 - quente * 62})`;
  const sombra = `rgb(${190 + quente * 20},${126 - quente * 40},${96 - quente * 50})`;
  const mao = (cima: boolean) => (
    <g transform={`translate(${540 + (cima ? vai : -vai)} ${cima ? 1000 : 1208}) scale(${cima ? 1 : -1} ${cima ? 1 : -1})`}>
      <path d="M-760 -66 L-210 -92 Q-110 -112 40 -104 L330 -96 Q392 -92 390 -60 Q388 -32 330 -32 L150 -36 L350 -22 Q412 -16 408 18 Q402 48 340 44 L150 28 L300 58 Q352 70 342 100 Q330 126 280 114 L90 76 Q-30 104 -210 96 L-760 92 Z" fill={pele} stroke={sombra} strokeWidth={6} />
      <path d="M-140 -102 Q-60 -208 60 -190 Q118 -176 92 -146 Q40 -118 0 -100 Z" fill={pele} stroke={sombra} strokeWidth={6} />
      <path d="M150 -34 L320 -36 M150 28 L300 34" stroke={sombra} strokeWidth={4} fill="none" />
    </g>
  );
  return (
    <AbsoluteFill style={{ background: "linear-gradient(#20112c, #6d2a35 38%, #c75a2d 66%, #2b1420)" }}>
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        <circle cx={540} cy={1105} r={180 + quente * 380} fill="#ffd27a" opacity={0.12 + quente * 0.42} style={{ filter: "blur(70px)" }} />
        {mao(false)}
        {mao(true)}
      </svg>
      <Faiscas x={500} y={1105} forca={quente * 0.7} angulo={0} alcance={500} n={26} semente="m" />
      <Faiscas x={560} y={1105} forca={quente * 0.7} angulo={3.14} alcance={500} n={26} semente="n" />
    </AbsoluteFill>
  );
};

const Corte: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const p = suave(t, m.apertam - 0.1, m.pastilhas);
  const calor = suave(t, m.pastilhas, m.carbono);
  const abre = 28 * (1 - p);
  const rola = t * 900;
  const larg = 200;
  const lado = (s: number) => {
    const x = (d: number) => 540 + s * d;
    return (
      <g>
        {[0, 1, 2].map((k) => {
          const y = 690 + k * 300;
          return (
            <g key={k}>
              <rect x={Math.min(x(286), x(540))} y={y} width={254} height={210} fill={p > 0.03 ? "#f59a23" : "#1a1c22"} opacity={0.2 + p * 0.8} />
              <rect x={Math.min(x(240 + abre), x(240 + abre + 200))} y={y + 4} width={200} height={202} rx={6} fill="url(#pist)" stroke="#3c4048" strokeWidth={3} />
              <rect x={Math.min(x(240 + abre), x(240 + abre + 200))} y={y + 170} width={200} height={36} fill="#555b65" />
              <rect x={Math.min(x(220 + abre), x(220 + abre + 18))} y={y - 4} width={18} height={218} fill="#eceef1" />
              <rect x={Math.min(x(130 + abre), x(130 + abre + 90))} y={y} width={90} height={210} fill="url(#past)" stroke={calor > 0.2 ? "#ff5a18" : "#2a2d33"} strokeWidth={calor > 0.2 ? 5 : 2} />
            </g>
          );
        })}
        {[0, 1].map((k) => <rect key={k} x={Math.min(x(286), x(540))} y={900 + k * 300} width={254} height={90} fill={p > 0.5 ? "#ff4a1e" : "#b32024"} />)}
        <path d={`M${x(286)} 1530 L${x(540)} 1530 L${x(540)} 1590 Q${x(540)} 1630 ${x(500)} 1630 L${x(320)} 1630 Q${x(286)} 1630 ${x(286)} 1590 Z`} fill="url(#verm)" />
        <rect x={Math.min(x(300), x(540))} y={625} width={240} height={65} fill="#a71b20" />
      </g>
    );
  };
  return (
    <AbsoluteFill style={{ background: "#07080c" }}>
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        <defs>
          <linearGradient id="pist" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#a8aeb7" /><stop offset="0.3" stopColor="#fbfcfd" /><stop offset="0.65" stopColor="#c4c9d1" /><stop offset="1" stopColor="#7d838d" /></linearGradient>
          <linearGradient id="verm" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#e92c2e" /><stop offset="1" stopColor="#a31217" /></linearGradient>
          <pattern id="past" width="16" height="16" patternUnits="userSpaceOnUse"><rect width="16" height="16" fill="#1a1712" /><circle cx="4" cy="5" r="2.2" fill="#3a3224" /><circle cx="12" cy="11" r="2.8" fill="#4b3f2a" /></pattern>
          <linearGradient id="fundoDisco" x1="0" x2="1"><stop offset="0" stopColor="#090a0d" /><stop offset="0.5" stopColor="#23262e" /><stop offset="1" stopColor="#090a0d" /></linearGradient>
        </defs>
        <rect x={540 - larg / 2 + 15} y={0} width={larg - 30} height={1920} fill="url(#fundoDisco)" />
        <rect x={540 - larg / 2 + 15} y={0} width={larg - 30} height={1920} fill="#d6491a" opacity={calor * 0.62} />
        {Array.from({ length: 22 }, (_, k) => <rect key={k} x={540 - 55} y={((k * 115 + rola) % 2530) - 300} width={110} height={18} fill="#000" opacity={0.55} />)}
        {Array.from({ length: 34 }, (_, k) => {
          const x = 450 + (k * 53) % 180;
          const y = (((k * 197) % 2100) + rola * (0.9 + (k % 4) * 0.2)) % 2100 - 100;
          return <line key={k} x1={x} y1={y} x2={x} y2={y - 60 - (k % 5) * 18} stroke="#a7d4ff" strokeWidth={2.4} opacity={0.72} />;
        })}
        {lado(1)}
        {lado(-1)}
        <rect x={0} y={560} width={1080} height={70} rx={8} fill="url(#verm)" />
        <rect x={0} y={560} width={1080} height={14} fill="#ff8d8a" opacity={0.42} />
        {[60, 1020].map((x) => <g key={x}><circle cx={x} cy={595} r={18} fill="#e8ebef" /><circle cx={x} cy={595} r={8} fill="#3c4048" /></g>)}
      </svg>
      <Faiscas x={420} y={1590} forca={calor} angulo={1.9} alcance={280} n={26} semente="c1" />
      <Faiscas x={660} y={1590} forca={calor} angulo={1.2} alcance={280} n={26} semente="c2" />
    </AbsoluteFill>
  );
};

const Furos: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const z = entra(t, m.mil, 0.9);
  return (
    <AbsoluteFill style={{ background: "#07080c" }}>
      <FundoPista velocidade={0.6} matiz="#07080c" />
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        <defs><linearGradient id="fur" x1="0" x2="1"><stop offset="0" stopColor="#f9c24e" /><stop offset="1" stopColor="#d66a14" /></linearGradient></defs>
        <g transform={`translate(${-250 - z * 120} 0)`}>
          <path d="M0 0 H470 Q640 960 470 1920 H0 Z" fill="#f0d9bb" />
          <path d="M470 0 Q640 960 470 1920 H820 Q1000 960 820 0 Z" fill="url(#fur)" />
          {Array.from({ length: 7 }, (_, c) => Array.from({ length: 26 }, (_, k) => {
            const y = ((k * 88 + c * 44 + t * 170) % 2288) - 100;
            const curva = 170 * (1 - Math.pow((y - 960) / 1000, 2));
            return <ellipse key={`${c}-${k}`} cx={520 + c * 48 + curva} cy={y} rx={13 - c * 0.5} ry={21} fill="#2c1403" />;
          }))}
        </g>
      </svg>
      {Array.from({ length: 16 }, (_, k) => {
        const v = (t * 1.3 + k * 0.137) % 1;
        const y = 620 + (k * 83) % 980;
        return <div key={k} style={{ position: "absolute", left: 1080 - v * 560, top: y, width: 150, height: 5, borderRadius: 3, opacity: suave(t, m.puxam - 0.3, m.puxam) * (1 - v * 0.6), background: "linear-gradient(90deg,#ffffff,#7fcbff00)", boxShadow: "0 0 10px #8fd4ff" }} />;
      })}
      <Placa valor={1000} prefixo="+" unidade="furinhos" inicio={m.mil + 0.1} x={660} y={1010} cor="#d7efff" tam={82} />
    </AbsoluteFill>
  );
};

const Limite: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const frio = suave(t, m.frioDemais - 0.2, m.frioDemais + 0.3);
  const quente = suave(t, m.quente - 0.15, m.quente + 0.4);
  const calor = 0.68 - frio * 0.62 + quente * 0.94;
  const cels = 700 - frio * 500 + quente * 700;
  return (
    <AbsoluteFill>
      <FundoPista velocidade={0.8} />
      <Disco x={540} y={1110} raio={480} calor={calor} giro={t * 95} id="l" />
      <Faiscas x={684} y={765} forca={Math.max(quente, m.frioDemais > 1e8 ? 0.6 : 0)} alcance={460} semente="l" />
      <Placa valor={cels} unidade="°C" inicio={m.inicio} x={540} y={1340} cor={quente > 0.3 ? "#ff8a4c" : frio > 0.5 ? "#8cc8ff" : "#ffcb5c"} />
      {t >= m.frioDemais && t < m.quente && <Placa texto="não para" inicio={m.para} x={540} y={1660} cor="#8cc8ff" tam={60} />}
      {t >= m.gasta && <Placa texto="gasta em minutos" inicio={m.gasta} x={540} y={1660} cor="#ff8a4c" tam={60} />}
    </AbsoluteFill>
  );
};

/** Trecho de pista visto de cima, com o carro correndo pelo traçado até a freada. */
const Pista: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const monaco = t >= m.monaco;
  const nome = monaco ? "Mônaco" : "Monza";
  const traco: [number, number][] = monaco
    ? [[1010, 1760], [860, 1640], [780, 1400], [860, 1120], [930, 900], [740, 700], [500, 770], [520, 1010], [340, 1190], [190, 1040], [120, 650]]
    : [[540, 1960], [540, 1500], [540, 1120], [540, 880], [620, 720], [470, 610], [540, 470], [540, 200]];
  const inicio = monaco ? m.monaco : t >= m.monza ? m.monza : m.equipes;
  const u = suave(t, inicio, inicio + (monaco ? 2.4 : t >= m.monza ? 1.9 : 3)) * (traco.length - 1.02);
  const a = traco[Math.floor(u)];
  const b = traco[Math.floor(u) + 1];
  const k = u - Math.floor(u);
  const cx = a[0] + (b[0] - a[0]) * k;
  const cy = a[1] + (b[1] - a[1]) * k;
  const ang = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI + 90;
  const caminho = traco.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ");
  return (
    <AbsoluteFill style={{ background: "linear-gradient(#0a1f15,#0d2a1b)" }}>
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        {Array.from({ length: 70 }, (_, q) => <circle key={q} cx={(q * 167) % 1080} cy={(q * 293) % 1920} r={6 + q % 12} fill="#134a2a" opacity={0.5} />)}
        <g strokeLinejoin="round" strokeLinecap="round" fill="none">
          <path d={caminho} stroke="#f4f4f5" strokeWidth={236} />
          <path d={caminho} stroke="#d62733" strokeWidth={236} strokeDasharray="46 46" />
          <path d={caminho} stroke="#f7f7f8" strokeWidth={204} />
          <path d={caminho} stroke="#2a2d33" strokeWidth={192} />
          <path d={caminho} stroke="#ffffff" strokeWidth={3} strokeDasharray="34 46" opacity={0.4} />
        </g>
        <g transform={`translate(${cx} ${cy}) rotate(${ang}) scale(1.35)`}>
          <path d="M-9 -58 L9 -58 L12 -14 L26 8 L26 42 L-26 42 L-26 8 L-12 -14 Z" fill="#e5311d" stroke="#3b0805" strokeWidth={3} />
          <rect x={-36} y={-44} width={72} height={10} rx={3} fill="#111" />
          <rect x={-36} y={48} width={72} height={10} rx={3} fill="#e5311d" />
          {[[-34, -30], [34, -30], [-36, 32], [36, 32]].map(([x, y], q) => <rect key={q} x={x - 8} y={y - 15} width={16} height={30} rx={4} fill="#0c0d10" />)}
          <circle r={9} cy={4} fill="#ffd21f" stroke="#111" strokeWidth={2} />
        </g>
      </svg>
      {t >= m.monza && <Placa key={nome} texto={nome} inicio={inicio} x={540} y={1500} tam={86} cor="#fff" />}
      {t >= m.freadas && t < m.monaco && <Placa texto="freadas violentas" inicio={m.freadas} x={540} y={1640} tam={50} cor="#ff8a4c" />}
      {t >= m.quase && <Placa texto="quase sem reta" inicio={m.quase} x={540} y={1640} tam={50} cor="#8cc8ff" />}
    </AbsoluteFill>
  );
};

const Pedal: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const f = suave(t, m.empurra - 0.1, m.empurra + 0.5);
  const a = 13 - f * 19;
  const pesos = [0, 1, 2, 3].map((k) => entra(t, m.cem + k * 0.2, 0.3));
  return (
    <AbsoluteFill style={{ background: "#101018" }}>
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        <defs>
          <pattern id="xadrez" width="72" height="72" patternUnits="userSpaceOnUse"><rect width="72" height="72" fill="#15151e" /><rect width="36" height="36" fill="#1e1e2a" /><rect x="36" y="36" width="36" height="36" fill="#1e1e2a" /></pattern>
          <radialGradient id="luzP" cx="0.3" cy="0.35"><stop offset="0" stopColor="#8a5a22" stopOpacity="0.55" /><stop offset="1" stopColor="#101018" stopOpacity="0" /></radialGradient>
          <linearGradient id="perna" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#f0323a" /><stop offset="1" stopColor="#8a0c13" /></linearGradient>
          <linearGradient id="pedal" x1="0" x2="1"><stop offset="0" stopColor="#7c828c" /><stop offset="0.5" stopColor="#f4f6f8" /><stop offset="1" stopColor="#868c96" /></linearGradient>
          <linearGradient id="anilha" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#40434c" /><stop offset="0.5" stopColor="#6e727c" /><stop offset="1" stopColor="#25272d" /></linearGradient>
        </defs>
        <rect width={1080} height={1920} fill="url(#xadrez)" />
        <rect width={1080} height={1920} fill="url(#luzP)" />
        <g transform={`translate(835 1680) rotate(${a})`}>
          <rect x={-34} y={-880} width={68} height={920} rx={12} fill="url(#pedal)" stroke="#262930" strokeWidth={4} />
          {Array.from({ length: 11 }, (_, k) => <ellipse key={k} cx={0} cy={-810 + k * 72} rx={13} ry={25} fill="#16181e" />)}
          <rect x={-34} y={-790} width={68} height={280} rx={8} fill="#1b1d23" stroke="#ff8a2a" strokeWidth={5} />
          {Array.from({ length: 5 }, (_, k) => <rect key={k} x={-24} y={-770 + k * 50} width={48} height={22} rx={5} fill="#6b7079" />)}
        </g>
        <circle cx={835} cy={1680} r={50} fill="#3a3f4b" stroke="#d6dae0" strokeWidth={10} />
        <g transform={`translate(${f * 100} ${f * -6})`}>
          <path d="M-160 700 Q240 690 440 880" fill="none" stroke="#55070c" strokeWidth={232} strokeLinecap="round" />
          <path d="M-160 700 Q240 690 440 880" fill="none" stroke="url(#perna)" strokeWidth={222} strokeLinecap="round" />
          <path d="M-160 650 Q220 640 420 800" fill="none" stroke="#ff8d8a" strokeWidth={12} strokeLinecap="round" opacity={0.45} />
          <path d="M470 770 L720 900 L735 1140 Q680 1210 620 1160 L560 1060 L470 1000 Z" fill="#14151a" stroke="#34363e" strokeWidth={5} />
          <path d="M520 1000 Q610 1020 680 1130" stroke="#e5311d" strokeWidth={22} fill="none" strokeLinecap="round" />
        </g>
        {pesos.map((p, k) => (
          <g key={k} opacity={p} transform={`translate(${250 + k * 74} ${1380 - (1 - p) * 180})`}>
            <rect x={0} y={-160} width={58} height={320} rx={14} fill="url(#anilha)" stroke="#111" strokeWidth={3} />
            <text x={29} y={12} textAnchor="middle" fill="#fff" fontFamily={FONTE} fontSize={24} fontWeight={800}>25</text>
          </g>
        ))}
        {pesos[0] > 0 && <rect x={190} y={1370} width={420} height={20} rx={10} fill="#a8adb6" opacity={pesos[0]} />}
      </svg>
      {t >= m.nenhuma && t < m.empurra && <Placa texto="sem assistência" inicio={m.nenhuma} x={500} y={1640} cor="#ff8a4c" tam={60} />}
      {t >= m.cem && <Placa valor={100} prefixo="+" unidade="kg" inicio={m.cem} x={395} y={1630} cor="#ffcb5c" tam={100} />}
    </AbsoluteFill>
  );
};

const Fim: React.FC<{ m: M }> = ({ m }) => {
  const t = useTempo();
  const abre = entra(t, m.inicio, 1.2);
  return (
    <AbsoluteFill>
      <FundoPista velocidade={1.2} />
      <AbsoluteFill style={{ transform: `scale(${2.05 - abre * 1.05})`, transformOrigin: `${50 + (1 - abre) * 20}% ${58 + (1 - abre) * 15}%` }}>
        <Disco x={540} y={1110} raio={480} calor={0.97 + Math.sin(t * 3) * 0.03} giro={t * 95} id="z" />
        <Faiscas x={684} y={765} forca={0.9} alcance={460} semente="z" />
      </AbsoluteFill>
      <Placa valor={1000} prefixo="+" unidade="°C" inicio={m.inicio + 0.7} x={540} y={1340} cor="#ffcb5c" />
    </AbsoluteFill>
  );
};

export const FreioF1: React.FC<Props> = ({ palavras }) => {
  const em = (trecho: string, apos = 0) => noTrecho(palavras, trecho, apos);
  const c1 = em("O segredo"), c2 = em("Frear é"), c3 = em("Quando o piloto"), c4 = em("Mas o limite"), c5 = em("E esse pedal"), c6 = em("Por isso quando");
  const esfregue = em("Esfregue"), freioFaz = em("O freio faz"), carbono = em("O carbono", c3), furinhos = em("E mais de mil"), equipes = em("as equipes");
  const fim = palavras[palavras.length - 1].f + 0.5;
  const heroi = { sai: em("ele sai"), hora: em("hora"), forca: em("A força"), cinco: em("cinco vezes"), segredo: c1, prato: em("prato"), seuCarro: em("No seu carro"), aco: em("aço"), aqui: em("Aqui é"), frio: em("frio o carbono"), frear: c2, esfregue };
  return (
    <AbsoluteFill style={{ background: "#0b0c11" }}>
      <Audio src={staticFile("f1-freio/voz.wav")} />
      <Cena de={0} ate={esfregue}><Heroi m={heroi} /></Cena>
      <Cena de={esfregue} ate={freioFaz}><Maos m={{ esfregue, freioFaz }} /></Cena>
      <Cena de={freioFaz} ate={c3}><Limite m={{ inicio: freioFaz, frioDemais: 1e9, quente: 1e9, para: 1e9, gasta: 1e9 }} /></Cena>
      <Cena de={c3} ate={carbono}><Corte m={{ apertam: em("apertam"), pastilhas: em("pastilhas"), carbono }} /></Cena>
      <Cena de={carbono} ate={furinhos}><Fim m={{ inicio: carbono }} /></Cena>
      <Cena de={furinhos} ate={c4}><Furos m={{ mil: furinhos, puxam: em("puxam") }} /></Cena>
      <Cena de={c4} ate={equipes}><Limite m={{ inicio: c4, frioDemais: em("Frio demais"), para: em("não para"), quente: em("Quente demais"), gasta: em("se gasta") }} /></Cena>
      <Cena de={equipes} ate={c5}><Pista m={{ equipes, monza: em("Monza"), freadas: em("freadas são"), monaco: em("Mônaco"), quase: em("quase não há") }} /></Cena>
      <Cena de={c5} ate={c6}><Pedal m={{ nenhuma: em("nenhuma"), empurra: em("empurra"), cem: em("cem quilos") }} /></Cena>
      <Cena de={c6} ate={fim}><Fim m={{ inicio: c6 }} /></Cena>
      <Legenda palavras={palavras} chaves={CHAVES} />
    </AbsoluteFill>
  );
};
