"""Smoke test v3 : batch + normalisation album/anchor."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from dlz import batch  # noqa: E402

sr = 48000
t = np.arange(int(2 * sr)) / sr
base = ((0.2 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 880 * t))
        * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5))
os.makedirs("/tmp/album_in", exist_ok=True)
for nm, amp in [("01_loud", 0.9), ("02_mid", 0.45), ("03_soft", 0.18)]:
    sf.write(f"/tmp/album_in/{nm}.wav", (base * amp).astype(np.float32), sr, subtype="PCM_24")

s = batch.run_batch("/tmp/album_in", "/tmp/album_out", "violin_solo", album=True)
print("album_gain_db =", s["album_gain_db"], "| count =", s["count"])
for tr in s["tracks"]:
    print(f"  {tr['name']:10} -> {tr['master_lufs']} LUFS  tp {tr['true_peak_dbtp']} dBTP")
# vérifs : ordre de loudness préservé, tous sous le plafond true-peak
lufs = [tr["master_lufs"] for tr in s["tracks"]]
tps = [tr["true_peak_dbtp"] for tr in s["tracks"]]
assert lufs == sorted(lufs, reverse=True), "ordre de loudness album non préservé"
assert all(tp <= -0.9 for tp in tps), "true-peak dépassé"
print("BATCH_OK")
