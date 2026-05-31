"""Interface en ligne de commande du pipeline Fides."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, pipeline, reference


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="fides",
        description="Auto-mastering transparent pour violon solo / petites formations classiques.")
    ap.add_argument("--version", action="version", version=f"Fides {__version__}")
    ap.add_argument("input", nargs="?", help="fichier audio d'entrée (WAV/FLAC/AIFF/MP3/M4A…, multicanal OK)")
    ap.add_argument("-o", "--outdir", help="dossier de sortie")
    ap.add_argument("-p", "--profile", default="violin_solo", help="profil (défaut: violin_solo)")
    ap.add_argument("-r", "--reference", default=None, help="WAV de référence (matchering)")
    ap.add_argument("--primary", type=int, default=None, help="forcer le canal primaire (index)")
    ap.add_argument("-t", "--target-lufs", type=float, default=None, help="cible LUFS (sinon profil)")
    ap.add_argument("--limit", action="store_true", help="limiteur doux pour atteindre la cible")
    ap.add_argument("--ebu", action="store_true", help="loudness via ffmpeg-normalize EBU (peut compresser)")
    ap.add_argument("--denoise", action="store_true", help="débruitage doux (off par défaut)")
    ap.add_argument("--deharsh", action="store_true", help="de-harsh dynamique d'archet (2–6 kHz)")
    ap.add_argument("--glue", action="store_true", help="compresseur doux program-dependent (off par défaut)")
    ap.add_argument("--reverb", nargs="?", type=float, const=0.2, default=None,
                    metavar="AMOUNT", help="réverbe d'espace 0..1 (défaut 0.2 si flag nu)")
    ap.add_argument("--ir", default=None,
                    help="IR de convolution : preset (hall/room/chamber) ou chemin WAV")
    ap.add_argument("--dry-run", action="store_true", help="analyse + plan seulement (pas de rendu)")
    ap.add_argument("--batch", action="store_true", help="traiter un DOSSIER de prises (input = dossier)")
    ap.add_argument("--no-album", action="store_true", help="désactive la normalisation album/anchor en batch")
    ap.add_argument("--blend", action="append", type=int, default=None, metavar="CH",
                    help="multipiste : ajouter le canal CH (ex. ambiance) au master (répétable)")
    ap.add_argument("--blend-gain", type=float, default=-6.0, metavar="DB",
                    help="gain des canaux --blend (défaut -6 dB)")
    ap.add_argument("--debleed", action="store_true",
                    help="[expérimental] isole les cordes via Demucs avant traitement")
    ap.add_argument("--full", action="store_true",
                    help="exporte la SESSION COMPLÈTE traitée (tous les canaux) en un fichier multicanal")
    ap.add_argument("--bit-depth", choices=["24", "32", "32f"], default=None,
                    help="profondeur de sortie : 24=PCM24 (défaut), 32=PCM32, 32f=float (défaut si --full)")
    ap.add_argument("--no-stems", action="store_true", help="ne pas écrire les stems")
    ap.add_argument("--list-profiles", action="store_true", help="liste les profils et quitte")
    ap.add_argument("-v", "--verbose", action="store_true", help="logs détaillés")
    ap.add_argument("-q", "--quiet", action="store_true", help="silencieux (erreurs seulement)")
    args = ap.parse_args(argv)

    import logging
    import warnings
    warnings.filterwarnings("ignore")
    level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    blend = [(ch, args.blend_gain) for ch in (args.blend or [])]

    if args.list_profiles:
        print("\n".join(reference.list_profiles()))
        return 0
    if not args.input or not args.outdir:
        ap.error("input et --outdir requis (ou --list-profiles)")

    if args.batch:
        try:
            from . import batch
            summary = batch.run_batch(
                args.input, args.outdir, args.profile, album=not args.no_album,
                target_lufs=args.target_lufs, make_stems=not args.no_stems,
                denoise=args.denoise, reverb=args.reverb, ir=args.ir,
                glue=args.glue, deharsh_dyn=args.deharsh, blend=blend,
                full=args.full, bit_depth=args.bit_depth)
        except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError, OSError) as e:
            print(f"Erreur : {e}", file=sys.stderr)
            return 2
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    try:
        rep = pipeline.run(
            args.input, args.outdir, args.profile, args.reference,
            make_stems=not args.no_stems, limit=args.limit, ebu=args.ebu,
            target_lufs=args.target_lufs, denoise=args.denoise, primary=args.primary,
            reverb=args.reverb, ir=args.ir, glue=args.glue, deharsh_dyn=args.deharsh,
            dry_run=args.dry_run, blend=blend, debleed=args.debleed,
            full=args.full, bit_depth=args.bit_depth)
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    print(json.dumps(rep["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
