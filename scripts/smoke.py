"""Smoke test : exerce tout le pipeline sur un signal synthétique court."""
import os
import sys
import json

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import pipeline, reference  # noqa: E402

np.random.seed(0)
sr = 48000
t = np.arange(int(3 * sr)) / sr
tone = (0.20 * np.sin(2 * np.pi * 440 * t)
        + 0.10 * np.sin(2 * np.pi * 880 * t)
        + 0.05 * np.sin(2 * np.pi * 1760 * t))
env = (np.sin(2 * np.pi * 0.5 * t) * 0.5 + 0.5) ** 2   # respirations -> vrai plancher
tone = tone * env
hum = 0.01 * np.sin(2 * np.pi * 50 * t)
noise = 0.0015 * np.random.randn(len(t))
ch_main = (tone + hum + noise).astype(np.float32)
ch_room = (0.06 * tone + 0.008 * np.random.randn(len(t))).astype(np.float32)
ch_clip = np.clip(ch_main * 3.0, -1.0, 1.0).astype(np.float32)
ch_sil = np.zeros_like(t, dtype=np.float32)
data = np.stack([ch_main, ch_room, ch_clip, ch_sil], axis=1)

os.makedirs("/tmp/dlz_smoke", exist_ok=True)
inp = "/tmp/dlz_smoke/in.wav"
sf.write(inp, data, sr, subtype="PCM_24")

print("profils:", reference.list_profiles())
rep = pipeline.run(inp, "/tmp/dlz_smoke/out", "violin_solo")
print(json.dumps(rep["summary"], indent=2, ensure_ascii=False))
print("FILES:", sorted(os.listdir("/tmp/dlz_smoke/out")))
print("STEMS:", sorted(os.listdir("/tmp/dlz_smoke/out/stems")))
print("SMOKE_OK")
