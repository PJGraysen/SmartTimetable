"""
Platform application registry.

This module is the single source of truth for what applications exist
in SmartTimeTablePro and which permissions gate visibility.

Static, versioned in code. No DB access. No migrations.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Application:
    slug: str
    name: str
    description: str
    entry_path: str
    icon: str
    required_permissions: tuple[str, ...] = ()
    visible_to_superusers: bool = True

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "entry_path": self.entry_path,
            "icon": self.icon,
        }


APPLICATIONS: tuple[Application, ...] = (
    Application(
        slug="timetable",
        name="Timetable Scheduling",
        description="Generate and manage school timetables",
        entry_path="/scheduling",
        icon="calendar",
        required_permissions=(),
    ),
    Application(
        slug="academic_analysis",
        name="Academic Analysis",
        description="Students, learning groups, exams, reports",
        entry_path="/academic-analysis",
        icon="graduation-cap",
        required_permissions=(),
    ),
    Application(
        slug="library",
        name="Library Management",
        description="Catalogue, members, circulation",
        entry_path="/library",
        icon="book-open",
        required_permissions=("library.view_book",),
    ),
)


def applications_for_user(user) -> tuple[Application, ...]:
    """
    Return the applications the given user may access.

    Semantics:
      - Unauthenticated user -> empty tuple.
      - Superuser -> every application with visible_to_superusers=True.
      - Otherwise -> applications whose required_permissions is empty
        OR whose required_permissions is non-empty and the user has at
        least one of them.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return ()
    if user.is_superuser:
        return tuple(a for a in APPLICATIONS if a.visible_to_superusers)

    result = []
    for app in APPLICATIONS:
        if not app.required_permissions:
            result.append(app)
            continue
        if any(user.has_perm(p) for p in app.required_permissions):
            result.append(app)
    return tuple(result)
