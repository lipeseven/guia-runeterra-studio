import { CheckCircle2, Cpu, HardDrive, LayoutPanelTop, Lock, Trash2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { api, arquivo, gb, quando, useAoVivo, type Etapa, type Recursos, type Video as TVideo } from '../api'
import { CirculoEstado, COR, RotuloEstado } from '../componentes/Estado'
import { MenuCard } from '../componentes/MenuCard'
import { Moldura } from '../componentes/Moldura'
import { PainelCapa } from '../componentes/PainelCapa'
import { PainelGravacao } from '../componentes/PainelGravacao'
import { PainelPublicacao } from '../componentes/PainelPublicacao'
import { PainelRoteiro } from '../componentes/PainelRoteiro'

export function Video({ id }: { id: number }) {
  const { dados: v, erro, recarregar } = useAoVivo<TVideo>(`/videos/${id}`, 3000)
  const { dados: rec } = useAoVivo<Recursos>('/recursos', 4000)

  const trilha = (
    <>
      <a href="#/" className="hover:text-texto">Quadro</a>
      <span className="text-apagado">/</span>
      <span className="truncate text-texto">{v?.titulo ?? '…'}</span>
    </>
  )
  if (erro?.startsWith('Error: 404'))
    return (
      <Moldura trilha={trilha}>
        <div className="p-6">
          <p className="text-sm">Este vídeo não existe mais (foi excluído).</p>
          <a href="#/" className="mt-2 inline-block text-sm text-ouro underline">Voltar ao quadro</a>
        </div>
      </Moldura>
    )
  if (!v) return <Moldura trilha={trilha}><p className="p-6 text-suave">Carregando…</p></Moldura>

  const concluidas = v.etapas.filter((e) => e.status === 'concluido').length
  const previa = [...v.etapas].reverse().find((e) => typeof e.dados.video === 'string' || typeof e.dados.audio === 'string')
  const roteiro = v.etapas.find((e) => e.chave === 'roteiro')!
  const gravacao = v.etapas.find((e) => e.chave === 'gravacao')!
  const publicacaoEtapa = v.etapas.find((e) => e.chave === 'publicacao')!

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
          <div className="ml-auto flex shrink-0 items-center gap-2">
          {Boolean(v.travado) && (
            <span className="flex items-center gap-1 text-xs text-ouro">
              <Lock className="size-3.5" /> travado
            </span>
          )}
          {v.etapas.some((e) => e.chave === 'rascunho' && typeof e.dados.video === 'string') ? (
            <a
              href={`#/video/${v.id}/storyboard`}
              className="ml-auto flex shrink-0 items-center gap-2 rounded-lg border border-ouro/60 px-4 py-2 text-sm text-ouro hover:bg-ouro/10"
            >
              <LayoutPanelTop className="size-4" /> Abrir storyboard
            </a>
          ) : (
            <button
              disabled
              title="O storyboard abre quando o primeiro rascunho estiver pronto"
              className="ml-auto flex shrink-0 items-center gap-2 rounded-lg border border-borda-forte px-4 py-2 text-sm text-apagado"
            >
              <LayoutPanelTop className="size-4" /> Abrir storyboard
            </button>
          )}
          <MenuCard video={v} aoMudar={recarregar} aoExcluir={() => (window.location.hash = '#/')} />
          </div>
        </div>

        {/* Trilha de etapas */}
        <div className="mt-6 flex gap-3 overflow-x-auto pb-2">
          {v.etapas.map((e) => (
            <CardEtapa key={e.chave} etapa={e} />
          ))}
        </div>

        {/* "Precisa de você" no topo: é a primeira coisa a ler, sem precisar rolar a tela */}
        <section
          className={`mt-5 rounded-xl border p-4 ${v.pendencias.length ? 'border-atencao/40 bg-painel' : 'border-borda bg-painel'}`}
        >
          <header className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className={`text-sm font-semibold ${v.pendencias.length ? 'text-atencao' : ''}`}>
              Precisa de você{v.pendencias.length ? ` (${v.pendencias.length})` : ''}
            </h2>
            <span className="truncate font-mono text-[11px] text-apagado">revisão por exceção · o resto segue sozinho</span>
          </header>
          {v.pendencias.length === 0 ? (
            <div className="flex items-center gap-3">
              <CheckCircle2 className="size-5 text-ok" />
              <p className="text-sm text-suave">Nada precisa de você agora.</p>
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
                  <AcaoPendencia chave={p.chave} id={p.id} videoId={v.id} aoMudar={recarregar} />
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="flex min-w-0 flex-col gap-5">
            {(['revisao', 'publicado'].includes(v.coluna) || publicacaoEtapa.status !== 'pendente') && (
              <PainelPublicacao videoId={v.id} etapa={publicacaoEtapa} publicado={v.coluna === 'publicado'} aoMudar={recarregar} />
            )}
            {(['gravacao', 'montagem', 'revisao', 'publicado'].includes(v.coluna) || gravacao.status !== 'pendente') && (
              <PainelGravacao videoId={v.id} etapa={gravacao} aoMudar={recarregar} />
            )}
            {(v.coluna !== 'ideia' || roteiro.status !== 'pendente') && (
              <>
                <ProximoPasso c={v.condicoes_direcao} direcao={v.etapas.find((e) => e.chave === 'direcao')!} />
                <PainelRoteiro videoId={v.id} etapa={roteiro} aoMudar={recarregar} />
                <PainelCapa videoId={v.id} aprovada={Boolean(v.capa_aprovada)} aoMudar={recarregar} />
              </>
            )}
            <Painel titulo="Prévia" lateral={previa ? `${previa.titulo.toLowerCase()} · ${previa.detalhe ?? ''}` : undefined}>
              {previa && typeof previa.dados.video === 'string' ? (
                <video key={previa.dados.video} src={arquivo(previa.dados.video)} controls className="w-full rounded-lg bg-black" />
              ) : previa && typeof previa.dados.audio === 'string' ? (
                <div>
                  <p className="mb-2 text-xs text-suave">Voz guia — só para o rascunho, nunca vai para o vídeo publicado.</p>
                  <audio key={`${previa.dados.audio}-${previa.atualizado_em}`} src={arquivo(previa.dados.audio)} controls className="w-full" />
                </div>
              ) : (
                <p className="text-sm text-suave">Ainda não há voz guia, rascunho nem render para ouvir/assistir.</p>
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

/** Diz em linguagem simples o que falta para o sistema seguir sozinho. */
function ProximoPasso({ c, direcao }: { c: TVideo['condicoes_direcao']; direcao: Etapa }) {
  const itens = [
    { ok: c.roteiro_aprovado, texto: 'roteiro aprovado' },
    { ok: c.voz_guia_pronta, texto: 'voz guia pronta' },
    { ok: c.capa_aprovada, texto: 'capa aprovada' },
  ]
  const tudo = itens.every((i) => i.ok)
  if (direcao.status === 'concluido' || direcao.status === 'andamento') return null
  return (
    <section className={`rounded-xl border p-4 ${tudo ? 'border-ok/40 bg-ok/5' : 'border-borda bg-painel'}`}>
      <h2 className="text-sm font-semibold">Próximo passo: Direção</h2>
      <p className="mt-1 text-sm text-suave">
        {tudo
          ? direcao.detalhe === 'diretor em construção'
            ? 'Tudo pronto. A direção vai começar sozinha assim que o diretor estiver construído.'
            : 'Tudo pronto: a direção começa sozinha.'
          : 'A direção começa sozinha quando estes três itens estiverem prontos — não precisa dar nenhum comando:'}
      </p>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1">
        {itens.map((i) => (
          <li key={i.texto} className={`flex items-center gap-1.5 text-sm ${i.ok ? 'text-ok' : 'text-suave'}`}>
            {i.ok ? <CheckCircle2 className="size-4" /> : <span className="size-3.5 rounded-full border border-current" />}
            {i.texto}
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Botão de cada pendência: algumas têm ação própria (ex.: aprovar roteiro); o resto é "Está ok". */
function AcaoPendencia({ chave, id, videoId, aoMudar }: { chave: string | null; id: number; videoId: number; aoMudar: () => void }) {
  const estilo = 'shrink-0 rounded-md border border-borda-forte px-3 py-1.5 text-xs hover:border-ok hover:text-ok'
  if (chave === 'publicar' || chave === 'limpeza')
    return (
      <button className={estilo} onClick={() => document.getElementById('publicacao')?.scrollIntoView({ behavior: 'smooth' })}>
        {chave === 'publicar' ? 'Ir para a publicação' : 'Escolher o que limpar'}
      </button>
    )
  if (chave === 'aprovar_gravacao')
    return (
      <div className="flex shrink-0 flex-col gap-1.5">
        <button className={estilo} onClick={() => document.getElementById('gravacao')?.scrollIntoView({ behavior: 'smooth' })}>
          Ouvir e ver os cortes
        </button>
        <button
          className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
          onClick={async () => {
            await api(`/videos/${videoId}/gravacao/aprovar`, { method: 'POST' })
            aoMudar()
          }}
        >
          Aprovar áudio limpo
        </button>
      </div>
    )
  if (chave === 'enviar_gravacao')
    return (
      <button className={estilo} onClick={() => document.getElementById('gravacao')?.scrollIntoView({ behavior: 'smooth' })}>
        Ir para a gravação
      </button>
    )
  if (chave === 'enviar_roteiro')
    return (
      <button className={estilo} onClick={() => document.getElementById('roteiro')?.scrollIntoView({ behavior: 'smooth' })}>
        Ir para o roteiro
      </button>
    )
  if (chave === 'ver_rascunho')
    return (
      <div className="flex shrink-0 flex-col gap-1.5">
        <a href={`#/video/${videoId}/storyboard`} className="rounded-md border border-ouro/60 px-3 py-1.5 text-center text-xs text-ouro hover:bg-ouro/10">
          Abrir storyboard
        </a>
        <button
          className={estilo}
          onClick={async () => {
            await api(`/pendencias/${id}/resolver`, { method: 'POST' })
            aoMudar()
          }}
        >
          Rascunho aprovado
        </button>
      </div>
    )
  if (chave === 'aprovar_capa')
    return (
      <button
        className="shrink-0 rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
        onClick={async () => {
          await api(`/videos/${videoId}/capa/aprovar`, { method: 'POST' })
          aoMudar()
        }}
      >
        Aprovar capa
      </button>
    )
  if (chave === 'aprovar_roteiro')
    return (
      <button
        className="shrink-0 rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-fundo hover:brightness-110"
        onClick={async () => {
          await api(`/videos/${videoId}/roteiro/aprovar`, { method: 'POST' })
          aoMudar()
        }}
      >
        Aprovar roteiro
      </button>
    )
  return (
    <button
      className={estilo}
      onClick={async () => {
        await api(`/pendencias/${id}/resolver`, { method: 'POST' })
        aoMudar()
      }}
    >
      {chave?.startsWith('erro_') ? 'Tentar de novo' : chave === 'ver_final' ? 'Vídeo aprovado' : 'Está ok'}
    </button>
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
