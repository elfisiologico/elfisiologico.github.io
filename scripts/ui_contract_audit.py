#!/usr/bin/env python3
"""Comprueba invariantes visuales de todas las páginas públicas antes de publicar."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from security_audit import is_public_path


ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
STYLES = ROOT / "styles.css"
IGNORED_HTML_ROOTS = {"tmp", "output", ".playwright-cli", ".playwright-mcp", ".git"}
IGNORED_HTML_FILES = {"articulo base.html", "categoria base.html", "categoria base v.7.html"}


def plain_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


def local_reference(path: Path, raw: str, base_dir: Path | None = None) -> Path | None:
    """Resuelve enlaces y recursos locales sin confundir URLs externas o anclas."""
    value = raw.strip()
    if not value or value.startswith(("#", "//", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return None
    reference = unquote(parsed.path)
    if not reference:
        return path
    target = ROOT / reference.lstrip("/") if reference.startswith("/") else (base_dir or path.parent) / reference
    if reference.endswith("/") or target.is_dir():
        target /= "index.html"
    return target.resolve()


def main() -> None:
    errors: list[str] = []
    css = STYLES.read_text(encoding="utf-8")
    version = hashlib.sha256(STYLES.read_bytes()).hexdigest()[:10]
    css_contract = (
        ".protocol-group li{display:grid",
        "grid-template-columns:minmax(150px,190px) minmax(0,1fr)",
        ".protocol-period,.protocol-exercises{display:block",
        "@media(max-width:620px)",
        ".protocol-group li{display:block}",
        ".measurement-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))",
        "@media(max-width:700px){.measurement-group-heading,.measurement-grid{grid-template-columns:1fr}",
    )
    for rule in css_contract:
        if rule not in css: errors.append(f"styles.css no conserva el contrato: {rule}")

    protocol_slugs = {
        article["slug"]
        for path in ARTICLES.glob("*.json")
        if (article := json.loads(path.read_text(encoding="utf-8"))).get("intervention_protocol")
        and article.get("rubric_v2", {}).get("status") == "complete"
    }
    rendered_protocols: set[str] = set()
    measurement_counts = {
        article["slug"]: sum(len(group["items"]) for group in article["measurement_battery"]["groups"])
        for path in ARTICLES.glob("*.json")
        if (article := json.loads(path.read_text(encoding="utf-8"))).get("measurement_battery")
        and article.get("rubric_v2", {}).get("status") == "complete"
    }
    rendered_measurements: set[str] = set()
    html_files = sorted(
        path for path in ROOT.rglob("*.html")
        if not any(part in IGNORED_HTML_ROOTS for part in path.relative_to(ROOT).parts)
        and path.name not in IGNORED_HTML_FILES
        and is_public_path(path.relative_to(ROOT).as_posix())
    )
    for path in html_files:
        html = path.read_text(encoding="utf-8")
        base_dir = path.parent
        base_match = re.search(r'<base\b[^>]*href=["\']([^"\']+)["\']', html, re.I)
        if base_match:
            base_path = unquote(urlparse(base_match.group(1)).path)
            base_dir = (ROOT / base_path.lstrip("/") if base_path.startswith("/") else path.parent / base_path).resolve()
            if not base_dir.exists():
                errors.append(f"{path.relative_to(ROOT)} declara una base local inexistente: {base_match.group(1)}")
        reference_html = re.sub(r'<base\b[^>]*>', '', html, flags=re.I)
        for attribute, raw in re.findall(r'\b(href|src)=["\']([^"\']+)["\']', reference_html, re.I):
            target = local_reference(path, raw, base_dir)
            if target is not None and (ROOT not in target.parents and target != ROOT):
                errors.append(f"{path.relative_to(ROOT)} contiene una referencia fuera del proyecto: {raw}")
            elif target is not None and not target.exists():
                errors.append(f"{path.relative_to(ROOT)} contiene {attribute} local roto: {raw}")
        navigation_labels = (
            ">Enfoque<", ">Tratamientos<", ">Pacientes<", ">Profesionales<",
            ">Con lógica<", ">Sobre Fran<", ">Pedir cita<",
        )
        if 'class="site-header global-header' not in html:
            errors.append(f"{path.relative_to(ROOT)} no usa la cabecera global")
        if 'class="menu-button"' not in html or 'class="main-nav"' not in html:
            errors.append(f"{path.relative_to(ROOT)} no conserva el menú responsive global")
        missing_navigation = [label[1:-1] for label in navigation_labels if label not in html]
        if missing_navigation:
            errors.append(
                f"{path.relative_to(ROOT)} pierde enlaces globales: {', '.join(missing_navigation)}"
            )
        if "script.js" not in html:
            errors.append(f"{path.relative_to(ROOT)} no carga el controlador de navegación")
        if 'rel="stylesheet"' in html and "styles.css" in html:
            match = re.search(r"styles\.css\?v=([a-f0-9]{10})", html)
            if not match or match.group(1) != version:
                errors.append(f"{path.relative_to(ROOT)} usa una versión obsoleta de styles.css")
        if 'class="intervention-protocol"' not in html:
            pass
        else:
            slug = path.stem
            rendered_protocols.add(slug)
            if html.count('id="protocolo"') != 1:
                errors.append(f"{slug}: la sección de protocolo debe tener un único id")
            groups = re.search(
                r'<div class="protocol-groups">(.*?)<div class="protocol-shared">',
                html,
                re.S,
            )
            if not groups:
                errors.append(f"{slug}: no se encontró la matriz de progresión")
            else:
                if re.search(r"</(?:strong|span)>\s*<(?:strong|span)", groups.group(1)):
                    errors.append(f"{slug}: conserva texto de progresión en elementos inline frágiles")
                steps = re.findall(r"<li>(.*?)</li>", groups.group(1), re.S)
                if not steps:
                    errors.append(f"{slug}: el protocolo no contiene tramos")
                for index, step in enumerate(steps, 1):
                    period = re.fullmatch(
                        r'<p class="protocol-period">(.*?)</p><p class="protocol-exercises">(.*?)</p>',
                        step,
                        re.S,
                    )
                    if not period:
                        errors.append(f"{slug}: tramo {index} no separa periodo y ejercicios en bloques seguros")
                    elif not plain_text(period.group(1)) or not plain_text(period.group(2)):
                        errors.append(f"{slug}: tramo {index} contiene un bloque vacío")
        if 'class="measurement-battery"' in html:
            slug = path.stem
            rendered_measurements.add(slug)
            if html.count('id="mediciones"') != 1:
                errors.append(f"{slug}: la batería de medición debe tener un único id")
            battery = re.search(r'<section class="measurement-battery".*?</section>',html,re.S)
            if not battery:
                errors.append(f"{slug}: no se encontró la batería de medición completa")
            else:
                cards=re.findall(r'<article class="measurement-card">(.*?)</article>',battery.group(0),re.S)
                if len(cards)!=measurement_counts.get(slug,0):
                    errors.append(f"{slug}: esperaba {measurement_counts.get(slug,0)} instrumentos y renderizó {len(cards)}")
                for index,card in enumerate(cards,1):
                    if not all(label in card for label in ("Qué mide","En qué consiste","Cómo se interpreta","Lectura prudente")):
                        errors.append(f"{slug}: instrumento {index} no conserva los cuatro niveles de lectura")

    missing = protocol_slugs - rendered_protocols
    unexpected = rendered_protocols - protocol_slugs
    if missing: errors.append(f"faltan protocolos renderizados: {', '.join(sorted(missing))}")
    if unexpected: errors.append(f"hay protocolos sin fuente canónica: {', '.join(sorted(unexpected))}")
    missing_measurements=set(measurement_counts)-rendered_measurements
    unexpected_measurements=rendered_measurements-set(measurement_counts)
    if missing_measurements: errors.append(f"faltan baterías de medición renderizadas: {', '.join(sorted(missing_measurements))}")
    if unexpected_measurements: errors.append(f"hay baterías de medición sin fuente canónica: {', '.join(sorted(unexpected_measurements))}")

    if errors:
        print("ERROR contrato visual")
        for error in errors: print(f"- {error}")
        sys.exit(1)
    print(
        f"Contrato visual OK: {len(html_files)} páginas, "
        f"{len(rendered_protocols)} protocolos, {len(rendered_measurements)} baterías de medición "
        f"y styles.css?v={version}."
    )


if __name__ == "__main__":
    main()
