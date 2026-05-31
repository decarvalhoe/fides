"""Génère les IR presets bundlées dans fides/ir/."""
import os
import sys

import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import space  # noqa: E402

os.makedirs(space.ir_dir(), exist_ok=True)
for name, cfg in space.PRESETS.items():
    ir = space.synth_ir(**cfg)
    p = space.preset_path(name)
    sf.write(p, ir, 48000, subtype="PCM_24")
    print(f"{name:8} {ir.shape[0]:>7} samples ({ir.shape[0] / 48000:.2f}s) -> {p}")
print("IR_GEN_DONE")
