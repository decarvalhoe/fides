# Changelog

Toutes les modifications notables de DLZ Mastering.

## [0.2.0] — 2026-05-31
### Ajouté
- **Format plein** : `--full` (réassemble tous les canaux traités en un fichier
  multicanal, SR d'origine) + `--bit-depth {24,32,32f}` (32-bit float sans perte).
- **Robustesse** : entrées multi-formats (soundfile + repli ffmpeg M4A/AAC),
  gestion mono/stéréo/multipiste (master stéréo si entrée stéréo), erreurs FR
  claires + exit codes, logging `-v/-q`, garde-fous NaN/court/silence, `--dry-run`.
- **Qualité audio** : réverbe d'espace (`--reverb`/`--ir`), de-harsh dynamique
  d'archet (`--deharsh`), déclip cubique, glue compressor (`--glue`).
- **Workflow** : mode batch (`--batch`) + normalisation album/anchor (EBU R128 s2),
  A/B aligné en loudness (`original_match.wav`), rapports HTML + MD + JSON.
- **Ensembles** : blend multi-micros (`--blend`), de-bleed Demucs expérimental (`--debleed`).
- **Packaging** : `pyproject.toml`, entry point `dlz`, CI GitHub Actions, profils embarqués.
- **Doc** : README, GUIDE (prise de son), ROADMAP, ISSUES, RESEARCH.

## [0.1.0] — 2026-05-31
### Ajouté
- MVP : analyse multicanal (rôles/bruit/clip/hum/tonal), planification, traitement
  transparent (HP, de-hum, EQ plafonné), loudness EBU R128 linéaire, null-test,
  rapport, CLI, tests.
