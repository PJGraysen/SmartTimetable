from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    get_grade10_parallel_block,
    get_grade10_parallel_block_for_subject,
    validate_grade10_parallel_blocks,
    describe_grade10_parallel_blocks,
)

print("=" * 78)
print("SMARTTIMETABLE PRO - OPT1 RUNTIME REQUIREMENT TRACE")
print("=" * 78)

print()
print("MODULE")
print("-" * 78)
print("apps.scheduling.engine.application.grade10_parallel_blocks")

print()
print("AUTHORITATIVE PARALLEL BLOCKS")
print("-" * 78)

validate_grade10_parallel_blocks()

for block in GRADE10_PARALLEL_BLOCKS:
    print(
        f"{block.code}: "
        f"{block.subject_codes}"
    )

print()
print("OPT1 LOOKUP")
print("-" * 78)

opt1 = get_grade10_parallel_block("OPTION_1")

print(f"CODE: {opt1.code}")
print(f"SUBJECTS: {opt1.subject_codes}")

print()
print("SUBJECT LOOKUPS")
print("-" * 78)

for subject_code in ("BIO", "MUS", "FRE"):
    block = get_grade10_parallel_block_for_subject(subject_code)

    print(
        f"{subject_code} -> "
        f"{block.code if block else None} "
        f"{block.subject_codes if block else None}"
    )

print()
print("BLOCK DESCRIPTIONS")
print("-" * 78)

for description in describe_grade10_parallel_blocks():
    print(description)

print()
print("=" * 78)
print("TRACE COMPLETE")
print("=" * 78)
