"""Smoke test v5 : chemins --reference (matchering/fallback) et --debleed (Demucs)."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import pipeline  # noqa: E402

sr = 48000
t = np.arange(int(2 * sr)) / sr
tone = (0.2 * np.sin(2 * np.pi * 440 * t) * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5)).astype(np.float32)
ref = (0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 1500 * t)).astype(np.float32)
os.makedirs("/tmp/s5", exist_ok=True)
sf.write("/tmp/s5/target.wav", tone, sr, subtype="PCM_24")
sf.write("/tmp/s5/ref.wav", ref, sr, subtype="PCM_24")

# --- reference (matchering ou fallback transparent) ---
r = pipeline.run("/tmp/s5/target.wav", "/tmp/s5/ref_out", "violin_solo", reference="/tmp/s5/ref.wav")
assert os.path.exists("/tmp/s5/ref_out/master.wav")
print("REFERENCE used_match =", r["summary"]["used_reference_match"],
      "| after =", r["summary"]["loudness_after"]["lufs"], "LUFS")
print("REF_OK")

# --- debleed (Demucs, télécharge le modèle au 1er run) ---
try:
    r2 = pipeline.run("/tmp/s5/target.wav", "/tmp/s5/db_out", "violin_solo", debleed=True)
    assert os.path.exists("/tmp/s5/db_out/master.wav")
    print("DEBLEED ok | mode =", r2["summary"]["mode"])
    print("DEBLEED_OK")
except Exception as e:
    print("DEBLEED_FAIL:", repr(e))
