from __future__ import annotations

import inspect

from apps.scheduling.engine.solver import variables as variables_module
from apps.scheduling.engine.infrastructure import django_loader
from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
)


print("=" * 78)
print("SMARTTIMETABLE PRO - COMPLETE CURRICULUM VARIABLE API TRACE")
print("=" * 78)
print()

print("VARIABLE MODULE")
print("-" * 78)
print(f"PATH: {variables_module.__file__}")
print()

print("AUTHORITATIVE GRADE 10 ELECTIVE BLOCKS")
print("-" * 78)

for block in GRADE10_PARALLEL_BLOCKS:
    print(
        f"{block.code}: "
        f"{tuple(block.subject_codes)}"
    )

print()

print("VARIABLE MODULE PUBLIC CALLABLES")
print("-" * 78)

for name in sorted(dir(variables_module)):
    if name.startswith("_"):
        continue

    value = getattr(variables_module, name)

    if callable(value):
        print(name)

print()

print("VARIABLE MODULE CALLABLE SIGNATURES")
print("-" * 78)

for name in sorted(dir(variables_module)):
    if name.startswith("_"):
        continue

    value = getattr(variables_module, name)

    if not callable(value):
        continue

    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        signature = "(signature unavailable)"

    print(f"{name}{signature}")

print()

print("ASSIGNMENT VARIABLE STRUCTURE")
print("-" * 78)

AssignmentVariable = getattr(
    variables_module,
    "AssignmentVariable",
    None,
)

if AssignmentVariable is None:
    print("AssignmentVariable NOT FOUND.")
else:
    print("AssignmentVariable annotations:")

    for name, value in getattr(
        AssignmentVariable,
        "__annotations__",
        {},
    ).items():
        print(f"{name}: {value}")

    print()
    print("AssignmentVariable dataclass fields:")

    for name in getattr(
        AssignmentVariable,
        "__dataclass_fields__",
        {},
    ):
        print(name)

print()

print("DJANGO LOADER")
print("-" * 78)
print(f"PATH: {django_loader.__file__}")
print()

print("LOADER PUBLIC CALLABLES")
print("-" * 78)

for name in sorted(dir(django_loader)):
    if name.startswith("_"):
        continue

    value = getattr(django_loader, name)

    if not callable(value):
        continue

    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        signature = "(signature unavailable)"

    print(f"{name}{signature}")

print()

print("COMPLETE CURRICULUM SCOPE")
print("-" * 78)
print("OPTION_1: BIO / MUS / FRE")
print("OPTION_2: CHEM / PHY / LIT")
print("OPTION_3: GEO / HIS / CS")
print("OPTION_4: BUS / AGR")
print()
print("Core subjects remain in scope.")
print("Standalone subjects remain in scope.")
print("Elective synchronization is limited to explicit blocks.")
print()

print("TRACE PURPOSE")
print("-" * 78)
print("Identify the actual variable-generation API.")
print("Do not generate solver variables.")
print("Do not execute the solver.")
print("Do not modify the database.")
print()

print("READ-ONLY GUARANTEE")
print("-" * 78)
print("No database records modified.")
print("No LessonRequirement records modified.")
print("No TeacherAssignment records modified.")
print("No timetable entries modified.")
print("No solver model modified.")
print()

print("=" * 78)
print("TRACE COMPLETE")
print("=" * 78)
