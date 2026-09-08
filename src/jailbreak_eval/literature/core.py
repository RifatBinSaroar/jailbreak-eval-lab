"""Canonical records, conservative identity matching and evidence checks."""

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .inputs import InputError, key

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "literature" / "paper_schema.json"
MISSING = {"", "unknown", "not reported", "not yet checked", "tbd", "n/a", "?", "-"}
STATUSES = ("unreviewed", "screened", "deep-reviewed", "verified")
ALIASES = {
    "paper": "title", "papertitle": "title", "venue": "venue_or_arxiv",
    "paperurl": "url", "paperlink": "url", "link": "url",
    "evaluationmetric": "metrics", "myunderstnding": "our_interpretation",
    "myunderstanding": "our_interpretation", "questions": "open_questions",
}
INTERNAL = {"sources", "missing_fields", "warnings"}
URL_RE = re.compile(r"https?://[^\s<>\"\[\]]+", re.I)
HYPERLINK = re.compile(r'^=HYPERLINK\(\s*"((?:[^"]|"")*)"\s*[,;]\s*"((?:[^"]|"")*)"\s*\)$', re.I)


def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def absent(value):
    return value is None or value == [] or (isinstance(value, str) and value.strip().casefold() in MISSING)


def is_url(value):
    if not isinstance(value, str) or re.search(r"\s", value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username
    except ValueError:
        return False


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def links_in(value):
    return sorted({link for text in strings(value) for link in URL_RE.findall(text)
                   if is_url(link)})


def doi(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if is_url(text):
        parsed = urlsplit(text)
        if parsed.hostname.casefold() not in {"doi.org", "dx.doi.org"}:
            return None
        text = parsed.path.lstrip("/")
    text = unquote(text)
    text = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.I)
    return text.casefold() if re.fullmatch(r"10\.\d{4,9}/\S+", text, re.I) else None


def arxiv(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if is_url(text):
        parsed = urlsplit(text)
        if parsed.hostname.casefold() not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            return None
        text = re.sub(r"^/(?:abs|pdf)/", "", unquote(parsed.path), flags=re.I)
    text = re.sub(r"^arxiv:\s*", "", text, flags=re.I)
    text = re.sub(r"\.pdf$", "", text, flags=re.I)
    if re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", text, re.I):
        return re.sub(r"v\d+$", "", text, flags=re.I).casefold()
    return None


def title_key(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value or "").casefold() if c.isalnum())


def convert(field, value, spec):
    if absent(value):
        return None
    if field == "year":
        if isinstance(value, bool):
            raise InputError("year must be an integer, not a boolean")
        if isinstance(value, (int, float)) and int(value) == value:
            return int(value)
        if isinstance(value, str) and re.fullmatch(r"\d{4}", value.strip()):
            return int(value)
        raise InputError(f"Invalid year: {value!r}; leave unknown years blank")
    if field == "executes_code":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().casefold() in {"yes", "no", "true", "false"}:
            return value.strip().casefold() in {"yes", "true"}
        raise InputError("executes_code must be yes/no, true/false, or blank")
    if field == "review":
        if isinstance(value, str):
            from .inputs import strict_json
            value = strict_json(value)
        if not isinstance(value, dict):
            raise InputError("review must be a JSON object")
        return value
    if "array" in spec.get("type", []):
        if isinstance(value, str):
            if value.lstrip().startswith("["):
                from .inputs import strict_json
                value = strict_json(value)
            else:
                value = [part.strip() for part in re.split(r"[;\n]", value) if part.strip()]
        if not isinstance(value, list) or any(not isinstance(v, str) or absent(v) for v in value):
            raise InputError(f"{field} must be a list of nonblank, known strings; leave unknown lists blank")
        return value
    if not isinstance(value, str):
        raise InputError(f"{field} must be text")
    value = value.strip()
    if field == "novelty_threat":
        return value.upper()
    if field == "evidence_status":
        return value.casefold().replace("_", "-")
    return value


def mapped(source, spec):
    """Copy only explicit canonical/approved alias values; retain everything raw."""
    lookup = {key(f): f for f in spec["properties"] if f not in INTERNAL}
    values, warnings, source_links = {}, [], set()
    for column in source["columns"]:
        name, value = column["header"], column["value"]
        field = ALIASES.get(key(name), lookup.get(key(name)))
        source_links.update(links_in(value))
        if column["hyperlink"]:
            if is_url(column["hyperlink"]):
                source_links.add(column["hyperlink"])
            else:
                warnings.append(f"Non-web hyperlink retained only in source cell {column['cell']}")
        hyperlink = column["hyperlink"]
        if column["is_formula"]:
            match = HYPERLINK.fullmatch(value or "")
            if match:
                hyperlink, value = (part.replace('""', '"') for part in match.groups())
                if is_url(hyperlink):
                    source_links.add(hyperlink)
            else:
                warnings.append(f"Formula not evaluated at {column['cell']}; canonical value remains missing")
                value = None
        if field:
            new = convert(field, value, spec["properties"][field])
            if field in values and values[field] != new:
                raise InputError(f"Conflicting columns for {field} in row {source['row']}")
            values[field] = new
        if field in {"title", "url"} and hyperlink and is_url(hyperlink):
            if not values.get("url"):
                values["url"] = hyperlink
            elif values["url"] != hyperlink:
                warnings.append("Multiple paper links retained in source_links")
        if field is None and not absent(value):
            warnings.append(f"Original column {name!r} preserved without research interpretation")
    for field, resolver, prefix in (("doi", doi, "https://doi.org/"), ("arxiv_id", arxiv, "https://arxiv.org/abs/")):
        if values.get(field):
            identity = resolver(values[field])
            if not identity:
                raise InputError(f"Invalid {field}: {values[field]!r}")
            source_links.add(prefix + identity)
    source_links.update(values.get("source_links") or [])
    values["source_links"] = sorted(source_links)
    return values, warnings


def refresh(record, spec):
    # These lists describe missing research information, not negative evidence.
    research_fields = spec["x-research-fields"]
    record["missing_fields"] = sorted(f for f in research_fields if absent(record.get(f)) or
                                      (f == "novelty_threat" and record.get(f) == "UNKNOWN"))
    record["source_links"] = sorted(set(record["source_links"] + ([record["url"]] if record["url"] else [])))
    record["warnings"] = sorted(set(record["warnings"]))


def make_record(source, spec):
    record = {field: None for field in spec["properties"]}
    record.update({"novelty_threat": "UNKNOWN", "evidence_status": "unreviewed",
                   "review": None, "source_links": [], "sources": [source], "warnings": []})
    values, warnings = mapped(source, spec)
    record.update(values)
    record["warnings"].extend(warnings)
    record["evidence_status"] = record["evidence_status"] or "unreviewed"
    record["novelty_threat"] = record["novelty_threat"] or "UNKNOWN"
    if not any(record.get(f) for f in ("title", "doi", "arxiv_id", "url")):
        raise InputError(f"Row {source['row']} in {source['file']} has no paper title or identifier")
    if not record["paper_id"]:
        identity = (doi(record["doi"]) or arxiv(record["arxiv_id"]) or title_key(record["title"]) or record["url"])
        record["paper_id"] = "paper-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
    refresh(record, spec)
    return record


def duplicate_candidates(records):
    """Report shared identifiers/titles without merging or discarding a row."""
    indices = defaultdict(list)
    for record in records:
        identities = {("doi", doi(record.get("doi"))), ("doi", doi(record.get("url"))),
                      ("arxiv_id", arxiv(record.get("arxiv_id"))), ("arxiv_id", arxiv(record.get("url"))),
                      ("title", title_key(record.get("title")))}
        # Generic code/data links are never paper identity keys.
        if record.get("url"):
            identities.add(("paper_url", record["url"].rstrip("/")))
        for kind, value in identities:
            if value:
                indices[kind, value].append(record["paper_id"])
    return [{"reason": kind, "value": value, "paper_ids": sorted(set(ids))}
            for (kind, value), ids in sorted(indices.items()) if len(set(ids)) > 1]


def ingest(rows, notes=()):
    spec, records, used = schema(), [], set()
    for source in rows:
        record = make_record(source, spec)
        original = record["paper_id"]
        if original in used:
            # Explicit IDs are curator keys; silently renaming one is unsafe.
            if any(key(c["header"]) == "paperid" and not absent(c["value"]) for c in source["columns"]):
                raise InputError(f"Repeated explicit paper_id: {original}")
            suffix = 2
            while f"{original}-{suffix}" in used:
                suffix += 1
            record["paper_id"] = f"{original}-{suffix}"
        used.add(record["paper_id"])
        records.append(record)
    by_id = {r["paper_id"]: r for r in records}
    enriched = set()
    for note in notes:
        values, warnings = mapped(note, spec)
        paper_id = values.get("paper_id")
        if paper_id not in by_id:
            raise InputError(f"Note row {note['row']} needs a paper_id from this import: {paper_id!r}")
        if paper_id in enriched:
            raise InputError(f"Multiple note overrides for {paper_id}; combine them explicitly")
        enriched.add(paper_id)
        record = by_id[paper_id]
        source_links = set(record["source_links"]) | set(values.pop("source_links", []))
        record.update(values)
        record["source_links"] = sorted(source_links)
        record["sources"].append(note)
        record["warnings"].extend(warnings)
        refresh(record, spec)
    records.sort(key=lambda r: r["paper_id"])
    registry = {"schema_version": "1.0", "records": records,
                "duplicate_candidates": duplicate_candidates(records)}
    errors = validate_registry(registry)
    if errors:
        raise InputError("Validation failed:\n" + "\n".join(errors))
    return registry


def validate_registry(registry):
    from jsonschema import Draft202012Validator, FormatChecker

    spec = schema()
    Draft202012Validator.check_schema(spec)
    validator = Draft202012Validator(spec, format_checker=FormatChecker())
    if not isinstance(registry, dict) or registry.get("schema_version") != "1.0":
        return ["Expected a registry object with schema_version '1.0'"]
    if set(registry) != {"schema_version", "records", "duplicate_candidates"}:
        return ["Registry must contain only schema_version, records, duplicate_candidates"]
    if not isinstance(registry.get("records"), list):
        return ["Registry records must be an array"]
    errors, seen = [], set()
    for index, record in enumerate(registry["records"]):
        prefix = f"record {index + 1}"
        schema_errors = list(validator.iter_errors(record))
        for error in schema_errors:
            errors.append(f"{prefix} {'.'.join(str(p) for p in error.absolute_path)}: {error.message}")
        if schema_errors:
            continue
        prefix = record["paper_id"]
        if prefix in seen:
            errors.append(f"Repeated paper_id: {prefix}")
        seen.add(prefix)
        if not any(record[f] for f in ("title", "doi", "arxiv_id", "url")):
            errors.append(f"{prefix}: missing paper identity")
        for field, resolver in (("doi", doi), ("arxiv_id", arxiv)):
            if record[field] and not resolver(record[field]):
                errors.append(f"{prefix}: invalid {field}")
        for field in spec["x-research-fields"]:
            value = record[field]
            if value is not None and absent(value) and field != "novelty_threat":
                errors.append(f"{prefix}: unknown {field} must be null")
            if isinstance(value, list) and any(absent(item) for item in value):
                errors.append(f"{prefix}: {field} contains an unknown/blank list item")
        for link in record["source_links"] + ([record["url"]] if record["url"] else []):
            if not is_url(link):
                errors.append(f"{prefix}: invalid HTTP(S) source link {link!r}")
        refreshed = copy.deepcopy(record)
        refresh(refreshed, spec)
        for field in ("missing_fields", "source_links", "warnings"):
            if record[field] != refreshed[field]:
                errors.append(f"{prefix}: stale/noncanonical {field}; rebuild the registry")
        status, review = record["evidence_status"], record["review"]
        if status != "unreviewed" and review is None:
            errors.append(f"{prefix}: {status} requires review provenance (reviewed_by, reviewed_at, notes)")
        if status in {"deep-reviewed", "verified"}:
            if not record["url"] and not record["doi"] and not record["arxiv_id"]:
                errors.append(f"{prefix}: {status} requires a primary paper URL, DOI or arXiv ID")
            if not record["paper_demonstrates"]:
                errors.append(f"{prefix}: {status} requires an explicit paper_demonstrates extraction")
        checks = review.get("checks", []) if review else []
        if status == "verified" and not checks:
            errors.append(f"{prefix}: verified requires at least one field-level source check")
        for check in checks:
            field = check["field"]
            if field not in spec["x-research-fields"] or field in record["missing_fields"]:
                errors.append(f"{prefix}: cannot verify unknown/missing field {field}")
            elif json.dumps(check["value"], sort_keys=True) != json.dumps(record[field], sort_keys=True):
                errors.append(f"{prefix}: stale verification value for {field}")
            if check["source_url"] not in record["source_links"] or not is_url(check["source_url"]):
                errors.append(f"{prefix}: verification source must be in source_links")
    if not errors and registry["duplicate_candidates"] != duplicate_candidates(registry["records"]):
        errors.append("Stale duplicate_candidates; rebuild the registry")
    return errors


def export_web(registry):
    errors = validate_registry(registry)
    if errors:
        raise InputError("Cannot export invalid registry:\n" + "\n".join(errors))
    counts = Counter(r["evidence_status"] for r in registry["records"])
    # Full structured records preserve claim buckets and source-cell provenance.
    return {**copy.deepcopy(registry), "summary": {
        "total_papers": len(registry["records"]),
        "by_evidence_status": {s: counts[s] for s in STATUSES},
        "incomplete_papers": sum(bool(r["missing_fields"]) for r in registry["records"]),
        "duplicate_groups": len(registry["duplicate_candidates"]),
    }}
