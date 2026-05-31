"""Génère assets/spectrum.png : spectres + différence (REC_0001, original vs master)."""
import os
import sys

import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import io_util  # noqa: E402

IN = os.path.expanduser("~/dlz/in/REC_0001.wav")
MASTER = os.path.expanduser("~/dlz/out/REC_0001/master.wav")

data, wi = io_util.load_audio(IN)
sr = wi.samplerate
orig = data[:, 12]
master, _ = io_util.load_audio(MASTER)
mas = master[:, 0] if master.ndim > 1 else master


def psd_db(x):
    f, P = signal.welch(x.astype(np.float64), fs=sr, nperseg=8192)
    return f, 10 * np.log10(P + 1e-12)


def at(f, P, hz):
    return P[np.argmin(np.abs(f - hz))]


def smooth_oct(f, y, frac=1 / 6):
    out = np.copy(y)
    for i in range(len(f)):
        m = (f >= f[i] * 2 ** (-frac / 2)) & (f <= f[i] * 2 ** (frac / 2))
        if m.any():
            out[i] = np.mean(y[m])
    return out


fo, Po = psd_db(orig)
fm, Pm = psd_db(mas)
Po -= at(fo, Po, 1000)
Pm -= at(fm, Pm, 1000)
diff = smooth_oct(fo, Pm - Po)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6.6), sharex=True)
ax1.semilogx(fo, Po, color="#9aa0a6", lw=1.2, label="Original (ch12)")
ax1.semilogx(fm, Pm, color="#127a2b", lw=1.1, alpha=0.85, label="Master Fides")
ax1.set_ylim(-55, 14)
ax1.set_ylabel("dB (aligné @1 kHz)")
ax1.set_title("Spectres quasi superposés → traitement transparent")
ax1.legend(loc="lower left")
ax1.grid(True, which="both", alpha=0.2)

ax2.axhline(0, color="#bbb", lw=1)
ax2.axhspan(-3, 3, color="#127a2b", alpha=0.06)
ax2.semilogx(fo, diff, color="#127a2b", lw=2)
ax2.set_ylim(-6, 6)
ax2.set_xlim(20, 20000)
ax2.set_ylabel("Δ master − orig (dB)")
ax2.set_xlabel("Fréquence (Hz)")
ax2.set_title("Ce que Fides a changé : EQ doux plafonné (passe-haut · bas-medium − · air +)")
ax2.grid(True, which="both", alpha=0.2)

fig.suptitle("Fides — REC_0001 : transparent, dynamique préservée", fontweight="bold")
fig.tight_layout()
os.makedirs("/mnt/c/Dev/dlz-mastering/assets", exist_ok=True)
out = "/mnt/c/Dev/dlz-mastering/assets/spectrum.png"
fig.savefig(out, dpi=120)
print("saved", out)
print("SPECTRUM_OK")
