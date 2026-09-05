from __future__ import annotations

from collections import defaultdict

from django.apps import apps

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    get_grade10_parallel_block_for_subject,
)

from apps.scheduling.engine.infrastructure.django_loader import (
    load_lesson_requirements,
)


print("=" * 78)
print("SMARTTIMETABLE PRO - COMPLETE GRADE 10 CURRICULUM LOAD TRACE")
print("=" * 78)
print()

print("AUTHORITATIVE BUSINESS CONTRACT")
print("-" * 78)
print("INSTRUCTIONAL GROUPS: Grade 10E / Grade 10W")
print("WEEKLY TEACHING LOAD: 49 lessons per instructional group")
print("MON=9, TUE=10, WED=10, THU=10, FRI=10")
print("MON P1 = ASSEMBLY")
print("P13 = PRAYERS")
print("P14 = ACTIVITIES")
print("TEA BREAK = 10:40-11:00")
print("LUNCH = 1:00-2:00")
print()

print("CORE")
print("-" * 78)
print("ENG=5  KIS=5  EMCM=5  CRE=4  PE=3  CSL=3")
print()

print("STANDALONE")
print("-" * 78)
print("ICT=2  PRP=1")
print("MUS IS NOT STANDALONE")
print()

print("ELECTIVE BLOCKS")
print("-" * 78)
print("OPTION_1 = BIO / MUS / FRE = 5")
print("OPTION_2 = CHEM / PHY / LIT = 5")
print("OPTION_3 = GEO / HIST / CS = 5")
print("OPTION_4 = BUS / AGRI = 5")
print()

print("1. DJANGO MODEL DISCOVERY")
print("-" * 78)

LessonRequirement = None

for model in apps.get_models():
    if model.__name__ == "LessonRequirement":
        LessonRequirement = model
        break

if LessonRequirement is None:
    raise RuntimeError(
        "LessonRequirement model could not be located "
        "through Django app registry."
    )

print(
    f"MODEL: "
    f"{LessonRequirement.__module__}."
    f"{LessonRequirement.__name__}"
)

print()

print("2. DATABASE → COMPLETE REQUIREMENT SET")
print("-" * 78)

database_requirements = list(
    LessonRequirement.objects
    .select_related("subject", "term")
    .filter(is_active=True)
)

print(
    f"ACTIVE DATABASE REQUIREMENTS: "
    f"{len(database_requirements)}"
)

database_by_subject = defaultdict(list)

for requirement in database_requirements:
    subject = getattr(requirement, "subject", None)

    subject_code = str(
        getattr(subject, "code", "")
        if subject is not None
        else ""
    ).strip().upper()

    if not subject_code:
        subject_code = "<NO SUBJECT CODE>"

    database_by_subject[subject_code].append(requirement)

print()

print("3. DATABASE REQUIREMENTS BY SUBJECT")
print("-" * 78)

for subject_code in sorted(database_by_subject):
    rows = database_by_subject[subject_code]

    groups = {
        getattr(row, "instructional_group_id", None)
        for row in rows
    }

    print(
        f"{subject_code}: "
        f"{len(rows)} requirement(s), "
        f"{len(groups)} instructional group(s)"
    )

print()

print("4. DATABASE → DOMAIN")
print("-" * 78)

domain_requirements = list(
    load_lesson_requirements(database_requirements)
)

print(
    f"DATABASE COUNT: "
    f"{len(database_requirements)}"
)

print(
    f"DOMAIN COUNT: "
    f"{len(domain_requirements)}"
)

if len(domain_requirements) == len(database_requirements):
    print(
        "PASS: DATABASE AND DOMAIN REQUIREMENT COUNTS MATCH"
    )
else:
    print(
        "FAIL: DATABASE AND DOMAIN REQUIREMENT COUNTS DIFFER"
    )

print()

print("5. DOMAIN REQUIREMENTS BY SUBJECT")
print("-" * 78)

domain_by_subject = defaultdict(list)

for requirement in domain_requirements:
    subject_code = str(
        getattr(requirement, "subject_code", "")
    ).strip().upper()

    if not subject_code:
        subject_code = "<NO SUBJECT CODE>"

    domain_by_subject[subject_code].append(requirement)

for subject_code in sorted(domain_by_subject):
    rows = domain_by_subject[subject_code]

    groups = {
        getattr(row, "instructional_group_id", None)
        for row in rows
    }

    weekly_values = {
        getattr(row, "periods_per_week", None)
        for row in rows
    }

    try:
        block = get_grade10_parallel_block_for_subject(
            subject_code
        )
        scope = block.code
    except Exception:
        scope = "CORE / STANDALONE / OTHER"

    print(
        f"{subject_code}: "
        f"requirements={len(rows)}, "
        f"groups={len(groups)}, "
        f"weekly={sorted(weekly_values, key=str)}, "
        f"scope={scope}"
    )

print()

print("6. COMPLETE DOMAIN REQUIREMENT DETAIL")
print("-" * 78)

for requirement in sorted(
    domain_requirements,
    key=lambda item: (
        str(getattr(item, "subject_code", "")),
        str(getattr(item, "instructional_group_id", "")),
        str(getattr(item, "id", "")),
    ),
):
    subject_code = str(
        getattr(requirement, "subject_code", "")
    ).strip().upper()

    try:
        block = get_grade10_parallel_block_for_subject(
            subject_code
        )
        scope = block.code
    except Exception:
        scope = "CORE / STANDALONE / OTHER"

    print(
        f"{subject_code} | "
        f"REQ={getattr(requirement, 'id', None)} | "
        f"GROUP={getattr(requirement, 'instructional_group_id', None)} | "
        f"WEEK={getattr(requirement, 'periods_per_week', None)} | "
        f"ACTIVE={getattr(requirement, 'is_active', None)} | "
        f"SCOPE={scope}"
    )

print()

print("7. ELECTIVE BLOCK COVERAGE")
print("-" * 78)

domain_subjects = set(domain_by_subject)

for block in GRADE10_PARALLEL_BLOCKS:
    print()
    print(
        f"{block.code}: "
        f"{tuple(block.subject_codes)}"
    )

    for subject_code in block.subject_codes:
        count = len(
            domain_by_subject.get(subject_code, [])
        )

        print(
            f"  {subject_code}: "
            f"{'FOUND' if count else 'MISSING'} "
            f"({count})"
        )

print()

print("8. CONTRACT CORE SUBJECT COVERAGE")
print("-" * 78)

core_contract = {
    "ENG": 5,
    "KIS": 5,
    "EMCM": 5,
    "CRE": 4,
    "PE": 3,
    "CSL": 3,
}

for subject_code, expected in core_contract.items():
    rows = domain_by_subject.get(subject_code, [])

    weekly_values = {
        getattr(row, "periods_per_week", None)
        for row in rows
    }

    print(
        f"{subject_code}: "
        f"{'FOUND' if rows else 'MISSING'} | "
        f"requirements={len(rows)} | "
        f"expected={expected} | "
        f"loaded_weekly={sorted(weekly_values, key=str)}"
    )

print()

print("9. CONTRACT STANDALONE SUBJECT COVERAGE")
print("-" * 78)

standalone_contract = {
    "ICT": 2,
    "PRP": 1,
}

for subject_code, expected in standalone_contract.items():
    rows = domain_by_subject.get(subject_code, [])

    weekly_values = {
        getattr(row, "periods_per_week", None)
        for row in rows
    }

    print(
        f"{subject_code}: "
        f"{'FOUND' if rows else 'MISSING'} | "
        f"requirements={len(rows)} | "
        f"expected={expected} | "
        f"loaded_weekly={sorted(weekly_values, key=str)}"
    )

print()

print("10. MUSIC STANDALONE CHECK")
print("-" * 78)

music_rows = domain_by_subject.get("MUS", [])

print(
    f"MUS DOMAIN REQUIREMENTS: "
    f"{len(music_rows)}"
)

print(
    "MUS MUST BELONG TO OPTION_1, "
    "NOT STANDALONE."
)

try:
    music_block = get_grade10_parallel_block_for_subject("MUS")

    print(
        f"MUS BLOCK: "
        f"{music_block.code}"
    )

except Exception as exc:
    print(
        f"WARNING: MUSIC BLOCK LOOKUP FAILED: "
        f"{exc}"
    )

print()

print("11. DATABASE → DOMAIN ID INTEGRITY")
print("-" * 78)

database_ids = {
    requirement.id
    for requirement in database_requirements
}

domain_ids = {
    requirement.id
    for requirement in domain_requirements
}

missing_ids = database_ids - domain_ids
unexpected_ids = domain_ids - database_ids

print(
    f"DATABASE IDS: {len(database_ids)}"
)

print(
    f"DOMAIN IDS: {len(domain_ids)}"
)

print(
    f"MISSING FROM DOMAIN: {len(missing_ids)}"
)

print(
    f"UNEXPECTED IN DOMAIN: {len(unexpected_ids)}"
)

if missing_ids:
    print()
    print("MISSING REQUIREMENTS")
    for requirement_id in sorted(
        missing_ids,
        key=str,
    ):
        print(requirement_id)

if unexpected_ids:
    print()
    print("UNEXPECTED DOMAIN REQUIREMENTS")
    for requirement_id in sorted(
        unexpected_ids,
        key=str,
    ):
        print(requirement_id)

print()

print("12. SCOPE GUARANTEE")
print("-" * 78)
print("ALL ACTIVE LessonRequirement records were supplied")
print("to load_lesson_requirements().")
print()
print("OPT1 remains BIO / MUS / FRE.")
print("OPT2 remains CHEM / PHY / LIT.")
print("OPT3 remains GEO / HIST / CS.")
print("OPT4 remains BUS / AGRI.")
print("Core subjects remain in scope.")
print("Standalone subjects remain in scope.")
print()
print("This trace does NOT generate solver variables.")
print("This trace does NOT execute CP-SAT.")
print("This trace does NOT generate a timetable.")
print("This trace does NOT modify the database.")
print("This trace does NOT modify the frontend.")

print()
print("=" * 78)
print("TRACE COMPLETE")
print("=" * 78)