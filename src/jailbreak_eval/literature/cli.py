"""Import cells or explicit curator revisions into canonical papers."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from .core import import_rows, review_notes, duplicate_candidates
from .inputs import read_rows, strict_json
from ..registry import latest_records, load_registries


def read_notes(path):
    path = Path(path)
    if path.suffix.lower() == '.jsonl':
        return [strict_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return strict_json(path.read_text(encoding='utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import')
    imp.add_argument('sources', nargs='+')
    imp.add_argument('--notes', help='Explicit canonical curator revisions in JSON; see quickstart')
    imp.add_argument('--sheet')
    imp.add_argument('--header-row', type=int, default=1)
    imp.add_argument('--timestamp', default=None)
    imp.add_argument('--project-root', default='.')
    imp.add_argument('--fail-on-duplicates', action='store_true')
    review = sub.add_parser('review')
    review.add_argument('notes')
    check = sub.add_parser('validate')
    for command in (imp, review, check):
        command.add_argument('--directory', default='registries')
    args = parser.parse_args(argv)
    try:
        if args.command == 'import':
            rows = []
            for path in args.sources:
                part, notices = read_rows(path, args.sheet, args.header_row)
                rows.extend(part)
                for notice in notices: print(notice)
            notes = read_notes(args.notes) if args.notes else []
            timestamp = args.timestamp or datetime.now(timezone.utc).isoformat()
            result = import_rows(rows, args.directory, args.project_root, timestamp, notes, args.fail_on_duplicates)
            print(f"Imported {len(result['imported_ids'])} paper rows. Duplicate candidate groups: {len(result['duplicate_candidates'])}.")
            for paper_id in result['imported_ids']: print(paper_id)
            for warning in result['warnings']: print(warning)
        elif args.command == 'review':
            review_notes(read_notes(args.notes), args.directory)
            print('Appended source-linked paper revisions under the same stable IDs.')
        else:
            records = latest_records(load_registries(args.directory))
            print(f"Valid: {len(records['papers'])} papers; {len(duplicate_candidates(records['papers']))} duplicate candidate groups.")
        print('Rebuild all dashboard data: python scripts/research.py build-web')
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
