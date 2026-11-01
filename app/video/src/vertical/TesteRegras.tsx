// Cena de teste do tema "regras da F1": bandeira amarela e Safety Car, numa pista em perspectiva.
// A pista é um plano com perspectiva real; a câmera anda por ela e tudo é preso às palavras da narração.
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { CarroCima, FONTE, Legenda, Placa, entra, noTrecho, suave, useTempo, type Palavra, type Pintura } from "./kit";

const PINTURAS: Pintura[] = [
  { base: "#14a38b", escuro: "#07564a", faixa: "#f4efe0" },
  { base: "#f26a21", escuro: "#8f340a", faixa: "#14202e" },
  { base: "#2f55d4", escuro: "#132a78", faixa: "#ffd21f" },
  { base: "#e9ecf1", escuro: "#8c93a0", faixa: "#d4213c" },
  { base: "#8a3fd1", escuro: "#431a6f", faixa: "#46e0c8" },
  { base: "#c8102e", escuro: "#6a0515", faixa: "#f5f5f5" },
  { base: "#1b1e26", escuro: "#07080c", faixa: "#b8f000" },
  { base: "#ffb000", escuro: "#a45f00", faixa: "#131313" },
];
const SC: Pintura = { base: "#e8edf2", escuro: "#7f8896", faixa: "#ff8a00", asa: "#2a2f39" };

const L = 6000; // comprimento do plano da pista
const LARG = 760; // largura do asfalto

const Bandeira: React.FC<{ x: number; y: number; forca: number; escala?: number }> = ({ x, y, forca, escala = 1 }) => {
  const t = useTempo();
  if (forca <= 0) return null;
  const ondas = Array.from({ length: 13 }, (_, k) => k * 40);
  const onda = (u: number, d: number) => Math.sin(u * 0.028 + t * 9 + d) * (8 + u * 0.09);
  const cima = ondas.map((u) => `${u} ${onda(u, 0)}`).join(" L");
  const baixo = [...ondas].reverse().map((u) => `${u} ${240 + onda(u, 0.5)}`).join(" L");
  return (
    <svg width={760} height={720} viewBox="-60 -120 760 720" style={{ position: "absolute", left: x, top: y, overflow: "visible", opacity: forca, transform: `scale(${escala * (0.86 + forca * 0.14)})`, transformOrigin: "60px 120px", zIndex: 30 }}>
      <defs>
        <linearGradient id="pano" x1="0" x2="1" y1="0" y2="0.25"><stop offset="0" stopColor="#ffd400" /><stop offset="0.35" stopColor="#ffe65a" /><stop offset="0.6" stopColor="#f4b800" /><stop offset="1" stopColor="#ffdc2e" /></linearGradient>
        <linearGradient id="mastro" x1="0" x2="1"><stop offset="0" stopColor="#6e7682" /><stop offset="0.5" stopColor="#f3f5f8" /><stop offset="1" stopColor="#7c8490" /></linearGradient>
      </defs>
      <rect x={-14} y={-60} width={14} height={640} rx={6} fill="url(#mastro)" />
      <path d={`M${cima} L${baixo} Z`} fill="url(#pano)" stroke="#a87900" strokeWidth={2.5} style={{ filter: "drop-shadow(0 16px 28px rgba(0,0,0,.45))" }} />
    </svg>
  );
};

export const TesteRegras: React.FC<{ palavras: Palavra[] }> = ({ palavras }) => {
  const t = useTempo();
  const em = (x: string, apos = 0) => noTrecho(palavras, x, apos);
  const amarela = em("bandeira amarela"), reduz = em("reduz"), serio = em("Se for"), sc = em("safety car"), fila = em("A fila"), vant = em("a vantagem");
  const fim = palavras[palavras.length - 1].f;

  // câmera: abertura rápida recuando pelo grid, depois acompanha o pelotão
  const abre = suave(t, 0, 1.15);
  const zona = suave(t, sc - 0.35, sc + 0.5);
  const avanço = t * 620 * (1 - suave(t, reduz, serio) * 0.55);
  const foco = L - 500 - avanço - (1 - abre) * 2300 - zona * 170;
  const inclina = 62 - (1 - abre) * 16 + suave(t, fila, fila + 1) * 5;
  const alto = 1 + (1 - abre) * 1.25 - zona * 0.1 - suave(t, fila, fila + 1.2) * 0.13;

  // pelotão: o intervalo entre os carros cai quando a fila se aperta
  const aperta = suave(t, fila + 0.1, vant + 0.9);
  const passo = 400 - aperta * 170;
  const lentos = suave(t, reduz, serio);
  const vezDoSc = entra(t, sc - 0.1, 0.9);
  const yLider = foco - 980;
  const ySc = yLider - 400 - (1 - vezDoSc) * 1300;
  const pisca = Math.sin(t * 26) > 0;
  const amareloNaPista = entra(t, amarela, 0.35) * (1 - suave(t, sc, sc + 0.6));
  const lista = PINTURAS.map((p, k) => ({ p, k, y: yLider + k * passo, x: 540 + [-90, 110, -130, 60, -40, 130, -110, 30][k] * (1 - aperta) + (k % 2 ? 62 : -62) * aperta }));
  const vantagem = 12.4 - 11.6 * suave(t, vant, vant + 0.9);

  return (
    <AbsoluteFill style={{ background: "#0a1420", overflow: "hidden" }}>
      <Audio src={staticFile("f1-teste/voz.wav")} />
      {/* céu ao amanhecer: cor do canal */}
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(#0b1a33 0%, #1c426a 16%, #7a7486 25%, #e0a06d 31%, #f4bf7a 34%, #15312b 35%)" }} />
      <AbsoluteFill style={{ perspective: 1050, perspectiveOrigin: "50% 30%" }}>
        <div style={{ position: "absolute", left: 540 - 1600, top: 1390 - foco, width: 3200, height: L, transformOrigin: `1600px ${foco}px`, transform: `rotateX(${inclina}deg) scale(${alto})`, background: "#1c5832" }}>
          {/* área de escape, zebra, asfalto, linhas */}
          <div style={{ position: "absolute", left: 1600 - LARG / 2 - 210, width: LARG + 420, top: 0, bottom: 0, background: "#c9a97a" }} />
          <div style={{ position: "absolute", left: 1600 - LARG / 2 - 62, width: LARG + 124, top: 0, bottom: 0, background: "repeating-linear-gradient(0deg,#d8283a 0 110px,#f4f4f4 110px 220px)" }} />
          <div style={{ position: "absolute", left: 1600 - LARG / 2, width: LARG, top: 0, bottom: 0, background: "linear-gradient(90deg,#3a3d46,#4b4d57 30%,#555660 50%,#4b4d57 70%,#3a3d46)" }} />
          <div style={{ position: "absolute", left: 1600 - LARG / 2, width: LARG, top: 0, bottom: 0, opacity: 0.42, background: "repeating-linear-gradient(0deg,transparent 0 34px,rgba(0,0,0,.2) 34px 37px),repeating-linear-gradient(90deg,transparent 0 58px,rgba(255,255,255,.05) 58px 60px)" }} />
          {[-1, 1].map((s) => <div key={s} style={{ position: "absolute", left: 1600 + s * (LARG / 2 - 16) - 7, width: 14, top: 0, bottom: 0, background: "#f4f4f4" }} />)}
          {/* trecho amarelo na pista: "aqui ninguém ultrapassa" */}
          <div style={{ position: "absolute", left: 1600 - LARG / 2, width: LARG, top: foco - 2600, height: 3000, opacity: amareloNaPista * 0.1, background: "#ffd400" }} />
          {[-1, 1].map((s) => <div key={s} style={{ position: "absolute", left: 1600 + s * (LARG / 2 - 16) - 11, width: 22, top: foco - 2600, height: 3000, opacity: amareloNaPista, background: "#ffd400", boxShadow: "0 0 40px 10px rgba(255,212,0,.6)" }} />)}
          {/* carros */}
          {lista.map(({ p, k, x, y }) => {
            const eixo = 1600 + (x - 540);
            return (
              <div key={k} style={{ position: "absolute", left: eixo - 75, top: y - 160, transform: "scale(1.2)" }}>
                <CarroCima p={p} id={`c${k}`} capacete={k % 2 ? "#f4f4f4" : "#ffd21f"} />
                <div style={{ position: "absolute", left: 150, top: 110, color: "#fff", fontFamily: FONTE, fontSize: 56, fontWeight: 800, opacity: 1 - lentos, transform: "rotate(0deg)" }}>{k + 1}</div>
              </div>
            );
          })}
          {/* safety car */}
          <div style={{ position: "absolute", left: 1600 - 75, top: ySc - 160, transform: "scale(1.2)" }}>
            <CarroCima p={SC} id="sc" capacete="#ff8a00" />
            <div style={{ position: "absolute", left: 22, top: 148, width: 106, height: 18, borderRadius: 6, background: "#14171d", boxShadow: "0 0 0 2px #333" }}>
              <div style={{ position: "absolute", left: 4, top: 3, width: 44, height: 12, background: pisca ? "#ffb300" : "#4d3a00", boxShadow: pisca ? "0 0 46px 20px rgba(255,170,0,.75)" : "none" }} />
              <div style={{ position: "absolute", right: 4, top: 3, width: 44, height: 12, background: pisca ? "#4d3a00" : "#ffb300", boxShadow: pisca ? "none" : "0 0 46px 20px rgba(255,170,0,.75)" }} />
            </div>
          </div>
        </div>
      </AbsoluteFill>
      {/* névoa no horizonte */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, height: 200, background: "linear-gradient(rgba(242,181,107,0), rgba(242,181,107,.42) 45%, rgba(242,181,107,0))", zIndex: 5 }} />
      {/* bandeira em primeiro plano, só enquanto a fala é dela */}
      <Bandeira x={120} y={760} escala={0.72} forca={entra(t, amarela - 0.05, 0.3) * (1 - suave(t, serio - 0.2, serio + 0.15))} />
      <Placa texto="NÃO ULTRAPASSE" inicio={reduz + 0.5} ate={serio - 0.1} x={540} y={1720} tam={64} cor="#ffd400" />
      {/* painel SC */}
      {t >= sc - 0.05 && (
        <div style={{ position: "absolute", left: "50%", top: 500, zIndex: 40, transform: `translateX(-50%) scale(${0.7 + entra(t, sc, 0.3) * 0.3})`, opacity: entra(t, sc, 0.2) * (1 - entra(t, vant - 0.15, 0.25)), background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00" }}>SC</div>
      )}
      {/* vantagem do líder: cai até quase zero */}
      <Placa texto={`${vantagem.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`} unidade="s de vantagem" inicio={fila + 0.3} x={540} y={1710} cor={vantagem < 2 ? "#ff5a4a" : "#ffffff"} tam={84} />
      <Legenda palavras={palavras} chaves={["amarela", "ultrapassa", "safety", "vantagem"]} />
      <AbsoluteFill style={{ background: "#000", opacity: suave(t, fim + 0.1, fim + 0.5), zIndex: 60 }} />
    </AbsoluteFill>
  );
};
