import os

import numpy as np
import soundfile as sf

from fides import pipeline, visualize


def test_spectrum_figure(tmp_path):
    sr = 48000
    t = np.arange(2 * sr) / sr
    x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    out = str(tmp_path / "s.png")
    p = visualize.spectrum_figure(x, x * 0.9, sr, out)
    assert p == out and os.path.exists(out)


def test_report_embeds_spectrum(tmp_path):
    sr = 48000
    t = np.arange(2 * sr) / sr
    x = (0.2 * np.sin(2 * np.pi * 440 * t) * (np.sin(2 * np.pi * 0.7 * t) * 0.5 + 0.5)).astype(np.float32)
    p = str(tmp_path / "in.wav")
    sf.write(p, x, sr, subtype="PCM_24")
    pipeline.run(p, str(tmp_path / "out"), "violin_solo")
    assert os.path.exists(str(tmp_path / "out" / "report_spectrum.png"))
    html = open(str(tmp_path / "out" / "report.html"), encoding="utf-8").read()
    assert "report_spectrum.png" in html
