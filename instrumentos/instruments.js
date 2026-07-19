const search = document.querySelector('[data-instrument-search]');
const construct = document.querySelector('[data-instrument-construct]');
const region = document.querySelector('[data-instrument-region]');
const purpose = document.querySelector('[data-instrument-purpose]');
const validation = document.querySelector('[data-instrument-validation]');
const permission = document.querySelector('[data-instrument-permission]');
const resetButton = document.querySelector('[data-filter-reset]');
const viewToggle = document.querySelector('[data-view-toggle]');
const grid = document.querySelector('.measure-grid');
const cards = [...document.querySelectorAll('[data-instrument-card]')];
const count = document.querySelector('[data-instrument-count]');
const summary = document.querySelector('[data-instrument-summary]');
const empty = document.querySelector('[data-instrument-empty]');
const compareButton = document.querySelector('[data-compare-open]');
const compareCount = document.querySelector('[data-compare-count]');
const comparePanel = document.querySelector('[data-compare-panel]');
const compareTable = document.querySelector('[data-compare-table]');
const compareClear = document.querySelector('[data-compare-clear]');
const compareChoices = [...document.querySelectorAll('[data-compare-choice]')];

const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const controls = { query: search, construct, region, purpose, validation, permission };

const restoreFiltersFromUrl = () => {
  const params = new URLSearchParams(window.location.search);
  Object.entries(controls).forEach(([name, control]) => {
    if (!control || !params.has(name)) return;
    const value = params.get(name);
    if (control === search || [...control.options].some((option) => option.value === value)) control.value = value;
  });
};

const updateFilterUrl = () => {
  const params = new URLSearchParams();
  Object.entries(controls).forEach(([name, control]) => {
    const value = control?.value.trim();
    if (value && value !== 'all') params.set(name, value);
  });
  const next = `${window.location.pathname}${params.size ? `?${params}` : ''}${window.location.hash}`;
  window.history.replaceState(null, '', next);
};
const selectedCards = () => compareChoices
  .filter((choice) => choice.checked)
  .map((choice) => choice.closest('[data-instrument-card]'));

const updateCompareControls = () => {
  const selected = selectedCards();
  if (compareCount) compareCount.textContent = selected.length;
  if (compareButton) compareButton.disabled = selected.length < 2;
  compareChoices.forEach((choice) => {
    choice.disabled = selected.length >= 3 && !choice.checked;
  });
  if (selected.length < 2 && comparePanel) comparePanel.hidden = true;
};

const filterInstruments = () => {
  const query = normalize(search?.value.trim() || '');
  const filters = {
    construct: construct?.value || 'all',
    region: region?.value || 'all',
    purpose: purpose?.value || 'all',
    validation: validation?.value || 'all',
    permission: permission?.value || 'all',
  };
  let visible = 0;
  cards.forEach((card) => {
    const text = normalize(card.dataset.search || card.textContent);
    const matches = (!query || text.includes(query)) && Object.entries(filters)
      .every(([field, value]) => value === 'all' || (field === 'purpose'
        ? (card.dataset.purpose || '').split(' ').includes(value)
        : card.dataset[field] === value));
    card.hidden = !matches;
    if (!matches) {
      const choice = card.querySelector('[data-compare-choice]');
      if (choice) choice.checked = false;
    }
    if (matches) visible += 1;
  });
  if (count) count.textContent = visible;
  if (summary) summary.textContent = visible === cards.length ? 'Colección revisada' : 'Resultados según tus filtros';
  if (empty) empty.hidden = visible !== 0;
  updateCompareControls();
  updateFilterUrl();
};

const comparisonRows = [
  ['Tipo', 'compareType'],
  ['Constructo', 'compareConstruct'],
  ['Tiempo', 'compareTime'],
  ['Rango', 'compareRange'],
  ['Dirección', 'compareDirection'],
  ['Versión española', 'compareValidation'],
  ['Población estudiada', 'comparePopulation'],
  ['Respaldo', 'compareEvidence'],
  ['Permiso', 'comparePermission'],
  ['Útil para', 'compareUseful'],
  ['No sirve para', 'compareNotFor'],
];

const renderComparison = () => {
  const selected = selectedCards();
  if (selected.length < 2 || !compareTable || !comparePanel) return;
  const head = `<thead><tr><th scope="col">Criterio</th>${selected.map((card) => `<th scope="col">${card.dataset.acronym}</th>`).join('')}</tr></thead>`;
  const body = comparisonRows.map(([label, field]) => `<tr><th scope="row">${label}</th>${selected.map((card) => `<td>${card.dataset[field]}</td>`).join('')}</tr>`).join('');
  compareTable.innerHTML = `<caption>Comparación de instrumentos seleccionados</caption>${head}<tbody>${body}</tbody>`;
  comparePanel.hidden = false;
  comparePanel.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  comparePanel.focus({ preventScroll: true });
};

[search, construct, region, purpose, validation, permission].forEach((control) => {
  control?.addEventListener(control === search ? 'input' : 'change', filterInstruments);
});
resetButton?.addEventListener('click', () => {
  Object.values(controls).forEach((control) => { if (control) control.value = control === search ? '' : 'all'; });
  filterInstruments();
  search?.focus();
});
const setCompact = (compact) => {
  grid?.classList.toggle('is-compact', compact);
  grid?.querySelectorAll('.measure-more').forEach((details) => { details.hidden = compact; });
  if (viewToggle) {
    viewToggle.setAttribute('aria-pressed', String(compact));
    viewToggle.textContent = compact ? 'Vista detallada' : 'Vista compacta';
  }
};
let viewWasManuallySet = false;
viewToggle?.addEventListener('click', () => {
  viewWasManuallySet = true;
  setCompact(!grid?.classList.contains('is-compact'));
});
const mobileView = window.matchMedia('(max-width: 620px)');
mobileView.addEventListener('change', (event) => {
  if (!viewWasManuallySet) setCompact(event.matches);
});
compareChoices.forEach((choice) => choice.addEventListener('change', updateCompareControls));
compareButton?.addEventListener('click', renderComparison);
compareClear?.addEventListener('click', () => {
  compareChoices.forEach((choice) => { choice.checked = false; });
  if (comparePanel) comparePanel.hidden = true;
  updateCompareControls();
});
restoreFiltersFromUrl();
setCompact(mobileView.matches);
filterInstruments();

const batteryForm = document.querySelector('[data-battery-builder]');
const batteryResult = document.querySelector('[data-battery-result]');
const batteryLinks = {
  PSFS: 'patient-specific-functional-scale/', ODI: 'oswestry-disability-index/', NDI: 'neck-disability-index/',
  QuickDASH: 'quickdash/', LEFS: 'lower-extremity-functional-scale/', END: 'escala-numerica-dolor/',
  PGIC: 'impresion-global-cambio-paciente/', 'EQ-5D-5L': 'eq-5d-5l/', 'WHODAS 2.0': 'whodas-2-participacion/',
  'PROMIS-SD 8a': 'promis-alteracion-sueno-8a/', 'PSEQ-10': 'pain-self-efficacy-questionnaire/',
  '30s-CST': 'rendimiento/chair-stand-30-segundos/', TUG: 'rendimiento/timed-up-and-go/',
  '10MWT': 'rendimiento/test-marcha-10-metros/', '6MWT': 'rendimiento/test-marcha-seis-minutos/',
};
const batteryMinutes = { PSFS: 4, ODI: 5, NDI: 4, QuickDASH: 5, LEFS: 5, END: 1, PGIC: 1, 'EQ-5D-5L': 3, 'WHODAS 2.0': 20, 'PROMIS-SD 8a': 3, 'PSEQ-10': 5, '30s-CST': 3, TUG: 3, '10MWT': 5, '6MWT': 18 };
const primaryByGoal = { funcion_personal: 'PSFS', dolor: 'END', participacion: 'WHODAS 2.0', sueno: 'PROMIS-SD 8a', calidad_vida: 'EQ-5D-5L', autoeficacia: 'PSEQ-10' };
const regional = { lumbar: 'ODI', cervical: 'NDI', superior: 'QuickDASH', inferior: 'LEFS' };
const performanceByContext = { lumbar: '30s-CST', cervical: 'TUG', superior: 'PSFS', inferior: '30s-CST', mayor: 'TUG', marcha: '10MWT', resistencia: '6MWT' };

const unique = (items) => [...new Set(items.filter(Boolean))];
batteryForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  const goal = batteryForm.querySelector('[data-builder-goal]').value;
  const context = batteryForm.querySelector('[data-builder-context]').value;
  const phase = batteryForm.querySelector('[data-builder-phase]').value;
  const budget = Number.parseInt(batteryForm.querySelector('[data-builder-time]').value, 10);
  let selection = [];
  if (goal === 'funcion_regional') selection.push(regional[context] || 'PSFS');
  else selection.push(primaryByGoal[goal] || regional[context] || 'PSFS');
  if (budget >= 10 && regional[context] && !selection.includes(regional[context])) selection.push(regional[context]);
  if (budget >= 10 && ['inferior', 'mayor', 'marcha', 'resistencia', 'lumbar', 'cervical'].includes(context)) selection.push(performanceByContext[context]);
  if (phase === 'seguimiento' && budget >= 20) selection.push('PGIC');
  selection = unique(selection);
  while (selection.reduce((sum, item) => sum + batteryMinutes[item], 0) > budget && selection.length > 1) selection.pop();
  const minutes = selection.reduce((sum, item) => sum + batteryMinutes[item], 0);
  if (minutes > budget) {
    const item = selection[0];
    batteryResult.innerHTML = `<span class="battery-result-kicker">El tiempo no alcanza</span><h3>No recortes ${item}</h3><p>La opción canónica de esta colección requiere unos ${minutes} minutos. Amplía el tiempo disponible o selecciona otro dominio; no recomendamos acortar un instrumento sin una versión validada.</p><ul><li><a href="${batteryLinks[item]}">Revisar ${item}</a><span>${minutes} min aprox.</span></li></ul><small>El tiempo orienta la batería, pero no justifica modificar ítems o puntuación.</small>`;
    batteryResult.classList.add('has-result');
    return;
  }
  const links = selection.map((item) => `<li><a href="${batteryLinks[item]}">${item}</a><span>${batteryMinutes[item]} min aprox.</span></li>`).join('');
  const performanceIncluded = selection.some((item) => ['30s-CST', 'TUG', '10MWT', '6MWT'].includes(item));
  batteryResult.innerHTML = `<span class="battery-result-kicker">Propuesta mínima · ${minutes} min aprox.</span><h3>${selection.join(' + ')}</h3><ul>${links}</ul><p>${performanceIncluded ? 'Combina percepción y ejecución. Mantén el protocolo de rendimiento idéntico en el seguimiento.' : 'Prioriza el constructo elegido. Añade rendimiento solo si una tarea objetiva cambiará la decisión.'}</p><small>Comprueba versión, licencia, seguridad y población antes de administrar.</small>`;
  batteryResult.classList.add('has-result');
});

const jointForm = document.querySelector('[data-joint-reading]');
const jointResult = document.querySelector('[data-joint-result]');
jointForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  const prom = Number.parseFloat(jointForm.querySelector('[data-joint-prom]').value);
  const performance = Number.parseFloat(jointForm.querySelector('[data-joint-performance]').value);
  if (!Number.isFinite(prom) || !Number.isFinite(performance)) {
    jointResult.innerHTML = '<strong>Faltan datos.</strong><span>Introduce ambos cambios numéricos.</span>';
    return;
  }
  const orient = (value, direction) => Math.sign(direction === 'lower' ? -value : value);
  const promSign = orient(prom, jointForm.querySelector('[data-joint-prom-direction]').value);
  const performanceSign = orient(performance, jointForm.querySelector('[data-joint-performance-direction]').value);
  let key = 'mixed';
  let title = 'Direcciones discordantes';
  if (promSign === 0 && performanceSign === 0) { key = 'stable'; title = 'Ambas vías estables'; }
  else if (promSign > 0 && performanceSign > 0) { key = 'both_improve'; title = 'Ambas vías mejoran'; }
  else if (promSign < 0 && performanceSign < 0) { key = 'both_worsen'; title = 'Ambas vías empeoran'; }
  else if (promSign > 0 && performanceSign <= 0) { key = 'self_report_only'; title = 'Mejora percibida sin mejora equivalente de rendimiento'; }
  else if (performanceSign > 0 && promSign <= 0) { key = 'performance_only'; title = 'Mejora de rendimiento sin mejora percibida equivalente'; }
  const guidance = JSON.parse(jointForm.dataset.guidance);
  jointResult.innerHTML = `<strong>${title}</strong><span>${guidance[key]}</span>`;
});
