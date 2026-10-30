import { FolderOpen } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'

type Lista = { pasta: string; arquivos: { nome: string; modificado: number }[] }

/** "escolher da pasta": .txt da pasta de roteiros do canal (dados/<canal>/roteiros), mais recentes primeiro. */
export function DaPasta({ aoEscolher, rotulo = 'escolher da pasta' }: { aoEscolher: (texto: string, nome: string) => void; rotulo?: string }) {
  const [lista, setLista] = useState<Lista | null>(null)
  const abrir = async () => setLista(lista ? null : await api<Lista>('/roteiros'))
  const escolher = async (nome: string) => {
    const r = await api<{ nome: string; texto: string }>(`/roteiros/${nome.split('/').map(encodeURIComponent).join('/')}`)
    setLista(null)
    aoEscolher(r.texto, r.nome)
  }
  return (
    <span className="relative inline-block">
      <button type="button" onClick={(e) => (e.stopPropagation(), abrir())} className="flex items-center gap-1.5 whitespace-nowrap text-xs text-suave hover:text-texto">
        <FolderOpen className="size-3.5" /> {rotulo}
      </button>
      {lista && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="absolute left-0 top-6 z-20 w-80 rounded-lg border border-borda-forte bg-painel p-2 text-left text-xs shadow-lg"
        >
          <p className="mb-1.5 break-all font-mono text-[10px] text-apagado">{lista.pasta}</p>
          {lista.arquivos.length === 0 && <p className="text-suave">Nenhum .txt na pasta ainda.</p>}
          <ul className="flex max-h-64 flex-col overflow-y-auto">
            {lista.arquivos.map((a) => (
              <li key={a.nome}>
                <button onClick={() => escolher(a.nome)} className="w-full truncate rounded px-1.5 py-1 text-left hover:bg-painel-2">
                  {a.nome}
                  <span className="ml-1 text-apagado">· {new Date(a.modificado * 1000).toLocaleDateString('pt-BR')}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </span>
  )
}
