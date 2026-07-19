#!/usr/bin/env python3
"""Calcula cobertura editorial real de pruebas clínicas."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
coverage = json.loads((ROOT / "data/clinical-test-coverage.json").read_text(encoding="utf-8"))
collection = json.loads((ROOT / "data/clinical-tests.json").read_text(encoding="utf-8"))
status = {item["slug"]: item["editorial_status"] for item in collection["suspicions"]}

targets = [(region["name"], target) for region in coverage["regions"] for target in region["targets"]]
counts = Counter(status.get(target["slug"], "not_started") for _, target in targets)
critical = [target for _, target in targets if target["priority"] == "critical"]
critical_published = sum(status.get(target["slug"]) == "published" for target in critical)
priority = [target for _, target in targets if target["priority"] in {"critical", "high"}]
priority_advanced = sum(status.get(target["slug"]) in {"clinical_review", "ready", "published"} for target in priority)
regions_covered = sum(any(status.get(target["slug"]) == "published" for target in region["targets"]) for region in coverage["regions"])

print(f"Cobertura publicada: {counts['published']}/{len(targets)} sospechas.")
print(f"Regiones con recorrido publicado: {regions_covered}/{len(coverage['regions'])}.")
print(f"Críticas publicadas: {critical_published}/{len(critical)}.")
print(f"Prioritarias avanzadas: {priority_advanced}/{len(priority)}.")
for region in coverage["regions"]:
    region_counts = Counter(status.get(target["slug"], "not_started") for target in region["targets"])
    print(f"- {region['name']}: {region_counts['published']} publicadas, {region_counts['evidence_review']} en evidencia, {region_counts['not_started']} sin iniciar")

complete = regions_covered == len(coverage["regions"]) and critical_published == len(critical) and priority_advanced / len(priority) >= .8
print(f"Estado global: {'COMPLETE' if complete else 'IN_PROGRESS'}")
sys.exit(0)
