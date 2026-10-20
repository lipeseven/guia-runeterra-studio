import { Loader2, Pause, Play, RotateCcw, Scissors, Undo2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, arquivo } from '../api'

type Fala = { id: number; i: number; f: number; texto: string; cortada: boolean; motivo: string | null; inicio_cortado: string | null }
type Dados = { falas: Fala[]; decisoes: Record<string, string> }

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
const PX_POR_SEGUNDO = 7

/**
 * Linha do tempo da gravação ORIGINAL: cada fala é um bloco (verde = entra no áudio limpo, vermelho = cortada).
 * Clique para ouvir; corte ou recupere à mão e "Refazer o áudio limpo" (sem transcrever de novo).
 */
export function LinhaDoTempo({ videoId, original, trabalhando, aoRefazer }: { videoId: number; original: string; trabalhando: boolean; aoRefazer: () => void }) {
  const [d, setD] = useState<Dados | null>(null)
  const [filtro, setFiltro] = useState<'cortadas' | 'todas' | 'escolhas'>('cortadas')
  const [tocando, setTocando] = useState<number | null>(null)
  const [enviando, setEnviando] = useState(false)
  const audio = useRef<HTMLAudioElement>(null)
  const fimRef = useRef<number>(0)
  const trilha = useRef<HTMLDivElement>(null)

  const carregar = () => api<Dados>(`/videos/${videoId}/gravacao/falas`).then(setD)
  useEffect(() => {
    carregar()
  }, [videoId, trabalhando]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!d || d.falas.length === 0) return null
  const dec = d.decisoes
  const fica = (x: Fala) => (dec[x.id] === 'manter' || dec[x.id] === 'inicio' ? true : dec[x.id] === 'cortar' ? false : !x.cortada)
  const total = d.falas[d.falas.length - 1].f + 1
  const escolhas = Object.keys(dec).length

  const ouvir = (x: Fala, comInicio = false) => {
    const a = audio.current
    if (!a) return
    if (tocando === x.id) {
      a.pause()
      setTocando(null)
      return
    }
    a.currentTime = Math.max(0, x.i - (comInicio ? 3 : 0.15))
    fimRef.current = x.f + 0.2
    setTocando(x.id)
    a.play()
    const el = trilha.current?.querySelector(`[data-fala="${x.id}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }
  const decidir = async (x: Fala, acao: string) => setD({ ...d, decisoes: (await api<{ decisoes: Record<string, string> }>(`/videos/${videoId}/gravacao/falas`, { method: 'POST', body: JSON.stringify({ id: x.id, acao }) })).decisoes })

  const lista = d.falas.filter((x) => (filtro === 'todas' ? true : filtro === 'cortadas' ? !fica(x) || x.inicio_cortado : dec[x.id]))

  return (
    <div className="rounded-lg border border-borda bg-painel-2 p-3">
      <audio
        ref={audio}
        src={arquivo(original)}
        onTimeUpdate={(e) => {
          if (tocando !== null && e.currentTarget.currentTime >= fimRef.current) {
            e.currentTarget.pause()
            setTocando(null)
          }
        }}
        className="hidden"
      />
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium">Linha do tempo da gravação</p>
        <span className="text-[11px] text-apagado">verde = entra · vermelho = cortado · contorno dourado = escolha sua · clique para ouvir</span>
        <button
          disabled={escolhas === 0 || trabalhando || enviando}
          onClick={async () => {
            setEnviando(true)
            try {
              await api(`/videos/${videoId}/gravacao/refazer`, { method: 'POST' })
              aoRefazer()
            } finally {
              setTimeout(() => setEnviando(false), 1500)
            }
          }}
          className="ml-auto flex items-center gap-1.5 rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo enabled:hover:brightness-110 disabled:opacity-40"
        >
          {trabalhando || enviando ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
          Refazer o áudio limpo{escolhas ? ` (${escolhas} escolha${escolhas > 1 ? 's' : ''})` : ''}
        </button>
      </div>

      {/* trilha: blocos na posição real do áudio original */}
      <div ref={trilha} className="overflow-x-auto pb-2">
        <div className="relative h-10" style={{ width: total * PX_POR_SEGUNDO }}>
          {Array.from({ length: Math.ceil(total / 60) }, (_, m) => (
            <span key={m} className="absolute top-0 h-full border-l border-borda/60 pl-0.5 font-mono text-[9px] text-apagado" style={{ left: m * 60 * PX_POR_SEGUNDO }}>
              {m}:00
            </span>
          ))}
          {d.falas.map((x) => (
            <button
              key={x.id}
              data-fala={x.id}
              title={`${mmss(x.i)} “${x.texto}”${x.cortada ? ` — ${x.motivo}` : ''}`}
              onClick={() => ouvir(x)}
              className={`absolute top-3 h-6 rounded-sm ${fica(x) ? 'bg-ok/70' : 'bg-red-500/70'} ${dec[x.id] ? 'ring-2 ring-ouro' : ''} ${tocando === x.id ? 'brightness-150' : ''}`}
              style={{ left: x.i * PX_POR_SEGUNDO, width: Math.max(2, (x.f - x.i) * PX_POR_SEGUNDO - 1) }}
            />
          ))}
        </div>
      </div>

      <div className="mb-1 flex gap-1 text-[11px]">
        {(
          [
            ['cortadas', `cortadas (${d.falas.filter((x) => !fica(x)).length})`],
            ['escolhas', `suas escolhas (${escolhas})`],
            ['todas', `todas (${d.falas.length})`],
          ] as const
        ).map(([v, r]) => (
          <button key={v} onClick={() => setFiltro(v)} className={`rounded px-2 py-0.5 ${filtro === v ? 'bg-painel text-texto' : 'text-suave hover:text-texto'}`}>
            {r}
          </button>
        ))}
      </div>
      <ul className="max-h-80 overflow-y-auto text-sm">
        {lista.map((x) => {
          const entra = fica(x)
          return (
            <li key={x.id} className={`flex items-center gap-2 border-b border-borda/50 py-1.5 last:border-0 ${dec[x.id] ? 'bg-ouro/5' : ''}`}>
              <button onClick={() => ouvir(x)} className="shrink-0 text-suave hover:text-texto" title="Ouvir (no áudio original)">
                {tocando === x.id ? <Pause className="size-4" /> : <Play className="size-4" />}
              </button>
              <span className="w-12 shrink-0 font-mono text-[11px] text-apagado">{mmss(x.i)}</span>
              <span className={`min-w-0 flex-1 ${entra ? 'text-texto/90' : 'text-red-300/80 line-through decoration-red-400/40'}`}>
                {x.inicio_cortado && dec[x.id] !== 'inicio' && <span className="text-red-300/80 line-through">{x.inicio_cortado} </span>}
                “{x.texto}”
              </span>
              <span className="shrink-0 text-[11px] text-apagado">{dec[x.id] ? 'escolha sua' : x.motivo ?? ''}</span>
              {x.inicio_cortado && dec[x.id] !== 'inicio' && (
                <button onClick={() => decidir(x, 'inicio')} className="shrink-0 rounded border border-borda px-1.5 py-0.5 text-[11px] text-suave hover:text-texto">
                  devolver o começo
                </button>
              )}
              {entra ? (
                <button onClick={() => decidir(x, 'cortar')} className="flex shrink-0 items-center gap-1 rounded border border-borda px-1.5 py-0.5 text-[11px] text-suave hover:border-red-400/60 hover:text-red-300">
                  <Scissors className="size-3" /> cortar
                </button>
              ) : (
                <button onClick={() => decidir(x, 'manter')} className="flex shrink-0 items-center gap-1 rounded border border-ok/50 px-1.5 py-0.5 text-[11px] text-ok hover:bg-ok/10">
                  <Undo2 className="size-3" /> recuperar
                </button>
              )}
              {dec[x.id] && (
                <button onClick={() => decidir(x, 'padrao')} className="shrink-0 text-[11px] text-apagado hover:text-texto" title="Volta à decisão automática">
                  ↺
                </button>
              )}
            </li>
          )
        })}
        {lista.length === 0 && <li className="py-2 text-xs text-apagado">Nada aqui.</li>}
      </ul>
    </div>
  )
}
