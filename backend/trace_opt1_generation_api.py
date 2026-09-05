from __future__ import annotations

import inspect
import django

django.setup()

from apps.scheduling.engine.infrastructure import django_loader
from apps.scheduling.engine.solver import variables as variables_module


print("=" * 78)
print("SMARTTIMETABLE PRO - OPT1 ACTUAL VARIABLE GENERATION TRACE")
print("=" * 78)
print()

print("VARIABLE MODULE")
print("-" * 78)
print(variables_module.__file__)
print()

print("PUBLIC CALLABLES")
print("-" * 78)

callables = []

for name in sorted(dir(variables_module)):
    if name.startswith("_"):
        continue

    value = getattr(variables_module, name)

    if callable(value):
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            signature = "(signature unavailable)"

        print(f"{name}{signature}")
        callables.append((name, value))

print()

print("ASSIGNMENT VARIABLE")
print("-" * 78)

AssignmentVariable = getattr(
    variables_module,
    "AssignmentVariable",
    None,
)

print(f"FOUND: {AssignmentVariable is not None}")

if AssignmentVariable is not None:
    print(
        "ANNOTATIONS:",
        getattr(
            AssignmentVariable,
            "__annotations__",
            {},
        ),
    )

print()

print("LOADER PUBLIC CALLABLES")
print("-" * 78)

for name in sorted(dir(django_loader)):
    if name.startswith("_"):
        continue

    value = getattr(django_loader, name)

    if callable(value):
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            signature = "(signature unavailable)"

        print(f"{name}{signature}")

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
