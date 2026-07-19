(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.FisioLogicoInstrumentTools = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function parseLocalizedNumber(value) {
    const normalized = String(value ?? '').trim().replace(/\s/g, '').replace(',', '.');
    if (!normalized || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return NaN;
    return Number(normalized);
  }

  function metricRange(metric) {
    const lower = metric.exclusive_min !== undefined
      ? `mayor que ${formatPlain(metric.exclusive_min, metric.decimals)}`
      : metric.min !== undefined ? `entre ${formatPlain(metric.min, metric.decimals)}` : '';
    const upper = metric.max !== undefined ? formatPlain(metric.max, metric.decimals) : '';
    if (metric.min !== undefined && upper) return `${lower} y ${upper}`;
    if (metric.exclusive_min !== undefined && upper) return `${lower} y como máximo ${upper}`;
    if (lower) return lower;
    if (upper) return `menor o igual que ${upper}`;
    return 'numérico';
  }

  function formatPlain(value, decimals) {
    return new Intl.NumberFormat('es-ES', {
      maximumFractionDigits: Math.max(0, decimals ?? 3),
      useGrouping: false,
    }).format(value);
  }

  function validateValue(value, metric) {
    if (!Number.isFinite(value)) return 'Introduce un número válido.';
    if (metric.min !== undefined && value < metric.min) return `El valor debe estar ${metricRange(metric)}.`;
    if (metric.exclusive_min !== undefined && value <= metric.exclusive_min) return `El valor debe ser ${metricRange(metric)}.`;
    if (metric.max !== undefined && value > metric.max) return `El valor debe estar ${metricRange(metric)}.`;
    if (metric.integer && !Number.isInteger(value)) return 'Esta métrica solo admite números enteros.';
    return '';
  }

  function roundTo(value, decimals) {
    const factor = 10 ** Math.max(0, decimals ?? 3);
    const rounded = Math.round((Math.abs(value) + Number.EPSILON) * factor) / factor;
    return value < 0 ? -rounded : rounded;
  }

  function calculateChange(baseline, followup, metric) {
    const baselineError = validateValue(baseline, metric);
    if (baselineError) return { ok: false, field: 'baseline', error: baselineError };
    const followupError = validateValue(followup, metric);
    if (followupError) return { ok: false, field: 'followup', error: followupError };

    const change = roundTo(followup - baseline, metric.decimals);
    let direction = 'sin diferencia en la precisión mostrada';
    if (change !== 0) {
      const favorable = metric.direction === 'higher_favorable' ? change > 0 : change < 0;
      direction = favorable ? 'dirección favorable según la escala' : 'dirección desfavorable según la escala';
    }
    return { ok: true, change, direction };
  }

  function formatSigned(value, decimals) {
    if (Object.is(value, -0) || value === 0) return formatPlain(0, decimals);
    const magnitude = formatPlain(Math.abs(value), decimals);
    return `${value > 0 ? '+' : '−'}${magnitude}`;
  }

  function initializeChangeCalculator(tool) {
    let config;
    try {
      config = JSON.parse(tool.dataset.calculatorConfig || '{}');
    } catch (_error) {
      return;
    }
    if (!Array.isArray(config.metrics) || !config.metrics.length) return;

    const form = tool.querySelector('[data-change-form]');
    const baseline = tool.querySelector('[data-change-baseline]');
    const followup = tool.querySelector('[data-change-followup]');
    const metricSelect = tool.querySelector('[data-change-metric]');
    const metricNote = tool.querySelector('[data-change-metric-note]');
    const result = tool.querySelector('[data-change-result]');
    if (!form || !baseline || !followup || !result) return;

    const selectedMetric = () => config.metrics.find((item) => item.id === metricSelect?.value) || config.metrics[0];
    const setResult = (title, detail, state) => {
      result.replaceChildren();
      const strong = document.createElement('strong');
      const span = document.createElement('span');
      strong.textContent = title;
      span.textContent = detail;
      result.append(strong, span);
      result.dataset.state = state;
    };
    const clearErrors = () => {
      baseline.removeAttribute('aria-invalid');
      followup.removeAttribute('aria-invalid');
    };
    const updateMetric = () => {
      const metric = selectedMetric();
      metricNote.textContent = `${metric.note} Rango admitido: ${metricRange(metric)}${metric.integer ? '; solo enteros' : ''}.`;
      baseline.value = '';
      followup.value = '';
      clearErrors();
      setResult('Sin cálculo', 'Introduce dos valores válidos de la misma métrica.', 'idle');
    };

    metricSelect?.addEventListener('change', updateMetric);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      clearErrors();
      const metric = selectedMetric();
      const calculation = calculateChange(
        parseLocalizedNumber(baseline.value),
        parseLocalizedNumber(followup.value),
        metric
      );
      if (!calculation.ok) {
        const field = calculation.field === 'baseline' ? baseline : followup;
        field.setAttribute('aria-invalid', 'true');
        setResult('Revisa los datos', calculation.error, 'error');
        field.focus();
        return;
      }
      setResult(
        `${formatSigned(calculation.change, metric.decimals)} ${metric.unit}`,
        `${calculation.direction}. No establece por sí solo un cambio real o clínicamente importante.`,
        calculation.change === 0 ? 'stable' : 'calculated'
      );
    });
    updateMetric();
  }

  function initializeDocument(doc) {
    doc.querySelectorAll('[data-change-calculator]').forEach(initializeChangeCalculator);
    doc.querySelectorAll('[data-print-protocol]').forEach((button) => {
      button.addEventListener('click', () => window.print());
    });
  }

  if (typeof document !== 'undefined') initializeDocument(document);

  return {
    parseLocalizedNumber,
    validateValue,
    calculateChange,
    formatSigned,
    metricRange,
    initializeDocument,
  };
});
