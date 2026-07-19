#!/usr/bin/env python3
"""Puerta única de auditoría para publicar una versión consolidada de FisioLógico."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BUILD_COMMANDS = [
    ["python3", "scripts/build_instruments.py"],
    ["python3", "scripts/build_clinical_tests.py"],
    ["python3", "scripts/build_site.py"],
    ["python3", "scripts/sync_navigation.py"],
]

AUDIT_COMMANDS = [
    ["python3", "scripts/security_audit.py"],
    ["python3", "scripts/validate_content.py"],
    ["python3", "scripts/validate_clinical_tests.py"],
    ["python3", "scripts/validate_pain_explorer.py"],
    ["python3", "scripts/ui_contract_audit.py"],
    ["python3", "scripts/seo_audit.py"],
    ["python3", "scripts/ai_search_audit.py"],
    ["node", "scripts/test_instrument_calculators.js"],
    ["python3", "scripts/build_public_site.py", "--output", "output/public-site"],
    ["git", "diff", "--check"],
]


def run(command: list[str]) -> None:
    print(f"\n→ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenera y audita toda la web antes de un lanzamiento global."
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Regenera instrumentos, pruebas clínicas, repositorio y navegación antes de auditar.",
    )
    args = parser.parse_args()

    if args.build:
        for command in BUILD_COMMANDS:
            run(command)

    for command in AUDIT_COMMANDS:
        run(command)

    print("\n✓ Web completa lista para una publicación consolidada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
