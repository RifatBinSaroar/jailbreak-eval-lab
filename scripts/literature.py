"""Run the literature workflow from a Git checkout; Node/npm is not needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jailbreak_eval.literature.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
