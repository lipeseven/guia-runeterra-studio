import { useState } from 'react'
import { api, type Etapa } from '../api'

/** Vídeo vertical: a voz de IA vem pronta de outro programa; aqui só sobe o arquivo. */
export function PainelVoz({ videoId, etapa, aoMudar }: { videoId: number; etapa: Etapa; aoMudar: () => void }) {
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const limpar = (e: unknown) => String(e).replace(/^Error: \d+ /, '').replace(/[{}"]|detail:/g, '')
  const enviar = async (arquivo: File) => {
    setErro(null)
    setEnviando(true)
    const corpo = new FormData()
    corpo.append('arquivo', arquivo)
    const r = await fetch(`/api/videos/${videoId}/voz`, { method: 'POST', body: corpo })
    setEnviando(false)
    if (!r.ok) setErro(limpar(await r.text()))
    aoMudar()
  }
  const daPasta = async () => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/voz/da-pasta`, { method: 'POST' })
      aoMudar()
    } catch (e) {
      setErro(limpar(e))
    }
  }
  const audio = typeof etapa.dados.audio === 'string' ? etapa.dados.audio : null
  return (
    <section id="voz" className="rounded-xl border border-borda bg-painel p-4">
      <h2 className="text-sm font-semibold">Voz</h2>
      <p className="mt-1 text-xs text-suave">{etapa.resumo ?? 'Gere a voz no seu programa e suba o áudio aqui.'}</p>
      {audio && <audio src={`/api/arquivo?caminho=${encodeURIComponent(audio)}`} controls className="mt-3 w-full" />}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <label className="cursor-pointer rounded border border-borda px-3 py-1.5 hover:border-borda-forte">
          {enviando ? 'Enviando…' : audio ? 'Trocar o áudio' : 'Escolher o áudio'}
          <input
            type="file"
            accept="audio/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && enviar(e.target.files[0])}
          />
        </label>
        <button onClick={daPasta} className="rounded border border-borda px-3 py-1.5 hover:border-borda-forte">
          Já coloquei na pasta
        </button>
      </div>
      {erro && <p className="mt-2 text-xs text-atencao">{erro}</p>}
    </section>
  )
}
