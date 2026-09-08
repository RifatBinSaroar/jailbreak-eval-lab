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
  const label = value => D.filled(value) ? escape(value) : 'Not recorded';
  const badge = (value, kind = '') => `<span class="badge ${escape(kind)}">${escape(value)}</span>`;
  function link(url, title, className = '') {
    const safe = D.safeURL(url);
    if (!safe) return `<span class="muted">${escape(title)} · link not recorded</span>`;
    return `<a href="${escape(safe)}" class="${escape(className)}"${/^https?:/i.test(safe) ? ' target="_blank" rel="noopener noreferrer"' : ''}>${escape(title)}</a>`;
  }
  const sourceLinks = record => {
    const sources = D.sources(record);
    return `<div class="source-links">${sources.length ? sources.map(s => link(s.url, s.label || 'Source')).join('') : '<span>Source not recorded</span>'}</div>`;
  };
  const list = (items, empty = 'Not recorded.') => D.strings(items).length
    ? `<ul class="compact-list">${D.strings(items).map(item => `<li>${escape(item)}</li>`).join('')}</ul>`
    : `<p class="muted">${escape(empty)}</p>`;
  const metadata = entries => `<dl class="metadata-grid">${entries.map(([key,value]) => `<div><dt>${escape(key)}</dt><dd>${label(value)}</dd></div>`).join('')}</dl>`;
  const sectionHead = (title, eyebrow = '', action = '') => `<div class="panel-heading"><div>${eyebrow ? `<p class="eyebrow">${escape(eyebrow)}</p>` : ''}<h2>${escape(title)}</h2></div>${action}</div>`;
  const routeLink = (route, title, button = false) => `<a href="#${escape(route)}"${button ? ' class="button secondary"' : ''}>${escape(title)}</a>`;
  function problem(data, name) {
    if (D.available(data, name)) return '';
    return `<section class="notice error" role="alert"><h2>${escape(name === 'project' ? 'Project guidance' : ROUTES[name]?.[0] || name)} unavailable</h2><p>Could not load <code>data/${escape(name)}.json</code>: ${escape(data[name]?.error || 'Data has not loaded.')}</p><p>Check the JSON file and use Refresh data. Open the dashboard with VS Code Live Server; opening the HTML file directly cannot load these records.</p></section>`;
  }
  const legend = () => `<div class="legend" aria-label="Evidence categories"><span>Evidence key</span>${badge('Measured result','measured')}${badge('Paper evidence','paper')}${badge('Project interpretation','interpretation')}${badge('Unresolved question','question')}${badge('Planned experiment','planned')}</div>`;
  function empty(title, detail, route, action, zero = true) {
    return `<section class="panel empty-state">${zero ? '<div class="empty-number" aria-hidden="true">0</div>' : ''}<h2>${escape(title)}</h2><p>${escape(detail)}</p>${route ? routeLink(route,action,true) : ''}</section>`;
  }
  function stat(title, value, note, color, route) {
    return `<a class="summary-card ${color}-card" href="#${route}"><span>${escape(title)}</span><strong>${escape(value)}</strong><small>${escape(note)}</small></a>`;
  }
  function readiness(data) {
    if (!D.available(data, 'project')) return problem(data,'project');
    return `<section class="panel">${sectionHead('Before the first run','Study readiness')}<ul class="readiness">${data.project.records.readiness.map(item => `<li><div class="readiness-title"><strong>${routeLink(ROUTES[item.view] ? item.view : 'overview',item.title)}</strong>${badge(item.status,item.status === 'complete' ? 'measured' : 'question')}</div><p>${escape(item.detail)}</p></li>`).join('')}</ul></section>`;
  }
  function overview(data) {
    const papers = D.records(data,'papers'), validators = D.records(data,'validators');
    const experiments = D.records(data,'experiments');
    const measuredReady = ['results','experiments','validators'].every(name => D.available(data,name));
    const report = D.resultReport(data);
    let html = `<div class="summary-grid">${stat('Papers in the registry',D.available(data,'papers') ? papers.length : 'Unavailable',D.available(data,'papers') ? `${papers.filter(p => p.evidence_status === 'verified').length} verified · includes reading queue` : 'Check the data file','blue','literature')}${stat('Validator candidates',D.available(data,'validators') ? validators.length : 'Unavailable',D.available(data,'validators') ? `${validators.filter(v => v.status === 'implemented').length} marked implemented` : 'Check the data file','purple','validators')}${stat('Registered experiments',D.available(data,'experiments') ? experiments.length : 'Unavailable',D.available(data,'experiments') ? `${experiments.filter(e => e.status === 'completed').length} marked completed` : 'Check the data file','green','experiments')}${stat('Measured result records',measuredReady ? report.accepted.length : 'Unavailable',measuredReady ? `${report.withheld.length} withheld for missing or invalid provenance` : 'Required registry unavailable','peach','results')}</div>`;
    html += legend();
    html += ['papers','validators','benchmarks','domains','experiments','results','gaps'].map(name => problem(data,name)).join('');
    if (!D.available(data,'project')) return html + problem(data,'project');
    const p = data.project.records;
    html += `<div class="content-grid"><section class="panel focus-panel">${sectionHead(D.text(p.direction),'Working hypothesis')}${badge('Project interpretation','interpretation')} ${badge(p.status || 'Status not recorded','question')}<p class="statement">${escape(p.hypothesis)}</p><p>${escape(p.decision)}</p>${metadata([['Lead case-study candidate',p.candidate],['Guidance date',p.as_of]])}<p class="muted">${escape(p.candidate_note)}</p>${sourceLinks(p)}</section>${readiness(data)}</div>`;
    html += `<div class="content-grid"><section class="panel">${sectionHead('Questions the study must answer')}${badge('Unresolved question','question')}${list(p.open_questions)}</section><section class="panel">${sectionHead('Read the current evidence')}${metadata(D.REVIEW_STATES.map(state => [state,D.available(data,'papers') ? String(papers.filter(paper => paper.evidence_status === state).length) : 'Unavailable']))}<p class="muted">${escape(p.scope_note)}</p>${routeLink('literature','Explore the reading queue',true)}</section></div>`;
    html += `<div class="notice"><p>${escape(p.novelty_note)}</p>${routeLink('gaps','Review novelty threats')}</div>`;
    return html;
  }
  const evidenceBox = (title, kind, items, fallback) => `<section class="evidence-box"><h3>${badge(title,kind)}</h3>${list(items,fallback)}</section>`;
  function paperCard(paper, forceOpen = false) {
    const primary = D.hasPaperSource(paper);
    const fields = ['url','year','success_definition','validator','human_ground_truth'];
    const missing = fields.filter(field => paper[field] === null || paper[field] === undefined || paper[field] === '');
    let evidence;
    if (!primary && D.strings(paper.paper_demonstrates).length) evidence = '<p class="muted">Claims withheld: add a direct paper source before displaying paper evidence.</p>';
    else evidence = list(paper.paper_demonstrates,'No paper findings extracted. A reading-queue entry is not verified evidence.');
    const original = paper.original_matrix;
    return `<article class="panel paper-card" id="paper-${escape(paper.paper_id)}"><div class="panel-heading"><div><span class="id">${escape(paper.paper_id)}</span><h2>${escape(paper.title)}</h2></div>${badge(paper.evidence_status,paper.evidence_status === 'verified' ? 'paper' : 'question')}</div><p class="meta">${label(paper.year == null ? null : String(paper.year))} · ${label(paper.venue_or_arxiv)} · ${label(paper.domain)}</p><div class="badges">${badge('Novelty threat: ' + (paper.novelty_threat || 'UNKNOWN'),'question')}${missing.length ? badge(`${missing.length} key fields incomplete`,'warning') : ''}</div><div class="source-links">${primary ? link(paper.url,'Open paper ↗') : '<span>Direct paper link not recorded</span>'}${routeLink('literature/' + encodeURIComponent(paper.paper_id),'Link to record')}</div><details${forceOpen ? ' open' : ''}><summary>Evidence, interpretation & extraction</summary><div class="evidence-grid"><section class="evidence-box"><h3>${badge('Paper evidence','paper')}</h3>${evidence}</section>${evidenceBox('Project interpretation','interpretation',paper.our_interpretation,'No interpretation recorded.')}${evidenceBox('Unresolved question','question',paper.open_questions,'No questions recorded. This does not establish completeness.')}</div>${metadata([['Success definition',paper.success_definition],['Validator / judge',paper.validator],['Evaluation types',D.strings(paper.evaluation_type).join(', ')],['Benchmark',paper.benchmark],['Human ground truth',paper.human_ground_truth],['Code execution',paper.executes_code === true ? 'Yes' : paper.executes_code === false ? 'No' : null],['Labels / score',paper.labels_or_score],['Subdomains',D.strings(paper.subdomains).join(', ')],['Reported metric names',D.strings(paper.metrics).join(', ')],['Missing key fields',missing.join(', ') || 'None in the dashboard key-field check']])}<h3>Author limitations</h3>${list(paper.authors_limitations)}${metadata([['False-positive evidence',primary ? paper.false_positive_evidence : null],['False-negative evidence',primary ? paper.false_negative_evidence : null]])}${original && typeof original === 'object' ? `<details><summary>Original literature-matrix fields</summary>${metadata(Object.entries(original).map(([key,value]) => [key,typeof value === 'string' ? value : JSON.stringify(value)]))}</details>` : ''}<p class="meta">Review status is supplied by the registry. It is not inferred from how many fields are filled.</p>${sourceLinks(paper)}</details></article>`;
  }
  function paperMatches(data, filters = {}, selected = '') {
    let papers = D.filterPapers(D.records(data,'papers'),filters);
    if (selected) papers = papers.filter(p => p.paper_id === selected);
    return papers;
  }
  function paperResults(data, filters, selected) {
    const papers = paperMatches(data,filters,selected);
    return papers.length ? papers.map(p => paperCard(p,Boolean(selected))).join('') : empty('No matching papers','Try another title, domain or review status. Missing search results do not establish a research gap.',null,null,false);
  }
  function literature(data, filters = {}, selected = '') {
    if (!D.available(data,'papers')) return problem(data,'papers');
    const papers = D.records(data,'papers');
    const domains = [...new Set(papers.map(p => p.domain).filter(D.filled))].sort();
    return `<div class="notice"><p>Paper findings, project interpretations and open questions are shown separately. Unreviewed entries are a reading queue; their metadata still needs confirmation.</p></div><form class="toolbar" id="paper-filters" role="search"><label>Search papers<input type="search" name="query" value="${escape(filters.query)}" placeholder="Title, ID, method or question" autocomplete="off"></label><label>Review status<select name="status"><option value="">All review stages</option>${D.REVIEW_STATES.map(state => `<option value="${state}"${filters.status === state ? ' selected' : ''}>${state}</option>`).join('')}</select></label><label>Domain<select name="domain"><option value="">All domains</option>${domains.map(domain => `<option value="${escape(domain)}"${filters.domain === domain ? ' selected' : ''}>${escape(domain)}</option>`).join('')}</select></label><button type="button" class="button secondary" id="clear-filters">Clear filters</button></form>${selected ? `<p class="meta">Showing linked record ${escape(selected)}. ${routeLink('literature','Show all papers')}</p>` : ''}<p class="record-count" id="paper-count" role="status" aria-live="polite">${paperMatches(data,filters,selected).length} of ${papers.length} records</p><div id="paper-results">${paperResults(data,filters,selected)}</div>`;
  }
  function registry(data, name) {
    if (!D.available(data,name)) return problem(data,name);
    const items = D.records(data,name);
    if (!items.length) return empty(`No ${name} registered`, 'Add source-linked records when the mapping is ready. No coverage or readiness is inferred from an empty registry.');
    return `<p class="record-count">${items.length} ${escape(name)} registered</p><div class="card-grid">${items.map(record => `<article class="panel">${sectionHead(D.text(record.name),record[D.COLLECTIONS[name]])}<div class="badges">${badge(record.status || 'status not recorded',record.status === 'implemented' ? '' : 'planned')}${badge('Project interpretation','interpretation')}</div><p>${escape(record.our_interpretation)}</p>${name === 'validators' ? metadata([['Role',record.role],['Evaluation type',record.evaluation_type],['Version',record.version],['Success definition',record.success_definition]]) + (record.implementation_url ? `<p>${link(record.implementation_url,'Implementation')}</p>` : '<p class="meta">Implementation not recorded</p>') : metadata([['Version',record.version],['Licence',record.licence],['Redistribution',record.redistribution === true ? 'Permitted per registry' : record.redistribution === false ? 'Not permitted per registry' : null],['Split',record.split]]) + (record.dataset_manifest ? `<p>${link(record.dataset_manifest,'Dataset manifest')}</p>` : '<p class="meta">Dataset manifest not recorded</p>')}${relatedPapers(data,record.paper_ids)}<h3>Open questions</h3>${list(record.open_questions)}${sourceLinks(record)}</article>`).join('')}</div>`;
  }
  function relatedPapers(data, ids) {
    if (!D.strings(ids).length) return '';
    return `<div class="source-links">${D.strings(ids).map(id => {
      const paper = D.records(data,'papers').find(p => p.paper_id === id);
      return paper ? routeLink('literature/' + encodeURIComponent(id),paper.title) : `<span>${escape(id)} · paper record unavailable</span>`;
    }).join('')}</div>`;
  }
  function domains(data) {
    if (!D.available(data,'domains')) return problem(data,'domains');
    const items = D.records(data,'domains');
    if (!items.length) return empty('No domains registered','Subdomain selection remains open.');
    function node(record, nested = false) {
      const children = items.filter(item => item.parent_id === record.domain_id);
      return `<${nested ? 'section' : 'article'} class="${nested ? 'domain-child' : 'panel'}">${nested ? `<h3>${escape(record.name)}</h3>` : sectionHead(D.text(record.name),record.domain_id)}<div class="badges">${badge(record.status || 'status not recorded','planned')}${badge('Project interpretation','interpretation')}</div><p>${escape(record.our_interpretation)}</p>${D.strings(record.open_questions).length ? `<h3>Open questions</h3>${list(record.open_questions)}` : ''}${sourceLinks(record)}${children.length ? `<div class="domain-children">${children.map(child => node(child,true)).join('')}</div>` : ''}</${nested ? 'section' : 'article'}>`;
    }
    return `<p class="record-count">${items.filter(d => !d.parent_id).length} domains · ${items.filter(d => d.parent_id).length} subdomains</p><div class="card-grid">${items.filter(d => !d.parent_id).map(d => node(d)).join('')}</div>`;
  }
  function experimentCard(record) {
    return `<article class="panel">${sectionHead(D.text(record.title),record.experiment_id)}<div class="badges">${badge(record.status || 'Status not recorded',record.status === 'planned' ? 'planned' : '')}${record.status === 'planned' ? badge('Planned experiment','planned') : ''}</div><p>${escape(record.description)}</p>${metadata([['Dataset version',record.dataset_version],['Development manifest',record.development_manifest],['Test manifest',record.test_manifest],['Validator IDs',D.strings(record.validator_ids).join(', ')],['Model',record.model],['Attack method',record.attack_method],['Config version',record.config_version],['Code commit',record.code_commit],['Success definition',record.success_definition]])}${record.config_url ? link(record.config_url,'Experiment config') : '<p class="meta">Config not recorded</p>'}${sourceLinks(record)}</article>`;
  }
  function experiments(data) {
    if (!D.available(data,'experiments')) return problem(data,'experiments');
    const items = D.records(data,'experiments');
    const summary = `<p class="record-count">${items.length} registered · ${items.filter(e => e.status === 'planned').length} planned · ${items.filter(e => e.status === 'completed').length} marked completed</p>`;
    return summary + (items.length ? `<div class="card-grid">${items.map(experimentCard).join('')}</div>` : `<div class="content-grid">${empty('No experiments registered yet','The synthesis proposes a pilot, but an experiment config and run manifest have not been registered. Study readiness is tracked separately from completed experiments.','results','View result readiness')}${readiness(data)}</div>`) + (D.available(data,'project') ? `<section class="panel">${sectionHead('Proposed pilot questions','Planning only')}${badge('Planned experiment','planned')}${list(data.project.records.open_questions)}${sourceLinks(data.project.records)}</section>` : problem(data,'project'));
  }
  function resultCard(record) {
    const p = record.provenance;
    const rows = Object.entries(D.METRICS).map(([key,title]) => {
      const value = record.metrics[key];
      return `<tr><th scope="row">${escape(title)}</th><td class="number">${typeof value === 'number' ? (value * 100).toFixed(2) + (key === 'asr_difference' ? ' pp' : '%') : 'Not measured'}</td></tr>`;
    }).join('');
    return `<article class="panel paper-card">${sectionHead(record.result_id,`${record.experiment_id} · ${p.run_id}`)}<div class="badges">${badge('Measured result','measured')}${badge(p.split === 'test' ? 'Held-out test split' : 'Development split','planned')}</div>${metadata([['Evaluator',record.validator_id],['Validator version',p.validator_version],['Model',p.model],['Attack method',p.attack_method],['Dataset version',p.dataset_version],['Measured cases',String(record.sample_size)],['Success definition',record.success_definition],['Comparison direction / reference',record.comparison]])}<div class="table-scroll"><table class="data-table"><caption>Values supplied by the recorded run artifacts; ratios displayed as percentages.</caption><thead><tr><th scope="col">Metric</th><th scope="col">Recorded value</th></tr></thead><tbody>${rows}</tbody></table></div><p class="metric-note">${escape(record.notes || 'Missing or undefined metrics remain unmeasured. Development and test records are not pooled.')}</p><details><summary>Run provenance & source artifacts</summary>${metadata([['Code commit',p.code_commit],['Config version',p.config_version],['Human-label version',p.human_labels_version],['Run timestamp',p.timestamp]])}<div class="source-links">${Object.entries(p.artifacts).map(([name,url]) => link(url,name)).join('')}</div></details></article>`;
  }
  function results(data) {
    if (!D.available(data,'results')) return problem(data,'results');
    const report = D.resultReport(data);
    let html = ['experiments','validators'].map(name => problem(data,name)).join('');
    if (report.withheld.length) html += `<section class="notice error"><h2>${report.withheld.length} result records withheld</h2><p>These records cannot be presented as measured results until their provenance and metric fields pass validation.</p>${report.withheld.map(item => `<details><summary>${escape(item.record.result_id)}</summary>${list(item.problems)}</details>`).join('')}</section>`;
    if (report.accepted.length) html += `<p class="record-count">${report.accepted.length} measured result records · each run and split shown separately</p>${report.accepted.map(resultCard).join('')}`;
    else html += empty(report.withheld.length ? 'No displayable measured results' : 'No measured results recorded',report.withheld.length ? 'Fix the withheld records before interpreting performance. Unavailable evidence is not a measured zero.' : 'There are no measured result records in this export. Accuracy, F1, ASR and evaluator rankings will appear only when source-linked run measurements are available.','experiments','Check experiment readiness',!report.withheld.length);
    if (D.available(data,'project')) html += `<section class="panel panel-stack">${sectionHead('Planned outcomes','Measurement plan')}${badge('Planned experiment','planned')}${list(data.project.records.planned_outcomes)}${sourceLinks(data.project.records)}</section>`;
    return html;
  }
  function gaps(data) {
    if (!D.available(data,'gaps')) return problem(data,'gaps');
    const items = D.records(data,'gaps');
    return `<div class="notice"><h2>Novelty is not established</h2><p>${escape(D.available(data,'project') ? data.project.records.novelty_note : 'Missing or incomplete papers do not establish a research gap.')}</p></div>${!items.length ? empty('No gap or threat records','An empty registry is not evidence of novelty.') : `<div class="card-grid">${items.map(item => `<article class="panel">${sectionHead(D.text(item.title),item.gap_id)}<div class="badges">${badge(item.kind || 'unclassified','question')}${badge(item.status || 'unresolved','question')}</div><h3>${badge('Project interpretation','interpretation')}</h3><p>${escape(item.our_interpretation)}</p><h3>${badge('Unresolved question','question')}</h3>${list(item.open_questions)}${relatedPapers(data,item.paper_ids)}${sourceLinks(item)}</article>`).join('')}</div>`}`;
  }
  function render(route, data, filters = {}, selected = '') {
    if (!Object.hasOwn(ROUTES,route)) return empty('View not found','Choose a workspace view from the navigation.','overview','Return to overview',false);
    switch (route) {
      case 'overview': return overview(data);
      case 'literature': return literature(data,filters,selected);
      case 'validators': case 'benchmarks': return registry(data,route);
      case 'domains': return domains(data);
      case 'experiments': return experiments(data);
      case 'results': return results(data);
      case 'gaps': return gaps(data);
    }
  }
  const api = {ROUTES, escape, render, paperResults, paperMatches, resultCard};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ResearchViews = api;
})(typeof window === 'undefined' ? globalThis : window);
