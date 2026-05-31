# Étude des outils (2025–2026) — synthèse vérifiée

Recherche multi‑sources, affirmations vérifiées de façon adversariale (votes 3‑0),
sources primaires (dépôts, PyPI, pages produit, norme EBU). Vérifié au **2026‑05‑31**.
Oriente la **pile hybride** du projet : cœur open‑source/local + matching + (option) VST3.

## TL;DR — pile retenue

| Étape | Outil | Licence | Scriptable | Local |
|---|---|---|---|---|
| Cœur DSP + effets + hôte VST3 | **pedalboard** 0.9.23 (Spotify) | GPLv3 | ✅ API NumPy | ✅ |
| Matching sur référence | **matchering** 2.0.6 (`mg.process`) | GPL‑3.0 | ✅ API/CLI | ✅ |
| Loudness EBU R128 (livraison) | **ffmpeg‑normalize** 1.37.8 / **pyloudnorm** | MIT | ✅ API/CLI | ✅ |
| IR de vraies salles (réverbe convolution) | **OpenAIR** (Univ. York) | CC (variable) | ⚠️ assets | ✅ |
| Séparation / dé‑bleed (option) | **Demucs** 4.0.1 (Meta) | MIT | ✅ API/CLI | ✅ |

## Mise en garde centrale (fortement étayée)

- **Les débruiteurs IA orientés voix dénaturent la musique.** *DeepFilterNet* (et HiFi‑GAN
  et consorts) sont **exclusivement** pour la parole ; la littérature évaluée par les pairs
  (Cadenza Challenge ICASSP 2024 ; ADNAC) montre qu'appliqués à de la musique ils
  « corrompent le contenu musical, ne retirent aucun bruit, ou suppriment le signal ».
  → **proscrits** en traitement direct des cordes. Le projet n'utilise QUE du débruitage
  **classique** (spectral, soustractif) et **opt‑in**.
- **iZotope Ozone / RX : aucune API/CLI/headless.** Automatisables uniquement en **hébergeant
  leur VST3** dans un hôte tiers (pedalboard ou DAW), **fiabilité à valider plugin par plugin**
  (un VST3 hébergé peut planter l'interpréteur ; le contrôle fin des paramètres n'est **pas**
  garanti — affirmation explicitement **réfutée**). Comme RX/Ozone n'ont pas de build **Linux**,
  ils ne tournent pas dans WSL2 → étape **côté Windows** si un jour nécessaires.

## Loudness — cibles classiques (EBU R128 s2, 2023)

- **‑23 LUFS** : baseline broadcast, la plus conservatrice (dynamique préservée).
- **‑20 à ‑16 LUFS** : fenêtre « distribution » si un niveau plus fort est voulu.
- Plateformes grand public : normalisent à **~‑14** (Spotify/YouTube) / **~‑16/‑14** (Apple/TIDAL).
  → Bonne pratique classique : **préserver la dynamique** à la cible de la plateforme plutôt que
  pousser le niveau. Pour les œuvres à mouvements : **normalisation album/anchor** (ancre = mouvement le plus fort).
- Choix d'implémentation DLZ : **gain linéaire plafonné true‑peak** (LRA intacte) par défaut ;
  `--limit`/`--ebu` disponibles si l'on accepte un compromis de dynamique.

## Caveats licences

- `pedalboard` **GPLv3** (bundle JUCE6 + SDK VST3) et `matchering` **GPL‑3.0** : copyleft →
  incompatibles avec une **distribution propriétaire** sans remplacement (hôte VST3 maison sous
  licence JUCE commerciale, etc.). Usage interne/personnel : OK.
- **OpenAIR** : « la plupart » des IR en Creative Commons mais **licences variables** (la présomption
  d'un CC BY 4.0 uniforme a été **réfutée**) → vérifier **item par item** avant usage commercial.

## Lacunes (non couvert / à approfondir)

- Catégorie restauration au‑delà de DeepFilterNet **non vérifiée** : iZotope RX 11, **Accentize
  dxRevive/SpectralBalance** (se revendiquent *musique* → à vérifier en priorité), Acon, Waves
  Clarity Vx, Supertone, CEDAR, Bertom, NVIDIA. Sonible (smart:EQ/smart:limit) non couvert.
- **Aucune mesure indépendante de qualité audio sur cordes** n'existe pour aucun outil. Le seul
  jugement fortement étayé est **négatif** (DeepFilterNet). → Le **null‑test/A‑B** du pipeline DLZ
  sert précisément à combler ce vide sur tes propres enregistrements.
- À évaluer : un modèle de débruitage/déréverbération entraîné **sur musique** (non‑voix),
  scriptable en Python.

## Sources clés

pedalboard — spotify.github.io/pedalboard · github.com/spotify/pedalboard ·
matchering — github.com/sergree/matchering · ffmpeg‑normalize — github.com/slhck/ffmpeg-normalize ·
Demucs — github.com/facebookresearch/demucs · DeepFilterNet — github.com/Rikorose/DeepFilterNet
(+ arXiv 2404.11116 Cadenza, arXiv 2511.01773 ADNAC) · EBU R128 s2 — tech.ebu.ch/docs/r/r128s2.pdf ·
OpenAIR — openair.hosted.york.ac.uk · Ozone — izotope.com/en/products/ozone.
