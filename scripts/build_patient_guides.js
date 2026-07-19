#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const dataDir = path.join(root, 'patients', 'explora-dolor', 'data');
const patientPath = path.join(dataDir, 'guides.json');
const professionalPath = path.join(dataDir, 'guides-professional.json');
const visualFlowPath = path.join(dataDir, 'visual-flow.json');

if (!fs.existsSync(professionalPath)) {
  fs.copyFileSync(patientPath, professionalPath);
}

const source = JSON.parse(fs.readFileSync(professionalPath, 'utf8'));
const visualFlow = JSON.parse(fs.readFileSync(visualFlowPath, 'utf8'));

const sourceLike = /\b(Travell|Simons|participantes?|estudios?|investigaci[oó]n|ensayos?|literatura|publicad[oa]s?|serie de casos|inyecci[oó]n|soluci[oó]n salina|por ciento)\b|%/i;
const technicalDifferential = /\b(tendinopat[ií]a|radiculopat[ií]a|neuropat[ií]a|bursitis|artrosis|síndrome|diagn[oó]stico diferencial|electromiograf|resonancia|ecograf[ií]a)\b/i;

const replacements = [
  [/dolor referido/gi, 'dolor que aparece en otra zona'],
  [/patr[oó]n de dolor/gi, 'forma en que aparece el dolor'],
  [/patr[oó]n referido/gi, 'recorrido del dolor'],
  [/patr[oó]n/gi, 'mapa'],
  [/puntos? gatillo miofasciales?/gi, 'zonas musculares sensibles'],
  [/puntos? gatillo/gi, 'zonas musculares sensibles'],
  [/puntos? sensibles? del m[uú]sculo/gi, 'zonas sensibles del músculo'],
  [/dolor musculoesquel[eé]tico/gi, 'dolor de músculos y articulaciones'],
  [/articulaci[oó]n radiocubital distal/gi, 'zona de la muñeca'],
  [/epic[oó]ndilo lateral/gi, 'parte externa del codo'],
  [/epic[oó]ndilo medial/gi, 'parte interna del codo'],
  [/regi[oó]n olecraniana/gi, 'parte posterior del codo'],
  [/ol[eé]cranon/gi, 'parte posterior del codo'],
  [/tabaquera anat[oó]mica/gi, 'base del pulgar'],
  [/dorso de la muñeca/gi, 'parte de atrás de la muñeca'],
  [/dorso de la mano/gi, 'parte de atrás de la mano'],
  [/dorso de los dedos/gi, 'parte de atrás de los dedos'],
  [/cara dorsal/gi, 'parte posterior'],
  [/cara volar/gi, 'parte de la palma'],
  [/regi[oó]n volar/gi, 'parte de la palma'],
  [/cara palmar/gi, 'parte de la palma'],
  [/regi[oó]n palmar/gi, 'palma'],
  [/posterolateral/gi, 'posterior y externa'],
  [/dorsolateral/gi, 'posterior y externa'],
  [/anterolateral/gi, 'delantera y externa'],
  [/anteromedial/gi, 'delantera e interna'],
  [/posteromedial/gi, 'posterior e interna'],
  [/ipsilateral/gi, 'del mismo lado'],
  [/contralateral/gi, 'del lado contrario'],
  [/regi[oó]n subclavicular/gi, 'zona bajo la clavícula'],
  [/mastoides/gi, 'zona detrás de la oreja'],
  [/articulaci[oó]n glenohumeral/gi, 'hombro'],
  [/regi[oó]n escapular/gi, 'zona del omóplato'],
  [/borde escapular/gi, 'borde del omóplato'],
  [/esc[aá]pula/gi, 'omóplato'],
  [/regi[oó]n cervical/gi, 'cuello'],
  [/columna cervical/gi, 'cuello'],
  [/regi[oó]n lumbar/gi, 'parte baja de la espalda'],
  [/columna lumbar/gi, 'parte baja de la espalda'],
  [/regi[oó]n tor[aá]cica/gi, 'parte media de la espalda'],
  [/columna tor[aá]cica/gi, 'parte media de la espalda'],
  [/regi[oó]n gl[uú]tea/gi, 'nalga'],
  [/regi[oó]n cubital/gi, 'lado del meñique'],
  [/regi[oó]n ulnar/gi, 'lado del meñique'],
  [/regi[oó]n radial/gi, 'lado del pulgar'],
  [/borde cubital/gi, 'lado del meñique'],
  [/borde radial/gi, 'lado del pulgar'],
  [/cefalea/gi, 'dolor de cabeza'],
  [/rango de movimiento/gi, 'movimiento'],
  [/prensi[oó]n/gi, 'agarre'],
  [/bipedestaci[oó]n/gi, 'estar de pie'],
  [/sedestaci[oó]n/gi, 'estar sentado'],
  [/deambulaci[oó]n/gi, 'caminar'],
  [/perpetuar/gi, 'hacer que dure'],
  [/perpetuaci[oó]n/gi, 'mantenimiento'],
  [/irradia(?:do|ción|r)?/gi, 'se extiende'],
  [/proyecta(?:do|r|n)?/gi, 'se extiende'],
  [/refiere(?:n|d|r)?/gi, 'puede sentirse'],
  [/sintomatolog[ií]a/gi, 'síntomas'],
  [/cl[ií]nica/gi, 'lo que notas'],
  [/distribuci[oó]n/gi, 'recorrido'],
  [/activaci[oó]n/gi, 'aparición'],
  [/hipersensibilidad/gi, 'sensibilidad'],
  [/parestesias?/gi, 'hormigueo'],
  [/debilidad funcional/gi, 'dificultad para usar la zona'],
  [/proximal(?:mente)?/gi, 'más cerca del cuerpo'],
  [/distal(?:mente)?/gi, 'más lejos del cuerpo'],
  [/responsable(?:s)? de/gi, 'relacionado con'],
];

function cleanText(value) {
  let text = String(value || '')
    .replace(/^[-–—•]\s*/, '')
    .replace(/\s+/g, ' ')
    .trim();

  replacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });

  text = text
    .replace(/\bdel del\b/gi, 'del')
    .replace(/\bde el\b/gi, 'del')
    .replace(/\bla el\b/gi, 'el')
    .replace(/\bse se\b/gi, 'se')
    .replace(/\bpuede sentirse(?:n)? dolor\b/gi, 'el dolor puede sentirse')
    .replace(/\bpuede sentirse(?:n)?\b/gi, 'puede sentirse')
    .replace(/\bpuede estar relacionado con\b/gi, 'puede guardar relación con')
    .replace(/\bdebe(?:n)?\b/gi, 'conviene')
    .replace(/\s+([,.;:])/g, '$1')
    .trim();

  if (text && !/[.!?]$/.test(text)) text += '.';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function usefulLine(value, { allowDifferential = false } = {}) {
  const original = String(value || '').trim();
  if (!original || sourceLike.test(original)) return '';
  if (!allowDifferential && technicalDifferential.test(original)) return '';
  return cleanText(original);
}

function pickLines(values, limit, options = {}) {
  const seen = new Set();
  const result = [];
  for (const value of Array.isArray(values) ? values : []) {
    const cleaned = usefulLine(value, options);
    if (!cleaned) continue;
    const key = cleaned.toLocaleLowerCase('es').replace(/[^a-záéíóúüñ0-9]/g, '');
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(cleaned);
    if (result.length >= limit) break;
  }
  return result;
}

const allZones = visualFlow.regions.flatMap((region) =>
  (region.zones || []).map((zone) => ({ ...zone, region_label: region.label })),
);

const specialZoneNames = {
  'cabeza-superior': 'la parte superior de la cabeza',
  'region-frontal': 'la frente',
  'region-temporal': 'la sien',
  'region-ocular-ceja': 'alrededor del ojo o la ceja',
  'region-auricular-atm': 'alrededor del oído o la articulación de la mandíbula',
  'region-mejilla-mandibula': 'la mejilla o la mandíbula',
  'region-dental': 'los dientes o la mandíbula',
  'region-occipital': 'la parte posterior de la cabeza',
  'garganta-cuello-anterior': 'la parte delantera de la garganta o el cuello',
  'cuello-posterior': 'la parte posterior del cuello',
  'codo-antecubital': 'la parte delantera del codo',
  'codo-olecraniana': 'la parte posterior del codo',
  'epicondilo-medial': 'la parte interna del codo',
  'epicondilo-lateral': 'la parte externa del codo',
  'muneca-dorsal': 'la parte de atrás de la muñeca',
  'mano-dorsal': 'la parte de atrás de la mano',
  'muneca-palmar': 'la parte de la palma junto a la muñeca',
  'mano-palmar': 'la palma de la mano',
  'base-pulgar-mano-radial': 'la base del pulgar',
  'dedos-dorsales': 'la parte de atrás de los dedos',
  'dedos-palmares': 'la parte de la palma de los dedos',
  'torax-pecho-anterior': 'la parte delantera del pecho',
  'torax-lateral': 'el lateral del pecho',
  'toracica-superior-posterior': 'la parte alta de la espalda',
  'toracica-media-posterior': 'la parte media de la espalda',
  'toracica-posterior-general': 'la espalda',
  'region-iliolumbar-iliosacra': 'un lado de la parte baja de la espalda, junto a la pelvis',
  'region-glutea-nalga': 'la nalga',
  'talon': 'el talón',
  'plantar-mediopie': 'la parte media de la planta del pie',
  'plantar-cabezas-metatarsales': 'la almohadilla de la planta, detrás de los dedos',
  'dorsal-antepie': 'la parte superior del pie',
  'plantar-dedo-gordo': 'la parte de abajo del dedo gordo',
  'dorsal-dedo-gordo': 'la parte de arriba del dedo gordo',
  'plantar-dedos-menores': 'la parte de abajo de los dedos menores',
  'dorsal-dedos-menores': 'la parte de arriba de los dedos menores',
};

function zoneName(zone) {
  if (specialZoneNames[zone.id]) return specialZoneNames[zone.id];
  let label = zone.label.toLocaleLowerCase('es');
  label = label
    .replace(/^región anteromedial de la /, 'la parte delantera e interna de la ')
    .replace(/^región anterior de la /, 'la parte delantera de la ')
    .replace(/^región anterior del /, 'la parte delantera del ')
    .replace(/^región posterior de la /, 'la parte posterior de la ')
    .replace(/^región posterior del /, 'la parte posterior del ')
    .replace(/^región lateral de la /, 'la parte externa de la ')
    .replace(/^región lateral del /, 'la parte externa del ')
    .replace(/^región medial de la /, 'la parte interna de la ')
    .replace(/^región medial del /, 'la parte interna del ')
    .replace(/^región dorsal de la /, 'la parte de atrás de la ')
    .replace(/^región dorsal del /, 'la parte de arriba del ')
    .replace(/^región volar o anterior del /, 'la parte delantera del ')
    .replace(/^región volar o palmar de la /, 'la parte de la palma de la ')
    .replace(/^región volar o palmar de los /, 'la parte de la palma de los ')
    .replace(/^región radial del /, 'el lado del pulgar del ')
    .replace(/^región cubital o ulnar del /, 'el lado del meñique del ')
    .replace(/^región del epicóndilo medial$/, 'la parte interna del codo')
    .replace(/^región del epicóndilo lateral$/, 'la parte externa del codo')
    .replace(/^región plantar de la /, 'la planta de la ')
    .replace(/^región plantar del /, 'la planta del ')
    .replace(/^región glútea o nalga$/, 'la nalga')
    .replace(/^región sacra$/, 'la zona central entre la parte baja de la espalda y las nalgas')
    .replace(/^región lumbar$/, 'la parte baja de la espalda')
    .replace(/^región abdominal inferior$/, 'la parte baja del abdomen')
    .replace(/^región abdominal$/, 'el abdomen')
    .replace(/^región pélvica$/, 'la pelvis')
    .replace(/^región /, 'la zona ')
    .replace(/ o [a-záéíóúüñ]+$/, '');
  return label;
}

function relatedZones(chapterId) {
  return allZones
    .filter((zone) => (zone.candidates || []).includes(chapterId))
    .sort((a, b) => (a.catalog_number || 999) - (b.catalog_number || 999));
}

const profiles = {
  'cabeza-cuello': {
    notice: [
      'La molestia puede sentirse como presión, tirantez o dolor y puede cambiar al mover el cuello o la mandíbula.',
      'El lugar donde duele no siempre coincide con el lugar donde está el músculo.',
    ],
    influence: [
      'Mantener la cabeza en la misma posición durante mucho tiempo.',
      'Apretar los dientes o hacer un esfuerzo repetido con la mandíbula.',
      'Dormir poco, acumular tensión o aumentar la actividad de forma brusca.',
    ],
    actions: [
      'Cambia de postura con frecuencia y haz pausas breves.',
      'Prueba movimientos suaves de cuello y mandíbula sin forzar.',
      'Evita apretar los dientes de forma consciente cuando no estés comiendo.',
    ],
    urgent: 'Busca atención urgente ante un dolor de cabeza repentino y muy intenso, dificultad para hablar, ver o mover una parte del cuerpo, desmayo o un golpe importante.',
  },
  'hombro-brazo': {
    notice: [
      'Puede molestar al elevar el brazo, alcanzar un objeto, cargar peso o permanecer mucho tiempo en la misma postura.',
      'El dolor puede aparecer en el hombro o sentirse también en el brazo, el pecho o la espalda.',
    ],
    influence: [
      'Repetir gestos con el brazo elevado o lejos del cuerpo.',
      'Aumentar de golpe el peso, el entrenamiento o el trabajo manual.',
      'Mantener durante mucho tiempo una postura que aumenta la molestia.',
    ],
    actions: [
      'Reduce temporalmente los gestos que aumentan claramente el dolor.',
      'Mantén movimientos suaves del hombro dentro de una zona cómoda.',
      'Acerca las cargas al cuerpo y reparte las tareas con pausas.',
    ],
    urgent: 'Busca atención urgente si aparece presión fuerte en el pecho, dificultad para respirar, una pérdida repentina de fuerza o sensibilidad, o un golpe importante.',
  },
  'codo-muneca-mano': {
    notice: [
      'Puede molestar al agarrar, girar, escribir, usar herramientas o repetir muchas veces el mismo gesto.',
      'El dolor puede sentirse en el codo, el antebrazo, la muñeca, la mano o los dedos.',
    ],
    influence: [
      'Repetir durante mucho tiempo movimientos de agarre, giro o teclado.',
      'Usar más fuerza de la necesaria o trabajar sin pausas.',
      'Mantener la muñeca o el codo en una posición incómoda.',
    ],
    actions: [
      'Alterna las tareas repetitivas con pausas breves.',
      'Reduce la fuerza de agarre siempre que sea posible.',
      'Mantén movimientos cómodos de codo, muñeca y mano.',
    ],
    urgent: 'Busca atención urgente si pierdes fuerza o sensibilidad de forma repentina, la mano cambia claramente de color o temperatura, o existe una deformidad tras un golpe.',
  },
  'tronco-suelo-pelvico': {
    notice: [
      'Puede cambiar al respirar, girar, incorporarte, cargar peso o mantener una postura.',
      'La molestia puede sentirse en el pecho, el abdomen, la espalda, la pelvis o la nalga.',
    ],
    influence: [
      'Permanecer mucho tiempo sentado, de pie o en la misma posición.',
      'Aumentar de golpe las cargas, los giros o el esfuerzo físico.',
      'Evitar todo movimiento por miedo al dolor durante varios días.',
    ],
    actions: [
      'Cambia de postura con frecuencia.',
      'Mantén una actividad suave si la toleras.',
      'Evita forzar los movimientos que reproducen claramente el dolor.',
    ],
    urgent: 'Busca atención urgente si aparece dolor fuerte en el pecho, dificultad para respirar, debilidad repentina en las piernas o cambios recientes al controlar la orina o las heces.',
  },
  'cadera-muslo-rodilla': {
    notice: [
      'Puede molestar al caminar, subir escaleras, levantarte, sentarte o apoyar sobre un lado.',
      'El dolor puede sentirse en la cadera, la ingle, la nalga, el muslo o la rodilla.',
    ],
    influence: [
      'Aumentar de golpe la distancia, el peso o la intensidad de la actividad.',
      'Permanecer mucho tiempo sentado o de pie sin cambiar de posición.',
      'Repetir el gesto que aumenta el dolor sin descanso suficiente.',
    ],
    actions: [
      'Ajusta temporalmente la carga y alterna posiciones.',
      'Conserva un movimiento cómodo sin intentar superar el dolor.',
      'Vuelve a aumentar la actividad de forma gradual.',
    ],
    urgent: 'Busca atención urgente si no puedes apoyar tras un golpe, aparece una deformidad, la pierna pierde fuerza o sensibilidad de repente, o se hincha y cambia de color rápidamente.',
  },
  'pierna-tobillo-pie': {
    notice: [
      'Puede molestar al caminar, correr, apoyar el pie, ponerte de puntillas o usar cierto calzado.',
      'El dolor puede sentirse en la pierna, el tobillo, el talón, la planta o los dedos.',
    ],
    influence: [
      'Aumentar de golpe el tiempo de pie, la distancia o la intensidad del ejercicio.',
      'Usar un calzado que comprime o no se adapta bien al pie.',
      'Repetir la actividad que aumenta el dolor sin recuperación suficiente.',
    ],
    actions: [
      'Reduce temporalmente la actividad que aumenta los síntomas.',
      'Revisa el calzado y evita que comprima la zona dolorida.',
      'Mantén movimiento cómodo si puedes apoyar con seguridad.',
    ],
    urgent: 'Busca atención urgente si no puedes apoyar tras un golpe, el pie cambia claramente de color o temperatura, o aparece hinchazón rápida con dolor intenso.',
  },
};

function patientContent(chapter) {
  const content = chapter.patient_content || {};
  const profile = profiles[chapter.region] || profiles['tronco-suelo-pelvico'];
  const zones = relatedZones(chapter.id);
  const where = [...new Set(zones.map((zone) => `Puede sentirse en ${zoneName(zone)}.`))].slice(0, 6);
  const firstStep = String(content.first_steps || '').trim()
    || 'Observa dónde aparece la molestia, qué la empeora y qué movimientos puedes hacer sin forzar.';

  return {
    intro: `Compara los mapas de ${chapter.title.toLocaleLowerCase('es')} con lo que sientes. Las zonas coloreadas muestran dónde puede aparecer la molestia, aunque el músculo esté en otro lugar.`,
    where_it_may_be_felt: where.length ? where : ['Puede sentirse cerca del músculo o extenderse hacia una zona próxima.'],
    what_you_may_notice: profile.notice,
    what_may_influence_it: profile.influence,
    corrective_actions: profile.actions,
    first_steps: firstStep,
    other_explanations: ['El dolor de una misma zona puede tener distintos orígenes. Una coincidencia con el dibujo no demuestra cuál es la causa.'],
    when_to_consult: [
      'Pide una valoración si el dolor aumenta, no mejora o te impide hacer tus actividades habituales.',
      profile.urgent,
    ],
  };
}

const patient = {
  version: '3.0.0-patient',
  source_label: 'Guías educativas de FisioLógico',
  generated_on: new Date().toISOString().slice(0, 10),
  status: 'patient_plain_language',
  chapter_count: source.chapters.length,
  chapters: source.chapters.map((chapter) => ({
    id: chapter.id,
    title: chapter.title,
    chapter_type: chapter.chapter_type,
    region: chapter.region,
    patient_content: patientContent(chapter),
    editorial_status: 'Lenguaje adaptado para pacientes; contenido educativo y no diagnóstico.',
  })),
};

fs.writeFileSync(patientPath, `${JSON.stringify(patient, null, 2)}\n`, 'utf8');
console.log(`Guías para pacientes generadas: ${patient.chapters.length}`);
console.log(`Fuente profesional conservada: ${path.relative(root, professionalPath)}`);
