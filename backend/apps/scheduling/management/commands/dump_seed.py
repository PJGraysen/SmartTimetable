"""Curated seed-data fixture for local bootstrap.

    python manage.py dump_seed
    python manage.py dump_seed --version-name "Term 1 - Master (baseline)"
"""
from __future__ import annotations
import json
from pathlib import Path
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError

DEFAULT_VERSION_NAME = "Term 1 - Master (baseline)"

INCLUDE = {
    "core":       ["AcademicYear", "Term", "School", "SchoolEvent"],
    "academics":  ["Subject", "Stream", "TeachingGroup", "InstructionalGroup",
                   "LessonRequirement", "GradingScheme", "GradingBand",
                   "Grade", "RankingRule"],
    "scheduling": ["Period", "Room", "RoomAvailability",
                   "TeacherAssignment", "TeacherAvailability",
                   "TeacherFreeAfternoon", "DutyAssignment",
                   "SchedulingRuleConfig"],
    "users":      ["Teacher"],
}

# Keys are the lowercased last segment of record["model"], e.g. "teacher".
# Fields removed entirely (PII or references to models not in the fixture).
# `groups` and `user_permissions` are m2m to auth.Group / auth.Permission,
# which we don't include; dropping them avoids dangling auth_user_groups
# rows without affecting a fresh-checkout boot.
PII_STRIP = {
    "teacher": {"phone"},
    "user":    {"groups", "user_permissions"},
}
PII_REPLACE = {
    "user": {
        "password":   "!seed-no-login",   # Django unusable-password marker
        "email":      "",
        "last_login": None,
    },
}


class Command(BaseCommand):
    help = "Write a curated seed fixture to backend/seed/data.json"

    def add_arguments(self, parser):
        parser.add_argument("--version-name", default=DEFAULT_VERSION_NAME,
            help=f"TimetableVersion.name to include (default: {DEFAULT_VERSION_NAME})")
        parser.add_argument("--output", default=None)
        parser.add_argument("--compact", action="store_true")

    def handle(self, *args, **opts):
        out_path = Path(opts["output"]) if opts["output"] else (
            Path(settings.BASE_DIR) / "seed" / "data.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        objects = []
        summary = {}

        # 1. Structural / reference data
        for app_label, names in INCLUDE.items():
            for name in names:
                M = apps.get_model(app_label, name)
                objs = list(M._base_manager.all())
                objects.extend(objs)
                summary[f"{app_label}.{name}"] = len(objs)

        # 2. Companion auth.User rows — only those referenced by Teacher.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        Teacher = apps.get_model("users", "Teacher")
        teacher_user_ids = [
            getattr(t, "user_id", None)
            for t in Teacher._base_manager.all()
            if getattr(t, "user_id", None) is not None
        ]
        if teacher_user_ids:
            users = list(User._base_manager.filter(id__in=teacher_user_ids))
            objects.extend(users)
            summary[f"{User._meta.app_label}.{User.__name__}"] = len(users)

        # 3. One TimetableVersion + its entries
        from apps.scheduling.models import TimetableVersion, TimetableEntry
        version = (TimetableVersion.objects
                   .filter(name=opts["version_name"])
                   .order_by("-created_at").first())
        if version is None:
            recent = list(TimetableVersion.objects
                          .order_by("-created_at")
                          .values_list("name", flat=True)[:10])
            raise CommandError(
                f"No TimetableVersion named {opts['version_name']!r}.\n"
                "Recent names:\n  - " + "\n  - ".join(recent))
        objects.append(version)
        summary["scheduling.TimetableVersion"] = 1

        entries = list(TimetableEntry.objects.filter(timetable_version=version))
        objects.extend(entries)
        summary["scheduling.TimetableEntry"] = len(entries)

        # 4. Serialize, then strip / replace PII (case-insensitive model match)
        self.stdout.write("Serializing ...")
        # pk-based serialization. Natural keys sound nicer but break
        # `loaddata` on a fresh DB: `Teacher.user` would serialize as
        # ["<username>"] and Django's deferred-save pass can insert the
        # Teacher before the User, yielding user_id=NULL. With pks, the
        # standard forward-reference mechanism works reliably.
        payload = serializers.serialize(
            "json", objects,
            use_natural_foreign_keys=False,
            use_natural_primary_keys=False,
        )
        data = json.loads(payload)
        stripped = 0
        replaced = 0
        for record in data:
            model_name = record["model"].split(".")[-1].lower()
            for f in PII_STRIP.get(model_name, ()):
                if f in record["fields"]:
                    record["fields"].pop(f, None)
                    stripped += 1
            for f, v in PII_REPLACE.get(model_name, {}).items():
                if f in record["fields"]:
                    record["fields"][f] = v
                    replaced += 1

        indent = None if opts["compact"] else 1
        out_path.write_text(json.dumps(data, indent=indent), encoding="utf-8")

        size_kb = out_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f"\nWrote {out_path}  ({size_kb:,.1f} KB, {len(data):,} records)"))
        self.stdout.write(f"  PII fields stripped: {stripped}")
        self.stdout.write(f"  PII fields replaced: {replaced}")
        self.stdout.write("")
        for key in sorted(summary):
            self.stdout.write(f"  {key:48s} {summary[key]:>7,}")
