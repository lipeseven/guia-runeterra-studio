import { CheckCircle2, FolderOpen, Loader2, Mic, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, arquivo, type Etapa } from '../api'

type Removido = { i: number; f: number; texto: string; motivo: string }
type Relatorio = {
  duracao_original: number
  duracao_limpa: number
  removidos: Removido[]
  pausas_encurtadas?: { em: number; de: number; para: number }[]
  divergencias_do_roteiro?: { roteiro: string; lido: string }[]
}

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
const EXTENSOES = '.wav,.mp3,.m4a,.flac,.ogg,.aac,.mp4,.mkv,.mov,.webm'

/** Envio da gravação (com progresso) e relatório da limpeza. */
export function PainelGravacao({ videoId, etapa, aoMudar }: { videoId: number; etapa: Etapa; aoMudar: () => void }) {
  const [progresso, setProgresso] = useState<number | null>(null)
  const [arrastando, setArrastando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [verCortes, setVerCortes] = useState(false)
  const seletor = useRef<HTMLInputElement>(null)
  const rel = etapa.dados.relatorio as Relatorio | undefined
  const trabalhando = etapa.status === 'andamento'

  const enviar = (f: File | undefined) => {
    if (!f) return
    setErro(null)
    const corpo = new FormData()
    corpo.append('arquivo', f)
    const xhr = new XMLHttpRequest() // XHR para mostrar o progresso do envio (arquivos de gravação são grandes)
    xhr.open('POST', `/api/videos/${videoId}/gravacao`)
    xhr.upload.onprogress = (e) => e.lengthComputable && setProgresso(Math.round((e.loaded / e.total) * 100))
    xhr.onload = () => {
      setProgresso(null)
      if (xhr.status >= 400) setErro(xhr.responseText.replace(/[{}"]|detail:/g, ''))
      aoMudar()
    }
    xhr.onerror = () => {
      setProgresso(null)
      setErro('Falha no envio')
    }
    xhr.send(corpo)
  }

  const daPasta = async () => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/gravacao/da-pasta`, { method: 'POST' })
      aoMudar()
    } catch (e) {
      setErro(String(e).replace(/^Error: \d+ /, '').replace(/[{}"]|detail:/g, ''))
    }
  }

  return (
    <section id="gravacao" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-center gap-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Mic className="size-4 text-suave" /> Gravação
        </h2>
        {rel && (
          <span className="font-mono text-[11px] text-apagado">
            {mmss(rel.duracao_original)} → {mmss(rel.duracao_limpa)} · {rel.removidos.length} cortes ·{' '}
            {rel.pausas_encurtadas?.length ?? 0} pausas encurtadas
          </span>
        )}
        {rel && !trabalhando && (
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => seletor.current?.click()} className="rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:bg-painel-2">
              Enviar outra gravação
            </button>
            {etapa.status === 'concluido' ? (
              <span className="flex items-center gap-1.5 text-xs text-ok">
                <CheckCircle2 className="size-4" /> Aprovada
              </span>
            ) : (
              <button
                onClick={async () => {
                  await api(`/videos/${videoId}/gravacao/aprovar`, { method: 'POST' })
                  aoMudar()
                }}
                className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
              >
                Aprovar áudio limpo
              </button>
            )}
          </div>
        )}
      </header>
      <input ref={seletor} type="file" accept={EXTENSOES} className="hidden" onChange={(e) => enviar(e.target.files?.[0])} />

      {progresso !== null ? (
        <div className="rounded-lg border border-borda-forte p-4">
          <p className="mb-2 text-sm">Enviando a gravação… {progresso}%</p>
          <div className="h-1.5 overflow-hidden rounded-full bg-borda">
            <div className="h-full bg-ouro" style={{ width: `${progresso}%` }} />
          </div>
        </div>
      ) : trabalhando ? (
        <div className="flex items-center gap-3 rounded-lg border border-andamento/40 bg-andamento/5 p-4">
          <Loader2 className="size-5 animate-spin text-andamento" />
          <div>
            <p className="text-sm">{etapa.resumo ?? 'trabalhando…'}</p>
            <p className="text-xs text-suave">O sistema limpa a gravação e depois espera você conferir. Você pode sair desta tela.</p>
          </div>
        </div>
      ) : !rel ? (
        <>
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setArrastando(true)
            }}
            onDragLeave={() => setArrastando(false)}
            onDrop={(e) => {
              e.preventDefault()
              setArrastando(false)
              enviar(e.dataTransfer.files[0])
            }}
            onClick={() => seletor.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center ${
              arrastando ? 'border-ouro bg-ouro/5' : 'border-borda-forte hover:border-suave'
            }`}
          >
            <Upload className="size-6 text-suave" />
            <p className="text-sm">
              Arraste a <b>gravação</b> aqui (áudio ou vídeo) ou <span className="text-ouro underline">clique para escolher</span>
            </p>
            <p className="text-xs text-apagado">wav, mp3, m4a, flac, ogg, mp4, mkv, mov… Grave lendo o roteiro aprovado; pode errar e repetir à vontade.</p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-suave">
            <span>Arquivo muito grande?</span>
            <button
              onClick={() => api(`/videos/${videoId}/abrir-pasta-entrada`, { method: 'POST' })}
              className="flex items-center gap-1.5 rounded-md border border-borda-forte px-2.5 py-1 hover:text-texto"
            >
              <FolderOpen className="size-3.5" /> Abrir a pasta entrada
            </button>
            <span>coloque o arquivo lá e clique em</span>
            <button onClick={daPasta} className="rounded-md border border-ouro/60 px-2.5 py-1 text-ouro hover:bg-ouro/10">
              Já coloquei na pasta
            </button>
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {typeof etapa.dados.original === 'string' && (
              <div>
                <p className="mb-1 text-xs text-suave">Original</p>
                <audio src={arquivo(etapa.dados.original)} controls className="w-full" />
              </div>
            )}
            {typeof etapa.dados.audio === 'string' && (
              <div>
                <p className="mb-1 text-xs text-suave">Limpa (vai para o vídeo)</p>
                <audio src={`${arquivo(etapa.dados.audio)}&v=${encodeURIComponent(etapa.atualizado_em ?? '')}`} controls className="w-full" />
              </div>
            )}
          </div>
          {!!rel.divergencias_do_roteiro?.length && (
            <div className="rounded-lg border border-atencao/30 bg-atencao/5 p-3 text-sm">
              <p className="mb-1 font-medium text-atencao">Lido diferente do roteiro (nada foi cortado por isso)</p>
              <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
                {rel.divergencias_do_roteiro.map((d, k) => (
                  <li key={k}>
                    “{d.roteiro}” → “{d.lido}”
                  </li>
                ))}
              </ul>
            </div>
          )}
          <button onClick={() => setVerCortes(!verCortes)} className="self-start text-xs text-suave underline hover:text-texto">
            {verCortes ? 'esconder' : 'ver'} os {rel.removidos.length} cortes feitos
          </button>
          {verCortes && (
            <ul className="max-h-64 overflow-y-auto rounded-lg border border-borda bg-painel-2 p-2 text-sm">
              {rel.removidos.map((r, k) => (
                <li key={k} className="flex gap-3 border-b border-borda/60 py-1.5 last:border-0">
                  <span className="w-24 shrink-0 font-mono text-[11px] text-apagado">
                    {mmss(r.i)}–{mmss(r.f)}
                  </span>
                  <span className="min-w-0 flex-1 text-texto/85">“{r.texto}”</span>
                  <span className="shrink-0 text-[11px] text-suave">{r.motivo}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-red-400">{erro}</p>}
    </section>
  )
}
