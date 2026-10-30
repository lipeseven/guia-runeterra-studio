import { CheckCircle2, ClipboardPaste, FileText, History, Loader2, Pencil, Send, Sparkles, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { DaPasta } from './DaPasta'
import { api, quando, type Etapa } from '../api'
import { ConferenciaRoteiro } from './ConferenciaRoteiro'

type DadosRoteiro = { texto: string | null; paragrafos?: number; palavras?: number; segundos?: number }
type Conversa = { quando: string; acao: 'gerar' | 'ajustar'; pedido: string; resumo: string; versao: number; palavras: number }
type Versao = { versao: number; palavras: number; inicio: string }

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`

/** Lê um .txt em UTF-8; se não for UTF-8 válido (Bloco de Notas antigo), cai para Windows-1252. */
async function lerTxt(arquivo: File) {
  const bytes = await arquivo.arrayBuffer()
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder('windows-1252').decode(bytes)
  }
}

const botao = 'rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:bg-painel-2'
const campo = 'w-full rounded-md border border-borda bg-painel-2 px-2.5 py-2 text-sm outline-none focus:border-suave'

export function PainelRoteiro({ videoId, etapa, aoMudar, conferindo = false }: { videoId: number; etapa: Etapa; aoMudar: () => void; conferindo?: boolean }) {
  const [dados, setDados] = useState<DadosRoteiro | null>(null)
  const [hist, setHist] = useState<{ conversa: Conversa[]; versoes: Versao[] }>({ conversa: [], versoes: [] })
  const [modo, setModo] = useState<'nada' | 'colar' | 'gerar' | 'editar'>('nada')
  const [arrastando, setArrastando] = useState(false)
  const [texto, setTexto] = useState('')
  const [pedido, setPedido] = useState('')
  const [ger, setGer] = useState({ minutos: 20, notas: '', base: '', usarBase: false })
  const [verHist, setVerHist] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const seletor = useRef<HTMLInputElement>(null)
  const versao = (etapa.dados.versao as number | undefined) ?? 0
  const trabalhando = etapa.status === 'andamento'

  const carregar = () => {
    api<DadosRoteiro>(`/videos/${videoId}/roteiro`).then(setDados)
    api<{ conversa: Conversa[]; versoes: Versao[] }>(`/videos/${videoId}/roteiro/historico`).then(setHist)
  }
  useEffect(() => {
    carregar()
  }, [videoId, versao, etapa.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const chamar = async (caminho: string, corpo: object) => {
    setErro(null)
    try {
      await api(`/videos/${videoId}/roteiro${caminho}`, { method: 'POST', body: JSON.stringify(corpo) })
      setModo('nada')
      setTexto('')
      carregar()
      aoMudar()
      return true
    } catch (e) {
      setErro(String(e))
      return false
    }
  }
  const receberArquivo = async (f: File | undefined) => {
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.txt')) return setErro('Envie um arquivo .txt')
    chamar('', { texto: await lerTxt(f), nome: f.name })
  }
  const receberBase = async (f: File | undefined) => {
    if (!f) return
    setGer({ ...ger, base: await lerTxt(f), usarBase: true })
  }

  const aprovado = etapa.status === 'concluido'
  const temRoteiro = Boolean(dados?.texto)

  const formGerar = (
    <div className="flex flex-col gap-3 rounded-lg border border-ouro/30 bg-ouro/5 p-3">
      <p className="flex items-center gap-1.5 text-sm font-medium">
        <Sparkles className="size-4 text-ouro" /> Gerar o roteiro com o Claude
      </p>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          Duração narrada
          <input
            type="number"
            min={3}
            max={40}
            value={ger.minutos}
            onChange={(e) => setGer({ ...ger, minutos: Number(e.target.value) })}
            className="w-16 rounded-md border border-borda bg-painel-2 px-2 py-1 text-sm"
          />
          min <span className="text-xs text-apagado">(~{Math.round(ger.minutos * 162)} palavras)</span>
        </label>
      </div>
      <textarea
        value={ger.notas}
        onChange={(e) => setGer({ ...ger, notas: e.target.value })}
        placeholder="Orientações (opcional): foco, ordem das seções, personagens que não podem faltar, tom, piadas…"
        className={`${campo} h-24 resize-y`}
      />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={ger.usarBase} onChange={(e) => setGer({ ...ger, usarBase: e.target.checked })} />
        Usar um roteiro base (ex.: canal gringo) — só como fonte de fatos, nunca tradução
      </label>
      {ger.usarBase && (
        <div className="flex flex-col gap-1.5">
          <textarea
            value={ger.base}
            onChange={(e) => setGer({ ...ger, base: e.target.value })}
            placeholder="Cole aqui o roteiro/transcrição base…"
            className={`${campo} h-40 resize-y font-mono text-xs`}
          />
          <label className="cursor-pointer self-start text-xs text-suave hover:text-texto">
            <input type="file" accept=".txt,text/plain" className="hidden" onChange={(e) => receberBase(e.target.files?.[0])} />
            ou escolher um .txt
          </label>
          <DaPasta rotulo="ou escolher da pasta de roteiros" aoEscolher={(texto) => setGer({ ...ger, base: texto, usarBase: true })} />
        </div>
      )}
      <div className="flex justify-end gap-2">
        <button onClick={() => setModo('nada')} className={botao}>
          Cancelar
        </button>
        <button
          disabled={ger.usarBase && ger.base.trim().length < 100}
          onClick={() =>
            chamar('/gerar', { minutos: ger.minutos, notas: ger.notas, base: ger.usarBase ? ger.base : null })
          }
          className="flex items-center gap-1.5 rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110 disabled:opacity-40"
        >
          <Sparkles className="size-3.5" /> {temRoteiro ? 'Gerar um novo (vira outra versão)' : 'Gerar roteiro'}
        </button>
      </div>
      <p className="text-[11px] text-apagado">
        Usa o Claude Opus (a mesma cota do seu plano). Leva de 1 a 3 minutos. O jeito do canal fica em
        docs/estilo_roteiro.md.
      </p>
    </div>
  )

  return (
    <section id="roteiro" className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-semibold">Roteiro</h2>
        {temRoteiro && (
          <span className="font-mono text-[11px] text-apagado">
            v{versao} · {dados?.paragrafos} parágrafos · {dados?.palavras} palavras · ~{mmss(dados?.segundos ?? 0)} narrado
          </span>
        )}
        {temRoteiro && !trabalhando && (
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setVerHist(!verHist)} className={`${botao} flex items-center gap-1`}>
              <History className="size-3.5" /> Versões
            </button>
            <button
              onClick={() => {
                setTexto(dados?.texto ?? '')
                setModo(modo === 'editar' ? 'nada' : 'editar')
              }}
              className={`${botao} flex items-center gap-1`}
            >
              <Pencil className="size-3.5" /> Editar
            </button>
            <button onClick={() => setModo(modo === 'gerar' ? 'nada' : 'gerar')} className={`${botao} flex items-center gap-1`}>
              <Sparkles className="size-3.5" /> Gerar de novo
            </button>
            <button onClick={() => seletor.current?.click()} className={botao}>
              Substituir
            </button>
            <DaPasta rotulo="substituir da pasta" aoEscolher={(texto, nome) => chamar('', { texto, nome })} />
            {aprovado ? (
              <span className="flex items-center gap-1.5 text-xs text-ok">
                <CheckCircle2 className="size-4" /> Aprovado
              </span>
            ) : (
              <button
                onClick={async () => {
                  try {
                    await api(`/videos/${videoId}/roteiro/aprovar`, { method: 'POST' })
                  } catch (e) {
                    return alert(String(e).match(/"detail":"([^"]+)"/)?.[1] ?? String(e)) // ex.: conferência ainda rodando
                  }
                  aoMudar()
                }}
                disabled={conferindo}
                title={conferindo ? 'Espere a conferência do roteiro terminar' : undefined}
                className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {conferindo ? 'Conferindo…' : 'Aprovar roteiro'}
              </button>
            )}
          </div>
        )}
      </header>

      <input ref={seletor} type="file" accept=".txt,text/plain" className="hidden" onChange={(e) => receberArquivo(e.target.files?.[0])} />

      {trabalhando && (
        <div className="mb-3 flex items-center gap-3 rounded-lg border border-andamento/40 bg-andamento/5 p-4">
          <Loader2 className="size-5 animate-spin text-andamento" />
          <p className="text-sm">{etapa.detalhe ?? 'o roteirista está trabalhando…'} (pode navegar à vontade)</p>
        </div>
      )}

      {!temRoteiro && !trabalhando && modo === 'nada' && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setArrastando(true)
            }}
            onDragLeave={() => setArrastando(false)}
            onDrop={(e) => {
              e.preventDefault()
              setArrastando(false)
              receberArquivo(e.dataTransfer.files[0])
            }}
            onClick={() => seletor.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors ${
              arrastando ? 'border-ouro bg-ouro/5' : 'border-borda-forte hover:border-suave'
            }`}
          >
            <Upload className="size-6 text-suave" />
            <p className="text-sm">
              Arraste o <b>.txt</b> do roteiro, ou <span className="text-ouro underline">clique para escolher</span>
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setModo('colar')
              }}
              className="mt-1 flex items-center gap-1.5 text-xs text-suave hover:text-texto"
            >
              <ClipboardPaste className="size-3.5" /> prefiro colar o texto
            </button>
            <DaPasta aoEscolher={(texto, nome) => chamar('', { texto, nome })} />
          </div>
          <button
            onClick={() => setModo('gerar')}
            className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-ouro/40 px-6 py-8 text-center hover:border-ouro hover:bg-ouro/5"
          >
            <Sparkles className="size-6 text-ouro" />
            <p className="text-sm">
              <b>Gerar com o Claude</b>
            </p>
            <p className="text-xs text-apagado">do zero ou a partir de um roteiro base</p>
          </button>
        </div>
      )}

      {modo === 'gerar' && !trabalhando && <div className="mb-3">{formGerar}</div>}

      {(modo === 'colar' || modo === 'editar') && (
        <div className="mb-3 flex flex-col gap-2">
          <textarea
            autoFocus
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Cole o roteiro aqui… (parágrafos separados por uma linha em branco)"
            className="h-96 w-full resize-y rounded-lg border border-borda-forte bg-painel-2 p-3 text-sm leading-relaxed outline-none focus:border-suave"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setModo('nada')} className={botao}>
              Cancelar
            </button>
            <button
              onClick={() => chamar('', { texto, nome: modo === 'editar' ? 'editado à mão' : 'roteiro colado' })}
              className="rounded-md bg-ouro px-3 py-1.5 text-xs font-semibold text-fundo"
            >
              {modo === 'editar' ? 'Salvar como nova versão' : 'Enviar roteiro'}
            </button>
          </div>
        </div>
      )}

      {temRoteiro && modo !== 'editar' && (
        <div className="max-h-96 overflow-y-auto rounded-lg border border-borda bg-painel-2 p-4">
          <div className="mb-2 flex items-center gap-1.5 font-mono text-[11px] text-apagado">
            <FileText className="size-3.5" /> {String(etapa.dados.arquivo_original ?? 'roteiro.txt')}
          </div>
          {dados!.texto!.split(/\n\s*\n/).map((p, k) => (
            <p key={k} className="mb-3 text-sm leading-relaxed text-texto/90 last:mb-0">
              {p}
            </p>
          ))}
        </div>
      )}

      {temRoteiro && !trabalhando && modo !== 'editar' && <ConferenciaRoteiro videoId={videoId} versao={versao} />}

      {/* ajuste fino com o Claude: devolve só os parágrafos alterados */}
      {temRoteiro && !trabalhando && modo === 'nada' && (
        <div className="mt-3 flex items-start gap-2">
          <textarea
            value={pedido}
            onChange={(e) => setPedido(e.target.value)}
            onKeyDown={async (e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && pedido.trim()) {
                if (await chamar('/ajustar', { pedido })) setPedido('')
              }
            }}
            placeholder="Ajuste fino com o Claude: “deixa o gancho da abertura mais forte”, “corta a parte do Swain pela metade”, “põe uma piada no fim da seção do Tahm”… (Ctrl+Enter envia)"
            className={`${campo} h-16 flex-1 resize-y`}
          />
          <button
            disabled={!pedido.trim()}
            onClick={async () => {
              if (await chamar('/ajustar', { pedido })) setPedido('')
            }}
            className="flex shrink-0 items-center gap-1.5 rounded-md bg-ouro px-3 py-2 text-xs font-semibold text-fundo hover:brightness-110 disabled:opacity-40"
          >
            <Send className="size-3.5" /> Ajustar
          </button>
        </div>
      )}

      {temRoteiro && verHist && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-borda bg-painel-2 p-3">
            <p className="mb-2 text-xs font-medium text-suave">Conversa com o roteirista</p>
            {hist.conversa.length === 0 && <p className="text-xs text-apagado">Nenhum pedido ainda.</p>}
            <ul className="flex flex-col gap-2">
              {[...hist.conversa].reverse().map((c, k) => (
                <li key={k} className="text-xs">
                  <span className="font-mono text-apagado">
                    v{c.versao} · {quando(c.quando)}
                  </span>
                  {c.pedido && <p className="text-texto/85">“{c.pedido}”</p>}
                  <p className="text-ok">→ {c.resumo}</p>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-borda bg-painel-2 p-3">
            <p className="mb-2 text-xs font-medium text-suave">Versões</p>
            <ul className="flex flex-col gap-1.5">
              {[...hist.versoes].reverse().map((v) => (
                <li key={v.versao} className="flex items-center gap-2 text-xs">
                  <span className={`font-mono ${v.versao === versao ? 'text-ouro' : 'text-apagado'}`}>v{v.versao}</span>
                  <span className="min-w-0 flex-1 truncate text-texto/80">{v.inicio}</span>
                  <span className="shrink-0 font-mono text-apagado">{v.palavras} pal.</span>
                  {v.versao !== versao && (
                    <button onClick={() => chamar('/restaurar', { versao: v.versao })} className="shrink-0 text-suave underline hover:text-texto">
                      voltar
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-red-400">{erro}</p>}
    </section>
  )
}
