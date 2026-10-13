import { AlertTriangle, Check, CircleDashed, Loader2, Sparkles } from 'lucide-react'
import type { Status } from '../api'

export const ROTULO: Record<Status, string> = {
  concluido: 'Concluído',
  andamento: 'Em andamento',
  atencao: 'Precisa de você',
  pendente: 'Aguardando',
  em_breve: 'Em breve',
}

export const COR: Record<Status, string> = {
  concluido: 'text-ok',
  andamento: 'text-andamento',
  atencao: 'text-atencao',
  pendente: 'text-apagado',
  em_breve: 'text-apagado',
}

export const FUNDO: Record<Status, string> = {
  concluido: 'bg-ok',
  andamento: 'bg-andamento',
  atencao: 'bg-atencao',
  pendente: 'bg-borda-forte',
  em_breve: 'bg-borda',
}

const ICONE = { concluido: Check, andamento: Loader2, atencao: AlertTriangle, pendente: CircleDashed, em_breve: Sparkles }

/** Círculo grande do card de etapa (como na referência). */
export function CirculoEstado({ status }: { status: Status }) {
  const Icone = ICONE[status]
  return (
    <div
      className={`grid size-11 place-items-center rounded-full border-2 ${COR[status]} ${
        status === 'em_breve' || status === 'pendente' ? 'border-dashed border-current/50' : 'border-current'
      }`}
    >
      <Icone className={`size-5 ${status === 'andamento' ? 'animate-spin [animation-duration:2.5s]' : ''}`} strokeWidth={2.4} />
    </div>
  )
}

export function RotuloEstado({ status }: { status: Status }) {
  const Icone = ICONE[status]
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${COR[status]}`}>
      <Icone className="size-3.5" strokeWidth={2.4} />
      {ROTULO[status]}
    </span>
  )
}
