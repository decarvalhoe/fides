"""Visualisation (optionnelle, best-effort) : preuve de transparence par run.

Figure à 2 panneaux : (haut) spectres original vs master superposés ; (bas) courbe
de différence lissée = ce que Fides a réellement changé (EQ doux plafonné).
Nécessite matplotlib ; renvoie None si indisponible ou signal trop court.
"""
from __future__ import annotations

import os

import numpy as np
from scipy import signal

EPS = 1e-12


def _psd_db(x, sr, nperseg=8192):
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    nper = int(min(nperseg, len(x)))
    f, P = signal.welch(x, fs=sr, nperseg=max(256, nper))
    return f, 10.0 * np.log10(P + EPS)


def _smooth_oct(f, y, frac=1 / 6):
    out = np.copy(y)
    for i in range(len(f)):
        m = (f >= f[i] * 2 ** (-frac / 2)) & (f <= f[i] * 2 ** (frac / 2))
        if m.any():
            out[i] = np.mean(y[m])
    return out


def spectrum_figure(orig, master, sr, out_path, title="Fides"):
    """Écrit une figure spectre/diff en PNG. Retourne le chemin ou None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    o = np.asarray(orig, dtype=np.float64).reshape(-1)
    m = np.asarray(master, dtype=np.float64).reshape(-1)
    if len(o) < sr // 4 or len(m) < sr // 4:
        return None
    try:
        fo, Po = _psd_db(o, sr)
        fm, Pm = _psd_db(m, sr)

        def at(f, P, hz):
            return P[np.argmin(np.abs(f - hz))]

        Po -= at(fo, Po, 1000)
        Pm -= at(fm, Pm, 1000)
        n = min(len(fo), len(fm))
        diff = _smooth_oct(fo[:n], Pm[:n] - Po[:n])

        fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True)
        a1.semilogx(fo, Po, color="#9aa0a6", lw=1.1, label="Original")
        a1.semilogx(fm, Pm, color="#127a2b", lw=1.1, alpha=0.85, label="Master Fides")
        a1.set_ylim(-55, 14)
        a1.set_ylabel("dB (@1 kHz)")
        a1.legend(loc="lower left")
        a1.grid(True, which="both", alpha=0.2)
        a1.set_title("Spectres superposés → transparent")
        a2.axhline(0, color="#bbb", lw=1)
        a2.axhspan(-3, 3, color="#127a2b", alpha=0.06)
        a2.semilogx(fo[:n], diff, color="#127a2b", lw=2)
        a2.set_ylim(-6, 6)
        a2.set_xlim(20, 20000)
        a2.set_ylabel("Δ master − orig (dB)")
        a2.set_xlabel("Fréquence (Hz)")
        a2.set_title("Ce que Fides a changé (EQ doux plafonné)")
        a2.grid(True, which="both", alpha=0.2)
        fig.suptitle(title, fontweight="bold")
        fig.tight_layout()
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fig.savefig(out_path, dpi=110)
        plt.close(fig)
        return out_path
    except Exception:
        return None
