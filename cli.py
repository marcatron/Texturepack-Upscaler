import os
import sys
import argparse
import time

from core.algorithms import AVAILABLE_ALGORITHMS
from core.processor import ResourcePackProcessor

def print_progress(current: int, total: int, filename: str, status: str):
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current // total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    # Truncate filename if too long
    fn = filename if len(filename) <= 25 else filename[:22] + "..."
    sys.stdout.write(f"\r[{bar}] {pct:5.1f}% | {fn:<28} | {status:<30}")
    sys.stdout.flush()

def run_cli(args=None):
    parser = argparse.ArgumentParser(
        description="Minecraft Resource Pack Upscaler - Skaliert Texturen verlustfrei und intelligent auf 32x / 48x / 64x hoch."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Pfad zum Quell-Ressourcenpaket (Ordner oder .zip Datei)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Pfad zum Ziel (Ordner oder .zip Datei). Standard: <input>_<scale>x"
    )
    parser.add_argument(
        "-a", "--algorithm",
        default="scale2x",
        choices=list(AVAILABLE_ALGORITHMS.keys()),
        help="Upscaling Algorithmus (Standard: scale2x)"
    )
    parser.add_argument(
        "-s", "--scale",
        type=int,
        default=None,
        help="Skalierungsfaktor (2, 3, 4). Wenn nicht angegeben, wird er vom Algorithmus bestimmt."
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=None,
        help="Anzahl paralleler CPU-Threads (Standard: Auto-Erkennung)"
    )

    parsed = parser.parse_args(args)

    input_path = os.path.abspath(parsed.input)
    if not os.path.exists(input_path):
        print(f"Fehler: Eingabepfad '{input_path}' existiert nicht!")
        sys.exit(1)

    algo = parsed.algorithm
    factor = parsed.scale or AVAILABLE_ALGORITHMS[algo]["factor"]

    output_path = parsed.output
    if not output_path:
        # Generate default output name
        base, ext = os.path.splitext(input_path)
        tag = f"_{factor * 16}x"
        if ext.lower() == ".zip":
            output_path = f"{base}{tag}.zip"
        else:
            output_path = f"{input_path}{tag}"

    print("=" * 70)
    print("Minecraft Texturepack Upscaler")
    print(f"Eingabe:       {input_path}")
    print(f"Ausgabe:       {output_path}")
    print(f"Algorithmus:   {AVAILABLE_ALGORITHMS[algo]['name']}")
    print(f"Zielauflösung: {factor * 16}x{factor * 16} ({factor}x Skalierung)")
    print("=" * 70)

    processor = ResourcePackProcessor(
        algorithm=algo,
        factor=factor,
        num_workers=parsed.workers,
        progress_callback=print_progress
    )

    try:
        stats = processor.process(input_path, output_path)
        print("\n" + "=" * 70)
        print("Erfolgreich abgeschlossen!")
        print(f"Dauer:                {stats.elapsed_seconds:.2f} Sekunden")
        print(f"Texturen skaliert:    {stats.upscaled_images}")
        print(f"Colormaps geschützt:  {stats.colormaps_preserved}")
        print(f"Dateien kopiert:      {stats.other_files_copied}")
        if stats.errors > 0:
            print(f"Warnungen/Fehler:     {stats.errors}")
        print(f"Gespeichert unter:    {stats.output_path}")
        print("=" * 70)
    except KeyboardInterrupt:
        print("\nVorgang durch Benutzer abgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFehler beim Verarbeiten: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_cli()
