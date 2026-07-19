#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const tools = require('../instrumentos/instrument-tools.js');

const root = path.resolve(__dirname, '..');
const load = (name) => JSON.parse(fs.readFileSync(path.join(root, 'data', name), 'utf8')).instruments;
const instruments = [...load('instruments.json'), ...load('performance-instruments.json')];
const byAcronym = new Map(instruments.map((item) => [item.acronym, item]));

assert.equal(tools.parseLocalizedNumber(' 30,5 '), 30.5, 'admite coma decimal española');
assert.ok(Number.isNaN(tools.parseLocalizedNumber('1e3')), 'rechaza notación no prevista');
assert.ok(Number.isNaN(tools.parseLocalizedNumber('')), 'rechaza valores vacíos');

for (const instrument of instruments) {
  const calculator = instrument.calculator;
  assert.equal(typeof calculator.enabled, 'boolean', `${instrument.acronym}: estado definido`);
  if (!calculator.enabled) {
    assert.ok(calculator.disabled_reason, `${instrument.acronym}: explica por qué está desactivada`);
    continue;
  }
  assert.ok(calculator.metrics.length > 0, `${instrument.acronym}: al menos una métrica`);
  assert.equal(new Set(calculator.metrics.map((metric) => metric.id)).size, calculator.metrics.length, `${instrument.acronym}: identificadores únicos`);
  for (const metric of calculator.metrics) {
    assert.ok(['higher_favorable', 'lower_favorable'].includes(metric.direction), `${instrument.acronym}/${metric.id}: dirección explícita`);
    assert.ok(metric.unit && metric.note, `${instrument.acronym}/${metric.id}: unidad y condiciones declaradas`);
    if (metric.min !== undefined) assert.equal(tools.validateValue(metric.min, metric), '', `${instrument.acronym}/${metric.id}: acepta mínimo`);
    if (metric.max !== undefined) assert.equal(tools.validateValue(metric.max, metric), '', `${instrument.acronym}/${metric.id}: acepta máximo`);
    if (metric.min !== undefined) assert.ok(tools.validateValue(metric.min - 1, metric), `${instrument.acronym}/${metric.id}: rechaza bajo rango`);
    if (metric.max !== undefined) assert.ok(tools.validateValue(metric.max + 1, metric), `${instrument.acronym}/${metric.id}: rechaza sobre rango`);
    if (metric.exclusive_min !== undefined) assert.ok(tools.validateValue(metric.exclusive_min, metric), `${instrument.acronym}/${metric.id}: mínimo exclusivo`);
    if (metric.integer) assert.ok(tools.validateValue((metric.min ?? 0) + 0.5, metric), `${instrument.acronym}/${metric.id}: exige enteros`);
  }
}

function calculate(acronym, metricId, baseline, followup) {
  const metric = byAcronym.get(acronym).calculator.metrics.find((item) => item.id === metricId);
  assert.ok(metric, `${acronym}/${metricId}: métrica presente`);
  return tools.calculateChange(baseline, followup, metric);
}

assert.match(calculate('ODI', 'percent', 60, 40).direction, /favorable/, 'ODI baja = favorable');
assert.match(calculate('NDI', 'raw', 30, 20).direction, /favorable/, 'NDI baja = favorable');
assert.match(calculate('QuickDASH', 'main', 70, 40).direction, /favorable/, 'QuickDASH baja = favorable');
assert.match(calculate('END', 'nrs', 8, 4).direction, /favorable/, 'END baja = favorable');
assert.match(calculate('WHODAS 2.0', 'normalized', 60, 45).direction, /favorable/, 'WHODAS baja = favorable');
assert.match(calculate('PROMIS-SD 8a', 'tscore', 65.5, 55.5).direction, /favorable/, 'PROMIS-SD baja = favorable');
assert.match(calculate('PCS', 'total', 30, 20).direction, /favorable/, 'PCS baja = favorable');
assert.match(calculate('PSFS', 'mean', 4, 7).direction, /favorable/, 'PSFS sube = favorable');
assert.match(calculate('PSEQ-10', 'total', 25, 40).direction, /favorable/, 'PSEQ sube = favorable');
assert.match(calculate('TUG', 'seconds', 12, 10).direction, /favorable/, 'TUG baja = favorable');
assert.match(calculate('10MWT', 'speed', 0.7, 0.9).direction, /favorable/, '10MWT sube = favorable');
assert.equal(calculate('EQ-5D-5L', 'index', -0.2, 0.5).change, 0.7, 'índice EQ-5D admite valores negativos ya calculados');
assert.equal(calculate('EQ-5D-5L', 'index', 0.5, 1.1).ok, false, 'índice EQ-5D no supera 1');
assert.equal(calculate('PSFS', 'mean', 0.0004, 0.0005).direction, 'sin diferencia en la precisión mostrada', 'no muestra +0 como cambio favorable');
assert.equal(calculate('PSFS', 'mean', 0.015, 0.01).change, -0.01, 'el redondeo es simétrico también para cambios negativos');
assert.equal(byAcronym.get('PGIC').calculator.enabled, false, 'PGIC permanece desactivada');

console.log(`OK: ${instruments.length} instrumentos y ${instruments.filter((item) => item.calculator.enabled).length} comparadores verificados.`);
