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
import { AlertTriangle, ChevronDown, GraduationCap, Lock, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
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
        <div className="flex flex-wrap items-center gap-4">
          <SeletorDeCanal />
          <Aprendizado />
        </div>
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

type Canal = { chave: string; nome: string; porta: number; canais: { chave: string; nome: string; porta: number }[] }

/** Nome do canal deste servidor; os outros canais abrem no servidor deles (os canais não se misturam). */
function SeletorDeCanal() {
  const [canal, setCanal] = useState<Canal | null>(null)
  const [aberto, setAberto] = useState(false)
  useEffect(() => {
    api<Canal>('/canal').then((c) => {
      setCanal(c)
      document.title = `${c.nome} Studio`
    })
  }, [])
  const outros = (canal?.canais ?? []).filter((c) => c.chave !== canal?.chave)
  return (
    <div className="relative inline-block">
      <button onClick={() => outros.length && setAberto(!aberto)} className="flex items-center gap-2">
        <h1 className="font-titulo text-4xl font-medium tracking-tight">{canal?.nome ?? '…'}</h1>
        {outros.length > 0 && <ChevronDown className="mt-1 size-5 text-suave" />}
      </button>
      {aberto && (
        <div className="absolute left-0 top-full z-40 mt-1 min-w-56 rounded-lg border border-borda bg-painel p-1 shadow-xl">
          {outros.map((c) => (
            <a
              key={c.chave}
              href={`http://127.0.0.1:${c.porta}/`}
              className="block rounded px-3 py-2 text-sm hover:bg-painel-2"
              title="Abre o painel deste canal (servidor próprio). Se não abrir, ligue o canal pelo iniciar.bat."
            >
              {c.nome}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

type Proposta = { id: number; video: string; regra: string; evidencia: string; status: 'pendente' | 'aprovada' | 'recusada' }

/** Regras que o sistema propôs depois de cada vídeo publicado (retrospectiva dos seus ajustes). Nada entra sem você aprovar. */
function Aprendizado() {
  const [d, setD] = useState<{ propostas: Proposta[]; exemplos: number } | null>(null)
  const [aberto, setAberto] = useState(false)
  const [textos, setTextos] = useState<Record<number, string>>({})
  const carregar = () => api<{ propostas: Proposta[]; exemplos: number }>('/aprendizado').then(setD)
  useEffect(() => {
    carregar()
    const t = setInterval(carregar, 60000)
    return () => clearInterval(t)
  }, [])
  if (!d) return null
  const pendentes = d.propostas.filter((p) => p.status === 'pendente')
  const decidir = async (p: Proposta, acao: 'aprovar' | 'recusar') => {
    await api(`/aprendizado/${p.id}`, { method: 'POST', body: JSON.stringify({ acao, texto: textos[p.id] ?? p.regra }) })
    carregar()
  }
  return (
    <div className="relative">
      <button
        onClick={() => setAberto(!aberto)}
        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs ${pendentes.length ? 'border-ouro/60 text-ouro hover:bg-ouro/10' : 'border-borda text-suave hover:text-texto'}`}
        title="O que o sistema aprendeu com os seus ajustes nos vídeos publicados"
      >
        <GraduationCap className="size-4" /> Aprendizado{pendentes.length ? ` · ${pendentes.length} para aprovar` : ''}
      </button>
      {aberto && (
        <div className="absolute left-0 top-full z-40 mt-2 w-[min(720px,90vw)] rounded-xl border border-borda bg-painel p-4 shadow-2xl">
          <p className="mb-1 text-sm font-medium">Aprendizado entre vídeos</p>
          <p className="mb-3 text-xs text-suave">
            A cada vídeo publicado, o sistema estuda os seus ajustes do storyboard e propõe regras para o diretor. Só entra o
            que você aprovar (pode editar o texto antes). Além disso, {d.exemplos} correções suas de legenda já vão como
            exemplo para o diretor pegar o seu tom.
          </p>
          {pendentes.length === 0 && <p className="text-xs text-apagado">Nenhuma proposta esperando. A próxima vem quando você publicar um vídeo.</p>}
          <ul className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto">
            {pendentes.map((p) => (
              <li key={p.id} className="rounded-lg border border-borda bg-painel-2 p-3">
                <textarea
                  value={textos[p.id] ?? p.regra}
                  onChange={(e) => setTextos({ ...textos, [p.id]: e.target.value })}
                  className="w-full resize-y rounded-md border border-borda bg-painel p-2 text-sm outline-none focus:border-suave"
                  rows={2}
                />
                <p className="mt-1 text-[11px] text-apagado">
                  {p.evidencia} · vídeo: {p.video}
                </p>
                <div className="mt-2 flex gap-2">
                  <button onClick={() => decidir(p, 'aprovar')} className="rounded-md bg-ok px-3 py-1 text-xs font-semibold text-fundo hover:brightness-110">
                    Aprovar (entra nas regras)
                  </button>
                  <button onClick={() => decidir(p, 'recusar')} className="rounded-md border border-borda px-3 py-1 text-xs text-suave hover:text-texto">
                    Recusar
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {d.propostas.some((p) => p.status !== 'pendente') && (
            <details className="mt-3 text-xs text-suave">
              <summary className="cursor-pointer hover:text-texto">histórico ({d.propostas.filter((p) => p.status !== 'pendente').length})</summary>
              <ul className="mt-1 flex flex-col gap-1">
                {d.propostas
                  .filter((p) => p.status !== 'pendente')
                  .map((p) => (
                    <li key={p.id}>
                      <span className={p.status === 'aprovada' ? 'text-ok' : 'text-apagado'}>{p.status === 'aprovada' ? '✓' : '✗'}</span> {p.regra}
                    </li>
                  ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
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
