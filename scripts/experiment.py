"""Run from a Git checkout with Python 3.10+; no pip or npm required."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jailbreak_eval.experiments.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
