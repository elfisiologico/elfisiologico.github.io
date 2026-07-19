#!/usr/bin/env python3
"""Genera el catálogo de instrumentos desde data/instruments.json."""
from __future__ import annotations

import html
import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from sync_navigation import sync_navigation

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "instruments.json"
OUTPUT = ROOT / "instrumentos" / "index.html"
PERFORMANCE_DATA = ROOT / "data" / "performance-instruments.json"
PERFORMANCE_OUTPUT = ROOT / "instrumentos" / "rendimiento" / "index.html"
GUIDANCE_DATA = ROOT / "data" / "instrument-guidance.json"
STYLE_VERSION = hashlib.sha256((ROOT / "styles.css").read_bytes()).hexdigest()[:10]

MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def esc(value):
    return html.escape(str(value), quote=True)


def key(value):
    normalized = unicodedata.normalize("NFD", str(value).lower())
    return "_".join("".join(c for c in normalized if unicodedata.category(c) != "Mn").split())


def date_es(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.day} de {MONTHS[parsed.month]} de {parsed.year}"


def purpose_keys(instrument):
    return " ".join(key(item) for item in instrument["purpose"])


def permission_action(instrument):
    if instrument.get("permission_url"):
        return f'<a class="permission-action" href="{esc(instrument["permission_url"])}" target="_blank" rel="noopener">{esc(instrument["permission_action"])} ↗</a>'
    return f'<span class="permission-action is-static">{esc(instrument["permission_action"])}</span>'


def card(instrument):
    acronym_class = " measure-acronym-long" if len(instrument["acronym"]) > 5 else ""
    search = " ".join(
        [instrument["acronym"], instrument["name"], instrument["construct"], instrument["region"], instrument["summary"]]
        + instrument["purpose"]
    )
    return f'''<article class="measure-card" data-instrument-card data-acronym="{esc(instrument["acronym"])}" data-type="{esc(instrument["type"])}" data-construct="{esc(instrument["construct_key"])}" data-region="{esc(instrument["region_key"])}" data-validation="{esc(instrument["validation_key"])}" data-permission="{esc(instrument["permission_key"])}" data-purpose="{esc(purpose_keys(instrument))}" data-search="{esc(search)}" data-compare-type="{esc(instrument["type_label"])}" data-compare-construct="{esc(instrument["construct"])}" data-compare-time="{esc(instrument["time"])}" data-compare-range="{esc(instrument["score_range"])}" data-compare-direction="{esc(instrument["direction_label"])}" data-compare-validation="{esc(instrument["spanish_label"])}" data-compare-population="{esc(instrument["validated_population"])}" data-compare-evidence="{esc(instrument["evidence_label"])}" data-compare-permission="{esc(instrument["permission_label"])}" data-compare-useful="{esc(instrument["useful_for"])}" data-compare-not-for="{esc(instrument["not_for"])}">
<div class="measure-card-top"><span class="measure-acronym{acronym_class}">{esc(instrument["acronym"])}</span><span class="measure-region">{esc(instrument["region"])}</span></div>
<label class="compare-choice"><input type="checkbox" data-compare-choice><span>Comparar</span></label>
<h2><a href="{esc(instrument["slug"])}/">{esc(instrument["name"])}</a></h2><p class="measure-construct">{esc(instrument["summary"])}</p>
<dl class="measure-logistics"><div><dt>Formato</dt><dd>{esc(instrument["items"])}</dd></div><div><dt>Tiempo</dt><dd>{esc(instrument["time"])}</dd></div></dl>
<dl class="measure-core"><div><dt>Rango</dt><dd>{esc(instrument["score_range"])}</dd></div><div class="direction-{esc(instrument["score_direction"])}"><dt>Dirección</dt><dd>{esc(instrument["direction_label"])}</dd></div></dl>
<ul class="measure-evidence" aria-label="Estado técnico"><li><span>Versión española</span><strong>{esc(instrument["spanish_label"])}</strong></li><li><span>Población estudiada</span><strong>{esc(instrument["validated_population"])}</strong></li><li><span>Permiso</span><strong>{esc(instrument["permission_label"])}</strong></li></ul>
<details class="measure-more"><summary>Utilidad, límites y elección</summary><div><p><strong>Administración</strong>{esc(instrument["administration"])}</p><p><strong>Periodo</strong>{esc(instrument["recall_period"])}</p><p><strong>Útil para</strong>{esc(instrument["useful_for"])}</p><p><strong>No sirve para</strong>{esc(instrument["not_for"])}</p><p><strong>Cuándo elegirla</strong>{esc(instrument["choice_note"])}</p>{permission_action(instrument)}</div></details>
<div class="measure-card-footer"><a href="{esc(instrument["slug"])}/">Abrir ficha técnica →</a><time datetime="{esc(instrument["updated_at"])}">Revisada {esc(date_es(instrument["updated_at"]))}</time></div></article>'''


def option(value, label):
    return f'<option value="{esc(value)}">{esc(label)}</option>'


def change_matrix(instrument):
    change = instrument["change_interpretation"]
    examples = "".join(
        f'''<article class="change-example"><div><span>{esc(item["metric"])}</span><strong>{esc(item["value"])}</strong></div><p>{esc(item["population"])}.</p><p>{esc(item["method"])}.</p><a href="{esc(item["source_url"])}" target="_blank" rel="noopener">Fuente del ejemplo ↗</a></article>'''
        for item in change["examples"]
    ) or '<p class="change-empty"><strong>Sin cifra transferible.</strong> No se ha incorporado un valor de ejemplo que pueda presentarse sin inducir una regla general.</p>'
    return f'''<section id="cambio" class="change-matrix"><p class="section-label">Interpretar el cambio</p><h2>Error, cambio detectable e importancia no son sinónimos.</h2><div class="change-definitions"><article><span>SEM</span><strong>{esc(change["sem"])}</strong><p>Error estándar de medida: incertidumbre de la puntuación.</p></article><article><span>MDC</span><strong>{esc(change["mdc"])}</strong><p>Cambio mínimo detectable: diferencia más allá del error para el método declarado.</p></article><article><span>MIC / MCID</span><strong>{esc(change["mic"])}</strong><p>Cambio considerado importante con un anclaje y una población concretos.</p></article></div><div class="change-examples">{examples}</div><p class="change-note">{esc(change["note"])}</p></section>'''


def change_calculator(instrument):
    calculator = instrument["calculator"]
    if not calculator["enabled"]:
        return f'''<section class="change-tool is-disabled"><p class="section-label">Herramienta de seguimiento</p><h2>Comparador desactivado.</h2><p>{esc(calculator["disabled_reason"])}</p><p class="change-tool-warning">Decisión deliberada: no se ofrece una operación numérica que pueda inducir una interpretación falsa.</p></section>'''
    metrics = calculator["metrics"]
    config = esc(json.dumps({"metrics": metrics}, ensure_ascii=False, separators=(",", ":")))
    metric_field = ""
    if len(metrics) > 1:
        options = "".join(f'<option value="{esc(metric["id"])}">{esc(metric["label"])}</option>' for metric in metrics)
        metric_field = f'<label class="change-tool-metric">Métrica comparable<select data-change-metric>{options}</select></label>'
    metric_note = esc(metrics[0]["note"])
    return f'''<section class="change-tool" data-change-calculator data-calculator-config="{config}"><p class="section-label">Comparador de seguimiento</p><h2>Calcula el cambio con límites explícitos.</h2><p>{esc(calculator["notice"])}</p><form class="change-tool-fields" data-change-form novalidate>{metric_field}<label>Puntuación inicial<input type="text" inputmode="decimal" autocomplete="off" data-change-baseline aria-describedby="change-metric-note"></label><label>Puntuación de seguimiento<input type="text" inputmode="decimal" autocomplete="off" data-change-followup aria-describedby="change-metric-note"></label><button type="submit" data-change-calculate>Calcular cambio</button></form><p class="change-tool-metric-note" id="change-metric-note" data-change-metric-note>{metric_note}</p><output class="change-tool-result" data-change-result aria-live="polite" aria-atomic="true"><strong>Sin cálculo</strong><span>Introduce dos valores válidos de la misma métrica.</span></output><p class="change-tool-warning">El signo describe la dirección de la escala. No demuestra por sí solo cambio real, importancia clínica ni causalidad.</p></section>'''


def maintenance_block(instrument):
    maintenance = instrument["maintenance"]
    return f'''<section class="instrument-maintenance"><p class="section-label">Mantenimiento</p><h2><span class="status-dot" aria-hidden="true"></span>{esc(maintenance["status"].capitalize())}</h2><dl><div><dt>Última búsqueda</dt><dd>{esc(date_es(instrument["evidence_search_date"]))}</dd></div><div><dt>Próxima revisión prevista</dt><dd>{esc(date_es(maintenance["next_review_at"]))}</dd></div><div><dt>Revisión anticipada</dt><dd>{esc(maintenance["review_cycle"])}</dd></div></dl></section>'''


def tools_script(depth):
    return f'<script src="{depth}instrument-tools.js?v=2" defer></script>'


def builder_html(guidance):
    builder = guidance["builder"]
    select = lambda name, label, values: f'<label>{label}<select data-builder-{name}>{"".join(option(value, text) for value, text in values)}</select></label>'
    return f'''<section class="battery-builder" id="crear-bateria"><div class="shell battery-builder-layout"><div class="battery-builder-heading"><p class="section-label light">Selector de batería</p><h2>Cuatro decisiones.<br>Una batería mínima.</h2><p>La propuesta orienta la elección; no sustituye el razonamiento sobre población, versión, seguridad o permisos.</p></div><form class="battery-builder-form" data-battery-builder>{select("goal", "1 · Qué necesitas medir", builder["goal_options"])}{select("context", "2 · Región o contexto", builder["context_options"])}{select("phase", "3 · Momento", builder["phase_options"])}{select("time", "4 · Tiempo disponible", builder["time_options"])}<button type="submit">Proponer batería</button></form><aside class="battery-result" data-battery-result aria-live="polite"><span class="battery-result-kicker">Propuesta inicial</span><h3>Selecciona cuatro criterios.</h3><p>Priorizaremos una medida principal y añadiremos otra solo si aporta un constructo diferente.</p></aside></div></section>'''


def cases_html(guidance):
    cards = "".join(
        f'''<article><span>{index:02d}</span><h3>{esc(case["label"])}</h3><p>{esc(case["question"])}</p><ul>{"".join(f"<li>{esc(item)}</li>" for item in case["battery"])}</ul><dl><div><dt>Repetición</dt><dd>{esc(case["schedule"])}</dd></div><div><dt>Evita</dt><dd>{esc(case["avoid"])}</dd></div></dl></article>'''
        for index, case in enumerate(guidance["cases"], 1)
    )
    return f'''<section class="clinical-cases"><div class="shell"><div class="selection-guide-heading"><p class="section-label">Casos de uso</p><h2>La batería se diseña desde la pregunta.</h2></div><div class="clinical-cases-grid">{cards}</div><p class="cases-disclaimer">Ejemplos educativos con situaciones ficticias. No constituyen una pauta para una persona concreta.</p></div></section>'''


def joint_reading_html(guidance):
    payload = esc(json.dumps(guidance["discordance"], ensure_ascii=False, separators=(",", ":")))
    return f'''<section class="joint-reading"><div class="shell joint-reading-layout"><div><p class="section-label light">Percepción + rendimiento</p><h2>Dos resultados.<br>Una conversación.</h2><p>Introduce cambios ya calculados. La herramienta solo compara direcciones y propone qué revisar.</p></div><form data-joint-reading data-guidance="{payload}"><fieldset><legend>Autoinforme</legend><label>Cambio<input type="number" step="any" inputmode="decimal" data-joint-prom></label><label>Mejora cuando<select data-joint-prom-direction><option value="higher">sube</option><option value="lower">baja</option></select></label></fieldset><fieldset><legend>Rendimiento</legend><label>Cambio<input type="number" step="any" inputmode="decimal" data-joint-performance></label><label>Mejora cuando<select data-joint-performance-direction><option value="higher">sube</option><option value="lower">baja</option></select></label></fieldset><button type="submit">Leer conjuntamente</button></form><output class="joint-result" data-joint-result aria-live="polite"><strong>Sin lectura todavía.</strong><span>Introduce ambos cambios; cero se interpreta como estable.</span></output></div></section>'''


def maintenance_index_html(guidance):
    changes = "".join(f'<li><time datetime="{esc(item["date"])}">{esc(date_es(item["date"]))}</time><span>{esc(item["change"])}</span></li>' for item in guidance["changelog"])
    return f'''<section class="collection-maintenance"><div class="shell"><div><p class="section-label">Mantenimiento visible</p><h2><span class="status-dot" aria-hidden="true"></span>Colección {esc(guidance["status"])}.</h2><p>Próxima revisión programada: <time datetime="{esc(guidance["next_review_at"])}">{esc(date_es(guidance["next_review_at"]))}</time>. Se adelantará si cambia una versión, licencia o evidencia relevante.</p></div><ol>{changes}</ol></div></section>'''


def generated_detail_page(instrument):
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source["label"])}</a></li>'
        for source in instrument["sources"]
    )
    detail_name = "" if instrument["name"].casefold() == instrument["acronym"].casefold() else f' · {esc(instrument["name"])}'
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "MedicalWebPage", "name": instrument["name"], "description": instrument["summary"], "url": f'https://www.elfisiologico.com/instrumentos/{instrument["slug"]}/', "dateModified": instrument["updated_at"], "author": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"}},
            {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Instrumentos clínicos", "item": "https://www.elfisiologico.com/instrumentos/"}, {"@type": "ListItem", "position": 2, "name": instrument["acronym"]}]},
        ],
    }
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(instrument["acronym"])}: uso e interpretación en fisioterapia · FisioLógico</title><meta name="description" content="Ficha técnica de {esc(instrument["name"])}: aplicación, puntuación, límites, evidencia y permisos."><meta name="robots" content="index,follow"><link rel="canonical" href="https://www.elfisiologico.com/instrumentos/{esc(instrument["slug"])}/"><meta property="og:type" content="article"><meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="{esc(instrument["acronym"])}: uso e interpretación en fisioterapia"><meta property="og:description" content="{esc(instrument["summary"])}"><meta property="og:url" content="https://www.elfisiologico.com/instrumentos/{esc(instrument["slug"])}/"><meta property="og:image" content="https://www.elfisiologico.com/assets/logo-fisiologico-cuadrado.png"><link rel="icon" href="../../assets/logo-fisiologico-cuadrado.png"><link rel="stylesheet" href="../../styles.css?v={STYLE_VERSION}"><link rel="stylesheet" href="../instruments.css?v=6"><meta name="theme-color" content="#000"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head><body class="editorial-page instruments-page"><a class="skip-link" href="#contenido">Saltar al contenido</a><header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="../../" aria-label="FisioLógico, inicio">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="../../patients/">Pacientes</a><a href="../../profesionales/" aria-current="page">Profesionales</a><a href="../../con-logica/">Con lógica</a></nav></div></header><main id="contenido">
<header class="measure-detail-hero"><div class="shell"><nav class="measure-breadcrumbs" aria-label="Migas de pan"><a href="../">Instrumentos</a><span>›</span><span>{esc(instrument["acronym"])}</span></nav><h1><span>{esc(instrument["acronym"])}</span>{detail_name}</h1><p class="measure-subtitle">{esc(instrument["summary"])} No establece un diagnóstico ni explica por sí sola la evolución.</p><dl class="measure-summary"><div><dt>Constructo</dt><dd>{esc(instrument["construct"])}</dd></div><div><dt>Formato</dt><dd>{esc(instrument["items"])}</dd></div><div><dt>Tiempo</dt><dd>{esc(instrument["time"])}</dd></div><div><dt>Rango</dt><dd>{esc(instrument["score_range"])}</dd></div></dl></div></header>
<div class="measurement-print" aria-label="Huella de medición"><div class="shell"><div class="print-cell"><span>Respaldo</span><strong>{esc(instrument["evidence_label"])}</strong></div><div class="print-cell"><span>Dirección</span><strong>{esc(instrument["direction_label"])}</strong></div><div class="print-cell"><span>Español</span><strong>{esc(instrument["spanish_label"])}</strong></div><div class="print-cell"><span>Población</span><strong>{esc(instrument["validated_population"])}</strong></div><div class="print-cell" data-state="limited"><span>Permiso</span><strong>{esc(instrument["permission_label"])}</strong></div></div></div>
<div class="measure-detail shell"><aside class="measure-rail"><p>En esta ficha</p><nav><a href="#decision">Decisión rápida</a><a href="#aplicacion">Aplicación</a><a href="#interpretacion">Interpretación</a><a href="#medicion">Calidad de medición</a><a href="#cambio">Interpretar cambio</a><a href="#permisos">Permisos</a><a href="#fuentes">Fuentes</a></nav><div class="permission-note"><strong>{esc(instrument["permission_label"])}.</strong><br>{esc(instrument["permission_status"])}</div></aside><article class="measure-copy">
<section id="decision" class="clinical-verdict"><p class="section-label">Decisión rápida</p><h2>{esc(instrument["choice_note"])}</h2><p>{esc(instrument["useful_for"])}.</p><p>No debe utilizarse para {esc(instrument["not_for"].lower())}.</p></section>
<section id="aplicacion"><p class="section-label">Aplicación</p><h2>Define exactamente qué se pregunta y cuándo.</h2><p><strong>Administración:</strong> {esc(instrument["administration"])}.</p><p><strong>Periodo de referencia:</strong> {esc(instrument["recall_period"])}.</p><p><strong>Versión:</strong> {esc(instrument["version"])}.</p></section>
<section id="interpretacion"><p class="section-label">Interpretación</p><h2>Una cifra necesita contexto y una referencia estable.</h2><p>Rango: {esc(instrument["score_range"])}. {esc(instrument["direction_label"])}. El cambio debe contrastarse con el error de medida, la población, el periodo y la finalidad; no se aplica un umbral universal.</p><div class="limits-panel"><h3>Límite principal</h3><p>{esc(instrument["not_for"])}.</p></div></section>
<section id="medicion"><p class="section-label">Calidad de medición</p><h2>{esc(instrument["evidence_label"])}.</h2><table class="measure-table"><caption>Resumen técnico de la evidencia</caption><tr><th>Método</th><td>{esc(instrument["evidence_method"])}</td></tr><tr><th>Población</th><td>{esc(instrument["validated_population"])}</td></tr><tr><th>Versión española</th><td>{esc(instrument["spanish_status"])}</td></tr><tr><th>Última búsqueda</th><td>{esc(date_es(instrument["evidence_search_date"]))}</td></tr></table></section>
{change_matrix(instrument)}{change_calculator(instrument)}
<section id="permisos"><p class="section-label">Uso y derechos</p><h2>{esc(instrument["permission_label"])}.</h2><p>{esc(instrument["permission_basis"])}.</p><p>{esc(instrument["permission_status"])}.</p>{permission_action(instrument)}</section>
<section id="fuentes"><p class="section-label">Fuentes verificadas</p><h2>Documentación principal</h2><ul class="source-list">{sources}</ul></section>
{maintenance_block(instrument)}
<section class="editorial-responsibility" aria-labelledby="responsabilidad-editorial"><p class="responsibility-label">Responsabilidad editorial</p><div class="responsibility-grid"><div><h2 id="responsabilidad-editorial"><a href="../../sobre-fran/">Francisco José Extremera García</a></h2><p class="responsibility-credentials">Fisioterapeuta colegiado ICPFA 4288 · Osteópata D.O.</p><p>Creador y responsable editorial de FisioLógico</p></div><dl><div><dt>Última revisión</dt><dd><time datetime="{esc(instrument["updated_at"])}">{esc(date_es(instrument["updated_at"]))}</time></dd></div><div><dt>Conflictos de interés</dt><dd>Ninguno declarado.</dd></div></dl></div><a class="responsibility-method" href="../../metodo-editorial/">Cómo revisamos el contenido →</a></section>
</article></div></main><footer class="site-footer"><div class="shell editorial-footer"><p>© <span data-current-year>2026</span> FisioLógico</p><a href="../">Volver a instrumentos</a></div></footer>{tools_script("../")}<script src="../../script.js?v=6" defer></script></body></html>'''


def canonical_detail_block(instrument):
    return f'''<!-- instrument-canonical:start --><section id="datos-operativos" class="instrument-canonical"><p class="section-label">Datos operativos verificados</p><h2>Versión, administración y trazabilidad</h2><dl><div><dt>Versión</dt><dd>{esc(instrument["version"])}</dd></div><div><dt>Administración</dt><dd>{esc(instrument["administration"])}</dd></div><div><dt>Periodo de referencia</dt><dd>{esc(instrument["recall_period"])}</dd></div><div><dt>Última búsqueda científica</dt><dd><time datetime="{esc(instrument["evidence_search_date"])}">{esc(date_es(instrument["evidence_search_date"]))}</time></dd></div><div><dt>Permisos comprobados</dt><dd><strong>{esc(instrument["permission_label"])}</strong> · <time datetime="{esc(instrument["permission_checked_at"])}">{esc(date_es(instrument["permission_checked_at"]))}</time> · {esc(instrument["permission_basis"])}</dd></div><div><dt>Criterio de evidencia</dt><dd>{esc(instrument["evidence_method"])}</dd></div></dl></section>{change_matrix(instrument)}{change_calculator(instrument)}{maintenance_block(instrument)}<!-- instrument-canonical:end -->'''


def sync_existing_detail(instrument):
    path = ROOT / "instrumentos" / instrument["slug"] / "index.html"
    source = path.read_text(encoding="utf-8")
    block = canonical_detail_block(instrument)
    if "<!-- instrument-canonical:start -->" in source:
        source = re.sub(r'<!-- instrument-canonical:start -->.*?<!-- instrument-canonical:end -->', block, source, flags=re.S)
    else:
        marker = '<section class="editorial-responsibility"'
        source = source.replace(marker, f'{block}{marker}', 1)
    source = re.sub(r'instruments\.css\?v=\d+', 'instruments.css?v=6', source)
    source = re.sub(r'instrument-tools\.js\?v=\d+', 'instrument-tools.js?v=2', source)
    if "instrument-tools.js" not in source:
        source = source.replace('<script src="../../script.js?v=6" defer></script>', f'{tools_script("../")}<script src="../../script.js?v=6" defer></script>')
    path.write_text(source, encoding="utf-8")


def performance_card(instrument):
    direction_symbol = "↓" if instrument["score_direction"] == "lower_better" else "↑"
    return f'''<article class="performance-card"><div class="performance-card-top"><strong>{esc(instrument["acronym"])}</strong><span>{esc(instrument["construct"])}</span></div><h2><a href="{esc(instrument["slug"])}/">{esc(instrument["name"])}</a></h2><p>{esc(instrument["summary"])}</p><dl class="performance-output"><div><dt>Resultado</dt><dd>{esc(instrument["outcome"])}</dd></div><div><dt>Dirección</dt><dd>{direction_symbol} {esc(instrument["direction_label"])}</dd></div></dl><dl class="performance-logistics"><div><dt>Tiempo</dt><dd>{esc(instrument["time"])}</dd></div><div><dt>Equipo</dt><dd>{esc(instrument["equipment"])}</dd></div></dl><div class="performance-warning"><strong>Estandariza</strong><p>{esc(instrument["standardization"])}</p></div><a class="performance-detail-link" href="{esc(instrument["slug"])}/">Abrir protocolo técnico →</a></article>'''


def performance_detail_page(instrument):
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source["label"])}</a></li>'
        for source in instrument["sources"]
    )
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "MedicalWebPage", "name": instrument["name"], "description": instrument["summary"], "url": f'https://www.elfisiologico.com/instrumentos/rendimiento/{instrument["slug"]}/', "dateModified": instrument["updated_at"], "author": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"}},
            {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Instrumentos", "item": "https://www.elfisiologico.com/instrumentos/"}, {"@type": "ListItem", "position": 2, "name": "Rendimiento físico", "item": "https://www.elfisiologico.com/instrumentos/rendimiento/"}, {"@type": "ListItem", "position": 3, "name": instrument["acronym"]}]},
        ],
    }
    direction_symbol = "↓" if instrument["score_direction"] == "lower_better" else "↑"
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(instrument["acronym"])}: protocolo e interpretación · FisioLógico</title><meta name="description" content="Protocolo técnico de {esc(instrument["name"])}: preparación, resultado, seguridad, estandarización y límites."><meta name="robots" content="index,follow"><link rel="canonical" href="https://www.elfisiologico.com/instrumentos/rendimiento/{esc(instrument["slug"])}/"><meta property="og:type" content="article"><meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="{esc(instrument["acronym"])}: protocolo e interpretación"><meta property="og:description" content="{esc(instrument["summary"])}"><meta property="og:url" content="https://www.elfisiologico.com/instrumentos/rendimiento/{esc(instrument["slug"])}/"><meta property="og:image" content="https://www.elfisiologico.com/assets/logo-fisiologico-cuadrado.png"><link rel="icon" href="../../../assets/logo-fisiologico-cuadrado.png"><link rel="stylesheet" href="../../../styles.css?v={STYLE_VERSION}"><link rel="stylesheet" href="../../instruments.css?v=6"><meta name="theme-color" content="#000"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head><body class="editorial-page instruments-page performance-page"><a class="skip-link" href="#contenido">Saltar al contenido</a><header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="../../../" aria-label="FisioLógico, inicio">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="../../../patients/">Pacientes</a><a href="../../../profesionales/" aria-current="page">Profesionales</a><a href="../../../con-logica/">Con lógica</a></nav></div></header><main id="contenido">
<header class="measure-detail-hero performance-detail-hero"><div class="shell"><nav class="measure-breadcrumbs" aria-label="Migas de pan"><a href="../../">Instrumentos</a><span>›</span><a href="../">Rendimiento</a><span>›</span><span>{esc(instrument["acronym"])}</span></nav><h1><span>{esc(instrument["acronym"])}</span> · {esc(instrument["name"])}</h1><p class="measure-subtitle">{esc(instrument["summary"])} El resultado describe una ejecución bajo condiciones concretas, no una capacidad universal.</p><dl class="measure-summary"><div><dt>Constructo</dt><dd>{esc(instrument["construct"])}</dd></div><div><dt>Resultado</dt><dd>{esc(instrument["outcome"])}</dd></div><div><dt>Tiempo</dt><dd>{esc(instrument["time"])}</dd></div><div><dt>Dirección</dt><dd>{direction_symbol} {esc(instrument["direction_label"])}</dd></div></dl></div></header>
<div class="performance-print"><div class="shell"><div><span>Equipo</span><strong>{esc(instrument["equipment"])}</strong></div><div><span>Población</span><strong>{esc(instrument["population"])}</strong></div><div><span>Evidencia</span><strong>{esc(instrument["evidence_label"])}</strong></div><div><span>Fuente</span><strong>{esc(instrument["permission_label"])}</strong></div></div></div>
<div class="measure-detail shell"><aside class="measure-rail"><p>En esta ficha</p><nav><a href="#decision">Decisión rápida</a><a href="#protocolo">Protocolo</a><a href="#seguridad">Seguridad</a><a href="#interpretacion">Interpretación</a><a href="#cambio">Interpretar cambio</a><a href="#fuentes">Fuentes</a></nav><button class="print-protocol-button" type="button" data-print-protocol>Imprimir protocolo</button><div class="permission-note"><strong>Condiciones constantes.</strong><br>{esc(instrument["standardization"])}</div></aside><article class="measure-copy">
<section id="decision" class="clinical-verdict"><p class="section-label">Decisión rápida</p><h2>{esc(instrument["useful_for"])}.</h2><p>No sirve para {esc(instrument["not_for"].lower())}.</p></section>
<section id="protocolo"><p class="section-label">Protocolo operativo</p><h2>Documenta antes de comparar.</h2><p>{esc(instrument["protocol"])}.</p><table class="measure-table"><caption>Condiciones del protocolo</caption><tr><th>Equipo</th><td>{esc(instrument["equipment"])}</td></tr><tr><th>Resultado</th><td>{esc(instrument["outcome"])}</td></tr><tr><th>Unidad o rango</th><td>{esc(instrument["score_range"])}</td></tr><tr><th>Población</th><td>{esc(instrument["population"])}</td></tr></table></section>
<section id="seguridad"><p class="section-label">Seguridad</p><h2>La prueba se detiene antes que el cronómetro.</h2><div class="performance-safety"><p>{esc(instrument["safety"])}.</p></div></section>
<section id="interpretacion"><p class="section-label">Interpretación</p><h2>{esc(instrument["direction_label"])}.</h2><p>{esc(instrument["standardization"])}.</p><div class="limits-panel"><h3>Límite principal</h3><p>{esc(instrument["not_for"])}.</p></div><p class="evidence-search-date">Última búsqueda científica: <time datetime="{esc(instrument["evidence_search_date"])}">{esc(date_es(instrument["evidence_search_date"]))}</time>.</p></section>
{change_matrix(instrument)}{change_calculator(instrument)}
<section id="fuentes"><p class="section-label">Fuentes verificadas</p><h2>Documentación principal</h2><ul class="source-list">{sources}</ul><a class="permission-action" href="{esc(instrument["permission_url"])}" target="_blank" rel="noopener">Consultar fuente del protocolo ↗</a></section>
{maintenance_block(instrument)}
<section class="editorial-responsibility" aria-labelledby="responsabilidad-editorial"><p class="responsibility-label">Responsabilidad editorial</p><div class="responsibility-grid"><div><h2 id="responsabilidad-editorial"><a href="../../../sobre-fran/">Francisco José Extremera García</a></h2><p class="responsibility-credentials">Fisioterapeuta colegiado ICPFA 4288 · Osteópata D.O.</p><p>Creador y responsable editorial de FisioLógico</p></div><dl><div><dt>Última revisión</dt><dd><time datetime="{esc(instrument["updated_at"])}">{esc(date_es(instrument["updated_at"]))}</time></dd></div><div><dt>Conflictos de interés</dt><dd>Ninguno declarado.</dd></div></dl></div><a class="responsibility-method" href="../../../metodo-editorial/">Cómo revisamos el contenido →</a></section>
</article></div></main><footer class="site-footer"><div class="shell editorial-footer"><p>© <span data-current-year>2026</span> FisioLógico</p><a href="../">Volver a rendimiento físico</a></div></footer>{tools_script("../../")}<script src="../../../script.js?v=6" defer></script></body></html>'''


def build_performance():
    payload = json.loads(PERFORMANCE_DATA.read_text(encoding="utf-8"))
    instruments = payload["instruments"]
    items = [{"@type": "ListItem", "position": index, "url": f'https://www.elfisiologico.com/instrumentos/rendimiento/{item["slug"]}/', "name": item["name"]} for index, item in enumerate(instruments, 1)]
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Batería de rendimiento físico en fisioterapia", "description": "Pruebas objetivas de rendimiento físico con protocolos y límites.", "url": "https://www.elfisiologico.com/instrumentos/rendimiento/", "author": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"}, "mainEntity": {"@type": "ItemList", "numberOfItems": len(instruments), "itemListElement": items}}
    cards = "".join(performance_card(instrument) for instrument in instruments)
    page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pruebas de rendimiento físico · FisioLógico</title><meta name="description" content="Batería de rendimiento físico para fisioterapia: 30s-CST, TUG, 10MWT y 6MWT con protocolos, seguridad, resultados y límites."><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="https://www.elfisiologico.com/instrumentos/rendimiento/"><meta property="og:type" content="website"><meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="Pruebas de rendimiento físico"><meta property="og:description" content="Cuatro pruebas objetivas, seleccionadas por la decisión clínica que ayudan a tomar."><meta property="og:url" content="https://www.elfisiologico.com/instrumentos/rendimiento/"><meta property="og:image" content="https://www.elfisiologico.com/assets/logo-fisiologico-cuadrado.png"><link rel="icon" href="../../assets/logo-fisiologico-cuadrado.png"><link rel="stylesheet" href="../../styles.css?v={STYLE_VERSION}"><link rel="stylesheet" href="../instruments.css?v=6"><meta name="theme-color" content="#000"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head><body class="editorial-page instruments-page performance-page"><a class="skip-link" href="#contenido">Saltar al contenido</a><header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="../../" aria-label="FisioLógico, inicio">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="../../patients/">Pacientes</a><a href="../../profesionales/" aria-current="page">Profesionales</a><a href="../../con-logica/">Con lógica</a></nav></div></header><main id="contenido"><section class="performance-hero"><div class="shell"><p class="section-label light">Rendimiento físico · batería paralela</p><h1><span>Observar una tarea.</span><span>Medirla <em>sin simplificarla.</em></span></h1><p>Cuatro pruebas objetivas para fuerza funcional, movilidad, velocidad y capacidad de marcha. El protocolo forma parte del resultado.</p></div></section>
<nav class="measurement-kinds" aria-label="Tipos de medición"><div class="shell"><a href="../"><span>Cuestionarios autoinformados</span><strong>12 PROM →</strong></a><a class="is-current is-performance" href="./" aria-current="page"><span>Rendimiento físico</span><strong>{len(instruments)} pruebas</strong></a><a href="../../pruebas-clinicas/"><span>Exploración física</span><strong>Pruebas por sospecha →</strong></a></div></nav>
<section class="performance-catalog"><div class="shell"><div class="performance-intro"><p class="section-label">Una batería, no cuatro obligaciones</p><h2>Elige la tarea que responde a tu pregunta.</h2><p>Combinar más pruebas no siempre mejora la medición. Mantén al menos una medida autoinformada y añade rendimiento cuando aporte información diferente. <a href="../#crear-bateria">Crear una batería mínima →</a></p></div><div class="performance-grid">{cards}</div></div></section>
<section class="performance-combination"><div class="shell"><h2>Una combinación mínima razonable.</h2><div><article><strong>Fuerza funcional</strong><p>30s-CST si levantarse repetidamente es relevante y seguro.</p></article><article><strong>Movilidad breve</strong><p>TUG para una secuencia integrada; 10MWT si la velocidad es la variable principal.</p></article><article><strong>Capacidad sostenida</strong><p>6MWT solo cuando la marcha submáxima y su respuesta clínica importen.</p></article><article><strong>Perspectiva personal</strong><p>Acompaña el rendimiento con PSFS, una medida regional o el dominio transversal pertinente.</p></article></div></div></section>
<section class="measure-principles"><div class="shell measure-principles-grid"><h2>La estandarización también es clínica.</h2><ol><li><span>Registra equipo, distancia, ayuda y protocolo.</span></li><li><span>No conviertas un punto de corte en diagnóstico.</span></li><li><span>Interpreta el cambio en la población correspondiente.</span></li><li><span>Detén la prueba cuando la seguridad lo exija.</span></li></ol></div></section></main><footer class="site-footer"><div class="shell editorial-footer"><p>© <span data-current-year>2026</span> FisioLógico · Información profesional.</p><div><a href="../../metodo-editorial/">Método editorial</a> <a href="../../sobre-fran/">Sobre Fran</a></div></div></footer><script src="../../script.js?v=6" defer></script></body></html>'''
    PERFORMANCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_OUTPUT.write_text(page, encoding="utf-8")
    for instrument in instruments:
        detail_dir = PERFORMANCE_OUTPUT.parent / instrument["slug"]
        detail_dir.mkdir(parents=True, exist_ok=True)
        (detail_dir / "index.html").write_text(performance_detail_page(instrument), encoding="utf-8")


def build():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    guidance = json.loads(GUIDANCE_DATA.read_text(encoding="utf-8"))
    instruments = payload["instruments"]
    items = [
        {"@type": "ListItem", "position": index, "url": f'https://www.elfisiologico.com/instrumentos/{item["slug"]}/', "name": item["name"]}
        for index, item in enumerate(instruments, 1)
    ]
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Cuestionarios e instrumentos de medición en fisioterapia",
        "description": "Selección técnica de medidas clínicas útiles en fisioterapia.",
        "url": "https://www.elfisiologico.com/instrumentos/",
        "author": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"},
        "isPartOf": {"@type": "WebSite", "name": "FisioLógico", "url": "https://www.elfisiologico.com/"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(instruments), "itemListElement": items},
    }
    construct_labels = {"funcion": "Función", "discapacidad": "Discapacidad", "dolor": "Experiencia de dolor", "intensidad_dolor": "Intensidad del dolor", "funcion_sintomas": "Función y síntomas", "cambio_global": "Cambio global", "calidad_vida": "Calidad de vida", "participacion": "Participación", "sueno": "Sueño", "autoeficacia": "Autoeficacia"}
    region_labels = {item["region_key"]: item["region"] for item in instruments}
    cards = "\n".join(card(item) for item in instruments)
    html_page = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Instrumentos clínicos de fisioterapia · FisioLógico</title><meta name="description" content="Cuestionarios y medidas clínicas útiles en fisioterapia: aplicación, puntuación, dirección, validación española, límites y permisos."><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="https://www.elfisiologico.com/instrumentos/">
<link rel="icon" href="../assets/logo-fisiologico-cuadrado.png"><link rel="stylesheet" href="../styles.css?v={STYLE_VERSION}"><link rel="stylesheet" href="instruments.css?v=6"><meta name="theme-color" content="#000000">
<meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="Instrumentos clínicos de fisioterapia"><meta property="og:description" content="Qué mide cada instrumento, cómo se puntúa, cuándo utilizarlo y dónde terminan sus conclusiones."><meta property="og:url" content="https://www.elfisiologico.com/instrumentos/"><meta property="og:type" content="website"><meta property="og:image" content="https://www.elfisiologico.com/assets/logo-fisiologico-cuadrado.png">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head>
<body class="editorial-page instruments-page"><a class="skip-link" href="#contenido">Saltar al contenido</a>
<header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="../" aria-label="FisioLógico, inicio">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="../patients/">Pacientes</a><a href="../profesionales/" aria-current="page">Profesionales</a><a href="../con-logica/">Con lógica</a></nav></div></header>
<main id="contenido"><section class="measure-hero"><div class="shell measure-hero-grid"><div class="measure-hero-copy"><p class="section-label light">Medición clínica · colección técnica en crecimiento</p><h1><span>Medir solo sirve</span><span>si ayuda a <em>decidir.</em></span></h1><p>Cuestionarios autoinformados seleccionados por su utilidad en fisioterapia, con puntuación, población, permisos y límites a la vista.</p></div><aside class="measure-thesis"><span>Criterio FisioLógico</span><strong>Menos escalas. Más contexto.</strong><p>No reproducimos cuestionarios sin permiso ni convertimos una puntuación en diagnóstico.</p></aside></div></section>
<nav class="measurement-kinds" aria-label="Tipos de medición"><div class="shell"><a class="is-current" href="./" aria-current="page"><span>Cuestionarios autoinformados</span><strong>{len(instruments)} PROM</strong></a><a href="rendimiento/"><span>Rendimiento físico</span><strong>4 pruebas objetivas →</strong></a><a href="../pruebas-clinicas/"><span>Exploración física</span><strong>Pruebas por sospecha →</strong></a></div></nav>
{builder_html(guidance)}
<section class="measure-finder"><div class="shell"><div class="measure-toolbar">
<label class="search-control">Qué necesitas medir<input type="search" data-instrument-search placeholder="Ej.: función, dolor lumbar, miembro superior…" autocomplete="off"></label>
<label>Constructo<select data-instrument-construct>{option("all", "Todos")}{''.join(option(value, label) for value, label in construct_labels.items())}</select></label>
<label>Región<select data-instrument-region>{option("all", "Todas")}{''.join(option(value, label) for value, label in sorted(region_labels.items(), key=lambda pair: pair[1]))}</select></label>
<label>Finalidad<select data-instrument-purpose>{option("all", "Cualquier finalidad")}{option("valoracion", "Valoración inicial")}{option("seguimiento", "Seguimiento")}{option("objetivos", "Objetivos individuales")}{option("cambio_global", "Cambio global")}</select></label>
<label>Versión española<select data-instrument-validation>{option("all", "Cualquier estado")}{option("validated", "Validada en España")}{option("official", "Versión oficial")}{option("generic", "Aplicación directa")}{option("limited", "Validación limitada")}{option("partial", "Adaptación parcial")}{option("unresolved", "Por documentar")}</select></label>
<label>Permiso<select data-instrument-permission>{option("all", "Cualquier estado")}{option("open", "Uso general")}{option("conditional", "Uso condicionado")}{option("license", "Requiere permiso")}{option("unresolved", "Por verificar")}</select></label>
</div><div class="measure-results-row"><p class="measure-results" aria-live="polite"><strong data-instrument-count>{len(instruments)}</strong> instrumentos · <span data-instrument-summary>Colección revisada</span></p><div class="measure-actions"><button class="filter-reset" type="button" data-filter-reset>Restablecer filtros</button><button class="view-toggle" type="button" data-view-toggle aria-pressed="false">Vista compacta</button><button class="compare-open" type="button" data-compare-open disabled>Comparar <span data-compare-count>0</span></button></div></div>
<div class="measure-grid">{cards}</div><div class="measure-empty" data-instrument-empty hidden><h2>No hay coincidencias</h2><p>Amplía los filtros o consulta las pruebas de exploración física por sospecha clínica.</p></div></div></section>
<section class="compare-panel" data-compare-panel hidden tabindex="-1" aria-labelledby="compare-title"><div class="shell"><div class="compare-heading"><div><p class="section-label">Comparación técnica</p><h2 id="compare-title">Lo comparable, sin perder el contexto.</h2></div><button type="button" data-compare-clear>Limpiar selección</button></div><p class="compare-swipe">Desliza lateralmente para ver toda la comparación →</p><div class="compare-scroll"><table data-compare-table><caption>Comparación de instrumentos seleccionados</caption></table></div><p class="compare-note">La validación y los valores de cambio pertenecen a poblaciones y métodos concretos. Consulta cada ficha antes de trasladarlos.</p></div></section>
<section class="selection-guide"><div class="shell"><div class="selection-guide-heading"><p class="section-label">Elegir con intención</p><h2>La pregunta clínica decide la medida.</h2></div><div class="selection-guide-grid"><article><strong>Intensidad del dolor</strong><h3>END</h3><p>Cuando necesitas una cifra breve con periodo y anclajes definidos.</p></article><article><strong>Objetivo individual</strong><h3>PSFS</h3><p>Cuando importa una actividad elegida por la persona.</p></article><article><strong>Cambio percibido</strong><h3>PGIC</h3><p>Cuando quieres añadir la perspectiva global en el seguimiento.</p></article><article><strong>Discapacidad regional</strong><h3>ODI o NDI</h3><p>Cuando necesitas una medida estandarizada lumbar o cervical.</p></article><article><strong>Función de una extremidad</strong><h3>QuickDASH o LEFS</h3><p>Cuando buscas una visión transversal del miembro superior o inferior.</p></article><article><strong>Exploración física</strong><h3>No es un PROM</h3><p><a href="../pruebas-clinicas/">Consulta pruebas por sospecha clínica →</a></p></article></div></div></section>
<section class="domain-completion"><div class="shell"><div class="selection-guide-heading"><p class="section-label">Dominios transversales</p><h2>Completa la batería solo cuando cambie una decisión.</h2></div><div class="domain-completion-grid"><article><strong>Calidad de vida</strong><h3>EQ-5D-5L</h3><p>Perspectiva genérica de salud y comparación entre problemas distintos.</p></article><article><strong>Participación</strong><h3>WHODAS 2.0</h3><p>Perfil CIF con dominio específico en la versión de 36 ítems.</p></article><article><strong>Sueño</strong><h3>PROMIS-SD 8a</h3><p>Alteración percibida del sueño en métrica T-score.</p></article><article><strong>Autoeficacia</strong><h3>PSEQ-10</h3><p>Confianza para actuar y participar pese al dolor.</p></article></div></div></section>
{joint_reading_html(guidance)}
{cases_html(guidance)}
{maintenance_index_html(guidance)}
<section class="measure-principles"><div class="shell measure-principles-grid"><h2>Qué exigimos antes de incorporar una medida.</h2><ol><li><span>Responde a una necesidad clínica real en fisioterapia.</span></li><li><span>La versión española y su población pueden identificarse.</span></li><li><span>La interpretación no se separa del error de medida ni del contexto.</span></li><li><span>Los derechos de reproducción y uso digital aparecen explícitos.</span></li></ol></div></section></main>
<footer class="site-footer"><div class="shell editorial-footer"><p>© <span data-current-year>2026</span> FisioLógico · Información profesional, no valoración individual.</p><div><a href="../metodo-editorial/">Método editorial</a> <a href="../sobre-fran/">Sobre Fran</a></div></div></footer>
<script src="instruments.js?v=4" defer></script><script src="../script.js?v=6" defer></script></body></html>'''
    OUTPUT.write_text(html_page, encoding="utf-8")
    for instrument in instruments:
        if instrument.get("generated_detail"):
            detail_dir = ROOT / "instrumentos" / instrument["slug"]
            detail_dir.mkdir(parents=True, exist_ok=True)
            (detail_dir / "index.html").write_text(generated_detail_page(instrument), encoding="utf-8")
        else:
            sync_existing_detail(instrument)
    build_performance()
    sync_navigation()
    print(f"Generados catálogos desde {DATA.relative_to(ROOT)} y {PERFORMANCE_DATA.relative_to(ROOT)} ({len(instruments)} autoinformes y 4 pruebas de rendimiento).")


if __name__ == "__main__":
    build()
