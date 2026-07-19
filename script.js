const menuButton = document.querySelector('.menu-button');
const nav = document.querySelector('.main-nav');
const mobileMenuQuery = window.matchMedia('(max-width: 820px)');

// Mantiene Formación visible en páginas antiguas sin depender de una regeneración masiva.
if (nav && !nav.querySelector('a[href*="formacion"]')) {
  const trainingLink = document.createElement('a');
  trainingLink.href = '/formacion/';
  trainingLink.textContent = 'Formación';
  const contactLink = nav.querySelector('.nav-cta');
  nav.insertBefore(trainingLink, contactLink);
}

const setMenuState = (open, returnFocus = false) => {
  if (!menuButton || !nav) return;
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
  nav.classList.toggle('open', open);
  nav.toggleAttribute('inert', !open && mobileMenuQuery.matches);
  document.body.classList.toggle('menu-open', open);
  if (open) nav.querySelector('a')?.focus();
  if (!open && returnFocus) menuButton.focus();
};

menuButton?.addEventListener('click', () => {
  setMenuState(menuButton.getAttribute('aria-expanded') !== 'true');
});

document.addEventListener('keydown', (event) => {
  if (menuButton?.getAttribute('aria-expanded') !== 'true' || !nav) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    setMenuState(false, true);
    return;
  }
  if (event.key !== 'Tab') return;
  const focusable = [menuButton, ...nav.querySelectorAll('a')];
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
});

mobileMenuQuery.addEventListener('change', (event) => {
  if (!event.matches) setMenuState(false);
  else if (menuButton?.getAttribute('aria-expanded') !== 'true' && nav) nav.setAttribute('inert', '');
});

if (nav && mobileMenuQuery.matches) nav.setAttribute('inert', '');

nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  setMenuState(false);
}));

const revealElements = document.querySelectorAll('.reveal');
if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  revealElements.forEach((element) => element.classList.add('visible'));
} else {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealElements.forEach((element) => observer.observe(element));
}
const yearTarget = document.querySelector('[data-current-year]');
if (yearTarget) yearTarget.textContent = new Date().getFullYear();

const categoryFilter = document.querySelector('[data-filter-category]');
const designFilter = document.querySelector('[data-filter-design]');
const yearFilter = document.querySelector('[data-filter-year]');
const searchFilter = document.querySelector('[data-filter-search]');
const sortControl = document.querySelector('[data-sort]');
const evidenceCards = [...document.querySelectorAll('.evidence-card')];
const evidenceGrid = document.querySelector('[data-evidence-grid]');
const resultsCount = document.querySelector('[data-results-count]');
const emptyState = document.querySelector('[data-empty-state]');
const activeFilters = document.querySelector('[data-active-filters]');
const filterEvidence = () => {
  const category = categoryFilter?.value || 'all';
  const design = designFilter?.value || 'all';
  const year = yearFilter?.value || 'all';
  const query = (searchFilter?.value || '').trim().toLowerCase();
  let visible = 0;
  evidenceCards.forEach((card) => {
    const matchesCategory = category === 'all' || card.dataset.category === category;
    const matchesDesign = design === 'all' || card.dataset.design === design;
    const matchesYear = year === 'all' || card.dataset.year === year;
    const matchesQuery = !query || (card.dataset.search || card.textContent).includes(query);
    card.hidden = !(matchesCategory && matchesDesign && matchesYear && matchesQuery);
    if (!card.hidden) visible += 1;
  });
  if (resultsCount) resultsCount.textContent = visible;
  if (emptyState) emptyState.hidden = visible !== 0;
  const labels = [];
  if (category !== 'all') labels.push(categoryFilter.options[categoryFilter.selectedIndex].textContent.replace(/ \(\d+\)$/, ''));
  if (design !== 'all') labels.push(designFilter.options[designFilter.selectedIndex].textContent.replace(/ \(\d+\)$/, ''));
  if (year !== 'all') labels.push(year);
  if (query) labels.push(`“${query}”`);
  if (activeFilters) activeFilters.textContent = labels.length ? `Filtros activos: ${labels.join(' · ')}` : '';
  const params = new URLSearchParams();
  if (category !== 'all') params.set('categoria', category);
  if (design !== 'all') params.set('diseno', design);
  if (year !== 'all') params.set('ano', year);
  if (query) params.set('buscar', query);
  history.replaceState(null, '', `${location.pathname}${params.size ? `#${params}` : ''}`);
};
categoryFilter?.addEventListener('change', filterEvidence);
designFilter?.addEventListener('change', filterEvidence);
yearFilter?.addEventListener('change', filterEvidence);
searchFilter?.addEventListener('input', filterEvidence);
sortControl?.addEventListener('change', () => {
  const mode = sortControl.value;
  const sorted = [...evidenceCards].sort((a, b) => {
    if (mode === 'score') return Number(b.dataset.score) - Number(a.dataset.score) || Number(b.dataset.year) - Number(a.dataset.year);
    if (mode === 'title') return a.querySelector('h2').textContent.localeCompare(b.querySelector('h2').textContent, 'es');
    return Number(b.dataset.year) - Number(a.dataset.year) || a.querySelector('h2').textContent.localeCompare(b.querySelector('h2').textContent, 'es');
  });
  sorted.forEach((card) => evidenceGrid?.append(card));
});
document.querySelector('[data-clear-filters]')?.addEventListener('click', () => {
  if (categoryFilter) categoryFilter.value = 'all';
  if (designFilter) designFilter.value = 'all';
  if (yearFilter) yearFilter.value = 'all';
  if (searchFilter) searchFilter.value = '';
  filterEvidence();
});
if (evidenceCards.length) {
  const params = new URLSearchParams(location.hash.slice(1));
  if (categoryFilter && [...categoryFilter.options].some((o) => o.value === params.get('categoria'))) categoryFilter.value = params.get('categoria');
  if (designFilter && [...designFilter.options].some((o) => o.value === params.get('diseno'))) designFilter.value = params.get('diseno');
  if (yearFilter && [...yearFilter.options].some((o) => o.value === params.get('ano'))) yearFilter.value = params.get('ano');
  if (searchFilter) searchFilter.value = params.get('buscar') || '';
  filterEvidence();
}

const clinicalScript = document.querySelector('script[src*="clinical-tests.js"]');
const needsClinicalScript = document.querySelector('.clinical-test-list') && !clinicalScript;
const needsClinicalIndexRefresh = document.querySelector('.clinical-grid') && !clinicalScript?.src.includes('v=2');
if (needsClinicalScript || needsClinicalIndexRefresh) {
  const clinicalTestsScript = document.createElement('script');
  clinicalTestsScript.src = '/pruebas-clinicas/clinical-tests.js?v=2';
  clinicalTestsScript.defer = true;
  document.head.appendChild(clinicalTestsScript);
}
