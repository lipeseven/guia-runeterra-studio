import * as Dialog from '@radix-ui/react-dialog'
import * as Menu from '@radix-ui/react-dropdown-menu'
import { Lock, LockOpen, MoreHorizontal, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api, type VideoResumo } from '../api'

/** Menu "⋯" do card: travar/destravar e excluir (com confirmação). */
export function MenuCard({ video, aoMudar, aoExcluir }: { video: Pick<VideoResumo, 'id' | 'titulo' | 'travado'>; aoMudar: () => void; aoExcluir?: () => void }) {
  const [confirmar, setConfirmar] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const travado = Boolean(video.travado)
  // impede que o clique/arraste no menu abra o vídeo ou comece um arraste do card
  const parar = (e: React.SyntheticEvent) => {
    e.stopPropagation()
    e.preventDefault()
  }
  const item = 'flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-sm outline-none data-[highlighted]:bg-painel-2'

  return (
    <>
      <Menu.Root modal={false}>
        <Menu.Trigger asChild>
          <button
            onPointerDown={(e) => e.stopPropagation()}
            onClick={parar}
            aria-label="Opções do vídeo"
            className="grid size-7 place-items-center rounded-md bg-fundo/70 text-suave backdrop-blur hover:bg-painel-2 hover:text-texto"
          >
            <MoreHorizontal className="size-4" />
          </button>
        </Menu.Trigger>
        <Menu.Portal>
          <Menu.Content
            align="end"
            sideOffset={4}
            onClick={(e) => e.stopPropagation()}
            className="z-50 min-w-44 rounded-lg border border-borda bg-painel p-1 shadow-xl shadow-black/50"
          >
            <Menu.Item
              className={item}
              onSelect={async () => {
                await api(`/videos/${video.id}/travar`, { method: 'PATCH', body: JSON.stringify({ travado: !travado }) })
                aoMudar()
              }}
            >
              {travado ? <LockOpen className="size-4 text-suave" /> : <Lock className="size-4 text-suave" />}
              {travado ? 'Destravar' : 'Travar'}
            </Menu.Item>
            <Menu.Item
              disabled={travado}
              className={`${item} text-red-400 data-[disabled]:cursor-not-allowed data-[disabled]:text-apagado`}
              onSelect={() => setConfirmar(true)}
            >
              <Trash2 className="size-4" />
              Excluir{travado ? ' (destrave antes)' : ''}
            </Menu.Item>
          </Menu.Content>
        </Menu.Portal>
      </Menu.Root>

      <Dialog.Root open={confirmar} onOpenChange={setConfirmar}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-borda bg-painel p-5 shadow-2xl">
            <Dialog.Title className="text-base font-semibold">Excluir “{video.titulo}”?</Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-suave">
              O card e o histórico saem do painel. Os arquivos do vídeo (roteiro, capa, rascunhos) vão para a Lixeira do Windows.
            </Dialog.Description>
            {erro && <p className="mt-3 text-sm text-atencao">{erro}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <Dialog.Close className="rounded-lg border border-borda-forte px-4 py-2 text-sm hover:bg-painel-2">Cancelar</Dialog.Close>
              <button
                onClick={async () => {
                  try {
                    await api(`/videos/${video.id}`, { method: 'DELETE' })
                    setConfirmar(false)
                    if (aoExcluir) aoExcluir()
                    else aoMudar()
                  } catch (e) {
                    setErro(String(e).replace(/^Error: \d+ /, '').replace(/[{}"]|detail:/g, ''))
                  }
                }}
                className="rounded-lg bg-red-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
              >
                Excluir
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}
