import { useEffect, useState } from 'react'
import { Quadro } from './telas/Quadro'
import { Storyboard } from './telas/Storyboard'
import { Video } from './telas/Video'

/** Rotas por hash: #/ (quadro) e #/video/<id>. Sem servidor de rotas — tudo local. */
function useRota() {
  const [hash, setHash] = useState(window.location.hash || '#/')
  useEffect(() => {
    const aoMudar = () => setHash(window.location.hash || '#/')
    window.addEventListener('hashchange', aoMudar)
    return () => window.removeEventListener('hashchange', aoMudar)
  }, [])
  return hash
}

export default function App() {
  const rota = useRota()
  const sb = rota.match(/^#\/video\/(\d+)\/storyboard/)
  if (sb) return <Storyboard id={Number(sb[1])} />
  const video = rota.match(/^#\/video\/(\d+)/)
  return video ? <Video id={Number(video[1])} /> : <Quadro />
}
