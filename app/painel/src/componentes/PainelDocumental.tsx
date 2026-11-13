import { useState } from 'react'
import { api, useAoVivo } from '../api'

/** Documentário horizontal (card formato "horizontal_doc"): o diretor documental do canal, pelo estado.json.
 *  História ★ → SPEC ★ → Ativos → Verificação → Rascunho ★. O painel não chama o Claude: o que precisa do modelo
 *  vira prompt + pendência para o orquestrador. Ver F1/horizontal/docs/painel.md. */

type EtapaDoc = { status: string; resumo?: string; aprovado_em?: string; atualizado_em?: string }
type PedidoDoc = { id: string; etapa: string; cena?: string; texto: string; status: string; criado_em: string; resposta?: string }
type Capitulo = { id: string; titulo: string; funcao: string; ritmo: string; em: string }
type Afirmacao = { id: string; texto: string; em: string; capitulo: string; tipo: string; verificavel: boolean }
type Historia = { titulo: string; tese: string; tempos: string; capitulos: Capitulo[]; afirmacoes: Afirmacao[]; avisos?: string[] }
type Cena = {
  id: string; em: string; t0: number; t1: number; capitulo: string; objetivo: string; camera?: string; motor: string
  kits: { kit: string; params: Record<string, unknown> }[]; afirmacoes: string[]; texto?: string[]
  sfx: { categoria: string; em: string }[]; transicao: { tipo: string; quadros: number }; notas?: string
}
type Spec = { tempos: string; cenas: Cena[]; avisos?: string[] }
type Item = { id: string; cena: string; cenas?: string[]; tipo: string; status: string; descricao: string; arquivo?: string | null; comando?: string }
type Achado = { codigo: string; msg: string; cena?: string | null }
type Verificacao = { status: string; contagem: { erros: number; pendencias: number; avisos: number }; erros: Achado[]; pendencias: Achado[]; avisos: Achado[] }
type Tarefa = { etapa: string; cena: string | null; prompt: string; comando: string }
type Doc = {
  estado: { etapa_atual: string; etapas: Record<string, EtapaDoc>; pedidos: PedidoDoc[] }
  titulos: Record<string, string>
  aprovacao: Record<string, boolean>
  entradas: { roteiro: boolean; palavras: number; tempos: string | null; briefing: boolean }
  avisos_entrada: string[]
  historia: Historia | null
  spec: Spec | null
  ativos: { resumo: Record<string, number>; itens: Item[] } | null
  verificacao: Verificacao | null
  orquestrador: Tarefa[]
  montador: boolean
  rascunho: string | null
}

const ETAPAS = ['historia', 'spec', 'ativos', 'verificacao', 'rascunho'] as const
const ROTULO: Record<string, string> = {
  pendente: 'aguardando', prompt_pronto: 'com o orquestrador', gerado: 'gerado', aprovado: 'aprovado',
  mudanca_pedida: 'mudança pedida', desatualizado: 'desatualizado', falhou: 'falhou', pronto: 'pronto',
}
const COR: Record<string, string> = {
  pendente: 'text-apagado', prompt_pronto: 'text-andamento', gerado: 'text-atencao', aprovado: 'text-ok',
  mudanca_pedida: 'text-atencao', desatualizado: 'text-atencao', falhou: 'text-atencao', pronto: 'text-ok',
}
const COR_ATIVO: Record<string, string> = {
  pronto: 'text-ok', falta: 'text-atencao', nao_validado: 'text-atencao', reprovado: 'text-atencao', nao_encontrado: 'text-atencao',
}
const BOTAO: Record<string, string> = {
  historia: 'Gerar prompt da História', spec: 'Gerar prompt da SPEC', ativos: 'Resolver ativos', verificacao: 'Verificar', rascunho: 'Montar rascunho',
}
const seg = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`
const limpar = (e: unknown) => String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)

export function PainelDocumental({ videoId, aoMudar }: { videoId: number; aoMudar: () => void }) {
  const { dados: d, erro: erroLeitura, setDados } = useAoVivo<Doc>(`/videos/${videoId}/doc`, 5000)
  const [aba, setAba] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)

  if (!d) return <section id="documentario" className="rounded-xl border border-borda bg-painel p-4 text-sm text-suave">{erroLeitura ? limpar(erroLeitura) : 'Carregando o documentário…'}</section>

  const atual = aba ?? (d.estado.etapa_atual === 'pronto' ? 'rascunho' : d.estado.etapa_atual)
  const reg = d.estado.etapas[atual]
  const abertos = d.estado.pedidos.filter((p) => p.etapa === atual && p.status === 'aberto')

  const agir = async (caminho: string, opcoes?: RequestInit, ok?: (r: Doc & { passo?: Record<string, unknown> }) => string | null) => {
    setErro(null)
    setAviso(null)
    setOcupado(true)
    try {
      const r = await api<Doc & { passo?: Record<string, unknown> }>(caminho, opcoes)
      setDados(r)
      setAviso(ok ? ok(r) : null)
      aoMudar()
    } catch (e) {
      setErro(limpar(e))
    } finally {
      setOcupado(false)
    }
  }
  const passo = () =>
    agir(`/videos/${videoId}/doc/passo/${atual}`, { method: 'POST' }, (r) =>
      r.passo?.do_cache ? 'Resposta já guardada para este mesmo prompt: aplicada sem gastar cota.'
        : r.passo?.precisa_modelo ? 'Prompt pronto. O orquestrador (chat) roda o prompt e aplica a resposta; a pendência mostra o comando.'
          : 'Feito.')
  const aprovar = () => agir(`/videos/${videoId}/doc/aprovar/${atual}`, { method: 'POST' }, () => `${d.titulos[atual]} aprovada ★`)
  const pedir = (texto: string, cena?: string) =>
    agir(`/videos/${videoId}/doc/pedido`, { method: 'POST', body: JSON.stringify({ etapa: atual, texto, cena: cena ?? null }) })
  const retirar = (id: string) => agir(`/videos/${videoId}/doc/pedido/${id}`, { method: 'DELETE' })

  const podeAprovar = d.aprovacao[atual] && ['gerado', 'mudanca_pedida'].includes(reg.status)
  const semMontador = atual === 'rascunho' && !d.montador

  return (
    <section id="documentario" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">Documentário</h2>
        <span className="font-mono text-[11px] text-apagado">
          roteiro {d.entradas.roteiro ? 'ok' : 'falta'} · {d.entradas.palavras} palavras · tempos {d.entradas.tempos ?? '—'}
          {d.entradas.briefing ? ' · com briefing' : ''}
        </span>
      </header>
      {d.avisos_entrada.map((a) => (
        <p key={a} className="mb-2 rounded-md border border-atencao/30 bg-atencao/5 px-3 py-2 text-xs text-atencao">{a}</p>
      ))}

      <nav className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Etapas do documentário">
        {ETAPAS.map((n) => {
          const bruto = d.estado.etapas[n].status
          const st = bruto === 'gerado' && !d.aprovacao[n] ? 'pronto' : bruto // sem ★: gerado = pronto
          const rasc = n === 'rascunho' && !d.montador
          return (
            <button
              key={n}
              onClick={() => setAba(n)}
              className={`rounded-lg border px-3 py-2 text-left ${atual === n ? 'border-ouro/70 bg-ouro/5' : 'border-borda hover:border-borda-forte'}`}
            >
              <span className="block text-sm font-medium">{d.titulos[n]}{d.aprovacao[n] ? ' ★' : ''}</span>
              <span className={`block font-mono text-[11px] ${rasc ? 'text-apagado' : COR[st]}`}>{rasc ? 'sem montador ainda' : ROTULO[st] ?? st}</span>
            </button>
          )
        })}
      </nav>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          disabled={ocupado || semMontador}
          onClick={passo}
          title={semMontador ? 'O montador (fase 5) ainda não existe' : undefined}
          className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {semMontador ? 'Rascunho: sem montador ainda' : abertos.length && ['historia', 'spec'].includes(atual) ? 'Gerar nova versão com os pedidos' : BOTAO[atual]}
        </button>
        {d.aprovacao[atual] && !semMontador && (
          <button
            disabled={ocupado || !podeAprovar}
            onClick={aprovar}
            className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Aprovar {d.titulos[atual]} ★
          </button>
        )}
        <span className="font-mono text-[11px] text-apagado">{reg.resumo ?? ''}</span>
      </div>
      {erro && <p className="mt-2 text-xs text-atencao">{erro}</p>}
      {aviso && <p className="mt-2 text-xs text-ok">{aviso}</p>}

      {d.orquestrador.length > 0 && (
        <div className="mt-3 rounded-lg border border-andamento/40 bg-andamento/5 p-3">
          <h3 className="text-xs font-semibold text-andamento">Para o orquestrador (o painel não chama o Claude)</h3>
          <ul className="mt-1 flex flex-col gap-2">
            {d.orquestrador.map((t) => (
              <li key={t.prompt} className="text-[11px]">
                <p className="text-suave">{d.titulos[t.etapa]}{t.cena ? ` · cena ${t.cena}` : ''}: rodar o prompt e gravar a resposta JSON</p>
                <code className="block break-all font-mono text-apagado">{t.prompt}</code>
                <code className="mt-0.5 block break-all font-mono text-texto/80">{t.comando}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4">
        {atual === 'historia' && <VerHistoria h={d.historia} />}
        {atual === 'spec' && (
          <VerSpec s={d.spec} v={d.verificacao} ativos={d.ativos} pedidos={d.estado.pedidos} ocupado={ocupado} pedir={pedir} retirar={retirar} />
        )}
        {atual === 'ativos' && <VerAtivos a={d.ativos} />}
        {atual === 'verificacao' && <VerVerificacao v={d.verificacao} />}
        {atual === 'rascunho' && (
          <p className="text-sm text-suave">
            {d.montador ? 'Montador disponível.' : 'Sem montador ainda: a montagem por cena e a mixagem única entram na fase 5 (F1/horizontal/montador/). Esta etapa é só o gancho.'}
          </p>
        )}
      </div>

      {['historia', 'spec'].includes(atual) && (
        <PedidosDaEtapa pedidos={d.estado.pedidos.filter((p) => p.etapa === atual)} ocupado={ocupado} pedir={(t) => pedir(t)} retirar={retirar} />
      )}
    </section>
  )
}

function VerHistoria({ h }: { h: Historia | null }) {
  if (!h) return <p className="text-sm text-suave">Ainda sem história. Gere o prompt; o orquestrador devolve a resposta.</p>
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="font-titulo text-lg leading-snug">{h.titulo}</p>
        <p className="mt-1 text-sm text-texto/85">{h.tese}</p>
        <p className="mt-1 font-mono text-[11px] text-apagado">tempos {h.tempos}</p>
      </div>
      <ol className="flex flex-col gap-1.5">
        {h.capitulos.map((c) => (
          <li key={c.id} className="rounded-md border border-borda bg-painel-2 px-3 py-2 text-sm">
            <span className="font-mono text-[11px] text-apagado">{c.id} · {c.funcao} · {c.ritmo}</span>
            <p className="font-medium">{c.titulo}</p>
            <p className="text-xs text-suave">começa em “{c.em}”</p>
          </li>
        ))}
      </ol>
      <div>
        <h3 className="text-xs font-semibold">Afirmações ({h.afirmacoes.length})</h3>
        <ul className="mt-1 flex flex-col gap-1">
          {h.afirmacoes.map((a) => (
            <li key={a.id} className="text-xs">
              <span className="font-mono text-apagado">{a.id} · {a.capitulo} · {a.tipo}{a.verificavel ? ' · verificável' : ''}</span>{' '}
              <span className="text-texto/85">{a.texto}</span>
            </li>
          ))}
        </ul>
      </div>
      <Avisos lista={h.avisos} />
    </div>
  )
}

function VerSpec({ s, v, ativos, pedidos, ocupado, pedir, retirar }: {
  s: Spec | null; v: Verificacao | null; ativos: Doc['ativos']; pedidos: PedidoDoc[]; ocupado: boolean
  pedir: (texto: string, cena: string) => void; retirar: (id: string) => void
}) {
  const [aberta, setAberta] = useState<string | null>(null)
  const [texto, setTexto] = useState('')
  if (!s) return <p className="text-sm text-suave">Ainda sem SPEC. Aprove a história e gere o prompt da SPEC.</p>
  const achados = (cena: string) => [
    ...(v?.erros ?? []).filter((x) => x.cena === cena).map((x) => ({ ...x, nivel: 'erro' })),
    ...(v?.pendencias ?? []).filter((x) => x.cena === cena).map((x) => ({ ...x, nivel: 'pendência' })),
    ...(v?.avisos ?? []).filter((x) => x.cena === cena).map((x) => ({ ...x, nivel: 'aviso' })),
  ]
  const faltas = (cena: string) => (ativos?.itens ?? []).filter((i) => i.status !== 'pronto' && (i.cena === cena || i.cenas?.includes(cena)))
  return (
    <div>
      <p className="mb-2 font-mono text-[11px] text-apagado">{s.cenas.length} cenas · tempos {s.tempos}</p>
      <Avisos lista={s.avisos} />
      <ol className="flex flex-col gap-2">
        {s.cenas.map((c, n) => {
          const meus = pedidos.filter((p) => p.cena === c.id)
          const ach = achados(c.id)
          const falt = faltas(c.id)
          return (
            <li key={c.id} data-cena={c.id} className="rounded-lg border border-borda bg-painel-2 p-3">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-mono text-[11px] text-apagado">{String(n + 1).padStart(2, '0')} · {c.id} · {seg(c.t0)}–{seg(c.t1)} · {c.capitulo}</span>
                <span className="rounded bg-ouro/15 px-1.5 py-0.5 font-mono text-[10px] text-ouro">{c.motor}</span>
                <span className="font-mono text-[10px] text-apagado">{c.transicao.tipo}{c.transicao.quadros ? ` ${c.transicao.quadros} q` : ''}</span>
                <button
                  onClick={() => { setAberta(aberta === c.id ? null : c.id); setTexto('') }}
                  className="ml-auto text-[11px] text-ouro hover:underline"
                >
                  pedir mudança
                </button>
              </div>
              <p className="mt-1 text-sm">{c.objetivo}</p>
              <p className="text-xs text-suave">em “{c.em}”{c.camera ? ` · câmera: ${c.camera}` : ''}</p>
              <p className="mt-1 font-mono text-[11px] text-apagado">
                kits: {c.kits.map((k) => k.kit).join(', ') || '—'}
                {c.texto?.length ? ` · tela: ${c.texto.join(' | ')}` : ''}
                {c.sfx.length ? ` · sfx: ${c.sfx.map((x) => `${x.categoria}@“${x.em}”`).join(', ')}` : ''}
              </p>
              {falt.map((i) => (
                <p key={i.id} className={`mt-1 text-[11px] ${COR_ATIVO[i.status]}`}>ativo {i.status}: {i.descricao}</p>
              ))}
              {ach.map((x, k) => (
                <p key={k} className={`mt-1 text-[11px] ${x.nivel === 'aviso' ? 'text-suave' : 'text-atencao'}`}>
                  {x.nivel} [{x.codigo}] {x.msg}
                </p>
              ))}
              {meus.map((p) => (
                <LinhaPedido key={p.id} p={p} ocupado={ocupado} retirar={retirar} />
              ))}
              {aberta === c.id && (
                <div className="mt-2 flex gap-2">
                  <input
                    autoFocus
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && texto.trim() && (pedir(texto, c.id), setAberta(null))}
                    placeholder="o que mudar nesta cena"
                    className="min-w-0 flex-1 rounded-md border border-borda bg-painel px-2 py-1.5 text-xs outline-none focus:border-suave"
                  />
                  <button
                    disabled={ocupado || !texto.trim()}
                    onClick={() => { pedir(texto, c.id); setAberta(null) }}
                    className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:opacity-40"
                  >
                    Pedir
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function VerAtivos({ a }: { a: Doc['ativos'] }) {
  const [prontos, setProntos] = useState(false)
  if (!a) return <p className="text-sm text-suave">Ativos ainda não resolvidos. Aprove a SPEC e clique em “Resolver ativos” (offline: só olha o que já existe).</p>
  const faltam = a.itens.filter((i) => i.status !== 'pronto')
  const ok = a.itens.filter((i) => i.status === 'pronto')
  return (
    <div>
      <p className="font-mono text-[11px] text-suave">
        {Object.entries(a.resumo).filter(([, n]) => n).map(([k, n]) => `${n} ${k}`).join(' · ')}
      </p>
      {faltam.length > 0 && (
        <p className="mt-1 text-[11px] text-apagado">Faltantes e não validados: o comando de cada um vai para o orquestrador (rede: OpenF1/YouTube). Não validado só entra com o seu OK na cena.</p>
      )}
      <ul className="mt-2 flex flex-col gap-1.5">
        {faltam.map((i) => (
          <li key={i.id} className="rounded-md border border-atencao/30 bg-atencao/5 px-3 py-2 text-xs">
            <span className={`font-mono ${COR_ATIVO[i.status]}`}>{i.status}</span> <span className="font-mono text-apagado">{i.tipo} · cena {i.cena}</span>
            <p className="text-texto/85">{i.descricao}</p>
            {i.comando && <code className="block break-all font-mono text-[11px] text-apagado">{i.comando}</code>}
          </li>
        ))}
      </ul>
      {ok.length > 0 && (
        <button onClick={() => setProntos(!prontos)} className="mt-2 text-[11px] text-suave hover:text-texto">
          {prontos ? 'esconder' : 'mostrar'} {ok.length} pronto(s)
        </button>
      )}
      {prontos && (
        <ul className="mt-1 flex flex-col gap-0.5">
          {ok.map((i) => (
            <li key={i.id} className="text-[11px] text-suave"><span className="text-ok">pronto</span> {i.tipo} · {i.descricao}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function VerVerificacao({ v }: { v: Verificacao | null }) {
  if (!v) return <p className="text-sm text-suave">Ainda não verificado. Clique em “Verificar” (checagens automáticas da SPEC, sem modelo).</p>
  const grupo = (nome: string, lista: Achado[], cor: string) =>
    lista.length > 0 && (
      <div className="mt-2">
        <h3 className={`text-xs font-semibold ${cor}`}>{nome} ({lista.length})</h3>
        <ul className="mt-1 flex flex-col gap-0.5">
          {lista.map((x, k) => (
            <li key={k} className="text-xs">
              <span className="font-mono text-apagado">[{x.codigo}]{x.cena ? ` ${x.cena}` : ''}</span> <span className="text-texto/85">{x.msg}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  return (
    <div>
      <p className={`text-sm font-medium ${v.status === 'aprovado' ? 'text-ok' : 'text-atencao'}`}>
        {v.status} · {v.contagem.erros} erro(s), {v.contagem.pendencias} pendência(s), {v.contagem.avisos} aviso(s)
      </p>
      {grupo('Erros', v.erros, 'text-atencao')}
      {grupo('Pendências', v.pendencias, 'text-atencao')}
      {grupo('Avisos', v.avisos, 'text-suave')}
    </div>
  )
}

function PedidosDaEtapa({ pedidos, ocupado, pedir, retirar }: { pedidos: PedidoDoc[]; ocupado: boolean; pedir: (t: string) => void; retirar: (id: string) => void }) {
  const [texto, setTexto] = useState('')
  const gerais = pedidos.filter((p) => !p.cena)
  return (
    <div className="mt-4 rounded-lg border border-borda p-3">
      <h3 className="text-xs font-semibold">Pedidos gerais desta etapa</h3>
      {gerais.map((p) => (
        <LinhaPedido key={p.id} p={p} ocupado={ocupado} retirar={retirar} />
      ))}
      <div className="mt-2 flex gap-2">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="pedido para a etapa inteira (o de uma cena fica na própria cena)"
          className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
        />
        <button
          disabled={ocupado || !texto.trim()}
          onClick={() => { pedir(texto); setTexto('') }}
          className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:opacity-40"
        >
          Pedir
        </button>
      </div>
    </div>
  )
}

function LinhaPedido({ p, ocupado, retirar }: { p: PedidoDoc; ocupado: boolean; retirar: (id: string) => void }) {
  return (
    <p className="mt-1 flex items-start gap-2 text-[11px]">
      <span className={`font-mono ${p.status === 'aberto' ? 'text-atencao' : 'text-apagado'}`}>{p.id} · {p.status}</span>
      <span className={p.status === 'aberto' ? 'text-texto/85' : 'text-apagado line-through'}>{p.texto}</span>
      {p.status === 'aberto' && (
        <button disabled={ocupado} onClick={() => retirar(p.id)} className="ml-auto shrink-0 text-apagado hover:text-atencao">retirar</button>
      )}
    </p>
  )
}

function Avisos({ lista }: { lista?: string[] }) {
  if (!lista?.length) return null
  return (
    <ul className="mb-2 flex flex-col gap-0.5">
      {lista.map((a) => (
        <li key={a} className="text-[11px] text-atencao">aviso: {a}</li>
      ))}
    </ul>
  )
}
