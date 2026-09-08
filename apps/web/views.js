(function (root) {
  'use strict';
  const D = typeof module !== 'undefined' && module.exports ? require('./data.js') : root.ResearchData;
  const ROUTES = Object.freeze({
    overview: ['Research overview', 'Follow the evidence. See what is ready for the next study.'],
    literature: ['Literature explorer', 'Search the reading queue and inspect evidence, interpretations and unanswered questions.'],
    validators: ['Validators', 'Track candidate methods, success definitions and implementation readiness.'],
    benchmarks: ['Benchmarks', 'Review candidate benchmarks and the metadata needed before selecting data.'],
    domains: ['Domains & subdomains', 'Inspect the study scope and the decisions still needed to select a first case.'],
    experiments: ['Experiment registry', 'Keep planned studies, run metadata and measured outcomes distinct.'],
    results: ['Results', 'Inspect recorded measurements alongside their run provenance and success definitions.'],
    gaps: ['Gaps & novelty threats', 'Test the proposed contribution against the closest work. Novelty remains an evidence question.']
  });
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const label = value => value !== null && value !== undefined && value !== '' ? escape(value) : 'Not recorded';
  const badge = (value, kind = '') => `<span class="badge ${escape(kind)}">${escape(value)}</span>`;
  function link(url, title, className = '') {
    const safe = D.safeURL(url);
    if (!safe) return `<span class="muted">${escape(title)} · link not recorded</span>`;
    return `<a href="${escape(safe)}" class="${escape(className)}"${/^https?:/i.test(safe) ? ' target="_blank" rel="noopener noreferrer"' : ''}>${escape(title)}</a>`;
  }
  const sourceLinks = record => {
    const sources = D.sources(record);
    return `<div class="source-links">${sources.length ? sources.map(s => link(s.url, s.locator || 'Source')).join('') : '<span>Source not recorded</span>'}</div>`;
  };
  const list = (items, empty = 'Not recorded.') => D.strings(items).length
    ? `<ul class="compact-list">${D.strings(items).map(item => `<li>${escape(item)}</li>`).join('')}</ul>`
    : `<p class="muted">${escape(empty)}</p>`;
  const metadata = entries => `<dl class="metadata-grid">${entries.map(([key,value]) => `<div><dt>${escape(key)}</dt><dd>${label(value)}</dd></div>`).join('')}</dl>`;
  const sectionHead = (title, eyebrow = '', action = '') => `<div class="panel-heading"><div>${eyebrow ? `<p class="eyebrow">${escape(eyebrow)}</p>` : ''}<h2>${escape(title)}</h2></div>${action}</div>`;
  const routeLink = (route, title, button = false) => `<a href="#${escape(route)}"${button ? ' class="button secondary"' : ''}>${escape(title)}</a>`;
  const artifactLinks = artifacts => `<div class="source-links">${(artifacts || []).map(a=>link('../../'+a.uri,a.description || 'Artifact')).join('')}</div>`;
  const legend = () => `<div class="legend" aria-label="Evidence categories"><span>Evidence key</span>${badge('Measured result','measured')}${badge('Paper evidence','paper')}${badge('Project interpretation','interpretation')}${badge('Unresolved question','question')}${badge('Planned experiment','planned')}</div>`;
  function empty(title, detail, route, action, zero=true) {
    return `<section class="panel empty-state">${zero ? '<div class="empty-number" aria-hidden="true">0</div>':''}<h2>${escape(title)}</h2><p>${escape(detail)}</p>${route ? routeLink(route,action,true):''}</section>`;
  }
  function stat(title,value,note,color,route) {
    return `<a class="summary-card ${color}-card" href="#${route}"><span>${escape(title)}</span><strong>${escape(value)}</strong><small>${escape(note)}</small></a>`;
  }
  function readiness(data) {
    const r=data.readiness;
    const items=[['Review the closest papers',`${r.papers_by_status.verified} verified; ${r.papers_by_status.listed} listed. Review status is recorded explicitly.`,'literature'],
      ['Select the study scope',`${data.domains.filter(d=>d.level==='subdomain' && d.status==='selected').length} selected subdomains. Candidate choices remain provisional.`,'domains'],
      ['Freeze data and protocol',`${data.datasets.filter(d=>d.status==='frozen').length} frozen datasets. Development, pilot and final test must stay separate.`,'experiments'],
      ['Check the validators',`${r.validators_implemented} implemented. Imported external decisions do not establish implementation readiness.`,'validators']];
    return `<section class="panel">${sectionHead('Before the first study','Research readiness')}<ul class="readiness">${items.map(([title,detail,route])=>`<li><strong>${routeLink(route,title)}</strong><p>${escape(detail)}</p></li>`).join('')}</ul></section>`;
  }
  function overview(data) {
    const r=data.readiness;
    return `<div class="summary-grid">${stat('Papers in the registry',r.papers,`${r.papers_by_status.verified} verified · stable IDs`,'blue','literature')}${stat('Validator candidates',r.validators,`${r.validators_implemented} implemented`,'purple','validators')}${stat('Registered experiments',r.experiments,`${r.experiments_completed} recorded as completed`,'green','experiments')}${stat('Measured result records',r.measured_results,'Reproduced from immutable run artifacts','peach','results')}</div>${legend()}<div class="content-grid"><section class="panel focus-panel">${sectionHead('Research Platform v0.1','Evidence before conclusions')}${badge('Project interpretation','interpretation')}<p class="statement">A shared workspace for literature, research readiness and reproducible evaluator comparisons.</p><p>Review the closest work, define the protocol and inspect measurements alongside their evidence.</p>${link('../../research/CONTROL_ROOM_SYNTHESIS_2026-09-08.md','Read the provisional control-room synthesis')}${metadata(D.REVIEW_STATES.map(s=>[s,r.papers_by_status[s]]))}</section>${readiness(data)}</div><div class="content-grid"><section class="panel">${sectionHead('Open research questions')}${list(data.open_questions.slice(0,5).map(q=>q.text),'No questions recorded. This does not establish completeness.')}${routeLink('gaps','Review questions and novelty threats',true)}</section><section class="panel">${sectionHead('Traceable workflow')}<p>Import literature → validate registries → rebuild dashboard data.</p><p>Record locally collected outputs → verify immutable artifacts → inspect results.</p>${link('../../docs/PLATFORM_QUICKSTART.md','Open the easy Python + Live Server guide')}</section></div><div class="notice"><p>${escape(data.novelty_note)}</p></div>`;
  }
  function paperCard(p,forceOpen=false) {
    const claims=p.paper_demonstrates.length ? `<ul class="compact-list">${p.paper_demonstrates.map(c=>`<li><strong>${escape(c.topic)}</strong> ${badge(c.verification_status,c.verification_status==='verified'?'paper':'question')}<p>${escape(c.claim)}</p>${link(p.sources.find(s=>s.id===c.source_id)?.url,c.locator)}</li>`).join('')}</ul>` : '<p class="muted">No paper findings extracted. Listed intake is not verified evidence.</p>';
    return `<article class="panel paper-card" id="paper-${escape(p.id)}"><div class="panel-heading"><div><span class="id">${escape(p.id)} · v${escape(p.version)}</span><h2>${escape(p.title)}</h2></div>${badge(p.evidence_status,p.evidence_status==='verified'?'paper':'question')}</div>${metadata([['Year',p.year],['Venue / identifier',p.venue_or_identifier]])}<div class="badges">${badge('Novelty: '+p.novelty.status,'question')}</div><div class="source-links">${routeLink('literature/'+encodeURIComponent(p.id),'Link to record')}</div>${sourceLinks(p)}<details${forceOpen?' open':''}><summary>Evidence, interpretation & provenance</summary><div class="evidence-grid"><section class="evidence-box"><h3>${badge('Paper evidence','paper')}</h3>${claims}</section><section class="evidence-box"><h3>${badge('Project interpretation','interpretation')}</h3>${list(p.our_interpretation.map(i=>i.text))}</section><section class="evidence-box"><h3>${badge('Unresolved question','question')}</h3>${list(p.open_questions.map(q=>q.text))}</section></div>${metadata([['Reviewer',p.review?.reviewer],['Reviewed at',p.review?.reviewed_at],['Review notes',p.review?.notes],['Record timestamp',p.timestamp]])}<h3>Original intake provenance</h3><p class="meta">Source file hashes, sheet/row, every original column, cell locations, formulas and hyperlinks are retained in the linked intake artifacts. Intake content is not independently verified.</p>${artifactLinks(p.intake_artifacts)}</details></article>`;
  }
  function paperMatches(data,filters={},selected='') {
    return D.filterPapers(data.papers,filters).filter(p=>!selected || p.id===selected);
  }
  function paperResults(data,filters,selected) {
    const papers=paperMatches(data,filters,selected);
    return papers.length ? papers.map(p=>paperCard(p,Boolean(selected))).join('') : empty('No matching papers','Try another title, domain or review state. Missing results do not establish a gap.',null,null,false);
  }
  function literature(data,filters={},selected='') {
    return `<div class="notice"><p>Listed → screened → deep-reviewed → verified. Extracted findings retain their actual review state. Each paper keeps one stable ID across revisions.</p></div>${data.duplicate_candidates.length ? `<details class="panel"><summary>${data.duplicate_candidates.length} duplicate candidate groups · no automatic merging</summary>${data.duplicate_candidates.map(g=>`<p>${escape(g.reason)}: ${escape(g.value)}</p><div class="source-links">${g.paper_ids.map(id=>routeLink('literature/'+encodeURIComponent(id),id)).join('')}</div>`).join('')}</details>`:''}<form class="toolbar" id="paper-filters" role="search"><label>Search papers<input type="search" name="query" value="${escape(filters.query)}" placeholder="Title, ID, evidence or question" autocomplete="off"></label><label>Review status<select name="status"><option value="">All review stages</option>${D.REVIEW_STATES.map(s=>`<option value="${s}"${filters.status===s?' selected':''}>${s}</option>`).join('')}</select></label><label>Domain<select name="domain"><option value="">All domains</option>${data.domains.map(d=>`<option value="${escape(d.id)}"${filters.domain===d.id?' selected':''}>${escape(d.name)}</option>`).join('')}</select></label><button type="button" class="button secondary" id="clear-filters">Clear filters</button></form>${selected?routeLink('literature','Show all papers'):''}<p class="record-count" id="paper-count" role="status" aria-live="polite">${paperMatches(data,filters,selected).length} of ${data.papers.length} records</p><div id="paper-results">${paperResults(data,filters,selected)}</div>`;
  }
  function relatedPapers(data,ids) {
    return `<div class="source-links">${(ids||[]).map(id=>routeLink('literature/'+encodeURIComponent(id),data.papers.find(p=>p.id===id)?.title || id)).join('')}</div>`;
  }
  function registry(data,name) {
    if (!data[name].length) return empty(`No ${name} registered`,'Add source-linked definitions when ready. Empty records do not establish coverage.');
    return `<div class="card-grid">${data[name].map(r=>`<article class="panel">${sectionHead(r.name,r.id)}${badge(r.status || 'candidate','planned')}${badge('Project interpretation','interpretation')}<p>${escape(r.notes || r.description)}</p>${name==='validators'? metadata([['Definition version',r.version],['Evaluation types',r.evaluation_types.join(', ')],['Success definition',r.success_definition],['Code execution',r.executes_code===null?null:String(r.executes_code)],['Code commit',r.code_commit]])+artifactLinks([r.implementation,r.capture_artifact].filter(Boolean)) : metadata([['Registry revision',r.version],['Upstream version',r.provenance.upstream_version],['Licence',r.provenance.license],['Redistribution',r.provenance.redistribution]])+sourceLinks({sources:[r.provenance.source]})}${relatedPapers(data,r.paper_ids)}</article>`).join('')}</div>`;
  }
  function domains(data) {
    function node(r,nested=false) {
      return `<${nested?'section':'article'} class="${nested?'domain-child':'panel'}">${sectionHead(r.name,r.id)}${badge(r.status,'planned')}${badge('Project interpretation','interpretation')}<p>${escape(r.definition)}</p><p class="muted">${escape(r.notes)}</p>${list(r.inclusion_criteria,'Inclusion criteria not fixed.')}${relatedPapers(data,r.paper_ids)}${data.domains.filter(d=>d.parent_id===r.id).map(c=>node(c,true)).join('')}</${nested?'section':'article'}>`;
    }
    return data.domains.length ? `<p class="record-count">${data.domains.filter(d=>!d.parent_id).length} domains · ${data.domains.filter(d=>d.parent_id).length} subdomains</p><div class="card-grid">${data.domains.filter(d=>!d.parent_id).map(d=>node(d)).join('')}</div>` : empty('No domains registered','Selection remains open.');
  }
  function experiments(data) {
    return data.experiments.length ? `<div class="card-grid">${data.experiments.map(e=>`<article class="panel">${sectionHead(e.experiment_code || e.name,e.id)}${badge(e.status,e.status==='planned'?'planned':'')}${badge(e.split+' split','question')}${e.split==='pilot'?badge('Pilot / kill-test','planned'):''}${e.record_kind==='synthetic'?badge('Synthetic fixture · not a finding','warning'):''}<p>${escape(e.notes)}</p>${metadata([['Revision',e.version],['Purpose',e.purpose],['Dataset',e.dataset.id+' @ '+e.dataset.version],['Models',e.models.map(m=>m.name+' @ '+m.version).join(', ')],['Attack methods',e.attack_methods.map(a=>a.name+' @ '+a.version).join(', ')],['Validators',e.validators.map(v=>v.id+' @ '+v.version).join(', ')],['Code commit',e.code_commit],['Protocol frozen',e.protocol_freeze]])}${artifactLinks([e.protocol].filter(Boolean))}</article>`).join('')}</div>` : `<div class="content-grid">${empty('No experiments registered yet','The planned kill-test has not been registered or run. Pilot data must remain distinct from development and final test.','results','View result readiness')}${readiness(data)}</div>`;
  }
  const metricValue=m=>m.value===null?'Not computed':m.unit==='ratio'?(100*m.value).toFixed(2)+'%':m.unit==='percentage_points'?m.value.toFixed(2)+' pp':String(m.value);
  function table(headers,rows,caption='') {
    return `<div class="table-scroll"><table class="data-table">${caption?`<caption>${escape(caption)}</caption>`:''}<thead><tr>${headers.map(h=>`<th scope="col">${escape(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${escape(v ?? 'Not computed')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function resultCard(r,data) {
    const run=data.runs.find(run=>run.id===r.run_id), exp=run.experiment;
    const validator=run.validator_definitions.find(v=>v.id===r.validator.id && v.version===r.validator.version);
    const detail=r.analysis?.evaluators[r.validator.id];
    return `<article class="panel paper-card">${sectionHead(validator?.name || r.validator.id,exp.experiment_code+' · '+r.run_id)}${badge(r.record_kind==='synthetic'?'Synthetic test output · not a research finding':'Measured result',r.record_kind==='synthetic'?'warning':'measured')}${badge(exp.split+' split','planned')}${metadata([['Success definition',validator?.success_definition],['Validator version',r.validator.version],['Dataset version',exp.dataset.version],['Purpose',exp.purpose]])}${table(['Metric','Value','Denominator'],r.metrics.map(m=>[m.name,metricValue(m),m.denominator]),'Undefined metrics remain null. Each run, split and endpoint is kept separate.')}${detail?`<details><summary>Coverage, FX and human-reference comparison</summary>${table(['Coverage item','Cases'],Object.entries(detail.coverage))}${table(['ASR','Value'],Object.entries(detail.asr))}${table(['Compared with humans','Value'],Object.entries(detail.versus_human))}</details>`:''}<details><summary>Run provenance and source artifacts</summary>${metadata([['Code commit',r.provenance.code_commit],['Run input hash',run.inputs_sha256],['Experiment hash',run.experiment_sha256],['Timestamp',run.timestamp],['Ablation',exp.ablation?JSON.stringify(exp.ablation):null]])}${artifactLinks(r.provenance.artifacts)}</details></article>`;
  }
  function results(data) {
    if (!data.results.length) return empty('No measured results recorded','There are no production run measurements. Accuracy, F1, ASR and rankings will appear after verified run recording.','experiments','Check experiment readiness');
    const analyses=[...new Map(data.results.filter(r=>r.analysis).map(r=>[r.run_id,r.analysis])).entries()];
    return data.results.map(r=>resultCard(r,data)).join('')+analyses.map(([run,a])=>`<section class="panel">${sectionHead('Evaluator comparisons & descriptive rankings',run)}<p>ASR differences are evaluator A minus evaluator B on shared determinate cases, in percentage points.</p>${table(['Evaluator A','Evaluator B','Paired cases','ASR difference (pp)','Disagreement rate'],a.evaluator_comparisons.map(c=>[c.evaluator_a,c.evaluator_b,c.n,c.asr_difference_pp_a_minus_b,c.disagreement_rate]))}${Object.entries(a.rankings).map(([dimension,r])=>`<h3>${escape(dimension)}</h3><p>${escape(r.status)}${r.reason?' · '+escape(r.reason):''}</p>${Object.entries(r.by_evaluator).map(([v,rows])=>table(['Evaluator','Condition','ASR','Rank'],rows.map(row=>[v,row.condition_id,row.asr,row.rank]))).join('')}`).join('')}<details><summary>Grouped analysis and ablation metadata</summary><pre>${escape(JSON.stringify({groups:a.groups,ablation:a.ablation},null,2))}</pre></details></section>`).join('');
  }
  function gaps(data) {
    return `<div class="notice"><h2>Novelty is not established</h2><p>${escape(data.novelty_note)}</p></div><div class="card-grid">${data.novelty_threats.map(t=>`<article class="panel">${sectionHead(t.title)}${badge(t.status,'question')}${badge('Project interpretation','interpretation')}<p>${escape(t.rationale)}</p>${relatedPapers(data,[t.paper_id])}</article>`).join('')}${data.open_questions.map(q=>`<article class="panel">${badge('Unresolved question','question')}<h2>${escape(q.text)}</h2>${relatedPapers(data,[q.paper_id])}</article>`).join('')}</div>${!data.novelty_threats.length&&!data.open_questions.length?empty('No questions or threats recorded','An empty registry is not evidence of novelty.'):''}`;
  }
  function render(route,data,filters={},selected='') {
    if (data.error) return `<section class="notice error" role="alert"><h2>Research data unavailable</h2><p>${escape(data.error)}</p><p>Rebuild all data with Python, then use Refresh data. Open index.html with VS Code Live Server.</p></section>`;
    const prefix=data.include_synthetic?'<div class="notice error"><h2>Synthetic preview enabled</h2><p>Fixture outputs are test data and must not be reported as research findings.</p></div>':'';
    const views={overview,literature,validators:d=>registry(d,'validators'),benchmarks:d=>registry(d,'benchmarks'),domains,experiments,results,gaps};
    return prefix+(Object.hasOwn(views,route)?views[route](data,filters,selected):empty('View not found','Choose a workspace view.','overview','Return to overview',false));
  }
  const api={ROUTES,escape,render,paperResults,paperMatches,resultCard};
  if(typeof module!=='undefined' && module.exports) module.exports=api; else root.ResearchViews=api;
})(typeof window==='undefined'?globalThis:window);
