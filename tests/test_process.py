import numpy as np

from fides import process as PROC
from fides import verify as V


def test_loudness_linear_respects_true_peak():
    sr = 48000
    t = np.arange(int(2 * sr)) / sr
    x = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)  # ~-6 dBFS
    y, meta = PROC.loudness_normalize_array(x, sr, target_lufs=-16.0, tp_ceiling=-1.0)
    assert len(y) == len(x)
    # le true-peak du master ne dépasse pas le plafond (tolérance oversampling)
    assert V.true_peak_dbtp(y, sr) <= -1.0 + 0.3
    assert meta["mode"] == "linéaire"
    assert meta["input_lufs"] is not None


def test_null_test_identity():
    rng = np.random.RandomState(0)
    x = (0.1 * rng.randn(48000)).astype(np.float32)
    nt = V.null_test(x, x)
    assert abs(nt["gain_match"] - 1.0) < 1e-3
    assert nt["residual_rel_db"] < -60  # signaux identiques -> résidu quasi nul


def test_process_channel_runs():
    sr = 48000
    t = np.arange(int(1 * sr)) / sr
    x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    plan_ch = {
        "highpass_hz": 30,
        "eq": [{"type": "highshelf", "freq": 11000, "gain_db": 3.0, "q": 0.7}],
    }
    y, meta = PROC.process_channel(x, sr, plan_ch)
    assert len(y) == len(x)
    assert np.isfinite(y).all()
    assert "eq" in meta["applied"]
