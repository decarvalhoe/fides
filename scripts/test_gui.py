"""Test headless de la logique GUI (process_files), sans tkinter/affichage."""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import gui  # noqa: E402  (import sûr en headless : tkinter chargé dans main() seulement)

sr = 48000
t = np.arange(2 * sr) / sr
sf.write("/tmp/gui_in.wav", (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr, subtype="PCM_24")

msgs = []
reps = gui.process_files(
    ["/tmp/gui_in.wav"], "/tmp/gui_out",
    {"profile": "violin_solo", "reverb_mode": "hall", "full": True, "deharsh": True},
    msgs.append)

assert os.path.exists("/tmp/gui_out/gui_in/master.wav")
assert os.path.exists("/tmp/gui_out/gui_in/full_processed.wav")
print("\n".join(msgs))
print("GUI_LOGIC_OK")
