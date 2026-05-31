"""Chargement audio robuste multi-formats : soundfile d'abord, repli ffmpeg.

libsndfile lit WAV/FLAC/AIFF/OGG (et MP3 en 1.1+). Pour les formats non gérés
(M4A/AAC/MP4…), on décode via ffmpeg vers un WAV 24-bit temporaire.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from . import io_wav


def load_audio(path: str):
    """Retourne (data [n, ch] float32, WavInfo) quel que soit le format d'entrée."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"fichier introuvable : {path}")
    try:
        return io_wav.read_wav(path)
    except Exception as e_sf:
        tmp = None
        try:
            tmp = _ffmpeg_decode(path)
            data, wi = io_wav.read_wav(tmp)
            wi.path = path  # garde le chemin d'origine dans le rapport
            return data, wi
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg introuvable : format non géré nativement et pas de repli possible")
        except Exception as e_ff:
            raise RuntimeError(
                f"impossible de lire '{os.path.basename(path)}' "
                f"(soundfile: {e_sf}; ffmpeg: {e_ff})")
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


def _ffmpeg_decode(path: str) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="dlz_")
    os.close(fd)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", path, "-c:a", "pcm_s24le", tmp]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError("ffmpeg absent du PATH")
    if r.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
        raise RuntimeError((r.stderr or "").strip()[:200] or "échec du décodage ffmpeg")
    return tmp
