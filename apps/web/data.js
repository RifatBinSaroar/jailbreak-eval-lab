/* Reader for Python's canonical export. No scientific records are defined here. */
(function(root) {
  'use strict';
  const COLLECTIONS = Object.freeze(Object.fromEntries(['papers','validators','benchmarks','domains','datasets','experiments','runs','human_labels','results'].map(n=>[n,'id'])));
  const REVIEW_STATES = ['listed','screened','deep-reviewed','verified'];
  const text = value => typeof value === 'string' ? value : '';
  const strings = value => Array.isArray(value) ? value.filter(v=>typeof v === 'string') : [];
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

  function parseBundle(value) {
    if (!object(value) || value.contract !== 'research-platform/0.1' || value.schema_version !== '1.0.0') throw new Error('Unsupported canonical export. Rebuild with Python.');
    if (!object(value.readiness) || !/^[a-f0-9]{64}$/.test(value.registry_sha256)) throw new Error('Missing canonical integrity/readiness metadata.');
    for (const name of Object.keys(COLLECTIONS)) {
      if (!Array.isArray(value[name])) throw new Error(`Missing canonical ${name} collection.`);
      const ids = new Set();
      for (const record of value[name]) {
        if (!object(record) || !/^[a-z_]+:[a-z0-9][a-z0-9._-]*$/.test(record.id) || !filled(record.version)) throw new Error('Missing canonical ID/version.');
        if (ids.has(record.id)) throw new Error(`Duplicate ID: ${record.id}`);
        ids.add(record.id);
        if (!['research','synthetic'].includes(record.record_kind) || (record.record_kind==='synthetic' && value.include_synthetic!==true)) throw new Error('Template/synthetic records in production export.');
      }
    }
    for (const name of ['paper_evidence','metrics','open_questions','novelty_threats','duplicate_candidates']) if (!Array.isArray(value[name])) throw new Error(`Missing ${name}.`);
    for (const paper of value.papers) {
      if (!filled(paper.title) || !REVIEW_STATES.includes(paper.evidence_status)) throw new Error('Invalid canonical paper review state.');
      for (const name of ['sources','paper_demonstrates','our_interpretation','open_questions']) if (!Array.isArray(paper[name])) throw new Error('Malformed paper extraction.');
      for (const claim of paper.paper_demonstrates) if (!paper.sources.some(s=>s.id===claim.source_id && safeURL(s.url))) throw new Error('Unlinked paper evidence.');
    }
    const domains = new Map(value.domains.map(d=>[d.id,d]));
    for (const domain of value.domains) {
      const visited = new Set([domain.id]); let parent = domain.parent_id;
      while (parent) {
        if (!domains.has(parent) || visited.has(parent)) throw new Error('Invalid domain hierarchy.');
        visited.add(parent); parent=domains.get(parent).parent_id;
      }
    }
    for (const result of value.results) {
      if (result.kind!=='aggregate' || !Array.isArray(result.metrics) || !object(result.provenance) || !Array.isArray(result.provenance.artifacts)) throw new Error('Expected traceable canonical aggregates.');
      if (!value.runs.some(r=>r.id===result.run_id && r.status==='completed') || !value.validators.some(v=>v.id===result.validator.id)) throw new Error('Unlinked measured result.');
      if (!/^[a-f0-9]{40}$|^[a-f0-9]{64}$/.test(result.provenance.code_commit) || !result.provenance.artifacts.length || result.provenance.artifacts.some(a=>!/^[a-f0-9]{64}$/.test(a.sha256))) throw new Error('Incomplete result provenance.');
      for (const metric of result.metrics) {
        if (metric.status==='computed' ? typeof metric.value!=='number' || !Number.isFinite(metric.value) || !(metric.denominator>0) : metric.value!==null) throw new Error('Invalid or undefined metric value.');
      }
    }
    return value;
  }
  async function loadAll(fetcher) {
    try {
      const response=await fetcher('data/research.json',{cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return parseBundle(await response.json());
    } catch(error) { return {error:error.message}; }
  }
  const records=(data,name)=>Array.isArray(data[name]) ? data[name] : [];
  const available=(data,name)=>!data.error && Array.isArray(data[name]);
  const filterPapers=(papers,filters={})=>papers.filter(p=>(!filters.status || p.evidence_status===filters.status) && (!filters.domain || p.domain_ids.includes(filters.domain)) && (!filters.query || JSON.stringify(p).toLowerCase().includes(filters.query.toLowerCase())));
  const sources=record=>Array.isArray(record.sources) ? record.sources.filter(s=>safeURL(s.url)) : [];
  const api={COLLECTIONS,REVIEW_STATES,text,strings,filled,object,safeURL,parseBundle,loadAll,records,available,filterPapers,sources};
  if (typeof module!=='undefined' && module.exports) module.exports=api; else root.ResearchData=api;
})(typeof window==='undefined' ? globalThis : window);
