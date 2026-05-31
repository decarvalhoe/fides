"""Planification — décide la chaîne et les paramètres depuis l'analyse + le profil.

Toutes les décisions sont conservatrices et plafonnées (philosophie « ne pas
dénaturer ») et restituées en clair pour le rapport.
"""
from __future__ import annotations


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _ratio_gain(deficit_or_excess, target, max_db):
    """Mappe un écart en points de % vers un gain/atténuation plafonné."""
    if target <= 0:
        return 0.0
    return _clamp(max_db * (deficit_or_excess / target), 0.0, max_db)


def plan_channel(ca, profile: dict, allow_denoise: bool = False) -> dict:
    p = {"index": ca.index, "role": ca.role, "steps": [], "eq": []}

    hp = profile.get("highpass_hz", 30)
    p["highpass_hz"] = hp
    p["steps"].append(f"passe-haut {hp} Hz (rumble)")

    if ca.clipped_runs > 0:
        p["declip"] = True
        p["steps"].append(f"déclip : {ca.clipped_runs} série(s) de pleine échelle")

    dh = profile.get("dehum", {})
    hum50 = (ca.hum_db or {}).get("50", 0.0)
    if dh and hum50 >= dh.get("min_excess_db", 8.0):
        freqs = [dh.get("base_hz", 50) * (k + 1) for k in range(dh.get("harmonics", 3))]
        p["dehum"] = {"freqs": freqs, "q": dh.get("q", 30)}
        p["steps"].append(f"de-hum {freqs} Hz (50 Hz à +{hum50:.1f} dB sur le voisinage)")

    dn = profile.get("denoise", {})
    fmin = dn.get("floor_min_dbfs", -65.0)
    fmax = dn.get("floor_max_dbfs", -48.0)
    # Ne débruite QUE si le plancher est dans la fenêtre "souffle" (ni program, ni déjà propre)
    if (allow_denoise and dn and fmin <= ca.noise_floor_dbfs <= fmax
            and ca.dynamic_range_db >= dn.get("min_dr_db", 20.0)):
        p["denoise"] = {"prop_decrease": dn.get("prop_decrease", 0.5)}
        p["steps"].append(
            f"débruitage doux (plancher {ca.noise_floor_dbfs:.1f} dBFS dans la fenêtre souffle, "
            f"prop={dn.get('prop_decrease', 0.5)})")

    tb = profile.get("target_bands_pct", {})
    bands = ca.bands_pct or {}
    if bands:
        a = profile.get("air_shelf")
        if a:
            deficit = tb.get("air", 0) - bands.get("air", 0)
            if deficit >= a.get("deficit_pct", 1.5):
                gain = _ratio_gain(deficit, tb.get("air", 1), a["max_gain_db"])
                if gain > 0.1:
                    p["eq"].append({"type": "highshelf", "freq": a["freq_hz"],
                                    "gain_db": round(gain, 2), "q": 0.7})
                    p["steps"].append(f"air +{gain:.1f} dB @ {a['freq_hz']} Hz")

        w = profile.get("warmth_shelf")
        if w:
            deficit = tb.get("low", 0) - bands.get("low", 0)
            if deficit >= w.get("deficit_pct", 3.0):
                gain = _ratio_gain(deficit, tb.get("low", 1), w["max_gain_db"])
                if gain > 0.1:
                    p["eq"].append({"type": "lowshelf", "freq": w["freq_hz"],
                                    "gain_db": round(gain, 2), "q": 0.7})
                    p["steps"].append(f"chaleur +{gain:.1f} dB @ {w['freq_hz']} Hz")

        lm = profile.get("lowmid_tame")
        if lm:
            excess = bands.get("low_mid", 0) - tb.get("low_mid", 0)
            if excess >= lm.get("excess_pct", 6.0):
                cut = _ratio_gain(excess, tb.get("low_mid", 1), lm["max_cut_db"])
                if cut > 0.1:
                    p["eq"].append({"type": "peak", "freq": lm["freq_hz"],
                                    "gain_db": round(-cut, 2), "q": lm.get("q", 1.0)})
                    p["steps"].append(f"bas-medium -{cut:.1f} dB @ {lm['freq_hz']} Hz")

        dhh = profile.get("deharsh")
        if dhh:
            excess = bands.get("high_mid", 0) - tb.get("high_mid", 0)
            if excess >= dhh.get("excess_pct", 6.0):
                cut = _ratio_gain(excess, tb.get("high_mid", 1), dhh["max_cut_db"])
                if cut > 0.1:
                    p["eq"].append({"type": "peak", "freq": dhh["freq_hz"],
                                    "gain_db": round(-cut, 2), "q": dhh.get("q", 1.2)})
                    p["steps"].append(f"de-harsh (archet) -{cut:.1f} dB @ {dhh['freq_hz']} Hz")

    if not p["eq"]:
        p["steps"].append("aucune correction tonale nécessaire")
    return p


def make_plan(analysis, profile: dict, allow_denoise: bool = False) -> dict:
    chans = analysis.unique_active_indices or analysis.active_indices
    plan = {
        "profile": profile.get("name"),
        "primary_index": analysis.primary_index,
        "loudness": profile.get("loudness", {"target_lufs": -16.0, "true_peak_dbtp": -1.0}),
        "process_channels": chans,
        "channels": {},
    }
    for c in chans:
        plan["channels"][str(c)] = plan_channel(analysis.channels[c], profile, allow_denoise)
    return plan
