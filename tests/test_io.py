import os

import numpy as np

from dlz import io_wav


def _sine(n, sr=48000, f=440, amp=0.1):
    return (amp * np.sin(2 * np.pi * f * np.arange(n) / sr)).astype(np.float32)


def test_write_read_roundtrip(tmp_path):
    sr = 48000
    x = _sine(sr)
    data = np.stack([x, 0.5 * x], axis=1)
    p = str(tmp_path / "a.wav")
    io_wav.write_wav(p, data, sr, "PCM_24")
    d, wi = io_wav.read_wav(p)
    assert wi.samplerate == sr
    assert wi.channels == 2
    assert d.shape[0] == sr
    assert not wi.truncated


def test_truncated_header(tmp_path):
    sr = 48000
    n = sr  # 1 s mono
    p = str(tmp_path / "t.wav")
    io_wav.write_wav(p, _sine(n), sr, "PCM_24")
    full = os.path.getsize(p)
    # retire ~0.4 s de données (24-bit mono = 3 octets/frame) sans toucher l'en-tête
    with open(p, "r+b") as f:
        f.truncate(full - int(0.4 * n) * 3)
    d, wi = io_wav.read_wav(p)
    assert wi.truncated
    assert 0 < wi.frames_read < wi.frames_declared


def test_deinterleave():
    data = np.zeros((100, 3), dtype=np.float32)
    data[:, 1] = 1.0
    chans = io_wav.deinterleave(data)
    assert len(chans) == 3
    assert np.allclose(chans[1], 1.0)
    assert np.allclose(chans[0], 0.0)
