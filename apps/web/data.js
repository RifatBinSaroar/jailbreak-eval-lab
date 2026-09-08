/* Shared, build-free data contract. Also loadable by Node's built-in test runner. */
(function (root) {
  'use strict';
  const COLLECTIONS = Object.freeze({
    papers: 'paper_id', validators: 'validator_id', benchmarks: 'benchmark_id',
    domains: 'domain_id', experiments: 'experiment_id', results: 'result_id', gaps: 'gap_id'
  });
  const REVIEW_STATES = ['unreviewed', 'screened', 'deep-reviewed', 'verified'];
  const METRICS = Object.freeze({accuracy: 'Accuracy', precision: 'Precision', recall: 'Recall',
    f1: 'F1', false_positive_rate: 'False-positive rate', false_negative_rate: 'False-negative rate',
    asr: 'ASR', asr_difference: 'ASR difference', disagreement: 'Evaluator disagreement'});
  const text = value => typeof value === 'string' ? value : '';
  const strings = value => Array.isArray(value) ? value.filter(item => typeof item === 'string') : [];
  const filled = value => typeof value === 'string' && value.trim().length > 0;
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function safeURL(value) {
    if (!filled(value) || /[\u0000-\u0020\u007f\\]/.test(value)) return null;
    if (/^https?:\/\//i.test(value)) {
      try { const url = new URL(value); return url.username || url.password ? null : url.href; } catch { return null; }
    }
    if (value.startsWith('//') || /[:]/.test(value) || value.startsWith('/')) return null;
    // Repository-relative files are served by Live Server. Never allow executable schemes.
    return /^(?:\.\.\/){0,2}[a-zA-Z0-9_][a-zA-Z0-9_./#?=&%+-]*$/.test(value) ? value : null;
  }
  function sources(record) {
    const list = Array.isArray(record.source_links) ? record.source_links : [];
    return list.filter(item => object(item) && safeURL(item.url));
  }
  function hasPaperSource(record) { return /^https?:\/\//i.test(text(record.url)) && Boolean(safeURL(record.url)); }
  function parseCollection(name, payload) {
    if (!Object.hasOwn(COLLECTIONS, name)) throw new Error('Unknown registry.');
    if (object(payload) && payload.schema_version !== undefined && payload.schema_version !== 1) {
      throw new Error('Unsupported schema_version; expected 1.');
    }
    // Importers can emit bare arrays or named envelopes as well as {records: []}.
    const records = Array.isArray(payload) ? payload : payload?.records ?? payload?.[name];
    if (!Array.isArray(records)) throw new Error('Expected an array of records.');
    const ids = new Set();
    for (const record of records) {
      if (!object(record) || !filled(record[COLLECTIONS[name]])) throw new Error(`Each record needs ${COLLECTIONS[name]}.`);
      const id = record[COLLECTIONS[name]];
      if (ids.has(id)) throw new Error(`Duplicate ID: ${id}.`);
      ids.add(id);
      if (name === 'papers') {
        if (!filled(record.title)) throw new Error(`${id}: title is required.`);
        if (!REVIEW_STATES.includes(record.evidence_status)) throw new Error(`${id}: invalid evidence_status.`);
        for (const field of ['paper_demonstrates', 'our_interpretation', 'open_questions']) {
          if (record[field] !== undefined && (!Array.isArray(record[field]) || record[field].some(x => !filled(x)))) {
            throw new Error(`${id}: ${field} must be an array of non-empty strings.`);
          }
        }
        if (record.evidence_status !== 'unreviewed' && !hasPaperSource(record)) {
          throw new Error(`${id}: reviewed paper records require a direct http(s) paper URL.`);
        }
      }
      if (name === 'domains' && record.parent_id === id) throw new Error(`${id}: a domain cannot be its own parent.`);
    }
    if (name === 'domains') {
      const byId = new Map(records.map(r => [r.domain_id, r]));
      for (const record of records) {
        const visited = new Set([record.domain_id]);
        let parent = record.parent_id;
        while (parent) {
          if (!byId.has(parent)) throw new Error(`${record.domain_id}: unknown parent ${parent}.`);
          if (visited.has(parent)) throw new Error(`${record.domain_id}: cyclic domain hierarchy.`);
          visited.add(parent); parent = byId.get(parent).parent_id;
        }
      }
    }
    return records;
  }
  function parseProject(payload) {
    if (!object(payload) || payload.schema_version !== 1 || !object(payload.project)) throw new Error('Expected schema_version 1 and a project object.');
    const p = payload.project;
    if (!filled(p.project_id) || !filled(p.hypothesis) || !Array.isArray(p.readiness)) throw new Error('Project ID, hypothesis and readiness are required.');
    const ids = new Set();
    for (const item of p.readiness) {
      if (!object(item) || !filled(item.id) || ids.has(item.id) || !filled(item.title) || !['pending','in-progress','complete','blocked'].includes(item.status)) {
        throw new Error('Readiness items need unique IDs, titles and a known status.');
      }
      ids.add(item.id);
    }
    return p;
  }
  async function loadOne(name, fetcher) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetcher(`data/${name}.json`, {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      return {status: 'ready', records: name === 'project' ? parseProject(payload) : parseCollection(name, payload)};
    } catch (error) {
      return {status: 'error', error: error.name === 'AbortError' ? 'Request timed out.' : error.message};
    } finally { clearTimeout(timeout); }
  }
  async function loadAll(fetcher) {
    const names = ['project', ...Object.keys(COLLECTIONS)];
    return Object.fromEntries(await Promise.all(names.map(async name => [name, await loadOne(name, fetcher)])));
  }
  const available = (data, name) => data[name]?.status === 'ready';
  const records = (data, name) => available(data, name) ? data[name].records : [];
  function filterPapers(papers, filters = {}) {
    const query = text(filters.query).trim().toLocaleLowerCase();
    return papers.filter(p => (!filters.status || p.evidence_status === filters.status) &&
      (!filters.domain || p.domain === filters.domain) &&
      (!query || [p.paper_id, p.title, p.venue_or_arxiv, p.domain, p.validator,
        ...strings(p.subdomains), ...strings(p.our_interpretation), ...strings(p.open_questions)]
        .filter(filled).join(' ').toLocaleLowerCase().includes(query)));
  }
  function inspectResult(result, data) {
    const problems = [];
    if (result.kind !== 'measured' || result.is_example === true || result.is_synthetic === true) problems.push('Only real measured records can enter the results view.');
    for (const name of ['experiments', 'validators']) if (!available(data, name)) problems.push(`${name} registry is unavailable.`);
    const experiment = records(data, 'experiments').find(e => e.experiment_id === result.experiment_id);
    if (!experiment) problems.push('Linked experiment is missing.');
    if (!records(data, 'validators').some(v => v.validator_id === result.validator_id)) problems.push('Linked validator is missing.');
    const p = result.provenance;
    if (!object(p)) return [...problems, 'Run provenance is missing.'];
    for (const key of ['run_id','dataset_version','validator_version','model','attack_method','config_version','human_labels_version','timestamp']) {
      if (!filled(p[key])) problems.push(`Missing provenance: ${key}.`);
    }
    if (!['development', 'test'].includes(p.split)) problems.push('Split must be development or test.');
    if (!/^[0-9a-f]{40}$/i.test(text(p.code_commit))) problems.push('A full code commit SHA is required.');
    if (!filled(p.timestamp) || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(p.timestamp) || Number.isNaN(Date.parse(p.timestamp))) problems.push('A timestamp with timezone is required.');
    for (const key of ['manifest', 'predictions', 'metrics', 'human_labels']) {
      if (!safeURL(p.artifacts?.[key])) problems.push(`Missing or unsafe artifact link: ${key}.`);
    }
    if (!object(result.metrics) || !Object.keys(METRICS).some(key => typeof result.metrics[key] === 'number')) {
      problems.push('No supported measured metrics are provided.');
    } else {
      for (const [key, value] of Object.entries(result.metrics)) {
        if (!Object.hasOwn(METRICS, key)) { problems.push(`Unsupported metric: ${key}.`); continue; }
        if (value !== null && (typeof value !== 'number' || !Number.isFinite(value) || value < (key === 'asr_difference' ? -1 : 0) || value > 1)) problems.push(`Invalid metric: ${key}.`);
      }
    }
    if (!Number.isInteger(result.sample_size) || result.sample_size < 1) problems.push('A positive measured sample size is required.');
    if (!filled(result.success_definition)) problems.push('The measured success definition is required.');
    if (typeof result.metrics?.asr_difference === 'number' && !filled(result.comparison)) problems.push('ASR differences require the comparison direction and reference.');
    return problems;
  }
  function resultReport(data) {
    const accepted = [], withheld = [];
    for (const result of records(data, 'results')) {
      const problems = inspectResult(result, data);
      if (problems.length) withheld.push({record: result, problems}); else accepted.push(result);
    }
    return {accepted, withheld};
  }
  const api = {COLLECTIONS, REVIEW_STATES, METRICS, text, strings, filled, safeURL, sources, hasPaperSource,
    parseCollection, parseProject, loadAll, available, records, filterPapers, inspectResult, resultReport};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ResearchData = api;
})(typeof window === 'undefined' ? globalThis : window);
