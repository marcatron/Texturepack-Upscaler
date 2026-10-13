import sys
import os

# Ensure the project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    # If command line arguments were provided (e.g. -i, -o, -h, --cli), run CLI
    if len(sys.argv) > 1 and sys.argv[1] not in ["--gui"]:
        from cli import run_cli
        run_cli()
    else:
        from gui import launch_gui
        launch_gui()

if __name__ == "__main__":
    main()
