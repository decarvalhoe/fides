"""Vérification : mesures loudness/true-peak (pyloudnorm) + null-test.

Le null-test quantifie « ce qu'on a changé » : on aligne le traité sur
l'original par un gain scalaire optimal, puis on mesure le résidu. Un résidu
relatif très bas = traitement transparent (ne dénature pas).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import resample_poly

EPS = 1e-12


def _db(x: float) -> float:
    x = float(x)
    return -np.inf if x <= 0 else 20.0 * np.log10(x)


def true_peak_dbtp(x: np.ndarray, sr: int, oversample: int = 4) -> float:
    """True-peak (dBTP) sur 1-D ou [n, ch] (max sur les canaux)."""
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 1:
        a = a[:, None]
    peak = 0.0
    for c in range(a.shape[1]):
        xo = resample_poly(a[:, c], oversample, 1)
        peak = max(peak, float(np.max(np.abs(xo))))
    return round(_db(peak + EPS), 2)


def measure(x: np.ndarray, sr: int) -> dict:
    import pyloudnorm as pyln
    a = np.asarray(x, dtype=np.float64)
    meas = a if a.ndim > 1 else a.reshape(-1)
    lufs = None
    try:
        val = float(pyln.Meter(sr).integrated_loudness(meas))
        if val == val and val != -np.inf:
            lufs = round(val, 2)
    except Exception:
        pass
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    return {
        "lufs": lufs,
        "peak_dbfs": round(_db(peak + EPS), 2),
        "true_peak_dbtp": true_peak_dbtp(a, sr),
    }


def null_test(orig: np.ndarray, proc: np.ndarray) -> dict:
    n = min(len(orig), len(proc))
    o = np.asarray(orig[:n], dtype=np.float64).reshape(-1)
    p = np.asarray(proc[:n], dtype=np.float64).reshape(-1)
    g = float(np.dot(o, p) / (np.dot(p, p) + EPS))   # gain optimal pour annuler
    resid = o - g * p
    rms_o = float(np.sqrt(np.mean(o ** 2) + EPS))
    rms_r = float(np.sqrt(np.mean(resid ** 2) + EPS))
    return {
        "gain_match": round(g, 4),
        "residual_dbfs": round(_db(rms_r), 2),
        "residual_rel_db": round(20.0 * np.log10(rms_r / rms_o), 2),
        "interpretation": _null_interp(20.0 * np.log10(rms_r / rms_o)),
        "residual": resid.astype(np.float32),
    }


def _null_interp(rel_db: float) -> str:
    if rel_db <= -30:
        return "très transparent (changement minime)"
    if rel_db <= -18:
        return "transparent (correction légère)"
    if rel_db <= -9:
        return "correction notable mais maîtrisée"
    return "changement important — à vérifier à l'écoute"
