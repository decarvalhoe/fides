import os

import pytest

from fides import space


def test_ir_presets_resolve():
    for name in ("hall", "room", "chamber"):
        p = space.resolve_ir(name)
        assert os.path.exists(p)


def test_ir_unknown_raises():
    with pytest.raises(FileNotFoundError):
        space.resolve_ir("/nope/does_not_exist_xyz.wav")


def test_synth_ir_shape():
    ir = space.synth_ir(rt60=1.0, predelay=0.01, er=5, sr=48000, seed=0)
    assert ir.ndim == 2 and ir.shape[1] == 2
    assert abs(float(ir.max())) <= 1.0 + 1e-6
