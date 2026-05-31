"""GUI Fides (tkinter) : glisser‑déposer / sélection de fichiers + traitement.

Lancement : `fides-gui` (après `pip install -e .`) ou `python -m fides.gui`.
Le glisser‑déposer est activé si `tkinterdnd2` est installé (extra `gui`) ; sinon
le bouton « Parcourir… » suffit. tkinter requis (Linux : `apt install python3-tk`).

`build_ui(root)` construit l'interface sans lancer la boucle d'événements
(testable / capturable) ; `main()` ajoute la boucle. `process_files()` (la logique
de traitement) n'a aucune dépendance tkinter → testable en headless.
"""
from __future__ import annotations

import os
import queue
import threading

from . import pipeline, reference

REVERBS = ["aucune", "algorithmique", "hall", "room", "chamber"]


def _profiles():
    try:
        return reference.list_profiles() or ["violin_solo", "string_quartet"]
    except Exception:
        return ["violin_solo", "string_quartet"]


def process_files(files, outdir, opts, log):
    """Traite une liste de fichiers. `log(str)` reçoit les messages. Retourne les rapports."""
    reps = []
    rev = opts.get("reverb_mode", "aucune")
    reverb_amt = 0.2 if rev == "algorithmique" else None
    ir = rev if rev in ("hall", "room", "chamber") else None
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        od = os.path.join(outdir, name)
        log(f"▶ {name} …")
        try:
            rep = pipeline.run(
                f, od, opts.get("profile", "violin_solo"),
                make_stems=opts.get("stems", True),
                denoise=opts.get("denoise", False),
                deharsh_dyn=opts.get("deharsh", False),
                reverb=reverb_amt, ir=ir,
                full=opts.get("full", False),
                target_lufs=opts.get("target_lufs"))
            s = rep["summary"]
            la = s["loudness_after"]
            log(f"  ✓ {la['lufs']} LUFS / {la['true_peak_dbtp']} dBTP · "
                f"null {s['null_residual_rel_db']} dB · → {od}")
            reps.append(rep)
        except Exception as e:
            log(f"  ✗ {name} : {e}")
    log("— Terminé —")
    return reps


def build_ui(root, has_dnd=False):
    """Construit l'UI sur `root` et renvoie un dict d'état. Ne lance pas mainloop."""
    import tkinter as tk
    from tkinter import filedialog, scrolledtext, ttk

    st = {"files": [], "log_q": queue.Queue()}
    root.title("Fides — auto‑mastering cordes")
    root.geometry("720x580")

    top = ttk.LabelFrame(root, text="Fichiers" + ("  (glisser‑déposer activé)" if has_dnd else ""))
    top.pack(fill="x", padx=10, pady=6)
    lb = tk.Listbox(top, height=6)
    lb.pack(side="left", fill="both", expand=True, padx=6, pady=6)
    st["lb"] = lb

    def add_files(paths):
        for p in paths:
            p = p.strip().strip("{}")
            if p and p not in st["files"] and os.path.isfile(p):
                st["files"].append(p)
                lb.insert("end", p)
    st["add_files"] = add_files

    def browse():
        add_files(filedialog.askopenfilenames(
            title="Choisir des enregistrements",
            filetypes=[("Audio", "*.wav *.flac *.aif *.aiff *.mp3 *.m4a *.ogg"), ("Tous", "*.*")]))

    btns = ttk.Frame(top)
    btns.pack(side="right", padx=6)
    ttk.Button(btns, text="Parcourir…", command=browse).pack(fill="x", pady=2)
    ttk.Button(btns, text="Vider", command=lambda: (st["files"].clear(), lb.delete(0, "end"))).pack(fill="x", pady=2)
    if has_dnd:
        try:
            from tkinterdnd2 import DND_FILES
            lb.drop_target_register(DND_FILES)
            lb.dnd_bind("<<Drop>>", lambda e: add_files(root.tk.splitlist(e.data)))
        except Exception:
            pass

    opt = ttk.LabelFrame(root, text="Options")
    opt.pack(fill="x", padx=10, pady=6)
    st["prof"] = tk.StringVar(value=_profiles()[0])
    st["rev"] = tk.StringVar(value="aucune")
    st["lufs"] = tk.StringVar(value="")
    st["full"] = tk.BooleanVar(value=False)
    st["denoise"] = tk.BooleanVar(value=False)
    st["deharsh"] = tk.BooleanVar(value=False)
    ttk.Label(opt, text="Profil").grid(row=0, column=0, sticky="w", padx=6, pady=4)
    ttk.Combobox(opt, textvariable=st["prof"], values=_profiles(), width=16, state="readonly").grid(row=0, column=1, padx=6)
    ttk.Label(opt, text="Réverbe").grid(row=0, column=2, sticky="w", padx=6)
    ttk.Combobox(opt, textvariable=st["rev"], values=REVERBS, width=14, state="readonly").grid(row=0, column=3, padx=6)
    ttk.Label(opt, text="Cible LUFS").grid(row=0, column=4, sticky="w", padx=6)
    ttk.Entry(opt, textvariable=st["lufs"], width=7).grid(row=0, column=5, padx=6)
    ttk.Checkbutton(opt, text="Format plein (multicanal 32f)", variable=st["full"]).grid(row=1, column=0, columnspan=2, sticky="w", padx=6)
    ttk.Checkbutton(opt, text="Débruitage doux", variable=st["denoise"]).grid(row=1, column=2, columnspan=2, sticky="w", padx=6)
    ttk.Checkbutton(opt, text="De‑harsh archet", variable=st["deharsh"]).grid(row=1, column=4, columnspan=2, sticky="w", padx=6)

    out = ttk.Frame(root)
    out.pack(fill="x", padx=10, pady=4)
    st["outdir"] = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "fides_out"))
    ttk.Label(out, text="Sortie").pack(side="left")
    ttk.Entry(out, textvariable=st["outdir"]).pack(side="left", fill="x", expand=True, padx=6)
    ttk.Button(out, text="…", width=3,
               command=lambda: st["outdir"].set(filedialog.askdirectory() or st["outdir"].get())).pack(side="left")

    log_w = scrolledtext.ScrolledText(root, height=14, font=("Consolas", 9))
    log_w.pack(fill="both", expand=True, padx=10, pady=6)
    st["log_w"] = log_w
    st["log"] = lambda msg: st["log_q"].put(msg)

    run_btn = ttk.Button(root, text="Traiter")
    run_btn.pack(pady=(0, 10))
    st["run_btn"] = run_btn

    def run():
        if not st["files"]:
            st["log"]("Aucun fichier.")
            return
        try:
            tgt = float(st["lufs"].get()) if st["lufs"].get().strip() else None
        except ValueError:
            st["log"]("Cible LUFS invalide.")
            return
        opts = {"profile": st["prof"].get(), "reverb_mode": st["rev"].get(), "target_lufs": tgt,
                "full": st["full"].get(), "denoise": st["denoise"].get(), "deharsh": st["deharsh"].get()}
        run_btn.config(state="disabled")

        def worker():
            try:
                process_files(list(st["files"]), st["outdir"].get(), opts, st["log"])
            finally:
                root.after(0, lambda: run_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    run_btn.config(command=run)
    return st


def main():  # pragma: no cover (UI)
    import tkinter as tk
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
        has_dnd = True
    except Exception:
        root = tk.Tk()
        has_dnd = False
    st = build_ui(root, has_dnd)

    def pump():
        q, w = st["log_q"], st["log_w"]
        while not q.empty():
            w.insert("end", q.get() + "\n")
            w.see("end")
        root.after(120, pump)

    pump()
    root.mainloop()


if __name__ == "__main__":
    main()
