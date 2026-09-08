/* No build step, package manager, remote script or backend is needed. */
(function () {
  'use strict';
  const D = window.ResearchData, V = window.ResearchViews;
  const content = document.getElementById('content');
  const status = document.getElementById('load-status');
  const refresh = document.getElementById('reload');
  const menu = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('navigation');
  const filters = {query: '', status: '', domain: ''};
  let data = null;
  let loading = false;
  function locationState() {
    const parts = location.hash.replace(/^#/, '').split('/');
    // Preserve useful old bookmarks from the static shell.
    const aliases = {home: 'overview', papers: 'literature', run: 'experiments', datasets: 'benchmarks', visuals: 'results', reports: 'results', docs: 'overview'};
    let selected = '';
    try { selected = decodeURIComponent(parts.slice(1).join('/')); } catch { /* Invalid record ID is handled as no match. */ selected = 'Invalid record ID'; }
    return {route: Object.hasOwn(aliases, parts[0]) ? aliases[parts[0]] : parts[0] || 'overview', selected};
  }
  function closeMenu(returnFocus = false) {
    navigation.classList.remove('open'); menu.setAttribute('aria-expanded','false');
    if (returnFocus) menu.focus();
  }
  function render(focus = false) {
    const {route, selected} = locationState();
    const info = Object.hasOwn(V.ROUTES, route) ? V.ROUTES[route] : ['View not found','Choose a workspace view from the navigation.'];
    document.getElementById('page-title').textContent = info[0];
    document.getElementById('page-description').textContent = info[1];
    document.title = `${info[0]} · JailbreakEval`;
    document.querySelectorAll('.nav-group .nav-item').forEach(item => {
      if (item.hash === `#${route}`) item.setAttribute('aria-current','page');
      else item.removeAttribute('aria-current');
    });
    if (data) content.innerHTML = V.render(route,data,filters,selected);
    bindFilters(selected);
    if (focus) document.getElementById('workspace').focus({preventScroll: false});
  }
  function bindFilters(selected) {
    const form = document.getElementById('paper-filters');
    if (!form) return;
    function update() {
      for (const key of Object.keys(filters)) filters[key] = form.elements.namedItem(key).value;
      document.getElementById('paper-count').textContent = `${V.paperMatches(data,filters,selected).length} of ${D.records(data,'papers').length} records`;
      document.getElementById('paper-results').innerHTML = V.paperResults(data,filters,selected);
    }
    form.addEventListener('submit',event => {event.preventDefault(); update();});
    form.addEventListener('input',update);
    form.addEventListener('change',update);
    document.getElementById('clear-filters').addEventListener('click',() => {
      for (const key of Object.keys(filters)) {filters[key] = ''; form.elements.namedItem(key).value = '';}
      if (selected) location.hash = 'literature'; else update();
      form.elements.namedItem('query').focus();
    });
  }
  async function load() {
    if (loading) return;
    loading = true; refresh.disabled = true; content.setAttribute('aria-busy','true');
    status.textContent = 'Loading JSON records…';
    try {
      data = await D.loadAll(window.fetch.bind(window));
      const failures = Object.values(data).filter(item => item.status === 'error').length;
      status.textContent = failures ? `${failures} data files unavailable. Affected views show the errors.` : `${Object.keys(data).length} data files loaded · Counts reflect this export`;
      render();
    } finally {
      loading = false; refresh.disabled = false; content.setAttribute('aria-busy','false');
    }
  }
  menu.addEventListener('click',() => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded',String(open)); navigation.classList.toggle('open',open);
  });
  document.addEventListener('keydown',event => {if (event.key === 'Escape' && navigation.classList.contains('open')) closeMenu(true);});
  document.querySelector('.skip-link').addEventListener('click',event => {
    event.preventDefault(); document.getElementById('workspace').focus();
  });
  navigation.addEventListener('click',event => {
    const anchor = event.target.closest('a');
    if (!anchor) return;
    closeMenu();
    if (anchor.hash && anchor.hash === location.hash) {event.preventDefault(); render(true);}
  });
  window.addEventListener('hashchange',() => {
    // Record links must not be hidden by stale search filters.
    if (locationState().selected) for (const key of Object.keys(filters)) filters[key] = '';
    closeMenu(); render(true);
  });
  refresh.addEventListener('click',load);
  render();
  load();
})();
