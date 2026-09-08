/* Canonical contract checks and safe in-memory rendering fixtures. No npm. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const D=require('../data.js'),V=require('../views.js');
const shipped=()=>JSON.parse(fs.readFileSync(path.join(__dirname,'../data/research.json'),'utf8'));
const fresh=()=>D.parseBundle(shipped());

function emptyBundle() {
 const d=fresh();for(const n of Object.keys(D.COLLECTIONS))d[n]=[];
 for(const n of ['paper_evidence','verified_paper_evidence','metrics','open_questions','novelty_threats','duplicate_candidates'])d[n]=[];
 d.readiness={...Object.fromEntries(Object.keys(D.COLLECTIONS).map(n=>[n,0])),papers_by_status:Object.fromEntries(D.REVIEW_STATES.map(s=>[s,0])),validators_implemented:0,experiments_completed:0,measured_results:0};
 return d;
}
test('shipped data obeys canonical provenance without locking future review stages',()=>{
 const d=fresh();assert.equal(d.papers.length,d.readiness.papers);
 assert.ok(d.papers.filter(p=>p.evidence_status==='listed').every(p=>p.paper_demonstrates.length===0));
 assert.ok(d.papers.every(p=>p.record_kind==='research'));
 assert.doesNotMatch(JSON.stringify(d),/"id":"WEB-/);
});
test('all eight production views render without undefined or NaN content',()=>{
 const d=fresh();assert.equal(Object.keys(V.ROUTES).length,8);
 for(const route of Object.keys(V.ROUTES))assert.doesNotMatch(V.render(route,d),/undefined|NaN/);
 const zero=emptyBundle();assert.match(V.render('results',zero),/No measured results recorded/);assert.doesNotMatch(V.render('results',zero),/0\.00%/);
 assert.match(V.render('experiments',zero),/No experiments registered yet/);
 assert.match(V.render('constructor',d),/View not found/);
});
test('only the canonical contract is accepted',()=>{
 for(const bad of [[],{schema_version:1,records:[]},{...shipped(),contract:'legacy'}])assert.throws(()=>D.parseBundle(bad),/Unsupported/);
 const d=shipped();delete d.runs;assert.throws(()=>D.parseBundle(d),/Missing/);
});
test('duplicate stable IDs and old review states are rejected',()=>{
 let d=shipped();d.papers.push(d.papers[0]);assert.throws(()=>D.parseBundle(d),/Duplicate ID/);
 d=shipped();d.papers[0].evidence_status='unreviewed';assert.throws(()=>D.parseBundle(d),/review state/);
});
test('templates and implicit synthetic records never parse as production',()=>{
 for(const kind of ['template','synthetic']){const d=shipped();d.papers[0].record_kind=kind;assert.throws(()=>D.parseBundle(d),/Template\/synthetic/);}
 const d=shipped();d.include_synthetic=true;d.papers[0].record_kind='synthetic';D.parseBundle(d);
 assert.match(V.render('overview',d),/Synthetic preview enabled/);
});
test('loading fetches exactly one canonical file',async()=>{
 const calls=[];const d=await D.loadAll(async(url)=>{calls.push(url);return {ok:true,json:async()=>shipped()}});
 assert.deepEqual(calls,['data/research.json']);assert.equal(d.papers.length,shipped().papers.length);
});
test('failed fetch and malformed data display unavailable, never false zero',async()=>{
 for(const response of [{ok:false,status:404},{ok:true,json:async()=>({broken:true})}]){
  const d=await D.loadAll(async()=>response);assert.ok(d.error);
  for(const route of Object.keys(V.ROUTES)){const html=V.render(route,d);assert.match(html,/unavailable/);assert.doesNotMatch(html,/empty-number|No measured results recorded/);}
 }
});
test('literature query, status, domain filtering and stable deep links',()=>{
 const d=fresh(),p=d.papers[0];p.domain_ids=['domain:filter-fixture'];
 assert.equal(D.filterPapers(d.papers,{query:p.id}).length,1);
 assert.equal(D.filterPapers(d.papers,{domain:'domain:filter-fixture'}).length,1);
 assert.equal(D.filterPapers(d.papers,{status:'verified'}).length,d.papers.filter(p=>p.evidence_status==='verified').length);
 assert.equal(V.paperMatches(d,{},p.id).length,1);
 assert.match(V.render('literature',d,{},p.id),/details open/);
 d.duplicate_candidates=[{reason:'title',value:'safe fixture',paper_ids:[d.papers[0].id,d.papers[1].id]}];
 assert.match(V.render('literature',d),/duplicate candidate groups/);
});
test('source URLs and HTML are escaped',()=>{
 for(const url of ['javascript:alert(1)','data:text/html,x','//evil.invalid','https://u:p@example.invalid','/absolute','http://example.invalid/\n'])assert.equal(D.safeURL(url),null);
 assert.ok(D.safeURL('../../literature/intake/safe.json'));
 const d=fresh();d.papers[0].title='<img src=x onerror="evil()">';d.papers[0].sources=[{id:'source:x',url:'javascript:evil()',locator:'<script>'}];
 const html=V.render('literature',d,{},d.papers[0].id);assert.doesNotMatch(html,/<img|<script|href="javascript/);assert.match(html,/&lt;img/);
});
test('screened extraction displays its actual review state and separate categories',()=>{
 const d=fresh(),p=d.papers[0];p.evidence_status='screened';p.sources=[{id:'source:safe',url:'https://example.invalid/safe',locator:'Safe fixture'}];
 p.paper_demonstrates=[{id:'evidence:safe',topic:'Fixture',claim:'Safe extracted evidence.',source_id:'source:safe',locator:'p.1',verification_status:'unverified'}];
 p.our_interpretation=[{id:'interpretation:safe',text:'Separate interpretation.',evidence_ids:['evidence:safe']}];
 p.open_questions=[{id:'question:safe',text:'Separate question?'}];D.parseBundle(d);
 const html=V.render('literature',d,{},p.id);
 for(const text of ['screened','unverified','Paper evidence','Project interpretation','Unresolved question','Safe extracted evidence.','Separate interpretation.','Separate question?'])assert.ok(html.includes(text));
});
test('unlinked extraction is rejected',()=>{
 const d=fresh();d.papers[0].paper_demonstrates=[{source_id:'source:missing'}];assert.throws(()=>D.parseBundle(d),/Unlinked/);
});
test('domain cycles and dangling parents fail closed',()=>{
 let d=shipped();d.domains[0].parent_id=d.domains[0].id;assert.throws(()=>D.parseBundle(d),/hierarchy/);
 d=shipped();d.domains[1].parent_id='domain:missing';assert.throws(()=>D.parseBundle(d),/hierarchy/);
});
test('novelty questions preserve explicit uncertainty',()=>{
 const html=V.render('gaps',fresh());assert.match(html,/Novelty is not established/);assert.match(html,/Missing literature never establishes/);assert.match(html,/Unresolved question/);
});
test('navigation shell stays responsive, keyboard accessible and build-free',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');const css=fs.readFileSync(path.join(__dirname,'../styles.css'),'utf8');
 for(const route of Object.keys(V.ROUTES))assert.ok(html.includes(`href="#${route}"`));
 assert.match(html,/aria-expanded="false"/);assert.match(html,/skip-link/);assert.match(css,/@media/);
 assert.doesNotMatch(html,/node_modules|type="module"|https?:\/\/.*\.js/);
});
test('canonical asset paths remain local and stable',()=>{
 const d=fresh();for(const p of d.papers)for(const a of p.intake_artifacts){assert.ok(D.safeURL('../../'+a.uri));assert.match(a.sha256,/^[a-f0-9]{64}$/);}
});
