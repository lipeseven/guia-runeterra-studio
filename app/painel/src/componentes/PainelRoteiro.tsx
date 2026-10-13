import { CheckCircle2, ClipboardPaste, FileText, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Etapa } from '../api'

type DadosRoteiro = { texto: string | null; paragrafos?: number; palavras?: number; segundos?: number }

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`

/** Lê um .txt em UTF-8; se não for UTF-8 válido (Bloco de Notas antigo), cai para Windows-1252. */
async function lerTxt(arquivo: File) {
  const bytes = await arquivo.arrayBuffer()
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder('windows-1252').decode(bytes)
  }
}

export function PainelRoteiro({ videoId, etapa, aoMudar }: { videoId: number; etapa: Etapa; aoMudar: () => void }) {
  const [dados, setDados] = useState<DadosRoteiro | null>(null)
  const [arrastando, setArrastando] = useState(false)
  const [colando, setColando] = useState(false)
  const [colado, setColado] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const seletor = useRef<HTMLInputElement>(null)
  const versao = (etapa.dados.versao as number | undefined) ?? 0

  const carregar = () => api<DadosRoteiro>(`/videos/${videoId}/roteiro`).then(setDados)
  useEffect(() => {
    carregar()
    // recarrega quando chega versão nova
  }, [videoId, versao]) // eslint-disable-line react-hooks/exhaustive-deps

  const enviar = async (texto: string, nome: string) => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/roteiro`, { method: 'POST', body: JSON.stringify({ texto, nome }) })
      setColando(false)
      setColado('')
      await carregar()
      aoMudar()
    } catch (e) {
      setErro(String(e))
    }
  }
  const receberArquivo = async (f: File | undefined) => {
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.txt')) return setErro('Envie um arquivo .txt')
    enviar(await lerTxt(f), f.name)
  }

  const aprovado = etapa.status === 'concluido'
  const temRoteiro = Boolean(dados?.texto)

  return (
    <section id="roteiro" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-center gap-3">
        <h2 className="text-sm font-semibold">Roteiro</h2>
        {temRoteiro && (
          <span className="font-mono text-[11px] text-apagado">
            v{versao} · {dados?.paragrafos} parágrafos · {dados?.palavras} palavras · ~{mmss(dados?.segundos ?? 0)} narrado
          </span>
        )}
        {temRoteiro && (
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => seletor.current?.click()} className="rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:bg-painel-2">
              Substituir
            </button>
            {aprovado ? (
              <span className="flex items-center gap-1.5 text-xs text-ok">
                <CheckCircle2 className="size-4" /> Aprovado
              </span>
            ) : (
              <button
                onClick={async () => {
                  await api(`/videos/${videoId}/roteiro/aprovar`, { method: 'POST' })
                  aoMudar()
                }}
                className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
              >
                Aprovar roteiro
              </button>
            )}
          </div>
        )}
      </header>

      <input ref={seletor} type="file" accept=".txt,text/plain" className="hidden" onChange={(e) => receberArquivo(e.target.files?.[0])} />

      {!temRoteiro && !colando && (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setArrastando(true)
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault()
            setArrastando(false)
            receberArquivo(e.dataTransfer.files[0])
          }}
          onClick={() => seletor.current?.click()}
          className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            arrastando ? 'border-ouro bg-ouro/5' : 'border-borda-forte hover:border-suave'
          }`}
        >
          <Upload className="size-6 text-suave" />
          <p className="text-sm">
            Arraste o <b>.txt</b> do roteiro aqui, ou <span className="text-ouro underline">clique para escolher</span>
          </p>
          <p className="text-xs text-apagado">Separe os parágrafos com uma linha em branco.</p>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setColando(true)
            }}
            className="mt-2 flex items-center gap-1.5 text-xs text-suave hover:text-texto"
          >
            <ClipboardPaste className="size-3.5" /> prefiro colar o texto
          </button>
        </div>
      )}

      {colando && (
        <div className="flex flex-col gap-2">
          <textarea
            autoFocus
            value={colado}
            onChange={(e) => setColado(e.target.value)}
            placeholder="Cole o roteiro aqui…"
            className="h-64 w-full resize-y rounded-lg border border-borda-forte bg-painel-2 p-3 text-sm leading-relaxed outline-none focus:border-suave"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setColando(false)} className="rounded-md border border-borda-forte px-3 py-1.5 text-xs">
              Cancelar
            </button>
            <button onClick={() => enviar(colado, 'roteiro colado')} className="rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo">
              Enviar roteiro
            </button>
          </div>
        </div>
      )}

      {temRoteiro && (
        <div className="max-h-96 overflow-y-auto rounded-lg border border-borda bg-painel-2 p-4">
          <div className="mb-2 flex items-center gap-1.5 font-mono text-[11px] text-apagado">
            <FileText className="size-3.5" /> {String(etapa.dados.arquivo_original ?? 'roteiro.txt')}
          </div>
          {dados!.texto!.split(/\n\s*\n/).map((p, k) => (
            <p key={k} className="mb-3 text-sm leading-relaxed text-texto/90 last:mb-0">
              {p}
            </p>
          ))}
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-red-400">{erro}</p>}
    </section>
  )
}
