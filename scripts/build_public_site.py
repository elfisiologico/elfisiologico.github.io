#!/usr/bin/env python3
"""Construye el único artefacto que puede publicarse en GitHub Pages."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from security_audit import ROOT, audit_public_tree, is_public_path


def run_git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def source_paths(ref: str | None) -> list[str]:
    if ref:
        output = run_git("ls-tree", "-r", "--name-only", "-z", ref)
    else:
        output = run_git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    return sorted(path for path in output.decode().split("\0") if path and is_public_path(path))


def source_bytes(path: str, ref: str | None) -> bytes:
    return run_git("show", f"{ref}:{path}") if ref else (ROOT / path).read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea un directorio de publicación sin fuentes ni material interno.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ref", help="Construye desde una referencia Git; sin esta opción usa el árbol de trabajo.")
    args = parser.parse_args()

    output = args.output.resolve()
    output_root = (ROOT / "output").resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    allowed = output == (ROOT / "_site").resolve() or output_root in output.parents or temporary_root in output.parents
    if not allowed:
        raise SystemExit("La salida solo puede escribirse en _site, output/ o el directorio temporal del sistema.")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    paths = source_paths(args.ref)
    for path in paths:
        destination = output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_bytes(path, args.ref))

    findings = audit_public_tree(output)
    if findings:
        print("El artefacto público contiene elementos no permitidos:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(f"Artefacto público construido: {len(paths)} archivos en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
