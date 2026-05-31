"""Entrées/sorties WAV robustes pour le pipeline DLZ.

Gère le multicanal 24-bit et les fichiers à en-tête tronqué/sur-déclaré
(typiques des enregistreurs de terrain coupés brutalement) en lisant les
frames réellement présentes via soundfile/libsndfile.

La détection de troncature compare la taille de chunk `data` DÉCLARÉE dans
l'en-tête RIFF aux octets physiquement présents (libsndfile, lui, recale
silencieusement le nombre de frames — d'où une vérification au niveau RIFF).
"""
from __future__ import annotations

import os
import struct
from dataclasses import asdict, dataclass

import numpy as np
import soundfile as sf

_VALID_SUBTYPES = {"PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"}
_BYTES_PER_SAMPLE = {"PCM_16": 2, "PCM_24": 3, "PCM_32": 4, "FLOAT": 4, "DOUBLE": 8}


@dataclass
class WavInfo:
    path: str
    samplerate: int
    channels: int
    frames_read: int        # frames réellement lues
    frames_declared: int    # frames déclarées dans l'en-tête RIFF
    subtype: str
    truncated: bool

    @property
    def duration(self) -> float:
        return self.frames_read / self.samplerate if self.samplerate else 0.0

    def as_dict(self):
        d = asdict(self)
        d["duration_s"] = round(self.duration, 3)
        return d


def _riff_data_chunk(path: str):
    """Retourne {'declared': octets, 'available': octets} du chunk `data`, ou None."""
    try:
        filesize = os.path.getsize(path)
        with open(path, "rb") as f:
            if f.read(4) != b"RIFF":
                return None
            f.read(4)
            if f.read(4) != b"WAVE":
                return None
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                cid, csize = hdr[:4], struct.unpack("<I", hdr[4:])[0]
                if cid == b"data":
                    offset = f.tell()
                    return {"declared": csize, "available": max(0, filesize - offset)}
                f.seek(csize + (csize % 2), 1)
    except Exception:
        return None
    return None


def _truncation(path: str, info, frames_read: int):
    dc = _riff_data_chunk(path)
    if not dc:
        return info.frames, frames_read < info.frames
    bps = _BYTES_PER_SAMPLE.get(info.subtype, 0)
    if bps and info.channels:
        declared_frames = dc["declared"] // (bps * info.channels)
    else:
        declared_frames = info.frames
    truncated = dc["declared"] > dc["available"] + 64   # tolérance padding
    return declared_frames, truncated


def probe(path: str) -> WavInfo:
    """En-tête seul, sans charger l'audio."""
    info = sf.info(path)
    declared, truncated = _truncation(path, info, info.frames)
    return WavInfo(path, info.samplerate, info.channels, info.frames,
                   declared, info.subtype, truncated)


def read_wav(path: str, dtype: str = "float32"):
    """Lit toutes les frames disponibles, même si l'en-tête sur-déclare la taille.

    Retourne (data [n, ch] float, WavInfo).
    """
    info = sf.info(path)
    blocks = []
    read = 0
    with sf.SoundFile(path) as f:
        while True:
            b = f.read(1 << 20, dtype=dtype, always_2d=True)
            if len(b) == 0:
                break
            blocks.append(b)
            read += len(b)
    if blocks:
        data = np.concatenate(blocks, axis=0)
    else:
        data = np.zeros((0, info.channels), dtype=dtype)
    declared_frames, truncated = _truncation(path, info, read)
    wi = WavInfo(path, info.samplerate, info.channels, read, declared_frames,
                 info.subtype, truncated)
    return data, wi


def write_wav(path: str, data: np.ndarray, samplerate: int, subtype: str = "PCM_24") -> str:
    """Écrit un tableau float [-1, 1] en WAV (24-bit par défaut)."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    if data.ndim == 1:
        data = data[:, None]
    if subtype not in _VALID_SUBTYPES:
        subtype = "PCM_24"
    sf.write(path, data, samplerate, subtype=subtype)
    return path


def repair_wav(src: str, dst: str, subtype: str | None = None) -> WavInfo:
    """Reconstruit un WAV valide à partir des frames lisibles (corrige l'en-tête)."""
    data, wi = read_wav(src)
    st = subtype or (wi.subtype if wi.subtype in _VALID_SUBTYPES else "PCM_24")
    write_wav(dst, data, wi.samplerate, subtype=st)
    return wi


def deinterleave(data: np.ndarray):
    """[n, ch] -> liste de ch tableaux 1-D contigus."""
    if data.ndim == 1:
        return [data.copy()]
    return [np.ascontiguousarray(data[:, c]) for c in range(data.shape[1])]
