// Ficha de dados desenhada (canal Pokémon): arte oficial no branco + número, nome, categoria, tipos, altura/peso e
// barras de stats — limpa e legível (os canais de referência colam prints da Bulbapedia). Os dados vêm da Pokédex
// local (tools/pokemon/pokedex.py), preenchidos pela montagem. Textos entram secos (regra do canal); só as barras
// e a arte se mexem.
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Figura } from "../componentes/Figura";
import { transformMovimento, type Movimento } from "../efeitos";
import { fonte } from "../estilo";
import type { Midia } from "../tipos";

export type DadosFicha = {
  numero: number;
  nome: string;
  categoria?: string;
  tipos: string[];
  altura_m?: number;
  peso_kg?: number;
  regiao?: string;
  stats: Record<string, number>;
};
export type CenaFicha = { tipo: "ficha"; de: number; ate: number; midia?: Midia; dados: DadosFicha; movimento?: Movimento };

// cores oficiais dos tipos (padrão dos jogos)
const COR_TIPO: Record<string, string> = {
  Normal: "#9FA19F", Fogo: "#E62829", Água: "#2980EF", Planta: "#3FA129", Elétrico: "#FAC000", Gelo: "#3DCEF3",
  Lutador: "#FF8000", Venenoso: "#9141CB", Terrestre: "#915121", Voador: "#81B9EF", Psíquico: "#EF4179",
  Inseto: "#91A119", Pedra: "#AFA981", Fantasma: "#704170", Dragão: "#5060E1", Sombrio: "#624D4E", Aço: "#60A1B8",
  Fada: "#EF70EF",
};

export const Ficha: React.FC<{ cena: CenaFicha; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const d = cena.dados;
  const p = interpolate(frame, [0, duracao], [0, 1], { extrapolateRight: "clamp" });
  const cor = COR_TIPO[d.tipos[0]] ?? "#444";
  const stats = Object.entries(d.stats);
  const total = stats.reduce((s, [, v]) => s + v, 0);
  const texto: React.CSSProperties = { fontFamily: fonte.rotulo, color: "#111" };
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {/* faixa da cor do tipo atrás da arte */}
      <div style={{ position: "absolute", left: 0, top: 0, width: 860, height: 1080, background: `${cor}1f` }} />
      {cena.midia && (
        <div style={{ position: "absolute", left: 60, top: 140, width: 740, height: 800 }}>
          <Figura midia={cena.midia} largura={740} altura={800} ajuste="contain" style={{ transform: transformMovimento(cena.movimento, p) }} />
        </div>
      )}
      <div style={{ position: "absolute", left: 930, top: 120, width: 900 }}>
        <div style={{ ...texto, fontSize: 44, color: "#888" }}>#{String(d.numero).padStart(4, "0")}</div>
        <div style={{ ...texto, fontSize: 104, lineHeight: 1.05, fontWeight: 700 }}>{d.nome}</div>
        {d.categoria && <div style={{ ...texto, fontSize: 40, color: "#555", marginTop: 6 }}>{d.categoria}</div>}
        <div style={{ display: "flex", gap: 16, marginTop: 28 }}>
          {d.tipos.map((t) => (
            <span key={t} style={{ ...texto, color: "#fff", background: COR_TIPO[t] ?? "#666", borderRadius: 40, padding: "8px 30px", fontSize: 38 }}>
              {t}
            </span>
          ))}
        </div>
        <div style={{ ...texto, fontSize: 34, color: "#444", marginTop: 28 }}>
          {d.altura_m !== undefined && <>altura {String(d.altura_m).replace(".", ",")} m</>}
          {d.peso_kg !== undefined && <> · peso {String(d.peso_kg).replace(".", ",")} kg</>}
          {d.regiao && <> · {d.regiao}</>}
        </div>
        <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 16 }}>
          {stats.map(([nome, v], k) => {
            // barras crescem em sequência no primeiro segundo (o texto já está lá)
            const cresce = interpolate(frame, [8 + k * 4, 28 + k * 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <div key={nome} style={{ display: "flex", alignItems: "center", gap: 18 }}>
                <span style={{ ...texto, width: 210, fontSize: 32, color: "#333" }}>{nome}</span>
                <span style={{ ...texto, width: 70, fontSize: 32, textAlign: "right" }}>{v}</span>
                <div style={{ flex: 1, height: 22, background: "#eee", borderRadius: 11, overflow: "hidden" }}>
                  <div style={{ width: `${Math.min(1, v / 200) * 100 * cresce}%`, height: "100%", background: cor, borderRadius: 11 }} />
                </div>
              </div>
            );
          })}
          <div style={{ ...texto, fontSize: 30, color: "#777", marginTop: 4 }}>total {total}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
