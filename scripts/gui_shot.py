"""Capture une copie d'écran de la GUI Fides -> assets/gui.png (sous Xvfb)."""
import os
import sys
import time

sys.path.insert(0, "/mnt/c/Dev/dlz-mastering")
from fides import gui  # noqa: E402

try:
    from tkinterdnd2 import TkinterDnD
    root = TkinterDnD.Tk()
    dnd = True
except Exception:
    import tkinter as tk
    root = tk.Tk()
    dnd = False

st = gui.build_ui(root, dnd)
for f in ["/home/decarvalhoe/dlz/in/REC_0001.wav",
          "/home/decarvalhoe/Musique/quatuor_mvt1.flac",
          "/home/decarvalhoe/Musique/sonate_adagio.wav"]:
    st["lb"].insert("end", f)
    st["files"].append(f)
st["prof"].set("violin_solo")
st["rev"].set("hall")
st["deharsh"].set(True)
st["full"].set(True)
st["log_w"].insert("end",
    "▶ REC_0001 …\n"
    "  ✓ -21.4 LUFS / -1.0 dBTP · null -22.9 dB · → ~/fides_out/REC_0001\n"
    "▶ quatuor_mvt1 …\n"
    "  ✓ -18.2 LUFS / -1.0 dBTP · null -24.1 dB · → ~/fides_out/quatuor_mvt1\n"
    "▶ sonate_adagio …\n"
    "  ✓ -19.0 LUFS / -1.0 dBTP · null -23.5 dB · → ~/fides_out/sonate_adagio\n"
    "— Terminé —\n")
root.update_idletasks()
root.update()
time.sleep(0.5)
root.update()

out = "/mnt/c/Dev/dlz-mastering/assets/gui.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
rc = os.system(f"import -window root '{out}' 2>/dev/null")
if rc != 0 or not os.path.exists(out):
    os.system(f"xwd -root -silent | convert xwd:- '{out}'")
root.destroy()
print("exists:", os.path.exists(out))
print("GUI_SHOT_OK")
