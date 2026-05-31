"""Traitement par lot + normalisation album/anchor (EBU R128 s2).

Un gain COMMUN est calculé sur tout le lot (ancre = piste la plus forte), puis
appliqué à chaque piste — ce qui préserve les rapports de loudness entre prises/
mouvements, tout en gardant chaque master sous le plafond true-peak.
"""
from __future__ import annotations

import json
import logging
import os

from . import pipeline as PL
from . import reference as REF
from . import verify as V

logger = logging.getLogger("dlz")

AUDIO_EXT = (".wav", ".flac", ".aif", ".aiff", ".mp3", ".m4a", ".ogg", ".opus")


def find_audio(input_dir: str):
    return sorted(os.path.join(input_dir, f) for f in os.listdir(input_dir)
                  if f.lower().endswith(AUDIO_EXT))


def run_batch(input_dir, outdir, profile_name="violin_solo", *, album=True,
              target_lufs=None, make_stems=True, denoise=False, reverb=None, ir=None,
              glue=False, deharsh_dyn=False, blend=None, full=False, bit_depth=None):
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"dossier introuvable : {input_dir}")
    profile = REF.load_profile(profile_name)
    files = find_audio(input_dir)
    if not files:
        raise RuntimeError(f"aucun fichier audio dans {input_dir}")
    loud = profile.get("loudness", {})
    tgt = float(target_lufs) if target_lufs is not None else loud.get("target_lufs", -16.0)
    tp = loud.get("true_peak_dbtp", -1.0)
    subtype = PL.resolve_subtype(bit_depth, full)
    os.makedirs(outdir, exist_ok=True)

    # Phase A : pre-master + mesures par piste
    ctxs = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        try:
            ctx = PL.process_to_pre(f, profile, denoise=denoise, reverb=reverb, ir=ir,
                                    glue=glue, deharsh_dyn=deharsh_dyn, blend=blend)
        except Exception as e:
            logger.warning("ignoré '%s' : %s", name, e)
            continue
        m = V.measure(ctx["pre"], ctx["sr"])
        ctx["name"] = name
        ctx["pre_lufs"] = m["lufs"]
        ctx["pre_tp"] = m["true_peak_dbtp"]
        ctxs.append(ctx)
    if not ctxs:
        raise RuntimeError("aucune piste exploitable dans le lot")

    # Phase B : gain album/anchor commun (ancre = piste la plus forte)
    album_gain = None
    if album:
        lufs_vals = [c["pre_lufs"] for c in ctxs if c["pre_lufs"] is not None]
        anchor = max(lufs_vals) if lufs_vals else tgt
        gain_need = tgt - anchor
        min_room = min(tp - c["pre_tp"] for c in ctxs)
        album_gain = min(gain_need, min_room)
        logger.info("album: ancre=%.2f LUFS, gain commun=%.2f dB", anchor, album_gain)

    # Phase C : finalize chaque piste
    tracks = []
    for ctx in ctxs:
        od = os.path.join(outdir, ctx["name"])
        rep = PL.finalize(ctx, od, tgt, tp, album_gain=album_gain, make_stems=make_stems,
                          subtype=subtype, full=full)
        tracks.append({"name": ctx["name"], "outdir": od,
                       "master_lufs": rep["summary"]["loudness_after"]["lufs"],
                       "true_peak_dbtp": rep["summary"]["loudness_after"]["true_peak_dbtp"],
                       "null_rel_db": rep["summary"]["null_residual_rel_db"]})

    summary = {"input_dir": input_dir, "outdir": outdir, "profile": profile_name,
               "album_normalization": album,
               "album_gain_db": (round(album_gain, 2) if album_gain is not None else None),
               "target_lufs": tgt, "count": len(tracks), "tracks": tracks}
    with open(os.path.join(outdir, "album_report.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    return summary
