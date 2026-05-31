"""Orchestrateur : Ingest/Repair -> Analyze -> Plan -> Process -> Verify -> Output.

Découpé en deux étages réutilisables :
- process_to_pre() : jusqu'au "pre-master" nettoyé (sans loudness) ;
- finalize() : loudness (ou gain album imposé) + verify + rapports + sorties.
Le mode "full" réassemble TOUS les canaux traités en un seul fichier multicanal
pleine résolution (32-bit float par défaut), SR d'origine préservé.
"""
from __future__ import annotations

import logging
import os

import numpy as np

from . import io_util, io_wav
from . import space
from . import analyze as A
from . import plan as P
from . import process as PROC
from . import reference as REF
from . import verify as V
from . import report as R

logger = logging.getLogger("dlz")

# profondeur de sortie -> sous-type libsndfile
_SUBTYPE = {"24": "PCM_24", "32": "PCM_32", "32f": "FLOAT",
            "float": "FLOAT", "float32": "FLOAT"}


def resolve_subtype(bit_depth, full):
    return _SUBTYPE.get(bit_depth or ("32f" if full else "24"), "PCM_24")


def _assemble_full(data, cleaned, analysis):
    """Réassemble la session complète : canaux traités là où on en a, sinon
    passthrough (canaux silencieux), duplicatas alignés sur leur source traitée."""
    n, nch = data.shape
    out = np.array(data, dtype=np.float32, copy=True)
    for c in range(nch):
        ca = analysis.channels[c]
        if c in cleaned:
            out[:, c] = cleaned[c][:n]
        elif ca.duplicate_of is not None and ca.duplicate_of in cleaned:
            out[:, c] = cleaned[ca.duplicate_of][:n]
    return out


def _normalize(pre, master_path, sr, tgt, tp, limit, ebu, pre_path, subtype="PCM_24"):
    if ebu:
        PROC.loudness_normalize_file(pre_path, master_path, tgt, tp, sr)
        return None
    master, m = PROC.loudness_normalize_array(pre, sr, tgt, tp, limit=limit)
    io_wav.write_wav(master_path, master, sr, subtype)
    return m


def _inject_options(plan, profile, glue, deharsh_dyn):
    for c in plan["process_channels"]:
        pc = plan["channels"][str(c)]
        if deharsh_dyn:
            pc["deharsh_dyn"] = {"freq": profile.get("deharsh", {}).get("freq_hz", 3200),
                                 "q": 1.2, "max_cut_db": 3.0, "thr_db": -28.0}
            pc["steps"].append("de-harsh dynamique (archet)")
        if glue:
            pc["glue"] = {"threshold_db": -18.0, "ratio": 1.5,
                          "attack_ms": 30.0, "release_ms": 250.0}
            pc["steps"].append("glue (compresseur doux)")


def _ingest_analyze(input_path, profile, denoise, primary, glue, deharsh_dyn):
    data, wi = io_util.load_audio(input_path)
    sr = wi.samplerate
    if not np.isfinite(data).all():
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        logger.warning("valeurs non finies nettoyées : %s", os.path.basename(input_path))
    if wi.frames_read < int(0.1 * sr):
        raise RuntimeError(f"fichier trop court ({wi.duration:.2f}s) — au moins 0,1 s requis")
    analysis = A.analyze(data, sr, truncated=wi.truncated)
    if analysis.primary_index is None:
        raise RuntimeError("aucun canal actif détecté — rien à traiter")
    if primary is not None:
        if primary not in analysis.unique_active_indices:
            raise RuntimeError(
                f"canal primaire {primary} indisponible (actifs uniques : {analysis.unique_active_indices})")
        analysis.primary_index = primary
    plan = P.make_plan(analysis, profile, allow_denoise=denoise)
    _inject_options(plan, profile, glue, deharsh_dyn)
    return data, wi, sr, analysis, plan


def process_to_pre(input_path, profile, *, denoise=False, primary=None,
                   reverb=None, ir=None, glue=False, deharsh_dyn=False, blend=None):
    data, wi, sr, analysis, plan = _ingest_analyze(
        input_path, profile, denoise, primary, glue, deharsh_dyn)
    cleaned = {}
    for c in plan["process_channels"]:
        y, _ = PROC.process_channel(data[:, c], sr, plan["channels"][str(c)])
        cleaned[c] = y
    uacols = plan["process_channels"]
    if data.shape[1] <= 2:
        mode = "mono" if len(uacols) == 1 else "stereo"
        cols = [cleaned[c] for c in uacols]
        pre = cols[0] if len(cols) == 1 else np.stack(cols, axis=1)
        orig_ref = data[:, uacols[0]] if len(uacols) == 1 else data[:, uacols].mean(axis=1)
    else:
        mode = "multitrack"
        pre = np.asarray(cleaned[analysis.primary_index], dtype=np.float64).copy()
        for ch, g in (blend or []):
            if ch in cleaned:
                pre = pre + np.asarray(cleaned[ch], dtype=np.float64) * (10.0 ** (g / 20.0))
        pre = pre.astype(np.float32)
        orig_ref = data[:, analysis.primary_index]
    if reverb is not None or ir:
        ir_path = space.resolve_ir(ir) if ir else None
        pre = PROC.apply_reverb(pre, sr, amount=(reverb if reverb is not None else 0.2), ir_path=ir_path)
    return {"pre": pre, "orig_ref": orig_ref, "analysis": analysis, "plan": plan,
            "wi": wi, "sr": sr, "mode": mode, "cleaned": cleaned, "profile": profile,
            "data": data}


def finalize(ctx, outdir, target_lufs, tp_ceiling, *, album_gain=None,
             make_stems=True, reference=None, limit=False, ebu=False,
             subtype="PCM_24", full=False):
    os.makedirs(outdir, exist_ok=True)
    sr, pre = ctx["sr"], ctx["pre"]
    analysis, plan, wi, orig_ref = ctx["analysis"], ctx["plan"], ctx["wi"], ctx["orig_ref"]

    stem_paths = {}
    if make_stems:
        stems_dir = os.path.join(outdir, "stems")
        os.makedirs(stems_dir, exist_ok=True)
        for c, y in ctx["cleaned"].items():
            sp = os.path.join(stems_dir, f"ch{c:02d}_clean.wav")
            io_wav.write_wav(sp, y, sr, subtype)
            stem_paths[str(c)] = sp

    pre_path = os.path.join(outdir, "_pre_master.wav")
    io_wav.write_wav(pre_path, pre, sr, subtype)

    master_path = os.path.join(outdir, "master.wav")
    used_reference = False
    lmeta = None
    if album_gain is not None:
        master = (np.asarray(pre, dtype=np.float64) * (10.0 ** (album_gain / 20.0))).astype(np.float32)
        io_wav.write_wav(master_path, master, sr, subtype)
        in_lufs = V.measure(pre, sr)["lufs"]
        lmeta = {"input_lufs": in_lufs, "gain_db": round(float(album_gain), 2),
                 "achieved_lufs": (round(in_lufs + album_gain, 2) if in_lufs is not None else None),
                 "target_lufs": target_lufs, "tp_ceiling_dbtp": tp_ceiling,
                 "tp_limited": True, "mode": "album-linéaire"}
    elif reference:
        try:
            REF.match_to_reference(pre_path, reference, master_path, 24)
            used_reference = True
        except Exception as e:
            logger.warning("matchering indisponible (%s) -> normalisation transparente", e)
            lmeta = _normalize(pre, master_path, sr, target_lufs, tp_ceiling, limit, ebu, pre_path, subtype)
    else:
        lmeta = _normalize(pre, master_path, sr, target_lufs, tp_ceiling, limit, ebu, pre_path, subtype)

    before = V.measure(orig_ref, sr)
    master_data, _ = io_wav.read_wav(master_path)
    after = V.measure(master_data if master_data.shape[1] > 1 else master_data[:, 0], sr)
    proc_ref = pre if pre.ndim == 1 else pre.mean(axis=1)
    nt = V.null_test(orig_ref, proc_ref)
    resid = nt.pop("residual")
    null_path = os.path.join(outdir, "null_residual.wav")
    io_wav.write_wav(null_path, np.asarray(resid, dtype=np.float32), sr, "PCM_24")

    outputs = {"master": master_path, "pre_master": pre_path,
               "null_residual": null_path, "stems": stem_paths}

    if before.get("lufs") is not None and lmeta and lmeta.get("achieved_lufs"):
        g = lmeta["achieved_lufs"] - before["lufs"]
        ab = (orig_ref.astype(np.float32) * (10.0 ** (g / 20.0)))
        ab_path = os.path.join(outdir, "original_match.wav")
        io_wav.write_wav(ab_path, ab, sr, "PCM_24")
        outputs["original_match"] = ab_path

    # Format plein : session complète multicanal traitée, pleine résolution
    if full:
        full_arr = _assemble_full(ctx["data"], ctx["cleaned"], analysis)
        full_path = os.path.join(outdir, "full_processed.wav")
        io_wav.write_wav(full_path, full_arr, sr, subtype)
        outputs["full_processed"] = full_path

    rep = R.build_report(wi, analysis, plan, before, after,
                         {**nt, "residual": None}, outputs, ctx["profile"], used_reference, lmeta)
    rep["summary"]["mode"] = ctx["mode"]
    rep["summary"]["output_subtype"] = subtype
    R.write_json(rep, os.path.join(outdir, "report.json"))
    R.write_md(rep, os.path.join(outdir, "report.md"))
    try:
        hp = os.path.join(outdir, "report.html")
        R.write_html(rep, hp)
        outputs["report_html"] = hp
    except Exception:
        pass
    return rep


def run(input_path: str, outdir: str, profile_name: str = "violin_solo",
        reference: str | None = None, make_stems: bool = True,
        limit: bool = False, ebu: bool = False, target_lufs: float | None = None,
        denoise: bool = False, primary: int | None = None,
        reverb: float | None = None, ir: str | None = None,
        glue: bool = False, deharsh_dyn: bool = False, dry_run: bool = False,
        blend=None, debleed: bool = False,
        full: bool = False, bit_depth: str | None = None) -> dict:
    os.makedirs(outdir, exist_ok=True)
    profile = REF.load_profile(profile_name)
    if debleed:
        from . import debleed as _db
        input_path = _db.isolate(input_path, outdir)

    if dry_run:
        data, wi, sr, analysis, plan = _ingest_analyze(
            input_path, profile, denoise, primary, glue, deharsh_dyn)
        empty = {"lufs": None, "peak_dbfs": None, "true_peak_dbtp": None}
        rep = R.build_report(wi, analysis, plan, empty, empty,
                             {"residual_rel_db": None, "interpretation": "(dry-run)"},
                             {}, profile, False, None)
        rep["summary"]["dry_run"] = True
        rep["summary"]["mode"] = "mono" if data.shape[1] == 1 else (
            "stereo" if data.shape[1] == 2 else "multitrack")
        R.write_json(rep, os.path.join(outdir, "report.json"))
        R.write_md(rep, os.path.join(outdir, "report.md"))
        return rep

    ctx = process_to_pre(input_path, profile, denoise=denoise, primary=primary,
                         reverb=reverb, ir=ir, glue=glue, deharsh_dyn=deharsh_dyn, blend=blend)
    loud = profile.get("loudness", {})
    tgt = float(target_lufs) if target_lufs is not None else loud.get("target_lufs", -16.0)
    tp = loud.get("true_peak_dbtp", -1.0)
    subtype = resolve_subtype(bit_depth, full)
    return finalize(ctx, outdir, tgt, tp, make_stems=make_stems,
                    reference=reference, limit=limit, ebu=ebu, subtype=subtype, full=full)
