"""Check every local Git revision plus working files; no network or execution."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jailbreak_eval.registry import REGISTRIES, load_registries, validate_history, validate_registries


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def records_at(sha):
    paths=set(git('ls-tree','-r','--name-only',sha).splitlines())
    expected={f'registries/{n}.json' for n in REGISTRIES}
    present=paths & expected
    if present and present!=expected:raise ValueError(f'{sha}: incomplete canonical registry set')
    envelopes={n:json.loads(git('show',f'{sha}:registries/{n}.json')) if present else
               {'schema_version':'1.0.0','registry':n,'records':[]} for n in REGISTRIES}
    return validate_registries(envelopes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True,help='full local base commit SHA')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}',args.base):parser.error('--base must be a full commit SHA')
    try:
        git('cat-file','-e',f'{args.base}^{{commit}}')
        subprocess.run(['git','merge-base','--is-ancestor',args.base,'HEAD'],check=True)
        commits=git('rev-list','--reverse',f'{args.base}..HEAD').splitlines()
        cache={}
        def at(sha):
            if sha not in cache:cache[sha]=records_at(sha)
            return cache[sha]
        for sha in commits:
            current=at(sha)
            for parent in git('show','-s','--format=%P',sha).split():
                validate_history(current,at(parent))
        current=load_registries()
        validate_history(current,at(git('rev-parse','HEAD')))
        validate_history(current,at(args.base))
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        parser.exit(1,f'Registry history check failed: {exc}\n')
    print(f'All {len(commits)} intervening commits and working records preserve immutable revisions and stable-ID updates.')

if __name__=='__main__':main()
