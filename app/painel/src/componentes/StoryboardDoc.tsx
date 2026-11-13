import { Check, Film, RefreshCw, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api, arquivo, useAoVivo } from '../api'
import { BotaoMic, EstadoDitado, useDitado } from './Ditado'

/** Storyboard do Rascunho do documentário (fase 7b): uma linha por cena da SPEC, como o storyboard do Runeterra.
 *  Quadros de prévia = o próprio trecho do montador (gerado sob demanda, cache por hash), nos momentos-chave.
 *  Ações diretas (movimento, entrada, corte, SFX, escolhas fechadas do kit) entram na SPEC na hora, sem modelo, e só
 *  a cena afetada é renderizada de novo. Qualquer outro pedido (texto ou voz) vai para o orquestrador, só desta cena. */

type Momento = { q: number; t: number; rotulo: string; i: number; arquivo?: string }
type Sfx = { categoria: string; em: string; i: number; ponto?: string; intensidade?: number }
type CenaSB = {
  id: string; n: number; em: string; i0: number; i1: number; t0: number; t1: number; capitulo: string; objetivo: string
  motor: string; kits: { kit: string; params: Record<string, unknown> }[]; texto_tela: string[]; camera?: string | null
  movimento?: { tipo: string; intensidade?: number } | null; transicao: { tipo: string; quadros: number }; sfx: Sfx[]
  frases: { i: number; t: number; texto: string }[]; momentos: Momento[]; quadros: Momento[]; hash: string | null
  estado: string; problema?: string | null; falha?: string | null; no_rascunho?: boolean | null
}
type SB = { cenas: CenaSB[]; tempos: string; gerando: string[]; aviso: string | null; palavras: string[]; contagem: Record<string, number> }
type PedidoDoc = { id: string; etapa: string; cena?: string; texto: string; status: string }

const ESTADO: Record<string, [string, string]> = {
  aprovada: ['aprovada ★', 'text-ok border-ok/50'],
  pronta: ['prévia pronta · aprove ★', 'text-atencao border-atencao/50'],
  desatualizada: ['desatualizada', 'text-atencao border-atencao/50'],
  sem_previa: ['sem prévia', 'text-apagado border-borda'],
  gerando: ['renderizando…', 'text-andamento border-andamento/50'],
  falhou: ['prévia falhou', 'text-atencao border-atencao/50'],
  sem_receita: ['sem receita no montador', 'text-atencao border-atencao/50'],
}
const MOVIMENTOS: [string, string][] = [
  ['parado', 'parado'], ['aproximar', 'zoom: aproximar'], ['afastar', 'zoom: afastar'], ['pan_esq', 'pan ←'], ['pan_dir', 'pan →'],
  ['subir', 'subir ↑'], ['descer', 'descer ↓'],
]
const TRANSICOES = ['corte', 'fade', 'wipe', 'zoom']
const SFX = ['impacto', 'riser', 'whoosh', 'sino', 'alerta', 'pop', 'clique', 'tecla', 'capitulo']
const seg = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`
const limpar = (e: unknown) => String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)
const sel = 'rounded border border-borda bg-painel px-1.5 py-1 text-[11px] outline-none focus:border-suave disabled:opacity-40'

export function StoryboardDoc({ videoId, pedidos, aoMudar }: { videoId: number; pedidos: PedidoDoc[]; aoMudar: () => void }) {
  const { dados: sb, erro: erroLeitura, setDados } = useAoVivo<SB>(`/videos/${videoId}/doc/storyboard`, 4000)
  const [erro, setErro] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState<string | null>(null) // id da cena (ou "todas") com ação em curso

  if (!sb) return <p className="text-sm text-suave">{erroLeitura ? limpar(erroLeitura) : 'Carregando o storyboard…'}</p>
  if (!sb.cenas.length) return <p className="text-sm text-suave">Sem SPEC ainda: o storyboard aparece quando a SPEC existir.</p>

  const agir = async (quem: string, caminho: string, corpo: unknown, ok?: (r: Record<string, unknown>) => string | null) => {
    setErro(null)
    setAviso(null)
    setOcupado(quem)
    try {
      const r = await api<Record<string, unknown>>(caminho, { method: 'POST', body: JSON.stringify(corpo) })
      const novo = (r.storyboard ?? (r.cenas ? r : null)) as SB | null
      if (novo) setDados(novo)
      setAviso(ok ? ok(r) : null)
      aoMudar()
      return true
    } catch (e) {
      setErro(limpar(e))
      return false
    } finally {
      setOcupado(null)
    }
  }
  const ajustar = (c: CenaSB, acao: Record<string, unknown>) =>
    agir(c.id, `/videos/${videoId}/doc/cena/${c.id}/ajuste`, { acao }, (r) => {
      const a = r.ajuste as { descricao: string; afetadas: string[] }
      return `Cena ${c.n}: ${a.descricao}. ` + (a.afetadas.length ? `Renderizando de novo só ${a.afetadas.length === 1 ? 'esta cena' : `${a.afetadas.length} cenas (vizinhas da transição/corte)`}.` : 'Nenhuma cena precisa de render (só o áudio muda).')
    })
  const previa = (cenas: string[] | null) =>
    agir(cenas?.[0] ?? 'todas', `/videos/${videoId}/doc/previa`, { cenas }, () => 'Prévia em andamento: cada cena renderiza no motor dela (o que já está no cache sai na hora).')
  const semPrevia = sb.cenas.filter((c) => ['sem_previa', 'desatualizada', 'falhou'].includes(c.estado)).map((c) => c.id)

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] text-apagado">
          {sb.cenas.length} cenas · tempos {sb.tempos} ·{' '}
          {Object.entries(sb.contagem).filter(([, n]) => n).map(([k, n]) => `${n} ${ESTADO[k]?.[0].replace(' · aprove ★', '') ?? k}`).join(' · ')}
        </span>
        <button
          disabled={Boolean(ocupado) || !semPrevia.length}
          onClick={() => previa(semPrevia)}
          className="ml-auto flex items-center gap-1 rounded-md border border-ouro/60 px-2.5 py-1 text-[11px] text-ouro hover:bg-ouro/10 disabled:opacity-40"
        >
          <Film className="size-3.5" /> Gerar prévias que faltam ({semPrevia.length})
        </button>
      </div>
      {sb.aviso && <p className="mb-2 text-[11px] text-atencao">{sb.aviso}</p>}
      {erro && <p className="mb-2 text-xs text-atencao">{erro}</p>}
      {aviso && <p className="mb-2 text-xs text-ok">{aviso}</p>}
      <ol className="flex flex-col gap-3" aria-label="Storyboard">
        {sb.cenas.map((c, k) => (
          <LinhaCena
            key={c.id}
            c={c}
            ant={sb.cenas[k - 1]}
            prox={sb.cenas[k + 1]}
            palavras={sb.palavras}
            ocupado={ocupado === c.id}
            bloqueado={Boolean(ocupado)}
            pedidos={pedidos.filter((p) => p.cena === c.id && p.etapa === 'spec')}
            videoId={videoId}
            ajustar={(a) => ajustar(c, a)}
            previa={() => previa([c.id])}
            aprovar={() => agir(c.id, `/videos/${videoId}/doc/cena/${c.id}/aprovar`, {}, () => `Cena ${c.n} aprovada ★`)}
            pedir={(texto, origem) =>
              agir(c.id, `/videos/${videoId}/doc/cena/${c.id}/pedido`, { texto, origem }, (r) => {
                const p = r.pedido as { prompt: string[] | null; aviso: string | null }
                return p.prompt ? 'Pedido enviado: prompt só desta cena pronto para o orquestrador (pendência no card).' : `Pedido guardado. ${p.aviso ?? ''}`
              })
            }
            retirar={(pid) => api(`/videos/${videoId}/doc/pedido/${pid}`, { method: 'DELETE' }).then(aoMudar).catch((e) => setErro(limpar(e)))}
          />
        ))}
      </ol>
    </div>
  )
}

function LinhaCena({ c, ant, prox, palavras, ocupado, bloqueado, pedidos, videoId, ajustar, previa, aprovar, pedir, retirar }: {
  c: CenaSB; ant?: CenaSB; prox?: CenaSB; palavras: string[]; ocupado: boolean; bloqueado: boolean; pedidos: PedidoDoc[]; videoId: number
  ajustar: (a: Record<string, unknown>) => void; previa: () => void; aprovar: () => void
  pedir: (texto: string, origem: 'texto' | 'voz') => Promise<boolean>; retirar: (pid: string) => void
}) {
  const [texto, setTexto] = useState('')
  const [origem, setOrigem] = useState<'texto' | 'voz'>('texto')
  const [aberto, setAberto] = useState(false)
  const dit = useDitado(videoId, (novo) => {
    setTexto((atual) => (atual.trim() ? `${atual.trimEnd()} ${novo}` : novo))
    setOrigem('voz')
    setAberto(true)
  })
  const [rot, cor] = ESTADO[c.estado] ?? [c.estado, 'text-suave border-borda']
  const intervalo = (de: number, ate: number) => Array.from({ length: Math.max(0, ate - de) }, (_, n) => de + n)
  const pal = (i: number) => `${palavras[i] ?? '?'} (${i})`
  const abertos = pedidos.filter((p) => p.status === 'aberto')
  const gps = c.kits.find((u) => u.kit === 'gps')
  const graf = c.kits.find((u) => u.kit === 'graficos')
  const dis = bloqueado || c.estado === 'gerando'

  return (
    <li data-cena={c.id} className="rounded-lg border border-borda bg-painel-2 p-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-[11px] text-apagado">{String(c.n).padStart(2, '0')} · {c.id} · {seg(c.t0)}–{seg(c.t1)} · {c.capitulo}</span>
        <span className="rounded bg-ouro/15 px-1.5 py-0.5 font-mono text-[10px] text-ouro">{c.motor}</span>
        <span className="font-mono text-[10px] text-apagado">kits: {c.kits.map((u) => u.kit).join(', ') || '—'}</span>
        <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${cor}`} data-estado={c.estado}>{rot}</span>
        {c.no_rascunho === false && <span className="font-mono text-[10px] text-atencao">diferente do último rascunho</span>}
        <span className="ml-auto flex items-center gap-2">
          <button disabled={dis} onClick={previa} className="flex items-center gap-1 text-[11px] text-suave hover:text-texto disabled:opacity-40" title="Renderiza (ou acha no cache) só esta cena">
            <RefreshCw className={`size-3 ${c.estado === 'gerando' ? 'animate-spin' : ''}`} /> prévia
          </button>
          <button
            disabled={dis || c.estado !== 'pronta'}
            onClick={aprovar}
            className="flex items-center gap-1 rounded bg-ok px-2 py-0.5 text-[11px] font-semibold text-fundo hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-30"
          >
            <Check className="size-3" /> Aprovar ★
          </button>
        </span>
      </div>

      {/* quadros de prévia nos momentos-chave */}
      {c.quadros.length > 0 ? (
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
          {c.quadros.map((q) => (
            <figure key={q.q} className="w-44 shrink-0">
              <img src={arquivo(q.arquivo!)} alt={`cena ${c.n}: ${q.rotulo}`} loading="lazy" className="aspect-video w-full rounded border border-borda object-cover" />
              <figcaption className="mt-0.5 line-clamp-2 font-mono text-[10px] text-apagado">{seg(q.t)} · {q.rotulo}</figcaption>
            </figure>
          ))}
        </div>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {c.momentos.map((m) => (
            <span key={m.q} className="rounded border border-dashed border-borda px-2 py-1 font-mono text-[10px] text-apagado">{seg(m.t)} · {m.rotulo}</span>
          ))}
        </div>
      )}
      {c.problema && <p className="mt-1 text-[11px] text-atencao">{c.problema}</p>}
      {c.falha && <p className="mt-1 break-all text-[11px] text-atencao">falhou: {c.falha}</p>}

      {/* texto falado em frases + o que a cena mostra */}
      <div className="mt-2 grid gap-1 text-sm">
        {c.frases.map((f) => (
          <p key={f.i} className="text-texto/90"><span className="mr-1 font-mono text-[10px] text-apagado">{seg(f.t)}</span>{f.texto}</p>
        ))}
        <p className="text-xs text-suave">{c.objetivo}{c.texto_tela.length ? ` · tela: ${c.texto_tela.join(' | ')}` : ''}{c.camera ? ` · câmera: ${c.camera}` : ''}</p>
      </div>

      {/* ações diretas (na hora, sem modelo) */}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-borda/60 pt-2 text-[11px] text-suave">
        <label className="flex items-center gap-1">
          câmera
          <select aria-label="Movimento de câmera" disabled={dis} value={c.movimento?.tipo ?? 'parado'} onChange={(e) => ajustar({ acao: 'movimento', tipo: e.target.value, intensidade: c.movimento?.intensidade })} className={sel}>
            {MOVIMENTOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
          {c.movimento && (
            <select aria-label="Intensidade do movimento" disabled={dis} value={String(c.movimento.intensidade ?? 0.08)} onChange={(e) => ajustar({ acao: 'movimento', tipo: c.movimento!.tipo, intensidade: Number(e.target.value) })} className={sel}>
              {[0.04, 0.08, 0.12, 0.2].map((x) => <option key={x} value={String(x)}>{Math.round(x * 100)}%</option>)}
            </select>
          )}
        </label>
        {ant && (
          <label className="flex items-center gap-1">
            entrada
            <select aria-label="Entrada da cena" disabled={dis} value={c.transicao.tipo} onChange={(e) => ajustar({ acao: 'transicao', tipo: e.target.value })} className={sel}>
              {TRANSICOES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            {c.transicao.tipo !== 'corte' && (
              <select aria-label="Quadros da entrada" disabled={dis} value={c.transicao.quadros} onChange={(e) => ajustar({ acao: 'transicao', tipo: c.transicao.tipo, quadros: Number(e.target.value) })} className={sel}>
                {[...new Set([12, 18, 24, 30, 45, c.transicao.quadros])].sort((a, b) => a - b).map((q) => <option key={q} value={q}>{q} q</option>)}
              </select>
            )}
          </label>
        )}
        {ant && (
          <label className="flex items-center gap-1">
            começa em
            <select aria-label="A cena começa em" disabled={dis} value={c.i0} onChange={(e) => ajustar({ acao: 'corte', indice: Number(e.target.value) })} className={`${sel} max-w-40`}>
              {intervalo(ant.i0 + 1, c.i1).map((i) => <option key={i} value={i}>{pal(i)}</option>)}
            </select>
          </label>
        )}
        {prox && (
          <label className="flex items-center gap-1">
            termina antes de
            <select aria-label="A cena termina antes de" disabled={dis} value={c.i1} onChange={(e) => ajustar({ acao: 'fim', indice: Number(e.target.value) })} className={`${sel} max-w-40`}>
              {intervalo(c.i0 + 1, prox.i1).map((i) => <option key={i} value={i}>{pal(i)}</option>)}
            </select>
          </label>
        )}
        {gps && (
          <label className="flex items-center gap-1">
            GPS
            <select aria-label="Câmera do GPS" disabled={dis} value={String(gps.params.camera_gps ?? 'perseguicao')} onChange={(e) => ajustar({ acao: 'kit', kit: 'gps', param: 'camera_gps', valor: e.target.value })} className={sel}>
              <option value="perseguicao">perseguindo</option>
              <option value="fixa">fixa</option>
            </select>
          </label>
        )}
        {graf && (
          <label className="flex items-center gap-1">
            <input type="checkbox" disabled={dis} checked={Boolean(graf.params.minimapa)} onChange={(e) => ajustar({ acao: 'kit', kit: 'graficos', param: 'minimapa', valor: e.target.checked })} />
            minimapa
          </label>
        )}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-suave">
        <span>SFX:</span>
        {c.sfx.map((s, j) => (
          <span key={`${j}-${s.i}`} className="flex items-center gap-1 rounded border border-borda px-1 py-0.5">
            <select aria-label={`Categoria do SFX ${j + 1}`} disabled={dis} value={s.categoria} onChange={(e) => ajustar({ acao: 'sfx', j, categoria: e.target.value })} className={sel}>
              {SFX.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
            em
            <select aria-label={`Palavra do SFX ${j + 1}`} disabled={dis} value={s.i} onChange={(e) => ajustar({ acao: 'sfx', j, indice: Number(e.target.value) })} className={`${sel} max-w-32`}>
              {intervalo(c.i0, c.i1).map((i) => <option key={i} value={i}>{pal(i)}</option>)}
            </select>
            <button aria-label={`Remover SFX ${j + 1}`} disabled={dis} onClick={() => ajustar({ acao: 'sfx', j, remover: true })} className="text-apagado hover:text-atencao disabled:opacity-40">
              <Trash2 className="size-3" />
            </button>
          </span>
        ))}
        <button disabled={dis} onClick={() => ajustar({ acao: 'sfx', categoria: 'impacto', indice: c.i0 })} className="text-ouro hover:underline disabled:opacity-40">+ SFX</button>
        {ocupado && <span className="font-mono text-andamento">aplicando…</span>}
      </div>

      {/* pedido por cena: texto ou voz → orquestrador (prompt só desta cena) */}
      {abertos.map((p) => (
        <p key={p.id} className="mt-1 flex items-start gap-2 text-[11px]">
          <span className="font-mono text-atencao">{p.id} · com o orquestrador</span>
          <span className="text-texto/85">{p.texto}</span>
          <button onClick={() => retirar(p.id)} className="ml-auto shrink-0 text-apagado hover:text-atencao">retirar</button>
        </p>
      ))}
      <div className="mt-2 flex items-start gap-2">
        <BotaoMic d={dit} rotulo={`Corrigir a cena ${c.n} por voz`} pequeno />
        {aberto || texto ? (
          <textarea
            aria-label={`Pedido para a cena ${c.n}`}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={2}
            placeholder="o que mudar nesta cena (vai para o orquestrador)"
            className="min-w-0 flex-1 resize-y rounded-md border border-borda bg-painel px-2 py-1.5 text-xs outline-none focus:border-ouro/60"
          />
        ) : (
          <button onClick={() => setAberto(true)} className="self-center text-[11px] text-ouro hover:underline">corrigir por texto ou voz…</button>
        )}
        {(aberto || texto) && (
          <button
            disabled={bloqueado || !texto.trim() || Boolean(dit.transcrevendo) || dit.gravando}
            onClick={async () => {
              if (await pedir(texto, origem)) {
                setTexto('')
                setOrigem('texto')
                setAberto(false)
              }
            }}
            className="flex items-center gap-1 self-center rounded-md border border-ouro/60 px-2.5 py-1.5 text-[11px] text-ouro hover:bg-ouro/10 disabled:opacity-40"
          >
            <Send className="size-3" /> Enviar
          </button>
        )}
      </div>
      <EstadoDitado d={dit} />
    </li>
  )
}
