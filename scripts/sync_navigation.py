#!/usr/bin/env python3
"""Unifica la navegación global y su versión de estilos en toda la web."""
from __future__ import annotations

import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE_VERSION = hashlib.sha256((ROOT / "styles.css").read_bytes()).hexdigest()[:10]


def navigation_for(path: Path) -> str:
    relative = path.relative_to(ROOT)
    prefix = "../" * (len(relative.parts) - 1)
    top = relative.parts[0] if len(relative.parts) > 1 else ""
    patients_current = ' aria-current="page"' if top == "patients" else ""
    treatments_current = ' aria-current="page"' if top == "tratamientos" else ""
    professionals_current = ' aria-current="page"' if top in {"profesionales", "repositorio", "instrumentos", "pruebas-clinicas"} else ""
    thinking_current = ' aria-current="page"' if top == "con-logica" else ""
    about_current = ' aria-current="page"' if top == "sobre-fran" else ""
    training_current = ' aria-current="page"' if top == "formacion" else ""
    home = "" if not prefix else f"{prefix}index.html"
    brand_home = "#inicio" if not prefix else prefix
    flow_class = "" if not prefix else " global-header--flow"
    return (
        f'<header class="site-header global-header{flow_class}" data-header><div class="shell header-inner">'
        f'<a class="brand" href="{brand_home}" aria-label="FisioLógico, inicio"><picture>'
        f'<source media="(max-width: 820px)" srcset="{prefix}assets/logo-fisiologico-cuadrado.png">'
        f'<img src="{prefix}assets/logo-fisiologico-horizontal.png" alt="FisioLógico" width="1100" height="220">'
        '</picture></a>'
        '<button class="menu-button" type="button" aria-expanded="false" aria-controls="nav-principal">'
        '<span class="sr-only">Abrir menú</span><span></span><span></span></button>'
        '<nav id="nav-principal" class="main-nav" aria-label="Navegación principal">'
        f'<a href="{home}#enfoque">Enfoque</a>'
        f'<a href="{prefix}tratamientos/"{treatments_current}>Tratamientos</a>'
        f'<a href="{prefix}patients/"{patients_current}>Pacientes</a>'
        f'<a href="{prefix}profesionales/"{professionals_current}>Profesionales</a>'
        f'<a href="{prefix}con-logica/"{thinking_current}>Con lógica</a>'
        f'<a href="{prefix}sobre-fran/"{about_current}>Sobre Fran</a>'
        f'<a href="{prefix}formacion/"{training_current}>Formación</a>'
        f'<a class="nav-cta" href="{home}#contacto">Pedir cita</a>'
        '</nav></div></header>'
    )


def sync_navigation() -> int:
    changed = 0
    for path in ROOT.rglob("*.html"):
        if any(part in {"tmp", ".git", ".playwright-mcp", "output"} for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        updated = source
        if re.search(r'<header class="[^"]*(?:site-header|editorial-header|thinking-header)', source):
            updated = re.sub(
                r'<header class="[^"]*(?:site-header|editorial-header|thinking-header)[^"]*".*?</header>',
                navigation_for(path),
                source,
                count=1,
                flags=re.DOTALL,
            )
        else:
            skip_link = re.search(r'(<a class="skip-link".*?</a>)', updated, flags=re.DOTALL)
            if skip_link:
                updated = updated[:skip_link.end()] + navigation_for(path) + updated[skip_link.end():]
            else:
                updated = re.sub(r'(<body(?:\s[^>]*)?>)', r'\1' + navigation_for(path), updated, count=1)
        if 'script.js' not in updated:
            updated = updated.replace('</body>', f'<script src="{prefix_for(path)}script.js?v=8" defer></script></body>', 1)
        updated = re.sub(r'styles\.css\?v=[^"\']+', f'styles.css?v={STYLE_VERSION}', updated)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def prefix_for(path: Path) -> str:
    relative = path.relative_to(ROOT)
    return "../" * (len(relative.parts) - 1)


if __name__ == "__main__":
    print(f"Navegación sincronizada en {sync_navigation()} páginas.")
