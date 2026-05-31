"""Profils de référence + matching sur référence.

- Profils JSON (cibles tonales + garde-fous) par type de formation.
- Matching optionnel via matchering (mg.process) quand une référence est fournie.
"""
from __future__ import annotations

import glob
import json
import os

_HERE = os.path.dirname(__file__)


def profiles_dir() -> str:
    env = os.environ.get("DLZ_PROFILES")
    if env:
        return os.path.normpath(env)
    pkg = os.path.join(_HERE, "profiles")          # profils embarqués dans le package
    if os.path.isdir(pkg):
        return pkg
    return os.path.normpath(os.path.join(_HERE, "..", "profiles"))  # repli dépôt


def list_profiles():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(profiles_dir(), "*.json")))


def load_profile(name: str) -> dict:
    path = os.path.join(profiles_dir(), f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"profil introuvable : '{name}' ({path}). Dispo : {list_profiles()}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_to_reference(target_path: str, reference_path: str, out_path: str,
                       bit_depth: int = 24) -> str:
    """Aligne target sur reference (RMS, réponse en fréquence, crête) via matchering.

    matchering est GPL-3.0 et peut échouer sous numpy 2.x ; l'appelant doit gérer
    l'exception et retomber sur le matcher interne le cas échéant.
    """
    import matchering as mg  # import paresseux : optionnel

    # silence les logs verbeux de matchering
    try:
        mg.log(info_handler=lambda *a, **k: None,
               warning_handler=lambda *a, **k: None)
    except Exception:
        pass

    result = mg.pcm24(out_path) if bit_depth >= 24 else mg.pcm16(out_path)
    mg.process(target=target_path, reference=reference_path, results=[result])
    return out_path
