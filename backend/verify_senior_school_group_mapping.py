import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.academics.services.senior_school_curriculum import (
    build_class_contract,
    class_contract_summary,
    validate_senior_school_contracts,
    validate_senior_school_group_mapping,
)


print("")
print("=" * 68)
print(" SERVICE-LEVEL CURRICULUM -> INSTRUCTIONAL GROUP RESOLUTION")
print("=" * 68)

groups = validate_senior_school_group_mapping()

expected = ("10E", "10W", "3E", "3W", "4E", "4W")

if tuple(groups.keys()) != expected:
    raise RuntimeError(
        f"Unexpected group resolution order/codes: {tuple(groups.keys())}"
    )

for code in expected:
    group = groups[code]

    print("")
    print(f"{code}:")
    print(f"  instructional_group_id = {group.id}")
    print(f"  instructional_group_name = {group.name}")
    print(f"  instructional_group_code = {group.code}")
    print(f"  teaching_group = {group.teaching_group.name}")

    if code in ("3E", "3W", "4E", "4W"):
        contract = build_class_contract(code)
        summary = class_contract_summary(code)

        print(f"  curriculum_level = {contract.level}")
        print(f"  standalone_lessons = {summary['standalone_total']}")
        print(f"  parallel_block_lessons = {summary['block_total']}")
        print(f"  activity_lessons = {summary['activity_total']}")
        print(f"  computed_weekly_total = {summary['computed_total']}")

        if summary["computed_total"] != 49:
            raise RuntimeError(
                f"{code} does not compute to 49 weekly periods."
            )

validate_senior_school_contracts()

print("")
print("=" * 68)
print(" SERVICE-LEVEL GROUP RESOLUTION PASSED")
print("=" * 68)
print("")
