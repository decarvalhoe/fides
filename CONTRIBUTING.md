# Contribuer à Fides

Fides est un outil d'auto-mastering **transparent** pour violon solo et petites
formations classiques. Issues et PR bienvenues.

## Développement
```bash
git clone https://github.com/decarvalhoe/fides.git && cd fides
python -m venv .venv && source .venv/bin/activate   # ffmpeg requis dans le PATH
pip install -e ".[dev,match]"
pytest
```

## Principes (à respecter dans toute contribution)
- **Ne pas dénaturer** : tout traitement reste minimal, plafonné et **prouvable**
  (null-test). Une nouvelle correction = un garde-fou + un test.
- **Zéro service payant** : aucune dépendance cloud/commerciale dans le cœur.
- **Transparent par défaut** : les traitements marquants (débruitage, glue, reverb)
  restent opt-in.

## Tests & CI
- `pytest` (suite dans `tests/`). La CI tourne sur **Python 3.10–3.12**.
- Couvrir les nouveautés : I/O, analyse, process (loudness/true-peak), pipeline, IR.

## Release (mainteneur)
1. Bump `version` dans `pyproject.toml` + entrée `CHANGELOG.md`.
2. Créer une **release GitHub** (tag `vX.Y.Z`).
3. La GitHub Action `publish.yml` publie sur PyPI via **trusted publishing**
   (OIDC, sans token — configurer le « pending publisher » sur PyPI une fois).
