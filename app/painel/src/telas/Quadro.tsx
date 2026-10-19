import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { AlertTriangle, Lock, Plus } from 'lucide-react'
import { useState } from 'react'
import { api, arquivo, AVISO_PUBLICAR, quando, useAoVivo, type Coluna, type Motor, type Status, type VideoResumo } from '../api'
import { FUNDO } from '../componentes/Estado'
import { MenuCard } from '../componentes/MenuCard'
import { Moldura } from '../componentes/Moldura'
import { ProgressoDoMotor } from '../componentes/Progresso'

type DadosQuadro = { colunas: Coluna[]; videos: VideoResumo[] }
const ORDEM_STATUS: Status[] = ['concluido', 'atencao', 'andamento', 'pendente', 'em_breve']

export function Quadro() {
  const { dados, recarregar, setDados } = useAoVivo<DadosQuadro>('/quadro', 5000)
  const { dados: motor } = useAoVivo<Motor>('/motor', 2000)
  const [arrastando, setArrastando] = useState<VideoResumo | null>(null)
  const sensores = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const soltar = async (e: DragEndEvent) => {
    setArrastando(null)
    const coluna = e.over?.id as string | undefined
    const id = Number(e.active.id)
    if (!dados || !coluna) return
    const video = dados.videos.find((v) => v.id === id)
    if (!video || video.coluna === coluna || video.travado || video.coluna === 'publicado') return
    if (coluna === 'publicado' && !window.confirm(AVISO_PUBLICAR)) return
    // otimista: move já na tela; o servidor confirma em seguida
    setDados({ ...dados, videos: dados.videos.map((v) => (v.id === id ? { ...v, coluna, ordem: 1e9 } : v)) })
    await api(`/videos/${id}/mover`, { method: 'PATCH', body: JSON.stringify({ coluna }) })
    recarregar()
  }

  return (
    <Moldura trilha={<span className="text-texto">Quadro de vídeos</span>}>
      <div className="px-6 pt-6 pb-3">
        <h1 className="font-titulo text-4xl font-medium tracking-tight">Guia de Runeterra</h1>
        <p className="mt-1 font-mono text-xs text-suave">
          {dados ? `${dados.videos.length} vídeos · arraste os cards entre as colunas` : 'carregando…'}
        </p>
      </div>
      <DndContext
        sensors={sensores}
        onDragStart={(e) => setArrastando(dados?.videos.find((v) => v.id === Number(e.active.id)) ?? null)}
        onDragEnd={soltar}
        onDragCancel={() => setArrastando(null)}
      >
        <div className="flex gap-4 overflow-x-auto px-6 pb-6">
          {dados?.colunas.map((c) => (
            <ColunaQuadro
              key={c.chave}
              coluna={c}
              videos={dados.videos.filter((v) => v.coluna === c.chave).sort((a, b) => a.ordem - b.ordem)}
              aoCriar={recarregar}
              motor={motor}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null}>{arrastando && <CardVideo video={arrastando} flutuando />}</DragOverlay>
      </DndContext>
    </Moldura>
  )
}

function ColunaQuadro({ coluna, videos, aoCriar, motor }: { coluna: Coluna; videos: VideoResumo[]; aoCriar: () => void; motor: Motor | null }) {
  const { setNodeRef, isOver } = useDroppable({ id: coluna.chave })
  const [titulo, setTitulo] = useState('')
  const criar = async () => {
    if (!titulo.trim()) return
    await api('/videos', { method: 'POST', body: JSON.stringify({ titulo, coluna: coluna.chave }) })
    setTitulo('')
    aoCriar()
  }
  return (
    <section
      ref={setNodeRef}
      className={`flex w-72 shrink-0 flex-col rounded-xl border p-3 transition-colors ${
        isOver ? 'border-ouro/60 bg-ouro/5' : 'border-borda bg-painel/60'
      }`}
    >
      <header className="mb-3 flex items-center justify-between px-1">
        <h2 className="text-sm font-semibold">{coluna.titulo}</h2>
        <span className="font-mono text-xs text-apagado">{videos.length}</span>
      </header>
      <div className="flex min-h-24 flex-col gap-2.5">
        {videos.map((v) => (
          <ArrastavelVideo key={v.id} video={v} aoMudar={aoCriar} motor={motor} />
        ))}
      </div>
      {coluna.chave === 'publicado' && <JaPublicado aoCriar={aoCriar} />}
      {coluna.chave === 'ideia' && (
        <div className="mt-3 flex items-center justify-center gap-2 rounded-lg border border-dashed border-borda-forte px-2.5 py-2">
          <Plus className="size-4 shrink-0 text-apagado" />
          <input
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && criar()}
            placeholder="Nova ideia de vídeo…"
            className="max-w-full min-w-[3ch] bg-transparent text-sm outline-none [field-sizing:content] placeholder:text-apagado"
          />
        </div>
      )}
    </section>
  )
}

/** Vídeo publicado antes do sistema: entra direto em Publicado, só para o histórico (capa, link, roteiro). */
function JaPublicado({ aoCriar }: { aoCriar: () => void }) {
  const [aberto, setAberto] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [url, setUrl] = useState('')
  const [data, setData] = useState('')
  const [capa, setCapa] = useState<File | null>(null)
  const [roteiro, setRoteiro] = useState<File | null>(null)
  const [enviando, setEnviando] = useState(false)
  const base64 = (f: File) =>
    new Promise<string>((ok, erro) => {
      const r = new FileReader()
      r.onload = () => ok(String(r.result).split(',')[1] ?? '')
      r.onerror = erro
      r.readAsDataURL(f)
    })
  const salvar = async () => {
    if (!titulo.trim()) return
    setEnviando(true)
    try {
      await api('/videos/ja-publicado', {
        method: 'POST',
        body: JSON.stringify({
          titulo,
          url: url || null,
          data: data || null,
          capa_nome: capa?.name ?? null,
          capa_base64: capa ? await base64(capa) : null,
          roteiro: roteiro ? await roteiro.text() : null,
        }),
      })
      setTitulo('')
      setUrl('')
      setData('')
      setCapa(null)
      setRoteiro(null)
      setAberto(false)
      aoCriar()
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e))
    } finally {
      setEnviando(false)
    }
  }
  const campo = 'w-full rounded-md border border-borda bg-painel-2 px-2 py-1 text-sm outline-none focus:border-suave'
  if (!aberto)
    return (
      <button
        onClick={() => setAberto(true)}
        className="mt-3 flex items-center justify-center gap-2 rounded-lg border border-dashed border-borda-forte px-2.5 py-2 text-sm text-apagado hover:text-texto"
      >
        <Plus className="size-4 shrink-0" /> Vídeo já publicado…
      </button>
    )
  return (
    <div className="mt-3 flex flex-col gap-1.5 rounded-lg border border-borda-forte p-2.5 text-xs text-suave">
      <span className="text-[11px] text-apagado">Só para o histórico do canal: não roda direção nem render.</span>
      <input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Título do vídeo" className={campo} autoFocus />
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Link do YouTube" className={campo} />
      <label className="flex items-center gap-2">
        publicado em <input type="date" value={data} onChange={(e) => setData(e.target.value)} className={campo} />
      </label>
      <label className="flex flex-col gap-0.5">
        capa / thumbnail (JPG, PNG, WEBP)
        <input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={(e) => setCapa(e.target.files?.[0] ?? null)} />
      </label>
      <label className="flex flex-col gap-0.5">
        roteiro (.txt, opcional)
        <input type="file" accept=".txt" onChange={(e) => setRoteiro(e.target.files?.[0] ?? null)} />
      </label>
      <div className="mt-1 flex gap-2">
        <button
          onClick={salvar}
          disabled={!titulo.trim() || enviando}
          className="rounded-md bg-ouro/20 px-2.5 py-1 text-ouro hover:bg-ouro/30 disabled:opacity-40"
        >
          {enviando ? 'salvando…' : 'Adicionar'}
        </button>
        <button onClick={() => setAberto(false)} className="px-2 py-1 text-apagado hover:text-texto">
          cancelar
        </button>
      </div>
    </div>
  )
}

function ArrastavelVideo({ video, aoMudar, motor }: { video: VideoResumo; aoMudar: () => void; motor: Motor | null }) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: String(video.id),
    disabled: Boolean(video.travado) || video.coluna === 'publicado', // publicado é definitivo
  })
  return (
    <div ref={setNodeRef} {...listeners} {...attributes} className={isDragging ? 'opacity-30' : ''}>
      <CardVideo video={video} menu={<MenuCard video={video} aoMudar={aoMudar} />} motor={motor} />
    </div>
  )
}

function CardVideo({ video, flutuando, menu, motor = null }: { video: VideoResumo; flutuando?: boolean; menu?: React.ReactNode; motor?: Motor | null }) {
  const segmentos = ORDEM_STATUS.flatMap((s) => Array(video.progresso[s] ?? 0).fill(s) as Status[])
  return (
    <a
      href={`#/video/${video.id}`}
      className={`block overflow-hidden rounded-lg border bg-painel-2 hover:border-borda-forte ${
        video.travado ? 'cursor-pointer border-ouro/40' : video.coluna === 'publicado' ? 'cursor-pointer border-borda' : 'cursor-grab border-borda active:cursor-grabbing'
      } ${
        flutuando ? 'rotate-2 shadow-2xl shadow-black/60' : ''
      }`}
      draggable={false}
    >
      {video.capa && (
        <img src={arquivo(video.capa)} alt="" className="aspect-video w-full object-cover opacity-90" draggable={false} />
      )}
      <div className="p-3">
        {/* menu na linha do título (fora da imagem da capa, sempre visível) */}
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 text-sm leading-snug font-medium">
            {video.travado ? <Lock className="mr-1.5 mb-0.5 inline size-3.5 text-ouro" /> : null}
            {video.titulo}
          </h3>
          {menu && <div className="-mt-0.5 -mr-1 shrink-0">{menu}</div>}
        </div>
        <div className="mt-2.5 flex gap-0.5">
          {segmentos.map((s, k) => (
            <span key={k} className={`h-1 flex-1 rounded-full ${FUNDO[s]}`} />
          ))}
        </div>
        <ProgressoDoMotor motor={motor} videoId={video.id} compacta />
        <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-apagado">
          <span>
            {video.progresso.concluido ?? 0}/{video.total_etapas} etapas
          </span>
          {video.pendencias > 0 ? (
            <span className="flex items-center gap-1 text-atencao">
              <AlertTriangle className="size-3" /> {video.pendencias}
            </span>
          ) : (
            <span>{quando(video.atualizado_em)}</span>
          )}
        </div>
      </div>
    </a>
  )
}
