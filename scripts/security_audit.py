#!/usr/bin/env python3
"""Bloquea secretos y archivos internos antes de publicar FisioLógico."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]

INTERNAL_PREFIXES = (
    ".agents/",
    ".codex/",
    ".git/",
    ".github/",
    "content/",
    "data/",
    "demo-reserva/",
    "docs/",
    "fuentes-pdf-repositorio/",
    "scripts/",
    "supabase/",
    "tests/",
)

INTERNAL_EXACT = {
    ".gitignore",
    "README.md",
    "articulo base.html",
    "categoria base.html",
    "categoria base v.7.html",
}

PUBLIC_SUFFIXES = {
    ".avif",
    ".css",
    ".html",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".png",
    ".svg",
    ".txt",
    ".webmanifest",
    ".webp",
    ".woff",
    ".woff2",
    ".xml",
}

PUBLIC_EXTENSIONLESS = {".nojekyll", "CNAME"}

SECRET_PATTERNS = {
    "clave privada": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "clave secreta Supabase": re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}\b"),
    "clave service_role literal": re.compile(r"\bservice_role\s*[:=]\s*['\"][A-Za-z0-9._-]{20,}['\"]", re.I),
    "secreto Stripe": re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "firma webhook Stripe": re.compile(r"\bwhsec_[A-Za-z0-9]{16,}\b"),
    "token GitHub": re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    "clave AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "clave API Google": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "URL con contraseña": re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s/:@]+:[^\s/@]+@", re.I),
}

JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def git_paths(include_untracked: bool = False) -> list[str]:
    command = ["git", "ls-files", "-z"]
    if include_untracked:
        command = ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
    return sorted(path for path in result.stdout.decode().split("\0") if path)


def is_internal_repository_path(path: str) -> bool:
    name = PurePosixPath(path).name
    return (
        path.startswith("docs/")
        or path.startswith("demo-reserva/")
        or path.startswith("supabase/.temp/")
        or path.startswith("supabase/.branches/")
        or path in INTERNAL_EXACT - {"README.md", ".gitignore"}
        or (path.startswith("patients/explora-dolor/") and "calibrador" in name)
        or (path.startswith("patients/explora-dolor/") and "calibrator" in name)
        or path.startswith("patients/explora-dolor/data/") and ("calibration" in name or name.endswith(".md"))
        or path in {
            "patients/explora-dolor/assets/anatomy-head-upper-body.png",
            "patients/explora-dolor/assets/anatomy-head-upper-body.svg",
        }
    )


def is_public_path(path: str) -> bool:
    normalized = path.lstrip("./")
    if not normalized or normalized in INTERNAL_EXACT:
        return False
    if normalized.startswith(INTERNAL_PREFIXES):
        return False
    name = PurePosixPath(normalized).name
    if name in PUBLIC_EXTENSIONLESS:
        return True
    if normalized.startswith("patients/explora-dolor/") and (
        "calibrador" in name
        or "calibrator" in name
        or "calibration" in name
        or name.endswith(".md")
        or name.startswith("anatomy-head-upper-body.")
    ):
        return False
    return PurePosixPath(normalized).suffix.lower() in PUBLIC_SUFFIXES


def decode_jwt_role(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def scan_text(path: str, text: str, public: bool = False) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{path}: {label}")
    for token in JWT_PATTERN.findall(text):
        if decode_jwt_role(token) == "service_role":
            findings.append(f"{path}: JWT de service_role")
            break
    if public and re.search(r"[A-Z0-9._%+-]+@(?:gmail|hotmail|outlook)\.[A-Z]{2,}", text, re.I):
        findings.append(f"{path}: correo personal en el artefacto público")
    return findings


def scan_file(path: Path, label: str, public: bool = False) -> list[str]:
    if path.stat().st_size > 5_000_000:
        return []
    data = path.read_bytes()
    if b"\0" in data[:4096]:
        return []
    return scan_text(label, data.decode("utf-8", errors="ignore"), public=public)


def audit_repository() -> list[str]:
    findings: list[str] = []
    tracked = git_paths()
    for path in tracked:
        if is_internal_repository_path(path):
            findings.append(f"{path}: archivo interno versionado en el repositorio público")
    for path in git_paths(include_untracked=True):
        candidate = ROOT / path
        if candidate.is_file():
            findings.extend(scan_file(candidate, path))
    return findings


def audit_public_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = candidate.relative_to(root).as_posix()
        if not is_public_path(relative):
            findings.append(f"{relative}: ruta no permitida en el artefacto público")
            continue
        findings.extend(scan_file(candidate, relative, public=True))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita secretos y exposición de archivos internos.")
    parser.add_argument("--public-root", type=Path, help="Audita exclusivamente un artefacto web ya construido.")
    args = parser.parse_args()

    findings = audit_public_tree(args.public_root.resolve()) if args.public_root else audit_repository()
    if findings:
        print("Auditoría de seguridad: BLOQUEADA")
        for finding in findings:
            print(f"- {finding}")
        return 1

    scope = f"artefacto {args.public_root}" if args.public_root else "repositorio y archivos publicables"
    print(f"Auditoría de seguridad OK: {scope}; sin secretos ni rutas internas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
