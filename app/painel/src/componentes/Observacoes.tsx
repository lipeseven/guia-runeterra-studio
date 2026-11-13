import { Mic, Pencil, Trash2, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, quando } from '../api'
import { BotaoMic, EstadoDitado, useDitado } from './Ditado'

/** Observações gerais do vídeo (qualquer formato), ditadas por voz ou digitadas.
 *  Microfone: clicar para gravar e clicar para parar, ou segurar e soltar. O áudio vai para o servidor, o
 *  faster-whisper local transcreve (PT-BR) em processo à parte e o texto cai no campo, editável, antes de salvar.
 *  No card documentário do F1 as observações entram nos prompts da História, da SPEC e dos pedidos por cena. */

type Obs = { id: number; texto: string; origem: 'voz' | 'texto'; criada_em: string; editada_em: string | null }

const limpar = (e: unknown) => String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)

export function Observacoes({ videoId, paraDiretor = false }: { videoId: number; paraDiretor?: boolean }) {
  const [lista, setLista] = useState<Obs[] | null>(null)
  const [texto, setTexto] = useState('')
  const [origem, setOrigem] = useState<'voz' | 'texto'>('texto')
  const [erro, setErro] = useState<string | null>(null)
  const [editando, setEditando] = useState<{ id: number; texto: string } | null>(null)
  const arquivoRef = useRef<HTMLInputElement>(null)
  // ditado local (componentes/Ditado.tsx, o mesmo do "corrigir por voz" das cenas do storyboard)
  const dit = useDitado(videoId, (novo) => {
    setTexto((atual) => (atual.trim() ? `${atual.trimEnd()} ${novo}` : novo))
    setOrigem('voz')
  })
  const { gravando, transcrevendo, enviarAudio } = dit

  const recarregar = useCallback(() => {
    api<{ observacoes: Obs[] }>(`/videos/${videoId}/observacoes`).then((r) => setLista(r.observacoes)).catch((e) => setErro(limpar(e)))
  }, [videoId])
  useEffect(recarregar, [recarregar])

  const agir = async (caminho: string, opcoes: RequestInit) => {
    setErro(null)
    try {
      const r = await api<{ observacoes: Obs[] }>(caminho, opcoes)
      setLista(r.observacoes)
      return true
    } catch (e) {
      setErro(limpar(e))
      return false
    }
  }
  const salvar = async () => {
    if (await agir(`/videos/${videoId}/observacoes`, { method: 'POST', body: JSON.stringify({ texto, origem }) })) {
      setTexto('')
      setOrigem('texto')
    }
  }
  const salvarEdicao = async () => {
    if (editando && (await agir(`/videos/${videoId}/observacoes/${editando.id}`, { method: 'PUT', body: JSON.stringify({ texto: editando.texto }) })))
      setEditando(null)
  }
  const apagar = (o: Obs) => {
    if (confirm(`Apagar esta observação?\n\n“${o.texto.slice(0, 200)}”`)) void agir(`/videos/${videoId}/observacoes/${o.id}`, { method: 'DELETE' })
  }

  return (
    <section id="observacoes" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">Observações gerais</h2>
        <span className="font-mono text-[11px] text-apagado">{lista ? `${lista.length} salva(s)` : '…'}</span>
      </header>
      <p className="mb-2 text-xs text-suave">
        Fale ou digite o que vale para o vídeo inteiro.
        {paraDiretor && ' Entram no prompt da História, da SPEC e dos pedidos por cena do diretor.'}
      </p>

      <div className="flex items-start gap-2">
        <BotaoMic d={dit} rotulo="Gravar observação por voz" />
        <textarea
          aria-label="Texto da observação"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={3}
          placeholder={gravando ? 'Gravando… fale à vontade.' : 'Digite, ou clique no microfone e fale.'}
          className="min-h-[4.5rem] w-full resize-y rounded-md border border-borda bg-fundo px-2 py-1.5 text-sm outline-none focus:border-ouro/60"
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={!texto.trim() || Boolean(transcrevendo) || gravando}
          onClick={salvar}
          className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Salvar observação
        </button>
        {texto && !gravando && (
          <button type="button" onClick={() => { setTexto(''); setOrigem('texto') }} className="text-xs text-suave hover:text-texto">
            Limpar
          </button>
        )}
        <button
          type="button"
          disabled={Boolean(transcrevendo) || gravando}
          onClick={() => arquivoRef.current?.click()}
          title="Transcrever um arquivo de áudio já gravado"
          className="ml-auto flex items-center gap-1 text-xs text-suave hover:text-texto disabled:opacity-40"
        >
          <Upload className="size-3" /> áudio
        </button>
        <input
          ref={arquivoRef}
          type="file"
          accept="audio/*,.webm,.ogg,.wav,.mp3,.m4a,.flac"
          className="hidden"
          data-teste="arquivo-audio"
          onChange={(e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (f) void enviarAudio(f, f.name)
          }}
        />
      </div>
      <EstadoDitado d={dit} />
      {erro && <p role="alert" className="mt-2 text-xs text-atencao">{erro}</p>}

      {lista && lista.length > 0 && (
        <ul className="mt-3 flex flex-col border-t border-borda/60">
          {[...lista].reverse().map((o) => (
            <li key={o.id} className="border-b border-borda/60 py-2 text-sm last:border-0">
              <div className="mb-1 flex items-center gap-2 font-mono text-[11px] text-apagado">
                {o.origem === 'voz' && <Mic className="size-3" aria-label="ditada" />}
                <span title={o.criada_em}>{quando(o.criada_em)}</span>
                {o.editada_em && <span title={o.editada_em}>· editada</span>}
                <span className="ml-auto flex gap-2">
                  <button type="button" aria-label="Editar observação" onClick={() => setEditando({ id: o.id, texto: o.texto })} className="hover:text-texto">
                    <Pencil className="size-3" />
                  </button>
                  <button type="button" aria-label="Apagar observação" onClick={() => apagar(o)} className="hover:text-atencao">
                    <Trash2 className="size-3" />
                  </button>
                </span>
              </div>
              {editando?.id === o.id ? (
                <div>
                  <textarea
                    aria-label="Editar texto da observação"
                    value={editando.texto}
                    onChange={(e) => setEditando({ id: o.id, texto: e.target.value })}
                    rows={3}
                    className="w-full resize-y rounded-md border border-borda bg-fundo px-2 py-1.5 text-sm outline-none focus:border-ouro/60"
                  />
                  <div className="mt-1 flex gap-3 text-xs">
                    <button type="button" disabled={!editando.texto.trim()} onClick={salvarEdicao} className="text-ouro hover:underline disabled:opacity-40">Salvar</button>
                    <button type="button" onClick={() => setEditando(null)} className="text-suave hover:text-texto">Cancelar</button>
                  </div>
                </div>
              ) : (
                <p className="whitespace-pre-wrap text-texto/85">{o.texto}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
