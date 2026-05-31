"""Traitement DSP transparent (par canal) + normalisation loudness (master).

Cleaning surgical (DC, déclip, de-hum, débruitage doux) puis EQ correctif
plafonné via pedalboard. La loudness EBU R128 est appliquée au master par
gain linéaire plafonné true-peak (dynamique préservée) — gère mono et stéréo.
"""
from __future__ import annotations

import numpy as np
from scipy import signal
import pedalboard as pb

EPS = 1e-12


def _dc_remove(x: np.ndarray) -> np.ndarray:
    return x - float(np.mean(x))


def _short_rms(x: np.ndarray, win: int) -> np.ndarray:
    n = len(x) // win
    if n < 1:
        return np.array([np.sqrt(np.mean(x.astype(np.float64) ** 2) + EPS)])
    xt = x[:n * win].reshape(n, win).astype(np.float64)
    return np.sqrt(np.mean(xt ** 2, axis=1) + EPS)


def _declip(x: np.ndarray, thr: float = 0.999):
    """Déclip par interpolation cubique des séries de pleine échelle."""
    y = x.copy()
    mask = np.abs(y) >= thr
    if not mask.any():
        return y, 0
    idx = np.flatnonzero(mask)
    splits = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    n = len(y)
    count = 0
    for s in splits:
        a, b = int(s[0]), int(s[-1])
        # points d'appui de part et d'autre de la série
        xs, ys = [], []
        for off in (-2, -1):
            if a + off >= 0:
                xs.append(a + off); ys.append(y[a + off])
        for off in (1, 2):
            if b + off < n:
                xs.append(b + off); ys.append(y[b + off])
        if len(xs) < 2:
            continue
        deg = 3 if len(xs) >= 4 else 1
        xs_local = [xx - a for xx in xs]   # repère local : évite le mauvais conditionnement
        coeffs = np.polyfit(xs_local, ys, deg)
        y[a:b + 1] = np.polyval(coeffs, np.arange(a, b + 1) - a)
        count += 1
    return y, count


def _notch(x: np.ndarray, sr: int, freqs, q: float = 30.0) -> np.ndarray:
    y = x.astype(np.float64)
    for f0 in freqs:
        if 0 < f0 < sr / 2 * 0.95:
            b, a = signal.iirnotch(f0, q, sr)
            y = signal.filtfilt(b, a, y)
    return y


def _denoise(x: np.ndarray, sr: int, prop_decrease: float = 0.5) -> np.ndarray:
    import noisereduce as nr
    win = int(0.4 * sr)
    noise = None
    if len(x) > 2 * win:
        st = _short_rms(x, win)
        i = int(np.argmin(st)) * win
        noise = x[i:i + win]
    try:
        return nr.reduce_noise(y=x, sr=sr, y_noise=noise, stationary=True,
                               prop_decrease=prop_decrease)
    except TypeError:
        return nr.reduce_noise(y=x, sr=sr, stationary=True,
                               prop_decrease=prop_decrease)


def _deharsh_dynamic(x: np.ndarray, sr: int, freq=3200.0, q=1.2,
                     max_cut_db=3.0, thr_db=-28.0) -> np.ndarray:
    """De-harsh DYNAMIQUE : n'atténue la bande archet que lorsqu'elle dépasse un seuil.

    On isole la bande (bandpass), on suit son enveloppe, et on retire une fraction
    de la bande proportionnelle au dépassement (jusqu'à max_cut_db). Transparent
    quand l'archet est doux, n'agit que sur les pics agressifs.
    """
    x = x.astype(np.float64)
    lo, hi = freq / (2 ** (1 / (2 * q))), freq * (2 ** (1 / (2 * q)))
    lo = max(20.0, lo); hi = min(sr / 2 * 0.95, hi)
    sos = signal.butter(2, [lo, hi], btype="band", fs=sr, output="sos")
    band = signal.sosfilt(sos, x)
    # enveloppe lissée de la bande
    env = np.abs(signal.hilbert(band))
    win = max(1, int(0.005 * sr))
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env_db = 20.0 * np.log10(env + EPS)
    over = np.clip(env_db - thr_db, 0, None)          # dépassement (dB)
    # fraction de réduction (0..1) plafonnée à max_cut
    red_db = np.minimum(over * 0.5, max_cut_db)
    frac = 1.0 - 10.0 ** (-red_db / 20.0)             # part de bande à soustraire
    return (x - frac * band).astype(np.float64)


def _build_board(plan_ch: dict) -> pb.Pedalboard:
    chain = [pb.HighpassFilter(cutoff_frequency_hz=float(plan_ch.get("highpass_hz", 30)))]
    for e in plan_ch.get("eq", []):
        t = e["type"]
        if t == "highshelf":
            chain.append(pb.HighShelfFilter(cutoff_frequency_hz=float(e["freq"]),
                                            gain_db=float(e["gain_db"]), q=float(e.get("q", 0.7))))
        elif t == "lowshelf":
            chain.append(pb.LowShelfFilter(cutoff_frequency_hz=float(e["freq"]),
                                           gain_db=float(e["gain_db"]), q=float(e.get("q", 0.7))))
        elif t == "peak":
            chain.append(pb.PeakFilter(cutoff_frequency_hz=float(e["freq"]),
                                       gain_db=float(e["gain_db"]), q=float(e.get("q", 1.0))))
    return pb.Pedalboard(chain)


def process_channel(x: np.ndarray, sr: int, plan_ch: dict):
    """Applique le plan d'un canal à un signal 1-D float. Retourne (y, meta)."""
    meta = {"applied": []}
    y = _dc_remove(np.asarray(x, dtype=np.float32))

    if plan_ch.get("declip"):
        y, cnt = _declip(y)
        meta["applied"].append(f"declip({cnt})")

    if "dehum" in plan_ch:
        d = plan_ch["dehum"]
        y = _notch(y, sr, d["freqs"], d.get("q", 30)).astype(np.float32)
        meta["applied"].append("dehum")

    if "denoise" in plan_ch:
        y = _denoise(y, sr, plan_ch["denoise"].get("prop_decrease", 0.5)).astype(np.float32)
        meta["applied"].append("denoise")

    if plan_ch.get("deharsh_dyn"):
        d = plan_ch["deharsh_dyn"]
        y = _deharsh_dynamic(y, sr, d.get("freq", 3200), d.get("q", 1.2),
                             d.get("max_cut_db", 3.0), d.get("thr_db", -28.0)).astype(np.float32)
        meta["applied"].append("deharsh_dyn")

    board = _build_board(plan_ch)
    y = board(np.ascontiguousarray(y, dtype=np.float32), float(sr))
    meta["applied"].append("eq" if plan_ch.get("eq") else "highpass")

    if plan_ch.get("glue"):
        g = plan_ch["glue"]
        comp = pb.Pedalboard([pb.Compressor(threshold_db=float(g.get("threshold_db", -18.0)),
                                            ratio=float(g.get("ratio", 1.5)),
                                            attack_ms=float(g.get("attack_ms", 30.0)),
                                            release_ms=float(g.get("release_ms", 250.0)))])
        y = comp(np.ascontiguousarray(np.asarray(y, dtype=np.float32)), float(sr))
        meta["applied"].append("glue")

    return np.asarray(y, dtype=np.float32).reshape(-1), meta


def loudness_normalize_file(in_path: str, out_path: str, target_lufs: float = -16.0,
                            true_peak: float = -1.0, sr: int = 48000) -> str:
    """Normalisation EBU R128 (deux passes) via ffmpeg-normalize (peut compresser la dynamique)."""
    from ffmpeg_normalize import FFmpegNormalize
    kwargs = dict(normalization_type="ebu", target_level=float(target_lufs),
                  true_peak=float(true_peak), dynamic=False,
                  audio_codec="pcm_s24le", sample_rate=int(sr))
    try:
        fn = FFmpegNormalize(**kwargs)
    except TypeError:
        kwargs.pop("sample_rate", None)
        kwargs.pop("audio_codec", None)
        fn = FFmpegNormalize(**kwargs)
    fn.add_media_file(in_path, out_path)
    fn.run_normalization()
    return out_path


def _true_peak(x, sr, oversample: int = 4) -> float:
    """True-peak (dBTP) sur 1-D ou [n, ch] (max sur les canaux)."""
    from scipy.signal import resample_poly
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 1:
        a = a[:, None]
    peak = 0.0
    for c in range(a.shape[1]):
        xo = resample_poly(a[:, c], oversample, 1)
        peak = max(peak, float(np.max(np.abs(xo))))
    return 20.0 * np.log10(peak + EPS)


def _apply_limiter(y, sr, ceiling_db):
    board = pb.Pedalboard([pb.Limiter(threshold_db=float(ceiling_db) - 0.5, release_ms=120.0)])
    a = np.asarray(y, dtype=np.float32)
    if a.ndim == 1:
        return board(np.ascontiguousarray(a), float(sr)).reshape(-1)
    cols = [board(np.ascontiguousarray(a[:, c]), float(sr)).reshape(-1) for c in range(a.shape[1])]
    return np.stack(cols, axis=1)


def loudness_normalize_array(x, sr, target_lufs: float = -16.0,
                             tp_ceiling: float = -1.0, limit: bool = False):
    """Normalisation loudness TRANSPARENTE (gain linéaire), mono ou stéréo.

    Le gain est plafonné par le true-peak (dynamique préservée). Avec limit=True,
    un limiteur doux atteint la cible au prix d'un écrêtage de crête minimal.
    """
    import pyloudnorm as pyln
    a = np.asarray(x, dtype=np.float64)
    meas = a if a.ndim > 1 else a.reshape(-1)
    try:
        lufs = float(pyln.Meter(sr).integrated_loudness(meas))
    except Exception:
        lufs = float("nan")
    tp = _true_peak(a, sr)
    valid = (lufs == lufs) and (lufs != -np.inf)
    need = (target_lufs - lufs) if valid else 0.0
    tp_room = tp_ceiling - tp
    if limit and valid:
        y = _apply_limiter(a * (10.0 ** (need / 20.0)), sr, tp_ceiling)
        gain, tp_limited = need, False
    else:
        gain = min(need, tp_room) if valid else min(0.0, tp_room)
        y = a * (10.0 ** (gain / 20.0))
        tp_limited = valid and (need > tp_room)
    meta = {
        "input_lufs": round(lufs, 2) if valid else None,
        "input_true_peak_dbtp": round(tp, 2),
        "gain_db": round(float(gain), 2),
        "achieved_lufs": (round(lufs + gain, 2) if (valid and not limit)
                          else (round(target_lufs, 2) if limit else None)),
        "target_lufs": target_lufs,
        "tp_ceiling_dbtp": tp_ceiling,
        "tp_limited": bool(tp_limited),
        "mode": "limiter" if limit else "linéaire",
    }
    return np.asarray(y, dtype=np.float32), meta


def apply_reverb(x, sr, amount: float = 0.2, ir_path: str | None = None):
    """Réverbe d'espace subtile (par canal). IR de convolution si fournie, sinon algorithmique."""
    a = np.asarray(x, dtype=np.float32)
    amount = float(max(0.0, min(1.0, amount)))
    if ir_path:
        board = pb.Pedalboard([pb.Convolution(ir_path, mix=amount)])
    else:
        board = pb.Pedalboard([pb.Reverb(room_size=0.5, damping=0.5,
                                         wet_level=amount, dry_level=1.0 - amount, width=1.0)])

    def _one(col):
        return board(np.ascontiguousarray(col, dtype=np.float32), float(sr)).reshape(-1)

    if a.ndim == 1:
        return _one(a).astype(np.float32)
    return np.stack([_one(a[:, c]) for c in range(a.shape[1])], axis=1).astype(np.float32)
