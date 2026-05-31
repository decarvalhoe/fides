"""Test : presets d'IR + réverbe à convolution."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import pipeline, space  # noqa: E402

for p in space.PRESETS:
    print(f"preset {p:8} present={os.path.exists(space.preset_path(p))}")

sr = 48000
t = np.arange(2 * sr) / sr
sf.write("/tmp/ir_in.wav", (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr, subtype="PCM_24")

r = pipeline.run("/tmp/ir_in.wav", "/tmp/ir_out", "violin_solo", ir="hall")
assert os.path.exists("/tmp/ir_out/master.wav")
r0 = pipeline.run("/tmp/ir_in.wav", "/tmp/ir_out0", "violin_solo")
print("null AVEC reverb hall :", r["summary"]["null_residual_rel_db"], "dB")
print("null SANS reverb      :", r0["summary"]["null_residual_rel_db"], "dB")
print("IR_TEST_OK")
