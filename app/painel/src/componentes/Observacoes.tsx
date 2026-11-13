import { Loader2, Mic, Pencil, Square, Trash2, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, quando } from '../api'

/** Observações gerais do vídeo (qualquer formato), ditadas por voz ou digitadas.
 *  Microfone: clicar para gravar e clicar para parar, ou segurar e soltar. O áudio vai para o servidor, o
 *  faster-whisper local transcreve (PT-BR) em processo à parte e o texto cai no campo, editável, antes de salvar.
 *  No card documentário do F1 as observações entram nos prompts da História, da SPEC e dos pedidos por cena. */

type Obs = { id: number; texto: string; origem: 'voz' | 'texto'; criada_em: string; editada_em: string | null }
type Tarefa = { status: 'na_fila' | 'transcrevendo' | 'pronto' | 'falhou'; texto: string | null; erro: string | null }

const limpar = (e: unknown) => String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)
const SEGURAR_MS = 450 // apertou e segurou mais que isso: soltar para de gravar

function erroDoMicrofone(e: unknown): string {
  const nome = (e as { name?: string })?.name
  if (nome === 'NotAllowedError' || nome === 'SecurityError')
    return 'O navegador negou o microfone. Clique no cadeado ao lado do endereço → Microfone → Permitir, e tente de novo.'
  if (nome === 'NotFoundError') return 'Nenhum microfone encontrado neste computador.'
  if (nome === 'NotReadableError') return 'O microfone está ocupado por outro programa (feche-o e tente de novo).'
  return `Não deu para usar o microfone: ${String(e)}`
}

function extensao(tipo: string) {
  if (tipo.includes('ogg')) return 'ogg'
  if (tipo.includes('mp4')) return 'm4a'
  if (tipo.includes('wav')) return 'wav'
  return 'webm'
}

export function Observacoes({ videoId, paraDiretor = false }: { videoId: number; paraDiretor?: boolean }) {
  const [lista, setLista] = useState<Obs[] | null>(null)
  const [texto, setTexto] = useState('')
  const [origem, setOrigem] = useState<'voz' | 'texto'>('texto')
  const [gravando, setGravando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [transcrevendo, setTranscrevendo] = useState<string | null>(null) // "na fila" | "transcrevendo…"
  const [erro, setErro] = useState<string | null>(null)
  const [editando, setEditando] = useState<{ id: number; texto: string } | null>(null)
  const gravador = useRef<MediaRecorder | null>(null)
  const pedacos = useRef<Blob[]>([])
  const apertou = useRef(0)
  const relogio = useRef<number | null>(null)
  const arquivoRef = useRef<HTMLInputElement>(null)

  const recarregar = useCallback(() => {
    api<{ observacoes: Obs[] }>(`/videos/${videoId}/observacoes`).then((r) => setLista(r.observacoes)).catch((e) => setErro(limpar(e)))
  }, [videoId])
  useEffect(recarregar, [recarregar])
  useEffect(() => () => gravador.current?.stream.getTracks().forEach((t) => t.stop()), [])

  const enviarAudio = async (audio: Blob, nome: string) => {
    setErro(null)
    setTranscrevendo('enviando…')
    try {
      const corpo = new FormData()
      corpo.append('arquivo', audio, nome)
      const r = await fetch(`/api/videos/${videoId}/observacoes/transcrever`, { method: 'POST', body: corpo })
      if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
      const { tarefa } = (await r.json()) as { tarefa: string }
      for (;;) {
        await new Promise((ok) => setTimeout(ok, 1000))
        const t = await api<Tarefa>(`/transcricoes/${tarefa}`)
        if (t.status === 'pronto') {
          const novo = (t.texto ?? '').trim()
          if (!novo) setErro('Não entendi nada no áudio (silêncio?). Tente de novo ou digite.')
          setTexto((atual) => (atual.trim() && novo ? `${atual.trimEnd()} ${novo}` : atual || novo))
          if (novo) setOrigem('voz')
          break
        }
        if (t.status === 'falhou') throw new Error(t.erro ?? 'a transcrição falhou')
        setTranscrevendo(t.status === 'na_fila' ? 'na fila…' : 'transcrevendo…')
      }
    } catch (e) {
      setErro(limpar(e))
    } finally {
      setTranscrevendo(null)
    }
  }

  const comecar = async () => {
    setErro(null)
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setErro('O microfone só funciona em localhost ou https. Abra o painel por http://localhost:<porta> (ou 127.0.0.1), não pelo IP da rede.')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setErro('Este navegador não grava áudio (MediaRecorder). Use o Chrome/Edge, ou envie um arquivo de áudio.')
      return
    }
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch (e) {
      setErro(erroDoMicrofone(e))
      return
    }
    const tipo = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find((t) => MediaRecorder.isTypeSupported(t))
    const rec = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined)
    pedacos.current = []
    rec.ondataavailable = (ev) => ev.data.size && pedacos.current.push(ev.data)
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      const blob = new Blob(pedacos.current, { type: rec.mimeType || tipo || 'audio/webm' })
      if (blob.size) void enviarAudio(blob, `ditado.${extensao(blob.type)}`)
      else setErro('Nada foi gravado.')
    }
    rec.start(250)
    gravador.current = rec
    setGravando(true)
    setSegundos(0)
    relogio.current = window.setInterval(() => setSegundos((s) => s + 1), 1000)
  }

  const parar = () => {
    if (relogio.current) window.clearInterval(relogio.current)
    relogio.current = null
    if (gravador.current?.state === 'recording') gravador.current.stop()
    gravador.current = null
    setGravando(false)
  }

  // clicar = liga/desliga; segurar = grava enquanto segura
  const aoApertar = () => {
    if (transcrevendo) return
    if (gravando) return parar()
    apertou.current = Date.now()
    void comecar()
  }
  const aoSoltar = () => {
    if (gravando && apertou.current && Date.now() - apertou.current > SEGURAR_MS) parar()
    apertou.current = 0
  }

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
        <button
          type="button"
          aria-label={gravando ? 'Parar de gravar' : 'Gravar observação por voz'}
          title={gravando ? 'Clique (ou solte) para parar' : 'Clique para gravar e clique para parar, ou segure enquanto fala'}
          disabled={Boolean(transcrevendo)}
          onPointerDown={aoApertar}
          onPointerUp={aoSoltar}
          onPointerLeave={aoSoltar}
          className={`flex size-10 shrink-0 items-center justify-center rounded-full border transition ${
            gravando ? 'animate-pulse border-atencao bg-atencao/15 text-atencao' : 'border-ouro/60 text-ouro hover:bg-ouro/10'
          } disabled:cursor-wait disabled:opacity-50`}
        >
          {transcrevendo ? <Loader2 className="size-4 animate-spin" /> : gravando ? <Square className="size-4" /> : <Mic className="size-4" />}
        </button>
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
      {gravando && <p className="mt-1 font-mono text-[11px] text-atencao">● gravando {segundos}s — clique no quadrado para parar</p>}
      {transcrevendo && <p className="mt-1 font-mono text-[11px] text-andamento">{transcrevendo}</p>}
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
