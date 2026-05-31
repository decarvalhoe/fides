# Issues — Fides

Backlog pour un outil **robuste, simple, pro, sans service payant**.
Priorités : **P0** bloquant · **P1** important · **P2** confort. Labels entre `[ ]`.

## v0.2 — Robustesse

- **#1 [robustesse][P0]** Entrées multi-formats. FLAC/AIFF/OGG natifs (soundfile) ; MP3/M4A/MP4/autres via décodage **ffmpeg** vers WAV temporaire. *AC : `fides IN.flac` et `IN.mp3` aboutissent.*
- **#2 [robustesse][P0]** Tout nombre de canaux : mono, stéréo, N. Pas de dé-duplication absurde en mono ; stéréo géré (paires). *AC : mono & stéréo & 14ch OK.*
- **#3 [robustesse][P0]** Validation & erreurs claires (fichier absent, format illisible, profil inconnu, aucun canal actif, sortie non inscriptible) — message FR, exit≠0, pas de traceback.
- **#4 [robustesse][P1]** Logging structuré (`--verbose`/`--quiet`) ; warnings ffmpeg/libs silencieux par défaut.
- **#5 [robustesse][P1]** Garde-fous numériques : NaN/Inf nettoyés, fichiers très courts (<0.4 s), entrée totalement silencieuse → message clair.
- **#6 [robustesse][P1]** `--dry-run` : analyse + plan seulement (report.json), aucun rendu audio.

## v0.3 — Qualité audio

- **#7 [qualité][P1]** Réverbe d'espace : `--reverb[=amount]` (pedalboard.Reverb, algorithmique) + `--ir IR.wav` (convolution). Subtile, off par défaut, null-test montre l'ajout.
- **#8 [qualité][P1]** De-harsh **dynamique** d'archet (2–6 kHz) : n'agit que sur les pics, pas un cut statique.
- **#9 [qualité][P2]** Déclip **cubique** (vs interpolation linéaire) + fondu aux bords.
- **#10 [qualité][P2]** `--glue` : compresseur très doux, program-dependent, off par défaut (préserve la dynamique).

## v0.4 — Workflow pro

- **#11 [workflow][P1]** Mode **batch** : `fides batch DIR -o OUT` traite toutes les prises d'un dossier avec réglages cohérents.
- **#12 [workflow][P1]** Normalisation **album/anchor** (EBU R128 s2) : gain commun calculé sur l'ensemble du lot (ancre = mouvement le plus fort).
- **#13 [workflow][P2]** Export A/B **aligné en loudness** : `original_match.wav` au même LUFS que le master (comparaison juste).
- **#14 [workflow][P2]** Rapport **HTML** autonome (en plus de MD/JSON).
- **#15 [pro][P1]** Packaging : `pyproject.toml` + entry point console `fides` (`pip install -e .`).

## v0.5 — Ensembles (palier 2)

- **#16 [ensemble][P2]** De-bleed **Demucs** optionnel (`--debleed`, local, MIT) — expérimental, documenté.
- **#17 [ensemble][P2]** Blend multi-micros close/room (mix pondéré) au lieu d'un seul primaire.

## v1.0 — Pro / qualité projet

- **#18 [pro][P2]** CI GitHub Actions (lint + pytest) — fichier prêt (s'active avec un repo/remote).
- **#19 [pro][P1]** Couverture de tests étendue (reverb, batch, album, formats, pipeline e2e synthétique).
- **#20 [pro][P2]** Doc : profils détaillés + court guide de prise de son (bonnes pratiques violon).

---

### Hors-scope (respect « sans service payant »)
Cloud/SaaS (LANDR, eMastered…), plugins commerciaux (iZotope, Sonible, Waves). L'hébergement
VST3 reste une **option Windows** non requise. Aucune dépendance payante n'entrera dans le cœur.
