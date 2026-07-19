#!/usr/bin/env python3
"""Auditor SEO reproducible para las páginas indexables de FisioLógico."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://www.elfisiologico.com"

# Estados y componentes del flujo interno que nunca deben aparecer en una ficha
# pública. La puntuación global /30 sí es parte del producto editorial.
FORBIDDEN_ARTICLE_MARKERS = {
    "evaluación v2": "estado interno de evaluación",
    "evaluacion v2": "estado interno de evaluación",
    "migración de rúbrica": "proceso interno de migración",
    "migracion de rubrica": "proceso interno de migración",
    "reevaluación por outcome": "proceso interno de reevaluación",
    "reevaluacion por outcome": "proceso interno de reevaluación",
    "bloqueos no compensables": "reglas internas de la rúbrica",
    "puntuación histórica v1": "historial interno de puntuación",
    "puntuacion historica v1": "historial interno de puntuación",
    "v1 histórica": "versión interna de la rúbrica",
    "v1 historica": "versión interna de la rúbrica",
    "ficha de evidencia": "componente público obsoleto de dimensiones",
    'class="rubric-context': "componente público obsoleto de rúbrica",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.h1 = 0
        self.meta = {}
        self.links = []
        self.canonical = ""
        self.jsonld = []
        self._jsonld = False
        self._json_buffer = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "title": self.in_title = True
        if tag == "h1": self.h1 += 1
        if tag == "meta":
            key = data.get("name") or data.get("property")
            if key: self.meta[key] = data.get("content", "")
        if tag == "link" and data.get("rel") == "canonical": self.canonical = data.get("href", "")
        if tag == "a" and data.get("href"): self.links.append(data["href"])
        if tag == "script" and data.get("type") == "application/ld+json":
            self._jsonld = True; self._json_buffer = []

    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        if tag == "script" and self._jsonld:
            self._jsonld = False
            raw = "".join(self._json_buffer).strip()
            if raw:
                try: self.jsonld.append(json.loads(raw))
                except json.JSONDecodeError: self.jsonld.append(None)

    def handle_data(self, data):
        if self.in_title: self.title += data
        if self._jsonld: self._json_buffer.append(data)


def path_from_url(url: str) -> Path:
    path = urlparse(url).path
    if path.endswith("/"): path += "index.html"
    return ROOT / path.lstrip("/")


def main() -> None:
    errors, warnings = [], []
    site = json.loads((ROOT / "data/site.json").read_text(encoding="utf-8"))
    sitemap = ET.parse(ROOT / "sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in sitemap.findall("s:url/s:loc", ns)]
    titles, descriptions = [], []

    for url in urls:
        path = path_from_url(url)
        label = str(path.relative_to(ROOT))
        if not path.exists():
            errors.append(f"{label}: URL del sitemap sin archivo")
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        parser = PageParser(); parser.feed(source)
        title = parser.title.strip(); description = parser.meta.get("description", "").strip()
        if not title: errors.append(f"{label}: falta <title>")
        if not 20 <= len(title) <= 120: warnings.append(f"{label}: título de {len(title)} caracteres")
        if not 70 <= len(description) <= 170: errors.append(f"{label}: descripción de {len(description)} caracteres")
        if parser.h1 != 1: errors.append(f"{label}: debe contener un único h1, encontrados {parser.h1}")
        if parser.canonical != url: errors.append(f"{label}: canonical {parser.canonical!r} no coincide con {url}")
        if "noindex" in parser.meta.get("robots", "").lower(): errors.append(f"{label}: URL del sitemap marcada noindex")
        if not parser.meta.get("og:title") or not parser.meta.get("og:description") or not parser.meta.get("og:image"): errors.append(f"{label}: Open Graph incompleto")
        if not parser.jsonld or any(item is None for item in parser.jsonld): errors.append(f"{label}: JSON-LD ausente o inválido")
        if "<main" not in source or "</main>" not in source: errors.append(f"{label}: falta región principal <main>")
        if 'class="skip-link"' not in source: warnings.append(f"{label}: falta enlace para saltar al contenido")
        if '<html lang="es"' not in source: errors.append(f"{label}: falta idioma español en <html>")
        for href in parser.links:
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            resolved = urlparse(urljoin(url, href))
            if resolved.netloc and resolved.netloc != urlparse(DOMAIN).netloc:
                continue
            internal_url = f"{DOMAIN}{unquote(resolved.path)}"
            if not path_from_url(internal_url).exists():
                errors.append(f"{label}: enlace interno roto {href!r}")
        public_path = urlparse(url).path
        is_clinical_content = "/repositorio/articulos/" in public_path or (
            public_path.startswith("/instrumentos/") and public_path not in ("/instrumentos/", "/instrumentos/rendimiento/")
        ) or (
            public_path.startswith("/pruebas-clinicas/") and public_path != "/pruebas-clinicas/"
        )
        if is_clinical_content:
            editorial_required = (
                'class="editorial-responsibility"',
                site["author"]["name"],
                site["editorial"]["credential_line"],
                site["editorial"]["role"],
                site["editorial"]["conflicts"],
                "Última revisión",
                "Conflictos de interés",
            )
            for required in editorial_required:
                if required not in source:
                    errors.append(f"{label}: responsabilidad editorial incompleta; falta {required!r}")
        titles.append((title, label)); descriptions.append((description, label))

    for value, count in Counter(x[0] for x in titles).items():
        if count > 1: errors.append(f"Título duplicado ({count}): {value}")
    for value, count in Counter(x[0] for x in descriptions).items():
        if value and count > 1: warnings.append(f"Descripción duplicada ({count}): {value[:80]}")

    required_hubs = {"/tratamientos/", "/patients/", "/patients/explora-dolor/", "/profesionales/", "/formacion/", "/repositorio/", "/instrumentos/", "/pruebas-clinicas/"}
    sitemap_paths = {urlparse(url).path for url in urls}
    for path in sorted(required_hubs - sitemap_paths):
        errors.append(f"sitemap: falta la sección estratégica {path}")

    all_articles = [json.loads(path.read_text()) for path in sorted((ROOT / "content/articles").glob("*.json"))]
    articles = [article for article in all_articles if article.get("rubric_v2", {}).get("status") == "complete"]
    public_article_urls = [url for url in urls if "/repositorio/articulos/" in url]
    if len(public_article_urls) != len(articles):
        errors.append(
            "repositorio/articulos: "
            f"{len(public_article_urls)} fichas indexables para {len(articles)} evaluaciones completas"
        )

    for article in articles:
        label = article["slug"]
        if not article["review"].get("published_at"): errors.append(f"{label}: falta published_at")
        if not article["source"].get("original_url"): errors.append(f"{label}: falta artículo original")
        if len(article["clinical_takeaway"]) < 80: errors.append(f"{label}: síntesis demasiado corta")

        public_path = ROOT / "repositorio/articulos" / f"{label}.html"
        if not public_path.exists():
            errors.append(f"{label}: falta ficha pública generada")
            continue
        public_source = public_path.read_text(encoding="utf-8", errors="ignore")
        normalized_source = public_source.casefold()
        for marker, reason in FORBIDDEN_ARTICLE_MARKERS.items():
            if marker.casefold() in normalized_source:
                errors.append(f"{label}: expone {reason} ({marker!r})")
        for required in ("Índice editorial", "Fuente primaria", article["source"]["pubmed_url"]):
            if required not in public_source:
                errors.append(f"{label}: falta elemento público requerido {required!r}")

    instrument_payload = json.loads((ROOT / "data/instruments.json").read_text(encoding="utf-8"))
    instruments = instrument_payload.get("instruments", [])
    instrument_index = (ROOT / "instrumentos/index.html").read_text(encoding="utf-8", errors="ignore")
    required_instrument_fields = (
        "slug", "name", "acronym", "type", "construct_key", "region_key", "summary",
        "score_range", "score_direction", "direction_label", "spanish_label", "validation_key",
        "validated_population", "permission_key", "permission_label", "permission_action",
        "permission_checked_at", "permission_basis", "evidence_label", "evidence_grade",
        "evidence_search_date", "evidence_method", "administration", "recall_period", "version",
        "choice_note", "useful_for", "not_for", "updated_at",
        "maintenance", "change_interpretation", "calculator",
    )
    for instrument in instruments:
        label = instrument.get("slug", "instrumento sin slug")
        for field in required_instrument_fields:
            if not instrument.get(field):
                errors.append(f"{label}: falta dato canónico {field!r}")
        if f'data-acronym="{instrument.get("acronym", "")}"' not in instrument_index:
            errors.append(f"{label}: no aparece en el catálogo generado")
        detail = ROOT / "instrumentos" / label / "index.html"
        if not detail.exists():
            errors.append(f"{label}: falta ficha técnica")
        else:
            detail_source = detail.read_text(encoding="utf-8", errors="ignore")
            for required in (instrument.get("acronym", ""), instrument.get("permission_label", ""), instrument.get("evidence_search_date", "")):
                if required and required not in detail_source:
                    errors.append(f"{label}: la ficha no refleja el dato canónico {required!r}")
    card_count = instrument_index.count("data-instrument-card")
    if card_count != len(instruments):
        errors.append(
            f"instrumentos/index.html: {card_count} tarjetas para {len(instruments)} registros canónicos"
        )

    performance_payload = json.loads((ROOT / "data/performance-instruments.json").read_text(encoding="utf-8"))
    performance = performance_payload.get("instruments", [])
    performance_index_path = ROOT / "instrumentos/rendimiento/index.html"
    if not performance_index_path.exists():
        errors.append("instrumentos/rendimiento/index.html: falta la batería de rendimiento")
        performance_index = ""
    else:
        performance_index = performance_index_path.read_text(encoding="utf-8", errors="ignore")
    required_performance_fields = (
        "slug", "name", "acronym", "construct", "summary", "purpose", "population",
        "time", "equipment", "protocol", "outcome", "score_range", "score_direction",
        "direction_label", "safety", "standardization", "useful_for", "not_for",
        "evidence_label", "evidence_search_date", "permission_label", "permission_url",
        "sources", "updated_at",
        "maintenance", "change_interpretation", "calculator", "printable_protocol",
    )
    for instrument in performance:
        label = instrument.get("slug", "prueba de rendimiento sin slug")
        for field in required_performance_fields:
            if not instrument.get(field):
                errors.append(f"{label}: falta dato canónico de rendimiento {field!r}")
        if instrument.get("acronym", "") not in performance_index:
            errors.append(f"{label}: no aparece en la batería de rendimiento")
        detail = ROOT / "instrumentos/rendimiento" / label / "index.html"
        if not detail.exists():
            errors.append(f"{label}: falta protocolo técnico")
        else:
            detail_source = detail.read_text(encoding="utf-8", errors="ignore")
            for required in (instrument.get("acronym", ""), instrument.get("evidence_search_date", ""), instrument.get("safety", "")):
                if required and required not in detail_source:
                    errors.append(f"{label}: el protocolo no refleja el dato canónico {required!r}")
    performance_card_count = performance_index.count('class="performance-card"')
    if performance_card_count != len(performance):
        errors.append(
            f"instrumentos/rendimiento/index.html: {performance_card_count} tarjetas para {len(performance)} registros canónicos"
        )

    guidance = json.loads((ROOT / "data/instrument-guidance.json").read_text(encoding="utf-8"))
    for field in ("updated_at", "next_review_at", "status", "builder", "cases", "discordance", "changelog"):
        if not guidance.get(field):
            errors.append(f"instrument-guidance.json: falta {field!r}")
    for required in (
        'data-battery-builder', 'data-battery-result', 'data-joint-reading',
        'class="clinical-cases"', 'class="collection-maintenance"',
    ):
        if required not in instrument_index:
            errors.append(f"instrumentos/index.html: falta herramienta {required!r}")
    for instrument in instruments:
        detail = ROOT / "instrumentos" / instrument["slug"] / "index.html"
        detail_source = detail.read_text(encoding="utf-8", errors="ignore")
        for required in ("Interpretar el cambio", "Próxima revisión prevista"):
            if required not in detail_source:
                errors.append(f"{instrument['slug']}: falta bloque avanzado {required!r}")
    for instrument in performance:
        detail = ROOT / "instrumentos/rendimiento" / instrument["slug"] / "index.html"
        detail_source = detail.read_text(encoding="utf-8", errors="ignore")
        for required in ("Interpretar el cambio", "data-print-protocol", "Próxima revisión prevista"):
            if required not in detail_source:
                errors.append(f"{instrument['slug']}: falta bloque avanzado {required!r}")

    print(f"SEO auditado: {len(urls)} URLs indexables, {len(articles)} análisis científicos.")
    for warning in warnings: print(f"WARN {warning}")
    for error in errors: print(f"ERROR {error}")
    print(f"Resultado: {len(errors)} errores, {len(warnings)} avisos.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
