import { CheckCircle2, Cpu, HardDrive, LayoutPanelTop, Trash2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { api, arquivo, gb, quando, useAoVivo, type Etapa, type Recursos, type Video as TVideo } from '../api'
import { CirculoEstado, COR, RotuloEstado } from '../componentes/Estado'
import { Moldura } from '../componentes/Moldura'

export function Video({ id }: { id: number }) {
  const { dados: v, recarregar } = useAoVivo<TVideo>(`/videos/${id}`, 3000)
  const { dados: rec } = useAoVivo<Recursos>('/recursos', 4000)

  const trilha = (
    <>
      <a href="#/" className="hover:text-texto">Quadro</a>
      <span className="text-apagado">/</span>
      <span className="truncate text-texto">{v?.titulo ?? '…'}</span>
    </>
  )
  if (!v) return <Moldura trilha={trilha}><p className="p-6 text-suave">Carregando…</p></Moldura>

  const concluidas = v.etapas.filter((e) => e.status === 'concluido').length
  const previa = [...v.etapas].reverse().find((e) => typeof e.dados.video === 'string')

  return (
    <Moldura trilha={trilha}>
      <div className="mx-auto max-w-[1680px] px-6 py-6">
        <div className="flex items-start gap-4">
          <div className="min-w-0">
            <h1 className="font-titulo text-4xl leading-tight font-medium tracking-tight">{v.titulo}</h1>
            <p className="mt-1 font-mono text-xs text-suave">
              {concluidas}/{v.etapas.length} etapas · {v.pendencias.length} pendência{v.pendencias.length === 1 ? '' : 's'} · atualizado {quando(v.atualizado_em)}
            </p>
          </div>
          <button
            disabled
            title="Em breve: revisão cena a cena com o player do Remotion"
            className="ml-auto flex shrink-0 items-center gap-2 rounded-lg border border-borda-forte px-4 py-2 text-sm text-suave"
          >
            <LayoutPanelTop className="size-4" /> Abrir storyboard
          </button>
        </div>

        {/* Trilha de etapas */}
        <div className="mt-6 flex gap-3 overflow-x-auto pb-2">
          {v.etapas.map((e) => (
            <CardEtapa key={e.chave} etapa={e} />
          ))}
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Painel titulo="Precisa de você" lateral="revisão por exceção · o resto segue sozinho">
              {v.pendencias.length === 0 ? (
                <div className="flex items-center gap-3 rounded-lg border border-dashed border-borda-forte p-4">
                  <CheckCircle2 className="size-5 text-ok" />
                  <div>
                    <p className="text-sm">Nada precisa de você agora</p>
                    <p className="text-xs text-suave">Quando algo pedir revisão (roteiro, cena sem imagem boa, rascunho pronto), aparece aqui.</p>
                  </div>
                </div>
              ) : (
                <ul className="flex flex-col gap-2">
                  {v.pendencias.map((p) => (
                    <li key={p.id} className="flex items-start gap-3 rounded-lg border border-atencao/30 bg-atencao/5 p-4">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-atencao">{p.titulo}</p>
                        <p className="mt-1 text-sm text-texto/85">{p.texto}</p>
                        {p.etapa && <p className="mt-1.5 font-mono text-[11px] text-apagado">etapa: {p.etapa}</p>}
                      </div>
                      <button
                        onClick={async () => {
                          await api(`/pendencias/${p.id}/resolver`, { method: 'POST' })
                          recarregar()
                        }}
                        className="shrink-0 rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:border-ok hover:text-ok"
                      >
                        Está ok
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Painel>

            <Painel titulo="Prévia" lateral={previa ? `${previa.titulo.toLowerCase()} · ${previa.detalhe ?? ''}` : undefined}>
              {previa ? (
                <video key={String(previa.dados.video)} src={arquivo(String(previa.dados.video))} controls className="w-full rounded-lg bg-black" />
              ) : (
                <p className="text-sm text-suave">Ainda não há rascunho nem render para assistir.</p>
              )}
            </Painel>
          </div>

          <div className="flex flex-col gap-5">
            <Painel titulo="Recursos">
              {rec ? <PainelRecursos rec={rec} /> : <p className="text-sm text-suave">…</p>}
            </Painel>
            <Painel titulo="Atividade">
              <ul className="flex flex-col">
                {v.atividade.map((a) => (
                  <li key={a.id} className="flex items-start gap-3 border-b border-borda/60 py-2 text-sm last:border-0">
                    <span className="w-12 shrink-0 pt-0.5 font-mono text-[11px] text-apagado">{quando(a.quando)}</span>
                    <span className={`mt-1.5 size-1.5 shrink-0 rounded-full ${a.tipo === 'ok' ? 'bg-ok' : a.tipo === 'alerta' ? 'bg-atencao' : 'bg-andamento'}`} />
                    <span className="text-texto/85">{a.texto}</span>
                  </li>
                ))}
              </ul>
            </Painel>
          </div>
        </div>
      </div>
    </Moldura>
  )
}

function CardEtapa({ etapa: e }: { etapa: Etapa }) {
  const apagado = e.status === 'em_breve'
  return (
    <div
      title={e.descricao}
      className={`flex min-h-[148px] w-[184px] shrink-0 flex-col rounded-xl border p-3.5 ${
        apagado ? 'border-dashed border-borda bg-painel/40' : e.status === 'atencao' ? 'border-atencao/40 bg-painel' : 'border-borda bg-painel'
      }`}
    >
      <div className="flex items-start justify-between">
        <CirculoEstado status={e.status} />
        <span className="font-mono text-[11px] text-apagado">{String(e.numero).padStart(2, '0')}</span>
      </div>
      <h3 className={`mt-3 text-sm font-semibold ${apagado ? 'text-suave' : ''}`}>{e.titulo}</h3>
      <p className={`mt-0.5 font-mono text-[11px] ${apagado ? 'text-apagado' : 'text-texto/90'}`}>{e.resumo ?? (apagado ? 'ainda não construída' : '—')}</p>
      {e.detalhe && <p className="mt-0.5 truncate text-[11px] text-suave">{e.detalhe}</p>}
      <div className="mt-auto pt-3">
        <RotuloEstado status={e.status} />
      </div>
    </div>
  )
}

function Painel({ titulo, lateral, children }: { titulo: string; lateral?: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-borda bg-painel p-4">
      <header className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">{titulo}</h2>
        {lateral && <span className="truncate font-mono text-[11px] text-apagado">{lateral}</span>}
      </header>
      {children}
    </section>
  )
}

function Barra({ valor, cor = 'bg-ok' }: { valor: number; cor?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-borda">
      <div className={`h-full rounded-full ${cor}`} style={{ width: `${Math.min(100, Math.max(2, valor))}%` }} />
    </div>
  )
}

function PainelRecursos({ rec }: { rec: Recursos }) {
  const { gpu, disco } = rec
  const usadoDisco = 100 - (disco.livre / disco.total) * 100
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-borda bg-painel-2 p-3">
        <div className="flex items-center gap-2 text-sm">
          <Cpu className="size-4 text-suave" />
          <span className="font-medium">{gpu.ok ? gpu.nome?.replace('NVIDIA GeForce ', '') : 'GPU indisponível'}</span>
          {gpu.ok && (
            <span className={`ml-auto font-mono text-[11px] ${gpu.estado === 'ocupada' ? 'text-andamento' : 'text-ok'}`}>
              {gpu.estado} · {gpu.temperatura}°C
            </span>
          )}
        </div>
        {gpu.ok && (
          <div className="mt-3 grid grid-cols-[48px_1fr_72px] items-center gap-2 font-mono text-[11px] text-suave">
            <span>uso</span>
            <Barra valor={gpu.uso ?? 0} cor="bg-andamento" />
            <span className="text-right">{gpu.uso}%</span>
            <span>VRAM</span>
            <Barra valor={((gpu.vram_usada ?? 0) / (gpu.vram_total ?? 1)) * 100} cor="bg-andamento" />
            <span className="text-right">{((gpu.vram_usada ?? 0) / 1024).toFixed(1)}/{((gpu.vram_total ?? 0) / 1024).toFixed(0)} GB</span>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-borda bg-painel-2 p-3">
        <div className="flex items-center gap-2 text-sm">
          <HardDrive className="size-4 text-suave" />
          <span className="font-medium">Disco C:</span>
          <span className="ml-auto font-mono text-[11px] text-suave">{gb(disco.livre)} livres</span>
        </div>
        <div className="mt-3">
          <Barra valor={usadoDisco} cor={usadoDisco > 90 ? 'bg-atencao' : 'bg-ok'} />
        </div>
        <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-suave">
          <span>Studio: dados {gb(disco.dados)} · projetos {gb(disco.projetos)}</span>
          <button disabled title="Em breve (Fase 4): limpeza de vídeos publicados" className="flex items-center gap-1 text-apagado">
            <Trash2 className="size-3" /> limpar
          </button>
        </div>
      </div>

      <ul className="flex flex-col">
        {rec.servicos.map((s) => {
          const ok = ['pronto', 'ligado', 'via chat'].includes(s.estado)
          return (
            <li key={s.nome} className="flex items-center gap-3 border-b border-borda/60 py-2 last:border-0">
              <span className={`size-2 shrink-0 rounded-full ${ok ? 'bg-ok' : 'bg-apagado'}`} />
              <div className="min-w-0">
                <p className="text-sm">
                  {s.nome} <span className="text-suave">· {s.papel}</span>
                </p>
                <p className="font-mono text-[11px] text-apagado">{s.detalhe}</p>
              </div>
              <span className={`ml-auto shrink-0 font-mono text-[11px] ${ok ? COR.concluido : 'text-apagado'}`}>{s.estado}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
