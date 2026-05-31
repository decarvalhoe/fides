# Guide de prise de son — violon / petites formations

Le traitement DLZ est **transparent** : il corrige et met au niveau, il ne *sauve* pas
une mauvaise prise. La qualité du master dépend d'abord de la captation. Conseils
concis pour des prises qui exploitent au mieux le pipeline.

## Format
- **48 kHz / 24-bit** minimum (96 kHz possible). Le 24-bit donne ~20 dB de marge de
  headroom : enregistrez **avec de la réserve**.
- Visez des **crêtes vers −12 à −6 dBFS**. Ne jamais toucher 0 dBFS (l'écrêtage est
  irréversible — voir `REC_0001` : la voie principale écrêtée a été écartée au profit
  d'une copie propre).

## Micros & placement (violon)
- **Petite/grande membrane à condensateur**, directivité cardioïde ou omni.
- **Distance** : 1 à 2 m, légèrement **au-dessus et devant** l'instrument (vers la
  table/ouïes), pas braqué sur le chevalet (→ dureté d'archet 2–6 kHz).
- Trop près = nasillard/agressif ; trop loin = noyé dans la pièce. Cherchez le point
  où le timbre est **rond et détaillé**.
- **Pièce** : une acoustique agréable vaut mieux qu'une réverbe ajoutée. Si la salle
  sonne bien, un **couple** (ORTF/paire espacée) capte un stéréo naturel.

## Multi-micros / formation
- **Micro proche** (définition) + **couple d'ambiance** (espace) : le pipeline peut
  les **mélanger** (`--blend CH --blend-gain -6`).
- Étiquetez/repérez les voies. Le système détecte automatiquement les canaux
  **vides / dupliqués / corrélés** et choisit la meilleure voie porteuse.

## Pièges courants (que le pipeline signale)
- **Écrêtage** (clip) : baissez le gain d'entrée. Le rapport liste les séries de
  pleine échelle.
- **Ronflette 50 Hz** (secteur EU) : éloignez les alimentations, vérifiez les masses.
  Détectée et notchée automatiquement si > seuil.
- **Souffle** : un préampli propre vaut mieux qu'un débruitage. Le débruitage est
  **opt-in** (`--denoise`) et reste doux.
- **Son mat / sans air** : souvent micro sombre ou trop loin ; le pipeline restaure
  l'air (high-shelf plafonné) mais une bonne capture limite le besoin.

## Livraison
- Cible par défaut **−16 LUFS / −1 dBTP**, **dynamique préservée** (gain linéaire).
  Pour des œuvres à mouvements, utilisez le **mode batch** (`--batch`) : normalisation
  **album/anchor** (même gain pour toutes les prises → rapports de nuances respectés).
- Écoutez toujours `null_residual.wav` (ce que le traitement a changé) et l'A/B
  `original_match.wav` (original au niveau du master) avant de valider.
