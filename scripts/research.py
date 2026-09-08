"""Simple entry point for the ONE canonical data build."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jailbreak_eval.registry import write_web, load_registries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build-web', 'validate'])
    parser.add_argument('--directory', default='registries')
    parser.add_argument('--output', default='apps/web/data/research.json')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--include-synthetic', action='store_true', help='Explicit synthetic preview, never production findings')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            r=load_registries(args.directory)
            print(f'Validated all nine registries; {sum(map(len,r.values()))} immutable revisions.')
        else:
            r=write_web(args.directory,args.output,artifact_root=args.project_root,include_synthetic=args.include_synthetic)
            print(f"Built {args.output}: {r['readiness']['papers']} papers, {r['readiness']['experiments']} experiments, {r['readiness']['measured_results']} aggregate results.")
    except (ValueError,OSError) as exc:
        parser.exit(1,f'Error: {exc}\n')

if __name__ == '__main__': main()
