import { Loader2 } from 'lucide-react'
import { useAoVivo, type Motor } from '../api'

const tempo = (s: number) => (s >= 3600 ? `${Math.floor(s / 3600)}h${String(Math.round((s % 3600) / 60)).padStart(2, '0')}` : s >= 60 ? `${Math.round(s / 60)} min` : `${s} s`)

/**
 * Barra de progresso do que o motor está fazendo NESTE vídeo (render, direção…). Some quando o motor está livre
 * ou trabalhando em outro vídeo. `compacta` = só a barrinha (cards do quadro).
 */
export function Progresso({ videoId, compacta = false }: { videoId: number; compacta?: boolean }) {
  const { dados: m } = useAoVivo<Motor>('/motor', 2000)
  return <ProgressoDoMotor motor={m} videoId={videoId} compacta={compacta} />
}

/** A barra em si, com o estado do motor já em mãos (o quadro consulta uma vez e repassa a todos os cards). */
export function ProgressoDoMotor({ motor: m, videoId, compacta = false }: { motor: Motor | null; videoId: number; compacta?: boolean }) {
  if (!m?.executando || m.executando.video !== videoId || !m.progresso) return null
  const p = m.progresso
  const pct = p.fracao == null ? null : Math.round(p.fracao * 100)
  const barra = (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-borda">
      {pct == null ? (
        <div className="h-full w-1/3 animate-pulse rounded-full bg-andamento" />
      ) : (
        <div className="h-full rounded-full bg-andamento transition-all duration-700" style={{ width: `${Math.max(2, pct)}%` }} />
      )}
    </div>
  )
  if (compacta)
    return (
      <div className="mt-2" title={`${p.titulo}: ${p.texto}`}>
        {barra}
        <p className="mt-1 truncate font-mono text-[10px] text-andamento">
          {pct != null ? `${pct}%` : p.titulo}
          {p.restante_s != null && ` · ~${tempo(p.restante_s)}`}
        </p>
      </div>
    )
  return (
    <section className="rounded-xl border border-andamento/40 bg-andamento/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin text-andamento" />
        <span className="font-semibold">{p.titulo}</span>
        <span className="min-w-0 truncate text-suave">{p.texto}</span>
        <span className="ml-auto shrink-0 font-mono text-xs text-andamento">
          {pct != null && `${pct}%`}
          {p.restante_s != null && ` · faltam ~${tempo(p.restante_s)}`}
        </span>
      </div>
      {barra}
    </section>
  )
}
