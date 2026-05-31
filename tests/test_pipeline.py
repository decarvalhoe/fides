import os

import numpy as np
import soundfile as sf

from dlz import pipeline, batch, io_wav


def _tone(n, sr=48000, f=440, amp=0.2):
    t = np.arange(n) / sr
    return (amp * np.sin(2 * np.pi * f * t) * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5)).astype(np.float32)


def test_mono_pipeline(tmp_path):
    sr = 48000
    p = str(tmp_path / "m.wav")
    sf.write(p, _tone(sr * 2), sr, subtype="PCM_24")
    rep = pipeline.run(p, str(tmp_path / "out"), "violin_solo")
    assert rep["summary"]["mode"] == "mono"
    m, _ = io_wav.read_wav(str(tmp_path / "out" / "master.wav"))
    assert m.shape[1] == 1
    assert rep["summary"]["loudness_after"]["true_peak_dbtp"] <= -0.9


def test_stereo_master(tmp_path):
    sr = 48000
    x = _tone(sr * 2)
    st = np.stack([x, np.roll(x, 40)], axis=1)
    p = str(tmp_path / "s.wav")
    sf.write(p, st, sr, subtype="PCM_24")
    rep = pipeline.run(p, str(tmp_path / "out"), "violin_solo")
    assert rep["summary"]["mode"] == "stereo"
    m, _ = io_wav.read_wav(str(tmp_path / "out" / "master.wav"))
    assert m.shape[1] == 2


def test_multitrack_primary_avoids_clip(tmp_path):
    sr = 48000
    close = _tone(sr * 2, amp=0.3)
    clipped = np.clip(close * 4.0, -1, 1).astype(np.float32)
    sil = np.zeros(sr * 2, dtype=np.float32)
    data = np.stack([clipped, close, sil], axis=1)   # ch0 écrêté, ch1 propre
    p = str(tmp_path / "mt.wav")
    sf.write(p, data, sr, subtype="PCM_24")
    rep = pipeline.run(p, str(tmp_path / "out"), "violin_solo")
    assert rep["summary"]["mode"] == "multitrack"
    assert rep["summary"]["primary_channel"] == 1   # évite le canal écrêté


def test_dry_run(tmp_path):
    sr = 48000
    p = str(tmp_path / "m.wav")
    sf.write(p, _tone(sr), sr, subtype="PCM_24")
    rep = pipeline.run(p, str(tmp_path / "out"), "violin_solo", dry_run=True)
    assert rep["summary"]["dry_run"] is True
    assert not os.path.exists(str(tmp_path / "out" / "master.wav"))


def test_batch_album_preserves_order(tmp_path):
    sr = 48000
    d = tmp_path / "in"
    d.mkdir()
    for nm, amp in [("a_loud", 0.8), ("b_soft", 0.3)]:
        sf.write(str(d / f"{nm}.wav"), _tone(sr * 2, amp=amp), sr, subtype="PCM_24")
    s = batch.run_batch(str(d), str(tmp_path / "out"), "violin_solo", album=True)
    assert s["count"] == 2
    assert s["album_gain_db"] is not None
    lufs = [tr["master_lufs"] for tr in s["tracks"]]
    assert lufs == sorted(lufs, reverse=True)   # rapport de loudness album préservé


def test_full_format_multichannel(tmp_path):
    sr = 48000
    close = _tone(sr, amp=0.3)
    room = _tone(sr, amp=0.1)
    sil = np.zeros(sr, dtype=np.float32)
    data = np.stack([close, room, sil], axis=1)
    p = str(tmp_path / "mt.wav")
    sf.write(p, data, sr, subtype="PCM_24")
    rep = pipeline.run(p, str(tmp_path / "out"), "violin_solo", full=True)
    fp = str(tmp_path / "out" / "full_processed.wav")
    assert os.path.exists(fp)
    full, wi = io_wav.read_wav(fp)
    assert full.shape[1] == 3            # TOUS les canaux préservés
    assert wi.subtype == "FLOAT"         # 32-bit float (pleine résolution)
    assert wi.samplerate == sr           # SR d'origine préservé
    assert "full_processed" in rep["summary"]["outputs"]


def test_bit_depth_pcm32(tmp_path):
    sr = 48000
    p = str(tmp_path / "m.wav")
    sf.write(p, _tone(sr), sr, subtype="PCM_24")
    pipeline.run(p, str(tmp_path / "out"), "violin_solo", bit_depth="32")
    _, wi = io_wav.read_wav(str(tmp_path / "out" / "master.wav"))
    assert wi.subtype == "PCM_32"
