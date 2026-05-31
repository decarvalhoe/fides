"""Fides — pipeline d'auto-mastering transparent pour cordes classiques.

Chaîne : Ingest/Repair -> Analyze -> Plan -> Process -> Verify -> Output.
Philosophie : traitement minimal, soustractif, transparent ; ne pas dénaturer.
"""
try:
    from importlib.metadata import PackageNotFoundError, version
    try:
        __version__ = version("fides-mastering")
    except PackageNotFoundError:
        __version__ = "0.2.2"
except Exception:  # pragma: no cover
    __version__ = "0.2.2"
