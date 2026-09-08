"""Full safe integration tests. No model, validator or payload execution."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from jailbreak_eval.registry import (REGISTRIES, load_registries, web_bundle, validate_history, validate_registries,
    canonical_sha256, run_inputs_sha256, latest_records, write_web)
from jailbreak_eval.store import envelopes, encode, append_records, save_records, write_lock
from jailbreak_eval.experiments.canonical import record_canonical, sync_run, verify_registered_runs, ident
from jailbreak_eval.experiments.runs import json_bytes,digest,verify_run
from jailbreak_eval.experiments.contracts import PREDICTION_COLUMNS,LABEL_COLUMNS

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/run_framework'

@pytest.fixture
def work(tmp_path):
    (tmp_path/'registries').mkdir()
    for n,e in envelopes({n:[] for n in REGISTRIES}).items(): (tmp_path/'registries'/f'{n}.json').write_bytes(encode(e))
    (tmp_path/'input').mkdir()
    for name in ('manifest.json','dataset_manifest.json','predictions.csv','human_labels.csv'):shutil.copyfile(FIXTURE/name,tmp_path/'input'/name)
    return tmp_path


def record(work):
    i=work/'input'
    return record_canonical(i/'manifest.json',i/'dataset_manifest.json',i/'predictions.csv',i/'human_labels.csv',work/'results/runs',work/'registries',work)


def load(path):return json.loads(path.read_text())

def write(path,value):path.write_bytes(json_bytes(value))


def edit_csv(path,columns,edit):
    rows=list(csv.DictReader(io.StringIO(path.read_text())))
    edit(rows)
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(rows)


def change_split(work,split):
    d=load(work/'input/dataset_manifest.json')
    for c in d['cases']:
        if c['split']=='test':c['split']=split
    write(work/'input/dataset_manifest.json',d)
    m=load(work/'input/manifest.json');m.update(split=split,purpose={'test':'final_evaluation','development':'development','pilot':'pilot'}[split])
    m['dataset']['sha256']=digest((work/'input/dataset_manifest.json').read_bytes())
    if split!='test':m['protocol']['frozen_at']=None
    write(work/'input/manifest.json',m)


def test_synthetic_capture_to_registry_to_web_and_dashboard_parser(work):
    run=record(work);r=load_registries(work/'registries')
    assert {k:len(r[k]) for k in ('experiments','runs','human_labels','results')}=={'experiments':1,'runs':1,'human_labels':4,'results':10}
    assert r['experiments'][0]['experiment_code']=='EXP-001'
    assert (run/'canonical_inputs.json').exists()
    b=web_bundle(work/'registries')
    assert b['readiness']['experiments']==0 and b['metrics']==[] and b['results']==[]
    b=web_bundle(work/'registries',include_synthetic=True)
    assert all(v['record_kind']=='synthetic' for v in b['results'])
    a=next(v for v in b['results'] if v['validator']['id']==ident('validator','VAL-A'))
    assert next(m for m in a['metrics'] if m['name']=='accuracy')['value']==0.5
    assert a['analysis']['evaluators'][ident('validator','VAL-A')]['classification']['confusion_matrix']=={'tp':1,'tn':1,'fp':1,'fn':1}
    assert a['analysis']['rankings']['attack_method_id']['status']=='unavailable'
    if shutil.which('node'):
        data=work/'web.json';write(data,b)
        code="const fs=require('fs'),d=require(process.argv[1]),v=require(process.argv[2]);const b=d.parseBundle(JSON.parse(fs.readFileSync(process.argv[3])));for(const route of Object.keys(v.ROUTES)){if(!v.render(route,b))throw Error(route)};if(!v.render('results',b).includes('Synthetic test output'))throw Error('missing synthetic label')"
        result=subprocess.run(['node','-e',code,str(ROOT/'apps/web/data.js'),str(ROOT/'apps/web/views.js'),str(data)],capture_output=True,text=True)
        assert result.returncode==0,result.stderr


def test_unresolved_and_adjudicated_human_references_preserve_truth(work):
    def edit(rows):
        rows[0].update(status='uncertain',label='',annotator_ids='')
        rows[1].update(status='adjudicated',adjudicator_id='SYNTHETIC-ADJUDICATOR')
    edit_csv(work/'input/human_labels.csv',LABEL_COLUMNS,edit)
    record(work);r=load_registries(work/'registries')
    assert {l['status'] for l in r['human_labels']}=={'unresolved','adjudicated','consensus'}
    unresolved=next(l for l in r['human_labels'] if l['status']=='unresolved')
    adjudicated=next(l for l in r['human_labels'] if l['status']=='adjudicated')
    assert unresolved['assessment']['predicted_success'] is None
    assert adjudicated['reference_review']['adjudicator_id']=='SYNTHETIC-ADJUDICATOR'
    assert adjudicated['reviewed_label_ids']==[]  # never invent independent votes
    b=web_bundle(work/'registries',include_synthetic=True)
    assert b['results'][0]['analysis']['evaluators'][ident('validator','VAL-A')]['classification']['n']==3


def test_fx_error_and_missing_predictions_never_become_failure(work):
    def edit(rows):
        rows.pop(0)
        rows[0].update(status='indeterminate',predicted_success='',score='',error_type='',functional_level='FX')
    edit_csv(work/'input/predictions.csv',PREDICTION_COLUMNS,edit)
    record(work);r=load_registries(work/'registries')
    unknown=[p for p in r['results'] if p['kind']=='prediction' and p['status']!='measured']
    assert {p['status'] for p in unknown}=={'missing','indeterminate','error'}
    assert all(p['assessment']['predicted_success'] is None and p['assessment']['score'] is None for p in unknown)
    web_bundle(work/'registries',include_synthetic=True)


def test_no_predictions_or_labels_produces_only_null_performance_metrics(work):
    for name,columns in [('predictions.csv',PREDICTION_COLUMNS),('human_labels.csv',LABEL_COLUMNS)]:
        (work/'input'/name).write_text(','.join(columns)+'\n')
    record(work)
    b=web_bundle(work/'registries',include_synthetic=True)
    assert b['metrics'] and all(m['value'] is None and m['status']=='undefined' for m in b['metrics'])
    assert all(r['assessment']['predicted_success'] is None for r in load_registries(work/'registries')['results'] if r['kind']=='prediction')


@pytest.mark.parametrize('split',['development','pilot','test'])
def test_each_split_has_explicit_purpose(work,split):
    change_split(work,split);record(work)
    e=load_registries(work/'registries')['experiments'][0]
    assert e['split']==split
    assert e['purpose']=={'test':'final_evaluation','pilot':'pilot','development':'development'}[split]


@pytest.mark.parametrize('from_split,to_split',[('pilot','test'),('development','test'),('pilot','development')])
def test_cross_revision_and_cross_dataset_alias_split_leakage_rejected(work,from_split,to_split):
    change_split(work,from_split);record(work)
    d=load(work/'input/dataset_manifest.json')
    d['dataset_id']='NEW-DATASET-ALIAS';d['version']='test-2';d['provenance']['retrieved_at']='2026-09-09T00:00:00Z'
    for c in d['cases']:
        if c['split']==from_split:c['split']=to_split
    # Existing development distractor must not create a duplicate condition.
    write(work/'input/dataset_manifest.json',d)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',config_version='v2',created_at='2026-09-09T01:00:00Z',split=to_split,purpose={'test':'final_evaluation','development':'development'}[to_split])
    m['dataset'].update(dataset_id=d['dataset_id'],version=d['version'],sha256=digest((work/'input/dataset_manifest.json').read_bytes()))
    m['protocol']['frozen_at']='2026-09-09T00:00:00Z'
    m['protocol']['version']='test-2'
    write(work/'input/manifest.json',m)
    with pytest.raises(ValueError,match='split leakage|metadata must exactly cover'):record(work)
    assert not (work/'results/runs/RUN-SECOND').exists()


def test_final_test_requires_frozen_protocol(work):
    m=load(work/'input/manifest.json');m['protocol']['frozen_at']=None;write(work/'input/manifest.json',m)
    with pytest.raises(ValueError,match='frozen protocol'):record(work)


def test_provenance_hashes_and_manual_metric_mutation_fail_closed(work):
    run=record(work);r=load_registries(work/'registries')
    e=r['experiments'][0];rr=r['runs'][0]
    assert rr['inputs_sha256']==run_inputs_sha256(e,r)
    assert rr['experiment_sha256']==canonical_sha256(e)
    assert all(a['sha256']==digest((work/a['uri']).read_bytes()) for a in rr['artifacts'])
    out=work/'web.json';write_web(work/'registries',out,include_synthetic=True);before=out.read_bytes()
    path=work/'registries/results.json';env=load(path)
    next(x for x in env['records'] if x['kind']=='aggregate')['metrics'][0]['value']=0.9
    write(path,env)
    with pytest.raises(ValueError,match='do not reproduce'):write_web(work/'registries',out,include_synthetic=True)
    assert out.read_bytes()==before


def test_canonical_snapshot_tampering_rejected(work):
    run=record(work);p=run/'canonical_inputs.json';s=load(p)
    s['experiments']['records'][0]['code_commit']='f'*40;write(p,s)
    with pytest.raises(ValueError,match='snapshot hash'):verify_run(run)


def test_snapshot_capture_disagreement_rejected_even_with_rewritten_hash(work):
    run=record(work);p=run/'canonical_inputs.json';s=load(p)
    s['experiments']['records'][0]['code_commit']='f'*40;write(p,s)
    m=load(run/'manifest.json');m['canonical_inputs']={'sha256':digest(p.read_bytes()),'size_bytes':p.stat().st_size};write(run/'manifest.json',m)
    with pytest.raises(ValueError,match='unversioned change|does not match'):sync_run(run,work/'registries',work)


def test_repeated_runs_reuse_same_scientific_versions(work):
    first=record(work)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',created_at='2026-09-09T00:00:00Z');write(work/'input/manifest.json',m)
    record(work)
    r=load_registries(work/'registries')
    assert len(r['experiments'])==1 and len(r['datasets'])==1 and len(r['validators'])==2 and len(r['runs'])==2
    web_bundle(work/'registries',include_synthetic=True)


def test_experiment_later_version_does_not_break_prior_run(work):
    record(work);old=load_registries(work/'registries')
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',config_version='v2',created_at='2026-09-09T00:00:00Z');m['config']={'test_only':True,'new_setting':True};m['protocol']['version']='test-2';write(work/'input/manifest.json',m)
    record(work);r=load_registries(work/'registries')
    validate_history(r,old)
    assert len({e['id'] for e in r['experiments']})==1 and len(r['experiments'])==2
    b=web_bundle(work/'registries',include_synthetic=True)
    assert len(b['experiments'])==1 and len(b['runs'])==2
    assert {run['experiment']['version'] for run in b['runs']}=={'synthetic-test-1','v2'}


def test_explicit_canonical_experiment_id_survives_recording(work):
    m=load(work/'input/manifest.json');m['canonical_experiment_id']='experiment:stable-exp-001';write(work/'input/manifest.json',m)
    record(work);e=load_registries(work/'registries')['experiments'][0]
    assert e['id']=='experiment:stable-exp-001' and e['experiment_code']=='EXP-001'


def test_sync_is_idempotent_and_can_recover_unpublished_records(work):
    run=record(work)
    expected=load_registries(work/'registries')
    for n,e in envelopes({n:[] for n in REGISTRIES}).items():write(work/'registries'/f'{n}.json',e)
    sync_run(run,work/'registries',work)
    assert load_registries(work/'registries')==expected
    sync_run(run,work/'registries',work)
    assert load_registries(work/'registries')==expected


def test_ablation_and_fractional_quality_retained(work):
    m=load(work/'input/manifest.json');m['ablation']={'study_id':'SAFE-ABLATION','variant_id':'safe-only','components':[]};write(work/'input/manifest.json',m)
    edit_csv(work/'input/predictions.csv',PREDICTION_COLUMNS,lambda rows:rows[0].update(q='0.75',score='0.25'))
    record(work);r=load_registries(work/'registries')
    assert any(p['assessment']['dimensions']['Q']==0.75 for p in r['results'] if p['kind']=='prediction')
    b=web_bundle(work/'registries',include_synthetic=True)
    assert b['results'][0]['analysis']['ablation']==m['ablation']


def test_config_values_redacted_at_every_nesting_level(work):
    m=load(work/'input/manifest.json');m['attack_methods'][0]['config']={'private':'LOCAL_SENTINEL'};m['models'][0]['config']={'private':'LOCAL_SENTINEL'};write(work/'input/manifest.json',m)
    record(work)
    assert 'LOCAL_SENTINEL' not in json.dumps(web_bundle(work/'registries',include_synthetic=True))


def test_registry_lock_blocks_concurrent_writes(work):
    with write_lock(work/'registries'):
        with pytest.raises(ValueError,match='already in progress'):
            with write_lock(work/'registries'):pass


def test_committed_source_workbook_absent_and_only_one_production_export():
    assert not list((ROOT/'apps/web/data').glob('*.json'))==[]
    assert {p.name for p in (ROOT/'apps/web/data').glob('*.json')}=={'research.json'}
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    assert not any(p.lower().endswith('.xlsx') for p in tracked)


def test_validator_revision_preserves_prior_run_endpoint(work):
    record(work)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',config_version='v2',created_at='2026-09-09T00:00:00Z')
    m['validators'][0].update(version='test-2',success_construct='new-synthetic-endpoint')
    m['protocol']['version']='test-2'
    write(work/'input/manifest.json',m);record(work)
    b=web_bundle(work/'registries',include_synthetic=True)
    by_run={r['id']:r for r in b['runs']}
    first=by_run[ident('run','RUN-SAFE-TEST-001')]
    second=by_run[ident('run','RUN-SECOND')]
    assert first['validator_definitions'][0]['success_definition']=='synthetic-card-match'
    assert second['validator_definitions'][0]['success_definition']=='new-synthetic-endpoint'
    assert first['validator_definitions'][0]['id']==second['validator_definitions'][0]['id']


def test_captured_definition_checksum_tampering_blocks_web(work):
    record(work);r=load_registries(work/'registries');artifact=r['datasets'][0]['manifest']
    (work/artifact['uri']).write_text('Changed harmless metadata')
    with pytest.raises(ValueError,match='hash mismatch'):web_bundle(work/'registries')


def test_same_version_modified_code_or_config_cannot_record_a_new_run(work):
    record(work)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',created_at='2026-09-09T00:00:00Z',code_commit='a'*40)
    write(work/'input/manifest.json',m)
    with pytest.raises(ValueError,match='unversioned'):record(work)
    assert not (work/'results/runs/RUN-SECOND').exists()


def test_formula_denominators_are_distinct_from_paired_cohort_size(work):
    def predictions(rows):
        for row in rows:row.update(status='ok',predicted_success='1',functional_level='',score='',error_type='')
    def labels(rows):
        for row in rows:row['label']='1'
    edit_csv(work/'input/predictions.csv',PREDICTION_COLUMNS,predictions)
    edit_csv(work/'input/human_labels.csv',LABEL_COLUMNS,labels)
    record(work)
    b=web_bundle(work/'registries',include_synthetic=True)
    f1=next(m for m in b['metrics'] if m['name']=='f1')
    assert f1['value']==1 and f1['denominator']==8 and f1['cohort_size']==4
    mcc=next(m for m in b['metrics'] if m['name']=='mcc')
    assert mcc['value'] is None and mcc['denominator']==0 and mcc['cohort_size']==4


def test_git_history_rejects_an_intermediate_unversioned_edit_even_if_restored(work):
    repo=work/'git-history';repo.mkdir();(repo/'registries').mkdir()
    initial={n:[] for n in REGISTRIES}
    paper=load(ROOT/'examples/registries/papers.json')['records'][0]
    paper.update(id='paper:safe-history',record_kind='synthetic',version='1',notes='Safe history test.')
    initial['papers']=[paper]
    for n,e in envelopes(initial).items():write(repo/'registries'/f'{n}.json',e)
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True,stderr=subprocess.STDOUT).strip()
    git('init');git('config','user.name','Safe Fixture');git('config','user.email','fixture@example.invalid')
    git('add','.');git('commit','-m','Initial synthetic history');baseline=git('rev-parse','HEAD')
    p=repo/'registries/papers.json';original=p.read_bytes();changed=load(p);changed['records'][0]['title']='Unversioned changed title';write(p,changed)
    git('add','.');git('commit','-m','Invalid unversioned edit')
    p.write_bytes(original);git('add','.');git('commit','-m','Restore final values')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/check_registry_history.py'),'--base',baseline],cwd=repo,capture_output=True,text=True)
    assert result.returncode==1 and 'immutable' in result.stderr


def test_final_configuration_cannot_change_under_same_frozen_protocol(work):
    record(work)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',config_version='v2',created_at='2026-09-09T00:00:00Z')
    m['config']={'test_only':True,'changed_after_freeze':True};write(work/'input/manifest.json',m)
    with pytest.raises(ValueError,match='same frozen protocol'):record(work)
    assert not (work/'results/runs/RUN-SECOND').exists()


def test_protocol_definition_cannot_change_without_version_bump(work):
    record(work)
    m=load(work/'input/manifest.json');m.update(run_id='RUN-SECOND',config_version='v2',created_at='2026-09-09T00:00:00Z')
    m['protocol']['success_definition']='Changed synthetic endpoint';write(work/'input/manifest.json',m)
    with pytest.raises(ValueError,match='protocol changed'):record(work)
