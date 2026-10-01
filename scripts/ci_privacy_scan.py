#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release privacy scan for tms-presentation-skills.

Fails when public trees contain personal/host-local markers or secrets-shaped text.
Ignore-rules and migration notes may mention deprecated ids / local-state dir names.
Secrets and host-local personal paths are never allowlisted.

Design constraints (do not weaken):
  - Never hardcode a real username, hostname, token, or absolute personal path
    in this file. A real identifier would leak machine identity into the repo,
    and a raw-string pattern can fail to match itself (word boundaries around
    an embedded backslash-b make the literal look like a longer word).
  - Never print raw matched secrets. Findings are redacted so CI logs do not
    re-leak whatever was accidentally committed.
  - Machine-specific extra denylist lives in scripts/.privacy-deny.local
    (gitignored). Put personal usernames / hostnames there, not here.

Zero third-party dependencies.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_EXTS = {
    ".md", ".py", ".js", ".json", ".css", ".html", ".csv", ".txt", ".yml", ".yaml",
    ".gitignore", "",
}
SKIP_DIRS = {
    "node_modules", "dist", "__pycache__", ".git", ".venv", "venv",
    ".codebuddy", ".h3caiwork", ".playwright-mcp", ".claude", ".agents", ".mimocode",
}

# Files allowed to mention deprecated ids / local-state dir names
# (policy, ignore rules, migration). Secrets and host-local personal paths
# are still enforced on every file.
ALLOWLIST = {
    Path("CHANGELOG.md"),
    Path("README.md"),
    Path("docs") / "PUBLISHING.md",
    Path("scripts") / "ci_privacy_scan.py",
    Path(".gitignore"),
}

# Paths that must never be tracked by git.
FORBIDDEN_TRACKED = (
    re.compile(r"(^|/)scripts/_"),
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"\.(pem|key|p12|pfx)$", re.I),
    re.compile(r"(^|/)credentials\.json$"),
    re.compile(r"(^|/)(node_modules|__pycache__|dist)/"),
    re.compile(r"(^|/)\.(codebuddy|h3caiwork|playwright-mcp|claude|agents|mimocode)/"),
)

DEPRECATED = re.compile(
    r"\b(topreport|TopReport|TOPREPORT_|MIGA_NODE_|MIGA_BROWSER_|"
    r"top-slides-expert|TopSlidesPptx|TopSlides|TOPSLIDES_|TOP_SLIDES_|topskills)\b"
)
LOCAL_STATE = re.compile(r"\b(codebuddy|h3caiwork|playwright-mcp)\b", re.I)

# Host-local path prefixes. Capture the username segment so findings name the
# leak without needing a hardcoded personal identifier in this source file.
WIN_HOME = re.compile(r"[A-Za-z]:\\Users\\([^\\\/\s\"'<>|]{1,64})", re.I)
NIX_HOME = re.compile(r"/(?:home|Users)/([^\/\s\"'<>|]{1,64})")
APPDATA_PATH = re.compile(
    r"[A-Za-z]:\\(?:Users\\[^\\\/\s\"'<>|]+\\)?AppData\\",
    re.I,
)
WIN_PERSONAL_TREE = re.compile(
    r"[A-Za-z]:\\(?:Users|Documents|Desktop|OneDrive)\\[^\s\"'<>|]{1,120}",
    re.I,
)

# Placeholder / shared account names that are safe in docs and CI examples.
SAFE_HOME_SEGMENTS = {
    "public", "default", "default user", "all users", "allusers",
    "shared", "user", "username", "yourname", "example", "ubuntu",
    "runner", "admin", "administrator",
}

# Require a letter TLD so version tags like pkg@2.0.0 are not "emails".
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")
EMAIL_OK_SUFFIXES = (
    "example.com", "example.org", "example.net",
    "users.noreply.github.com", "noreply.github.com",
)

# Secrets-shaped tokens. Keep bodies generic — never a real secret.
API_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{10,}")
GH_TOKEN = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}")
GH_PAT = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")
NPM_TOKEN = re.compile(r"\bnpm_[A-Za-z0-9]{20,}")
AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
SECRET_ASSIGN = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
    r"password|passwd|private[_-]?key|session[_-]?token|refresh[_-]?token)\b"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9+/._\-]{12,}"
)


def redact(value: str) -> str:
    """Show shape only — never the raw secret/username body."""
    value = value.replace("\n", " ").strip()
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-1]}(len={len(value)})"


def iter_files():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.name.startswith(".privacy-deny") or p.name in {".env", ".npmrc"}:
            continue
        if p.suffix.lower() not in SCAN_EXTS and p.name not in {".gitignore", "LICENSE"}:
            continue
        yield rel, p


def load_local_denylist() -> set[str]:
    """Optional machine-specific extra terms from a gitignored local file.

    Format: one term per line. Lines starting with # are comments.
    File is never scanned and never committed (see .gitignore).
    """
    path = ROOT / "scripts" / ".privacy-deny.local"
    terms: set[str] = set()
    if not path.is_file():
        return terms
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return terms
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        terms.add(line)
    return terms


def check_tracked_paths() -> list[str]:
    """Fail if git tracks temp scripts, secrets, caches, or agent local state."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    errors: list[str] = []
    for raw in out.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace").replace("\\", "/")
        for pat in FORBIDDEN_TRACKED:
            if pat.search(rel):
                errors.append(f"git-tracked forbidden path: {rel}")
                break
    return errors


def scan_text(rel: Path, text: str, allow: bool, deny_extra: set[str]) -> list[str]:
    findings: list[tuple[int, str, str]] = []

    for m in WIN_HOME.finditer(text):
        user = m.group(1)
        if user.lower() not in SAFE_HOME_SEGMENTS:
            findings.append((m.start(), "Windows home username", redact(user)))
    for m in NIX_HOME.finditer(text):
        user = m.group(1)
        if user.lower() not in SAFE_HOME_SEGMENTS:
            findings.append((m.start(), "Unix/macOS home username", redact(user)))
    for m in APPDATA_PATH.finditer(text):
        findings.append((m.start(), "AppData path", redact(m.group(0))))
    for m in WIN_PERSONAL_TREE.finditer(text):
        findings.append((m.start(), "host-local personal path", redact(m.group(0))))

    for m in EMAIL.finditer(text):
        token = m.group(0)
        if any(token.endswith(suffix) or suffix in token for suffix in EMAIL_OK_SUFFIXES):
            continue
        findings.append((m.start(), "email-like token", redact(token)))

    secret_rules = (
        (API_KEY, "API key-shaped token"),
        (GH_TOKEN, "GitHub token-shaped"),
        (GH_PAT, "GitHub PAT-shaped"),
        (NPM_TOKEN, "npm token-shaped"),
        (AWS_KEY, "AWS access key-shaped"),
        (BEARER, "Bearer token-shaped"),
        (PRIVATE_KEY, "private key block"),
        (SECRET_ASSIGN, "secret assignment"),
    )
    for rule, label in secret_rules:
        for m in rule.finditer(text):
            findings.append((m.start(), label, redact(m.group(0))))

    for term in deny_extra:
        if not term:
            continue
        idx = 0
        while True:
            pos = text.find(term, idx)
            if pos < 0:
                break
            findings.append((pos, "local denylist term", redact(term)))
            idx = pos + max(1, len(term))

    if not allow:
        for m in LOCAL_STATE.finditer(text):
            findings.append((m.start(), "private agent host branding", redact(m.group(0))))
        for m in DEPRECATED.finditer(text):
            findings.append((m.start(), "deprecated identifier", m.group(0)))

    errors: list[str] = []
    for start, label, value in sorted(findings, key=lambda x: x[0]):
        line = text.count("\n", 0, start) + 1
        errors.append(f"{rel}:{line}: {label}: {value}")
    return errors


def self_check() -> list[str]:
    """Prove patterns catch synthetic leaks without embedding a real identity.

    Samples are assembled at runtime so this source file never contains a
    contiguous host path / secret that the main scan would (correctly) flag.
    """
    sep = "\\"
    samples = (
        (sep.join(["C:", "Users", "someuser1", "AppData", "Roaming", "x"]),
         "Windows home username"),
        ("/" + "home/" + "someuser2/project", "Unix/macOS home username"),
        ("contact leak@" + "corp-internal.invalid", "email-like token"),
        ("sk-" + "abc123def456ghi789", "API key-shaped token"),
        ("ghp_" + "a" * 22, "GitHub token-shaped"),
        ("-----BEGIN " + "PRIVATE KEY-----", "private key block"),
    )
    errors: list[str] = []
    for sample, expect in samples:
        hits = scan_text(Path("self-check"), sample, allow=False, deny_extra=set())
        if not any(expect in h for h in hits):
            errors.append(f"self-check missed {expect!r} in synthetic sample")
    # A local username-shaped token in THIS file must not be required or present.
    src = Path(__file__).read_text(encoding="utf-8", errors="replace")
    if re.search(r"\bp6\d{4}\b", src):
        errors.append("scanner source embeds a local username-shaped token")
    return errors


def main() -> int:
    errors: list[str] = []
    checked = 0
    deny_extra = load_local_denylist()
    for rel, path in iter_files():
        checked += 1
        allow = rel in ALLOWLIST
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{rel}: unreadable ({redact(str(exc))})")
            continue
        errors.extend(scan_text(rel, text, allow, deny_extra))

    errors.extend(check_tracked_paths())
    errors.extend(self_check())

    print(f"privacy scan: {checked} files")
    if deny_extra:
        print(f"privacy scan: local denylist terms = {len(deny_extra)}")
    if errors:
        print(f"FAIL: {len(errors)} finding(s)")
        for e in errors[:50]:
            print(" ", e)
        return 1
    print("PASS: no privacy/deprecation findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
