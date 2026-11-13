import { Loader2, Mic, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

/** Ditado local (faster-whisper PT-BR no servidor, processo à parte): o mesmo das Observações gerais, reaproveitado no
 *  "corrigir por voz" de cada cena do storyboard. Clicar para gravar e clicar para parar, ou segurar e soltar.
 *  O texto transcrito vai para `aoTexto` (o campo da tela), para o Felipe corrigir ANTES de salvar/enviar. */

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

export function useDitado(videoId: number, aoTexto: (novo: string) => void) {
  const [gravando, setGravando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [transcrevendo, setTranscrevendo] = useState<string | null>(null) // "na fila" | "transcrevendo…"
  const [erro, setErro] = useState<string | null>(null)
  const gravador = useRef<MediaRecorder | null>(null)
  const pedacos = useRef<Blob[]>([])
  const apertou = useRef(0)
  const relogio = useRef<number | null>(null)
  const destino = useRef(aoTexto)
  destino.current = aoTexto
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
          else destino.current(novo)
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

  return { gravando, segundos, transcrevendo, erro, setErro, aoApertar, aoSoltar, enviarAudio }
}

export function BotaoMic({ d, rotulo = 'Gravar por voz', pequeno = false }: { d: ReturnType<typeof useDitado>; rotulo?: string; pequeno?: boolean }) {
  const tam = pequeno ? 'size-8' : 'size-10'
  return (
    <button
      type="button"
      aria-label={d.gravando ? 'Parar de gravar' : rotulo}
      title={d.gravando ? 'Clique (ou solte) para parar' : 'Clique para gravar e clique para parar, ou segure enquanto fala'}
      disabled={Boolean(d.transcrevendo)}
      onPointerDown={d.aoApertar}
      onPointerUp={d.aoSoltar}
      onPointerLeave={d.aoSoltar}
      className={`flex ${tam} shrink-0 items-center justify-center rounded-full border transition ${
        d.gravando ? 'animate-pulse border-atencao bg-atencao/15 text-atencao' : 'border-ouro/60 text-ouro hover:bg-ouro/10'
      } disabled:cursor-wait disabled:opacity-50`}
    >
      {d.transcrevendo ? <Loader2 className="size-4 animate-spin" /> : d.gravando ? <Square className="size-4" /> : <Mic className="size-4" />}
    </button>
  )
}

export function EstadoDitado({ d }: { d: ReturnType<typeof useDitado> }) {
  return (
    <>
      {d.gravando && <p className="mt-1 font-mono text-[11px] text-atencao">● gravando {d.segundos}s — clique no quadrado para parar</p>}
      {d.transcrevendo && <p className="mt-1 font-mono text-[11px] text-andamento">{d.transcrevendo}</p>}
      {d.erro && <p role="alert" className="mt-2 text-xs text-atencao">{d.erro}</p>}
    </>
  )
}
