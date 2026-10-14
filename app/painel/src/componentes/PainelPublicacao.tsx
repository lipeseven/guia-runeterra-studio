import { Check, Copy, Download, FolderOpen, Loader2, RefreshCw, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, arquivo, AVISO_PUBLICAR, type Etapa } from '../api'

type Textos = {
  titulos: string[]
  titulo: string
  descricao: string
  tags: string[]
  comentario_fixado: string
  capitulos: { titulo: string; tempo: string }[]
  thumbnail: string | null
  midias_usadas: number
}
type Dados = {
  textos: Textos | null
  tamanhos: { trabalho: number; saida: number; entrada: number; direcao: number }
  url: string | null
  video_final: string | null
}

function BotaoCopiar({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false)
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(texto)
        setOk(true)
        setTimeout(() => setOk(false), 1500)
      }}
      className="flex shrink-0 items-center gap-1 rounded-md border border-borda-forte px-2 py-1 text-[11px] text-suave hover:text-texto"
    >
      {ok ? <Check className="size-3.5 text-ok" /> : <Copy className="size-3.5" />} {ok ? 'copiado' : 'copiar'}
    </button>
  )
}

/** Textos do YouTube, thumbnail, "marcar como publicado" e limpeza dos arquivos. */
export function PainelPublicacao({ videoId, etapa, publicado, aoMudar }: { videoId: number; etapa: Etapa; publicado: boolean; aoMudar: () => void }) {
  const [d, setD] = useState<Dados | null>(null)
  const [url, setUrl] = useState('')
  const carregar = () => api<Dados>(`/videos/${videoId}/publicacao`).then(setD)
  useEffect(() => {
    carregar()
  }, [videoId, etapa.status, etapa.atualizado_em, publicado]) // eslint-disable-line react-hooks/exhaustive-deps

  const t = d?.textos
  const salvar = (campos: Partial<Textos>) => {
    if (!d?.textos) return
    setD({ ...d, textos: { ...d.textos, ...campos } })
    api(`/videos/${videoId}/publicacao`, { method: 'PUT', body: JSON.stringify(campos) })
  }

  return (
    <section id="publicacao" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-center gap-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Send className="size-4 text-suave" /> Publicação
        </h2>
        {t && <span className="font-mono text-[11px] text-apagado">{t.capitulos.length} capítulos · {t.midias_usadas} mídias usadas</span>}
        {t && etapa.status !== 'andamento' && !publicado && (
          <button
            onClick={async () => {
              await api(`/videos/${videoId}/publicacao/gerar`, { method: 'POST' })
              aoMudar()
            }}
            className="ml-auto flex items-center gap-1.5 rounded-md border border-borda-forte px-3 py-1.5 text-xs text-suave hover:text-texto"
          >
            <RefreshCw className="size-3.5" /> Gerar textos de novo
          </button>
        )}
      </header>

      {etapa.status === 'andamento' ? (
        <div className="flex items-center gap-3 rounded-lg border border-andamento/40 bg-andamento/5 p-4">
          <Loader2 className="size-5 animate-spin text-andamento" />
          <p className="text-sm">{etapa.resumo ?? 'preparando…'}</p>
        </div>
      ) : !t ? (
        <div className="flex items-center gap-3 text-sm text-suave">
          <p>Os textos são preparados quando você aprova o vídeo final (“Vídeo aprovado”).</p>
          <button
            onClick={async () => {
              await api(`/videos/${videoId}/publicacao/gerar`, { method: 'POST' })
              aoMudar()
            }}
            className="shrink-0 rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:text-texto"
          >
            Gerar agora
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* título */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium text-suave">Título ({t.titulo.length}/100)</span>
              <BotaoCopiar texto={t.titulo} />
            </div>
            <input
              value={t.titulo}
              onChange={(e) => setD({ ...d!, textos: { ...t, titulo: e.target.value } })}
              onBlur={(e) => salvar({ titulo: e.target.value })}
              className="w-full rounded-md border border-borda bg-painel-2 px-2.5 py-2 text-sm outline-none focus:border-suave"
            />
            <div className="mt-1.5 flex flex-col gap-1">
              {t.titulos.map((op) => (
                <button
                  key={op}
                  onClick={() => salvar({ titulo: op })}
                  className={`text-left text-xs ${op === t.titulo ? 'text-ouro' : 'text-suave hover:text-texto'}`}
                >
                  {op === t.titulo ? '● ' : '○ '}
                  {op}
                </button>
              ))}
            </div>
          </div>

          {/* descrição */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium text-suave">Descrição (com capítulos, créditos e aviso da Riot)</span>
              <BotaoCopiar texto={t.descricao} />
            </div>
            <textarea
              value={t.descricao}
              onChange={(e) => setD({ ...d!, textos: { ...t, descricao: e.target.value } })}
              onBlur={(e) => salvar({ descricao: e.target.value })}
              className="h-56 w-full resize-y rounded-md border border-borda bg-painel-2 p-2.5 font-mono text-xs leading-relaxed outline-none focus:border-suave"
            />
          </div>

          {/* tags e comentário */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-xs font-medium text-suave">Tags</span>
                <BotaoCopiar texto={t.tags.join(', ')} />
              </div>
              <textarea
                defaultValue={t.tags.join(', ')}
                onBlur={(e) => salvar({ tags: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) })}
                className="h-20 w-full resize-y rounded-md border border-borda bg-painel-2 p-2 text-xs outline-none focus:border-suave"
              />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-xs font-medium text-suave">Comentário fixado</span>
                <BotaoCopiar texto={t.comentario_fixado} />
              </div>
              <textarea
                defaultValue={t.comentario_fixado}
                onBlur={(e) => salvar({ comentario_fixado: e.target.value })}
                className="h-20 w-full resize-y rounded-md border border-borda bg-painel-2 p-2 text-xs outline-none focus:border-suave"
              />
            </div>
          </div>

          {/* arquivos */}
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-borda bg-painel-2 p-3">
            {t.thumbnail && <img src={arquivo(t.thumbnail)} alt="Thumbnail" className="h-20 rounded border border-borda" />}
            <div className="min-w-0 flex-1 text-xs text-suave">
              <p>
                {t.thumbnail || d?.video_final
                  ? 'Thumbnail 1280×720 (a sua capa) e o vídeo final ficam na pasta de saída.'
                  : 'Vídeo final e thumbnail foram para a Lixeira na limpeza.'}
              </p>
              {d?.video_final && <p className="mt-1 truncate font-mono text-[11px] text-apagado">{d.video_final}</p>}
            </div>
            {t.thumbnail && (
              <a href={arquivo(t.thumbnail)} download="thumbnail.jpg" className="flex items-center gap-1.5 rounded-md border border-borda-forte px-2.5 py-1.5 text-xs text-suave hover:text-texto">
                <Download className="size-3.5" /> Thumbnail
              </a>
            )}
            <button
              onClick={() => api(`/videos/${videoId}/abrir-pasta-saida`, { method: 'POST' })}
              className="flex items-center gap-1.5 rounded-md border border-borda-forte px-2.5 py-1.5 text-xs text-suave hover:text-texto"
            >
              <FolderOpen className="size-3.5" /> Abrir pasta de saída
            </button>
          </div>

          {/* publicar */}
          {!publicado || !d?.url ? (
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ouro/40 bg-ouro/5 p-3">
              <span className="text-sm">{publicado ? 'Link do vídeo no YouTube:' : 'Subiu no YouTube?'}</span>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="link do vídeo (opcional)"
                className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
              />
              <button
                onClick={async () => {
                  if (!publicado && !window.confirm(AVISO_PUBLICAR)) return
                  await api(`/videos/${videoId}/publicado`, { method: 'POST', body: JSON.stringify({ url }) })
                  aoMudar()
                }}
                className="rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
              >
                {publicado ? 'Salvar link' : 'Marcar como publicado'}
              </button>
            </div>
          ) : (
            d?.url && (
              <p className="text-xs text-suave">
                Publicado:{' '}
                <a href={d.url} target="_blank" rel="noreferrer" className="text-ouro underline">
                  {d.url}
                </a>
              </p>
            )
          )}
        </div>
      )}

    </section>
  )
}
