"""De-bleed EXPÉRIMENTAL via Demucs (local, MIT) — palier 2.

⚠️ Demucs est entraîné sur de la musique populaire (stems voix/batterie/basse/
autres). Sur des cordes classiques, l'isolation est approximative et peut
dénaturer — option expérimentale, à valider à l'oreille. On conserve par défaut
le stem « other » (non voix/batterie/basse), le plus proche des cordes.
"""
from __future__ import annotations

import logging
import os

from . import io_wav

logger = logging.getLogger("dlz")


def isolate(input_path: str, outdir: str, model: str = "htdemucs", stem: str = "other") -> str:
    """Sépare via Demucs et écrit le stem choisi en WAV ; retourne son chemin."""
    try:
        import torch
        from demucs.apply import apply_model
        from demucs.audio import AudioFile
        from demucs.pretrained import get_model
    except Exception as e:  # torch/demucs absents ou API changée
        raise RuntimeError(f"Demucs/torch indisponibles (palier 2 requis) : {e}")

    logger.info("de-bleed Demucs (%s) — expérimental sur cordes…", model)
    m = get_model(model)
    m.cpu().eval()
    # lecture à la fréquence/canaux du modèle (stéréo), puis normalisation demucs
    wav = AudioFile(input_path).read(streams=0, samplerate=m.samplerate,
                                     channels=m.audio_channels)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.no_grad():
        sources = apply_model(m, wav[None], device="cpu", progress=False)[0]
    sources = sources * (ref.std() + 1e-8) + ref.mean()

    names = list(m.sources)
    idx = names.index(stem) if stem in names else len(names) - 1
    arr = sources[idx].cpu().numpy().T  # (n, ch)
    os.makedirs(outdir, exist_ok=True)
    out_path = os.path.join(outdir, "_debleed.wav")
    io_wav.write_wav(out_path, arr.astype("float32"), int(m.samplerate), "PCM_24")
    logger.info("de-bleed: stem '%s' (%s) isolé -> %s", stem, names, out_path)
    return out_path
