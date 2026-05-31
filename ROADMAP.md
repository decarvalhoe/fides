# Roadmap — Fides

Objectif : un outil **robuste, simple, professionnel**, **100 % open-source / local**,
**sans aucun service payant**. Cordes classiques (violon solo, petites formations).

| Version | Thème | État |
|---|---|---|
| **v0.1** | MVP : analyse → plan → process surgical → loudness transparent → null-test → rapport → CLI → tests | fait |
| **v0.2** | **Robustesse** : entrées multi-formats, tout nb de canaux/mono/stéréo, validation & erreurs claires, logging, dry-run, garde-fous numériques | en cours |
| **v0.3** | **Qualité audio** : réverbe d'espace (algorithmique + convolution IR), de-harsh dynamique d'archet, déclip cubique, glue compressor optionnel | en cours |
| **v0.4** | **Workflow pro** : mode batch (dossier), normalisation **album/anchor**, A/B aligné en loudness, rapport **HTML**, packaging (`pyproject` + entry point `fides`) | en cours |
| **v0.5** | **Ensembles** (palier 2) : de-bleed **Demucs** (local, MIT) optionnel, blend multi-micros close/room | dépend deps |
| **v1.0** | **Pro** : CI, doc complète, profils enrichis, guide de prise de son, évaluation A/B systématique | à venir |

## Paliers d'installation (tous gratuits/locaux)

- **Palier 1** (fait) : numpy, scipy, soundfile, pyloudnorm, **pedalboard**, noisereduce, ffmpeg-normalize, **matchering**.
- **Palier 2** : **torch (CPU)** + **demucs** (de-bleed optionnel). GPU NVIDIA dispo (RTX 2060) si besoin, non requis.

## Principes directeurs

1. **Ne pas dénaturer** : traitement minimal, soustractif, plafonné, réversible, prouvé (null-test).
2. **Zéro service payant** : aucune API cloud, aucun plugin commercial requis. (Hébergement VST3 = option Windows hors-scope.)
3. **Simple** : une commande, des profils, des défauts sûrs. `fides IN.wav -o OUT/`.
4. **Pro** : batch, loudness album/anchor EBU R128 s2, rapports, packaging, tests, CI.
