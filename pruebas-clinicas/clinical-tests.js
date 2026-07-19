if (!window.__clinicalTestsInitialized) {
window.__clinicalTestsInitialized = true;
const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const search = document.querySelector('[data-clinical-search]');
const region = document.querySelector('[data-clinical-region]');
let cards = [...document.querySelectorAll('[data-suspicion-card]')];
const count = document.querySelector('[data-clinical-count]');
const empty = document.querySelector('[data-clinical-empty]');

function filterSuspicions() {
  const query = normalize(search?.value.trim() || '');
  const selectedRegion = region?.value || 'all';
  let visible = 0;
  cards.forEach((card) => {
    const matches = (!query || normalize(card.dataset.search || card.textContent).includes(query)) &&
      (selectedRegion === 'all' || card.dataset.region === selectedRegion);
    card.hidden = !matches;
    if (matches) visible += 1;
  });
  if (count) count.textContent = visible;
  if (empty) empty.hidden = visible !== 0;
}

search?.addEventListener('input', filterSuspicions);
region?.addEventListener('change', filterSuspicions);
document.querySelectorAll('[data-region-link]').forEach((link) => {
  link.addEventListener('click', () => {
    if (!region) return;
    region.value = link.dataset.regionLink || 'all';
    filterSuspicions();
    document.querySelectorAll('[data-region-link]').forEach((item) => {
      const active = item.dataset.regionLink === region.value;
      item.classList.toggle('is-active', active);
      if (active) item.setAttribute('aria-current', 'true');
      else item.removeAttribute('aria-current');
    });
  });
});
filterSuspicions();

}
