import { useCallback, useEffect, useState } from 'react'

export type Status = 'pendente' | 'andamento' | 'concluido' | 'atencao' | 'em_breve'

export type Coluna = { chave: string; titulo: string }

export type VideoResumo = {
  id: number
  titulo: string
  slug: string
  coluna: string
  ordem: number
  capa: string | null
  atualizado_em: string
  progresso: Partial<Record<Status, number>>
  total_etapas: number
  pendencias: number
  travado: number
}

export type Etapa = {
  chave: string
  numero: number
  titulo: string
  descricao: string
  status: Status
  resumo: string | null
  detalhe: string | null
  dados: Record<string, unknown>
  atualizado_em: string | null
}

export type Pendencia = { id: number; etapa: string | null; chave: string | null; titulo: string; texto: string; criada_em: string }
export type Atividade = { id: number; texto: string; tipo: 'info' | 'ok' | 'alerta'; quando: string }

export type Video = VideoResumo & { etapas: Etapa[]; pendencias: Pendencia[]; atividade: Atividade[] }

export type Recursos = {
  gpu: { ok: boolean; nome?: string; uso?: number; vram_usada?: number; vram_total?: number; temperatura?: number; estado?: string }
  disco: { livre: number; total: number; dados: number; projetos: number }
  servicos: { nome: string; papel: string; estado: string; detalhe: string }[]
}

export const arquivo = (caminho: string) => `/api/arquivo?caminho=${encodeURIComponent(caminho)}`

export async function api<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  const r = await fetch(`/api${caminho}`, {
    ...opcoes,
    headers: { 'Content-Type': 'application/json', ...(opcoes?.headers ?? {}) },
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

/** Busca e atualiza sozinho a cada `ms` (o painel é "ao vivo"). */
export function useAoVivo<T>(caminho: string, ms = 3000) {
  const [dados, setDados] = useState<T | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const recarregar = useCallback(() => {
    api<T>(caminho)
      .then((d) => {
        setDados(d)
        setErro(null)
      })
      .catch((e) => setErro(String(e)))
  }, [caminho])
  useEffect(() => {
    recarregar()
    const t = setInterval(recarregar, ms)
    return () => clearInterval(t)
  }, [recarregar, ms])
  return { dados, erro, recarregar, setDados }
}

export const gb = (bytes: number) => `${(bytes / 1e9).toFixed(bytes > 1e11 ? 0 : 1)} GB`

export function quando(iso: string) {
  const d = new Date(iso)
  const hoje = new Date()
  const mesmoDia = d.toDateString() === hoje.toDateString()
  return mesmoDia
    ? d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}
