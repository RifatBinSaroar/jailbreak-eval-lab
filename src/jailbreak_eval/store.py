"""Append canonical revisions with validation and rollback on local write errors."""

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile

from .registry import REGISTRIES, load_registries, require, validate_history, validate_registries


def envelopes(records):
    return {n: {"schema_version": "1.0.0", "registry": n, "records": records[n]} for n in REGISTRIES}


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


@contextmanager
def write_lock(directory):
    directory = Path(directory).resolve()
    directory.parent.mkdir(parents=True, exist_ok=True)
    lock = directory.parent / ("." + directory.name + "-write.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError(f"Registry write already in progress: {lock}") from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def append_records(previous, additions):
    current = deepcopy(previous)
    for name in REGISTRIES:
        for row in additions.get(name, []):
            old = next((r for r in current[name] if (r["id"], r["version"]) == (row["id"], row["version"])), None)
            require(old is None or old == row, f"{row['id']}: unversioned change; append a new version")
            if old is None:
                current[name].append(deepcopy(row))
    validate_registries(envelopes(current))
    validate_history(current, previous)
    return current


def save_records(directory, current, previous=None):
    """Caller holds write_lock. Stage the whole directory, then swap with rollback.

    A process/OS crash can leave a .*-backup directory. Keep it and restore it
    before retrying; a missing canonical directory fails closed on every reader.
    """
    root = Path(directory).resolve()
    validate_registries(envelopes(current))
    if previous is not None:
        validate_history(current, previous)
        require(load_registries(root) == previous, "Registries changed during the operation; retry")
    stage = Path(tempfile.mkdtemp(prefix=f".{root.name}-stage-", dir=root.parent))
    backup = root.parent / f".{root.name}-backup"
    require(not backup.exists(), f"Restore or inspect interrupted transaction: {backup}")
    try:
        if root.exists():
            shutil.copytree(root, stage, dirs_exist_ok=True)
        for name, envelope in envelopes(current).items():
            (stage / f"{name}.json").write_bytes(encode(envelope))
        if root.exists():
            root.rename(backup)
        try:
            stage.rename(root)
        except BaseException:
            if backup.exists():
                backup.rename(root)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
