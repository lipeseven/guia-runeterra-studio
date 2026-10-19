import { Globe, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'

type Achado = { imagem: string; miniatura: string; titulo: string; pagina: string; fonte: string; largura: number; altura: number; licenca?: string; autor?: string }
export type MidiaBaixada = { midia_id: number; nome: string; miniatura: string }

/** Busca de imagens na internet (DuckDuckGo + Wikimedia Commons). A escolhida é baixada para o acervo e usada na hora. */
export function BuscaInternet({ inicial, usar, compacta }: { inicial: string; usar: (m: MidiaBaixada) => Promise<void>; compacta?: boolean }) {
  const [aberto, setAberto] = useState(false)
  const [consulta, setConsulta] = useState(inicial)
  const [achados, setAchados] = useState<Achado[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  const [baixando, setBaixando] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const buscar = async (n: number) => {
    if (!consulta.trim()) return
    setBuscando(true)
    setErro(null)
    try {
      setAchados(await api<Achado[]>(`/internet/buscar?q=${encodeURIComponent(consulta)}&n=${n}`))
    } catch (e) {
      setErro(String(e))
    } finally {
      setBuscando(false)
    }
  }
  if (!aberto)
    return (
      <button
        onClick={() => {
          setConsulta(inicial)
          setAberto(true)
        }}
        className="mt-2 flex items-center gap-1.5 text-[11px] text-suave hover:text-texto"
      >
        <Globe className="size-3.5" /> nada serve? buscar na internet
      </button>
    )
  return (
    <div className="mt-2 rounded-md border border-borda/70 p-2">
      <div className="flex gap-2">
        <Globe className="size-4 self-center text-suave" />
        <input
          autoFocus
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar(24)}
          placeholder="Buscar imagem na internet (em inglês costuma achar mais) e Enter"
          className="flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1 text-xs outline-none focus:border-suave"
        />
        {buscando && <Loader2 className="size-4 animate-spin self-center text-suave" />}
        <button onClick={() => setAberto(false)} className="text-[11px] text-apagado hover:text-texto">
          fechar
        </button>
      </div>
      {erro && <p className="mt-1 text-[11px] text-red-400">{erro}</p>}
      {achados && (
        <>
          <div className={`mt-2 grid gap-2 ${compacta ? 'grid-cols-6' : 'grid-cols-4'}`}>
            {achados.map((a) => (
              <button
                key={a.imagem}
                disabled={baixando !== null}
                title={`${a.titulo}\n${a.fonte} · ${a.largura}×${a.altura}`}
                onClick={async () => {
                  setBaixando(a.imagem)
                  setErro(null)
                  try {
                    const m = await api<MidiaBaixada>('/internet/baixar', {
                      method: 'POST',
                      body: JSON.stringify({ url: a.imagem, titulo: a.titulo, pagina: a.pagina, fonte: a.fonte, licenca: a.licenca ?? '', autor: a.autor ?? '' }),
                    })
                    await usar(m)
                    setAberto(false)
                    setAchados(null)
                  } catch (e) {
                    setErro(String(e))
                  } finally {
                    setBaixando(null)
                  }
                }}
                className="relative overflow-hidden rounded-md border border-borda text-left hover:border-ouro disabled:opacity-60"
              >
                <img src={a.miniatura} alt="" referrerPolicy="no-referrer" className="aspect-video w-full object-cover" />
                <span className="block truncate px-1.5 py-0.5 font-mono text-[10px] text-suave">
                  {a.largura}×{a.altura} · {a.fonte}
                </span>
                {baixando === a.imagem && (
                  <span className="absolute inset-0 flex items-center justify-center bg-black/60">
                    <Loader2 className="size-5 animate-spin" />
                  </span>
                )}
              </button>
            ))}
          </div>
          {achados.length > 0 && achados.length % 24 === 0 && (
            <button
              disabled={buscando}
              onClick={() => buscar(achados.length + 24)}
              className="mt-2 w-full rounded-md border border-borda py-1 text-[11px] text-suave hover:border-suave hover:text-texto"
            >
              Mostrar mais
            </button>
          )}
          <p className="mt-1 text-[10px] text-apagado">A imagem escolhida é baixada para o acervo (dados/acervo_internet) com a página de origem guardada para os créditos.</p>
        </>
      )}
    </div>
  )
}

/** Clipe por link (YouTube etc.): o sistema baixa (até 1080p) e corta em tomadas; depois aparece na busca de clipes. */
export function ClipeDoLink() {
  const [url, setUrl] = useState('')
  const [estado, setEstado] = useState<{ pendentes: string[]; ultimos: { url: string; titulo?: string; erro?: string }[] } | null>(null)
  const ver = () => api<NonNullable<typeof estado>>('/acervo/clipes-baixados').then(setEstado)
  const enviar = async () => {
    if (!url.trim()) return
    await api('/acervo/clipe-do-link', { method: 'POST', body: JSON.stringify({ url }) })
    setUrl('')
    ver()
    const t = setInterval(async () => {
      const e = await api<NonNullable<typeof estado>>('/acervo/clipes-baixados')
      setEstado(e)
      if (e.pendentes.length === 0) setTimeout(() => clearInterval(t), 20000) // dá tempo de cortar as tomadas
    }, 4000)
  }
  return (
    <div className="mt-2 text-[11px] text-suave">
      <div className="flex gap-2">
        <Globe className="size-3.5 self-center" />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && enviar()}
          placeholder="Ou cole o link de um vídeo (YouTube…) e Enter: ele é baixado e cortado em tomadas"
          className="flex-1 rounded-md border border-borda bg-painel-2 px-2 py-1 text-xs outline-none focus:border-suave"
        />
      </div>
      {estado && (
        <ul className="mt-1 flex flex-col gap-0.5">
          {estado.pendentes.map((u) => (
            <li key={u} className="flex items-center gap-1 text-andamento">
              <Loader2 className="size-3 animate-spin" /> na fila: {u}
            </li>
          ))}
          {estado.ultimos.slice(0, 3).map((x) => (
            <li key={x.url} className={x.erro ? 'text-red-400' : 'text-ok'}>
              {x.erro ? `falhou: ${x.erro}` : `baixado: “${x.titulo}” — aparece na busca de clipes depois de cortar as tomadas`}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
