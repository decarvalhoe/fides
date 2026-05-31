import numpy as np

from fides import analyze as A


def _build(sr=48000, dur=2.0):
    t = np.arange(int(dur * sr)) / sr
    tone = (0.2 * np.sin(2 * np.pi * 440 * t)
            + 0.1 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
    hum = (0.02 * np.sin(2 * np.pi * 50 * t)).astype(np.float32)
    ch0 = (tone + hum).astype(np.float32)          # actif, ronflette
    ch1 = np.clip(tone * 4.0, -1, 1).astype(np.float32)  # écrêté
    ch2 = ch0.copy()                                # duplicata exact de ch0
    ch3 = np.zeros_like(t, dtype=np.float32)         # silence
    return np.stack([ch0, ch1, ch2, ch3], axis=1), sr


def test_roles_and_detections():
    data, sr = _build()
    res = A.analyze(data, sr)
    # silence exclu des actifs
    assert 3 not in res.active_indices
    assert res.channels[3].role == "silent"
    # duplicata détecté
    assert res.channels[2].role == "duplicate"
    assert res.channels[2].duplicate_of == 0
    # ronflette 50 Hz détectée sur ch0
    assert res.channels[0].hum_db.get("50", 0) > 8
    # écrêtage détecté sur ch1
    assert res.channels[1].clipped_runs > 0
    # primaire parmi les actifs uniques
    assert res.primary_index in res.unique_active_indices
    assert set(res.unique_active_indices) == {0, 1}


def test_silent_input():
    sr = 48000
    data = np.zeros((sr, 2), dtype=np.float32)
    res = A.analyze(data, sr)
    assert res.active_indices == []
    assert res.primary_index is None
