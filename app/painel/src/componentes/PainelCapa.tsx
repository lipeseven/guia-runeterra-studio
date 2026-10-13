import { CheckCircle2, ImagePlus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, arquivo } from '../api'

type Circulo = { cx: number; cy: number; r: number; nome?: string }
type DadosCapa = { capa: string | null; circulos: Circulo[] }

const paraBase64 = (f: File) =>
  new Promise<string>((ok, falha) => {
    const leitor = new FileReader()
    leitor.onload = () => ok(String(leitor.result).split(',')[1])
    leitor.onerror = falha
    leitor.readAsDataURL(f)
  })

/** Capa do vídeo (grade de personagens): vira a abertura e a fonte dos ícones das seções. */
export function PainelCapa({ videoId, aprovada, aoMudar }: { videoId: number; aprovada: boolean; aoMudar: () => void }) {
  const [dados, setDados] = useState<DadosCapa | null>(null)
  const [arrastando, setArrastando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [versao, setVersao] = useState(0)
  const seletor = useRef<HTMLInputElement>(null)
  const img = useRef<HTMLImageElement>(null)
  const [tam, setTam] = useState({ w: 1, h: 1 })

  useEffect(() => {
    api<DadosCapa>(`/videos/${videoId}/capa`).then(setDados)
  }, [videoId, versao])

  const enviar = async (f: File | undefined) => {
    if (!f) return
    setErro(null)
    try {
      await api(`/videos/${videoId}/capa`, { method: 'POST', body: JSON.stringify({ nome: f.name, dados_base64: await paraBase64(f) }) })
      setVersao((n) => n + 1)
      aoMudar()
    } catch (e) {
      setErro(String(e))
    }
  }

  return (
    <section className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-center gap-3">
        <h2 className="text-sm font-semibold">Capa</h2>
        {dados?.capa && (
          <span className={`font-mono text-[11px] ${dados.circulos.length ? 'text-apagado' : 'text-atencao'}`}>
            {dados.circulos.length ? `${dados.circulos.length} ícones detectados` : 'nenhum ícone detectado — confira a capa'}
          </span>
        )}
        {dados?.capa && (
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => seletor.current?.click()} className="rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:bg-painel-2">
              Substituir
            </button>
            {aprovada ? (
              <span className="flex items-center gap-1.5 text-xs text-ok">
                <CheckCircle2 className="size-4" /> Aprovada
              </span>
            ) : (
              <button
                onClick={async () => {
                  await api(`/videos/${videoId}/capa/aprovar`, { method: 'POST' })
                  aoMudar()
                }}
                className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
              >
                Aprovar capa
              </button>
            )}
          </div>
        )}
      </header>
      <input ref={seletor} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => enviar(e.target.files?.[0])} />

      {dados?.capa ? (
        <div className="relative overflow-hidden rounded-lg border border-borda">
          <img
            ref={img}
            key={`${dados.capa}-${versao}`}
            src={`${arquivo(dados.capa)}&v=${versao}`}
            onLoad={() => img.current && setTam({ w: img.current.clientWidth, h: img.current.clientHeight })}
            className="block w-full"
            alt="Capa do vídeo"
          />
          {/* círculos detectados, numerados na ordem de leitura */}
          {dados.circulos.map((c, k) => {
            const r = c.r * Math.min(tam.w, tam.h)
            return (
              <div
                key={k}
                className="absolute grid place-items-center rounded-full border-2 border-ouro"
                style={{ left: c.cx * tam.w - r, top: c.cy * tam.h - r, width: 2 * r, height: 2 * r }}
              >
                <span className="rounded bg-fundo/80 px-1.5 font-mono text-[11px] text-ouro">{k + 1}</span>
              </div>
            )
          })}
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setArrastando(true)
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault()
            setArrastando(false)
            enviar(e.dataTransfer.files[0])
          }}
          onClick={() => seletor.current?.click()}
          className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center ${
            arrastando ? 'border-ouro bg-ouro/5' : 'border-borda-forte hover:border-suave'
          }`}
        >
          <ImagePlus className="size-6 text-suave" />
          <p className="text-sm">
            Arraste a <b>capa</b> (grade de personagens) ou <span className="text-ouro underline">clique para escolher</span>
          </p>
          <p className="text-xs text-apagado">Ela vira a abertura do vídeo e os ícones de cada seção.</p>
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-red-400">{erro}</p>}
    </section>
  )
}
