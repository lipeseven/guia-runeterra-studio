"""CLAP (laion/larger_clap_general, local): liga áudio e texto no mesmo espaço — classifica sons e acha
um efeito sonoro pela descrição ("deep cinematic boom")."""
from __future__ import annotations

import numpy as np
import torch
from scipy.signal import resample_poly

NOME = "laion/larger_clap_general"


class Clap:
    def __init__(self, dispositivo: str | None = None) -> None:
        from transformers import ClapModel, ClapProcessor

        self.dev = dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        self.proc = ClapProcessor.from_pretrained(NOME)
        self.modelo = ClapModel.from_pretrained(NOME).to(self.dev).eval()

    @staticmethod
    def _vetor(saida) -> torch.Tensor:
        t = saida.pooler_output if hasattr(saida, "pooler_output") else saida
        return torch.nn.functional.normalize(t, dim=-1)

    @torch.no_grad()
    def textos(self, descricoes: list[str]) -> np.ndarray:
        e = self.proc(text=descricoes, return_tensors="pt", padding=True).to(self.dev)
        return self._vetor(self.modelo.get_text_features(**e)).cpu().numpy()

    @torch.no_grad()
    def audios(self, trechos: list[np.ndarray], sr: int) -> np.ndarray:
        """Trechos mono float32 na taxa `sr` → vetores normalizados."""
        saida = []
        for k in range(0, len(trechos), 32):
            lote = [resample_poly(x, 48000, sr).astype(np.float32) if sr != 48000 else x.astype(np.float32)
                    for x in trechos[k:k + 32]]
            e = self.proc(audio=lote, sampling_rate=48000, return_tensors="pt").to(self.dev)
            saida.append(self._vetor(self.modelo.get_audio_features(**e)).cpu().numpy())
        return np.concatenate(saida) if saida else np.zeros((0, 512), dtype=np.float32)

    def classificar(self, trechos: list[np.ndarray], sr: int, rotulos: dict[str, str]) -> list[tuple[str, float]]:
        if not trechos:
            return []
        t = self.textos(list(rotulos.values()))
        logits = self.audios(trechos, sr) @ t.T * 100
        p = np.exp(logits - logits.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        nomes = list(rotulos)
        return [(nomes[i], float(linha[i])) for linha, i in zip(p, p.argmax(1))]

    def liberar(self) -> None:
        del self.modelo
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
