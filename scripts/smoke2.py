"""Smoke test v2 : mono/stéréo/formats/reverb/de-harsh/dry-run."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import pipeline, io_wav  # noqa: E402

sr = 48000
t = np.arange(int(2 * sr)) / sr
tone = (0.2 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 880 * t))
tone = (tone * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5)).astype(np.float32)
D = "/tmp/s2"
os.makedirs(D, exist_ok=True)

# mono
sf.write(f"{D}/mono.wav", tone, sr, subtype="PCM_24")
r = pipeline.run(f"{D}/mono.wav", f"{D}/mono_out", "violin_solo")
print("MONO     mode=", r["summary"]["mode"], "after=", r["summary"]["loudness_after"]["lufs"])
assert r["summary"]["mode"] == "mono"

# stéréo -> master stéréo
st = np.stack([tone, np.roll(tone, 50)], axis=1)
sf.write(f"{D}/st.wav", st, sr, subtype="PCM_24")
r = pipeline.run(f"{D}/st.wav", f"{D}/st_out", "violin_solo")
md, _ = io_wav.read_wav(f"{D}/st_out/master.wav")
print("STEREO   mode=", r["summary"]["mode"], "master_ch=", md.shape[1])
assert r["summary"]["mode"] == "stereo" and md.shape[1] == 2

# FLAC (soundfile natif)
sf.write(f"{D}/a.flac", tone, sr)
r = pipeline.run(f"{D}/a.flac", f"{D}/flac_out", "violin_solo")
print("FLAC     ok mode=", r["summary"]["mode"])

# M4A (repli ffmpeg)
os.system(f"ffmpeg -y -loglevel error -i {D}/mono.wav {D}/a.m4a")
r = pipeline.run(f"{D}/a.m4a", f"{D}/m4a_out", "violin_solo")
print("M4A      ok (repli ffmpeg) mode=", r["summary"]["mode"])

# reverb + de-harsh dynamique
r = pipeline.run(f"{D}/mono.wav", f"{D}/rv_out", "violin_solo", reverb=0.25, deharsh_dyn=True)
print("REVERB   ok null=", r["summary"]["null_residual_rel_db"])

# dry-run
r = pipeline.run(f"{D}/mono.wav", f"{D}/dry_out", "violin_solo", dry_run=True)
print("DRYRUN   files=", sorted(os.listdir(f"{D}/dry_out")))
assert r["summary"].get("dry_run") is True

print("HTML     mono_out:", os.path.exists(f"{D}/mono_out/report.html"))
print("AB       stereo_out original_match:", os.path.exists(f"{D}/st_out/original_match.wav"))
print("SMOKE2_OK")
