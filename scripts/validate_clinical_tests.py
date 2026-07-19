#!/usr/bin/env python3
"""Valida la colección canónica de sospechas y pruebas clínicas."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from html import escape
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "clinical-tests.json"
ALLOWED_EVIDENCE = {"green", "amber", "red"}
ALLOWED_EDITORIAL_STATUS = {"draft", "evidence_review", "clinical_review", "ready", "published", "update_required", "retired"}


def region_key(value: str) -> str:
    plain = unicodedata.normalize("NFD", value)
    plain = "".join(character for character in plain if unicodedata.category(character) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def main() -> None:
    errors: list[str] = []
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schema_version") != "2.0": errors.append("schema_version debe ser 2.0")
    try:
        date.fromisoformat(data.get("updated_at", ""))
    except ValueError:
        errors.append("updated_at debe usar YYYY-MM-DD")
    suspicions = data.get("suspicions")
    if not isinstance(suspicions, list) or not suspicions:
        errors.append("suspicions debe ser una lista no vacía")
        suspicions = []
    slugs: list[str] = []
    for index, suspicion in enumerate(suspicions, 1):
        label = f"suspicions[{index}]"
        for field in ("editorial_status", "slug", "name", "short_name", "region", "purpose", "evidence_status", "summary"):
            if not suspicion.get(field): errors.append(f"{label}: falta {field}")
        status = suspicion.get("editorial_status")
        if status not in ALLOWED_EDITORIAL_STATUS: errors.append(f"{label}: editorial_status no permitido")
        slug = suspicion.get("slug", "")
        slugs.append(slug)
        if status != "published":
            candidates = suspicion.get("candidate_tests", [])
            if not isinstance(candidates, list) or len(candidates) < 3:
                errors.append(f"{label}: un expediente en revisión requiere al menos tres pruebas candidatas")
            sources = suspicion.get("review_sources", [])
            if not isinstance(sources, list) or not sources:
                errors.append(f"{label}: un expediente en revisión requiere fuentes")
            for source_index, source in enumerate(sources, 1):
                pmid = source.get("pmid", "")
                if source.get("url") != f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/":
                    errors.append(f"{label}.review_sources[{source_index}]: fuente PubMed no canónica")
            if not suspicion.get("blocking_reason"):
                errors.append(f"{label}: falta blocking_reason")
            continue
        for field in ("next_review_at", "primary_source", "tests"):
            if not suspicion.get(field): errors.append(f"{label}: una sospecha publicada requiere {field}")
        try: date.fromisoformat(suspicion.get("next_review_at", ""))
        except ValueError: errors.append(f"{label}: next_review_at debe usar YYYY-MM-DD")
        page = ROOT / "pruebas-clinicas" / slug / "index.html"
        if not page.exists(): errors.append(f"{label}: falta la ficha pública {page.relative_to(ROOT)}")
        source = suspicion.get("primary_source", {})
        pmid = source.get("pmid", "")
        if source.get("url") != f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/":
            errors.append(f"{label}: fuente PubMed no canónica")
        tests = suspicion.get("tests", [])
        if len(tests) < 3: errors.append(f"{label}: requiere al menos tres pruebas o componentes")
        names: list[str] = []
        for test_index, test in enumerate(tests, 1):
            location = f"{label}.tests[{test_index}]"
            for field in ("name", "role", "direction", "evidence", "execution", "positive", "metrics", "note"):
                if not test.get(field): errors.append(f"{location}: falta {field}")
            if test.get("evidence") not in ALLOWED_EVIDENCE:
                errors.append(f"{location}: evidence no permitido")
            if len(test.get("note", "")) < 80:
                errors.append(f"{location}: note requiere una cautela clínica explícita")
            if not 90 <= len(test.get("execution", "")) <= 260:
                errors.append(f"{location}: execution debe ser breve, pero suficientemente orientativa")
            if not 70 <= len(test.get("positive", "")) <= 220:
                errors.append(f"{location}: positive debe explicar qué observar sin sobrediagnosticar")
            metrics = test.get("metrics", {})
            if metrics.get("status") not in {"pooled", "range", "not_estimated"}:
                errors.append(f"{location}: metrics.status no permitido")
            for field in ("sensitivity", "specificity", "lr_positive", "lr_negative", "context", "source"):
                if not metrics.get(field): errors.append(f"{location}.metrics: falta {field}")
            metrics_source = metrics.get("source", {})
            metrics_pmid = metrics_source.get("pmid", "")
            if metrics_source.get("url") != f"https://pubmed.ncbi.nlm.nih.gov/{metrics_pmid}/":
                errors.append(f"{location}.metrics: fuente PubMed no canónica")
            names.append(test.get("name", "").casefold())
        if len(names) != len(set(names)): errors.append(f"{label}: pruebas duplicadas")
        if page.exists():
            rendered = page.read_text(encoding="utf-8")
            if rendered.count('class="test-procedure"') != len(tests):
                errors.append(f"{label}: la ficha no materializa todas las ejecuciones sin JavaScript")
            if rendered.count('class="diagnostic-metrics"') != len(tests):
                errors.append(f"{label}: la ficha no materializa todas las métricas diagnósticas")
            if rendered.count('class="test-caution"') != len(tests):
                errors.append(f"{label}: la ficha no materializa todas las cautelas clínicas")
            for test in tests:
                if f'<h3>{escape(test["name"])}</h3>' not in rendered:
                    errors.append(f'{label}: falta la prueba "{test["name"]}" en la ficha')
    if len(slugs) != len(set(slugs)): errors.append("slugs duplicados")
    published = [item for item in suspicions if item.get("editorial_status") == "published"]
    collection = (ROOT / "pruebas-clinicas" / "index.html").read_text(encoding="utf-8")
    if collection.count("data-suspicion-card") != len(published):
        errors.append("la portada no materializa todas las sospechas publicadas sin JavaScript")
    if f'<strong data-clinical-count>{len(published)}</strong>' not in collection:
        errors.append("el contador estático de la portada no coincide con las sospechas publicadas")
    visual_regions = set(re.findall(r'data-region-link="([^"]+)"', collection))
    published_regions = {region_key(item["region"]) for item in published}
    if visual_regions != published_regions:
        errors.append("la navegación visual no cubre todas las regiones publicadas")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for item in published:
        url = f'https://www.elfisiologico.com/pruebas-clinicas/{item["slug"]}/'
        if url not in sitemap: errors.append(f'sitemap: falta {url}')
    print(f"Validadas {len(suspicions)} sospechas clínicas y {sum(len(x.get('tests', [])) for x in suspicions)} componentes.")
    for error in errors: print(f"ERROR {error}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__": main()
