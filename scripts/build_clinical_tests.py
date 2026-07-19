#!/usr/bin/env python3
"""Materializa la colección clínica canónica en HTML accesible sin JavaScript."""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

from sync_navigation import sync_navigation

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "clinical-tests.json"
INDEX = ROOT / "pruebas-clinicas" / "index.html"
BASE_URL = "https://www.elfisiologico.com/pruebas-clinicas"
SITEMAP = ROOT / "sitemap.xml"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def region_key(value: str) -> str:
    plain = unicodedata.normalize("NFD", value)
    plain = "".join(character for character in plain if unicodedata.category(character) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def search_terms(item: dict) -> str:
    values = [item["name"], item["short_name"], item["region"], item["purpose"], item["summary"]]
    for test in item["tests"]:
        values.extend((test["name"], test["role"], test["direction"]))
    return " ".join(values)


def card_html(item: dict) -> str:
    tests = "".join(
        f'<span>{esc(test["name"])} <b>{esc(test["role"])}</b></span>'
        for test in item["tests"][:3]
    )
    return (
        f'<article class="suspicion-card" data-suspicion-card data-region="{region_key(item["region"])}" '
        f'data-search="{esc(search_terms(item))}">'
        f'<div class="suspicion-meta"><span>{esc(item["region"])}</span><span>{esc(item["purpose"])}</span></div>'
        f'<h2><a href="{esc(item["slug"])}/">{esc(item["name"])}</a></h2>'
        f'<p>{esc(item["summary"])}</p><div class="test-stack">{tests}</div>'
        f'<a href="{esc(item["slug"])}/">Abrir recorrido clínico →</a></article>'
    )


def diagnostic_html(test: dict) -> str:
    metrics = test["metrics"]
    source = metrics["source"]
    return (
        '<!-- clinical-data:start -->'
        '<div class="test-procedure">'
        f'<div><span>Resumen de ejecución</span><p>{esc(test["execution"])}</p></div>'
        f'<div><span>Qué observar</span><p>{esc(test["positive"])}</p></div></div>'
        f'<div class="diagnostic-metrics" data-status="{esc(metrics["status"])}">'
        '<div class="metrics-heading"><span>Rendimiento diagnóstico</span>'
        f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">Fuente PMID {esc(source["pmid"])} ↗︎</a></div>'
        '<dl>'
        f'<div><dt>Sensibilidad</dt><dd>{esc(metrics["sensitivity"])}</dd></div>'
        f'<div><dt>Especificidad</dt><dd>{esc(metrics["specificity"])}</dd></div>'
        f'<div><dt>LR+</dt><dd>{esc(metrics["lr_positive"])}</dd></div>'
        f'<div><dt>LR−</dt><dd>{esc(metrics["lr_negative"])}</dd></div>'
        f'</dl><p>{esc(metrics["context"])}</p></div>'
        f'<p class="test-caution"><strong>Límite clínico:</strong> {esc(test["note"])}</p>'
        '<!-- clinical-data:end -->'
    )


def detail_sources(item: dict) -> dict[str, str]:
    sources = {item["primary_source"]["pmid"]: item["primary_source"]["url"]}
    for test in item["tests"]:
        source = test["metrics"]["source"]
        sources[source["pmid"]] = source["url"]
    return sources


def detail_structured_data(item: dict, title: str, description: str) -> str:
    url = f'{BASE_URL}/{item["slug"]}/'
    sources = detail_sources(item)
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "MedicalWebPage",
                "@id": f"{url}#webpage",
                "name": title,
                "description": description,
                "url": url,
                "dateModified": "2026-07-14",
                "lastReviewed": "2026-07-14",
                "inLanguage": "es",
                "isAccessibleForFree": True,
                "audience": {"@type": "MedicalAudience", "audienceType": "Fisioterapeutas"},
                "author": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"},
                "reviewedBy": {"@id": "https://www.elfisiologico.com/sobre-fran/#person"},
                "publisher": {"@id": "https://www.elfisiologico.com/#organization"},
                "about": {"@type": "MedicalCondition", "name": item["name"]},
                "citation": [
                    {"@type": "ScholarlyArticle", "identifier": f"PMID:{pmid}", "url": source_url}
                    for pmid, source_url in sources.items()
                ],
                "isPartOf": {"@id": "https://www.elfisiologico.com/#website"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Pruebas clínicas",
                        "item": f"{BASE_URL}/",
                    },
                    {"@type": "ListItem", "position": 2, "name": item["name"], "item": url},
                ],
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def detail_page_html(item: dict) -> str:
    title = f'Pruebas para {item["name"].lower()}'
    description = f'{item["summary"][:145].rstrip(" .")}.'.replace('"', '')
    cards = "".join(
        '<article class="clinical-test" data-evidence="' + esc(test["evidence"]) + '">'
        '<div class="clinical-test-head"><h3>' + esc(test["name"]) + '</h3>'
        '<span class="clinical-role">' + esc(test["role"]) + '</span></div>'
        '<p class="clinical-direction">' + esc(test["direction"]) + '.</p></article>'
        for test in item["tests"]
    )
    sources = detail_sources(item)
    source_items = "".join(
        f'<li><a href="{esc(url)}" target="_blank" rel="noopener">Fuente diagnóstica verificada · PMID {esc(pmid)}</a></li>'
        for pmid, url in sources.items()
    )
    structured = detail_structured_data(item, title, description)
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(title)} · FisioLógico</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
        f'<link rel="canonical" href="{BASE_URL}/{esc(item["slug"])}/"><link rel="icon" href="../../assets/logo-fisiologico-cuadrado.png">'
        '<link rel="stylesheet" href="../../styles.css?v=6"><link rel="stylesheet" href="../clinical-tests.css?v=1"><link rel="stylesheet" href="../clinical-test-procedure.css?v=2">'
        f'<meta property="og:type" content="article"><meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(item["summary"])}"><meta property="og:image" content="https://www.elfisiologico.com/assets/logo-fisiologico-cuadrado.png">'
        f'<script type="application/ld+json">{structured}</script></head><body class="editorial-page clinical-page"><a class="skip-link" href="#contenido">Saltar al contenido</a>'
        '<header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="../../">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="../../patients/">Pacientes</a><a href="../../profesionales/" aria-current="page">Profesionales</a><a href="../../con-logica/">Con lógica</a></nav></div></header><main id="contenido">'
        f'<section class="clinical-detail-hero"><div class="shell"><p class="clinical-breadcrumbs"><a href="../">Pruebas clínicas</a> / {esc(item["region"])}</p><h1>Sospecha de {esc(item["name"].lower())}</h1><p class="clinical-lead">{esc(item["summary"])}</p><div class="clinical-status"><span>{esc(item["region"])}</span><span>{esc(item["evidence_status"])}</span><span>Revisión científica</span></div></div></section>'
        '<div class="clinical-flow"><div class="shell"><div class="flow-step"><span>Empieza</span><strong>Historia y seguridad</strong></div><div class="flow-step"><span>Selecciona</span><strong>Prueba y función</strong></div><div class="flow-step"><span>Interpreta</span><strong>Cambio de probabilidad</strong></div><div class="flow-step"><span>Decide</span><strong>Siguiente paso</strong></div></div></div>'
        '<div class="shell clinical-detail"><aside class="clinical-rail"><p>En esta ficha</p><nav><a href="#pregunta">Pregunta</a><a href="#seleccion">Selección</a><a href="#interpretacion">Interpretación</a><a href="#limites">Límites</a><a href="#fuentes">Fuentes</a></nav></aside><article class="clinical-copy">'
        f'<section id="pregunta"><p class="section-label">Pregunta clínica</p><h2>¿La exploración modifica la sospecha de {esc(item["short_name"].lower())}?</h2><p>La probabilidad previa nace del mecanismo, la evolución y el examen básico. Cada componente se elige por su función y solo se interpreta en la población y con la técnica descritas.</p><div class="reasoning-strip"><div><span>Primero</span><strong>Seguridad</strong></div><div><span>Después</span><strong>Hallazgo concordante</strong></div><div><span>Final</span><strong>Decisión clínica</strong></div></div></section>'
        f'<section id="seleccion"><p class="section-label">Selección razonada</p><h2>Componentes que responden a funciones diferentes.</h2><div class="clinical-test-list">{cards}</div></section>'
        f'<section id="interpretacion"><p class="section-label">Interpretación</p><h2>El resultado modifica una hipótesis; no la sustituye.</h2><p>{esc(item["summary"])}</p></section>'
        '<section id="limites" class="clinical-warning"><h2>Las cifras no viajan solas.</h2><p>Sensibilidad, especificidad y cocientes de probabilidad pertenecen a una población, una variante técnica y un patrón de referencia. Un resultado aislado no autoriza diagnóstico ni tratamiento sin integración clínica.</p></section>'
        f'<section id="fuentes"><p class="section-label">Fuentes verificadas</p><h2>Literatura diagnóstica utilizada</h2><ul class="clinical-sources">{source_items}</ul></section>'
        '<section class="editorial-responsibility" aria-labelledby="responsabilidad-editorial"><p class="responsibility-label">Responsabilidad editorial</p><div class="responsibility-grid"><div><h2 id="responsabilidad-editorial"><a href="../../sobre-fran/">Francisco José Extremera García</a></h2><p class="responsibility-credentials">Fisioterapeuta colegiado ICPFA 4288 · Osteópata D.O.</p><p>Creador y responsable editorial de FisioLógico</p></div><dl><div><dt>Última revisión</dt><dd><time datetime="2026-07-14">14 de julio de 2026</time></dd></div><div><dt>Conflictos de interés</dt><dd>Ninguno declarado.</dd></div></dl></div><a class="responsibility-method" href="../../metodo-editorial/">Cómo revisamos el contenido →</a></section>'
        '</article></div></main><footer class="site-footer"><div class="shell editorial-footer"><p>© <span data-current-year>2026</span> FisioLógico</p><a href="../">Volver a pruebas clínicas</a></div></footer><script src="../../script.js?v=6" defer></script></body></html>'
    )


def update_collection(published: list[dict]) -> None:
    source = INDEX.read_text(encoding="utf-8")
    region_links = (
        '<a href="#explorador" data-region-link="columna-cervical">Cervical</a><a href="#explorador" data-region-link="columna-lumbar">Lumbar</a>'
        '<a href="#explorador" data-region-link="hombro">Hombro</a><a href="#explorador" data-region-link="codo">Codo</a>'
        '<a href="#explorador" data-region-link="muneca-y-mano">Muñeca y mano</a><a href="#explorador" data-region-link="cadera">Cadera</a>'
        '<a href="#explorador" data-region-link="rodilla">Rodilla</a><a href="#explorador" data-region-link="tobillo-y-pie">Tobillo y pie</a>'
        '<a href="#explorador" data-region-link="sistema-nervioso-periferico">Nervios periféricos</a><a href="#explorador" data-region-link="cribado-vascular">Cribado vascular</a>'
    )
    map_hotspots = (
        '<a class="map-hotspot map-cervical" href="#explorador" data-region-link="columna-cervical">Cervical</a>'
        '<a class="map-hotspot map-shoulder" href="#explorador" data-region-link="hombro">Hombro</a>'
        '<a class="map-hotspot map-elbow" href="#explorador" data-region-link="codo">Codo</a>'
        '<a class="map-hotspot map-hand" href="#explorador" data-region-link="muneca-y-mano">Muñeca y mano</a>'
        '<a class="map-hotspot map-lumbar" href="#explorador" data-region-link="columna-lumbar">Lumbar</a>'
        '<a class="map-hotspot map-hip" href="#explorador" data-region-link="cadera">Cadera</a>'
        '<a class="map-hotspot map-knee" href="#explorador" data-region-link="rodilla">Rodilla</a>'
        '<a class="map-hotspot map-ankle" href="#explorador" data-region-link="tobillo-y-pie">Tobillo y pie</a>'
    )
    region_overview = (
        '<section class="clinical-region-overview" aria-labelledby="regiones-clinicas"><div class="shell clinical-region-layout">'
        '<div class="clinical-region-copy"><p class="section-label">Navegación anatómica</p><h2 id="regiones-clinicas">Selecciona una región para filtrar las pruebas.</h2>'
        '<p>Pulsa directamente sobre la lámina o utiliza la lista. El buscador permite localizar patologías, maniobras y funciones clínicas.</p>'
        f'<nav class="clinical-region-links" aria-label="Filtrar pruebas por región">{region_links}</nav></div>'
        '<figure class="clinical-anatomy-map"><img src="../patients/explora-dolor/assets/body-anatomy-v1.webp?v=17" width="1369" height="1149" alt="" loading="eager">'
        f'<span class="clinical-map-instruction">Elige una región</span>{map_hotspots}</figure></div></section>'
    )
    if "clinical-region-overview" not in source:
        source = source.replace('<section class="clinical-finder">', region_overview + '<section class="clinical-finder" id="explorador">', 1)
    else:
        source = re.sub(r'<section class="clinical-region-overview".*?</section>', region_overview, source, count=1, flags=re.DOTALL)
    source = source.replace(
        '../assets/pruebas-clinicas-regiones.jpg" width="1672" height="941" alt="Vista frontal y posterior de una figura vestida con las regiones clínicas destacadas"',
        '../patients/explora-dolor/assets/body-anatomy-v1.webp?v=17" width="1369" height="1149" alt="Vista anatómica anterior y posterior del cuerpo"',
    )
    source = source.replace(
        "Mapa visual de acceso. Las áreas coloreadas no representan un diagnóstico ni la localización exacta del dolor.",
        "La misma lámina anatómica del selector para pacientes, reutilizada como acceso visual coherente entre secciones.",
    )
    cards = "".join(card_html(item) for item in published)
    source, count = re.subn(
        r'<div class="clinical-grid">.*?</div><div class="clinical-empty"',
        f'<div class="clinical-grid">{cards}</div><div class="clinical-empty"',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("No se pudo reconstruir la cuadrícula clínica")
    regions = sorted({item["region"] for item in published}, key=region_key)
    options = '<option value="all">Todas</option>' + "".join(
        f'<option value="{region_key(label)}">{esc(label)}</option>' for label in regions
    )
    source, count = re.subn(
        r'(<select data-clinical-region>).*?(</select>)',
        rf'\1{options}\2',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("No se pudo actualizar el selector regional")
    source = re.sub(
        r'<p class="clinical-results"[^>]*>.*?</p>',
        f'<p class="clinical-results" aria-live="polite"><strong data-clinical-count>{len(published)}</strong> sospechas clínicas revisadas</p>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace("Exploración física · colección piloto", "Exploración física · colección clínica")
    source = source.replace("No hay coincidencias en el piloto", "No hay coincidencias en la colección")
    source = source.replace("La colección crecerá tras revisión metodológica.", "Prueba otra región, patología o nombre de maniobra.")
    source = source.replace(
        "Prueba otra región o una sospecha más amplia. Prueba otra región, patología o nombre de maniobra.",
        "Prueba otra región, patología o nombre de maniobra.",
    )
    item_list = {
        "@type": "ItemList",
        "numberOfItems": len(published),
        "itemListElement": [
            {"@type": "ListItem", "position": index, "url": f"{BASE_URL}/{item['slug']}/"}
            for index, item in enumerate(published, 1)
        ],
    }

    def replace_json_ld(match: re.Match[str]) -> str:
        payload = json.loads(match.group(1))
        if payload.get("@type") == "CollectionPage":
            payload["mainEntity"] = item_list
        return '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "</script>"

    source = re.sub(r'<script type="application/ld\+json">(.*?)</script>', replace_json_ld, source, flags=re.DOTALL)
    source = source.replace('clinical-tests.js?v=1', 'clinical-tests.js?v=2')
    INDEX.write_text(source, encoding="utf-8")


def update_detail(item: dict) -> None:
    path = ROOT / "pruebas-clinicas" / item["slug"] / "index.html"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(detail_page_html(item), encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    title_match = re.search(r"<title>(.*?) · FisioLógico</title>", source, flags=re.DOTALL)
    description_match = re.search(r'<meta name="description" content="([^"]+)">', source)
    title = html.unescape(title_match.group(1)) if title_match else f'Pruebas para {item["name"].lower()}'
    description = html.unescape(description_match.group(1)) if description_match else item["summary"]
    structured = detail_structured_data(item, title, description)
    source, schema_count = re.subn(
        r'<script type="application/ld\+json">.*?</script>',
        f'<script type="application/ld+json">{structured}</script>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if schema_count != 1:
        raise RuntimeError(f"No se pudo actualizar JSON-LD en {path.relative_to(ROOT)}")
    source = re.sub(
        r'<meta name="robots" content="[^"]+">',
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">',
        source,
        count=1,
    )
    if "clinical-test-procedure.css" not in source:
        source = source.replace(
            '<link rel="stylesheet" href="../clinical-tests.css?v=1">',
            '<link rel="stylesheet" href="../clinical-tests.css?v=1"><link rel="stylesheet" href="../clinical-test-procedure.css?v=2">',
            1,
        )
    for test in item["tests"]:
        name = re.escape(html.escape(test["name"], quote=False))
        pattern = re.compile(
            rf'(<article class="clinical-test"[^>]*>.*?<h3>{name}</h3>.*?<p class="clinical-direction">.*?</p>)(.*?)(</article>)',
            re.DOTALL,
        )
        match = pattern.search(source)
        if not match:
            raise RuntimeError(f'No se encontró "{test["name"]}" en {path.relative_to(ROOT)}')
        middle = re.sub(r'<!-- clinical-data:start -->.*?<!-- clinical-data:end -->', "", match.group(2), flags=re.DOTALL)
        middle = middle.replace(f'<p>{esc(test["note"])}</p>', "", 1)
        replacement = match.group(1) + diagnostic_html(test) + middle + match.group(3)
        source = source[: match.start()] + replacement + source[match.end() :]
    source = source.replace('clinical-tests.js?v=1', 'clinical-tests.js?v=2')
    path.write_text(source, encoding="utf-8")


def update_sitemap(published: list[dict]) -> None:
    source = SITEMAP.read_text(encoding="utf-8")
    missing = "".join(
        f'  <url><loc>{BASE_URL}/{item["slug"]}/</loc><lastmod>2026-07-14</lastmod></url>\n'
        for item in published if f'{BASE_URL}/{item["slug"]}/' not in source
    )
    if missing:
        source = source.replace("</urlset>", missing + "</urlset>")
        SITEMAP.write_text(source, encoding="utf-8")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    published = [item for item in data["suspicions"] if item["editorial_status"] == "published"]
    update_collection(published)
    for item in published:
        update_detail(item)
    update_sitemap(published)
    sync_navigation()
    print(f"Materializadas {len(published)} sospechas y {sum(len(item['tests']) for item in published)} componentes.")


if __name__ == "__main__":
    main()
