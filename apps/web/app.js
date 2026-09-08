const papers = [
  { title: 'PAIR', meta: 'General LLM judge · human comparison', tag: 'Judge baseline' },
  { title: 'GUIDEDBENCH / GUIDEDEVAL', meta: 'Case-specific evaluation guidelines', tag: 'Case-specific' },
  { title: 'RMCBench', meta: 'Malicious-code evaluation · GOOD / BAD / UNCLEAR', tag: 'Domain-specific' },
  { title: 'Smoke and Mirrors / CodeJailbreaker', meta: 'SERIOUS / SLIGHT · Malicious Ratio', tag: 'Function-aware' },
  { title: 'RedCode', meta: 'Risky code execution and generation · sandbox checks', tag: 'Functional' },
  { title: 'WildGuard', meta: 'Specialised safety evaluator', tag: 'Safety model' }
];

const list = document.getElementById('paperList');
const toggle = document.getElementById('togglePapers');
let expanded = false;

function renderPapers() {
  list.innerHTML = '';
  papers.forEach((paper, index) => {
    const item = document.createElement('div');
    item.className = `paper-item ${!expanded && index >= 4 ? 'hidden-paper' : ''}`;
    item.innerHTML = `
      <div>
        <strong>${paper.title}</strong>
        <small>${paper.meta}</small>
      </div>
      <span class="paper-tag">${paper.tag}</span>
    `;
    list.appendChild(item);
  });
  toggle.textContent = expanded ? 'Show less' : 'Show all';
}

toggle.addEventListener('click', () => {
  expanded = !expanded;
  renderPapers();
});

renderPapers();

for (const link of document.querySelectorAll('.nav-item')) {
  link.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    link.classList.add('active');
  });
}
