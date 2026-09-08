"""No-install CLI for offline run recording and result export."""

import argparse
import sys

from .contracts import ContractError
from .runs import read_inputs, rebuild_web, record_run, verify_run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record and analyze existing evaluator decisions. No model or payload execution.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("validate", "Validate a proposed run without writing files"),
                            ("record", "Save immutable inputs and derived results")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--manifest", required=True)
        command.add_argument("--dataset", required=True)
        command.add_argument("--predictions", required=True)
        command.add_argument("--labels", required=True)
        if name == "record":
            command.add_argument("--runs-dir", default="results/runs")
    verify = commands.add_parser("verify", help="Verify checksums and reproduce every metric/error")
    verify.add_argument("run_directory")
    web = commands.add_parser("rebuild-web", help="Reproduce and export aggregate website JSON")
    web.add_argument("--runs-dir", default="results/runs")
    web.add_argument("--output", default="apps/web/data/results.json")
    web.add_argument("--include-synthetic", action="store_true", help="Explicit test/demo export only; records stay marked synthetic")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            manifest, _, cases, predictions, labels = read_inputs(args.manifest, args.dataset, args.predictions, args.labels)
            print(f"Valid {manifest['run_id']}: {len(cases)} cases, {len(predictions)} predictions, {len(labels)} reference rows")
        elif args.command == "record":
            print(record_run(args.manifest, args.dataset, args.predictions, args.labels, args.runs_dir))
        elif args.command == "verify":
            manifest, _, _ = verify_run(args.run_directory)
            print(f"Verified {manifest['run_id']}: all inputs, metrics, and errors reproduce")
        else:
            result = rebuild_web(args.runs_dir, args.output, args.include_synthetic)
            print(f"Wrote {args.output}: {result['research_run_count']} research runs, {result['synthetic_run_count']} synthetic runs")
    except (ContractError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
