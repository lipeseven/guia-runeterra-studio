import { Loader2, Play, RotateCcw, Save, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

type Palavra = { p: string; i: number; f: number; fala: number }
type Onda = { de: number; picos: number[]; palavras: Palavra[] }

const L = 1000 // largura do desenho (viewBox)
const A = 150 // altura da onda
const seg = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(2).padStart(5, '0')}`

/**
 * Mini editor de uma fala: forma de onda do áudio ORIGINAL (± 2 s em volta), as palavras que o Whisper marcou e dois
 * marcadores (começo e fim) que se arrastam ou se ajustam de 10 em 10 ms. "Salvar corte" grava o intervalo exato
 * (entra no "Refazer o áudio limpo" como as outras escolhas); o sistema não ajusta nada por cima dele.
 */
export function EditorFala({
  videoId,
  id,
  de,
  ate,
  manual,
  textoFala,
  ouvir,
  aoSalvar,
  aoFechar,
}: {
  videoId: number
  id: number
  de: number
  ate: number
  manual?: string
  textoFala: string
  ouvir: (i: number, f: number) => void
  aoSalvar: (decisoes: Record<string, string>) => void
  aoFechar: () => void
}) {
  const janelaDe = Math.max(0, de - 2)
  const janelaAte = Math.min(janelaDe + 60, ate + 2)
  const [onda, setOnda] = useState<Onda | null>(null)
  const [ini, setIni] = useState(manual ? Number(manual.split(':')[0]) : de)
  const [fim, setFim] = useState(manual ? Number(manual.split(':')[1]) : ate)
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const arrasto = useRef<'ini' | 'fim' | null>(null)

  useEffect(() => {
    setOnda(null)
    api<Onda>(`/videos/${videoId}/gravacao/onda?de=${janelaDe}&ate=${janelaAte}`)
      .then(setOnda)
      .catch((e) => setMsg(String(e)))
  }, [videoId, id]) // eslint-disable-line react-hooks/exhaustive-deps

  const dur = janelaAte - janelaDe
  const x = (t: number) => ((t - janelaDe) / dur) * L
  const tempo = (px: number) => janelaDe + (px / L) * dur
  const mover = (e: React.PointerEvent) => {
    if (!arrasto.current || !svg.current) return
    const r = svg.current.getBoundingClientRect()
    const v = Math.min(janelaAte, Math.max(janelaDe, tempo(((e.clientX - r.left) / r.width) * L)))
    if (arrasto.current === 'ini') setIni(Math.min(v, fim - 0.05))
    else setFim(Math.max(v, ini + 0.05))
    setMsg(null)
  }
  const ajustar = (qual: 'ini' | 'fim', d: number) => {
    setMsg(null)
    if (qual === 'ini') setIni((v) => Math.min(Math.max(janelaDe, v + d), fim - 0.05))
    else setFim((v) => Math.max(Math.min(janelaAte, v + d), ini + 0.05))
  }
  const salvar = async (remover = false) => {
    setSalvando(true)
    try {
      const r = await api<{ decisoes: Record<string, string> }>(`/videos/${videoId}/gravacao/corte`, {
        method: 'POST',
        body: JSON.stringify(remover ? { id } : { id, i: Number(ini.toFixed(3)), f: Number(fim.toFixed(3)) }),
      })
      aoSalvar(r.decisoes)
      setMsg(remover ? 'Corte manual removido (volta ao automático).' : 'Corte salvo. Clique em "Refazer o áudio limpo".')
    } catch (e) {
      setMsg(String(e))
    } finally {
      setSalvando(false)
    }
  }

  const marcador = (qual: 'ini' | 'fim', pos: number, cor: string) => (
    <g
      onPointerDown={(e) => {
        arrasto.current = qual
        ;(e.target as Element).setPointerCapture(e.pointerId)
      }}
      style={{ cursor: 'ew-resize' }}
    >
      <line x1={x(pos)} x2={x(pos)} y1={0} y2={A + 26} stroke={cor} strokeWidth={2} />
      <rect x={x(pos) - 9} y={0} width={18} height={A + 26} fill="transparent" />
      <polygon points={`${x(pos) - 7},0 ${x(pos) + 7},0 ${x(pos)},12`} fill={cor} />
    </g>
  )

  const passos = [-0.1, -0.01, 0.01, 0.1]

  return (
    <div className="mb-3 rounded-lg border border-ouro/50 bg-painel p-3">
      <div className="mb-2 flex items-center gap-2">
        <p className="text-sm font-medium">Editar corte da fala {id}</p>
        <span className="min-w-0 flex-1 truncate text-[11px] text-apagado">“{textoFala}”</span>
        <button onClick={aoFechar} className="text-suave hover:text-texto" title="Fechar">
          <X className="size-4" />
        </button>
      </div>
      {!onda ? (
        <p className="flex items-center gap-2 py-6 text-xs text-suave">
          <Loader2 className="size-4 animate-spin" /> carregando a forma de onda…
        </p>
      ) : (
        <svg
          ref={svg}
          viewBox={`0 0 ${L} ${A + 26}`}
          className="w-full touch-none select-none rounded bg-fundo"
          onPointerMove={mover}
          onPointerUp={() => (arrasto.current = null)}
        >
          <rect x={x(ini)} y={0} width={Math.max(0, x(fim) - x(ini))} height={A} fill="rgba(80,200,120,0.12)" />
          {onda.picos.map((v, k) => {
            const px = x(onda.de + k * 0.01)
            const h = Math.max(1, v * (A / 2 - 4))
            return (
              <line
                key={k}
                x1={px}
                x2={px}
                y1={A / 2 - h}
                y2={A / 2 + h}
                stroke={px >= x(ini) && px <= x(fim) ? '#6fcf97' : '#6b7280'}
                strokeWidth={Math.max(1, L / onda.picos.length)}
              />
            )
          })}
          {onda.palavras.map((w, k) => (
            <g key={k}>
              <line x1={x(w.i)} x2={x(w.i)} y1={A - 6} y2={A} stroke="#d4a64a" strokeWidth={1} opacity={0.6} />
              <text x={x(w.i) + 2} y={A + 12} fontSize={11} fill={w.fala === id ? '#e5e7eb' : '#9ca3af'}>
                {w.p}
              </text>
            </g>
          ))}
          {marcador('ini', ini, '#4ade80')}
          {marcador('fim', fim, '#f87171')}
        </svg>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button onClick={() => ouvir(ini, fim)} className="flex items-center gap-1.5 rounded-md border border-borda-forte px-2.5 py-1 hover:bg-painel-2">
          <Play className="size-3.5" /> ouvir o corte
        </button>
        <button
          onClick={() => ouvir(Math.max(janelaDe, ini - 1), ini + 0.4)}
          className="rounded-md border border-borda px-2 py-1 text-suave hover:text-texto"
          title="Ouve 1 s antes do começo até 0,4 s depois"
        >
          1 s antes
        </button>
        <span className="mx-1 text-apagado">começo {seg(ini)}</span>
        {passos.map((d) => (
          <button key={d} onClick={() => ajustar('ini', d)} className="rounded border border-borda px-1.5 py-0.5 font-mono text-[11px] text-suave hover:text-texto">
            {d > 0 ? '+' : ''}
            {Math.round(d * 1000)}
          </button>
        ))}
        <span className="mx-1 text-apagado">fim {seg(fim)}</span>
        {passos.map((d) => (
          <button key={d} onClick={() => ajustar('fim', d)} className="rounded border border-borda px-1.5 py-0.5 font-mono text-[11px] text-suave hover:text-texto">
            {d > 0 ? '+' : ''}
            {Math.round(d * 1000)}
          </button>
        ))}
        <span className="ml-auto flex items-center gap-2">
          {manual && (
            <button onClick={() => salvar(true)} disabled={salvando} className="flex items-center gap-1 rounded border border-borda px-2 py-1 text-suave hover:text-texto">
              <RotateCcw className="size-3.5" /> voltar ao automático
            </button>
          )}
          <button
            onClick={() => salvar()}
            disabled={salvando}
            className="flex items-center gap-1.5 rounded-md bg-ouro px-3 py-1.5 font-semibold text-fundo enabled:hover:brightness-110 disabled:opacity-40"
          >
            {salvando ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />} Salvar corte
          </button>
        </span>
      </div>
      {msg && <p className="mt-1.5 text-xs text-ouro">{msg}</p>}
    </div>
  )
}
