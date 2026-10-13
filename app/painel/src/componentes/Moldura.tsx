import * as Tooltip from '@radix-ui/react-tooltip'
import { Activity, FolderOpen, LayoutGrid, Search, Settings } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Recursos } from '../api'
import { useAoVivo } from '../api'

type Item = { icone: typeof LayoutGrid; rotulo: string; href?: string; emBreve?: boolean }
const ITENS: Item[] = [
  { icone: LayoutGrid, rotulo: 'Quadro de vídeos', href: '#/' },
  { icone: FolderOpen, rotulo: 'Acervo (em breve)', emBreve: true },
  { icone: Activity, rotulo: 'Recursos (em breve)', emBreve: true },
  { icone: Settings, rotulo: 'Configurações (em breve)', emBreve: true },
]

export function Moldura({ trilha, children }: { trilha: ReactNode; children: ReactNode }) {
  const { dados: rec } = useAoVivo<Recursos>('/recursos', 4000)
  return (
    <Tooltip.Provider delayDuration={150}>
      <div className="flex h-full">
        <aside className="flex w-14 shrink-0 flex-col items-center gap-2 border-r border-borda bg-painel py-3">
          <a href="#/" className="mb-3 grid size-9 place-items-center rounded-lg bg-ouro/15 font-titulo text-lg font-semibold text-ouro">
            G
          </a>
          {ITENS.map(({ icone: Icone, rotulo, href, emBreve }) => (
            <Tooltip.Root key={rotulo}>
              <Tooltip.Trigger asChild>
                <a
                  href={href}
                  aria-disabled={emBreve}
                  className={`grid size-9 place-items-center rounded-lg ${
                    emBreve ? 'cursor-default text-apagado' : 'text-suave hover:bg-painel-2 hover:text-texto'
                  }`}
                >
                  <Icone className="size-[18px]" />
                </a>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content side="right" sideOffset={8} className="rounded-md border border-borda bg-painel-2 px-2 py-1 text-xs text-texto">
                  {rotulo}
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          ))}
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-12 shrink-0 items-center gap-3 border-b border-borda px-5 text-sm">
            <div className="flex min-w-0 items-center gap-2 text-suave">{trilha}</div>
            <span className="flex items-center gap-1.5 text-xs text-ok">
              <span className="size-1.5 animate-pulse rounded-full bg-ok" /> Ao vivo
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Chip>
                GPU <b className="text-texto">{rec?.gpu.ok ? `${rec.gpu.uso}%` : '—'}</b>
              </Chip>
              <Chip>
                Disco livre <b className="text-texto">{rec ? `${Math.round(rec.disco.livre / 1e9)} GB` : '—'}</b>
              </Chip>
              <Chip>Custo <b className="text-ok">R$ 0,00</b></Chip>
              <div className="flex h-8 w-64 items-center gap-2 rounded-lg border border-borda bg-painel px-3 text-xs text-apagado">
                <Search className="size-3.5" /> Buscar vídeo, cena, mídia… <span className="ml-auto">em breve</span>
              </div>
            </div>
          </header>
          <main className="min-h-0 flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </Tooltip.Provider>
  )
}

function Chip({ children }: { children: ReactNode }) {
  return <span className="flex h-8 items-center gap-1.5 rounded-lg border border-borda bg-painel px-3 font-mono text-[11px] text-suave">{children}</span>
}
