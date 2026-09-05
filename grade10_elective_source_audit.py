from pathlib import Path

ROOT = Path(r"C:\Projects\SmartTimetable")

print("=" * 100)
print("SMARTTIMETABLE PRO - GRADE 10 ELECTIVE CONFIGURATION SOURCE AUDIT")
print("READ ONLY - NO DATABASE CHANGES")
print("=" * 100)

patterns = [
    "Grade 10",
    "Grade 10E",
    "Grade 10W",
    "Option 1",
    "Option 2",
    "Option 3",
    "Option 4",
    "BIO",
    "MUS",
    "FRE",
    "CHEM",
    "PHY",
    "LIT",
    "GEO",
    "HIST",
    "CS",
    "BUS",
    "AGRI",
    "elective",
    "option",
]

extensions = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}

excluded = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".smarttimetable-backups",
}

hits = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if any(part in excluded for part in path.parts):
        continue

    if path.suffix.lower() not in extensions:
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    lower = text.lower()

    matched = [p for p in patterns if p.lower() in lower]

    if matched:
        hits.append((path, matched, text))

print("\nSOURCE FILES CONTAINING RELEVANT GRADE 10 / ELECTIVE TERMS")
print("-" * 100)

if not hits:
    print("NO MATCHING SOURCE FILES FOUND.")
else:
    for path, matched, text in hits:
        print(f"\nFILE: {path}")
        print("MATCHES:", ", ".join(matched))

        lines = text.splitlines()

        printed = set()

        for i, line in enumerate(lines):
            ll = line.lower()

            if not any(p.lower() in ll for p in patterns):
                continue

            start = max(0, i - 2)
            end = min(len(lines), i + 3)

            block = tuple(range(start, end))

            if block in printed:
                continue

            printed.add(block)

            print(f"\n  --- lines {start + 1}-{end} ---")

            for n in range(start, end):
                print(f"  {n + 1:5}: {lines[n]}")

print("\n" + "=" * 100)
print("END OF SOURCE AUDIT")
print("=" * 100)