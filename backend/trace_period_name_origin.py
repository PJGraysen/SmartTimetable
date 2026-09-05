from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

print("=" * 110)
print("SMARTTIMETABLE PRO - PERIOD NAME ORIGIN CODE TRACE")
print("READ-ONLY - NO DATABASE CHANGES")
print("=" * 110)

patterns = [
    r'Period\s+\{?.*number',
    r'name\s*=\s*[f]?["\']Period',
    r'Period\s+\d+',
    r'period\.name',
    r'\.name\s*=\s*.*Period',
    r'create\([^)]*name',
    r'update_or_create\([^)]*name',
    r'get_or_create\([^)]*name',
    r'bulk_create',
    r'PERIOD',
    r'BREAK',
    r'LUNCH',
    r'period_number',
]

extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}

skip_dirs = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
}

matches = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() not in extensions:
        continue
    if any(part in skip_dirs for part in path.parts):
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                matches.append(
                    (
                        str(path.relative_to(ROOT)),
                        lineno,
                        pattern,
                        line.strip(),
                    )
                )

print()
print(f"PROJECT ROOT: {ROOT}")
print(f"MATCHES: {len(matches)}")
print()

for relpath, lineno, pattern, line in matches:
    print("-" * 110)
    print(f"FILE:    {relpath}")
    print(f"LINE:    {lineno}")
    print(f"PATTERN: {pattern}")
    print(f"CODE:    {line}")

print()
print("=" * 110)
print("TARGETED PERIOD MODEL FILES")
print("=" * 110)

for path in ROOT.rglob("*.py"):
    if any(part in skip_dirs for part in path.parts):
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if re.search(r'class\s+Period\b', text):
        print()
        print(f"PERIOD MODEL CANDIDATE: {path.relative_to(ROOT)}")

        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            if re.search(r'class\s+Period\b|name\s*=|number\s*=|start|end|Meta', line, re.I):
                start = max(1, i - 3)
                end = min(len(lines), i + 3)

                print(f"\n--- lines {start}-{end} ---")
                for n in range(start, end + 1):
                    print(f"{n:5}: {lines[n-1]}")

print()
print("=" * 110)
print("PERIOD SEED / INITIALIZATION CANDIDATES")
print("=" * 110)

seed_terms = [
    "Period 1",
    "Period 2",
    "Period 3",
    "Period 4",
    "Period 5",
    "Period 6",
    "Period 7",
    "Period 8",
    "Period 9",
    "Period 10",
    "Period 11",
    "Period 12",
    "Period 13",
    "Period 14",
    "Period 15",
    "Break",
    "Lunch",
]

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() not in extensions:
        continue
    if any(part in skip_dirs for part in path.parts):
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    found = [term for term in seed_terms if term.lower() in text.lower()]

    if found:
        print()
        print(f"FILE: {path.relative_to(ROOT)}")
        print(f"TERMS: {', '.join(found)}")

print()
print("=" * 110)
print("END - READ ONLY")
print("=" * 110)
