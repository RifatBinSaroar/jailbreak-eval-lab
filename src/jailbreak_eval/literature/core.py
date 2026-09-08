"""Literature intake into the single canonical registry contract.

Cells are immutable intake artifacts, never an alternate scientific registry.
Only an explicit, source-linked curator revision can add paper evidence.
"""

from copy import deepcopy
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from .inputs import InputError, key
from ..registry import canonical_sha256, latest_records, load_registries, load_schema, require
from ..store import append_records, encode, save_records, write_lock

MISSING = {"", "unknown", "not reported", "not yet checked", "tbd", "n/a", "?", "-"}
URL_RE = re.compile(r'https?://[^\s<>"\[\]]+', re.I)
HYPERLINK = re.compile(r'^=HYPERLINK\(\s*"((?:[^"]|"")*)"\s*[,;]\s*"((?:[^"]|"")*)"\s*\)$', re.I)

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


def schema():
    return load_schema()['$defs']['paper']


def fields(source):
    values, warnings, links, explicit = {}, [], set(), set()
    for column in source['columns']:
        value, hyperlink = column['value'], column['hyperlink']
        links.update(links_in(value))
        if is_url(hyperlink):
            links.add(hyperlink)
        if column['is_formula']:
            match = HYPERLINK.fullmatch(value or '')
            if match:
                hyperlink, value = (s.replace('""', '"') for s in match.groups())
                if is_url(hyperlink):
                    links.add(hyperlink)
            else:
                warnings.append(f"Formula not evaluated at {column['cell']}")
                value = None
        name = key(column['header'])
        name = {'paper':'title', 'papertitle':'title', 'paperid':'id', 'venue':'venue_or_identifier',
                'venueorarxiv':'venue_or_identifier', 'venueoridentifier':'venue_or_identifier', 'paperurl':'url', 'paperlink':'url', 'link':'url',
                'myunderstnding':'our_interpretation', 'myunderstanding':'our_interpretation',
                'ourinterpretation':'our_interpretation', 'questions':'open_questions',
                'openquestions':'open_questions', 'arxivid':'arxiv_id'}.get(name, name)
        new = None if absent(value) else value
        require(name not in explicit or values[name] == new, f"Conflicting columns for {name} in row {source['row']}")
        values[name] = new
        explicit.add(name)
        if name in {'title', 'url'} and is_url(hyperlink):
            values.setdefault('url', hyperlink)
    if values.get('doi'):
        require(doi(values['doi']) is not None, 'Invalid DOI; leave unknown values blank')
        links.add('https://doi.org/' + doi(values['doi']))
    if values.get('arxiv_id'):
        require(arxiv(values['arxiv_id']) is not None, 'Invalid arXiv ID')
        links.add('https://arxiv.org/abs/' + arxiv(values['arxiv_id']))
    return values, warnings, sorted(links)


def text_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split('\n') if part.strip()]
    require(isinstance(value, list) and all(isinstance(s, str) for s in value), 'Notes must be text or a list of text')
    return value


def intake_paper(source, paper_id, timestamp, artifact):
    value, warnings, links = fields(source)
    require(isinstance(value.get('title'), str), 'A listed paper needs the supplied title; no title is invented')
    year = value.get('year')
    if year is not None:
        require(not isinstance(year, bool) and (str(year).isdigit() or isinstance(year, float) and year.is_integer()), 'Year must be an integer or blank')
        year = int(year)
    return {
        'id': paper_id, 'record_kind': value.get('recordkind') or 'research', 'version': '1', 'timestamp': timestamp,
        'notes': 'Imported reading queue. Intake metadata has not been independently checked.',
        'title': value['title'], 'year': year, 'venue_or_identifier': value.get('venue_or_identifier'),
        'identifiers': {'doi': doi(value.get('doi')), 'arxiv_id': arxiv(value.get('arxiv_id'))},
        'sources': [{'id': 'source:' + hashlib.sha256(url.encode()).hexdigest()[:24], 'url': url,
                     'kind': 'paper' if url == value.get('url') or doi(url) or arxiv(url) else 'intake',
                     'locator': 'Link supplied in literature intake; paper identity/content not verified.'} for url in links],
        'evidence_status': 'listed', 'review': None, 'intake_artifacts': [artifact],
        'benchmark_ids': [], 'domain_ids': [], 'validator_ids': [], 'paper_demonstrates': [],
        'our_interpretation': [{'id': f"interpretation:{paper_id.split(':')[1]}-{i}", 'text': text, 'evidence_ids': []}
                               for i, text in enumerate(text_list(value.get('our_interpretation')), 1)],
        'open_questions': [{'id': f"question:{paper_id.split(':')[1]}-{i}", 'text': text}
                           for i, text in enumerate(text_list(value.get('open_questions')), 1)],
        'novelty': {'status': 'unassessed', 'basis': 'manual_evidence_review', 'rationale': None, 'evidence_ids': []},
    }, warnings


def duplicate_candidates(records):
    indices = defaultdict(set)
    for paper in records:
        keys = [('doi', paper['identifiers']['doi']), ('arxiv_id', paper['identifiers']['arxiv_id']),
                ('title', title_key(paper['title']))]
        for source in paper['sources']:
            keys += [('doi', doi(source['url'])), ('arxiv_id', arxiv(source['url']))]
            if source.get('kind') == 'paper' and source['url']:
                keys.append(('paper_url', source['url'].rstrip('/')))
        for kind, value in keys:
            if value:
                indices[kind, value].add(paper['id'])
    return [{'reason': kind, 'value': value, 'paper_ids': sorted(ids)}
            for (kind, value), ids in sorted(indices.items()) if len(ids) > 1]


def sidecar(source, paper_id, project_root):
    # Hash the complete source row, including blank cells, formulas and hyperlinks.
    content = {'artifact_kind': 'literature_intake', 'paper_id': paper_id, 'source': source}
    raw = encode(content)
    digest = hashlib.sha256(raw).hexdigest()
    relative = f'literature/intake/{digest}.json'
    artifact = {'id': 'artifact:intake-' + digest, 'uri': relative, 'sha256': digest,
                'media_type': 'application/json', 'description': 'Original intake cells and source-file provenance; not verified evidence.'}
    return artifact, Path(project_root) / relative, raw


def existing_intake(records, root):
    entries = []
    seen = set()
    for paper in records['papers']:
        for artifact in paper['intake_artifacts']:
            if artifact['id'] in seen:
                continue
            seen.add(artifact['id'])
            path = (Path(root) / artifact['uri']).resolve()
            require(path.is_relative_to(Path(root).resolve()), 'Intake artifact escapes project root')
            raw = path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == artifact['sha256'], 'Intake artifact checksum mismatch')
            entries.append(json.loads(raw))
    return entries


def import_rows(rows, directory, project_root, timestamp, notes=(), fail_on_duplicates=False):
    """Incremental append. Never replace a curated paper with an intake snapshot."""
    with write_lock(directory):
        previous = load_registries(directory)
        known = existing_intake(previous, project_root)
        latest = {p['id']: p for p in latest_records(previous)['papers']}
        additions, pending, used = [], [], set()
        warnings = []
        for source in rows:
            value, _, _ = fields(source)
            paper_id = value.get('id')
            if paper_id:
                require(paper_id.startswith('paper:'), 'Use the exported canonical paper: ID in the paper_id column')
            else:
                exact = {e['paper_id'] for e in known if e['source'] == source}
                # Reordering is safe only for a unique, unchanged row in the SAME named source.
                same = {e['paper_id'] for e in known if e['source']['file'] == source['file']
                        and e['source']['sheet'] == source['sheet']
                        and [(c['header'], c['value'], c['hyperlink'], c['is_formula']) for c in e['source']['columns']]
                        == [(c['header'], c['value'], c['hyperlink'], c['is_formula']) for c in source['columns']]}
                matches = exact or same
                require(len(matches) <= 1, 'Ambiguous duplicate row identity; add an explicit paper_id column')
                paper_id = next(iter(matches), None)
                changed = any(e['source']['file'] == source['file'] and e['source']['sheet'] == source['sheet']
                              and e['source']['row'] == source['row'] for e in known)
                require(paper_id is not None or not changed, 'Changed intake row: add its existing paper_id (or a new explicit ID) before importing')
                paper_id = paper_id or 'paper:' + uuid4().hex
            require(paper_id not in used, 'Repeated paper_id in one import; keep duplicate candidates as distinct IDs')
            used.add(paper_id)
            artifact, path, raw = sidecar(source, paper_id, project_root)
            if paper_id in latest:
                # Attach new source bytes only through an explicit versioned revision.
                if artifact not in latest[paper_id]['intake_artifacts']:
                    require(value.get('version') and value.get('timestamp'), 'Updated intake needs version and timestamp columns alongside paper_id')
                    row = deepcopy(latest[paper_id])
                    row.update(version=str(value['version']), timestamp=value['timestamp'])
                    row['intake_artifacts'].append(artifact)
                    additions.append(row)
            else:
                row, notice = intake_paper(source, paper_id, timestamp, artifact)
                additions.append(row)
                warnings.extend(notice)
            pending.append((path, raw))
        current = append_records(previous, {'papers': additions})
        # --notes is an explicit canonical curator revision, not a matrix-cell promotion.
        if notes:
            current = reviewed_revisions(current, notes)
        duplicates = duplicate_candidates(latest_records(current)['papers'])
        require(not fail_on_duplicates or not duplicates, 'Duplicate candidates found; nothing committed')
        for path, raw in pending:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                require(path.read_bytes() == raw, 'Immutable intake artifact conflict')
            else:
                path.write_bytes(raw)
        save_records(directory, current, previous)
        return {'imported_ids': sorted(used), 'duplicate_candidates': duplicates, 'warnings': warnings}


def reviewed_revisions(previous, notes):
    additions = []
    latest = {p['id']: p for p in latest_records(previous)['papers']}
    for note in notes:
        require(isinstance(note, dict) and {'id','version','timestamp','review'} <= note.keys(), 'Review notes need id, version, timestamp and review provenance')
        require(note['id'] in latest, f"Unknown paper ID: {note['id']}")
        require(note['review'] is not None, 'Curator revision requires recorded reviewer/date/notes')
        require(note['version'] != latest[note['id']]['version'], 'Reviewed update needs a new version, SAME stable ID')
        row = {**deepcopy(latest[note['id']]), **note}
        require(row['record_kind'] == latest[note['id']]['record_kind'], 'Cannot promote a synthetic fixture')
        # Changed evidence cannot retain an earlier verification declaration silently.
        old_claims = {e['id']: e for e in latest[note['id']]['paper_demonstrates']}
        for claim in row['paper_demonstrates']:
            if old_claims.get(claim['id']) != claim and claim['verification_status'] == 'verified':
                require('paper_demonstrates' in note and claim['id'] in note['review']['verified_evidence_ids'], 'Changed evidence needs a fresh explicit verification')
        additions.append(row)
        latest[row['id']] = row
    return append_records(previous, {'papers': additions})


def review_notes(notes, directory):
    with write_lock(directory):
        previous = load_registries(directory)
        current = reviewed_revisions(previous, notes)
        save_records(directory, current, previous)
        return current
