# Changelog

Toutes les modifications notables de Fides.

## [0.2.3] — 2026-05-31
### Ajouté
- **Preuve visuelle par run** : chaque `report.html` embarque son graphe
  « spectres superposés + courbe de différence (EQ plafonné) » (`report_spectrum.png`,
  via `fides/visualize.py`, matplotlib best-effort).
- **Lint ruff** (E/F/W/I) + job CI dédié ; extra `viz` (matplotlib).
### Corrigé
- Titres des rapports MD/HTML (« DLZ » → « Fides ») ; 5 `E702` et ordre des imports.

## [0.2.2] — 2026-05-31
### Ajouté
- **Publication PyPI automatisée** : workflow `publish.yml` (GitHub Action,
  trusted publishing OIDC — sans token) déclenché à chaque release publiée.
- **Matrice CI** Python 3.10–3.12 ; `CONTRIBUTING.md` ; CLI `fides --version`.
### Changé
- `requires-python` ≥ 3.10 (imposé par numpy 2.2 / scipy 1.15) ; correction du nom
  de programme CLI (`fides`) et version dynamique via `importlib.metadata`.

## [0.2.1] — 2026-05-31
### Ajouté
- **Réverbe à convolution prête à l'emploi** : presets `hall/room/chamber` bundlés
  (`fides/space.py` + `fides/ir/*.wav`) ; `--ir hall|room|chamber` ou un chemin WAV.
- **GUI** glisser‑déposer `fides-gui` (tkinter ; extra `gui`) + capture `assets/gui.png`.
- **README** : badges (CI, licence, Python) + capture spectrale `assets/spectrum.png`.
- **Packaging PyPI** : métadonnées (classifiers, URLs, auteur), `MANIFEST.in`,
  distribution **`fides-mastering`** (profils + IR embarqués), `twine check` OK.

## [0.2.0] — 2026-05-31
### Ajouté
- **Format plein** : `--full` (réassemble tous les canaux traités en un fichier
  multicanal, SR d'origine) + `--bit-depth {24,32,32f}` (32-bit float sans perte).
- **Robustesse** : entrées multi-formats (soundfile + repli ffmpeg M4A/AAC),
  gestion mono/stéréo/multipiste (master stéréo si entrée stéréo), erreurs FR
  claires + exit codes, logging `-v/-q`, garde-fous NaN/court/silence, `--dry-run`.
- **Qualité audio** : réverbe d'espace (`--reverb` algorithmique ou `--ir hall|room|chamber`
  presets bundlés / IR perso), de-harsh dynamique d'archet (`--deharsh`), déclip cubique,
  glue compressor (`--glue`).
- **Workflow** : mode batch (`--batch`) + normalisation album/anchor (EBU R128 s2),
  A/B aligné en loudness (`original_match.wav`), rapports HTML + MD + JSON.
- **Ensembles** : blend multi-micros (`--blend`), de-bleed Demucs expérimental (`--debleed`).
- **Interface graphique** : `fides-gui` (tkinter, glisser‑déposer avec l'extra `gui`).
- **Packaging** : `pyproject.toml`, entry points `fides` + `fides-gui`, CI GitHub Actions, profils + IR embarqués.
- **Doc** : README (badges + capture spectrale `assets/spectrum.png`), GUIDE, ROADMAP, ISSUES, RESEARCH.

## [0.1.0] — 2026-05-31
### Ajouté
- MVP : analyse multicanal (rôles/bruit/clip/hum/tonal), planification, traitement
  transparent (HP, de-hum, EQ plafonné), loudness EBU R128 linéaire, null-test,
  rapport, CLI, tests.
