const DATA_URL = './data/shoulder.json';
const IS_PROFESSIONAL = document.body?.dataset.audience === 'professional';
const CORPUS_URL = IS_PROFESSIONAL ? './data/guides-professional.json?v=1' : './data/guides.json?v=3';
const VISUAL_FLOW_URL = './data/visual-flow.json?v=9';
const PAIN_PATTERNS_URL = './data/pain-patterns.json?v=8';
const CALIBRATION_STORAGE_KEY = 'fisiologico-anatomy-calibration-v1';
const CALIBRATION_SCHEMA = 'regional-anatomy-v2';

const state = { data: null, corpus: null, visualFlow: null, painPatterns: { items: [] }, zone: null, corpusLimit: 12, selectedRegion: null, selectedSubzone: 'all', selectedVisualView: 'front', selectedVisualZone: null, comparison: new Set(), lastChapterTrigger: null };
const results = document.querySelector('[data-muscle-results]');
const summary = document.querySelector('[data-result-summary]');
const empty = document.querySelector('[data-empty-map]');

const escapeHtml = (value = '') => value.replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

const list = (items) => `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
const normalise = (value = '') => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const setJourneyStep = (stepNumber) => {
  document.querySelectorAll('[data-journey-step]').forEach((step) => {
    const current = step.dataset.journeyStep === String(stepNumber);
    step.classList.toggle('is-current', current);
    if (current) step.setAttribute('aria-current', 'step'); else step.removeAttribute('aria-current');
  });
};

const relationCopy = IS_PROFESSIONAL ? {
  primary: { eyebrow: 'Esta zona forma parte del patrón', badge: 'Zona habitual' },
  secondary: { eyebrow: 'El patrón puede extenderse a esta zona', badge: 'Zona posible' },
  related: { eyebrow: 'Patrón muscular relacionado', badge: 'Relacionado' }
} : {
  primary: { eyebrow: 'El dibujo incluye esta zona', badge: 'Zona habitual' },
  secondary: { eyebrow: 'El dolor puede llegar hasta aquí', badge: 'Zona posible' },
  related: { eyebrow: 'Músculo que puede guardar relación', badge: 'Relacionado' }
};

const relatedLinks = (names) => names.map((name) => {
  const target = state.data.muscles.find((muscle) => muscle.name === name);
  if (target) return `<a href="#muscle-${target.id}" data-muscle-link="${target.id}">${escapeHtml(name)}</a>`;
  const query = normalise(name);
  const chapter = state.corpus.chapters.find((item) => normalise(item.title).includes(query));
  return chapter ? `<a href="#chapter-${chapter.id}" data-chapter-link="${chapter.id}">${escapeHtml(name)}</a>` : `<span>${escapeHtml(name)}</span>`;
}).join(', ');

const patientSectionLabels = IS_PROFESSIONAL ? {
  intro: 'Presentación clínica',
  where_it_may_be_felt: 'Patrón de dolor referido',
  what_you_may_notice: 'Síntomas y limitación funcional',
  what_may_influence_it: 'Activación y perpetuación',
  corrective_actions: 'Acciones correctivas',
  first_steps: 'Orientación inicial',
  when_to_consult: 'Derivación y consulta',
  other_explanations: 'Diagnóstico diferencial y valoración'
} : {
  intro: 'En pocas palabras',
  where_it_may_be_felt: 'Dónde podrías notarlo',
  what_you_may_notice: 'Qué suele acompañarlo',
  what_may_influence_it: 'Qué puede empeorarlo',
  corrective_actions: 'Qué puedes probar',
  first_steps: 'Por dónde empezar',
  when_to_consult: 'Cuándo pedir ayuda',
  other_explanations: 'Si no encaja contigo'
};

const patientSection = ([key, value]) => {
  const content = Array.isArray(value)
    ? `<ul>${value.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
    : `<p>${escapeHtml(value)}</p>`;
  return `<section class="chapter-section chapter-section-${escapeHtml(key)}"><h4>${escapeHtml(patientSectionLabels[key] || key)}</h4>${content}</section>`;
};

const regionLabels = {
  'cabeza': 'Cabeza', 'atm-mandibula': IS_PROFESSIONAL ? 'ATM y mandíbula' : 'Mandíbula y oído', 'cuello': 'Cuello',
  hombro: 'Hombro', brazo: 'Brazo', codo: 'Codo', antebrazo: 'Antebrazo',
  muneca: 'Muñeca', mano: 'Mano', 'torax-abdomen': IS_PROFESSIONAL ? 'Tórax y abdomen' : 'Pecho y abdomen',
  dorsales: IS_PROFESSIONAL ? 'Dorsales' : 'Parte media de la espalda', lumbares: IS_PROFESSIONAL ? 'Lumbares' : 'Parte baja de la espalda', pelvis: 'Pelvis',
  cadera: 'Cadera', muslo: 'Muslo', rodilla: 'Rodilla', pierna: 'Pierna',
  tobillo: 'Tobillo', pie: 'Pie',
  'cabeza-cuello': 'Cabeza y cuello', 'hombro-brazo': 'Hombro y brazo',
  'codo-muneca-mano': 'Codo, muñeca y mano', 'muneca-mano': 'Muñeca y mano',
  'tronco-suelo-pelvico': 'Tronco y suelo pélvico', 'cadera-muslo': 'Cadera y muslo',
  'cadera-muslo-rodilla': 'Cadera, muslo y rodilla', 'pierna-tobillo-pie': 'Pierna, tobillo y pie'
};

const kneeChapterIds = new Set([
  'consideraciones-clinicas-de-dolor-de-cadera-muslo-y-rodilla',
  'cuadriceps-y-sartorio', 'gemelos', 'isquiotibiales', 'popliteo'
]);

const elbowChapterIds = new Set([
  'consideraciones-clinicas-de-dolor-de-codo-muneca-y-mano',
  'extensores-de-la-muneca-y-braquiorradial',
  'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo',
  'supinador'
]);

const headChapterIds = new Set([
  'consideraciones-clinicas-de-dolor-de-cabeza-y-cuello',
  'esplenio-de-cabeza-y-cuello', 'esternocleidomastoideo-y-masetero',
  'musculos-cervicales-posteriores', 'musculos-faciales', 'occipitofrontal',
  'suboccipitales', 'temporal'
]);

const atmChapterIds = new Set([
  'consideraciones-clinicas-de-dolor-de-cabeza-y-cuello', 'digastrico',
  'esternocleidomastoideo-y-masetero', 'musculos-faciales',
  'pterigoideo-lateral', 'pterigoideo-medial', 'temporal'
]);

const neckChapterIds = new Set([
  'consideraciones-clinicas-de-dolor-de-cabeza-y-cuello', 'digastrico',
  'escalenos', 'esplenio-de-cabeza-y-cuello',
  'esternocleidomastoideo-y-masetero', 'musculos-cervicales-posteriores',
  'suboccipitales'
]);

const chapterRegions = (chapter) => {
  const inferred = state.visualFlow?.regions
    .filter((item) => item.zones.some((zone) => zone.candidates.includes(chapter.id)))
    .map((item) => item.id) || [];
  if (inferred.length) return [...new Set(inferred)];
  const clinicalRegions = {
    'cabeza-cuello': ['cabeza', 'atm-mandibula', 'cuello'],
    'hombro-brazo': ['hombro', 'brazo', 'dorsales'],
    'codo-muneca-mano': ['codo', 'antebrazo', 'muneca', 'mano'],
    'tronco-suelo-pelvico': ['torax-abdomen', 'dorsales', 'lumbares', 'pelvis'],
    'cadera-muslo-rodilla': ['cadera', 'muslo', 'rodilla'],
    'pierna-tobillo-pie': ['pierna', 'tobillo', 'pie']
  };
  return clinicalRegions[chapter.region] || [chapter.region];
};

const bodyRegions = [
  ['cabeza', 'Cabeza'],
  ['atm-mandibula', IS_PROFESSIONAL ? 'ATM y mandíbula' : 'Mandíbula y oído'],
  ['cuello', 'Cuello'],
  ['hombro', 'Hombro'],
  ['brazo', 'Brazo'],
  ['codo', 'Codo'],
  ['antebrazo', 'Antebrazo'],
  ['muneca', 'Muñeca'],
  ['mano', 'Mano'],
  ['torax-abdomen', IS_PROFESSIONAL ? 'Tórax y abdomen' : 'Pecho y abdomen'],
  ['dorsales', IS_PROFESSIONAL ? 'Dorsales' : 'Parte media de la espalda'],
  ['lumbares', IS_PROFESSIONAL ? 'Lumbares' : 'Parte baja de la espalda'],
  ['pelvis', 'Pelvis'],
  ['cadera', 'Cadera'],
  ['muslo', 'Muslo'],
  ['rodilla', 'Rodilla'],
  ['pierna', 'Pierna'],
  ['tobillo', 'Tobillo'],
  ['pie', 'Pie']
];

const bodyRegionGroups = [
  ['Cabeza y cuello', ['cabeza', 'atm-mandibula', 'cuello']],
  ['Miembro superior', ['hombro', 'brazo', 'codo', 'antebrazo', 'muneca', 'mano']],
  ['Tronco', ['torax-abdomen', 'dorsales', 'lumbares', 'pelvis']],
  ['Miembro inferior', ['cadera', 'muslo', 'rodilla', 'pierna', 'tobillo', 'pie']]
];
const bodyRegionLabelMap = new Map(bodyRegions);

const visualViewLabels = {
  front: 'Vista anterior',
  lateral: 'Vista lateral',
  medial: 'Vista interna',
  plantar: 'Vista plantar',
  back: 'Vista posterior'
};
const visualViewTabLabels = { front: 'Anterior', lateral: 'Lateral', medial: 'Interna', plantar: 'Plantar', back: 'Posterior' };
const visualRegionQuestion = {
  cabeza: 'en la cabeza',
  'atm-mandibula': IS_PROFESSIONAL ? 'en la ATM o la mandíbula' : 'en la mandíbula o junto al oído',
  cuello: 'en el cuello',
  hombro: 'en el hombro',
  brazo: 'en el brazo',
  codo: 'en el codo',
  antebrazo: 'en el antebrazo',
  muneca: 'en la muñeca',
  mano: 'en la mano',
  'torax-abdomen': IS_PROFESSIONAL ? 'en el tórax o el abdomen' : 'en el pecho o el abdomen',
  dorsales: IS_PROFESSIONAL ? 'en la espalda dorsal' : 'en la parte media de la espalda',
  lumbares: IS_PROFESSIONAL ? 'en la zona lumbar' : 'en la parte baja de la espalda',
  pelvis: 'en la pelvis',
  cadera: 'en la cadera',
  muslo: 'en el muslo',
  rodilla: 'en la rodilla',
  pierna: 'en la pierna',
  tobillo: 'en el tobillo',
  pie: 'en el pie'
};

const visualRegion = (regionId = state.selectedRegion) => state.visualFlow?.regions.find((region) => region.id === regionId);
const visualZone = (zoneId = state.selectedVisualZone) => visualRegion()?.zones.find((zone) => zone.id === zoneId);
const patientZoneNames = {
  'cabeza-superior': 'La parte superior de la cabeza', 'region-frontal': 'La frente', 'region-temporal': 'La sien',
  'region-ocular-ceja': 'El ojo y la ceja', 'region-occipital': 'La parte posterior de la cabeza',
  'region-auricular-atm': 'El oído y la articulación de la mandíbula', 'region-mejilla-mandibula': 'La mejilla y la mandíbula',
  'region-dental': 'Los dientes y la mandíbula', 'garganta-cuello-anterior': 'La parte delantera de la garganta y el cuello',
  'cuello-posterior': 'La parte posterior del cuello', 'codo-antecubital': 'La parte delantera del codo',
  'codo-olecraniana': 'La parte posterior del codo', 'epicondilo-medial': 'La parte interna del codo',
  'epicondilo-lateral': 'La parte externa del codo', 'antebrazo-volar': 'La parte delantera del antebrazo',
  'antebrazo-dorsal': 'La parte posterior del antebrazo', 'antebrazo-radial': 'El lado del pulgar del antebrazo',
  'antebrazo-ulnar': 'El lado del meñique del antebrazo', 'muneca-dorsal': 'La parte de atrás de la muñeca',
  'muneca-palmar': 'La parte de la palma junto a la muñeca', 'mano-dorsal': 'La parte de atrás de la mano',
  'mano-palmar': 'La palma de la mano', 'base-pulgar-mano-radial': 'La base del pulgar',
  'dedos-dorsales': 'La parte de atrás de los dedos', 'dedos-palmares': 'La parte de la palma de los dedos',
  'torax-pecho-anterior': 'La parte delantera del pecho', 'torax-lateral': 'El lateral del pecho',
  'toracica-superior-posterior': 'La parte alta de la espalda', 'toracica-media-posterior': 'La parte media de la espalda',
  'toracica-posterior-general': 'La espalda', 'region-lumbar': 'La parte baja de la espalda',
  'region-iliolumbar-iliosacra': 'Un lado de la parte baja de la espalda, junto a la pelvis',
  'region-sacra': 'La zona central entre la espalda y las nalgas', 'region-glutea-nalga': 'La nalga',
  'talon': 'El talón', 'plantar-mediopie': 'La parte media de la planta del pie',
  'plantar-cabezas-metatarsales': 'La almohadilla de la planta, detrás de los dedos',
  'dorsal-antepie': 'La parte superior del pie', 'plantar-dedo-gordo': 'La parte de abajo del dedo gordo',
  'dorsal-dedo-gordo': 'La parte de arriba del dedo gordo', 'plantar-dedos-menores': 'La parte de abajo de los dedos menores',
  'dorsal-dedos-menores': 'La parte de arriba de los dedos menores'
};
const plainZoneLabel = (zone) => {
  if (IS_PROFESSIONAL) return zone.label;
  if (patientZoneNames[zone.id]) return patientZoneNames[zone.id];
  return zone.label
    .replace(/^Región anteromedial de la /, 'La parte delantera e interna de la ')
    .replace(/^Región anterior de la /, 'La parte delantera de la ')
    .replace(/^Región anterior del /, 'La parte delantera del ')
    .replace(/^Región posterior de la /, 'La parte posterior de la ')
    .replace(/^Región posterior del /, 'La parte posterior del ')
    .replace(/^Región lateral de la /, 'La parte externa de la ')
    .replace(/^Región lateral del /, 'La parte externa del ')
    .replace(/^Región medial de la /, 'La parte interna de la ')
    .replace(/^Región medial del /, 'La parte interna del ')
    .replace(/^Región abdominal inferior$/, 'La parte baja del abdomen')
    .replace(/^Región abdominal$/, 'El abdomen')
    .replace(/^Región pélvica$/, 'La pelvis')
    .replace(/^Región /, 'La zona ');
};
const visualAsset = (region, view) => Object.prototype.hasOwnProperty.call(region.assets || {}, view)
  ? region.assets[view]
  : (region.asset || state.visualFlow.asset);
const visualCoordinateSpace = (region) => region.coordinate_space || state.visualFlow.coordinate_space;
const availableVisualViews = (region) => region.views.filter((view) => Boolean(visualAsset(region, view)));

const zoneGeometry = (zone) => {
  if (Array.isArray(zone.polygon) && zone.polygon.length >= 3) {
    const points = zone.polygon.map(([x, y]) => [Number(x), Number(y)]);
    const cx = points.reduce((sum, point) => sum + point[0], 0) / points.length;
    const cy = points.reduce((sum, point) => sum + point[1], 0) / points.length;
    const rx = Math.max(12, ...points.map((point) => Math.abs(point[0] - cx)));
    const ry = Math.max(10, ...points.map((point) => Math.abs(point[1] - cy)));
    return { type: 'polygon', points, cx, cy, rx, ry };
  }
  const [cx, cy, rx, ry] = zone.ellipse.map(Number);
  return { type: 'ellipse', cx, cy, rx, ry };
};

const zoneShape = (geometry, className, extra = '') => geometry.type === 'polygon'
  ? `<polygon class="${className}" points="${geometry.points.map((point) => point.join(',')).join(' ')}" ${extra}></polygon>`
  : `<ellipse class="${className}" cx="${geometry.cx}" cy="${geometry.cy}" rx="${geometry.rx}" ry="${geometry.ry}" ${extra}></ellipse>`;

const applyOverviewLandmarks = (visualFlow) => {
  if (!visualFlow?.overview) return;
  document.querySelectorAll('.whole-body-view').forEach((view) => {
    const viewId = view.classList.contains('back') ? 'back' : 'front';
    view.querySelectorAll('[data-body-region]').forEach((button) => {
      const point = visualFlow.overview[viewId]?.[button.dataset.bodyRegion];
      if (!Array.isArray(point) || point.length !== 2) return;
      button.style.setProperty('--hotspot-x', `${point[0]}%`);
      button.style.setProperty('--hotspot-y', `${point[1]}%`);
    });
  });
};

const updateVisualUrl = (chapterId = null) => {
  const url = new URL(window.location.href);
  if (state.selectedRegion) url.searchParams.set('region', state.selectedRegion); else url.searchParams.delete('region');
  if (state.selectedVisualZone) url.searchParams.set('zone', state.selectedVisualZone); else url.searchParams.delete('zone');
  if (chapterId) url.searchParams.set('guide', chapterId); else url.searchParams.delete('guide');
  url.hash = 'explorador';
  window.history.replaceState({}, '', url);
};

const visualSvg = (region, view, zones, { interactive = false, selectedZoneId = null, label = '' } = {}) => {
  const crop = region.crops[view];
  const [imageWidth, imageHeight] = visualCoordinateSpace(region);
  const shapes = zones.map((zone, index) => {
    const geometry = zoneGeometry(zone);
    const { cx, cy, rx, ry } = geometry;
    if (!interactive) {
      const core = geometry.type === 'polygon'
        ? zoneShape(geometry, 'pattern-core', `transform="translate(${cx} ${cy}) scale(.56) translate(${-cx} ${-cy})"`)
        : `<ellipse class="pattern-core" cx="${cx}" cy="${cy}" rx="${Math.max(12, rx * .55)}" ry="${Math.max(10, ry * .55)}"></ellipse>`;
      return `<g class="pattern-zone">${zoneShape(geometry, 'pattern-spread')}${core}</g>`;
    }
    const selected = selectedZoneId === zone.id ? ' is-selected' : '';
    const hit = geometry.type === 'polygon'
      ? zoneShape(geometry, 'visual-zone-hit')
      : `<ellipse class="visual-zone-hit" cx="${cx}" cy="${cy}" rx="${Math.max(rx, 28)}" ry="${Math.max(ry, 28)}"></ellipse>`;
    return `<g class="visual-zone${selected}" role="button" tabindex="0" data-visual-zone="${escapeHtml(zone.id)}" aria-label="${index + 1}. ${escapeHtml(plainZoneLabel(zone))}">${hit}${zoneShape(geometry, 'visual-zone-area')}<circle class="visual-zone-marker" cx="${cx}" cy="${cy}" r="18"></circle><text class="visual-zone-number" x="${cx}" y="${cy + 6}" text-anchor="middle">${index + 1}</text></g>`;
  }).join('');
  return `<svg class="visual-region-svg${interactive ? ' is-interactive' : ' is-pattern'}" viewBox="${crop.join(' ')}" role="img" aria-label="${escapeHtml(label)}"><image href="${escapeHtml(visualAsset(region, view))}" x="0" y="0" width="${imageWidth}" height="${imageHeight}"></image>${shapes}</svg>`;
};

const renderVisualView = (view) => {
  const region = visualRegion();
  const availableViews = region ? availableVisualViews(region) : [];
  if (!region || !availableViews.includes(view)) return;
  state.selectedVisualView = view;
  const zones = region.zones.filter((zone) => zone.view === view);
  const tabs = document.querySelector('[data-visual-view-tabs]');
  tabs.style.setProperty('--visual-view-count', availableViews.length);
  tabs.innerHTML = availableViews.map((viewId) => `<button type="button" data-visual-view="${viewId}" aria-label="${visualViewLabels[viewId]}" aria-pressed="${viewId === view}" class="${viewId === view ? 'is-selected' : ''}">${visualViewTabLabels[viewId]}</button>`).join('');
  document.querySelector('[data-visual-map]').innerHTML = visualSvg(region, view, zones, { interactive: true, selectedZoneId: state.selectedVisualZone, label: `${region.label}, ${visualViewLabels[view].toLowerCase()}. Las zonas numeradas son seleccionables.` });
  document.querySelector('[data-visual-zone-list]').innerHTML = zones.map((zone, index) => `<button type="button" data-visual-zone="${escapeHtml(zone.id)}" aria-pressed="${zone.id === state.selectedVisualZone}" class="${zone.id === state.selectedVisualZone ? 'is-selected' : ''}"><span>${index + 1}</span>${escapeHtml(plainZoneLabel(zone))}</button>`).join('');
};

const painPatternsForChapter = (chapterId) => state.painPatterns.items
  .filter((pattern) => pattern.chapter_id === chapterId);

const painPatternImage = (pattern, className = 'pain-pattern-image') => {
  const views = Array.isArray(pattern.views) && pattern.views.length ? pattern.views : [pattern];
  return `<div class="pain-pattern-view-grid" data-view-count="${views.length}">${views.map((view) => `<div class="pain-pattern-view"><img class="${className}" src="${escapeHtml(view.image)}" alt="${escapeHtml(IS_PROFESSIONAL ? view.alt : `Dibujo para comparar dónde puede sentirse el dolor relacionado con ${pattern.name}, ${(view.label || 'vista anatómica').toLowerCase()}.`)}" width="${view.width}" height="${view.height}" loading="lazy" decoding="async"></div>`).join('')}</div>`;
};

const chapterPatternGallery = (chapter) => {
  const patterns = painPatternsForChapter(chapter.id);
  if (!patterns.length) return '';
  return `<section class="chapter-pattern-gallery" aria-labelledby="chapter-pattern-title-${chapter.id}">
    <div class="chapter-pattern-gallery-heading"><p class="section-label">${IS_PROFESSIONAL ? 'Mapas de dolor referido' : 'Dónde puede aparecer'}</p><h4 id="chapter-pattern-title-${chapter.id}">${IS_PROFESSIONAL ? 'Compara las distribuciones visuales' : 'Compara los dibujos con lo que sientes'}</h4><p>${IS_PROFESSIONAL ? 'Las áreas coloreadas representan distribuciones orientativas y deben integrarse con anamnesis, exploración y diagnóstico diferencial.' : 'Las zonas coloreadas orientan. Que un dibujo se parezca a tu dolor no demuestra cuál es la causa.'}</p></div>
    <div class="chapter-pattern-gallery-grid">${patterns.map((pattern) => `<figure>${painPatternImage(pattern)}<figcaption><strong>${escapeHtml(pattern.name)}</strong><span>${IS_PROFESSIONAL ? 'Patrón orientativo' : 'Mapa para comparar'}</span></figcaption></figure>`).join('')}</div>
  </section>`;
};

const candidatePatternCard = (chapter, region, selectedZone) => {
  const zones = region.zones.filter((zone) => zone.view === selectedZone.view && zone.candidates.includes(chapter.id));
  const painPatterns = painPatternsForChapter(chapter.id);
  const firstPattern = painPatterns[0];
  const where = chapter.patient_content?.where_it_may_be_felt;
  const teaser = Array.isArray(where) ? where[0] : (where || chapter.patient_content?.intro || (IS_PROFESSIONAL ? 'Consulta la presentación clínica y el patrón referido.' : 'Abre la guía para ver dónde podrías notarlo.'));
  return `<article class="visual-pattern-card">
    <figure>${firstPattern ? painPatternImage(firstPattern) : visualSvg(region, selectedZone.view, zones, { label: `${IS_PROFESSIONAL ? 'Distribución orientativa' : 'Zonas coloreadas'} para ${patientTitle(chapter)}` })}<figcaption>${firstPattern ? `${IS_PROFESSIONAL ? 'Mapa dibujado' : 'Dibujo'} · ${painPatterns.length} ${painPatterns.length === 1 ? 'vista' : 'vistas'}` : `${IS_PROFESSIONAL ? 'Distribución orientativa' : 'Mapa para comparar'} · ${visualViewLabels[selectedZone.view].replace('Vista ', '')}`}</figcaption></figure>
    <div class="visual-pattern-card-copy"><p>${IS_PROFESSIONAL ? 'Coincide en' : 'Puede sentirse en'} ${escapeHtml(plainZoneLabel(selectedZone).toLowerCase())}</p><h3>${escapeHtml(patientTitle(chapter))}</h3><span>${escapeHtml(teaser)}</span><button type="button" data-open-visual-chapter="${chapter.id}">${IS_PROFESSIONAL ? 'Abrir ficha clínica' : 'Ver esta guía'} →</button></div>
  </article>`;
};

function selectVisualZone(zoneId, { focusResults = true } = {}) {
  const region = visualRegion();
  const zone = region?.zones.find((item) => item.id === zoneId);
  if (!region || !zone || !visualAsset(region, zone.view)) return;
  state.selectedVisualZone = zoneId;
  state.selectedVisualView = zone.view;
  renderVisualView(zone.view);
  const chapters = zone.candidates.map((id) => state.corpus.chapters.find((chapter) => chapter.id === id)).filter(Boolean);
  const patterns = document.querySelector('[data-visual-patterns]');
  const detail = document.querySelector('[data-visual-chapter-detail]');
  detail.hidden = true;
  detail.innerHTML = '';
  patterns.hidden = false;
  document.querySelector('[data-visual-flow-next]').hidden = false;
  document.querySelector('[data-visual-patterns-title]').textContent = IS_PROFESSIONAL ? '¿Qué distribución se aproxima al patrón descrito?' : '¿Qué dibujo se parece más a lo que sientes?';
  document.querySelector('[data-visual-pattern-count]').textContent = `${chapters.length} ${chapters.length === 1 ? (IS_PROFESSIONAL ? 'patrón muscular' : 'mapa') : (IS_PROFESSIONAL ? 'patrones musculares' : 'mapas')} · ${plainZoneLabel(zone)}`;
  document.querySelector('[data-visual-pattern-grid]').innerHTML = chapters.map((chapter) => candidatePatternCard(chapter, region, zone)).join('');
  document.querySelector('[data-visual-zone-status]').textContent = `${plainZoneLabel(zone)}: ${chapters.length} ${chapters.length === 1 ? (IS_PROFESSIONAL ? 'patrón relacionado' : 'mapa relacionado') : (IS_PROFESSIONAL ? 'patrones relacionados' : 'mapas relacionados')}.`;
  document.querySelector('[data-visual-zone-crumb]').textContent = plainZoneLabel(zone);
  document.querySelector('[data-visual-zone-crumb]').hidden = false;
  document.querySelector('[data-zone-crumb-separator]').hidden = false;
  setJourneyStep(3);
  updateVisualUrl();
  if (focusResults) {
    patterns.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    document.querySelector('[data-visual-patterns-title]').focus({ preventScroll: true });
  }
}

function renderVisualRegion(regionId, { focus = true } = {}) {
  const region = visualRegion(regionId);
  if (!region) return;
  state.selectedRegion = regionId;
  state.selectedVisualZone = null;
  state.selectedVisualView = availableVisualViews(region)[0];
  document.querySelector('[data-shoulder-detail]').hidden = true;
  document.querySelector('[data-region-pathway]').hidden = true;
  const flow = document.querySelector('[data-visual-flow]');
  flow.hidden = false;
  document.querySelector('[data-visual-region-crumb]').textContent = region.label;
  document.querySelector('[data-visual-zone-crumb]').hidden = true;
  document.querySelector('[data-zone-crumb-separator]').hidden = true;
  document.querySelector('[data-visual-flow-title]').textContent = `¿Dónde lo notas ${visualRegionQuestion[regionId] || `en ${region.label.toLowerCase()}`}?`;
  document.querySelector('[data-visual-patterns]').hidden = true;
  document.querySelector('[data-visual-flow-next]').hidden = true;
  document.querySelector('[data-visual-chapter-detail]').hidden = true;
  document.querySelector('[data-visual-chapter-detail]').innerHTML = '';
  document.querySelector('[data-visual-zone-status]').textContent = 'Selecciona una zona para continuar.';
  renderVisualView(state.selectedVisualView);
  setJourneyStep(2);
  updateVisualUrl();
  if (focus) {
    flow.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    document.querySelector('[data-visual-flow-title]').focus({ preventScroll: true });
  }
}

const regionSubzones = {
  'pierna-tobillo-pie': [
    ['all', 'Toda la región', []],
    ['pantorrilla', 'Pantorrilla', ['gemelos', 'soleo-y-plantar', 'tibial-posterior']],
    ['parte-anterior', 'Parte anterior de la pierna', ['tibial-anterior', 'extensores-largos-del-pie']],
    ['tobillo-interno', 'Tobillo interno', ['tibial-posterior', 'flexores-largos-del-pie']],
    ['tobillo-externo', 'Tobillo externo', ['fibulares-largo-corto-y-tercero']],
    ['talon', 'Talón', ['gemelos', 'soleo-y-plantar', 'tibial-posterior']],
    ['empeine', 'Empeine', ['extensores-largos-del-pie', 'tibial-anterior']],
    ['planta', 'Planta del pie', ['musculatura-intrinseca-del-pie', 'flexores-largos-del-pie', 'tibial-posterior', 'soleo-y-plantar']],
    ['dedos', 'Dedos', ['extensores-largos-del-pie', 'flexores-largos-del-pie', 'musculatura-intrinseca-del-pie']]
  ]
};

const patientTitle = (chapter) => {
  const title = chapter.chapter_type === 'ficha_muscular'
    ? chapter.title.replace(/^Músculos?\s+/i, '')
    : chapter.title.replace(/^Consideraciones clínicas\s+(?:de|del)\s+/i, '').replace(/^Consideraciones clínicas\s+/i, '');
  return title.charAt(0).toUpperCase() + title.slice(1);
};

const chapterRegionLabel = (chapter) => chapterRegions(chapter)
  .map((region) => regionLabels[region])
  .filter(Boolean)
  .join(' · ') || 'Otras regiones';

const chapterCard = (chapter) => `
  <article class="chapter-card" id="chapter-${chapter.id}" data-chapter-card data-regions="${chapterRegions(chapter).join(' ')}" data-type="${chapter.chapter_type}" data-search="${escapeHtml(normalise(chapter.title))}">
    <p>${chapter.chapter_type === 'ficha_muscular' ? 'Músculo' : 'Guía por zona o situación'} · ${escapeHtml(chapterRegionLabel(chapter))}</p>
    <h3>${escapeHtml(patientTitle(chapter))}</h3>
    <p class="chapter-card-intro">${escapeHtml(chapter.patient_content?.intro || (IS_PROFESSIONAL ? 'Información clínica para contrastar el patrón y orientar el razonamiento.' : 'Información sencilla para comparar el dibujo con lo que sientes.'))}</p>
    <button type="button" data-open-chapter="${chapter.id}">Ver guía →</button>
  </article>`;

const chapterTeaser = (chapter) => {
  const content = chapter.patient_content || {};
  const source = content.where_it_may_be_felt || content.what_you_may_notice || content.intro || '';
  return Array.isArray(source) ? source[0] : source;
};

const structuresForChapter = (chapter) => state.corpus.chapters
  .filter((candidate) => candidate.chapter_type === 'ficha_muscular' && chapterRegions(candidate).some((region) => chapterRegions(chapter).includes(region)))
  .sort((a, b) => patientTitle(a).localeCompare(patientTitle(b), 'es'));

const relatedStructureBlock = (chapter) => {
  if (chapter.chapter_type !== 'consideracion_clinica') return '';
  const structures = structuresForChapter(chapter);
  if (!structures.length) return '';
  return `<section class="chapter-related-structures"><p class="section-label">Continúa por un músculo</p><h4>${structures.length} guías relacionadas con esta zona</h4><p>${IS_PROFESSIONAL ? 'La guía regional aporta contexto. Para comparar patrones concretos, abre una estructura:' : 'Abre un músculo para comparar su dibujo con lo que sientes:'}</p><div>${structures.map((item) => `<button type="button" data-open-related-chapter="${item.id}">${escapeHtml(patientTitle(item))}<span>${IS_PROFESSIONAL ? 'Ver patrón' : 'Ver dibujo'} →</span></button>`).join('')}</div></section>`;
};

const chapterDetail = (chapter) => {
  const sections = Object.entries(chapter.patient_content || {});
  return `
    <button class="chapter-detail-close" type="button" data-close-chapter aria-label="Cerrar guía">×</button>
    <p class="section-label">${chapter.chapter_type === 'ficha_muscular' ? (IS_PROFESSIONAL ? 'Ficha de patrón muscular' : 'Guía de un músculo') : 'Guía por zona o situación'} · ${escapeHtml(chapterRegionLabel(chapter))}</p>
    <h3 tabindex="-1">${escapeHtml(patientTitle(chapter))}</h3>
    ${chapterPatternGallery(chapter)}
    ${relatedStructureBlock(chapter)}
    <p class="chapter-reading-guide"><strong>${IS_PROFESSIONAL ? 'Integra el patrón, no lo interpretes de forma aislada.' : 'Compara, pero no intentes adivinar una causa.'}</strong> ${IS_PROFESSIONAL ? 'Contrasta la presentación, la distribución, los factores de perpetuación y las alternativas antes de formular una hipótesis.' : 'Mira primero dónde aparece el dolor. Después revisa qué puede empeorarlo y qué cambios sencillos puedes probar.'}</p>
    ${sections.length ? `<div class="chapter-preview-grid">${sections.map(patientSection).join('')}</div>` : ''}
    <p class="chapter-caution">${IS_PROFESSIONAL ? 'La concordancia de una distribución no confirma la estructura responsable y debe contextualizarse mediante valoración individual.' : 'Una coincidencia en el dibujo no demuestra que ese músculo sea la causa. Úsalo para entender y explicar mejor lo que sientes.'}</p>
    <div class="chapter-next"><strong>${IS_PROFESSIONAL ? 'Continúa el razonamiento clínico.' : 'Ya tienes una primera orientación.'}</strong><span>${IS_PROFESSIONAL ? 'Compara otras distribuciones e integra los hallazgos con la exploración y el diagnóstico diferencial.' : 'Puedes comparar otro dibujo, volver al cuerpo o pedir una valoración si la molestia no mejora, empeora o limita tu actividad.'}</span><div class="chapter-next-actions">${IS_PROFESSIONAL ? '<a href="../../index.html#contacto">Contactar con FisioLógico →</a>' : '<button type="button" data-close-chapter>Comparar otro dibujo</button><a href="#explorador" data-reset-explorer>Volver al mapa</a><a class="primary" href="../../index.html#contacto">Solicitar valoración →</a>'}</div></div>`;
};

function renderCorpus() {
  const grid = document.querySelector('[data-corpus-grid]');
  const ordered = [...state.corpus.chapters].sort((a, b) => {
    if (a.chapter_type !== b.chapter_type) return a.chapter_type === 'ficha_muscular' ? -1 : 1;
    return patientTitle(a).localeCompare(patientTitle(b), 'es');
  });
  grid.innerHTML = ordered.map(chapterCard).join('');
  document.querySelector('[data-corpus-total]').textContent = state.corpus.chapter_count;
  filterCorpus();
}

const regionStructureCard = (chapter) => {
  const pattern = painPatternsForChapter(chapter.id)[0];
  return `
  <article class="region-structure-card">
    <div class="region-structure-card-top"><p>Guía por estructura</p><label><input type="checkbox" data-compare-chapter="${chapter.id}" ${state.comparison.has(chapter.id) ? 'checked' : ''}> Comparar</label></div>
    ${pattern ? `<figure class="region-structure-pattern">${painPatternImage(pattern)}<figcaption>Mapa de dolor disponible</figcaption></figure>` : ''}
    <h3>${escapeHtml(patientTitle(chapter))}</h3>
    <span>${escapeHtml(chapterTeaser(chapter))}</span>
    <button type="button" data-open-region-chapter="${chapter.id}">${IS_PROFESSIONAL ? 'Comparar este patrón' : 'Ver este mapa'} →</button>
  </article>`;
};

const comparisonValue = (chapter, key) => {
  const value = chapter.patient_content?.[key];
  if (Array.isArray(value)) return value[0] || 'No especificado';
  return value || 'No especificado';
};

function renderComparison() {
  const selected = [...state.comparison].map((id) => state.corpus.chapters.find((chapter) => chapter.id === id)).filter(Boolean);
  const panel = document.querySelector('[data-pattern-comparison]');
  const status = document.querySelector('[data-comparison-status]');
  status.textContent = selected.length === 0 ? `Abre una guía o elige entre dos y tres ${IS_PROFESSIONAL ? 'estructuras' : 'músculos'} para compararlos.` : selected.length === 1 ? `Elige ${IS_PROFESSIONAL ? 'una estructura' : 'un músculo'} más para activar la comparación.` : `${selected.length} ${IS_PROFESSIONAL ? 'estructuras seleccionadas' : 'músculos seleccionados'}. Compara las diferencias antes de abrir una guía completa.`;
  panel.hidden = selected.length < 2;
  if (selected.length < 2) return;
  const rows = [
    ['Dónde puede sentirse', 'where_it_may_be_felt'],
    ['Qué puedes notar', 'what_you_may_notice'],
    ['Qué puede influir', 'what_may_influence_it'],
    ['Primer paso prudente', 'first_steps']
  ];
  document.querySelector('[data-pattern-comparison-table]').innerHTML = `<table><thead><tr><th>Compara</th>${selected.map((chapter) => `<th>${escapeHtml(patientTitle(chapter))}</th>`).join('')}</tr></thead><tbody>${rows.map(([label, key]) => `<tr><th>${label}</th>${selected.map((chapter) => `<td>${escapeHtml(comparisonValue(chapter, key))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function visibleRegionStructures(regionId) {
  const structures = state.corpus.chapters.filter((chapter) => chapter.chapter_type === 'ficha_muscular' && chapterRegions(chapter).includes(regionId));
  const config = regionSubzones[regionId]?.find(([id]) => id === state.selectedSubzone);
  const ids = config?.[2] || [];
  return (ids.length ? structures.filter((chapter) => ids.includes(chapter.id)) : structures)
    .sort((a, b) => patientTitle(a).localeCompare(patientTitle(b), 'es'));
}

function selectSubzone(subzoneId) {
  state.selectedSubzone = subzoneId;
  const structures = visibleRegionStructures(state.selectedRegion);
  document.querySelectorAll('[data-region-subzone]').forEach((button) => {
    const selected = button.dataset.regionSubzone === subzoneId;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  document.querySelector('[data-region-structure-grid]').innerHTML = structures.map(regionStructureCard).join('');
  const label = regionSubzones[state.selectedRegion]?.find(([id]) => id === subzoneId)?.[1];
  document.querySelector('[data-region-pathway-count]').textContent = `${structures.length} ${structures.length === 1 ? 'guía' : 'guías'} por estructura${subzoneId === 'all' ? '' : ` · ${label}`}`;
  renderComparison();
}

function renderRegionPathway(regionId) {
  const pathway = document.querySelector('[data-region-pathway]');
  const chapters = state.corpus.chapters.filter((chapter) => chapterRegions(chapter).includes(regionId));
  const structures = chapters.filter((chapter) => chapter.chapter_type === 'ficha_muscular')
    .sort((a, b) => patientTitle(a).localeCompare(patientTitle(b), 'es'));
  const overviews = chapters.filter((chapter) => chapter.chapter_type === 'consideracion_clinica')
    .sort((a, b) => patientTitle(a).localeCompare(patientTitle(b), 'es'));
  const label = regionLabels[regionId] || 'esta región';
  state.selectedRegion = regionId;
  state.selectedSubzone = 'all';
  state.comparison.clear();
  pathway.hidden = false;
  document.querySelector('[data-region-pathway-title]').textContent = `${structures.length} ${IS_PROFESSIONAL ? 'estructuras' : 'músculos'} relacionados con ${label.toLowerCase()}`;
  document.querySelector('[data-region-pathway-copy]').textContent = IS_PROFESSIONAL ? 'Empieza por las estructuras: cada ficha permite contrastar presentación, distribución, perpetuación y acciones correctivas.' : 'Abre los músculos que más se parezcan a lo que notas. Cada guía explica dónde podrías sentirlo y qué puede empeorarlo.';
  document.querySelector('[data-region-pathway-count]').textContent = structures.length === 1 ? '1 guía por estructura' : `${structures.length} guías por estructura`;
  document.querySelector('[data-region-structure-grid]').innerHTML = structures.map(regionStructureCard).join('');
  const refine = document.querySelector('[data-region-refine]');
  const subzones = regionSubzones[regionId] || [];
  refine.hidden = subzones.length === 0;
  document.querySelector('[data-region-refine-options]').innerHTML = subzones.map(([id, subzoneLabel]) => `<button type="button" data-region-subzone="${id}" aria-pressed="${id === 'all'}" class="${id === 'all' ? 'selected' : ''}">${escapeHtml(subzoneLabel)}</button>`).join('');
  const overviewBox = document.querySelector('[data-region-overviews]');
  overviewBox.hidden = overviews.length === 0;
  document.querySelector('[data-region-overview-links]').innerHTML = overviews.map((chapter) => `<button type="button" data-open-region-chapter="${chapter.id}">${escapeHtml(patientTitle(chapter))} <span>Ver contexto →</span></button>`).join('');
  const detail = document.querySelector('[data-region-chapter-detail]');
  detail.hidden = true;
  detail.innerHTML = '';
  renderComparison();
}

function filterCorpus() {
  const query = normalise(document.querySelector('[data-corpus-search]')?.value.trim() || '');
  const region = document.querySelector('[data-corpus-region]')?.value || 'all';
  const type = document.querySelector('[data-corpus-type]')?.value || 'all';
  let matches = 0;
  document.querySelectorAll('[data-chapter-card]').forEach((cardElement) => {
    const matchesFilters = (!query || cardElement.dataset.search.includes(query)) &&
      (region === 'all' || cardElement.dataset.regions.split(' ').includes(region)) &&
      (type === 'all' || cardElement.dataset.type === type);
    if (matchesFilters) matches += 1;
    cardElement.hidden = !matchesFilters || matches > state.corpusLimit;
  });
  document.querySelector('[data-corpus-count]').textContent = matches;
  updateCorpusGuidance(matches, region);
  const moreButton = document.querySelector('[data-corpus-more]');
  moreButton.hidden = matches <= state.corpusLimit;
}

function updateCorpusGuidance(matches, region) {
  const guidance = document.querySelector('[data-corpus-guidance]');
  const number = document.querySelector('[data-corpus-guidance-number]');
  const title = document.querySelector('[data-corpus-guidance-title]');
  const copy = document.querySelector('[data-corpus-guidance-copy]');
  const action = guidance.querySelector('.corpus-guidance-action');
  number.textContent = matches;
  guidance.classList.toggle('is-empty', matches === 0);
  if (matches === 0) {
    title.textContent = 'No hay tarjetas con estos filtros';
    copy.textContent = 'No significa que no exista una explicación para tu molestia: esta selección solo indica que no hay una guía coincidente en el orientador.';
    action.textContent = 'Prueba a borrar la búsqueda o elige una región o tipo de guía diferente.';
    return;
  }
  const cardLabel = matches === 1 ? 'esta tarjeta' : `estas ${matches} tarjetas`;
  const regionText = region === 'all' ? 'tu búsqueda actual' : `la región de ${regionLabels[region].toLowerCase()}`;
  title.textContent = `${IS_PROFESSIONAL ? 'Cómo interpretar' : 'Qué significan'} ${cardLabel}`;
  copy.textContent = IS_PROFESSIONAL ? `Las tarjetas reúnen estructuras y patrones de ${regionText} que pueden guardar relación con la zona señalada. La concordancia no identifica por sí sola la estructura responsable.` : `Las tarjetas reúnen músculos de ${regionText} cuyos dibujos pueden coincidir con la zona que has señalado. Una coincidencia no significa que ese músculo sea la causa.`;
  action.textContent = IS_PROFESSIONAL ? 'Abre las fichas para contrastar distribuciones y valorar qué información puede modificar el razonamiento clínico.' : 'Abre los dibujos que más se parezcan a lo que notas y apunta qué actividades cambian la molestia.';
}

function selectBodyRegion(regionId) {
  const label = regionLabels[regionId] || 'la región seleccionada';
  document.querySelectorAll('[data-body-region]').forEach((button) => {
    const selected = button.dataset.bodyRegion === regionId;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  setJourneyStep(2);
  document.querySelector('[data-region-pathway]').hidden = true;
  document.querySelector('[data-shoulder-detail]').hidden = true;
  document.querySelector('[data-corpus-search]').value = '';
  document.querySelector('[data-corpus-region]').value = regionId;
  document.querySelector('[data-corpus-type]').value = 'all';
  state.corpusLimit = 12;
  filterCorpus();
  const region = visualRegion(regionId);
  const zoneCount = region?.zones.length || 0;
  document.querySelector('[data-body-selection]').textContent = `${label}: ahora puedes señalar una de ${zoneCount} zonas más precisas.`;
  renderVisualRegion(regionId);
}

function showChapter(chapterId, target = '[data-chapter-detail]', trigger = null) {
  const chapter = state.corpus.chapters.find((item) => item.id === chapterId);
  if (!chapter) return;
  const detail = document.querySelector(target);
  state.lastChapterTrigger = trigger;
  detail.innerHTML = chapterDetail(chapter);
  detail.hidden = false;
  detail.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  detail.querySelector('h3').focus({ preventScroll: true });
}

function navigateToChapter(chapterId) {
  document.querySelector('[data-corpus-search]').value = '';
  document.querySelector('[data-corpus-region]').value = 'all';
  document.querySelector('[data-corpus-type]').value = 'all';
  state.corpusLimit = 12;
  filterCorpus();
  showChapter(chapterId);
}

const card = (muscle, relation) => `
  <article class="muscle-card" id="muscle-${muscle.id}" tabindex="-1">
    <div class="muscle-card-head">
      <p>${relationCopy[relation].eyebrow}</p>
      <h3>${escapeHtml(muscle.name)}</h3>
      <span class="relation ${relation}">${relationCopy[relation].badge}</span>
    </div>
    <p class="muscle-summary">${escapeHtml(muscle.summary)}</p>
    <p class="card-hint">Abre solo los apartados que necesites para comparar.</p>
    <details><summary>Cómo puede sentirse</summary>${list(muscle.sensations)}</details>
    <details><summary>Cómo puede afectar al día a día</summary>${list(muscle.daily_impact)}</details>
    <details><summary>Actividades y factores agravantes</summary><h4>Actividades relacionadas</h4>${list(muscle.related_activities)}<h4>Puede agravarse con</h4>${list(muscle.aggravating_factors)}</details>
    <details><summary>Orientación inicial</summary>${list(muscle.initial_guidance)}</details>
    <details class="assessment"><summary>Cuándo pedir valoración</summary>${list(muscle.seek_assessment)}</details>
    <details><summary>Qué más puede parecerse</summary><p class="related-links"><strong>Patrones musculares:</strong> ${relatedLinks(muscle.similar_patterns)}.</p><p><strong>Otras posibilidades:</strong> ${escapeHtml(muscle.alternatives.join(', '))}.</p></details>
  </article>`;

function navigateToMuscle(muscleId) {
  let target = document.querySelector(`#muscle-${muscleId}`);
  if (!target) {
    const muscle = state.data.muscles.find((item) => item.id === muscleId);
    if (!muscle) return;
    results.insertAdjacentHTML('beforeend', card(muscle, 'related'));
    target = document.querySelector(`#muscle-${muscleId}`);
  }
  target.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  target.focus({ preventScroll: true });
  target.classList.add('muscle-card-highlight');
  window.setTimeout(() => target.classList.remove('muscle-card-highlight'), 1400);
}

function selectZone(zoneId) {
  state.zone = zoneId;
  const zone = state.data.zones.find((item) => item.id === zoneId);
  const matches = state.data.muscles
    .map((muscle) => ({ muscle, relation: muscle.pain_zones.primary.includes(zoneId) ? 'primary' : muscle.pain_zones.secondary.includes(zoneId) ? 'secondary' : null }))
    .filter((item) => item.relation)
    .sort((a, b) => a.relation.localeCompare(b.relation));

  document.querySelectorAll('[data-zone]').forEach((button) => {
    const selected = button.dataset.zone === zoneId;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  empty.hidden = true;
  const countLabel = matches.length === 1 ? `1 ${IS_PROFESSIONAL ? 'patrón relacionado' : 'mapa relacionado'}` : `${matches.length} ${IS_PROFESSIONAL ? 'patrones relacionados' : 'mapas relacionados'}`;
  summary.innerHTML = `<strong>${countLabel}</strong><span>No están ordenados por probabilidad.</span><span class="result-actions"><a href="#selector-zona">Cambiar zona ↑</a><a href="#siguiente-paso">Decidir qué hacer ↓</a></span>`;
  results.innerHTML = matches.map(({ muscle, relation }) => card(muscle, relation)).join('');
  document.querySelector('[data-journey-complete]').hidden = false;
  setJourneyStep(2);
  document.querySelector('.results').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}

function renderJourneyOutcome(form) {
  const similarity = form.elements.similarity.value;
  const behaviour = form.elements.behaviour.value;
  const limitation = form.elements.limitation.value;
  const warning = form.elements.warning.value;
  const outcome = document.querySelector('[data-journey-outcome]');
  let tone = 'observe';
  let title = 'Puedes empezar observando la evolución';
  let copy = IS_PROFESSIONAL ? 'Existe concordancia parcial con algún patrón, los síntomas cambian con la actividad y la limitación es pequeña. Ajusta temporalmente los factores agravantes y revalora la evolución.' : 'Algún dibujo se parece a lo que notas, la molestia cambia con la actividad y te limita poco. Reduce temporalmente lo que la empeora, mantén un movimiento cómodo y observa cómo evoluciona.';
  if (warning === 'yes') {
    tone = 'urgent';
    title = 'Solicita atención prioritaria';
    copy = IS_PROFESSIONAL ? 'Una señal de alarma prevalece sobre la concordancia con cualquier patrón muscular. Aplica la recomendación de seguridad o deriva al servicio correspondiente.' : 'Una señal de alarma es más importante que cualquier parecido con un dibujo. Sigue la recomendación de seguridad de esta página o contacta con un servicio sanitario.';
  } else if (limitation === 'severe') {
    tone = 'assessment';
    title = 'Conviene solicitar una valoración';
    copy = IS_PROFESSIONAL ? 'Una limitación importante para la carga o las actividades habituales requiere evaluación individual, aunque exista concordancia con algún patrón.' : 'Si te cuesta mucho apoyar o hacer tus actividades habituales, pide una valoración aunque algún dibujo se parezca a lo que notas.';
  } else if (limitation === 'moderate' || similarity === 'no' || behaviour === 'no') {
    tone = 'assessment';
    title = 'Una valoración puede aclarar mejor el problema';
    copy = IS_PROFESSIONAL ? 'La concordancia es incompleta, el comportamiento no está claro o la limitación es moderada. La exploración individual debe integrar otras estructuras e hipótesis.' : 'El dibujo no encaja del todo, no está claro qué cambia la molestia o te limita bastante. Una valoración personal puede aclarar aspectos que esta guía no puede comprobar.';
  }
  outcome.className = `journey-outcome ${tone}`;
  outcome.innerHTML = `<p class="section-label">Orientación final</p><h4>${title}</h4><p>${copy}</p><div><button type="button" data-revisit-patterns>Volver a comparar</button><a href="#explorador" data-reset-explorer>Volver al mapa corporal</a><a href="../../index.html#contacto">Solicitar valoración →</a></div>`;
  outcome.hidden = false;
  outcome.focus({ preventScroll: true });
  outcome.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
  setJourneyStep(3);
}

function resetExplorer({ focus = true } = {}) {
  state.selectedRegion = null;
  state.selectedSubzone = 'all';
  state.selectedVisualZone = null;
  state.comparison.clear();
  document.querySelector('[data-visual-flow]').hidden = true;
  document.querySelector('[data-region-pathway]').hidden = true;
  document.querySelector('[data-shoulder-detail]').hidden = true;
  document.querySelectorAll('[data-body-region]').forEach((button) => {
    button.classList.remove('selected');
    button.setAttribute('aria-pressed', 'false');
  });
  document.querySelector('[data-body-selection]').textContent = 'Selecciona una región para continuar.';
  document.querySelector('[data-corpus-region]').value = 'all';
  setJourneyStep(1);
  updateVisualUrl();
  if (focus) document.querySelector('.whole-body-selector').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}

function initialise(data, corpus, visualFlow, painPatterns) {
  state.data = data;
  state.corpus = corpus;
  state.visualFlow = visualFlow;
  state.painPatterns = painPatterns;
  applyOverviewLandmarks(visualFlow);
  state.corpusLimit = 12;
  document.querySelector('[data-corpus-search]').value = '';
  document.querySelector('[data-corpus-region]').value = 'all';
  document.querySelector('[data-corpus-type]').value = 'all';
  document.querySelector('[data-red-flags]').innerHTML = data.red_flags.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  const reviewDate = new Date(`${data.review.updated_at}T00:00:00`).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
  document.querySelector('[data-review-meta]').textContent = `Autor: ${data.review.author}. Revisión clínica: ${data.review.reviewer}. Actualizado el ${reviewDate}.`;
  document.querySelector('[data-body-region-list]').innerHTML = bodyRegionGroups.map(([group, ids]) => `<section class="body-region-group"><p>${escapeHtml(group)}</p>${ids.map((id) => `<button type="button" data-body-region="${id}" aria-pressed="false">${escapeHtml(bodyRegionLabelMap.get(id) || id)}</button>`).join('')}</section>`).join('');
  document.querySelectorAll('[data-body-region]').forEach((button) => {
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => selectBodyRegion(button.dataset.bodyRegion));
  });
  const visualFlowRoot = document.querySelector('[data-visual-flow]');
  visualFlowRoot.addEventListener('click', (event) => {
    const regionBack = event.target.closest('[data-back-regions]');
    if (regionBack) {
      resetExplorer();
      return;
    }
    const viewButton = event.target.closest('[data-visual-view]');
    if (viewButton) {
      renderVisualView(viewButton.dataset.visualView);
      return;
    }
    const zoneButton = event.target.closest('[data-visual-zone]');
    if (zoneButton) {
      selectVisualZone(zoneButton.dataset.visualZone);
      return;
    }
    if (event.target.closest('[data-change-visual-zone]')) {
      document.querySelector('[data-visual-map]').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
      return;
    }
    const chapterButton = event.target.closest('[data-open-visual-chapter]');
    if (chapterButton) {
      showChapter(chapterButton.dataset.openVisualChapter, '[data-visual-chapter-detail]', chapterButton);
      setJourneyStep(4);
      updateVisualUrl(chapterButton.dataset.openVisualChapter);
    }
  });
  visualFlowRoot.addEventListener('keydown', (event) => {
    const zone = event.target.closest('g[data-visual-zone]');
    if (!zone || !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    selectVisualZone(zone.dataset.visualZone);
  });
  document.querySelector('[data-zone-list]').innerHTML = data.zones.map((zone) => `<button data-zone="${zone.id}" aria-pressed="false">${escapeHtml(zone.label)}</button>`).join('');
  document.querySelectorAll('[data-zone]').forEach((button) => button.addEventListener('click', () => selectZone(button.dataset.zone)));
  results.addEventListener('click', (event) => {
    const muscleLink = event.target.closest('[data-muscle-link]');
    if (muscleLink) {
      event.preventDefault();
      navigateToMuscle(muscleLink.dataset.muscleLink);
      return;
    }
    const chapterLink = event.target.closest('[data-chapter-link]');
    if (chapterLink) {
      event.preventDefault();
      navigateToChapter(chapterLink.dataset.chapterLink);
    }
  });
  results.addEventListener('toggle', (event) => {
    const opened = event.target.closest('details[open]');
    if (!opened) return;
    opened.closest('.muscle-card')?.querySelectorAll('details[open]').forEach((detail) => {
      if (detail !== opened) detail.open = false;
    });
  }, true);
  summary.addEventListener('click', (event) => {
    if (!event.target.closest('a[href="#siguiente-paso"]')) return;
    setJourneyStep(3);
  });
  document.querySelector('[data-corpus-search]').addEventListener('input', () => { state.corpusLimit = 12; filterCorpus(); });
  document.querySelector('[data-corpus-region]').addEventListener('change', () => { state.corpusLimit = 12; filterCorpus(); });
  document.querySelector('[data-corpus-type]').addEventListener('change', () => { state.corpusLimit = 12; filterCorpus(); });
  document.querySelector('[data-corpus-more]').addEventListener('click', () => { state.corpusLimit += 12; filterCorpus(); });
  document.querySelector('[data-restart-map]').addEventListener('click', () => {
    document.querySelectorAll('[data-zone]').forEach((button) => { button.classList.remove('selected'); button.setAttribute('aria-pressed', 'false'); });
    state.zone = null;
    results.innerHTML = '';
    empty.hidden = false;
    summary.textContent = `Selecciona una zona para ver los ${IS_PROFESSIONAL ? 'patrones' : 'mapas'} relacionados.`;
    document.querySelector('[data-journey-complete]').hidden = true;
    setJourneyStep(1);
    document.querySelector('.atlas-layout').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
  document.querySelector('[data-corpus-grid]').addEventListener('click', (event) => {
    const button = event.target.closest('[data-open-chapter]');
    if (button) showChapter(button.dataset.openChapter, '[data-chapter-detail]', button);
  });
  document.querySelector('[data-region-pathway]').addEventListener('click', (event) => {
    const subzone = event.target.closest('[data-region-subzone]');
    if (subzone) {
      selectSubzone(subzone.dataset.regionSubzone);
      return;
    }
    if (event.target.closest('[data-clear-comparison]')) {
      state.comparison.clear();
      selectSubzone(state.selectedSubzone);
      return;
    }
    if (event.target.closest('[data-revisit-patterns]')) {
      document.querySelector('[data-region-structure-grid]').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
      return;
    }
    const button = event.target.closest('[data-open-region-chapter]');
    if (button) showChapter(button.dataset.openRegionChapter, '[data-region-chapter-detail]', button);
  });
  document.querySelector('[data-region-pathway]').addEventListener('change', (event) => {
    const checkbox = event.target.closest('[data-compare-chapter]');
    if (!checkbox) return;
    if (checkbox.checked && state.comparison.size >= 3) {
      checkbox.checked = false;
      document.querySelector('[data-comparison-status]').textContent = `Puedes comparar un máximo de tres ${IS_PROFESSIONAL ? 'estructuras' : 'músculos'}.`;
      return;
    }
    if (checkbox.checked) state.comparison.add(checkbox.dataset.compareChapter);
    else state.comparison.delete(checkbox.dataset.compareChapter);
    renderComparison();
  });
  document.querySelector('[data-journey-form]').addEventListener('submit', (event) => {
    event.preventDefault();
    renderJourneyOutcome(event.currentTarget);
  });
  document.addEventListener('click', (event) => {
    const reset = event.target.closest('[data-reset-explorer]');
    if (!reset) return;
    event.preventDefault();
    resetExplorer();
  });
  document.querySelectorAll('[data-chapter-detail], [data-region-chapter-detail], [data-visual-chapter-detail]').forEach((detail) => {
    detail.addEventListener('click', (event) => {
      const related = event.target.closest('[data-open-related-chapter]');
      if (related) {
        showChapter(related.dataset.openRelatedChapter, detail.hasAttribute('data-region-chapter-detail') ? '[data-region-chapter-detail]' : '[data-chapter-detail]', related);
        return;
      }
      if (!event.target.closest('[data-close-chapter]')) return;
      detail.hidden = true;
      detail.innerHTML = '';
      if (detail.hasAttribute('data-visual-chapter-detail')) {
        setJourneyStep(state.selectedVisualZone ? 3 : 2);
        updateVisualUrl();
      }
      if (state.lastChapterTrigger?.isConnected) state.lastChapterTrigger.focus();
      else document.querySelector('[data-corpus-search]').focus();
    });
  });
  renderCorpus();
  const requestedParams = new URLSearchParams(window.location.search);
  const requestedRawRegion = requestedParams.get('region');
  const legacyRegionAliases = {
    'cabeza-cuello': 'cabeza', 'hombro-brazo': 'hombro',
    'codo-muneca-mano': 'codo', 'muneca-mano': 'muneca',
    'tronco-suelo-pelvico': 'torax-abdomen', 'cadera-muslo': 'cadera',
    'cadera-muslo-rodilla': 'cadera', 'pierna-tobillo-pie': 'pierna'
  };
  const requestedRegion = legacyRegionAliases[requestedRawRegion] || requestedRawRegion;
  if (requestedRegion && bodyRegions.some(([id]) => id === requestedRegion)) {
    window.requestAnimationFrame(() => {
      selectBodyRegion(requestedRegion);
      const requestedZone = requestedParams.get('zone');
      if (requestedZone && visualRegion(requestedRegion)?.zones.some((zone) => zone.id === requestedZone)) {
        selectVisualZone(requestedZone, { focusResults: false });
        const requestedGuide = requestedParams.get('guide');
        if (requestedGuide && visualZone(requestedZone)?.candidates.includes(requestedGuide)) {
          const trigger = document.querySelector(`[data-open-visual-chapter="${CSS.escape(requestedGuide)}"]`);
          showChapter(requestedGuide, '[data-visual-chapter-detail]', trigger);
          setJourneyStep(4);
          updateVisualUrl(requestedGuide);
        }
      }
    });
    return;
  }
  if (window.location.hash === '#explorador') {
    window.requestAnimationFrame(() => {
      const root = document.documentElement;
      const previousBehavior = root.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      document.querySelector('#explorador').scrollIntoView({ block: 'start' });
      root.style.scrollBehavior = previousBehavior;
    });
  }
}

const fetchJson = (url) => fetch(url).then((response) => {
  if (!response.ok) throw new Error('No se pudo cargar el contenido.');
  return response.json();
});

const loadVisualFlow = () => {
  if (new URL(window.location.href).searchParams.get('draft') === '1') {
    try {
      const draft = JSON.parse(window.localStorage.getItem(CALIBRATION_STORAGE_KEY));
      if (draft?.calibration_schema === CALIBRATION_SCHEMA && draft?.regions?.length) return Promise.resolve(draft);
    } catch (_) {
      // El borrador es opcional; si está dañado se utiliza el archivo publicado.
    }
  }
  return fetchJson(VISUAL_FLOW_URL);
};

const loadPainPatterns = () => fetchJson(PAIN_PATTERNS_URL).catch(() => ({ items: [] }));

Promise.all([fetchJson(DATA_URL), fetchJson(CORPUS_URL), loadVisualFlow(), loadPainPatterns()])
  .then(([data, corpus, visualFlow, painPatterns]) => initialise(data, corpus, visualFlow, painPatterns))
  .catch(() => {
    summary.textContent = 'El piloto no ha podido cargar sus datos. Recarga la página o vuelve más tarde.';
    empty.hidden = true;
  });
