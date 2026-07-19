#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const packDir = path.join(root, 'content/pain-explorer/mapas-musculares-para-dibujar');
const manifestPath = path.join(packDir, 'manifest.json');
const publicDir = path.join(root, 'patients/explora-dolor/assets/pain-patterns');
const dataPath = path.join(root, 'patients/explora-dolor/data/pain-patterns.json');
const cropperPath = path.join(root, 'scripts/crop_pain_pattern_views.js');

const viewCrops = {
  'anatomy-head-neck.png': [
    { id: 'anterior', label: 'Vista anterior', x: 95, y: 275, width: 350, height: 455 },
    { id: 'lateral', label: 'Vista lateral', x: 535, y: 275, width: 350, height: 455 },
    { id: 'posterior', label: 'Vista posterior', x: 1005, y: 275, width: 350, height: 455 }
  ],
  'anatomy-head-upper-body.png': [
    { id: 'anterior', label: 'Vista anterior', x: 30, y: 190, width: 430, height: 820 },
    { id: 'lateral', label: 'Vista lateral', x: 510, y: 240, width: 430, height: 570 },
    { id: 'posterior', label: 'Vista posterior', x: 1000, y: 190, width: 430, height: 820 }
  ],
  'anatomy-shoulder-arm.png': [
    { id: 'anterior', label: 'Vista anterior', x: 95, y: 205, width: 350, height: 760 },
    { id: 'lateral', label: 'Vista lateral', x: 505, y: 205, width: 400, height: 760 },
    { id: 'posterior', label: 'Vista posterior', x: 965, y: 205, width: 390, height: 760 }
  ],
  'anatomy-trunk-pelvis.png': [
    { id: 'anterior', label: 'Vista anterior', x: 35, y: 195, width: 430, height: 735 },
    { id: 'lateral', label: 'Vista lateral', x: 500, y: 195, width: 430, height: 735 },
    { id: 'posterior', label: 'Vista posterior', x: 945, y: 195, width: 455, height: 735 }
  ],
  'anatomy-elbow-forearm-hand.png': [
    { id: 'anterior', label: 'Vista anterior', x: 170, y: 245, width: 300, height: 735 },
    { id: 'lateral', label: 'Vista lateral', x: 560, y: 245, width: 330, height: 735 },
    { id: 'posterior', label: 'Vista posterior', x: 965, y: 245, width: 330, height: 735 }
  ],
  'anatomy-hip-thigh-knee.png': [
    { id: 'anterior', label: 'Vista anterior', x: 45, y: 150, width: 410, height: 800 },
    { id: 'lateral', label: 'Vista lateral', x: 515, y: 150, width: 365, height: 800 },
    { id: 'posterior', label: 'Vista posterior', x: 945, y: 150, width: 425, height: 800 }
  ],
  'anatomy-leg-ankle-foot.png': [
    { id: 'anterior', label: 'Vista anterior', x: 45, y: 225, width: 410, height: 665 },
    { id: 'lateral', label: 'Vista lateral', x: 480, y: 225, width: 455, height: 665 },
    { id: 'posterior', label: 'Vista posterior', x: 945, y: 225, width: 430, height: 665 }
  ],
  'anatomy-leg-medial.png': [
    { id: 'medial', label: 'Vista medial', x: 420, y: 140, width: 560, height: 855 }
  ],
  'anatomy-foot-plantar.png': [
    { id: 'plantar', label: 'Vista plantar', x: 500, y: 150, width: 480, height: 850 }
  ]
};

const mappings = {
  'MM-001': ['Occipitofrontal · vientre frontal', 'occipitofrontal'],
  'MM-002': ['Occipitofrontal · vientre occipital', 'occipitofrontal'],
  'MM-003': ['Orbicular de los ojos', 'musculos-faciales'],
  'MM-004': ['Cigomáticos', 'musculos-faciales'],
  'MM-005': ['Buccinador', 'musculos-faciales'],
  'MM-006': ['Platisma', 'musculos-faciales'],
  'MM-007': ['Temporal', 'temporal'],
  'MM-008': ['Masetero', 'esternocleidomastoideo-y-masetero'],
  'MM-009': ['Pterigoideo lateral', 'pterigoideo-lateral'],
  'MM-010': ['Pterigoideo medial', 'pterigoideo-medial'],
  'MM-011': ['Digástrico', 'digastrico'],
  'MM-012': ['Esternocleidomastoideo · división esternal', 'esternocleidomastoideo-y-masetero'],
  'MM-013': ['Esplenio de la cabeza', 'esplenio-de-cabeza-y-cuello'],
  'MM-014': ['Esplenio del cuello', 'esplenio-de-cabeza-y-cuello'],
  'MM-015': ['Semiespinoso de la cabeza', 'musculos-cervicales-posteriores'],
  'MM-016': ['Suboccipitales', 'suboccipitales'],
  'MM-017': ['Escalenos', 'escalenos'],
  'MM-018': ['Multífidos cervicales', 'musculos-cervicales-posteriores'],
  'MM-019': ['Trapecio', 'trapecio'],
  'MM-020': ['Elevador de la escápula', 'elevador-de-la-escapula'],
  'MM-021': ['Romboides', 'romboides'],
  'MM-022': ['Pectoral mayor', 'pectoral-mayor-y-subclavio'],
  'MM-023': ['Pectoral menor', 'pectoral-menor'],
  'MM-024': ['Subclavio', 'pectoral-mayor-y-subclavio'],
  'MM-025': ['Esternal', 'esternal'],
  'MM-026': ['Intercostales', 'intercostales-y-diafragma'],
  'MM-027': ['Serrato anterior', 'serrato-anterior'],
  'MM-028': ['Serrato posterior superior', 'serrato-posterior-superior-e-inferior'],
  'MM-029': ['Serrato posterior inferior', 'serrato-posterior-superior-e-inferior'],
  'MM-030': ['Dorsal ancho', 'dorsal-ancho-y-redondo-mayor'],
  'MM-031': ['Iliocostal torácico', 'paraespinales-toracolumbares'],
  'MM-032': ['Iliocostal lumbar', 'paraespinales-toracolumbares'],
  'MM-033': ['Longísimo torácico', 'paraespinales-toracolumbares'],
  'MM-034': ['Multífidos toracolumbares', 'paraespinales-toracolumbares'],
  'MM-035': ['Recto abdominal', 'musculos-abdominales'],
  'MM-036': ['Oblicuo externo del abdomen', 'musculos-abdominales'],
  'MM-037': ['Oblicuo interno del abdomen', 'musculos-abdominales'],
  'MM-038': ['Piramidal del abdomen', 'musculos-abdominales'],
  'MM-039': ['Cuadrado lumbar', 'cuadrado-lumbar'],
  'MM-040': ['Iliopsoas', 'psoas-mayor-psoas-menor-e-iliaco'],
  'MM-041': ['Glúteo mayor', 'gluteo-mayor'],
  'MM-042': ['Glúteo medio', 'gluteo-medio'],
  'MM-043': ['Glúteo menor', 'gluteo-menor-y-tensor-de-la-fascia-lata'],
  'MM-044': ['Piriforme', 'piriforme-obturadores-gemelos-y-cuadrado-femoral'],
  'MM-045': ['Obturador interno', 'piriforme-obturadores-gemelos-y-cuadrado-femoral'],
  'MM-046': ['Suelo pélvico', 'suelo-pelvico'],
  'MM-047': ['Deltoides', 'deltoides'],
  'MM-048': ['Supraespinoso', 'supraespinoso'],
  'MM-049': ['Infraespinoso', 'infraespinoso'],
  'MM-050': ['Subescapular', 'subescapular'],
  'MM-051': ['Redondo menor', 'redondo-menor'],
  'MM-052': ['Redondo mayor', 'dorsal-ancho-y-redondo-mayor'],
  'MM-053': ['Bíceps braquial', 'biceps-braquial'],
  'MM-054': ['Braquial', 'braquial'],
  'MM-055': ['Coracobraquial', 'coracobraquial'],
  'MM-056': ['Tríceps braquial', 'triceps-braquial-y-anconeo'],
  'MM-057': ['Ancóneo', 'triceps-braquial-y-anconeo'],
  'MM-058': ['Braquiorradial', 'extensores-de-la-muneca-y-braquiorradial'],
  'MM-059': ['Supinador', 'supinador'],
  'MM-060': ['Pronador redondo', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-061': ['Extensor radial largo del carpo', 'extensores-de-la-muneca-y-braquiorradial'],
  'MM-062': ['Extensor radial corto del carpo', 'extensores-de-la-muneca-y-braquiorradial'],
  'MM-063': ['Extensor cubital del carpo', 'extensores-de-la-muneca-y-braquiorradial'],
  'MM-064': ['Extensor de los dedos', 'extensor-de-los-dedos-de-la-mano-y-extensor-del-indice'],
  'MM-065': ['Extensor del índice', 'extensor-de-los-dedos-de-la-mano-y-extensor-del-indice'],
  'MM-066': ['Palmar largo', 'palmar-largo'],
  'MM-067': ['Flexor radial del carpo', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-068': ['Flexor cubital del carpo', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-069': ['Flexor superficial de los dedos', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-070': ['Flexor profundo de los dedos', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-071': ['Flexor largo del pulgar', 'flexores-de-la-muneca-y-de-los-dedos-en-el-antebrazo'],
  'MM-072': ['Oponente del pulgar', 'aductor-del-pulgar-y-oponente-del-pulgar'],
  'MM-073': ['Aductor del pulgar', 'aductor-del-pulgar-y-oponente-del-pulgar'],
  'MM-074': ['Primer interóseo dorsal de la mano', 'interoseos-lumbricales-y-separador-del-menique-de-la-mano'],
  'MM-075': ['Abductor del meñique de la mano', 'interoseos-lumbricales-y-separador-del-menique-de-la-mano'],
  'MM-076': ['Tensor de la fascia lata', 'gluteo-menor-y-tensor-de-la-fascia-lata'],
  'MM-077': ['Recto femoral', 'cuadriceps-y-sartorio'],
  'MM-078': ['Vasto lateral', 'cuadriceps-y-sartorio'],
  'MM-079': ['Vasto medial', 'cuadriceps-y-sartorio'],
  'MM-080': ['Vasto intermedio', 'cuadriceps-y-sartorio'],
  'MM-081': ['Sartorio', 'cuadriceps-y-sartorio'],
  'MM-082': ['Aductor largo', 'aductor-mayor-aductor-largo-aductor-corto-pectineo-y-gracil'],
  'MM-083': ['Aductor corto', 'aductor-mayor-aductor-largo-aductor-corto-pectineo-y-gracil'],
  'MM-084': ['Aductor mayor', 'aductor-mayor-aductor-largo-aductor-corto-pectineo-y-gracil'],
  'MM-085': ['Pectíneo', 'aductor-mayor-aductor-largo-aductor-corto-pectineo-y-gracil'],
  'MM-086': ['Grácil', 'aductor-mayor-aductor-largo-aductor-corto-pectineo-y-gracil'],
  'MM-087': ['Bíceps femoral', 'isquiotibiales'],
  'MM-088': ['Semitendinoso', 'isquiotibiales'],
  'MM-089': ['Semimembranoso', 'isquiotibiales'],
  'MM-090': ['Gastrocnemio', 'gemelos'],
  'MM-091': ['Sóleo', 'soleo-y-plantar'],
  'MM-092': ['Plantar', 'soleo-y-plantar'],
  'MM-093': ['Poplíteo', 'popliteo'],
  'MM-094': ['Tibial anterior', 'tibial-anterior'],
  'MM-095': ['Tibial posterior', 'tibial-posterior'],
  'MM-096': ['Fibular largo', 'fibulares-largo-corto-y-tercero'],
  'MM-097': ['Fibular corto', 'fibulares-largo-corto-y-tercero'],
  'MM-098': ['Fibular tercero', 'fibulares-largo-corto-y-tercero'],
  'MM-099': ['Extensor largo de los dedos del pie', 'extensores-largos-del-pie'],
  'MM-100': ['Extensor largo del dedo gordo', 'extensores-largos-del-pie'],
  'MM-101': ['Flexor largo de los dedos del pie', 'flexores-largos-del-pie'],
  'MM-102': ['Flexor largo del dedo gordo', 'flexores-largos-del-pie'],
  'MM-103': ['Extensor corto de los dedos del pie', 'musculatura-intrinseca-del-pie'],
  'MM-104': ['Extensor corto del dedo gordo', 'musculatura-intrinseca-del-pie'],
  'MM-105': ['Flexor corto del dedo gordo', 'musculatura-intrinseca-del-pie'],
  'MM-106': ['Abductor del dedo gordo', 'musculatura-intrinseca-del-pie'],
  'MM-107': ['Cuadrado plantar', 'musculatura-intrinseca-del-pie'],
  'MM-108': ['Abductor del meñique del pie', 'musculatura-intrinseca-del-pie'],
  'MM-109': ['Interóseos del pie', 'musculatura-intrinseca-del-pie']
};

const slugify = (value) => value
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-|-$/g, '');

const sha256 = (filePath) => crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const chapters = new Set(JSON.parse(fs.readFileSync(path.join(root, 'patients/explora-dolor/data/guides.json'), 'utf8')).chapters.map((chapter) => chapter.id));
const selectedBlocks = new Set(['01_cabeza-y-cara', '02_cuello-y-cintura-escapular', '03_torax-abdomen-espalda-y-pelvis', '04_hombro-y-brazo', '05_antebrazo-muneca-y-mano', '06_cadera-y-muslo', '07_pierna-tobillo-y-pie']);
const selected = manifest.items.filter((item) => selectedBlocks.has(item.block));
const items = [];
const skipped = [];

fs.mkdirSync(publicDir, { recursive: true });
for (const file of fs.readdirSync(publicDir).filter((name) => name.endsWith('.png'))) {
  fs.unlinkSync(path.join(publicDir, file));
}

for (const item of selected) {
  const mapping = mappings[item.canonical_id || item.id];
  if (!mapping) throw new Error(`Falta el vínculo editorial de ${item.id}.`);
  if (!chapters.has(mapping[1])) throw new Error(`La guía ${mapping[1]} vinculada a ${item.id} no existe.`);
  if (item.status !== 'modificado') {
    skipped.push({ id: item.id, reason: 'plantilla_sin_dibujo' });
    continue;
  }

  const source = path.join(root, item.drawing_file);
  const dimensions = execFileSync('/usr/bin/sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', '-g', 'format', source], { encoding: 'utf8' });
  const width = Number(dimensions.match(/pixelWidth: (\d+)/)?.[1]);
  const height = Number(dimensions.match(/pixelHeight: (\d+)/)?.[1]);
  const format = dimensions.match(/format: (\w+)/)?.[1];
  if (width !== 1448 || height !== 1086 || format !== 'png') {
    throw new Error(`${item.id} debe ser PNG de 1448 × 1086; se recibió ${width} × ${height} (${format}).`);
  }

  const [name, chapterId] = mapping;
  const fileName = `${item.id.toLowerCase()}-${slugify(name)}.png`;
  const cropKey = path.basename(item.source_template);
  const crops = viewCrops[cropKey];
  if (!crops) throw new Error(`No hay recortes configurados para ${cropKey} (${item.id}).`);
  items.push({
    id: item.id,
    canonical_id: item.canonical_id || item.id,
    name,
    chapter_id: chapterId,
    variant: item.variant,
    image: '',
    alt: `Mapa orientativo del patrón de dolor referido asociado a ${name.toLowerCase()}.`,
    width,
    height,
    sha256: '',
    _drawing: source,
    _template: path.join(root, item.source_template),
    _outputStem: path.basename(fileName, '.png'),
    _crops: crops
  });
}

const cropConfigPath = path.join(os.tmpdir(), `fisiologico-pain-crops-${process.pid}.json`);
const cropReportPath = path.join(os.tmpdir(), `fisiologico-pain-crops-${process.pid}-report.json`);
fs.writeFileSync(cropConfigPath, JSON.stringify({
  outputDirectory: publicDir,
  reportPath: cropReportPath,
  items: items.map((item) => ({
    id: item.id,
    drawing: item._drawing,
    template: item._template,
    outputStem: item._outputStem,
    views: item._crops
  }))
}), 'utf8');
execFileSync(process.execPath, [cropperPath, cropConfigPath], { stdio: 'inherit' });
const cropReport = JSON.parse(fs.readFileSync(cropReportPath, 'utf8'));
const cropsById = new Map(cropReport.items.map((item) => [item.id, item.views]));

for (const item of items) {
  const generated = cropsById.get(item.id) || [];
  if (!generated.length) throw new Error(`${item.id} no contiene ninguna vista dibujada detectable.`);
  item.views = generated.map((view) => {
    const generatedPath = path.join(publicDir, view.file);
    const hash = sha256(generatedPath);
    return {
      id: view.id,
      label: view.label,
      image: `./assets/pain-patterns/${view.file}?v=${hash.slice(0, 10)}`,
      alt: `${item.alt.replace(/\.$/, '')}, ${view.label.toLowerCase()}.`,
      width: view.width,
      height: view.height,
      sha256: hash
    };
  });
  const primary = item.views[0];
  item.image = primary.image;
  item.alt = primary.alt;
  item.width = primary.width;
  item.height = primary.height;
  item.sha256 = primary.sha256;
  delete item._drawing;
  delete item._template;
  delete item._outputStem;
  delete item._crops;
}

fs.unlinkSync(cropConfigPath);
fs.unlinkSync(cropReportPath);

items.sort((a, b) => a.id.localeCompare(b.id, 'es'));

const output = {
  version: '1.7.0',
  updated_at: new Date().toISOString().slice(0, 10),
  purpose: 'Mapas visuales orientativos para comparar distribuciones de dolor; no identifican por sí solos la estructura responsable.',
  author: 'FisioLógico',
  reviewer: 'Francisco José Extremera García · Fisioterapeuta colegiado ICPFA 4288',
  count: items.length,
  items,
  skipped
};

fs.writeFileSync(dataPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
console.log(`Mapas ingeridos: ${items.length}`);
console.log(`Plantillas sin dibujo omitidas: ${skipped.map((item) => item.id).join(', ') || 'ninguna'}`);
console.log(`Catálogo: ${path.relative(root, dataPath)}`);
