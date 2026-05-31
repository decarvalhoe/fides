"""Réverbe d'espace : IR synthétiques bundlées + résolution d'IR.

Les IR « presets » (chamber/room/hall) sont des réponses impulsionnelles
synthétiques (réflexions précoces + queue diffuse exponentielle), générées et
livrées avec le package — utilisables directement via `--ir hall|room|chamber`.
Pour de vraies salles, fournir un chemin WAV (ex. bibliothèque OpenAIR).
"""
from __future__ import annotations

import os

import numpy as np
from scipy.signal import butter, sosfilt

_HERE = os.path.dirname(__file__)

PRESETS = {
    "chamber": dict(rt60=0.8, predelay=0.012, er=6, seed=1),
    "room":    dict(rt60=1.3, predelay=0.018, er=8, seed=2),
    "hall":    dict(rt60=2.2, predelay=0.028, er=10, seed=3),
}


def synth_ir(rt60: float, predelay: float, er: int, sr: int = 48000, seed: int = 0) -> np.ndarray:
    """Génère une IR stéréo synthétique plausible (réflexions précoces + queue diffuse)."""
    rng = np.random.RandomState(seed)
    n = int((predelay + rt60 * 1.1) * sr)
    ir = np.zeros((n, 2), dtype=np.float64)
    p = int(predelay * sr)
    for k in range(er):                                  # réflexions précoces (taps épars)
        d = p + int(rng.uniform(0.003, 0.05 * (k + 1)) * sr)
        if d >= n:
            continue
        g = 0.82 ** (k + 1)
        ir[d, 0] += g * rng.uniform(0.6, 1.0) * (1 if rng.rand() > 0.5 else -1)
        d2 = min(d + int(rng.uniform(0.0005, 0.002) * sr), n - 1)
        ir[d2, 1] += g * rng.uniform(0.6, 1.0) * (1 if rng.rand() > 0.5 else -1)
    t = np.arange(n) / sr                                # queue diffuse exponentielle
    tail = rng.randn(n, 2) * np.exp(-t / (rt60 / 6.908))[:, None] * 0.5
    tail[:p] = 0
    ir += tail
    ir = sosfilt(butter(2, 8000, fs=sr, output="sos"), ir, axis=0)  # adoucit le très aigu
    ir /= (np.max(np.abs(ir)) + 1e-9)
    return ir.astype(np.float32)


def ir_dir() -> str:
    return os.path.join(_HERE, "ir")


def preset_path(name: str) -> str:
    return os.path.join(ir_dir(), f"{name}.wav")


def resolve_ir(spec: str) -> str:
    """Retourne un chemin d'IR à partir d'un preset (hall/room/chamber) ou d'un chemin."""
    if spec in PRESETS:
        p = preset_path(spec)
        if not os.path.exists(p):                        # cache : génère si absent
            import soundfile as sf
            os.makedirs(ir_dir(), exist_ok=True)
            sf.write(p, synth_ir(**PRESETS[spec]), 48000, subtype="PCM_24")
        return p
    if os.path.exists(spec):
        return spec
    raise FileNotFoundError(
        f"IR introuvable : '{spec}' (presets : {list(PRESETS)}, ou un chemin WAV)")
