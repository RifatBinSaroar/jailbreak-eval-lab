"""Python-only import, validation and website export commands."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .core import ROOT, export_web, ingest, validate_registry
from .inputs import InputError, read_rows, strict_json


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_json(path, data):
    """Replace one complete JSON artifact atomically on its destination filesystem."""
    path = Path(path)
    payload = encode(data)  # Serialize before opening any output.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def destinations(paths, inputs, replace):
    targets = [Path(p).resolve() for p in paths if p]
    if len(set(targets)) != len(targets):
        raise InputError("Output paths must be different from each other")
    for target in targets:
        if target in {Path(p).resolve() for p in inputs}:
            raise InputError("An output path cannot overwrite an input")
        if target.exists() and (not replace or not target.is_file()):
            raise InputError(f"Output already exists: {target}. Use --replace to rebuild it.")
    return targets


def parser():
    result = argparse.ArgumentParser(description="Import literature without inventing paper details. No npm needed.")
    commands = result.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import", help="Rebuild a complete registry from Excel or structured notes")
    imp.add_argument("sources", nargs="+", help=".xlsx, .csv, .tsv, .json or .jsonl files")
    imp.add_argument("--notes", help="JSON/JSONL notes keyed by paper_id; applied after intake")
    imp.add_argument("--sheet", help="Read only this Excel sheet (otherwise detect paper sheets)")
    imp.add_argument("--header-row", type=int, default=1, help="1-based heading row (default: 1)")
    imp.add_argument("--output", default=str(ROOT / "literature/registry.json"))
    imp.add_argument("--web-output", default=str(ROOT / "apps/web/public/data/literature.json"))
    imp.add_argument("--report", default=str(ROOT / "literature/import_report.json"))
    imp.add_argument("--replace", action="store_true", help="Explicitly rebuild existing outputs")
    imp.add_argument("--fail-on-duplicates", action="store_true", help="Block publication when duplicate candidates exist")
    val = commands.add_parser("validate", help="Check registry structure, provenance and review metadata")
    val.add_argument("registry", nargs="?", default=str(ROOT / "literature/registry.json"))
    val.add_argument("--fail-on-duplicates", action="store_true")
    exp = commands.add_parser("export", help="Validate and regenerate website JSON from a canonical registry")
    exp.add_argument("registry", nargs="?", default=str(ROOT / "literature/registry.json"))
    exp.add_argument("--output", default=str(ROOT / "apps/web/public/data/literature.json"))
    exp.add_argument("--replace", action="store_true")
    exp.add_argument("--fail-on-duplicates", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    report = {"ok": False, "errors": [], "notices": []}
    report_ready = False
    try:
        if args.command == "import":
            if args.notes and Path(args.notes).suffix.casefold() not in {".json", ".jsonl"}:
                raise InputError("--notes must be .json or .jsonl")
            inputs = args.sources + ([args.notes] if args.notes else [])
            destinations([args.output, args.web_output, args.report], inputs, args.replace)
            report_ready = True
            rows = []
            for source in args.sources:
                data, notices = read_rows(source, args.sheet, args.header_row)
                rows.extend(data)
                report["notices"].extend(notices)
            notes = read_rows(args.notes)[0] if args.notes else []
            registry = ingest(rows, notes)
        else:
            registry = strict_json(Path(args.registry).read_text(encoding="utf-8"))
            errors = validate_registry(registry)
            if errors:
                raise InputError("Validation failed:\n" + "\n".join(errors))
        report["duplicate_candidates"] = registry["duplicate_candidates"]
        if args.fail_on_duplicates and registry["duplicate_candidates"]:
            raise InputError("Duplicate candidates found. Review the report; no papers were merged.")
        if args.command == "import":
            web = export_web(registry)
            report.update({"ok": True, "summary": web["summary"],
                           "incomplete_fields": {r["paper_id"]: r["missing_fields"] for r in registry["records"]},
                           "warnings": {r["paper_id"]: r["warnings"] for r in registry["records"] if r["warnings"]}})
            write_json(args.output, registry)
            write_json(args.web_output, web)
            write_json(args.report, report)
            print(f"Imported {len(registry['records'])} paper rows.")
            print(f"Registry: {args.output}\nWebsite JSON: {args.web_output}\nReport: {args.report}")
            for notice in report["notices"]:
                print(notice)
            print(f"Incomplete papers: {web['summary']['incomplete_papers']}; duplicate groups: {len(registry['duplicate_candidates'])}.")
            print("Review labels describe recorded human review; this command does not verify paper claims.")
        elif args.command == "export":
            destinations([args.output], [args.registry], args.replace)
            write_json(args.output, export_web(registry))
            print(f"Exported {len(registry['records'])} paper rows to {args.output}")
        else:
            print(f"Valid registry: {len(registry['records'])} paper rows; {len(registry['duplicate_candidates'])} duplicate groups.")
        return 0
    except (InputError, OSError, ValueError, ImportError) as exc:
        report["ok"] = False
        report["errors"].append(str(exc))
        if report_ready:
            try:
                write_json(args.report, report)
            except OSError as report_error:
                print(f"Could not write report: {report_error}", file=sys.stderr)
        print(f"Error: {exc}", file=sys.stderr)
        return 2
