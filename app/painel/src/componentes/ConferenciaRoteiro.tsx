import { AlertTriangle, BookOpen, CheckCircle2, CopyCheck, HelpCircle, Loader2, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'

type Fato = {
  paragrafo: number
  trecho?: string
  afirmacao: string
  veredito: 'confere' | 'diverge' | 'sem_fonte'
  explicacao: string
  fonte: { fonte: string; texto: string } | null
}
type Semelhanca = { geral: number; total: number; frases: { frase: string; base: string; nota: number; nivel: string }[] }
type Dossie = {
  quando: string
  assuntos: string[]
  fatos: { assunto: string; fato: string; canon: string; fonte: string | null }[]
  crivo: { afirmacao: string; veredito: 'confirmada' | 'corrigida' | 'desatualizada' | 'sem_fonte'; correcao: string; fonte: { fonte: string; texto: string } | null }[]
}
type Dados = {
  dossie: Dossie | null
  conferencia: { quando: string; semelhanca?: Semelhanca; fatos?: Fato[]; erro_fatos?: string } | null
  atual: boolean
  base: string | null
}

const ICONE = {
  diverge: <AlertTriangle className="size-3.5 shrink-0 text-atencao" />,
  sem_fonte: <HelpCircle className="size-3.5 shrink-0 text-suave" />,
  confere: <CheckCircle2 className="size-3.5 shrink-0 text-ok" />,
}
const CRIVO = {
  corrigida: ['text-atencao', 'corrigidas (o roteiro base estava errado)'],
  desatualizada: ['text-atencao', 'desatualizadas / não canon'],
  sem_fonte: ['text-suave', 'sem fonte (ficaram de fora)'],
  confirmada: ['text-ok', 'confirmadas'],
} as const
const NOMES = { diverge: 'a fonte diz diferente', sem_fonte: 'sem fonte encontrada (confira se quiser)', confere: 'conferem com a fonte' }

/** Conferência do roteiro antes de aprovar: fatos de lore × wiki/Universe e semelhança com o roteiro base. */
export function ConferenciaRoteiro({ videoId, versao }: { videoId: number; versao: number }) {
  const [d, setD] = useState<Dados | null>(null)
  const [aberto, setAberto] = useState<Record<string, boolean>>({ diverge: true })
  const [editBase, setEditBase] = useState(false)
  const [base, setBase] = useState('')
  const [fonteAberta, setFonteAberta] = useState<number | null>(null)
  const carregar = () => api<Dados>(`/videos/${videoId}/roteiro/conferencia`).then(setD)
  useEffect(() => {
    carregar()
  }, [videoId, versao]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!d || d.atual) return
    const t = setInterval(carregar, 4000) // conferindo: atualiza sozinho
    return () => clearInterval(t)
  }, [d?.atual]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return null
  const c = d.conferencia
  const fatos = c?.fatos ?? []
  const grupos = (['diverge', 'sem_fonte', 'confere'] as const).map((v) => [v, fatos.filter((f) => f.veredito === v)] as const)

  return (
    <div className="mt-3 rounded-lg border border-borda bg-painel-2 p-3 text-xs">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <CopyCheck className="size-4 text-suave" />
        <span className="text-sm font-medium">Conferência do roteiro</span>
        {!d.atual && (
          <span className="flex items-center gap-1 text-andamento">
            <Loader2 className="size-3.5 animate-spin" /> conferindo esta versão…
          </span>
        )}
        <span className="ml-auto flex items-center gap-2">
          <button
            onClick={() => {
              setBase(d.base ?? '')
              setEditBase(!editBase)
            }}
            className="text-suave underline hover:text-texto"
          >
            {d.base ? 'roteiro base ✓' : '+ roteiro base (detector de semelhança)'}
          </button>
          <button
            onClick={async () => {
              await api(`/videos/${videoId}/roteiro/conferir`, { method: 'POST' })
              setD({ ...d, atual: false })
            }}
            className="flex items-center gap-1 text-suave hover:text-texto"
            title="Conferir de novo (só os parágrafos que mudaram usam o Claude)"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </span>
      </div>

      {editBase && (
        <div className="mb-3 flex flex-col gap-1.5">
          <textarea
            value={base}
            onChange={(e) => setBase(e.target.value)}
            placeholder="Cole o roteiro/transcrição do vídeo modelado (canal gringo). Fica só para comparar — nada é copiado."
            className="h-32 w-full resize-y rounded-md border border-borda bg-painel p-2 font-mono text-[11px] outline-none focus:border-suave"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setEditBase(false)} className="px-2 py-1 text-suave">
              cancelar
            </button>
            <button
              onClick={async () => {
                await api(`/videos/${videoId}/roteiro/base`, { method: 'POST', body: JSON.stringify({ texto: base }) })
                setEditBase(false)
                setD({ ...d, atual: false, base: base.trim() ? base : null })
              }}
              className="rounded bg-ouro/20 px-2.5 py-1 text-ouro hover:bg-ouro/30"
            >
              {base.trim() ? 'guardar e comparar' : 'remover base'}
            </button>
          </div>
        </div>
      )}

      {d.dossie && <Pesquisa dossie={d.dossie} />}

      {c?.semelhanca && (
        <div className="mb-3">
          <p className={c.semelhanca.frases.length ? 'text-atencao' : 'text-ok'}>
            {c.semelhanca.frases.length
              ? `${c.semelhanca.frases.length} de ${c.semelhanca.total} frases (${c.semelhanca.geral}%) parecidas com o roteiro base — reescreva com as suas palavras:`
              : 'Nenhuma frase parecida demais com o roteiro base. ✓'}
          </p>
          {c.semelhanca.frases.map((f, k) => (
            <div key={k} className="mt-1.5 rounded border border-atencao/30 p-1.5">
              <p className="text-texto/90">
                <span className={`mr-1 rounded px-1 ${f.nivel === 'quase igual' ? 'bg-red-500/20 text-red-300' : 'bg-atencao/15 text-atencao'}`}>
                  {f.nivel}
                </span>
                {f.frase}
              </p>
              <p className="mt-0.5 text-apagado">base: {f.base}</p>
            </div>
          ))}
        </div>
      )}

      {c?.erro_fatos && <p className="text-atencao">Checagem de fatos falhou: {c.erro_fatos}</p>}
      {c && !c.erro_fatos && fatos.length === 0 && d.atual && <p className="text-apagado">Nenhuma afirmação de lore para checar.</p>}
      {grupos.map(([v, lista]) =>
        lista.length === 0 ? null : (
          <div key={v} className="mb-1.5">
            <button onClick={() => setAberto({ ...aberto, [v]: !aberto[v] })} className="flex items-center gap-1.5 hover:text-texto">
              {ICONE[v]} <b>{lista.length}</b> {NOMES[v]} {aberto[v] ? '▴' : '▾'}
            </button>
            {aberto[v] && (
              <ul className="mt-1 flex flex-col gap-1.5 pl-5">
                {lista.map((f) => {
                  const id = fatos.indexOf(f)
                  return (
                    <li key={id}>
                      <p className="text-texto/90">
                        <span className="font-mono text-apagado">¶{f.paragrafo + 1}</span> {f.afirmacao}
                      </p>
                      {f.explicacao && <p className="text-suave">{f.explicacao}</p>}
                      {f.fonte && (
                        <button onClick={() => setFonteAberta(fonteAberta === id ? null : id)} className="text-apagado underline hover:text-texto">
                          {f.fonte.fonte}
                        </button>
                      )}
                      {fonteAberta === id && f.fonte && <p className="mt-1 rounded bg-painel p-1.5 text-apagado">“{f.fonte.texto}”</p>}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        ),
      )}
    </div>
  )
}

/** Pesquisa feita ANTES de escrever: fatos com fonte que o roteirista usou + crivo do roteiro base. */
function Pesquisa({ dossie }: { dossie: Dossie }) {
  const [aberto, setAberto] = useState<string | null>(null)
  const grupos = (['corrigida', 'desatualizada', 'sem_fonte', 'confirmada'] as const).map((v) => [v, dossie.crivo.filter((x) => x.veredito === v)] as const)
  return (
    <div className="mb-3 rounded border border-borda p-2">
      <p className="flex flex-wrap items-center gap-1.5">
        <BookOpen className="size-3.5 text-suave" />
        <b>Pesquisa:</b> {dossie.fatos.length} fatos verificados sobre {dossie.assuntos.join(', ')}
        <button onClick={() => setAberto(aberto === 'fatos' ? null : 'fatos')} className="text-apagado underline hover:text-texto">
          {aberto === 'fatos' ? 'esconder' : 'ver'}
        </button>
      </p>
      {aberto === 'fatos' && (
        <ul className="mt-1 flex max-h-72 flex-col gap-1 overflow-y-auto pl-5">
          {dossie.fatos.map((f, k) => (
            <li key={k} className="text-texto/90">
              <span className="text-apagado">{f.assunto}:</span> {f.fato}
              {f.canon !== 'atual' && <span className="ml-1 rounded bg-atencao/15 px-1 text-atencao">{f.canon === 'antigo' ? 'lore antigo' : 'só no jogo'}</span>}
              {f.fonte && <span className="ml-1 text-apagado">({f.fonte})</span>}
            </li>
          ))}
        </ul>
      )}
      {dossie.crivo.length > 0 && <p className="mt-1.5 text-suave">Crivo do roteiro base ({dossie.crivo.length} afirmações):</p>}
      {grupos.map(([v, lista]) =>
        lista.length === 0 ? null : (
          <div key={v} className="pl-5">
            <button onClick={() => setAberto(aberto === v ? null : v)} className={`hover:text-texto ${CRIVO[v][0]}`}>
              <b>{lista.length}</b> {CRIVO[v][1]} {aberto === v ? '▴' : '▾'}
            </button>
            {aberto === v && (
              <ul className="mt-1 flex flex-col gap-1.5 pl-3">
                {lista.map((x, k) => (
                  <li key={k}>
                    <p className="text-texto/90">{x.afirmacao}</p>
                    {x.correcao && <p className="text-suave">→ {x.correcao}</p>}
                    {x.fonte && <p className="text-apagado">{x.fonte.fonte}</p>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ),
      )}
    </div>
  )
}
