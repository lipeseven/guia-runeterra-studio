import { useState } from 'react'
import { api, useAoVivo, type Etapa } from '../api'

type Plano = { id: string; n: number; tipo: string; clima: string | null; inicio: number; trecho: string; extras: string[] }
type Pedido = { plano: string | null; texto: string; quando: string }
type Dados = { planos: Plano[]; pedidos: Pedido[]; avisos: string[] }

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

/** Vídeo vertical: a direção da animação, plano a plano. Pedidos ficam na fila até "Refazer com os pedidos". */
export function PainelAnimacao({ videoId, direcao, render, aoMudar }: { videoId: number; direcao: Etapa; render: Etapa; aoMudar: () => void }) {
  const { dados, recarregar } = useAoVivo<Dados>(`/videos/${videoId}/animacao`, 5000)
  const [aberto, setAberto] = useState<string | null>(null)
  const [texto, setTexto] = useState('')
  const [geral, setGeral] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const trabalhando = direcao.status === 'andamento' || render.status === 'andamento'
  const limpar = (e: unknown) => String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)

  const pedir = async (plano: string | null, t: string) => {
    if (!t.trim()) return
    setErro(null)
    try {
      await api(`/videos/${videoId}/animacao/pedido`, { method: 'POST', body: JSON.stringify({ plano, texto: t }) })
    } catch (e) {
      return setErro(limpar(e))
    }
    setTexto('')
    setGeral('')
    setAberto(null)
    recarregar()
  }
  const tirar = async (n: number) => {
    await api(`/videos/${videoId}/animacao/pedido/${n}`, { method: 'DELETE' })
    recarregar()
  }
  const refazer = async (do_zero: boolean, so_render = false) => {
    if (do_zero && !confirm('O diretor vai escolher todas as cenas de novo (os pedidos na fila são descartados). Continuar?')) return
    setErro(null)
    try {
      await api(`/videos/${videoId}/animacao/refazer`, { method: 'POST', body: JSON.stringify({ do_zero, so_render }) })
    } catch (e) {
      return setErro(limpar(e))
    }
    recarregar()
    aoMudar()
  }

  const planos = dados?.planos ?? []
  const pedidos = dados?.pedidos ?? []
  const doPlano = (id: string) => pedidos.map((p, n) => ({ ...p, n })).filter((p) => p.plano === id)

  return (
    <section id="animacao" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">Animação</h2>
        <span className="truncate font-mono text-[11px] text-apagado">
          {planos.length ? `${planos.length} planos` : direcao.resumo ?? 'o diretor começa quando a voz estiver pronta'}
        </span>
      </header>

      {dados?.avisos?.length ? (
        <ul className="mb-3 list-disc pl-5 text-xs text-atencao">
          {dados.avisos.map((a) => <li key={a}>{a}</li>)}
        </ul>
      ) : null}

      {planos.length > 0 && (
        <ol className="flex max-h-[520px] flex-col overflow-y-auto rounded-lg border border-borda">
          {planos.map((p) => {
            const meus = doPlano(p.id)
            return (
              <li key={p.id} className="border-b border-borda/60 px-3 py-2 last:border-0">
                <div className="flex items-start gap-3">
                  <span className="w-10 shrink-0 pt-0.5 font-mono text-[11px] text-apagado">{mmss(p.inicio)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-texto/90">{p.trecho}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-suave">
                      {p.n}. {p.tipo.replace('_', ' ')}{p.clima ? ` · ${p.clima}` : ''}{p.extras.length ? ` · ${p.extras.join(', ')}` : ''}
                    </p>
                    {meus.map((m) => (
                      <p key={m.n} className="mt-1 flex items-center gap-2 text-xs text-ouro">
                        pedido: {m.texto}
                        <button onClick={() => tirar(m.n)} className="text-apagado hover:text-atencao">tirar</button>
                      </p>
                    ))}
                    {aberto === p.id && (
                      <div className="mt-2 flex gap-2">
                        <input
                          autoFocus
                          value={texto}
                          onChange={(e) => setTexto(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && pedir(p.id, texto)}
                          placeholder="ex.: câmera mais perto; troque pelos pneus; placa com 300 km"
                          className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
                        />
                        <button onClick={() => pedir(p.id, texto)} className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10">
                          Anotar
                        </button>
                      </div>
                    )}
                  </div>
                  {aberto !== p.id && (
                    <button
                      onClick={() => {
                        setAberto(p.id)
                        setTexto('')
                      }}
                      className="shrink-0 rounded-md border border-borda px-2 py-1 text-[11px] text-suave hover:border-borda-forte hover:text-texto"
                    >
                      pedir mudança
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      )}

      {planos.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          <div className="flex gap-2">
            <input
              value={geral}
              onChange={(e) => setGeral(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && pedir(null, geral)}
              placeholder="pedido geral (vale para o vídeo todo)"
              className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
            />
            <button onClick={() => pedir(null, geral)} className="rounded-md border border-borda px-3 py-1.5 text-xs hover:border-borda-forte">
              Anotar
            </button>
          </div>
          {pedidos.filter((p) => !p.plano).map((p) => (
            <p key={p.quando + p.texto} className="flex items-center gap-2 text-xs text-ouro">
              pedido geral: {p.texto}
              <button onClick={() => tirar(pedidos.indexOf(p))} className="text-apagado hover:text-atencao">tirar</button>
            </p>
          ))}
          <div className="flex flex-wrap items-center gap-2">
            <button
              disabled={trabalhando || pedidos.length === 0}
              onClick={() => refazer(false)}
              className="rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110 disabled:opacity-40"
            >
              Refazer com os pedidos ({pedidos.length})
            </button>
            <button
              disabled={trabalhando}
              onClick={() => refazer(true)}
              className="rounded-md border border-borda px-3 py-1.5 text-xs text-suave hover:border-borda-forte hover:text-texto disabled:opacity-40"
            >
              Refazer do zero
            </button>
            <button
              disabled={trabalhando || pedidos.length > 0}
              onClick={() => refazer(false, true)}
              title="Sem Claude: renderiza de novo a mesma direção (ex.: depois de melhorar um modelo 3D)"
              className="rounded-md border border-borda px-3 py-1.5 text-xs text-suave hover:border-borda-forte hover:text-texto disabled:opacity-40"
            >
              Só renderizar de novo
            </button>
            {trabalhando && <span className="text-xs text-andamento">o motor está trabalhando nesta animação…</span>}
          </div>
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-atencao">{erro}</p>}
    </section>
  )
}
