import { ArrowLeft, Columns2, Eraser, Loader2, MessageSquarePlus, Music, Play, RotateCcw, Search, Trash2, Wand2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, arquivo, useAoVivo, type Video } from '../api'
import { Moldura } from '../componentes/Moldura'
import { Progresso } from '../componentes/Progresso'

type Candidato = { idx: number; nome: string; tipo: string; miniatura: string }
type Cena = {
  k: number
  numero: string // fixo: dividir/remover cenas não renumera as outras (40, 40.1, 40.2…)
  id: string
  secao: string | null
  conferir: boolean
  tipo: string
  legenda: string | null
  frase: string
  inicio: number | null
  fim: number | null
  busca: string | null
  escolhido: Candidato | null
  metade2: { nome: string; miniatura: string } | null // meio a meio: imagem na outra metade (no lugar do texto)
  clipe: { midia_id: number; inicio: number; duracao: number } | null // vídeo original do clipe escolhido
  candidatos: Candidato[]
  pecas: Peca[] // itens de lista / tela dividida / mosaico (cada um com a própria imagem)
  recusada: boolean
  no_rascunho: boolean
  removida: boolean
  comentario: string | null
  comentario_aplicado: boolean
  motivo: string | null
  ajustada: boolean
  pendente: boolean // mexida depois que o último rascunho começou
  lado: string | null // meio a meio / citação: lado da imagem no rascunho
  sem_fundo: boolean // imagem com o fundo de cor lisa removido (cópia à parte)
  so_texto_no_video: boolean // no rascunho a cena entrou como texto (faltou imagem)
  palavras: { i: number; t: string }[] // narração da cena no rascunho (para escolher quando o texto entra)
  texto_em: number | null // palavra em que o texto entrou (null = junto com a imagem)
  fundo: string | null // texto: claro | escuro
  som: string | null
  som_no_rascunho: boolean
}
type Peca = { j: number; rotulo: string; busca: string | null; escolhido: Candidato | null; candidatos: Candidato[]; ajustada: boolean }
type Dados = { cenas: Cena[]; tipos: string[]; pedidos_pendentes: number; ajustes: number; pendentes: number; capa: string | null }

const NOME_TIPO: Record<string, string> = {
  capa: 'Capa', cartao: 'Cartão', telacheia: 'Tela cheia', recorte: 'Recorte', mosaico: 'Mosaico', clipe: 'Clipe', dialogo: 'Diálogo',
  meio: 'Meio a meio', texto: 'Só texto', citacao: 'Citação', dividida: 'Tela dividida', lista: 'Lista', hub: 'Transição de seção',
}
/** Para quais tipos uma cena pode virar sem perder as imagens que já tem. */
const UMA_IMAGEM = ['cartao', 'telacheia', 'recorte', 'meio', 'citacao']
function tiposPossiveis(atual: string, tipos: string[]): string[] {
  // "só texto" também pode virar cena com imagem (a imagem vem da busca no acervo)
  if (UMA_IMAGEM.includes(atual) || atual === 'texto') return tipos.filter((t) => UMA_IMAGEM.includes(t) || t === 'texto')
  // clipe pode virar cena de imagem: usa um quadro parado do próprio clipe (no momento escolhido) ou a imagem buscada
  if (atual === 'clipe') return ['clipe', ...tipos.filter((t) => UMA_IMAGEM.includes(t))]
  if (atual === 'mosaico') return ['mosaico', 'dividida', 'lista']
  if (atual === 'dividida' || atual === 'lista') return ['dividida', 'lista']
  return [atual]
}
const mmss = (s: number | null) => (s == null ? '—' : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`)

export function Storyboard({ id }: { id: number }) {
  const { dados: v, recarregar: recarregarVideo } = useAoVivo<Video>(`/videos/${id}`, 3000)
  const [enviando, setEnviando] = useState(false)
  const [sb, setSb] = useState<Dados | null>(null)
  const player = useRef<HTMLVideoElement>(null)
  const [agora, setAgora] = useState(0)

  const carregar = () => api<Dados>(`/videos/${id}/storyboard`).then(setSb)
  useEffect(() => {
    carregar()
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const direcao = v?.etapas.find((e) => e.chave === 'direcao')
  const rascunho = v?.etapas.find((e) => e.chave === 'rascunho')
  const trabalhando = enviando || direcao?.status === 'andamento'
  // quando o motor termina um rascunho novo, recarrega as cenas
  useEffect(() => {
    if (!trabalhando) carregar()
  }, [trabalhando, rascunho?.atualizado_em]) // eslint-disable-line react-hooks/exhaustive-deps

  const ajustar = async (cid: string, acao: Record<string, unknown>) => {
    await api(`/videos/${id}/storyboard/${encodeURIComponent(cid)}`, { method: 'POST', body: JSON.stringify(acao) })
    await carregar()
  }
  const irPara = (s: number | null) => {
    if (s == null || !player.current) return
    player.current.currentTime = s
    player.current.play()
  }
  const atual = sb?.cenas.find((c) => c.inicio != null && c.fim != null && agora >= c.inicio && agora < c.fim)

  const trilha = (
    <>
      <a href="#/" className="hover:text-texto">Quadro</a>
      <span className="text-apagado">/</span>
      <a href={`#/video/${id}`} className="truncate hover:text-texto">{v?.titulo ?? '…'}</a>
      <span className="text-apagado">/</span>
      <span className="text-texto">Storyboard</span>
    </>
  )
  const video = typeof rascunho?.dados.video === 'string' ? rascunho.dados.video : null

  return (
    <Moldura trilha={trilha}>
      <div className="mx-auto max-w-[1680px] px-6 py-5">
        <div className="mb-4 flex items-center gap-3">
          <a href={`#/video/${id}`} className="flex items-center gap-1.5 text-sm text-suave hover:text-texto">
            <ArrowLeft className="size-4" /> voltar ao vídeo
          </a>
          <h1 className="font-titulo text-3xl font-medium tracking-tight">Storyboard</h1>
          <span className="font-mono text-xs text-suave">
            {sb ? `${sb.cenas.length} cenas · ${rascunho?.detalhe ?? ''}` : '…'}
          </span>
          <div className="ml-auto flex items-center gap-3">
            {sb && (sb.ajustes > 0 || sb.pendentes > 0) && (
              <span className="flex items-center gap-2 font-mono text-xs">
                <span className="text-suave" title="Todas as cenas que você já ajustou neste vídeo">
                  {sb.ajustes} ajustada{sb.ajustes === 1 ? '' : 's'} no total
                </span>
                <span className="text-apagado">·</span>
                <span
                  className={sb.pendentes > 0 ? 'text-atencao' : 'text-ok'}
                  title="Cenas mexidas depois que o último rascunho começou: entram só no PRÓXIMO rascunho"
                >
                  {sb.pendentes > 0
                    ? `${sb.pendentes} pendente${sb.pendentes === 1 ? '' : 's'} (${trabalhando ? 'ficam para o rascunho seguinte' : 'entram no próximo rascunho'})`
                    : trabalhando ? 'tudo o que você pediu está neste rascunho' : 'nada pendente'}
                </span>
                {sb.pedidos_pendentes > 0 && !trabalhando && (
                  <span className="text-atencao">· {sb.pedidos_pendentes} pedido(s) ao diretor (usa o Claude)</span>
                )}
              </span>
            )}
            <button
              disabled={trabalhando || !sb}
              onClick={async () => {
                setEnviando(true) // reação imediata; o motor confirma em seguida
                try {
                  await api(`/videos/${id}/rascunho/refazer`, { method: 'POST' })
                  recarregarVideo()
                } finally {
                  setTimeout(() => setEnviando(false), 1500)
                }
              }}
              className="flex items-center gap-2 rounded-lg bg-ouro px-4 py-2 text-sm font-semibold text-fundo enabled:hover:brightness-110 disabled:opacity-40"
            >
              {trabalhando ? <Loader2 className="size-4 animate-spin" /> : <Wand2 className="size-4" />}
              {enviando && direcao?.status !== 'andamento' ? 'Enviando…' : trabalhando ? direcao?.resumo ?? 'trabalhando…' : 'Gerar novo rascunho'}
            </button>
          </div>
        </div>
        <div className="mb-4">
          <Progresso videoId={id} />
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          {/* player fixo */}
          <div className="lg:sticky lg:top-4 lg:self-start">
            {video ? (
              <video
                ref={player}
                key={`${video}-${rascunho?.atualizado_em}`}
                src={`${arquivo(video)}&v=${encodeURIComponent(rascunho?.atualizado_em ?? '')}`}
                controls
                onTimeUpdate={(e) => setAgora(e.currentTarget.currentTime)}
                className="w-full rounded-xl border border-borda bg-black"
              />
            ) : (
              <p className="text-sm text-suave">Ainda não há rascunho.</p>
            )}
            {atual && (
              <p className="mt-2 font-mono text-xs text-suave">
                tocando: cena {atual.numero ?? atual.k} · {NOME_TIPO[atual.tipo] ?? atual.tipo}
              </p>
            )}
          </div>

          {/* lista de cenas */}
          <div className="flex flex-col gap-3">
            {sb?.cenas.map((c) => (
              <CartaoCena key={c.id} cena={c} tipos={sb.tipos} capa={sb.capa} ativa={atual?.id === c.id} ajustar={ajustar} irPara={irPara} />
            ))}
          </div>
        </div>
      </div>
    </Moldura>
  )
}

function CartaoCena({
  cena: c,
  tipos,
  capa,
  ativa,
  ajustar,
  irPara,
}: {
  cena: Cena
  tipos: string[]
  capa: string | null
  ativa: boolean
  ajustar: (cid: string, acao: Record<string, unknown>) => Promise<void>
  irPara: (s: number | null) => void
}) {
  const [aba, setAba] = useState<'nada' | 'trocar' | 'pedir' | 'itens' | 'metade'>('nada')
  const [legenda, setLegenda] = useState(c.legenda ?? '')
  const [pedido, setPedido] = useState(c.comentario ?? '')
  const [consulta, setConsulta] = useState('')
  const [resultados, setResultados] = useState<{ midia_id: number; nome: string; miniatura: string }[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  useEffect(() => setLegenda(c.legenda ?? ''), [c.legenda])

  const temImagem = c.candidatos.length > 0
  // cena de UMA imagem (ou só texto): sempre dá para buscar uma imagem no acervo
  // lista e tela dividida só mostram as imagens dos ITENS: uma imagem da cena inteira ficaria sem uso (o mosaico a usa de fundo)
  const soItens = ['lista', 'dividida'].includes(c.tipo)
  const aceitaImagem = !soItens && (temImagem || [...UMA_IMAGEM, 'texto'].includes(c.tipo))
  const foraDoVideo = !c.no_rascunho && !c.removida
  const usaLegenda = ['cartao', 'recorte', 'meio', 'texto'].includes(c.tipo)
  const borda = c.removida
    ? 'border-dashed border-borda opacity-50'
    : ativa
      ? 'border-ouro'
      : c.recusada && !c.escolhido
        ? 'border-atencao/50'
        : c.ajustada
          ? 'border-andamento/50'
          : 'border-borda'

  return (
    <article className={`rounded-xl border bg-painel p-3 ${borda}`}>
      <div className="flex gap-3">
        <button
          onClick={() => irPara(c.inicio)}
          disabled={c.inicio == null}
          className="group relative h-[90px] w-[160px] shrink-0 overflow-hidden rounded-lg border border-borda bg-painel-2"
          title="Ver esta cena no player"
        >
          <MiniaturaDaCena c={c} capa={capa} />
          {c.inicio != null && (
            <span className="absolute inset-0 grid place-items-center bg-black/0 opacity-0 transition group-hover:bg-black/40 group-hover:opacity-100">
              <Play className="size-6 text-white" />
            </span>
          )}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-apagado">
              #{c.numero ?? c.k} · {mmss(c.inicio)}–{mmss(c.fim)}
            </span>
            <select
              value={c.tipo}
              onChange={(e) => ajustar(c.id, { acao: 'tipo', tipo: e.target.value })}
              disabled={tiposPossiveis(c.tipo, tipos).length < 2}
              className="rounded-md border border-borda bg-painel-2 px-1.5 py-0.5 text-xs"
            >
              {tiposPossiveis(c.tipo, tipos).map((t) => (
                <option key={t} value={t}>{NOME_TIPO[t] ?? t}</option>
              ))}
            </select>
            {c.tipo === 'meio' && (
              <span className="flex overflow-hidden rounded-md border border-borda text-[11px]" title="De que lado fica a imagem (o texto vai na outra metade)">
                {(['esq', 'dir'] as const).map((l) => (
                  <button
                    key={l}
                    onClick={() => ajustar(c.id, { acao: 'lado', lado: l })}
                    className={`px-2 py-0.5 ${c.lado === l ? 'bg-ouro/20 text-ouro' : 'text-suave hover:text-texto'}`}
                  >
                    imagem à {l === 'esq' ? 'esquerda' : 'direita'}
                  </button>
                ))}
              </span>
            )}
            {c.tipo === 'meio' && (
              <span className="flex items-center gap-1 text-[11px] text-suave" title="O que vai na OUTRA metade">
                outra metade:
                <span className="flex overflow-hidden rounded-md border border-borda">
                  <button
                    onClick={() => c.metade2 && ajustar(c.id, { acao: 'metade_texto' })}
                    className={`px-2 py-0.5 ${!c.metade2 ? 'bg-ouro/20 text-ouro' : 'hover:text-texto'}`}
                  >
                    texto
                  </button>
                  <button
                    onClick={() => setAba(aba === 'metade' ? 'nada' : 'metade')}
                    className={`px-2 py-0.5 ${c.metade2 ? 'bg-ouro/20 text-ouro' : 'hover:text-texto'}`}
                  >
                    imagem{c.metade2 ? `: ${c.metade2.nome}` : ''}
                  </button>
                </span>
              </span>
            )}
            {c.so_texto_no_video && !c.pendente && (c.escolhido || c.pecas.some((p) => p.escolhido)) && (
              <span className="text-[11px] text-atencao">
                no vídeo entrou só o texto: {c.pecas.length ? 'faltam imagens nos itens (mínimo 2)' : 'a imagem não pôde ser usada'}
              </span>
            )}
            {c.recusada && !c.escolhido && (
              <span className="text-[11px] text-atencao">
                nenhuma imagem serviu{c.no_rascunho ? ' · no rascunho entra só o texto: escolha uma imagem' : ''}
              </span>
            )}
            {c.comentario && (
              <span className={`text-[11px] ${c.comentario_aplicado ? 'text-ok' : 'text-andamento'}`}>
                {c.comentario_aplicado ? 'pedido atendido' : 'pedido ao diretor pendente'}
              </span>
            )}
            {c.ajustada && !c.removida && !c.comentario && <span className="text-[11px] text-andamento">ajustada</span>}
            {c.pendente && <span className="rounded bg-atencao/15 px-1.5 text-[11px] text-atencao">pendente · próximo rascunho</span>}
            {c.conferir && (
              <span className="flex items-center gap-1.5 text-[11px] text-atencao">
                a frase mudou no roteiro: confira a cena
                <button onClick={() => ajustar(c.id, { acao: 'conferido' })} className="rounded border border-atencao/50 px-1.5 hover:bg-atencao/10">
                  está ok
                </button>
              </span>
            )}
          </div>
          <p className="mt-1 line-clamp-2 text-sm text-texto/85">{c.frase || <i className="text-apagado">(não aparece no vídeo)</i>}</p>
          {foraDoVideo && (
            <p className="mt-1.5 rounded-md border border-atencao/40 bg-atencao/5 px-2 py-1.5 text-[11px] leading-snug text-atencao">
              Esta cena foi planejada, mas <b>não está no vídeo</b>: nenhuma imagem do acervo serviu, então a cena anterior
              continua na tela no lugar dela. Busque uma imagem, troque para “Só texto” ou remova a cena.
            </p>
          )}
          {c.som && (
            <p className="mt-1 flex items-center gap-1.5 text-[11px] text-suave">
              <Music className="size-3 shrink-0" />
              <span className="truncate">
                efeito sonoro: {c.som}
                {!c.som_no_rascunho && <span className="text-apagado"> (não entrou: limite de efeitos por minuto)</span>}
              </span>
              <button
                onClick={() => ajustar(c.id, { acao: 'sem_som' })}
                title="Tirar o efeito sonoro desta cena"
                className="ml-1 shrink-0 rounded px-1 text-apagado hover:text-red-300"
              >
                <X className="size-3" />
              </button>
            </p>
          )}
          {usaLegenda && c.tipo !== 'texto' && (c.palavras ?? []).length > 0 && <QuandoOTextoEntra c={c} ajustar={ajustar} />}
          {usaLegenda && (
            <input
              value={legenda}
              onChange={(e) => setLegenda(e.target.value)}
              onBlur={() => legenda !== (c.legenda ?? '') && ajustar(c.id, { acao: 'legenda', texto: legenda })}
              onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
              placeholder="legenda"
              className="mt-1.5 w-full rounded-md border border-borda bg-painel-2 px-2 py-1 text-sm outline-none focus:border-suave"
            />
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {aceitaImagem && (
              <Botao ativo={aba === 'trocar'} onClick={() => setAba(aba === 'trocar' ? 'nada' : 'trocar')}>
                <Search className="size-3.5" /> {c.clipe ? 'Trocar clipe / momento' : c.tipo === 'mosaico' ? 'Trocar fundo' : c.escolhido ? 'Trocar imagem' : c.tipo === 'texto' ? 'Pôr uma imagem' : 'Buscar imagem'}
              </Botao>
            )}
            {['cartao', 'telacheia', 'recorte', 'meio', 'citacao'].includes(c.tipo) && c.escolhido && !c.removida && (
              <Botao
                onClick={async () => {
                  try {
                    await ajustar(c.id, { acao: 'juntar_proxima' })
                  } catch (e) {
                    alert(e instanceof Error ? e.message : String(e))
                  }
                }}
              >
                <Columns2 className="size-3.5" /> Juntar com a próxima
              </Botao>
            )}
            {['cartao', 'telacheia', 'recorte', 'meio', 'citacao'].includes(c.tipo) && c.escolhido && !c.clipe && !c.removida && (
              <Botao
                ativo={c.sem_fundo}
                onClick={async () => {
                  try {
                    await ajustar(c.id, { acao: 'sem_fundo', ligar: !c.sem_fundo })
                  } catch (e) {
                    alert(e instanceof Error ? e.message : String(e))
                  }
                }}
              >
                <Eraser className="size-3.5" /> {c.sem_fundo ? 'Voltar o fundo' : 'Remover fundo'}
              </Botao>
            )}
            {c.pecas.length > 0 && (
              <Botao ativo={aba === 'itens'} onClick={() => setAba(aba === 'itens' ? 'nada' : 'itens')}>
                <Search className="size-3.5" /> Trocar imagens ({c.pecas.length} itens)
              </Botao>
            )}
            <Botao ativo={aba === 'pedir'} onClick={() => setAba(aba === 'pedir' ? 'nada' : 'pedir')}>
              <MessageSquarePlus className="size-3.5" /> Pedir ao diretor
            </Botao>
            {c.ajustada || c.removida ? (
              <Botao onClick={() => ajustar(c.id, { acao: 'restaurar' })}>
                <RotateCcw className="size-3.5" /> Desfazer ajustes
              </Botao>
            ) : (
              c.tipo !== 'capa' && (
                <Botao onClick={() => ajustar(c.id, { acao: 'remover' })}>
                  <Trash2 className="size-3.5" /> Remover cena
                </Botao>
              )
            )}
          </div>
        </div>
      </div>

      {aba === 'trocar' && (
        <div className="mt-3 border-t border-borda pt-3">
          {c.candidatos.length > 0 && <p className="mb-2 text-xs text-suave">Outros candidatos que o diretor considerou:</p>}
          <div className="grid grid-cols-4 gap-2">
            {c.candidatos.map((cand) => (
              <button
                key={cand.idx}
                onClick={() => ajustar(c.id, { acao: 'candidato', idx: cand.idx })}
                className={`overflow-hidden rounded-md border text-left ${c.escolhido?.idx === cand.idx ? 'border-ouro' : 'border-borda hover:border-suave'}`}
              >
                <img src={arquivo(cand.miniatura)} alt="" className="aspect-video w-full object-cover" />
                <span className="block truncate px-1.5 py-1 font-mono text-[10px] text-suave">{cand.nome}</span>
              </button>
            ))}
          </div>
          {c.clipe && <MomentoDoClipe clipe={c.clipe} usar={(s) => ajustar(c.id, { acao: 'clipe_inicio', segundos: s })} />}
          {c.tipo !== 'clipe' && (
            <>
              <div className="mt-3 flex gap-2">
                <input
                  value={consulta}
                  onChange={(e) => setConsulta(e.target.value)}
                  onKeyDown={async (e) => {
                    if (e.key !== 'Enter' || !consulta.trim()) return
                    setBuscando(true)
                    setResultados(await api(`/acervo/buscar?q=${encodeURIComponent(consulta)}&n=16`))
                    setBuscando(false)
                  }}
                  placeholder="Buscar outra no acervo (ex.: fiddlesticks milharal, corvos ao pôr do sol) e Enter"
                  className="flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-sm outline-none focus:border-suave"
                />
                {buscando && <Loader2 className="size-5 animate-spin self-center text-suave" />}
              </div>
              {resultados && (
                <div className="mt-2 grid grid-cols-4 gap-2">
                  {resultados.map((r) => (
                    <button
                      key={r.midia_id}
                      onClick={async () => {
                        await ajustar(c.id, { acao: 'usar_midia', midia_id: r.midia_id, nome: r.nome, miniatura: r.miniatura })
                        setResultados(null)
                        setAba('nada')
                      }}
                      className="overflow-hidden rounded-md border border-borda text-left hover:border-ouro"
                    >
                      <img src={arquivo(r.miniatura)} alt="" className="aspect-video w-full object-cover" />
                      <span className="block truncate px-1.5 py-1 font-mono text-[10px] text-suave">{r.nome}</span>
                    </button>
                  ))}
                </div>
              )}
              {resultados && resultados.length > 0 && resultados.length % 16 === 0 && (
                <button
                  disabled={buscando}
                  onClick={async () => {
                    // pede a lista maior e acrescenta só as novas (mesma ordem de relevância)
                    setBuscando(true)
                    const mais = await api<typeof resultados>(`/acervo/buscar?q=${encodeURIComponent(consulta)}&n=${resultados.length + 16}`)
                    setResultados(mais)
                    setBuscando(false)
                  }}
                  className="mt-2 w-full rounded-md border border-borda py-1.5 text-xs text-suave hover:border-suave hover:text-texto disabled:opacity-50"
                >
                  {buscando ? 'buscando…' : 'Mostrar mais'}
                </button>
              )}
            </>
          )}
        </div>
      )}

      {aba === 'metade' && (
        <div className="mt-3 border-t border-borda pt-3">
          <p className="mb-2 text-xs text-suave">
            Imagem para a outra metade (no lugar do texto; a legenda, se houver, aparece como rótulo sobre ela):
          </p>
          <ItemDaCena
            peca={{ j: 0, rotulo: 'outra metade', busca: null, escolhido: null, candidatos: [], ajustada: false }}
            ajustar={async (acao) => {
              await ajustar(c.id, { ...acao, acao: 'metade_usar_midia' })
              setAba('nada')
            }}
          />
        </div>
      )}

      {aba === 'itens' && (
        <div className="mt-3 space-y-3 border-t border-borda pt-3">
          {c.pecas.map((p) => (
            <ItemDaCena key={p.j} peca={p} ajustar={(acao) => ajustar(c.id, { ...acao, j: p.j })} />
          ))}
        </div>
      )}

      {aba === 'pedir' && (
        <div className="mt-3 border-t border-borda pt-3">
          <p className="mb-2 text-xs text-suave">
            Diga ao diretor o que mudar nesta cena. Ele refaz só as cenas com pedido (usa um pouco da cota do Claude).
          </p>
          <textarea
            value={pedido}
            onChange={(e) => setPedido(e.target.value)}
            placeholder="Ex.: aqui é metáfora, quero algo de destruição · use um clipe da cinemática · troque por um meme de choque"
            className="h-20 w-full resize-y rounded-md border border-borda bg-painel-2 p-2 text-sm outline-none focus:border-suave"
          />
          <div className="mt-2 flex justify-end">
            <button
              onClick={async () => {
                await ajustar(c.id, { acao: 'comentario', texto: pedido })
                setAba('nada')
              }}
              disabled={!pedido.trim()}
              className="rounded-md bg-andamento/90 px-3 py-1.5 text-xs font-semibold text-fundo disabled:opacity-40"
            >
              Guardar pedido
            </button>
          </div>
        </div>
      )}
    </article>
  )
}

function Botao({ children, onClick, ativo }: { children: React.ReactNode; onClick: () => void; ativo?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs ${
        ativo ? 'border-suave bg-painel-2 text-texto' : 'border-borda-forte text-suave hover:text-texto'
      }`}
    >
      {children}
    </button>
  )
}

/** Escolher o momento do clipe: o vídeo original do acervo com "usar a partir daqui". */
function MomentoDoClipe({ clipe, usar }: { clipe: { midia_id: number; inicio: number; duracao: number }; usar: (s: number) => Promise<void> }) {
  const ref = useRef<HTMLVideoElement>(null)
  const [t, setT] = useState(clipe.inicio)
  const [salvo, setSalvo] = useState(false)
  return (
    <div className="mb-3">
      <p className="mb-2 text-xs text-suave">
        Momento do clipe: posicione o vídeo onde a cena deve começar e clique em “Usar a partir daqui”.
      </p>
      <video
        ref={ref}
        src={`/api/acervo/video/${clipe.midia_id}#t=${clipe.inicio}`}
        controls
        muted
        preload="metadata"
        onTimeUpdate={(e) => setT(e.currentTarget.currentTime)}
        className="aspect-video w-full rounded-md border border-borda bg-black"
      />
      <div className="mt-2 flex items-center gap-3">
        <button
          onClick={async () => {
            await usar(t)
            setSalvo(true)
          }}
          className="rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
        >
          Usar a partir daqui ({mmss(t)})
        </button>
        <span className="font-mono text-[11px] text-apagado">
          {salvo ? 'salvo: entra no próximo rascunho' : `agora começa em ${mmss(clipe.inicio)}`}
        </span>
      </div>
    </div>
  )
}

/** Um item de lista / tela dividida / mosaico: imagem atual, candidatos do diretor e busca no acervo. */
function ItemDaCena({ peca, ajustar }: { peca: Peca; ajustar: (acao: Record<string, unknown>) => Promise<void> }) {
  const [consulta, setConsulta] = useState('')
  const [resultados, setResultados] = useState<{ midia_id: number; nome: string; miniatura: string }[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  const buscar = async (n: number) => {
    if (!consulta.trim()) return
    setBuscando(true)
    setResultados(await api(`/acervo/buscar?q=${encodeURIComponent(consulta)}&n=${n}`))
    setBuscando(false)
  }
  const miniatura = (cand: Candidato, ativo: boolean, onClick: () => void) => (
    <button
      key={`${cand.idx}-${cand.nome}`}
      onClick={onClick}
      className={`overflow-hidden rounded-md border text-left ${ativo ? 'border-ouro' : 'border-borda hover:border-suave'}`}
    >
      <img src={arquivo(cand.miniatura)} alt="" className="aspect-video w-full object-cover" />
      <span className="block truncate px-1.5 py-1 font-mono text-[10px] text-suave">{cand.nome}</span>
    </button>
  )
  return (
    <div className="rounded-lg border border-borda/70 p-2">
      <p className="mb-2 flex items-center gap-2 text-xs">
        <span className="font-mono text-apagado">item {peca.j + 1}</span>
        <b className="text-texto">{peca.rotulo || '(sem rótulo)'}</b>
        {!peca.escolhido && <span className="text-atencao">sem imagem</span>}
        {peca.ajustada && <span className="text-andamento">escolhida por você</span>}
      </p>
      <div className="grid grid-cols-6 gap-2">
        {peca.candidatos.map((cand) =>
          miniatura(cand, peca.escolhido?.idx === cand.idx, () => ajustar({ acao: 'peca_candidato', idx: cand.idx })),
        )}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar(16)}
          placeholder={`Buscar no acervo para “${peca.rotulo || 'este item'}” e Enter`}
          className="flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1 text-xs outline-none focus:border-suave"
        />
        {buscando && <Loader2 className="size-4 animate-spin self-center text-suave" />}
      </div>
      {resultados && (
        <>
          <div className="mt-2 grid grid-cols-6 gap-2">
            {resultados.map((r) =>
              miniatura({ idx: -1, nome: r.nome, tipo: 'midia', miniatura: r.miniatura }, false, async () => {
                await ajustar({ acao: 'peca_usar_midia', midia_id: r.midia_id, nome: r.nome, miniatura: r.miniatura })
                setResultados(null)
                setConsulta('')
              }),
            )}
          </div>
          {resultados.length > 0 && resultados.length % 16 === 0 && (
            <button
              disabled={buscando}
              onClick={() => buscar(resultados.length + 16)}
              className="mt-2 w-full rounded-md border border-borda py-1 text-[11px] text-suave hover:border-suave hover:text-texto"
            >
              Mostrar mais
            </button>
          )}
        </>
      )}
    </div>
  )
}

/**
 * Miniatura que REPRESENTA a cena como ela fica na tela (esquema 16:9, fundo branco do canal): cartão, recorte,
 * tela cheia, meio a meio, lista, tela dividida, mosaico, texto, capa/transição — com as imagens escolhidas.
 */
function MiniaturaDaCena({ c, capa }: { c: Cena; capa: string | null }) {
  if (c.so_texto_no_video && !c.pendente)
    return (
      <span className="grid h-full w-full place-items-center bg-[#f4f1ea] p-2 text-center text-[9px] font-semibold leading-tight text-neutral-800">
        {c.legenda || '[imagem pendente]'}
      </span>
    )
  const img = c.escolhido ? arquivo(c.escolhido.miniatura) : null
  const itens = c.pecas.filter((p) => p.escolhido).map((p) => ({ j: p.j, src: arquivo(p.escolhido!.miniatura), rotulo: p.rotulo }))
  const legenda = c.legenda ? <span className="line-clamp-1 px-1 text-center text-[7px] font-semibold leading-tight text-neutral-800">{c.legenda}</span> : null
  const branco = 'h-full w-full bg-[#f4f1ea]'
  const vazio = (txt: string) => (
    <span className={`grid ${branco} place-items-center px-2 text-center text-[10px] text-neutral-500`}>{txt}</span>
  )
  switch (c.tipo) {
    case 'capa':
    case 'hub':
      return capa ? <img src={arquivo(capa)} alt="" className="h-full w-full object-cover" /> : vazio('capa do vídeo')
    case 'dialogo':
      return capa ? <img src={arquivo(capa)} alt="" className="h-full w-full object-cover opacity-70" /> : vazio('diálogo')
    case 'telacheia':
    case 'clipe':
      return img ? (
        <span className="relative block h-full w-full">
          <img src={img} alt="" className="h-full w-full object-cover" />
          {c.tipo === 'clipe' && <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-[8px] text-white">clipe</span>}
        </span>
      ) : vazio('sem imagem')
    case 'cartao':
    case 'citacao':
      return img ? (
        <span className={`flex ${branco} flex-col items-center justify-center gap-1 p-1.5`}>
          <img src={img} alt="" className="max-h-[62px] max-w-[120px] rounded-sm object-cover shadow" />
          {legenda}
        </span>
      ) : vazio(c.legenda ? `“${c.legenda}” (sem imagem)` : 'sem imagem')
    case 'recorte':
      return img ? (
        <span className={`flex ${branco} flex-col items-center justify-center gap-0.5 p-1`}>
          <img src={img} alt="" className="max-h-[66px] max-w-[110px] object-contain" />
          {legenda}
        </span>
      ) : vazio('sem imagem')
    case 'meio':
      return img ? (
        <span className={`flex ${branco} ${c.lado === 'dir' ? 'flex-row-reverse' : ''}`}>
          <img src={img} alt="" className="h-full w-1/2 object-cover" />
          {c.metade2 ? (
            <span className="relative w-1/2">
              <img src={arquivo(c.metade2.miniatura)} alt="" className="h-full w-full object-cover" />
              {c.legenda && <span className="absolute inset-x-0 bottom-0 bg-white/85">{legenda}</span>}
            </span>
          ) : (
          <span className="grid w-1/2 place-items-center">{legenda ?? <span className="text-[8px] text-neutral-500">texto</span>}</span>
          )}
        </span>
      ) : vazio('sem imagem')
    case 'texto':
      return (
        <span className={`grid h-full w-full place-items-center p-2 ${c.fundo === 'escuro' ? 'bg-neutral-900 text-neutral-100' : 'bg-[#f4f1ea] text-neutral-800'}`}>
          <span className="line-clamp-3 text-center text-[9px] font-semibold leading-tight">{c.legenda || 'só texto'}</span>
        </span>
      )
    case 'lista':
      return itens.length ? (
        <span className={`flex ${branco} items-center justify-center gap-1 px-1.5`}>
          {itens.map((p) => (
            <span key={p.j} className="flex min-w-0 flex-1 flex-col items-center gap-0.5">
              <img src={p.src} alt="" className="aspect-[4/3] w-full rounded-sm object-cover shadow" />
              {p.rotulo && <span className="w-full truncate text-center text-[6px] font-semibold text-neutral-700">{p.rotulo}</span>}
            </span>
          ))}
        </span>
      ) : vazio('lista sem imagens')
    case 'dividida':
      return itens.length ? (
        <span className="flex h-full w-full gap-0.5 bg-white">
          {itens.map((p) => (
            <img key={p.j} src={p.src} alt="" className="h-full min-w-0 flex-1 object-cover" />
          ))}
        </span>
      ) : vazio('tela dividida sem imagens')
    case 'mosaico':
      return (
        <span className="relative block h-full w-full bg-[#f4f1ea]">
          {img && <img src={img} alt="" className="absolute inset-0 h-full w-full object-cover" />}
          <span className="absolute inset-0 flex items-center justify-center gap-1 px-2">
            {itens.map((p, k) => (
              <img
                key={p.j}
                src={p.src}
                alt=""
                className="w-[30%] rounded-sm border border-white object-cover shadow"
                style={{ transform: `rotate(${(k % 2 ? 1 : -1) * 4}deg)` }}
              />
            ))}
          </span>
        </span>
      )
    default:
      return img ? <img src={img} alt="" className="h-full w-full object-cover" /> : vazio('sem imagem')
  }
}

/** Quando o texto da cena entra: junto com a imagem ou numa palavra da narração (clique na palavra). Sem cota. */
function QuandoOTextoEntra({ c, ajustar }: { c: Cena; ajustar: (cid: string, acao: Record<string, unknown>) => Promise<void> }) {
  const [aberto, setAberto] = useState(false)
  const primeira = c.palavras[0]?.i
  const junto = c.texto_em == null || c.texto_em === primeira
  const palavra = c.palavras.find((p) => p.i === c.texto_em)?.t
  return (
    <div className="mt-1.5 text-[11px] text-suave">
      <button onClick={() => setAberto(!aberto)} className="hover:text-texto">
        o texto entra: <b className="text-texto">{junto ? 'junto com a imagem' : `em “${palavra ?? '…'}”`}</b>{' '}
        <span className="text-apagado">({aberto ? 'fechar' : 'mudar'})</span>
      </button>
      {aberto && (
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <button
            onClick={() => ajustar(c.id, { acao: 'legenda_em', indice: -1 })}
            className={`rounded border px-1.5 py-0.5 ${junto ? 'border-ouro text-ouro' : 'border-borda hover:border-suave'}`}
          >
            junto com a imagem
          </button>
          <span className="text-apagado">ou na palavra:</span>
          {c.palavras.slice(1).map((p) => (
            <button
              key={p.i}
              onClick={() => ajustar(c.id, { acao: 'legenda_em', indice: p.i })}
              className={`rounded px-1 py-0.5 ${c.texto_em === p.i ? 'bg-ouro/20 text-ouro' : 'hover:bg-painel-2 hover:text-texto'}`}
            >
              {p.t}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}