import { GitCompareArrows, Undo2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'

type Mudancas = {
  versao: number | null
  base: number | null
  reescrito: boolean
  lista: { paragrafo: number; partes: { t: 'igual' | 'saiu' | 'entrou'; x: string }[] }[]
}

const COR = {
  igual: 'text-texto/70',
  saiu: 'rounded bg-red-500/20 text-red-300 line-through',
  entrou: 'rounded bg-ok/15 text-ok',
}

/** O que mudou nesta versão do roteiro, palavra por palavra, com "desfazer" por alteração. Comparação local, sem cota. */
export function MudancasRoteiro({ videoId, versao, bloqueado, aoDesfazer }: { videoId: number; versao: number; bloqueado: boolean; aoDesfazer: (versao: number, indice: number) => Promise<boolean> }) {
  const [m, setM] = useState<Mudancas | null>(null)
  const [aberto, setAberto] = useState(true)
  useEffect(() => {
    api<Mudancas>(`/videos/${videoId}/roteiro/mudancas`).then(setM).catch(() => setM(null))
  }, [videoId, versao])
  if (!m?.versao) return null
  if (m.reescrito) return <p className="mb-3 text-xs text-apagado">v{m.versao} reescreveu quase todo o roteiro em relação à v{m.base}.</p>
  if (m.lista.length === 0) return null

  return (
    <div className="mb-3 rounded-lg border border-borda bg-painel-2 p-3 text-xs">
      <button onClick={() => setAberto(!aberto)} className="flex items-center gap-1.5 hover:text-texto">
        <GitCompareArrows className="size-4 text-suave" />
        <span className="text-sm font-medium">O que mudou nesta versão</span>
        <span className="text-apagado">
          {m.lista.length} {m.lista.length === 1 ? 'alteração' : 'alterações'} desde a v{m.base} {aberto ? '▴' : '▾'}
        </span>
      </button>
      {aberto && (
        <ul className="mt-2 flex max-h-96 flex-col gap-2 overflow-y-auto">
          {m.lista.map((a, k) => (
            <li key={k} className="rounded border border-borda p-2">
              <div className="mb-1 flex items-center">
                <span className="font-mono text-apagado">¶{a.paragrafo + 1}</span>
                <button
                  disabled={bloqueado}
                  onClick={() => aoDesfazer(m.versao!, k)}
                  title={bloqueado ? 'Espere a conferência terminar' : 'Volta só esta alteração; cria uma versão nova'}
                  className="ml-auto flex items-center gap-1 text-suave hover:text-texto disabled:opacity-40"
                >
                  <Undo2 className="size-3.5" /> desfazer
                </button>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {a.partes.map((p, j) => (
                  <span key={j} className={COR[p.t]}>
                    {p.x}
                  </span>
                ))}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
