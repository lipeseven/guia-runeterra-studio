import { useState } from 'react'
import { Play } from 'lucide-react'
import { api, useAoVivo, type Etapa } from '../api'

type Plano = { id: string; n: number; tipo: string; clima: string | null; inicio: number; trecho: string; extras: string[] }
type Pedido = { plano: string | null; texto: string; quando: string }
type Aviso = { texto: string; resposta: boolean; plano: string | null }
type Dados = { planos: Plano[]; pedidos: Pedido[]; avisos: Aviso[] }

/** Toca a Prévia a partir do segundo do plano (o player fica ao lado, na página do vídeo). */
const tocar = (s: number) => {
  const v = document.getElementById('previa-video') as HTMLVideoElement | null
  if (!v) return
  v.currentTime = s
  void v.play()
  v.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

type Musica = { ligada: boolean; descricao: string; volume?: number; pasta: string; em_uso: string | null; propria: boolean }

/** Música de fundo do vídeo: gerada no PC pela descrição (ou a do Felipe, posta na pasta musica/ do projeto).
 *  Aplicar refaz só o áudio do último vídeo: sem Claude e sem renderizar a imagem. */
function MusicaDeFundo({ videoId, trabalhando, aoMudar }: { videoId: number; trabalhando: boolean; aoMudar: () => void }) {
  const { dados, recarregar } = useAoVivo<Musica>(`/videos/${videoId}/musica`, 8000)
  const [ligada, setLigada] = useState<boolean | null>(null)
  const [descricao, setDescricao] = useState<string | null>(null)
  const [volume, setVolume] = useState<number | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const lig = ligada ?? dados?.ligada ?? false
  const desc = descricao ?? dados?.descricao ?? ''
  const vol = volume ?? dados?.volume ?? -14
  const aplicar = async () => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/musica`, { method: 'POST', body: JSON.stringify({ ligada: lig, descricao: desc, volume: vol }) })
    } catch (e) {
      return setErro(String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e))
    }
    setLigada(null)
    setDescricao(null)
    setVolume(null)
    recarregar()
    aoMudar()
  }
  return (
    <div className="mt-4 rounded-lg border border-borda p-3">
      <div className="flex items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={lig} onChange={(e) => setLigada(e.target.checked)} />
          Música de fundo
        </label>
        <span className="truncate font-mono text-[11px] text-apagado">
          {dados?.em_uso ? (dados.propria ? `sua música: ${dados.em_uso}` : 'gerada no PC') : 'sem música'}
        </span>
      </div>
      {lig && (
        <input
          value={desc}
          onChange={(e) => setDescricao(e.target.value)}
          placeholder="como ela é, em inglês (vazio = calm modern electronic, soft pads, light beat)"
          className="mt-2 w-full rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
        />
      )}
      {lig && (
        <label className="mt-2 flex items-center gap-3 text-xs text-suave">
          volume
          <input type="range" min={-30} max={0} step={1} value={vol} onChange={(e) => setVolume(Number(e.target.value))} className="flex-1" />
          <span className="w-24 font-mono text-[11px] text-apagado">{vol} dB{vol === -14 ? " (padrão)" : ""}</span>
        </label>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          disabled={trabalhando}
          onClick={aplicar}
          className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:opacity-40"
        >
          {lig ? 'Aplicar música' : 'Tirar a música'}
        </button>
        <span className="text-[11px] text-apagado">
          baixa e abaixando sozinha quando há fala · só refaz o áudio (sem Claude) · sua própria música: ponha o arquivo em {dados?.pasta ?? 'musica/'}
        </span>
      </div>
      {erro && <p className="mt-2 text-xs text-atencao">{erro}</p>}
    </div>
  )
}

/** Vídeo vertical: a direção da animação, plano a plano. Pedidos ficam na fila até "Refazer com os pedidos". */
type Candidata = { titulo: string; pagina: string; miniatura: string; ano: number | null; licenca: string; autor: string }
type Pessoa = { candidatas: Candidata[]; escolhida: number | null; aprovada: boolean }

/** Fotos de pessoas reais (Wikimedia Commons, só licença livre): só a foto aprovada aqui entra no vídeo. */
function FotosPessoas({ videoId }: { videoId: number }) {
  const { dados, recarregar } = useAoVivo<Record<string, Pessoa>>(`/videos/${videoId}/fotos`, 15000)
  const pessoas = Object.entries(dados ?? {}).filter(([, p]) => p.candidatas.length)
  if (!pessoas.length) return null
  const escolher = async (nome: string, escolhida: number | null) => {
    await api(`/videos/${videoId}/fotos`, { method: 'POST', body: JSON.stringify({ nome, escolhida, aprovada: true }) })
    recarregar()
  }
  return (
    <div className="mt-4 rounded-lg border border-borda p-3">
      <h3 className="text-xs font-semibold">Fotos das pessoas</h3>
      <p className="mt-0.5 text-[11px] text-apagado">Fotos livres do Wikimedia Commons (crédito vai na descrição). Clique na foto que vale; depois “Só renderizar de novo”.</p>
      {pessoas.map(([nome, p]) => (
        <div key={nome} className="mt-3">
          <p className="text-xs">
            {nome}{' '}
            <span className={p.aprovada ? 'text-ok' : 'text-atencao'}>
              {p.aprovada ? (p.escolhida === null ? '· sem foto (silhueta)' : '· aprovada') : '· aguardando você'}
            </span>
          </p>
          <div className="mt-1 flex flex-wrap gap-2">
            {p.candidatas.map((c, i) => (
              <button key={c.pagina} onClick={() => escolher(nome, i)} title={`${c.autor} · ${c.licenca}${c.ano ? ` · ${c.ano}` : ''}`}
                className={`h-28 w-24 overflow-hidden rounded border-2 ${p.escolhida === i ? (p.aprovada ? 'border-ok' : 'border-ouro') : 'border-transparent opacity-80 hover:opacity-100'}`}>
                <img src={c.miniatura} alt={c.titulo} className="h-full w-full object-cover" loading="lazy" />
              </button>
            ))}
            <button onClick={() => escolher(nome, null)}
              className={`h-28 w-24 rounded border-2 text-[11px] text-suave ${p.aprovada && p.escolhida === null ? 'border-ok' : 'border-borda'}`}>
              sem foto
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

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
  const fechar = () => {
    setAberto(null)
    setTexto('')
  }
  const [respondendo, setRespondendo] = useState<number | null>(null)
  const [resposta, setResposta] = useState('')
  const responderAviso = async (k: number) => {
    if (!resposta.trim()) return
    setErro(null)
    try {
      await api(`/videos/${videoId}/animacao/aviso/${k}/responder`, { method: 'POST', body: JSON.stringify({ texto: resposta }) })
    } catch (e) {
      return setErro(limpar(e))
    }
    setResposta('')
    setRespondendo(null)
    recarregar()
  }
  const aceitarAviso = async (k: number) => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/animacao/aviso/${k}`, { method: 'DELETE' })
    } catch (e) {
      return setErro(limpar(e))
    }
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
          {dados.avisos.map((a, k) => (
            <li key={a.texto} className="mb-1.5">
              <span>{a.texto}</span>
              {!trabalhando && (
                <span className="ml-2 inline-flex gap-2 whitespace-nowrap">
                  {a.resposta && (
                    <button onClick={() => { setRespondendo(respondendo === k ? null : k); setResposta('') }} className="text-ouro hover:underline">
                      Responder
                    </button>
                  )}
                  <button onClick={() => aceitarAviso(k)} title="Tira o aviso da lista" className="text-apagado hover:text-texto hover:underline">
                    Está bom assim
                  </button>
                </span>
              )}
              {respondendo === k && (
                <div className="mt-1.5 flex gap-2">
                  <textarea
                    value={resposta}
                    onChange={(e) => setResposta(e.target.value)}
                    rows={2}
                    autoFocus
                    placeholder={a.plano ? 'Sua resposta vira pedido desta cena' : 'Sua resposta vira pedido geral'}
                    className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs text-texto outline-none focus:border-suave"
                  />
                  <button onClick={() => responderAviso(k)} disabled={!resposta.trim()} className="self-end rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10 disabled:opacity-40">
                    Enviar
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      {planos.length > 0 && (
        <ol className="flex max-h-[520px] flex-col overflow-y-auto rounded-lg border border-borda">
          {planos.map((p) => {
            const meus = doPlano(p.id)
            return (
              <li key={p.id} className="border-b border-borda/60 px-3 py-2 last:border-0">
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => tocar(p.inicio)}
                    title="Assistir a partir deste trecho"
                    className="flex w-14 shrink-0 items-center gap-1 pt-0.5 font-mono text-[11px] text-apagado hover:text-ouro"
                  >
                    <Play className="size-3" />
                    {mmss(p.inicio)}
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-texto/90">{p.trecho}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-suave">
                      {p.n}. {p.tipo.replace('_', ' ')}{p.clima ? ` · ${p.clima}` : ''}{p.extras.length ? ` · ${p.extras.join(', ')}` : ''}
                    </p>
                    {meus.map((m) => (
                      <p key={m.n} className="mt-1 flex items-center gap-2 text-xs text-ouro">
                        pedido: {m.texto}
                        <button onClick={() => tirar(m.n)} className="text-apagado hover:text-atencao">descartar</button>
                      </p>
                    ))}
                    {aberto === p.id && (
                      <div className="mt-2 flex gap-2">
                        <input
                          autoFocus
                          value={texto}
                          onChange={(e) => setTexto(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') pedir(p.id, texto)
                            if (e.key === 'Escape') fechar()
                          }}
                          placeholder="ex.: câmera mais perto; troque pelos pneus; placa com 300 km"
                          className="min-w-0 flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1.5 text-xs outline-none focus:border-suave"
                        />
                        <button onClick={() => pedir(p.id, texto)} className="rounded-md border border-ouro/60 px-3 py-1.5 text-xs text-ouro hover:bg-ouro/10">
                          Anotar
                        </button>
                        <button onClick={fechar} title="Fecha sem anotar (Esc)" className="rounded-md border border-borda px-3 py-1.5 text-xs text-suave hover:border-borda-forte hover:text-texto">
                          Cancelar
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
              <button onClick={() => tirar(pedidos.indexOf(p))} className="text-apagado hover:text-atencao">descartar</button>
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
      {planos.length > 0 && <MusicaDeFundo videoId={videoId} trabalhando={trabalhando} aoMudar={aoMudar} />}
      {planos.length > 0 && <FotosPessoas videoId={videoId} />}
      {erro && <p className="mt-2 text-xs text-atencao">{erro}</p>}
    </section>
  )
}
