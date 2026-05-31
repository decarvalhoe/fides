"""Analyse par canal — le 'cerveau' du pipeline.

Mesure par canal : peak/RMS/crest/DC, plancher de bruit, dynamique, clipping,
centroïde spectral, profil tonal par bandes, ronflette secteur. Classe les
canaux (actif / silence / duplicata) et détecte les corrélations inter-canaux.

Dépend uniquement de numpy + scipy (testable sans le reste de la pile).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np
from scipy import signal

EPS = 1e-12

# Bandes tonales (Hz) pertinentes pour le violon / les cordes.
BANDS = [
    ("sub", 0, 40),
    ("low", 40, 160),
    ("low_mid", 160, 500),
    ("mid", 500, 2000),
    ("high_mid", 2000, 6000),
    ("high", 6000, 12000),
    ("air", 12000, 20000),
]
MAINS_HZ = (50.0, 100.0, 150.0)  # réseau électrique européen (50 Hz) + harmoniques


def _db(x) -> float:
    return 20.0 * np.log10(float(max(x, EPS)))


def _pdb(x) -> float:
    return 10.0 * np.log10(float(max(x, EPS)))


def _trap(y, x):
    fn = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    return float(fn(y, x))


@dataclass
class ChannelAnalysis:
    index: int
    role: str = "active"                 # active | silent | duplicate
    duplicate_of: Optional[int] = None
    peak_dbfs: float = -np.inf
    rms_dbfs: float = -np.inf
    crest_db: float = 0.0
    dc_offset: float = 0.0
    noise_floor_dbfs: float = -np.inf    # p05 du RMS court terme
    loud_dbfs: float = -np.inf           # p95 du RMS court terme
    dynamic_range_db: float = 0.0
    snr_db: float = 0.0                  # loud - noise_floor
    clipped_samples: int = 0
    clipped_runs: int = 0                # séries de pleine échelle (>= 3 éch.) -> écrêtage franc
    clip_pct: float = 0.0
    centroid_hz: float = 0.0
    bands_pct: dict = field(default_factory=dict)
    hum_db: dict = field(default_factory=dict)  # dB au-dessus du voisinage à 50/100/150 Hz
    quality_score: float = 0.0

    def as_dict(self):
        return asdict(self)


@dataclass
class Analysis:
    samplerate: int
    channels_count: int
    frames: int
    duration_s: float
    truncated: bool
    channels: list = field(default_factory=list)
    active_indices: list = field(default_factory=list)
    unique_active_indices: list = field(default_factory=list)
    correlations: list = field(default_factory=list)  # (i, j, r) pour |r| > seuil
    primary_index: Optional[int] = None               # meilleur canal "porteur"

    def to_dict(self):
        return {
            "samplerate": self.samplerate,
            "channels_count": self.channels_count,
            "frames": self.frames,
            "duration_s": round(self.duration_s, 3),
            "truncated": self.truncated,
            "active_indices": self.active_indices,
            "unique_active_indices": self.unique_active_indices,
            "primary_index": self.primary_index,
            "correlations": [(int(i), int(j), round(float(r), 4)) for i, j, r in self.correlations],
            "channels": [c.as_dict() for c in self.channels],
        }


def _short_term_rms(x: np.ndarray, sr: int, win_s: float = 0.05) -> np.ndarray:
    win = max(1, int(win_s * sr))
    if len(x) < 2 * win:
        return np.array([np.sqrt(np.mean(x.astype(np.float64) ** 2) + EPS)])
    hop = win
    nf = (len(x) - win) // hop
    xc = np.ascontiguousarray(x, dtype=np.float64)
    frames = np.lib.stride_tricks.as_strided(
        xc, shape=(nf, win), strides=(xc.strides[0] * hop, xc.strides[0])
    )
    return np.sqrt(np.mean(frames ** 2, axis=1) + EPS)


def _detect_clipping(x: np.ndarray, thr: float = 0.999, min_run: int = 3):
    mask = np.abs(x) >= thr
    clipped = int(mask.sum())
    runs = 0
    if clipped:
        # compte les séries consécutives de longueur >= min_run
        idx = np.flatnonzero(mask)
        if idx.size:
            splits = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
            runs = sum(1 for s in splits if s.size >= min_run)
    return clipped, runs


def _psd(x: np.ndarray, sr: int):
    nper = int(min(sr, len(x)))
    nper = max(256, nper)
    f, P = signal.welch(x.astype(np.float64), fs=sr, nperseg=nper,
                        noverlap=nper // 2, window="hann")
    return f, P


def _bands_pct(f, P):
    tot = _trap(P, f)
    out = {}
    nyq = f[-1]
    for name, lo, hi in BANDS:
        hi = min(hi, nyq)
        if hi <= lo:
            out[name] = 0.0
            continue
        m = (f >= lo) & (f < hi)
        e = _trap(P[m], f[m]) if m.any() else 0.0
        out[name] = round(100.0 * e / tot, 2) if tot > 0 else 0.0
    return out


def _hum(f, P):
    out = {}
    for hz in MAINS_HZ:
        if hz >= f[-1]:
            continue
        idx = int(np.argmin(np.abs(f - hz)))
        neigh = (f >= hz - 25) & (f <= hz + 25) & (np.abs(f - hz) > 6)
        peak = _pdb(P[idx])
        base = _pdb(np.median(P[neigh])) if neigh.any() else peak
        out[str(int(hz))] = round(peak - base, 2)
    return out


def analyze(data: np.ndarray, samplerate: int,
            silence_dbfs: float = -60.0, dup_corr: float = 0.9995,
            corr_report: float = 0.4, truncated: bool = False) -> Analysis:
    """Analyse complète d'un buffer [n, ch] (float [-1, 1])."""
    if data.ndim == 1:
        data = data[:, None]
    n, ch = data.shape
    sr = samplerate
    res = Analysis(sr, ch, n, n / sr if sr else 0.0, truncated)

    peak = np.max(np.abs(data), axis=0) if n else np.zeros(ch)
    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2, axis=0) + EPS) if n else np.zeros(ch)
    dc = np.mean(data, axis=0) if n else np.zeros(ch)

    active = []
    for c in range(ch):
        ca = ChannelAnalysis(index=c)
        ca.peak_dbfs = round(_db(peak[c]), 2)
        ca.rms_dbfs = round(_db(rms[c]), 2)
        ca.crest_db = round(ca.peak_dbfs - ca.rms_dbfs, 2)
        ca.dc_offset = round(float(dc[c]), 6)

        col = np.ascontiguousarray(data[:, c])
        st = _short_term_rms(col, sr)
        st_db = 20.0 * np.log10(st)
        ca.noise_floor_dbfs = round(float(np.percentile(st_db, 5)), 2)
        ca.loud_dbfs = round(float(np.percentile(st_db, 95)), 2)
        ca.dynamic_range_db = round(ca.loud_dbfs - ca.noise_floor_dbfs, 2)
        ca.snr_db = round(ca.loud_dbfs - ca.noise_floor_dbfs, 2)

        clipped, runs = _detect_clipping(col)
        ca.clipped_samples = clipped
        ca.clipped_runs = runs
        ca.clip_pct = round(100.0 * clipped / n, 4) if n else 0.0

        if ca.peak_dbfs < silence_dbfs:
            ca.role = "silent"
        else:
            ca.role = "active"
            active.append(c)
            f, P = _psd(col, sr)
            ca.centroid_hz = round(float(np.sum(f * P) / (np.sum(P) + EPS)), 1)
            ca.bands_pct = _bands_pct(f, P)
            ca.hum_db = _hum(f, P)

        res.channels.append(ca)

    res.active_indices = active

    # --- corrélations & duplicatas (sur signal décimé) ---
    if len(active) >= 2 and n > 0:
        dec = max(1, n // 200_000)
        d = data[::dec][:, active].astype(np.float64)
        # garde-fou : retire la moyenne pour corrélation
        C = np.corrcoef(d.T)
        for ii in range(len(active)):
            for jj in range(ii + 1, len(active)):
                r = float(C[ii, jj])
                if abs(r) > corr_report:
                    res.correlations.append((active[ii], active[jj], r))
        # duplicatas : j ~ i (corr > dup_corr) et niveaux proches -> j duplicate_of i
        for jj in range(len(active)):
            for ii in range(jj):
                r = float(C[ii, jj])
                ci, cj = res.channels[active[ii]], res.channels[active[jj]]
                if r > dup_corr and abs(ci.rms_dbfs - cj.rms_dbfs) < 0.5:
                    if res.channels[active[jj]].role != "duplicate":
                        res.channels[active[jj]].role = "duplicate"
                        res.channels[active[jj]].duplicate_of = active[ii]
                    break

    res.unique_active_indices = [c for c in active if res.channels[c].role == "active"]

    # --- score qualité & canal primaire ---
    for c in res.unique_active_indices:
        ca = res.channels[c]
        score = ca.snr_db                      # privilégie le rapport signal/bruit
        score -= 6.0 * ca.clipped_runs         # pénalise fortement l'écrêtage franc
        if ca.peak_dbfs > -0.1:                # pénalise le 0 dBFS (risque de clip)
            score -= 10.0
        # pénalise un niveau anormalement bas (capte mal) ou un DC marqué
        if ca.rms_dbfs < -45:
            score -= 5.0
        score -= 100.0 * abs(ca.dc_offset)
        ca.quality_score = round(float(score), 2)
    if res.unique_active_indices:
        res.primary_index = max(res.unique_active_indices,
                                key=lambda c: res.channels[c].quality_score)
    return res
