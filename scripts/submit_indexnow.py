#!/usr/bin/env python3
"""Notifica a IndexNow las URLs canónicas publicadas por FisioLógico."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://www.elfisiologico.com"
ENDPOINT = "https://api.indexnow.org/indexnow"
KEY = "2af7d992efd2cc18e68bd60b12da63a9"
KEY_LOCATION = f"{DOMAIN}/{KEY}.txt"


def sitemap_urls() -> list[str]:
    tree = ET.parse(ROOT / "sitemap.xml")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [node.text for node in tree.findall("s:url/s:loc", namespace) if node.text]


def payload(urls: list[str]) -> dict[str, object]:
    return {
        "host": "www.elfisiologico.com",
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="notifica todas las URLs del sitemap")
    parser.add_argument("--dry-run", action="store_true", help="valida el envío sin hacer una petición")
    parser.add_argument("urls", nargs="*", help="URLs canónicas concretas")
    args = parser.parse_args()

    urls = sitemap_urls() if args.all else args.urls
    if not urls:
        parser.error("indica --all o una o varias URLs")
    invalid = [url for url in urls if not url.startswith(f"{DOMAIN}/") and url != f"{DOMAIN}/"]
    if invalid:
        parser.error(f"URL fuera del dominio: {invalid[0]}")
    if len(urls) > 10_000:
        parser.error("IndexNow admite un máximo de 10.000 URLs por petición")
    if (ROOT / f"{KEY}.txt").read_text(encoding="utf-8").strip() != KEY:
        parser.error("el archivo de verificación de la clave no coincide")

    body = json.dumps(payload(urls), ensure_ascii=False).encode("utf-8")
    if args.dry_run:
        print(f"IndexNow preparado: {len(urls)} URLs, clave {KEY_LOCATION}")
        return

    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "FisioLogico-IndexNow/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        if error.code in (200, 202):
            status = error.code
        else:
            raise
    print(f"IndexNow aceptó {len(urls)} URLs · HTTP {status}")
    sys.exit(0 if status in (200, 202) else 1)


if __name__ == "__main__":
    main()
