#!/usr/bin/env python3
"""Validación mínima y sin dependencias del contenido del orientador de dolor."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "content" / "pain-explorer"
REQUIRED_MUSCLE = {
    "id", "name", "summary", "pain_zones", "sensations", "daily_impact",
    "related_activities", "aggravating_factors", "initial_guidance",
    "seek_assessment", "similar_patterns", "alternatives"
}


def validate(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    zones = {zone["id"] for zone in data.get("zones", [])}
    if not zones:
        errors.append("no hay zonas")
    if len(data.get("disclaimer", "")) < 80:
        errors.append("el aviso clínico es demasiado breve")
    if not data.get("red_flags"):
        errors.append("faltan señales de alarma")
    muscle_ids: set[str] = set()
    for muscle in data.get("muscles", []):
        label = muscle.get("id", "sin-id")
        missing = REQUIRED_MUSCLE - set(muscle)
        if missing:
            errors.append(f"{label}: faltan {', '.join(sorted(missing))}")
            continue
        if label in muscle_ids:
            errors.append(f"{label}: id duplicado")
        muscle_ids.add(label)
        related_zones = set(muscle["pain_zones"]["primary"] + muscle["pain_zones"]["secondary"])
        unknown = related_zones - zones
        if unknown:
            errors.append(f"{label}: zonas desconocidas {', '.join(sorted(unknown))}")
        for field in ("daily_impact", "aggravating_factors", "initial_guidance", "seek_assessment", "alternatives"):
            if not muscle[field]:
                errors.append(f"{label}: {field} está vacío")
    try:
        date.fromisoformat(data.get("review", {}).get("updated_at", ""))
    except ValueError:
        errors.append("review.updated_at debe usar YYYY-MM-DD")
    if data.get("review", {}).get("status") == "published":
        errors.append("el piloto no debe marcarse como publicado antes de la revisión final")
    return errors


def validate_corpus(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    chapters = data.get("chapters", [])
    if data.get("chapter_count") != len(chapters):
        errors.append("chapter_count no coincide con el número de capítulos")
    if data.get("publication_status") != "internal_noindex":
        errors.append("el corpus importado debe mantenerse como internal_noindex")
    ids: set[str] = set()
    required = {"id", "title", "chapter_type", "region", "source_file", "word_count", "headings", "available_sections", "section_previews", "patient_content", "editorial_status"}
    for chapter in chapters:
        label = chapter.get("id", "sin-id")
        missing = required - set(chapter)
        if missing:
            errors.append(f"{label}: faltan {', '.join(sorted(missing))}")
        if label in ids:
            errors.append(f"{label}: id duplicado")
        ids.add(label)
        if chapter.get("editorial_status") != "importado_pendiente_revision":
            errors.append(f"{label}: estado editorial inesperado")
        patient = chapter.get("patient_content", {})
        for field in ("intro", "first_steps", "when_to_consult"):
            if not patient.get(field):
                errors.append(f"{label}: falta patient_content.{field}")
        for field, value in patient.items():
            if not isinstance(value, (str, list)):
                errors.append(f"{label}: patient_content.{field} debe ser texto o lista")
            if isinstance(value, list) and not all(isinstance(item, str) and item.strip() for item in value):
                errors.append(f"{label}: patient_content.{field} contiene elementos inválidos")
    if len(chapters) < 60:
        errors.append("cobertura incompleta: se esperaban al menos 60 capítulos")
    return errors


def main() -> None:
    failed = False
    files = sorted(DATA_DIR.glob("*.json"))
    for path in files:
        errors = validate_corpus(path) if path.name == "corpus-index.json" else validate(path)
        print(f"{'ERROR' if errors else 'OK'} {path.name}" + (f": {'; '.join(errors)}" if errors else ""))
        failed |= bool(errors)
    print(f"Validados {len(files)} conjuntos del orientador.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
