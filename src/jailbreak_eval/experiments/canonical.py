"""One-way capture adapter: offline input files -> canonical records.

The PR4 capture manifest/CSVs are immutable intake transport, not registries.
All scientific identity/version references and every public result use registry.py.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from math import sqrt

from ..registry import (REGISTRIES, canonical_sha256, experiment_for_run, load_registries,
                        pinned, require, run_inputs_sha256, validate_registries, verify_local_artifacts)
from ..store import append_records, encode, envelopes, save_records, write_lock
from .analysis import analyze
from .contracts import load_json
from .runs import digest, json_bytes, read_inputs, record_run, verify_run, validate_inputs


def ident(prefix, value):
    # Reversible case-sensitive capture identifiers: readable slug plus collision guard.
    import re
    if re.fullmatch(prefix + r":[a-z0-9][a-z0-9._-]*", value):
        return value
    slug = re.sub('[^a-z0-9._-]+', '-', value.lower()).strip('-')
    return f'{prefix}:{slug}-{hashlib.sha256(value.encode()).hexdigest()[:12]}'


def base(rid, version, timestamp, kind, notes=None):
    return dict(id=rid, version=version, timestamp=timestamp, record_kind=kind, notes=notes)


def artifact(uri, raw, description, media='application/json'):
    sha = digest(raw)
    return dict(id='artifact:' + digest((uri + sha).encode()), uri=uri, sha256=sha, media_type=media, description=description)


def captured(value, category, pending):
    raw = json_bytes(value)
    uri = f'data/manifests/captured/{category}-{digest(raw)}.json'
    pending[uri] = raw
    return artifact(uri, raw, 'Supplied capture metadata; no independent implementation/source verification implied.')


def definitions(manifest, inputs, previous):
    """Normalize capture fields without inventing implementations, findings or votes."""
    m = manifest
    pending = {}
    additions = {n: [] for n in REGISTRIES}
    kind, time = m['record_kind'], m['created_at']
    dataset = load_json(inputs['dataset_manifest.json'], 'dataset capture')
    did = ident('dataset', dataset['dataset_id'])
    p = dataset['provenance']
    dataset_uri = f"data/manifests/captured/dataset-{digest(inputs['dataset_manifest.json'])}.json"
    pending[dataset_uri] = inputs['dataset_manifest.json']
    cases = []
    for c in dataset['cases']:
        cases.append({'id': ident('case', c['case_id']), 'group_id': ident('group', c['duplicate_group_id']),
                      **{k: c[k] for k in c if k != 'case_id'}})
    ds = {**base(did, dataset['version'], time, kind), 'name': dataset['dataset_id'],
          'status': 'frozen', 'benchmark': None, 'domain_ids': [], 'cases': cases,
          'manifest': artifact(dataset_uri, inputs['dataset_manifest.json'], 'Exact supplied dataset manifest bytes.'),
          'provenance': {'source': {'id': ident('source', p['source']),
                                   'url': p['source'] if p['source'].startswith(('http://','https://')) else None,
                                   'locator': p['source']}, 'upstream_version': p['source_version'],
                         'license': p['license'], 'retrieved_at': p['retrieved_at'],
                         'redistribution': {True:'permitted',False:'prohibited',None:'unknown'}[p['redistribution_allowed']],
                         'transformations': [{'id': ident('transformation', did + text), 'description': text,
                                              'code_commit': None} for text in p['transformations']]}}
    prior_dataset = next((r for r in previous['datasets'] if r['id'] == did and r['version'] == ds['version']), None)
    if prior_dataset:
        ds['timestamp'] = prior_dataset['timestamp']
    additions['datasets'].append(ds)
    validator_pins = []
    for value in m['validators']:
        vid = ident('validator', value['validator_id'])
        capture = captured(value, 'validator', pending)
        row = {**base(vid, value['version'], time, kind, 'External recorded decisions; implementation has not been independently audited.'),
               'name': value['name'], 'status': 'external_recorded', 'evaluation_types': [],
               'domain_ids': [], 'paper_ids': [], 'executes_code': None,
               'success_definition': value['success_construct'], 'output_definition': 'Explicit 0/1 or unresolved/error capture; full scoring details in captured definition.',
               'rubric': {'id': ident('rubric', vid), 'version': value['version'], 'artifact': capture},
               'code_commit': None, 'implementation': None, 'judge_model': None, 'judge_prompt': None,
               'capture_artifact': capture}
        old = next((r for r in previous['validators'] if r['id'] == vid and r['version'] == row['version']), None)
        if old:
            row['timestamp'] = old['timestamp']
        additions['validators'].append(row)
        validator_pins.append({'id': vid, 'version': value['version']})
    protocol = captured(m['protocol'], 'protocol', pending)
    ground = captured(m['human_ground_truth'], 'human-policy', pending)
    eid = m.get('canonical_experiment_id') or ident('experiment', m['experiment_id'])
    experiment = {
        **base(eid, m['config_version'], time, kind, 'Definition imported from offline capture; original metadata retained by hash.'),
        'name': m['experiment_id'], 'experiment_code': m['experiment_id'], 'status': 'frozen',
        'dataset': {'id': did, 'version': ds['version']}, 'validators': validator_pins,
        'config': {'id': ident('config', eid), 'version': m['config_version'], 'parameters': m['config']},
        'models': [{'id': ident('model', v['model_id']), 'name': v['name'], 'provider': None,
                    'version': v['version']} for v in m['models']],
        'attack_methods': [{'id': ident('attack', v['attack_method_id']), 'name': v['name'], 'version': v['version'],
                            'config': {'id': ident('config', v['attack_method_id']), 'version': v['version'], 'parameters': v['config']}}
                           for v in m['attack_methods']],
        'code_commit': m['code_commit'], 'split': m['split'], 'purpose': m['purpose'],
        'seed': m['seed'], 'human_ground_truth': {'id': ident('rubric', eid + '-human'), 'version': m['human_ground_truth']['rubric_version'], 'artifact': ground},
        'protocol': protocol, 'protocol_freeze': m['protocol']['frozen_at'], 'ablation': m['ablation']}
    old = next((r for r in previous['experiments'] if r['id'] == eid and r['version'] == experiment['version']), None)
    if old:
        experiment['timestamp'] = old['timestamp']
    additions['experiments'].append(experiment)
    # Exact model configs, success constructs, endpoint and human-label version
    # remain part of a canonical config, not an untracked parallel manifest.
    experiment['config']['parameters'] = {'capture_config': m['config'], 'models': m['models'],
                                         'capture_protocol': m['protocol'], 'human_ground_truth': m['human_ground_truth']}
    current = append_records(previous, additions)
    return additions, current, pending


def assessment(row=None, reason=None, label=None):
    return {'predicted_success': (row['predicted_success'] == '1' if row and row['status'] == 'ok' else label),
            'functional_stage': row['functional_level'] or None if row else None,
            'dimensions': {k.upper(): float(row[k]) if row and row[k] else None for k in 'rhfqe'},
            'score': float(row['score']) if row and row['score'] else None, 'confidence': None,
            'reason': reason or (row['evidence_ref'] or 'Captured evaluator decision' if row else None)}


def outputs(run_dir, project_root, input_records):
    root = Path(run_dir).resolve()
    m, metrics, errors = verify_run(root)
    raw_inputs = {n: (root / n).read_bytes() for n in ('dataset_manifest.json','predictions.csv','human_labels.csv')}
    capture = {k: v for k, v in m.items() if k not in ('artifacts','analysis','canonical_inputs')}
    cases, predictions, labels = validate_inputs(capture, raw_inputs)
    rid, kind, time = ident('run', m['run_id']), m['record_kind'], m['created_at']
    experiment = input_records['experiments'][0]
    additions = {n: [] for n in REGISTRIES}
    arts = {p.name: artifact(p.relative_to(Path(project_root).resolve()).as_posix(), p.read_bytes(),
                            'Immutable run capture / reproducible analysis artifact.', 'text/csv' if p.suffix == '.csv' else 'application/json')
            for p in sorted(root.iterdir()) if p.is_file()}
    run = {**base(rid, '1', time, kind), 'experiment_id': experiment['id'],
           'experiment_sha256': canonical_sha256(experiment), 'inputs_sha256': run_inputs_sha256(experiment, input_records),
           'status': 'completed', 'started_at': time, 'finished_at': time,
           'environment': None, 'recording_only': True, 'artifacts': list(arts.values()), 'exclusions': []}
    # These are recorder completion timestamps, not inferred model-execution times.
    run['notes'] = 'Completed offline recording/analysis. Capture created_at is used as the recorder event time; model execution times are not inferred.'
    additions['runs'].append(run)
    label_by_case = {}
    resolved_ids = []
    for i, value in enumerate(labels, 2):
        lid = ident('label', m['run_id'] + '/' + value['label_id'])
        resolved = value['status'] in {'consensus','adjudicated'}
        row = {**base(lid, m['human_ground_truth']['version'], time, kind, 'Imported reference attestation; individual annotator votes were not supplied and are not fabricated.'),
               'run_id': rid, 'dataset': experiment['dataset'], 'case_id': ident('case', value['case_id']), 'split': m['split'],
               'input_artifact': arts['dataset_manifest.json'], 'annotator_id': ident('annotator', value['adjudicator_id'] or value['annotator_ids'] or 'unassigned'),
               'rubric': experiment['human_ground_truth'], 'status': value['status'] if resolved else 'unresolved',
               'assessment': assessment(label=value['label'] == '1' if resolved else None, reason=value['evidence_ref'] or 'Reference unresolved'),
               'evidence': [arts['human_labels.csv']], 'reviewed_label_ids': [], 'supersedes_id': None,
               'reference_review': {'annotator_ids': value['annotator_ids'].split('|') if value['annotator_ids'] else [],
                                    'adjudicator_id': value['adjudicator_id'] or None, 'source_row': i}}
        additions['human_labels'].append(row)
        label_by_case[value['case_id']] = lid if resolved else None
        if resolved: resolved_ids.append(lid)
    prediction_by_key = {(p['case_id'], p['validator_id']): p for p in predictions}
    for v in m['validators']:
        pin = {'id': ident('validator', v['validator_id']), 'version': v['version']}
        source_ids = []
        for case in cases:
            value = prediction_by_key.get((case['case_id'], v['validator_id']))
            result_id = ident('result', m['run_id'] + '/' + v['validator_id'] + '/' + case['case_id'])
            source_ids.append(result_id)
            status = {'ok':'measured', 'indeterminate':'indeterminate', 'error':'error'}.get(value['status']) if value else 'missing'
            row = {**base(result_id, '1', time, kind), 'kind':'prediction', 'run_id': rid, 'validator':pin,
                   'human_label_ids': [label_by_case[case['case_id']]] if label_by_case.get(case['case_id']) else [],
                   'provenance': {'code_commit':m['code_commit'], 'config':experiment['config'], 'artifacts': [arts['predictions.csv'], arts['manifest.json']]},
                   'case_id':ident('case',case['case_id']), 'input_artifact':arts['dataset_manifest.json'],
                   'status':status, 'assessment':assessment(value, reason=(value['error_type'] or value['evidence_ref'] or status) if value else 'Missing prediction in captured inputs'),
                   'source_result_ids':[], 'excluded_result_ids':[], 'metrics':[]}
            additions['results'].append(row)
        aggregate_id = ident('result', m['run_id'] + '/' + v['validator_id'] + '/aggregate')
        values = metrics['evaluators'][v['validator_id']]
        c = values['classification']; cm = c['confusion_matrix']
        denominators = {'accuracy': c['n'], 'precision':cm['tp']+cm['fp'], 'recall':cm['tp']+cm['fn'],
                        'f1':2*cm['tp']+cm['fp']+cm['fn'], 'false_positive_rate':cm['fp']+cm['tn'], 'false_negative_rate':cm['fn']+cm['tp'],
                        'specificity':cm['tn']+cm['fp'], 'mcc':sqrt((cm['tp']+cm['fp'])*(cm['tp']+cm['fn'])*(cm['tn']+cm['fp'])*(cm['tn']+cm['fn']))}
        metric_rows = []
        def add_metric(name, value, denominator, definition, unit='ratio'):
            metric_rows.append({'id':ident('metric',aggregate_id+'/'+name), 'name':name, 'definition':definition,
                                'unit':unit, 'status':'computed' if value is not None else 'undefined', 'value':value,
                                'denominator':denominator, 'denominator_basis':'formula' if name in {'f1','mcc'} else 'cases',
                                'cohort_size': c['n'] if name in denominators or name.startswith('confusion_') else len(cases),
                                'reason':None if value is not None else 'Undefined denominator or no paired determinate observations.', 'uncertainty':None})
        for name, denominator in denominators.items():
            add_metric(name,c[name],denominator,'Resolved human/evaluator pairs. Denominator is the actual formula denominator; cohort_size is the paired case count. Confusion counts and formulas are recorded in the analysis.')
        add_metric('asr',values['asr']['rate'],values['asr']['denominator'],metrics['definitions']['asr'])
        for name in ('tp','tn','fp','fn'):
            add_metric('confusion_'+name,cm[name] if c['n'] else None,c['n'],metrics['definitions']['confusion_matrix'],'count')
        additions['results'].append({**base(aggregate_id,'1',time,kind),'kind':'aggregate','run_id':rid,'validator':pin,
            'human_label_ids':resolved_ids,'provenance':{'code_commit':m['code_commit'],'config':experiment['config'],
            'artifacts':[arts['metrics.json'],arts['errors.json'],arts['manifest.json'],arts['dataset_manifest.json'],arts['human_labels.csv'],arts['predictions.csv']]},
            'case_id':None,'input_artifact':None,'status':'measured','assessment':None,
            'source_result_ids':source_ids,'excluded_result_ids':[],'metrics':metric_rows,
            'analysis': canonical_analysis(metrics, m)})
    return additions, metrics, errors


def canonical_analysis(metrics, manifest):
    """Replace transport IDs throughout the derived report with canonical IDs."""
    mapping = {manifest['run_id']: ident('run', manifest['run_id']),
               manifest['experiment_id']: manifest.get('canonical_experiment_id') or ident('experiment', manifest['experiment_id'])}
    for collection, field, prefix in (('validators','validator_id','validator'), ('models','model_id','model'), ('attack_methods','attack_method_id','attack')):
        mapping.update({r[field]: ident(prefix, r[field]) for r in manifest[collection]})
    def convert(value):
        if isinstance(value, dict):
            return {mapping.get(k,k): convert(v) for k,v in value.items() if k != 'case_ids'}
        if isinstance(value,list): return [convert(v) for v in value]
        if isinstance(value,str): return mapping.get(value,value)
        return value
    return convert(metrics)


def record_canonical(manifest_path, dataset_path, predictions_path, labels_path, runs_dir, directory, project_root):
    project_root = Path(project_root).resolve()
    require(Path(runs_dir).resolve().is_relative_to(project_root), 'Run directory must be inside the project root')
    with write_lock(directory):
        previous = load_registries(directory)
        m, inputs, _, _, _ = read_inputs(manifest_path,dataset_path,predictions_path,labels_path)
        additions, current, pending = definitions(m,inputs,previous)
        # Validate cross-version/split/definition constraints BEFORE publishing a run.
        for uri, raw in pending.items():
            path = project_root / uri
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists(): require(path.read_bytes()==raw,'Captured definition artifact conflict')
            else: path.write_bytes(raw)
        target = record_run(manifest_path,dataset_path,predictions_path,labels_path,runs_dir,canonical_inputs=envelopes(additions))
        derived, _, _ = outputs(target,project_root,additions)
        current = append_records(current,derived)
        save_records(directory,current,previous)
        return target


def sync_run(run_dir,directory,project_root):
    """Recover registry publication after a write failure; never mutate the bundle."""
    with write_lock(directory):
        previous=load_registries(directory)
        verify_run(run_dir)
        snap=json.loads((Path(run_dir)/'canonical_inputs.json').read_text())
        additions=validate_registries(snap)
        # Reconcile exact capture metadata to the sealed canonical definitions.
        m=json.loads((Path(run_dir)/'manifest.json').read_text())
        inputs={'dataset_manifest.json':(Path(run_dir)/'dataset_manifest.json').read_bytes()}
        capture={k:v for k,v in m.items() if k not in ('artifacts','analysis','canonical_inputs')}
        regenerated, _, _ = definitions(capture,inputs,additions)
        require(regenerated==additions,'Canonical snapshot does not match captured metadata')
        current=append_records(previous,additions)
        derived,_,_=outputs(run_dir,project_root,additions)
        current=append_records(current,derived)
        save_records(directory,current,previous)
        return current


def verify_registered_runs(records,project_root):
    """Fail closed on stale hashes, unmapped results or hand-entered metrics."""
    summaries={}
    for run in records['runs']:
        if run['status'] != 'completed': continue
        manifests=[a for a in run['artifacts'] if a['uri'].endswith('/manifest.json')]
        require(len(manifests)==1,f"{run['id']}: measured export needs an immutable recorder bundle")
        ref=manifests[0]; path=(Path(project_root)/ref['uri']).resolve()
        require(path.is_relative_to(Path(project_root).resolve()),'Run path escapes project root')
        require(path.is_file() and digest(path.read_bytes())==ref['sha256'],'Registered manifest checksum mismatch')
        snapshot=validate_registries(json.loads((path.parent/'canonical_inputs.json').read_text()))
        verify_local_artifacts(snapshot, project_root)
        saved=json.loads(path.read_text())
        capture={k:v for k,v in saved.items() if k not in ('artifacts','analysis','canonical_inputs')}
        regenerated, _, _=definitions(capture, {'dataset_manifest.json':(path.parent/'dataset_manifest.json').read_bytes()}, snapshot)
        require(regenerated==snapshot, 'Canonical input definitions do not match capture metadata')
        # Every sealed version must remain in the canonical history, exactly.
        for name in REGISTRIES:
            for row in snapshot[name]:
                require(pinned(records[name],row)==row,'Canonical run input revision drift')
        additions,metrics,errors=outputs(path.parent,project_root,snapshot)
        for name in ('runs','human_labels','results'):
            expected={r['id']:r for r in additions[name]}
            actual={r['id']:r for r in records[name] if r['id']==run['id']} if name=='runs' else {r['id']:r for r in records[name] if r.get('run_id')==run['id']}
            require(actual==expected,f"{run['id']}: canonical {name} do not reproduce from immutable inputs")
        summaries[run['id']]={'analysis':metrics,'errors':errors}
    return summaries
