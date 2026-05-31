#!/usr/bin/env bash
# Palier 2 (gratuit/local) : torch CPU + demucs (de-bleed optionnel pour ensembles).
set -uo pipefail
PY="$HOME/dlz/.venv/bin/python"
echo "[*] palier 2 : torch (CPU) + demucs"
# torch ET torchaudio depuis le MÊME index (sinon demucs tire un torchaudio incompatible)
"$PY" -m pip install --quiet torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
  || echo "[warn] torch/torchaudio CPU: échec d'installation"
"$PY" -m pip install --quiet demucs \
  || echo "[warn] demucs: échec d'installation"
"$PY" - <<'PY'
for m in ["torch", "demucs"]:
    try:
        mod = __import__(m)
        print(f"  {m} {getattr(mod, '__version__', '?')}")
    except Exception as e:
        print(f"  {m} absent: {type(e).__name__}: {e}")
PY
echo "[DONE] palier 2"
