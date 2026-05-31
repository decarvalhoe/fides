#!/usr/bin/env bash
# Provisionnement palier 1 : venv + stack audio open-source (sans sudo, sans GPU).
set -euo pipefail
ROOT="$HOME/dlz"
mkdir -p "$ROOT/in" "$ROOT/out" "$ROOT/ref" "$ROOT/log"
PY="$ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "[*] création du venv $ROOT/.venv"
  python3 -m venv "$ROOT/.venv"
fi

echo "[*] mise à jour pip/wheel/setuptools"
"$PY" -m pip install --quiet --upgrade pip wheel setuptools

echo "[*] installation du coeur open-source (quelques minutes)..."
"$PY" -m pip install numpy scipy soundfile pyloudnorm pedalboard noisereduce ffmpeg-normalize

echo "[*] matchering (optionnel)"
"$PY" -m pip install matchering || echo "[warn] matchering non installé -> on utilisera le matcher interne"

echo "[*] versions installées :"
"$PY" - <<'PY'
import importlib
for m in ["numpy","scipy","soundfile","pyloudnorm","pedalboard","noisereduce","matchering"]:
    try:
        mod = importlib.import_module(m)
        print(f"  {m:12} {getattr(mod,'__version__','?')}")
    except Exception as e:
        print(f"  {m:12} (absent: {type(e).__name__})")
import soundfile as sf
print("  libsndfile  ", sf.__libsndfile_version__)
PY
echo "[DONE] palier 1 OK"
