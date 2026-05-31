# DLZ Mastering

Auto‑mastering **transparent** pour **violon solo et petites formations classiques**
(quatuor à cordes, musique de chambre). Le logiciel analyse l'enregistrement, décide
une chaîne de traitement minimale et soustractive, l'applique, puis **prouve** sa
transparence (null‑test, A/B, mesures EBU R128). Objectif : *capitaliser sur les
meilleures pratiques studio sans dénaturer le son original.*

> Pile hybride open‑source / local (cf. [`RESEARCH.md`](RESEARCH.md)) :
> **pedalboard** (DSP) · **pyloudnorm**/**ffmpeg‑normalize** (loudness EBU R128) ·
> **matchering** (matching sur référence, optionnel) · IR de vraies salles **OpenAIR**.
> Runtime : **WSL2 / Ubuntu** (Linux‑first ; GPU NVIDIA dispo mais non requis).

## Philosophie « ne pas dénaturer »

- Traitement **minimal, soustractif, plafonné** (chaque correction est bornée).
- **Aucun débruiteur IA orienté voix** (DeepFilterNet, etc.) : ils détruisent le timbre
  des cordes (preuves dans `RESEARCH.md`). Le débruitage est **classique** et **opt‑in**.
- **Loudness par gain linéaire** plafonné true‑peak → **dynamique (LRA) intacte**.
- **Garde‑fous fournis à chaque rendu** : `null_residual.wav` (ce qui a été ajouté/retiré),
  `_pre_master.wav` (nettoyé sans loudness, pour l'A/B), rapport détaillé des décisions.

## Architecture (pipeline)

```
Ingest/Repair → Analyze → Plan → Process → Verify → Output
   io_wav        analyze    plan    process   verify   report
   lecture       stats/     chaîne  HP·dehum  LUFS/    master + stems
   tolérante     rôles/     + params ·EQ·     true-pk  + null + report
   (tronqué)     bruit/clip          loudness null-test (json/md)
```

| Module | Rôle |
|---|---|
| `dlz/io_wav.py` | Lecture multicanal 24‑bit robuste (fichiers à en‑tête **tronqué**), repair RIFF, écriture |
| `dlz/io_util.py` | Chargement multi‑formats (soundfile + repli **ffmpeg** pour M4A/AAC…) |
| `dlz/analyze.py` | Stats/canal, classification (actif/silence/**duplicata**), bruit, **clip**, hum 50 Hz, tonal |
| `dlz/plan.py` | Décide la chaîne + paramètres (plafonnés) depuis l'analyse + profil |
| `dlz/process.py` | DC, déclip, de‑hum (notch), débruitage doux (opt‑in), EQ (pedalboard), loudness |
| `dlz/reference.py` | Profils JSON + matching sur référence (matchering, optionnel) |
| `dlz/verify.py` | Mesures LUFS/true‑peak (pyloudnorm) + **null‑test** |
| `dlz/report.py` | Rapport JSON + Markdown |
| `dlz/batch.py` | Traitement par lot + normalisation **album/anchor** (EBU R128 s2) |
| `dlz/debleed.py` | De‑bleed **expérimental** via Demucs (palier 2, ensembles) |
| `dlz/pipeline.py` / `cli.py` | Orchestration + CLI |

## Installation (WSL2 / Ubuntu)

```bash
# depuis WSL (Ubuntu)
bash /mnt/c/Dev/dlz-mastering/scripts/provision.sh   # crée ~/dlz/.venv + installe la pile
source ~/dlz/.venv/bin/activate
```

Pré‑requis présents par défaut sous Ubuntu‑WSL : `python3`, `ffmpeg`. La pile Python
(numpy, scipy, soundfile, pyloudnorm, pedalboard, noisereduce, ffmpeg‑normalize,
matchering) est installée par `scripts/provision.sh` (sans sudo).

## Usage

```bash
# traitement par défaut (transparent : pas de débruitage, loudness linéaire)
python -m dlz.cli ~/dlz/in/REC_0001.wav -o ~/dlz/out/REC_0001 -p violin_solo

# options
python -m dlz.cli IN.wav -o OUT/ \
    -p string_quartet \          # profil
    -t -18 \                     # cible LUFS (sinon valeur du profil)
    --denoise \                  # active le débruitage doux (off par défaut)
    --limit \                    # limiteur doux pour atteindre la cible (sinon gain linéaire)
    --ebu \                      # loudness via ffmpeg-normalize EBU R128 (peut compresser)
    --reference REF.wav \        # matching sur une référence (matchering)
    --reverb 0.2 \               # réverbe d'espace subtile (ou --ir IR.wav pour convolution)
    --deharsh --glue \           # de-harsh dynamique d'archet ; léger glue compressor
    --blend 5 --blend-gain -6 \  # multipiste : ajoute le canal 5 (ambiance) au master
    --no-stems

# mode batch (dossier de prises) + normalisation album/anchor
python -m dlz.cli /chemin/prises -o OUT/ --batch -p string_quartet

# dry-run (analyse + plan, sans rendu) · liste des profils · entry point packagé
python -m dlz.cli IN.wav -o OUT/ --dry-run
python -m dlz.cli --list-profiles
pip install -e . && dlz IN.wav -o OUT/        # commande `dlz` après installation

# format plein : session COMPLÈTE multicanal traitée, 32-bit float, SR d'origine
dlz IN.wav -o OUT/ --full                      # -> full_processed.wav (tous les canaux, float)
dlz IN.wav -o OUT/ --bit-depth 32f             # master/stems en 32-bit float (sans perte)
```

### Sorties (`OUT/`)

| Fichier | Contenu |
|---|---|
| `master.wav` | **Livrable** (24‑bit, loudness/true‑peak normalisés) |
| `_pre_master.wav` | Nettoyé **sans** loudness — pour l'A/B vs original |
| `null_residual.wav` | **Différence** traité−original alignée en gain (« ce qu'on a changé ») |
| `stems/chNN_clean.wav` | Stems nettoyés par canal actif unique |
| `full_processed.wav` | **Format plein** (`--full`) : session complète multicanal traitée, pleine résolution (32f) |
| `report.json` / `report.md` | Analyse, plan, mesures, garde‑fous |

## Choix du canal « primaire »

Pour un multipiste, le master est dérivé du **meilleur canal porteur** (score = SNR,
pénalités fortes sur l'écrêtage et le 0 dBFS). Ex. sur `REC_0001` (14 canaux), le
système écarte la voie principale **écrêtée** (ch2, 1021 séries de pleine échelle) et
choisit **ch12**, copie propre 12 dB plus bas du même contenu. Override manuel : `--primary N`.

## Limitations connues / feuille de route

- Choix du primaire automatique (override `--primary N` disponible).
- Réverbe à convolution (pedalboard.Convolution + IR OpenAIR) : **câblée mais non activée** par défaut.
- Pas encore : normalisation **album/anchor** multi‑prises (EBU R128 s2), de‑esser dynamique
  d'archet, hébergement de VST3 commerciaux (Windows‑side, cf. `RESEARCH.md`).
- Le déclip est une interpolation simple (suffisant en secours ; pas un restaurateur dédié).

## Licences

`pedalboard` (GPLv3) et `matchering` (GPL‑3.0) : **copyleft**. Usage interne/personnel
sans souci ; une **distribution propriétaire** nécessiterait des alternatives non‑GPL
(cf. `RESEARCH.md`, questions ouvertes). Le reste de la pile est permissif.
