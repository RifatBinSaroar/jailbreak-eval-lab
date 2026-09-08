"""Compare research records to an existing local Git commit, without network I/O."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from jailbreak_eval.registry import REGISTRIES, load_registries, validate_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="full local base commit SHA")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", args.base):
        parser.error("--base must be a full commit SHA")
    subprocess.run(["git", "cat-file", "-e", f"{args.base}^{{commit}}"], check=True)
    paths = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", args.base], text=True).splitlines())
    registry_paths = {f"registries/{name}.json" for name in REGISTRIES}
    present = registry_paths & paths
    if present and present != registry_paths:
        parser.error("base commit contains an incomplete canonical registry set")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in REGISTRIES:
            path = f"registries/{name}.json"
            content = (subprocess.check_output(["git", "show", f"{args.base}:{path}"], text=True)
                       if present else json.dumps({"schema_version": "1.0.0", "registry": name, "records": []}))
            (root / f"{name}.json").write_text(content, encoding="utf-8")
        validate_history(load_registries(), load_registries(root))
    print("Registry history is append-only relative to the base commit.")


if __name__ == "__main__":
    main()
