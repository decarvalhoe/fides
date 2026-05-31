"""Smoke test v4 : blend multi-micros (multipiste) + import de-bleed."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from dlz import pipeline, io_wav  # noqa: E402

sr = 48000
t = np.arange(int(2 * sr)) / sr
close = (0.30 * np.sin(2 * np.pi * 440 * t) * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5)).astype(np.float32)
room = (0.10 * np.sin(2 * np.pi * 440 * (t - 0.01))).astype(np.float32)
sil = np.zeros_like(t, dtype=np.float32)
os.makedirs("/tmp/mt", exist_ok=True)
sf.write("/tmp/mt/mt.wav", np.stack([close, room, sil], axis=1), sr, subtype="PCM_24")

r0 = pipeline.run("/tmp/mt/mt.wav", "/tmp/mt/out0", "violin_solo")
r1 = pipeline.run("/tmp/mt/mt.wav", "/tmp/mt/out1", "violin_solo", blend=[(1, -6.0)])
m0, _ = io_wav.read_wav("/tmp/mt/out0/master.wav")
m1, _ = io_wav.read_wav("/tmp/mt/out1/master.wav")
n = min(len(m0), len(m1))
diff = float(np.mean(np.abs(m0[:n, 0] - m1[:n, 0])))
print("mode=", r0["summary"]["mode"], "primary=", r0["summary"]["primary_channel"],
      "blend_diff=", round(diff, 6))
assert r0["summary"]["mode"] == "multitrack"
assert diff > 1e-5, "le blend n'a eu aucun effet"

from dlz import debleed  # noqa: E402
assert hasattr(debleed, "isolate")
print("debleed import OK")
print("BLEND_OK")
