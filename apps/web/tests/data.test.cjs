/* Safe in-memory fixtures only. None are exported into apps/web/data/. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const D = require('../data.js');
const V = require('../views.js');
const root = path.join(__dirname,'..');
function shipped() {
  return Object.fromEntries(['project',...Object.keys(D.COLLECTIONS)].map(name => {
    const payload = JSON.parse(fs.readFileSync(path.join(root,'data',`${name}.json`),'utf8'));
    return [name,{status:'ready',records:name === 'project' ? D.parseProject(payload) : D.parseCollection(name,payload)}];
  }));
}
function fixture() {
  const data = shipped();
  data.experiments.records = [{experiment_id:'TEST-EXP',status:'completed',title:'Safe fixture'}];
  data.validators.records = [{validator_id:'TEST-VAL',name:'Safe fixture validator'}];
  const result = {result_id:'TEST-RESULT',experiment_id:'TEST-EXP',validator_id:'TEST-VAL',kind:'measured',
    sample_size:2, success_definition:'A benign fixture has the expected label.',
    metrics:{accuracy:0,precision:null,recall:1,f1:0,asr_difference:-0.5},comparison:'Fixture evaluator minus reference evaluator on identical cases.',
    provenance:{run_id:'TEST-RUN',dataset_version:'safe-fixture-v1',validator_version:'test-v1',
      model:'test-only',attack_method:'none — benign fixture',config_version:'test-v1',human_labels_version:'test-v1',
      code_commit:'a'.repeat(40),timestamp:'2026-09-08T00:00:00Z',split:'test',
      artifacts:{manifest:'data/test/manifest.json',predictions:'data/test/predictions.csv',metrics:'data/test/metrics.json',human_labels:'data/test/labels.csv'}}};
  data.results.records = [result];
  return {data,result};
}
test('shipped registries validate and contain no measured experiment outputs',() => {
  const data=shipped();
  assert.equal(data.results.records.length,0);
  assert.equal(data.experiments.records.length,0);
  assert.ok(data.papers.records.length>0);
  assert.ok(data.papers.records.every(p=>p.evidence_status==='unreviewed' && p.paper_demonstrates.length===0));
  assert.equal(data.validators.records.filter(v=>v.status==='implemented').length,0);
});
test('all eight production views render from the shipped data without undefined content',() => {
  const data=shipped();
  for(const route of Object.keys(V.ROUTES)) {
    const html=V.render(route,data);
    assert.ok(html.length>100,route);
    assert.doesNotMatch(html,/undefined|NaN/,route);
  }
  assert.match(V.render('results',data),/No measured results recorded/);
  assert.doesNotMatch(V.render('results',data),/0\.00%/);
  assert.match(V.render('experiments',data),/No experiments registered yet/);
  assert.match(V.render('constructor',data),/View not found/);
});
test('array and named/enveloped importer outputs are accepted; IDs and statuses are enforced',() => {
  const paper=shipped().papers.records[0];
  for(const payload of [[paper],{papers:[paper]},{schema_version:1,records:[paper]}]) assert.equal(D.parseCollection('papers',payload).length,1);
  assert.throws(()=>D.parseCollection('papers',{schema_version:2,records:[]}),/Unsupported/);
  assert.throws(()=>D.parseCollection('papers',{records:{}}),/array/);
  assert.throws(()=>D.parseCollection('papers',[paper,paper]),/Duplicate/);
  assert.throws(()=>D.parseCollection('papers',[{...paper,paper_id:''}]),/paper_id/);
  assert.throws(()=>D.parseCollection('papers',[{...paper,evidence_status:'verified'}]),/direct/);
  assert.throws(()=>D.parseCollection('papers',[{...paper,evidence_status:'made-up'}]),/invalid/);
  assert.throws(()=>D.parseCollection('papers',[{...paper,paper_demonstrates:'claim'}]),/array/);
});
test('domain trees reject missing parents and cycles',() => {
  assert.throws(()=>D.parseCollection('domains',[{domain_id:'a',parent_id:'missing'}]),/unknown parent/);
  assert.throws(()=>D.parseCollection('domains',[{domain_id:'a',parent_id:'b'},{domain_id:'b',parent_id:'a'}]),/cyclic/);
});
test('paper search combines query, status and domain and preserves input records',() => {
  const p=shipped().papers.records[0];
  const papers=[{...p,domain:'Test scope'}, {...p,paper_id:'p2',title:'Second',domain:'Other',evidence_status:'screened'}];
  assert.equal(D.filterPapers(papers,{query:'jAwS',status:'unreviewed',domain:'Test scope'}).length,1);
  assert.equal(D.filterPapers(papers,{query:'JAWS',status:'screened'}).length,0);
  assert.equal(D.filterPapers(papers,{query:'   '}).length,2);
  assert.equal(papers[0].domain,'Test scope');
  assert.match(V.render('literature',shipped(),{},p.paper_id),/<details open>/);
  assert.match(V.render('literature',shipped(),{},'not-present'),/No matching papers/);
});
test('registry HTML and source links cannot inject executable markup',() => {
  const data=shipped();
  data.papers.records[0] = {...data.papers.records[0],title:'<img src=x onerror=alert(1)>',
    url:'javascript:alert(1)',paper_demonstrates:['UNSOURCED_CLAIM'],
    our_interpretation:['<script>bad()</script>'],source_links:[{label:'bad',url:'javascript:alert(1)'}]};
  const html=V.render('literature',data);
  assert.doesNotMatch(html,/<img|<script|href="javascript:|UNSOURCED_CLAIM/);
  assert.match(html,/&lt;img/);
  assert.match(html,/Claims withheld/);
  for(const url of ['javascript:alert(1)','data:text/html,bad','//example.com','https:\\evil.test','https://name:secret@example.com','https://exa\nmple.com']) assert.equal(D.safeURL(url),null,url);
  assert.equal(D.safeURL('../../results/runs/run-001/manifest.json'),'../../results/runs/run-001/manifest.json');
  assert.ok(D.safeURL('https://example.org/paper'));
});
test('review stage does not rise when fields are populated',() => {
  const data=shipped();
  data.papers.records[0] = {...data.papers.records[0],url:'https://example.org/paper',year:2026,
    validator:'Fixture',success_definition:'Fixture',human_ground_truth:'Fixture'};
  const parsed=D.parseCollection('papers',data.papers.records);
  assert.equal(parsed[0].evidence_status,'unreviewed');
  assert.match(V.render('literature',data),/No paper findings extracted/);
});
test('each fetch failure stays unavailable; successful empty files stay ready',async () => {
  const data=await D.loadAll(async (url,options) => {
    assert.equal(options.cache,'no-store');
    if(url==='data/papers.json') return {ok:false,status:404};
    if(url==='data/validators.json') return {ok:true,json:async()=>{throw new SyntaxError('Invalid JSON')}};
    if(url==='data/project.json') return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,'data/project.json')))};
    return {ok:true,json:async()=>({schema_version:1,records:[]})};
  });
  assert.equal(data.papers.status,'error'); assert.equal(data.validators.status,'error');
  assert.equal(data.results.status,'ready'); assert.equal(data.results.records.length,0);
  assert.match(V.render('overview',data),/Unavailable/);
  assert.match(V.render('literature',data),/HTTP 404/);
  assert.doesNotMatch(V.render('literature',data),/No matching papers/);
});
test('valid result values retain true zero, null and signed percentage-point differences',() => {
  const {data,result}=fixture();
  assert.deepEqual(D.inspectResult(result,data),[]);
  const html=V.render('results',data);
  assert.match(html,/0\.00%/); assert.match(html,/Not measured/); assert.match(html,/-50\.00 pp/);
  assert.match(html,/Held-out test split/); assert.match(html,/test\/manifest.json/);
});
test('results without complete provenance, artifacts, valid metrics or links are withheld',() => {
  const mutations=[
    r=>{delete r.provenance},r=>{delete r.provenance.artifacts.metrics},
    r=>{r.provenance.artifacts.manifest='javascript:alert(1)'},r=>{r.provenance.code_commit='short'},
    r=>{r.provenance.split='combined'},r=>{r.provenance.timestamp='yesterday'},
    r=>{r.experiment_id='absent'},r=>{r.validator_id='absent'},
    r=>{r.metrics.accuracy='0.9'},r=>{r.metrics.accuracy=Infinity},r=>{r.metrics.accuracy=1.1},
    r=>{r.metrics.accuracy=-0.1},r=>{r.sample_size=0},r=>{r.success_definition=''},
    r=>{r.is_example=true},r=>{r.is_synthetic=true},r=>{r.kind='planned'},r=>{r.comparison=null},
    r=>{r.metrics.toString=0.2}
  ];
  for(const mutate of mutations) {
    const {data,result}=fixture();mutate(result);
    const report=D.resultReport(data);
    assert.equal(report.accepted.length,0,String(mutate));
    assert.equal(report.withheld.length,1);
    const html=V.render('results',data);
    assert.match(html,/result records withheld/);
    assert.doesNotMatch(html,/0\.00%/);
  }
});
test('failed required registries cannot produce trusted measured results',() => {
  const {data}=fixture(); data.experiments={status:'error',error:'missing'};
  assert.equal(D.resultReport(data).accepted.length,0);
  assert.match(V.render('results',data),/unavailable/);
});
test('development and test results remain separate with explicit labels',() => {
  const {data,result}=fixture();
  const other=structuredClone(result);other.result_id='TEST-DEV';other.provenance.run_id='DEV-RUN';other.provenance.split='development';
  data.results.records.push(other);
  const html=V.render('results',data);
  assert.match(html,/Development split/);assert.match(html,/Held-out test split/);
  assert.equal((html.match(/class="data-table"/g)||[]).length,2);
});
test('HTML references local existing assets and navigation maps to real views',() => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const match of html.matchAll(/(?:src|href)="([^"#]+\.(?:js|css))"/g)) assert.ok(fs.existsSync(path.join(root,match[1])),match[1]);
  for(const route of Object.keys(V.ROUTES)) assert.ok(html.includes(`href="#${route}"`),route);
  assert.doesNotMatch(html,/https?:\/\/.*\.(?:js|css)/);
});
