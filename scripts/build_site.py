#!/usr/bin/env python3
"""Genera el repositorio científico, SEO y redirecciones históricas."""
from __future__ import annotations

import html
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from sync_navigation import sync_navigation

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
OUTPUT = ROOT / "repositorio"
PDF_ARCHIVE = ROOT / "fuentes-pdf-repositorio" / "pdfs-originales"
OG_IMAGE = "/assets/logo-fisiologico-cuadrado.png"


def stylesheet_version():
    """Invalida la caché siempre que cambie la hoja de estilos canónica."""
    return hashlib.sha256((ROOT / "styles.css").read_bytes()).hexdigest()[:10]


STYLE_VERSION = stylesheet_version()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value):
    return html.escape(str(value), quote=True)


def meta_description(text, limit=160):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    shortened = text[: limit - 1].rsplit(" ", 1)[0]
    return f"{shortened}…"


def meta_title(text, limit=58):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rsplit(' ', 1)[0]}…"


def date_es(value):
    """Presenta una fecha ISO con formato editorial español."""
    months = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    year, month, day = (int(part) for part in value.split("-"))
    return f"{day} de {months[month - 1]} de {year}"


def public_score(article):
    """Devuelve solo el total publicable; la evaluación detallada permanece interna."""
    current = article.get("rubric_v2", {})
    if current.get("status") == "complete":
        return current["total"]
    return article["score"]


def design_group(article):
    design = article["study_design"].lower()
    if "meta" in design or "systematic" in design or "sistemática" in design:
        return "synthesis", "Revisión sistemática"
    if "no aleator" in design or "nonrandom" in design or "no random" in design:
        return "observational", "Estudio no aleatorizado"
    if "random" in design or "aleator" in design:
        return "randomized", "Ensayo aleatorizado"
    if "observ" in design or "transversal" in design or "cohort" in design or "casos y controles" in design or "registro" in design:
        return "observational", "Estudio observacional"
    if "narrativ" in design or "review" in design or "revisión" in design or "scoping" in design:
        return "review", "Revisión"
    if "animal" in design or "experimental" in design or "in silico" in design:
        return "experimental", "Estudio experimental"
    return "other", "Otros diseños"


def public_outcome(article):
    current = article.get("rubric_v2", {})
    return current.get("primary_outcome") or "Afirmación clínica principal del estudio"


def search_text(article):
    current = article.get("rubric_v2", {})
    parts = [article["title"], article["title_es"], article["category_name"], article["study_design"], article["population"], article["clinical_takeaway"], article["source"]["pmid"], article["source"].get("doi", ""), current.get("primary_outcome", ""), current.get("target_claim", "")]
    return " ".join(str(part) for part in parts if part).lower()


def is_editorially_complete(article):
    """Publica solo evaluaciones v2 cerradas; nunca estados provisionales."""
    return article.get("rubric_v2", {}).get("status") == "complete"


def editorial_responsibility(site, updated_at, conflicts, depth="../../"):
    """Firma editorial pública y canónica para todo contenido científico generado."""
    editorial = site["editorial"]
    legacy_conflicts = {"No declarados por el revisor.", "Sin conflictos de interés declarados."}
    conflict_text = editorial["conflicts"] if not conflicts or conflicts in legacy_conflicts else conflicts
    return f'''<section class="editorial-responsibility" aria-labelledby="responsabilidad-editorial"><p class="responsibility-label">{esc(editorial["label"])}</p><div class="responsibility-grid"><div><h2 id="responsabilidad-editorial"><a href="{depth}sobre-fran/">{esc(site["author"]["name"])}</a></h2><p class="responsibility-credentials">{esc(editorial["credential_line"])}</p><p>{esc(editorial["role"])}</p></div><dl><div><dt>Última revisión</dt><dd><time datetime="{esc(updated_at)}">{esc(date_es(updated_at))}</time></dd></div><div><dt>Conflictos de interés</dt><dd>{esc(conflict_text)}</dd></div></dl></div><a class="responsibility-method" href="{depth}metodo-editorial/">Cómo revisamos el contenido →</a></section>'''


def layout(title, description, canonical_path, body, depth="../", structured_data=None, page_type="website", robots="index,follow,max-image-preview:large"):
    site = load(ROOT / "data/site.json")
    canonical = f"{site['domain']}{canonical_path}"
    title = meta_title(title)
    description = meta_description(description)
    structured = ""
    if structured_data:
        structured = f'<script type="application/ld+json">{json.dumps(structured_data, ensure_ascii=False)}</script>'
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · FisioLógico</title><meta name="description" content="{esc(description)}"><meta name="robots" content="{esc(robots)}">
<link rel="canonical" href="{esc(canonical)}"><link rel="icon" href="{depth}assets/logo-fisiologico-cuadrado.png"><link rel="stylesheet" href="{depth}styles.css?v={STYLE_VERSION}">
<meta name="theme-color" content="#070707"><meta property="og:locale" content="es_ES"><meta property="og:site_name" content="FisioLógico"><meta property="og:title" content="{esc(title)} · FisioLógico">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:type" content="{esc(page_type)}"><meta property="og:image" content="{esc(site['domain'] + OG_IMAGE)}"><meta property="og:image:alt" content="Identidad visual de FisioLógico"><meta name="twitter:card" content="summary_large_image">{structured}</head>
<body class="editorial-page"><a class="skip-link" href="#contenido">Saltar al contenido</a>
<header class="editorial-header"><div class="shell editorial-nav"><a class="editorial-brand" href="{depth}index.html" aria-label="FisioLógico, inicio">Fisio<span>Lógico</span></a><nav aria-label="Principal"><a href="{depth}patients/">Pacientes</a><a href="{depth}profesionales/">Profesionales</a><a href="{depth}con-logica/">Con lógica</a></nav></div></header>
<main id="contenido">{body}</main><footer class="site-footer"><div class="shell editorial-footer"><p>FisioLógico · evidencia, criterio y transferencia clínica.</p><div><a href="{depth}sobre-fran/">Autor</a><a href="{depth}metodo-editorial/">Criterio editorial</a><a href="mailto:{esc(site['email'])}">Contacto</a></div></div></footer></body></html>'''


def card(a, href_prefix="articulos/"):
    score = public_score(a)
    design_key, design_label = design_group(a)
    editorial_card = a.get("card", {})
    if editorial_card:
        insight = f'''<div class="card-insight"><span>Pregunta que responde</span><p>{esc(editorial_card["question"])}</p><strong>{esc(editorial_card["answer"])}</strong><small>{esc(editorial_card["key_data"])}</small></div>'''
    else:
        insight = f'<p>{esc(a["clinical_takeaway"])}</p>'
    return f'''<article class="evidence-card" data-year="{a['year']}" data-score="{score}" data-category="{esc(a['category'])}" data-design="{design_key}" data-search="{esc(search_text(a))}">
<div class="evidence-meta"><span>{esc(a['category_name'])}</span><span>{a['year']}</span><strong title="Puntuación editorial de FisioLógico">Índice {score}/30</strong></div>
<h2><a href="{href_prefix}{esc(a['slug'])}.html">{esc(a['title_es'])}</a></h2><p class="original-title" lang="en">{esc(a['title'])}</p>{insight}
<dl class="quick-facts"><div><dt>Diseño</dt><dd>{esc(design_label)}</dd></div><div><dt>Límite</dt><dd>{esc(a['limitations'][0])}</dd></div></dl>
<div class="card-source"><a href="{href_prefix}{esc(a['slug'])}.html">Abrir análisis →</a><a href="{esc(a['source']['pubmed_url'])}" target="_blank" rel="noopener noreferrer" aria-label="Abrir registro original en PubMed">PubMed · {esc(a['source']['pmid'])}</a></div></article>'''


def build_index(articles, categories, curation):
    counts = Counter(a["category"] for a in articles)
    active = [c for c in categories if counts[c["slug"]]]
    cats = "".join(f'<option value="{esc(c["slug"])}">{esc(c["name"])} ({counts[c["slug"]]})</option>' for c in active)
    design_counts = Counter(design_group(a)[0] for a in articles)
    design_order = [("synthesis", "Revisión sistemática"), ("randomized", "Ensayo aleatorizado"), ("observational", "Estudio observacional"), ("review", "Revisión"), ("experimental", "Estudio experimental"), ("other", "Otros diseños")]
    designs = "".join(f'<option value="{key}">{label} ({design_counts[key]})</option>' for key, label in design_order if design_counts[key])
    years = "".join(f'<option value="{year}">{year}</option>' for year in sorted({a["year"] for a in articles}, reverse=True))
    cards = "".join(card(a) for a in sorted(articles, key=lambda x: (-x["year"], x["title_es"])))
    by_slug = {a["slug"]: a for a in articles}
    featured = [by_slug[slug] for slug in curation["featured"] if slug in by_slug]
    featured_html = "".join(f'<article class="featured-card"><p>{esc(a["category_name"])} · {esc(a["study_design"])}</p><h3><a href="articulos/{esc(a["slug"])}.html">{esc(a["title_es"])}</a></h3><small class="original-title" lang="en">{esc(a["title"])}</small><span>Índice editorial · {public_score(a)}/30</span></article>' for a in featured)
    featured_section = f'<section class="featured-section"><div class="shell"><div class="featured-heading"><p class="section-label">Lecturas esenciales</p><h2>Selección para orientarse.</h2><p>Estudios útiles para comprender resultados, límites y transferencia clínica sin convertir la evidencia en una receta.</p></div><div class="featured-grid">{featured_html}</div></div></section>' if featured else ""
    active_journeys = [j for j in curation["journeys"] if journey_articles(j, articles)]
    journeys_html = "".join(f'<a class="journey-card" href="recorridos/{esc(j["slug"])}.html"><span>Pregunta clínica</span><h3>{esc(j["question"])}</h3><p>{esc(j["description"])}</p><strong>Explorar recorrido →</strong></a>' for j in active_journeys)
    body = f'''<section class="repository-hero"><div class="shell repository-hero-grid"><div><p class="section-label light">Repositorio científico · {len(articles)} análisis</p><h1>Evidencia para<br><em>decidir mejor.</em></h1><p>Localiza un estudio, comprueba qué observó y detecta dónde terminan sus conclusiones.</p></div><aside class="method-note" aria-label="Criterio editorial"><span>Criterio editorial propio</span><strong>Índice /30 · fuente original · límites</strong><p>La puntuación resume una evaluación interna; no sustituye el análisis ni expresa por sí sola certeza científica.</p><a href="#criterios">Cómo interpretar una ficha ↓</a></aside></div></section>
<section class="evidence-section evidence-first"><div class="shell"><div class="evidence-toolbar"><div><p class="section-label">Buscar evidencia</p><p class="results-count" aria-live="polite"><strong data-results-count>{len(articles)}</strong> análisis disponibles</p></div><div class="evidence-controls"><label class="search-control">Pregunta, técnica, outcome o PMID <input type="search" data-filter-search placeholder="Ej.: dolor lumbar, ejercicio, función…" autocomplete="off"></label><label>Área clínica <select data-filter-category><option value="all">Todas ({len(articles)})</option>{cats}</select></label><label>Diseño <select data-filter-design><option value="all">Todos</option>{designs}</select></label><label>Año <select data-filter-year><option value="all">Todos</option>{years}</select></label><label>Ordenar <select data-sort><option value="newest">Más recientes</option><option value="score">Mayor puntuación</option><option value="title">Título A–Z</option></select></label></div></div><div class="active-filters" data-active-filters aria-live="polite"></div><div class="evidence-grid" data-evidence-grid>{cards}</div><div class="empty-state" data-empty-state hidden><h2>No hay análisis con estos criterios</h2><p>Prueba otra área, diseño o año, o elimina la búsqueda.</p><button class="button button-dark" type="button" data-clear-filters>Limpiar filtros</button></div></div></section>
<section class="journeys-section"><div class="shell"><div class="journeys-heading"><p class="section-label">Recorridos clínicos</p><h2>Empieza por una pregunta, no por una técnica.</h2></div><div class="journeys-grid">{journeys_html}</div></div></section>{featured_section}
<section class="criteria" id="criterios"><div class="shell criteria-grid"><div><p class="section-label light">Cómo leer el repositorio</p><h2>Una ayuda para razonar,<br>no un veredicto.</h2><a class="text-link" href="../metodo-editorial/">Conoce nuestro compromiso editorial →</a></div><div class="tier-list"><p><strong>Índice editorial</strong><span>El total sobre 30 resume una evaluación interna de FisioLógico. Ayuda a comparar análisis, pero no sustituye la lectura crítica ni expresa por sí solo certeza científica.</span></p><p><strong>Resultado observado</strong><span>Qué encontró realmente el estudio en la población y el tiempo evaluados.</span></p><p><strong>Límites</strong><span>Qué incertidumbres impiden ampliar o simplificar sus conclusiones.</span></p><p><strong>Transferencia</strong><span>Qué puede aportar al razonamiento clínico sin convertirlo en una receta.</span></p><p><strong>Fuente primaria</strong><span>Acceso directo a PubMed y al artículo original para contrastar el análisis.</span></p></div></div></section><script src="../script.js" defer></script>'''
    structured = {"@context":"https://schema.org","@type":"CollectionPage","name":"Repositorio científico de FisioLógico","description":"Análisis metodológico de estudios de fisioterapia con resultados, límites y transferencia clínica.","url":"https://www.elfisiologico.com/repositorio/","author":{"@id":"https://www.elfisiologico.com/sobre-fran/#person"},"isPartOf":{"@type":"WebSite","name":"FisioLógico","url":"https://www.elfisiologico.com/"},"mainEntity":{"@type":"ItemList","numberOfItems":len(articles),"itemListElement":[{"@type":"ListItem","position":position,"url":f"https://www.elfisiologico.com/repositorio/articulos/{article['slug']}.html","name":article["title_es"]} for position, article in enumerate(articles, 1)]}}
    (OUTPUT / "index.html").write_text(layout("Repositorio científico", "Análisis metodológico de estudios de fisioterapia con resultados, límites y transferencia clínica para profesionales sanitarios.", "/repositorio/", body, "../", structured), encoding="utf-8")


def paragraphs(items):
    return "".join(f"<p>{esc(item)}</p>" for item in items)


def intervention_protocol(a):
    protocol = a.get("intervention_protocol")
    if not protocol:
        return "", ""
    facts = "".join(f'<div><dt>{esc(item["label"])}</dt><dd>{esc(item["value"])}</dd></div>' for item in protocol["facts"])
    groups = []
    for group in protocol["groups"]:
        progression = "".join(
            f'<li><p class="protocol-period">{esc(item["period"])}</p>'
            f'<p class="protocol-exercises">{esc(item["exercises"])}</p></li>'
            for item in group["progression"]
        )
        groups.append(f'<article class="protocol-group"><h3>{esc(group["name"])}</h3><p>{esc(group["description"])}</p><ol>{progression}</ol></article>')
    shared = "".join(f'<li>{esc(item)}</li>' for item in protocol["shared_components"])
    section = f'''<section class="intervention-protocol" id="protocolo"><p class="section-label">Intervención estudiada</p><h2>En qué consistieron los ejercicios</h2><p class="protocol-summary">{esc(protocol["summary"])}</p><dl class="protocol-facts">{facts}</dl><div class="protocol-groups">{"".join(groups)}</div><div class="protocol-shared"><h3>Qué recibieron ambos grupos</h3><ul>{shared}</ul></div><p class="protocol-source-note">{esc(protocol["source_note"])}</p></section>'''
    return '<a href="#protocolo">Ejercicios</a>', section


def measurement_battery(a):
    battery = a.get("measurement_battery")
    if not battery:
        return "", ""
    groups = []
    for group_index, group in enumerate(battery["groups"], 1):
        items = []
        for item in group["items"]:
            internal_link = (
                f'<a class="measurement-link" href="{esc(item["internal_url"])}">Ver ficha del instrumento →</a>'
                if item.get("internal_url") else ""
            )
            items.append(
                f'''<article class="measurement-card"><header><span>{esc(item["short_name"])}</span><h4>{esc(item["name"])}</h4></header>'''
                f'''<dl><div><dt>Qué mide</dt><dd>{esc(item["measures"])}</dd></div><div><dt>En qué consiste</dt><dd>{esc(item["procedure"])}</dd></div>'''
                f'''<div><dt>Cómo se interpreta</dt><dd>{esc(item["scoring"])}</dd></div></dl>'''
                f'''<p class="measurement-caution"><strong>Lectura prudente</strong>{esc(item["clinical_note"])}</p>{internal_link}</article>'''
            )
        groups.append(
            f'''<div class="measurement-group" aria-labelledby="measurement-group-{group_index}"><div class="measurement-group-heading">'''
            f'''<h3 id="measurement-group-{group_index}">{esc(group["name"])}</h3><p>{esc(group["description"])}</p></div>'''
            f'''<div class="measurement-grid">{"".join(items)}</div></div>'''
        )
    section = (
        f'''<section class="measurement-battery" id="mediciones"><p class="section-label">Instrumentos del estudio</p>'''
        f'''<h2>Qué escalas y pruebas utilizaron</h2><p class="measurement-summary">{esc(battery["summary"])}</p>'''
        f'''<div class="measurement-groups">{"".join(groups)}</div><p class="measurement-source-note">{esc(battery["source_note"])}</p></section>'''
    )
    return '<a href="#mediciones">Escalas y pruebas</a>', section


def build_article(a, site, articles):
    score = public_score(a)
    _, design_label = design_group(a)
    outcome = public_outcome(a)
    source_links = f'<a class="source-button primary" href="{esc(a["source"]["original_url"])}" target="_blank" rel="noopener noreferrer">Abrir artículo original</a><a class="source-button" href="{esc(a["source"]["pubmed_url"])}" target="_blank" rel="noopener noreferrer">Ver en PubMed · PMID {esc(a["source"]["pmid"])}</a>'
    canonical_path = f"/repositorio/articulos/{a['slug']}.html"
    author_url = f"{site['domain']}/sobre-fran/"
    related = [item for item in articles if item["category"] == a["category"] and item["slug"] != a["slug"]][:3]
    related_html = "".join(f'<li><a href="{esc(item["slug"])}.html">{esc(item["title_es"])}</a><span>{public_score(item)}/30</span></li>' for item in related)
    related_section = f'<section class="related-articles"><p class="section-label">Sigue explorando</p><h2>Otros análisis sobre {esc(a["category_name"])}</h2><ul>{related_html}</ul><a href="../categorias/{esc(a["category"])}.html">Explorar evidencia sobre {esc(a["category_name"])} →</a></section>' if related else ""
    article_json = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "@id": f"{site['domain']}{canonical_path}#article", "headline": a["title_es"], "alternateName": a["title"], "description": meta_description(a.get("seo",{}).get("description", a["clinical_takeaway"])), "datePublished": a["review"]["published_at"], "dateModified": a["review"]["updated_at"], "inLanguage": "es", "isAccessibleForFree": True, "educationalLevel": "Profesional sanitario", "about": [{"@type":"Thing","name":a["category_name"]},{"@type":"Thing","name":a["study_design"]},{"@type":"Thing","name":outcome}], "keywords": [a["category_name"], a["study_design"], outcome, "fisioterapia", "lectura crítica"], "author": {"@type": "Person", "@id": f"{author_url}#person", "name": site["author"]["name"], "url": author_url}, "reviewedBy": {"@type":"Person","@id":f"{author_url}#person"}, "publisher": {"@type": "Organization", "@id": f"{site['domain']}/#organization", "name": site["brand"], "url": f"{site['domain']}/", "logo": {"@type": "ImageObject", "url": f"{site['domain']}{OG_IMAGE}"}}, "image": f"{site['domain']}{OG_IMAGE}", "citation": a["citation"], "isBasedOn": a["source"]["original_url"], "sameAs": [a["source"]["pubmed_url"], a["source"]["original_url"]], "mainEntityOfPage": f"{site['domain']}{canonical_path}"},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type":"ListItem","position":1,"name":"Repositorio científico","item":f"{site['domain']}/repositorio/"},{"@type":"ListItem","position":2,"name":a["category_name"],"item":f"{site['domain']}/repositorio/categorias/{a['category']}.html"},{"@type":"ListItem","position":3,"name":a["title_es"],"item":f"{site['domain']}{canonical_path}"}]}
    ]}
    card_data = a.get("card") or {}
    answer_heading = card_data.get("question", "Qué permite llevarse de este estudio")
    answer_lead = card_data.get("answer", a["clinical_takeaway"])
    key_data = f'<p class="answer-key-data"><span>Dato clave</span>{esc(card_data["key_data"])}</p>' if card_data.get("key_data") else ""
    answer_context = f'<p class="answer-context">{esc(a["clinical_takeaway"])}</p>' if answer_lead != a["clinical_takeaway"] else ""
    protocol_nav, protocol_section = intervention_protocol(a)
    measurement_nav, measurement_section = measurement_battery(a)
    body = f'''<article class="article-page"><header class="article-hero"><div class="shell article-header"><nav class="breadcrumbs" aria-label="Migas de pan"><a href="../">Repositorio</a><span>›</span><a href="../categorias/{esc(a['category'])}.html">{esc(a['category_name'])}</a></nav><p class="section-label light">Análisis crítico · {esc(a['category_name'])}</p><h1>{esc(a['title_es'])}</h1><p class="original-study-title"><span>Título original</span><span lang="en">{esc(a['title'])}</span></p><dl class="article-facts"><div><dt>Diseño</dt><dd>{esc(design_label)}</dd></div><div><dt>Población</dt><dd>{esc(a['population'])}</dd></div><div><dt>Año</dt><dd>{a['year']}</dd></div><div class="fact-score"><dt>Índice editorial</dt><dd><strong>{score}</strong> / 30</dd></div></dl><div class="article-source-actions">{source_links}</div><p class="article-citation">{esc(a['citation'])}</p></div></header>
<div class="reading-signature" aria-label="Estructura de lectura crítica"><div class="shell"><p><span>Observado</span><strong>{esc(outcome)}</strong></p><p><span>Límite</span><strong>{esc(a['limitations'][0])}</strong></p><p><span>Aplicabilidad</span><strong>Interpretación clínica, no receta terapéutica</strong></p></div></div>
<div class="shell article-layout"><aside class="evidence-rail"><p class="section-label">En esta ficha</p><nav aria-label="Contenido del análisis"><a href="#respuesta">Respuesta corta</a><a href="#resultados">Resultados e interpretación</a>{measurement_nav}{protocol_nav}<a href="#transferencia">Aplicabilidad clínica</a><a href="#limites">Límites</a><a href="#poblacion">Población</a><a href="#fuente">Fuente original</a></nav><div class="rail-source"><span>Fuente verificada</span><strong>PubMed · PMID {esc(a['source']['pmid'])}</strong><small>Revisión: {esc(a['review']['updated_at'])}</small></div></aside>
<div class="article-body"><section class="clinical-answer" id="respuesta"><p class="section-label">Respuesta clínica corta</p><h2>{esc(answer_heading)}</h2><p class="answer-lead">{esc(answer_lead)}</p>{key_data}{answer_context}</section><section id="resultados"><p class="section-label">Observado</p><h2>Qué encontró y cómo interpretarlo</h2>{paragraphs(a['critical_analysis'])}</section>{measurement_section}{protocol_section}<section class="application" id="transferencia"><p class="section-label">Aplicabilidad</p><h2>Qué significa clínicamente</h2>{paragraphs(a['clinical_application'])}</section><section class="limits" id="limites"><p class="section-label">Límite</p><h2>Qué no permite afirmar</h2>{paragraphs(a['limitations'])}</section><section class="population-context" id="poblacion"><p class="section-label">Contexto</p><h2>¿Se parece a tu paciente?</h2><dl><div><dt>Población estudiada</dt><dd>{esc(a['population'])}</dd></div><div><dt>Diseño</dt><dd>{esc(a['study_design'])}</dd></div><div><dt>Resultado evaluado</dt><dd>{esc(outcome)}</dd></div></dl></section><section class="source-panel" id="fuente"><p class="section-label">Fuente primaria</p><h2>Lee el estudio, no solo nuestro análisis</h2><p>{esc(a['citation'])}</p><div>{source_links}</div></section>{editorial_responsibility(site, a['review']['updated_at'], a['review']['conflicts'])}{related_section}</div></div></article>'''
    target = OUTPUT / "articulos" / f"{a['slug']}.html"
    description = a.get("seo",{}).get("description", a["clinical_takeaway"])
    if description.startswith("Juicio integrador y crítico"):
        description = f"Análisis crítico de {a['title_es']}: diseño, sesgos, resultados, límites y transferencia clínica en fisioterapia."
    target.write_text(layout(a.get("seo",{}).get("title", a["title_es"]), description, canonical_path, body, "../../", article_json, "article"), encoding="utf-8")


def build_categories(articles, categories, site):
    target_dir = OUTPUT / "categorias"
    target_dir.mkdir(parents=True, exist_ok=True)
    for category in categories:
        items = [a for a in articles if a["category"] == category["slug"]]
        if not items:
            continue
        cards = "".join(card(a, "../articulos/") for a in sorted(items, key=lambda x: (-x["year"], x["title_es"])))
        canonical_path = f"/repositorio/categorias/{category['slug']}.html"
        title = f"Evidencia sobre {category['name']} en fisioterapia"
        description = f"Análisis crítico de estudios sobre {category['name'].lower()}: {category['description']} Resultados, límites y transferencia clínica."
        structured = {"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","name":title,"description":meta_description(description),"url":f"{site['domain']}{canonical_path}","isPartOf":{"@type":"WebSite","name":site["brand"],"url":f"{site['domain']}/"},"mainEntity":{"@type":"ItemList","numberOfItems":len(items),"itemListElement":[{"@type":"ListItem","position":position,"url":f"{site['domain']}/repositorio/articulos/{article['slug']}.html","name":article["title_es"]} for position, article in enumerate(items, 1)]}},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Repositorio científico","item":f"{site['domain']}/repositorio/"},{"@type":"ListItem","position":2,"name":category["name"],"item":f"{site['domain']}{canonical_path}"}]}]}
        body = f'''<section class="category-hero"><div class="shell"><nav class="breadcrumbs" aria-label="Migas de pan"><a href="../">Repositorio</a><span>›</span><span>{esc(category['name'])}</span></nav><p class="section-label light">Categoría científica · {len(items)} análisis</p><h1>{esc(category['name'])}</h1><p>{esc(category['description'])}</p></div></section><section class="evidence-section"><div class="shell"><div class="category-intro"><h2>Análisis disponibles</h2><p>Cada ficha distingue el resultado observado, sus límites y la transferencia posible a fisioterapia.</p></div><div class="evidence-grid">{cards}</div></div></section>'''
        (target_dir / f"{category['slug']}.html").write_text(layout(title, description, canonical_path, body, "../../", structured), encoding="utf-8")


def journey_articles(journey, articles):
    categories = set(journey.get("categories", [])); tiers = set(journey.get("tiers", [])); keywords = [x.lower() for x in journey.get("keywords", [])]
    matches = []
    for article in articles:
        haystack = f"{article['title']} {article['clinical_takeaway']} {article['category_name']}".lower()
        if (categories and article["category"] in categories) or (tiers and article["tier"] in tiers) or any(word in haystack for word in keywords):
            matches.append(article)
    return sorted(matches, key=lambda x: (-x["year"], x["title"]))


def build_journeys(articles, journeys, site):
    target_dir = OUTPUT / "recorridos"; target_dir.mkdir(parents=True, exist_ok=True)
    for journey in journeys:
        items = journey_articles(journey, articles)
        if not items:
            continue
        cards = "".join(card(a, "../articulos/") for a in items)
        canonical_path = f"/repositorio/recorridos/{journey['slug']}.html"
        structured = {"@context":"https://schema.org","@type":"CollectionPage","name":journey["question"],"description":journey["description"],"url":f"{site['domain']}{canonical_path}","isPartOf":{"@type":"WebSite","name":site["brand"],"url":f"{site['domain']}/"}}
        body = f'''<section class="category-hero journey-hero"><div class="shell"><nav class="breadcrumbs" aria-label="Migas de pan"><a href="../">Repositorio</a><span>›</span><span>Recorrido clínico</span></nav><p class="section-label light">Recorrido clínico · {len(items)} análisis</p><h1>{esc(journey['question'])}</h1><p>{esc(journey['description'])}</p></div></section><section class="evidence-section"><div class="shell"><div class="category-intro"><h2>Qué dice la evidencia seleccionada</h2><p>No es una recomendación terapéutica: es una ruta para comparar diseños, resultados y límites.</p></div><div class="evidence-grid">{cards}</div></div></section>'''
        (target_dir / f"{journey['slug']}.html").write_text(layout(journey["question"], journey["description"], canonical_path, body, "../../", structured), encoding="utf-8")


def build_trust_pages(site):
    author_url = f"{site['domain']}/sobre-fran/"
    author_schema = {"@context":"https://schema.org","@type":"ProfilePage","mainEntity":{"@type":"Person","@id":f"{author_url}#person","name":site["author"]["name"],"jobTitle":site["author"]["role"],"description":f"{site['author']['credential']}. {site['author']['academic_role']}.","url":author_url,"sameAs":list(site["profiles"].values()),"worksFor":{"@type":"MedicalBusiness","name":site["clinic"]["name"]}}}
    author_body = f'''<section class="trust-hero"><div class="shell trust-copy"><p class="section-label light">Autor y revisor científico</p><h1>Francisco José<br><em>Extremera García</em></h1><p>{esc(site['author']['credential'])} · {esc(site['author']['role'])}.</p></div></section><section class="trust-content"><div class="shell article-body"><section><h2>Experiencia y responsabilidad editorial</h2><p>Fran es el creador de FisioLógico y responsable de la revisión del repositorio científico. Su trabajo integra práctica clínica, docencia y lectura crítica de la evidencia aplicada a fisioterapia.</p><p>{esc(site['author']['academic_role'])}. Desarrolla su actividad clínica en {esc(site['clinic']['name'])}, en Málaga.</p></section><section><h2>Áreas de trabajo</h2><p>Dolor musculoesquelético, dolor orofacial y trastornos temporomandibulares, fisioterapia invasiva aplicada al neuroeje, ejercicio terapéutico y transferencia clínica de la investigación.</p></section><section><h2>Perfiles profesionales</h2><p><a href="{esc(site['profiles']['linkedin'])}" rel="me">LinkedIn</a> · <a href="{esc(site['profiles']['substack'])}" rel="me">Substack</a> · <a href="{esc(site['profiles']['instagram'])}" rel="me">Instagram</a></p></section><section><h2>Criterio editorial</h2><p>La autoría identifica quién interpreta la evidencia, pero no sustituye la fuente primaria. Cada análisis enlaza el estudio original, hace explícitos sus límites y documenta su fecha de revisión.</p><a class="button button-dark" href="../metodo-editorial/">Nuestro compromiso editorial</a></section></div></section>'''
    author_dir = ROOT / "sobre-fran"; author_dir.mkdir(exist_ok=True)
    (author_dir / "index.html").write_text(layout("Francisco José Extremera García, fisioterapeuta", f"Autor y revisor científico de FisioLógico. {site['author']['credential']} en Málaga.", "/sobre-fran/", author_body, "../", author_schema, "profile"), encoding="utf-8")

    method_schema = {"@context":"https://schema.org","@type":"WebPage","name":"Compromiso editorial de FisioLógico","url":f"{site['domain']}/metodo-editorial/","about":{"@type":"Thing","name":"Lectura crítica de evidencia en fisioterapia"},"author":{"@id":f"{author_url}#person"},"dateModified":"2026-07-14"}
    method_body = '''<section class="trust-hero"><div class="shell trust-copy"><p class="section-label light">Compromiso editorial</p><h1>Evidencia con<br><em>criterio y límites.</em></h1><p>Principios claros para ofrecer análisis útiles, prudentes y verificables.</p></div></section><section class="trust-content"><div class="shell article-body"><section><h2>Fuente primaria</h2><p>Cada ficha identifica y enlaza el artículo original y su registro en PubMed para que el lector pueda contrastar el análisis.</p></section><section><h2>Lectura crítica</h2><p>Diferenciamos los resultados observados de su interpretación y explicamos la población estudiada, el contexto y las limitaciones relevantes.</p></section><section><h2>Índice editorial</h2><p>El total visible sobre 30 sintetiza nuestra valoración interna de la calidad y la utilidad del estudio. Facilita la comparación dentro del repositorio, pero no equivale por sí solo a certeza científica ni reemplaza el análisis completo.</p></section><section><h2>Prudencia clínica</h2><p>La evidencia se presenta como apoyo al razonamiento profesional, no como una receta ni como sustituto de una valoración individual. Evitamos extender las conclusiones más allá de lo realmente estudiado.</p></section><section><h2>Autoría y actualización</h2><p>Las fichas identifican al revisor y su fecha de actualización. Cuando aparece información relevante, el contenido puede revisarse para mantener su utilidad.</p></section><section><h2>Criterio propio</h2><p>El procedimiento detallado de evaluación es interno y forma parte del trabajo editorial de FisioLógico.</p></section></div></section>'''
    method_dir = ROOT / "metodo-editorial"; method_dir.mkdir(exist_ok=True)
    (method_dir / "index.html").write_text(layout("Compromiso editorial", "Principios de FisioLógico para publicar análisis científicos verificables, prudentes y orientados al razonamiento clínico.", "/metodo-editorial/", method_body, "../", method_schema), encoding="utf-8")


def redirect(path: Path, destination: str):
    canonical = f"https://www.elfisiologico.com{destination}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contenido trasladado · FisioLógico</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="{esc(canonical)}"><meta http-equiv="refresh" content="0;url={esc(destination)}"><script>location.replace({json.dumps(destination)});</script></head><body><p>Este contenido ya no forma parte de la selección publicada. Consulta el <a href="{esc(destination)}">repositorio científico de FisioLógico</a>.</p></body></html>''', encoding="utf-8")


def build_redirects(articles, categories):
    for a in articles:
        destination = f"/repositorio/articulos/{a['slug']}.html"
        for legacy in a.get("legacy_paths", []):
            redirect(ROOT / legacy.lstrip("/"), destination)
    for category in categories:
        legacy_slug = {"ejercicio": "ejercicio", "tdcs": "estimulacion-cortical"}.get(category["slug"], category["slug"])
        legacy = ROOT / "categorias" / f"{legacy_slug}.html"
        if legacy.exists():
            redirect(legacy, f"/repositorio/categorias/{category['slug']}.html")
    redirect(ROOT / "categorias" / "index.html", "/repositorio/")
    redirect(ROOT / "repository" / "index.html", "/repositorio/")
    redirect(ROOT / "repository.html", "/repositorio/")


def build_retired_redirects(all_articles, articles, categories, active_categories, journeys, active_journeys):
    """Conserva rutas antiguas sin mantener contenido no respaldado ni indexable."""
    active_slugs = {article["slug"] for article in articles}
    for article in all_articles:
        if article["slug"] not in active_slugs:
            redirect(OUTPUT / "articulos" / f"{article['slug']}.html", "/repositorio/")

    active_category_slugs = {category["slug"] for category in active_categories}
    for category in categories:
        if category["slug"] in active_category_slugs:
            continue
        redirect(OUTPUT / "categorias" / f"{category['slug']}.html", "/repositorio/")
        legacy_slug = {"ejercicio": "ejercicio", "tdcs": "estimulacion-cortical"}.get(category["slug"], category["slug"])
        legacy = ROOT / "categorias" / f"{legacy_slug}.html"
        if legacy.exists():
            redirect(legacy, "/repositorio/")

    active_journey_slugs = {journey["slug"] for journey in active_journeys}
    for journey in journeys:
        if journey["slug"] not in active_journey_slugs:
            redirect(OUTPUT / "recorridos" / f"{journey['slug']}.html", "/repositorio/")


def build_sitemap(articles, categories, journeys, site):
    active_categories = {a["category"] for a in articles}
    urls = [
        ("/", "2026-07-18"),
        ("/tratamientos/", "2026-07-18"),
        ("/patients/", "2026-07-18"),
        ("/patients/explora-dolor/", "2026-07-18"),
        ("/profesionales/", "2026-07-18"),
        ("/profesionales/mapa-dolor-muscular/", "2026-07-18"),
        ("/formacion/", "2026-07-17"),
        ("/formacion/aiim/", "2026-07-17"),
        ("/formacion/paradigma-vascular/", "2026-07-17"),
        ("/formacion/nervios-perifericos/", "2026-07-17"),
        ("/formacion/oep-sas-2027/", "2026-07-17"),
        ("/repositorio/", "2026-07-15"),
        ("/instrumentos/", "2026-07-18"),
        ("/instrumentos/patient-specific-functional-scale/", "2026-07-18"),
        ("/instrumentos/oswestry-disability-index/", "2026-07-18"),
        ("/instrumentos/pain-catastrophizing-scale/", "2026-07-18"),
        ("/instrumentos/neck-disability-index/", "2026-07-18"),
        ("/instrumentos/quickdash/", "2026-07-18"),
        ("/instrumentos/lower-extremity-functional-scale/", "2026-07-18"),
        ("/instrumentos/escala-numerica-dolor/", "2026-07-18"),
        ("/instrumentos/impresion-global-cambio-paciente/", "2026-07-18"),
        ("/instrumentos/eq-5d-5l/", "2026-07-18"),
        ("/instrumentos/whodas-2-participacion/", "2026-07-18"),
        ("/instrumentos/promis-alteracion-sueno-8a/", "2026-07-18"),
        ("/instrumentos/pain-self-efficacy-questionnaire/", "2026-07-18"),
        ("/instrumentos/rendimiento/", "2026-07-18"),
        ("/instrumentos/rendimiento/chair-stand-30-segundos/", "2026-07-18"),
        ("/instrumentos/rendimiento/timed-up-and-go/", "2026-07-18"),
        ("/instrumentos/rendimiento/test-marcha-10-metros/", "2026-07-18"),
        ("/instrumentos/rendimiento/test-marcha-seis-minutos/", "2026-07-18"),
        ("/con-logica/", "2026-07-14"),
        ("/sobre-fran/", "2026-07-14"),
        ("/metodo-editorial/", "2026-07-14"),
    ]
    clinical_tests = load(ROOT / "data/clinical-tests.json")
    clinical_index = ROOT / "pruebas-clinicas" / "index.html"
    if clinical_index.exists():
        urls.append(("/pruebas-clinicas/", clinical_tests.get("updated_at", "2026-07-14")))
    for suspicion in clinical_tests.get("suspicions", []):
        page = ROOT / "pruebas-clinicas" / suspicion["slug"] / "index.html"
        if suspicion.get("editorial_status") == "published" and page.exists():
            urls.append((f"/pruebas-clinicas/{suspicion['slug']}/", clinical_tests.get("updated_at", "2026-07-14")))
    urls += [(f"/repositorio/categorias/{c['slug']}.html", "2026-07-14") for c in categories if c["slug"] in active_categories]
    urls += [(f"/repositorio/recorridos/{j['slug']}.html", "2026-07-14") for j in journeys]
    urls += [(f"/repositorio/articulos/{a['slug']}.html", a["review"]["updated_at"]) for a in articles]
    entries = "".join(f"  <url><loc>{esc(site['domain'] + url)}</loc><lastmod>{lastmod}</lastmod></url>\n" for url, lastmod in urls)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}</urlset>\n', encoding="utf-8")


def main():
    site, categories = load(ROOT / "data/site.json"), load(ROOT / "data/categories.json")
    curation = load(ROOT / "data/repository-curation.json")
    all_articles = [load(p) for p in sorted(ARTICLES.glob("*.json"))]
    articles = [article for article in all_articles if is_editorially_complete(article)]
    active_categories = [category for category in categories if any(article["category"] == category["slug"] for article in articles)]
    active_journeys = [journey for journey in curation["journeys"] if journey_articles(journey, articles)]
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "articulos").mkdir(parents=True)
    build_index(articles, categories, curation)
    for article in articles:
        build_article(article, site, articles)
    build_categories(articles, categories, site)
    build_journeys(articles, curation["journeys"], site)
    build_trust_pages(site)
    build_redirects(articles, active_categories)
    build_retired_redirects(all_articles, articles, categories, active_categories, curation["journeys"], active_journeys)
    build_sitemap(articles, active_categories, active_journeys, site)
    sync_navigation()
    print(f"Generados {len(articles)} artículos con texto completo, categorías SEO, páginas de confianza, sitemap y redirecciones.")


if __name__ == "__main__":
    main()
