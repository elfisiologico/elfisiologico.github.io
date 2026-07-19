#!/usr/bin/env python3
"""Auditoría reproducible de preparación para respuestas y búsquedas con IA."""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from seo_audit import DOMAIN, ROOT, PageParser, path_from_url

SEARCH_BOTS = ("OAI-SearchBot", "ChatGPT-User", "PerplexityBot")
INTERNAL_PATHS = ("/.codex/", "/content/", "/scripts/", "/data/", "/docs/")
STRATEGIC_URLS = (
    f"{DOMAIN}/",
    f"{DOMAIN}/tratamientos/",
    f"{DOMAIN}/patients/",
    f"{DOMAIN}/profesionales/",
    f"{DOMAIN}/formacion/",
    f"{DOMAIN}/repositorio/",
    f"{DOMAIN}/instrumentos/",
    f"{DOMAIN}/pruebas-clinicas/",
    f"{DOMAIN}/sobre-fran/",
    f"{DOMAIN}/metodo-editorial/",
)


def schema_nodes(value: object):
    if isinstance(value, dict):
        if "@type" in value:
            yield value
        for nested in value.values():
            yield from schema_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from schema_nodes(nested)


def nodes_of_type(parser: PageParser, schema_type: str) -> list[dict]:
    return [
        node
        for payload in parser.jsonld
        if payload is not None
        for node in schema_nodes(payload)
        if schema_type in ([node.get("@type")] if isinstance(node.get("@type"), str) else node.get("@type", []))
    ]


def visible_text(source: str) -> str:
    source = re.sub(r"<(script|style)\b.*?</\1>", " ", source, flags=re.IGNORECASE | re.DOTALL)
    source = re.sub(r"<[^>]+>", " ", source)
    return re.sub(r"\s+", " ", html.unescape(source)).strip()


def robots_group(source: str, agent: str) -> str:
    pattern = rf"(?ims)^User-agent:\s*{re.escape(agent)}\s*$\n(.*?)(?=^User-agent:|^Sitemap:|\Z)"
    match = re.search(pattern, source)
    return match.group(1) if match else ""


def fetch_live(path: str, user_agent: str = "FisioLogico-AEO-Audit/1.0") -> tuple[str, str]:
    url = f"{DOMAIN}{path}"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


def audit_live_delivery(errors: list[str]) -> None:
    checks = (
        ("/robots.txt", "OAI-SearchBot", ("User-agent: OAI-SearchBot", "User-agent: PerplexityBot")),
        ("/llms.txt", "ChatGPT-User", ("# FisioLógico", f"{DOMAIN}/repositorio/")),
        ("/2af7d992efd2cc18e68bd60b12da63a9.txt", "PerplexityBot", ("2af7d992efd2cc18e68bd60b12da63a9",)),
        (
            "/pruebas-clinicas/lesion-meniscal/",
            "OAI-SearchBot",
            (
                f'<link rel="canonical" href="{DOMAIN}/pruebas-clinicas/lesion-meniscal/">',
                '"@type":"MedicalWebPage"',
                '"reviewedBy"',
                '"citation"',
            ),
        ),
    )
    for path, agent, markers in checks:
        requested = f"{DOMAIN}{path}"
        try:
            final_url, source = fetch_live(path, agent)
        except (urllib.error.URLError, TimeoutError) as error:
            errors.append(f"producción: no se pudo recuperar {requested}: {error}")
            continue
        if final_url != requested:
            errors.append(f"producción: {requested} redirige a {final_url}; no coincide con la URL canónica")
        for marker in markers:
            if marker not in source:
                errors.append(f"producción: {requested} no entrega {marker!r} a {agent}")


def main() -> None:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--live", action="store_true", help="comprueba también la entrega HTTPS en producción")
    args = argument_parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    robots_path = ROOT / "robots.txt"
    robots = robots_path.read_text(encoding="utf-8") if robots_path.exists() else ""
    for agent in SEARCH_BOTS:
        group = robots_group(robots, agent)
        if not group:
            errors.append(f"robots.txt: falta grupo explícito para {agent}")
            continue
        if not re.search(r"(?im)^Allow:\s*/\s*$", group):
            errors.append(f"robots.txt: {agent} no tiene acceso público explícito")
        for internal in INTERNAL_PATHS:
            if not re.search(rf"(?im)^Disallow:\s*{re.escape(internal)}\s*$", group):
                errors.append(f"robots.txt: {agent} no protege {internal}")
    if f"Sitemap: {DOMAIN}/sitemap.xml" not in robots:
        errors.append("robots.txt: falta referencia canónica al sitemap")

    llms_path = ROOT / "llms.txt"
    if not llms_path.exists():
        errors.append("llms.txt: falta el índice editorial complementario")
    else:
        llms = llms_path.read_text(encoding="utf-8")
        for url in STRATEGIC_URLS:
            if url not in llms:
                errors.append(f"llms.txt: falta {url}")
        if "no sustituye una valoración individual" not in llms:
            errors.append("llms.txt: falta el límite sanitario")

    indexnow_scripts = list((ROOT / "scripts").glob("submit_indexnow.py"))
    if not indexnow_scripts:
        errors.append("IndexNow: falta herramienta de notificación")
    else:
        script_source = indexnow_scripts[0].read_text(encoding="utf-8")
        key_match = re.search(r'^KEY = "([a-f0-9]{8,128})"$', script_source, flags=re.MULTILINE)
        if not key_match:
            errors.append("IndexNow: clave ausente o inválida")
        else:
            key = key_match.group(1)
            key_path = ROOT / f"{key}.txt"
            if not key_path.exists() or key_path.read_text(encoding="utf-8").strip() != key:
                errors.append("IndexNow: archivo de verificación ausente o incoherente")

    sitemap = ET.parse(ROOT / "sitemap.xml")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries = sitemap.findall("s:url", namespace)
    urls: list[str] = []
    lastmods: dict[str, str] = {}
    for entry in entries:
        location = entry.findtext("s:loc", namespaces=namespace)
        lastmod = entry.findtext("s:lastmod", namespaces=namespace)
        if not location:
            errors.append("sitemap.xml: entrada sin loc")
            continue
        urls.append(location)
        if not lastmod or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod):
            errors.append(f"sitemap.xml: lastmod ausente o inválido en {location}")
        else:
            lastmods[location] = lastmod

    article_count = instrument_count = clinical_count = citable_count = 0
    for url in urls:
        path = path_from_url(url)
        label = str(path.relative_to(ROOT))
        if not path.exists():
            errors.append(f"{label}: URL sin archivo")
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        parser = PageParser()
        parser.feed(source)
        page_text = visible_text(source)
        robots_meta = parser.meta.get("robots", "").casefold()
        if "noindex" in robots_meta or "nosnippet" in robots_meta:
            errors.append(f"{label}: limita indexación o fragmentos")
        max_snippet = re.search(r"max-snippet\s*:\s*(-?\d+)", robots_meta)
        if max_snippet and int(max_snippet.group(1)) == 0:
            errors.append(f"{label}: impide fragmentos textuales")
        if len(page_text) < 250:
            warnings.append(f"{label}: poco texto visible para recuperación ({len(page_text)} caracteres)")
        if not parser.jsonld or any(payload is None for payload in parser.jsonld):
            errors.append(f"{label}: JSON-LD ausente o inválido")

        public_path = urlparse(url).path
        is_article = "/repositorio/articulos/" in public_path
        is_clinical = public_path.startswith("/pruebas-clinicas/") and public_path != "/pruebas-clinicas/"
        is_instrument = public_path.startswith("/instrumentos/") and public_path not in (
            "/instrumentos/", "/instrumentos/rendimiento/"
        )

        if is_article:
            article_count += 1
            citable_count += 1
            articles = nodes_of_type(parser, "Article")
            if not articles:
                errors.append(f"{label}: falta schema Article")
            else:
                article = articles[0]
                for field in (
                    "headline", "description", "datePublished", "dateModified", "author", "publisher",
                    "citation", "isBasedOn", "sameAs", "mainEntityOfPage",
                ):
                    if not article.get(field):
                        errors.append(f"{label}: Article sin {field}")
            for marker in (
                'class="clinical-answer"', 'class="answer-lead"', "Qué no permite afirmar",
                "Fuente primaria", 'class="editorial-responsibility"',
            ):
                if marker not in source:
                    errors.append(f"{label}: falta bloque citable {marker!r}")

        if is_clinical:
            clinical_count += 1
            citable_count += 1
            pages = nodes_of_type(parser, "MedicalWebPage")
            if not pages:
                errors.append(f"{label}: falta schema MedicalWebPage")
            else:
                page = pages[0]
                for field in (
                    "name", "description", "url", "dateModified", "lastReviewed", "inLanguage",
                    "author", "reviewedBy", "publisher", "about", "citation", "isPartOf",
                ):
                    if not page.get(field):
                        errors.append(f"{label}: MedicalWebPage sin {field}")
            for marker in ("Pregunta clínica", "Fuente verificada", 'class="clinical-lead"', 'class="editorial-responsibility"'):
                if marker not in source and marker.replace("Fuente verificada", "Fuentes verificadas") not in source:
                    errors.append(f"{label}: falta bloque citable {marker!r}")

        if is_instrument:
            instrument_count += 1
            citable_count += 1
            if not nodes_of_type(parser, "MedicalWebPage"):
                errors.append(f"{label}: falta schema MedicalWebPage")
            for marker in ("Fuente", 'class="editorial-responsibility"', "Última revisión"):
                if marker not in source:
                    errors.append(f"{label}: falta señal de confianza {marker!r}")

    homepage = PageParser()
    homepage.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    organizations = nodes_of_type(homepage, "Organization")
    if not organizations or len(organizations[0].get("sameAs", [])) < 2:
        errors.append("index.html: entidad Organization sin perfiles corroboradores")
    profile = PageParser()
    profile.feed((ROOT / "sobre-fran/index.html").read_text(encoding="utf-8"))
    people = nodes_of_type(profile, "Person")
    if not people or len(people[0].get("sameAs", [])) < 2:
        errors.append("sobre-fran/index.html: entidad Person sin perfiles corroboradores")

    if args.live:
        audit_live_delivery(errors)

    print(
        f"AEO/GEO auditado: {len(urls)} URLs recuperables; "
        f"{citable_count} fichas clínicas citables "
        f"({article_count} análisis, {instrument_count} instrumentos, {clinical_count} pruebas)"
        f"{' y entrega en producción' if args.live else ''}."
    )
    for warning in warnings:
        print(f"WARN {warning}")
    for error in errors:
        print(f"ERROR {error}")
    print(f"Resultado IA: {len(errors)} errores, {len(warnings)} avisos.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
