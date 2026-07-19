#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = path.resolve(__dirname, '..');
const inventoryPath = path.join(root, 'patients/explora-dolor/data/inventario-mapas-musculares.md');
const assetsDir = path.join(root, 'patients/explora-dolor/assets');
const packDir = path.join(root, 'content/pain-explorer/mapas-musculares-para-dibujar');
const manifestPath = path.join(packDir, 'manifest.json');

const blockRanges = [
  { start: 1, end: 11, dir: '01_cabeza-y-cara' },
  { start: 12, end: 21, dir: '02_cuello-y-cintura-escapular' },
  { start: 22, end: 46, dir: '03_torax-abdomen-espalda-y-pelvis' },
  { start: 47, end: 57, dir: '04_hombro-y-brazo' },
  { start: 58, end: 75, dir: '05_antebrazo-muneca-y-mano' },
  { start: 76, end: 89, dir: '06_cadera-y-muslo' },
  { start: 90, end: 109, dir: '07_pierna-tobillo-y-pie' }
];

const explicitTemplates = new Map([
  [20, 'anatomy-shoulder-arm.png'],
  [21, 'anatomy-shoulder-arm.png'],
  [22, 'anatomy-shoulder-arm.png'],
  [23, 'anatomy-shoulder-arm.png'],
  [24, 'anatomy-shoulder-arm.png'],
  [28, 'anatomy-shoulder-arm.png'],
  [30, 'anatomy-shoulder-arm.png'],
  [95, 'anatomy-leg-medial.png'],
  [101, 'anatomy-foot-plantar.png'],
  [102, 'anatomy-foot-plantar.png'],
  [105, 'anatomy-foot-plantar.png'],
  [106, 'anatomy-foot-plantar.png'],
  [107, 'anatomy-foot-plantar.png'],
  [108, 'anatomy-foot-plantar.png'],
  [109, 'anatomy-foot-plantar.png']
]);

function slugify(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function sha256(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function blockFor(id) {
  const block = blockRanges.find((item) => id >= item.start && id <= item.end);
  if (!block) throw new Error(`No hay bloque asignado para MM-${String(id).padStart(3, '0')}.`);
  return block.dir;
}

function templateFor(id) {
  if (explicitTemplates.has(id)) return explicitTemplates.get(id);
  if (id <= 18) return 'anatomy-head-neck.png';
  if (id <= 46) return 'anatomy-trunk-pelvis.png';
  if (id <= 57) return 'anatomy-shoulder-arm.png';
  if (id <= 75) return 'anatomy-elbow-forearm-hand.png';
  if (id <= 89) return 'anatomy-hip-thigh-knee.png';
  if (id <= 104) return 'anatomy-leg-ankle-foot.png';
  return 'anatomy-foot-plantar.png';
}

function variantFor(id) {
  if (id === 12) return 'division-esternal';
  if (id === 13) return 'vertex';
  return 'mapa-01';
}

function variantsFor(entry) {
  if (entry.number === 19) {
    return [
      { id: 'MM-019', variant: 'mapa-completo', template: 'anatomy-head-upper-body.png' }
    ];
  }

  return [{
    id: entry.code,
    variant: variantFor(entry.number),
    template: templateFor(entry.number)
  }];
}

const inventory = fs.readFileSync(inventoryPath, 'utf8');
const entries = [...inventory.matchAll(/\*\*(MM-(\d{3})) — ([^*]+)\*\*/g)].map((match) => ({
  code: match[1],
  number: Number(match[2]),
  label: match[3].trim()
}));

if (entries.length !== 109) {
  throw new Error(`El inventario contiene ${entries.length} unidades; se esperaban 109.`);
}

fs.mkdirSync(packDir, { recursive: true });

const manifest = {
  version: '1.1.0',
  generated_at: new Date().toISOString(),
  canvas: { width: 1448, height: 1086, color_space: 'sRGB' },
  total: 0,
  items: []
};

let created = 0;
let preserved = 0;

for (const entry of entries) {
  const block = blockFor(entry.number);
  const targetDir = path.join(packDir, block);
  fs.mkdirSync(targetDir, { recursive: true });

  for (const definition of variantsFor(entry)) {
    const sourcePath = path.join(assetsDir, definition.template);
    const fileName = `${definition.id}__${slugify(entry.label)}__${definition.variant}.png`;
    const targetPath = path.join(targetDir, fileName);

    if (!fs.existsSync(targetPath)) {
      try {
        fs.copyFileSync(sourcePath, targetPath, fs.constants.COPYFILE_FICLONE);
      } catch {
        fs.copyFileSync(sourcePath, targetPath);
      }
      created += 1;
    } else {
      preserved += 1;
    }

    const baseline = sha256(sourcePath);
    const current = sha256(targetPath);
    manifest.items.push({
      id: definition.id,
      canonical_id: entry.code,
      label: entry.label,
      block,
      variant: definition.variant,
      source_template: `patients/explora-dolor/assets/${definition.template}`,
      drawing_file: path.relative(root, targetPath),
      baseline_sha256: baseline,
      current_sha256: current,
      status: current === baseline ? 'pendiente' : 'modificado'
    });
  }
}

manifest.total = manifest.items.length;
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

const modified = manifest.items.filter((item) => item.status === 'modificado').length;
console.log(`Paquete: ${path.relative(root, packDir)}`);
console.log(`Nuevas copias: ${created}`);
console.log(`Copias preservadas: ${preserved}`);
console.log(`Modificadas por Fran: ${modified}`);
console.log(`Total: ${manifest.items.length}`);
