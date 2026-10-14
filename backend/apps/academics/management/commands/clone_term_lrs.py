"""Clone LessonRequirements from a source term to a target term.

Term-agnostic, idempotent, non-destructive.

For each active LessonRequirement in the source term:
  - If a target LR with the same (instructional_group, subject,
    requirement_type) exists, update it in place.
  - Otherwise create it.

After the upsert, any target LR whose (group, subject, type) is not
represented in the source term's active set is deactivated (never
deleted, because TeacherAssignment.lesson_requirement is PROTECT).

This is the canonical "seed a new term from a working baseline"
operation. It replaces the earlier --wipe approach, which could not
run against terms whose LRs were already referenced by
TeacherAssignment rows.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import LessonRequirement
from apps.core.models import Term


class Command(BaseCommand):
    help = "Clone LessonRequirements from a source term to a target term."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="source", required=True)
        parser.add_argument("--to", dest="target", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        source = Term.objects.filter(
            name__iexact=options["source"]
        ).first()
        target = Term.objects.filter(
            name__iexact=options["target"]
        ).first()

        if source is None:
            raise CommandError(f"Source term {options['source']!r} not found.")
        if target is None:
            raise CommandError(f"Target term {options['target']!r} not found.")
        if source.pk == target.pk:
            raise CommandError("Source and target must differ.")

        self.stdout.write(f"Source: {source.name} [{source.pk}]")
        self.stdout.write(f"Target: {target.name} [{target.pk}]")

        src_qs = (
            LessonRequirement.objects
            .filter(term=source, is_active=True)
            .select_related("subject", "instructional_group", "teacher")
        )
        src_lrs = [
            lr for lr in src_qs
            if lr.instructional_group is None
            or lr.instructional_group.is_active
        ]
        self.stdout.write(f"Source active LRs: {len(src_lrs)}")

        if not src_lrs:
            raise CommandError("Source term has no active LRs.")

        source_keys = set()
        for lr in src_lrs:
            source_keys.add((
                lr.instructional_group_id,
                lr.subject_id,
                lr.requirement_type,
            ))

        if not options["apply"]:
            self.stdout.write("")
            self.stdout.write("DRY RUN - pass --apply to write.")
            for lr in src_lrs[:20]:
                gc = (
                    lr.instructional_group.code
                    if lr.instructional_group else "<none>"
                )
                self.stdout.write(
                    f"  {gc:8s}  {lr.subject.code:8s}"
                    f"  {lr.requirement_type:12s}"
                    f"  lpw={lr.lessons_per_week}"
                )
            if len(src_lrs) > 20:
                self.stdout.write(f"  ... and {len(src_lrs) - 20} more")
            return

        created = 0
        updated = 0
        unchanged = 0
        deactivated = 0

        with transaction.atomic():
            for src in src_lrs:
                existing = LessonRequirement.objects.filter(
                    term=target,
                    instructional_group=src.instructional_group,
                    subject=src.subject,
                    requirement_type=src.requirement_type,
                ).first()

                if existing is None:
                    LessonRequirement.objects.create(
                        term=target,
                        instructional_group=src.instructional_group,
                        subject=src.subject,
                        teacher=src.teacher,
                        requirement_type=src.requirement_type,
                        lessons_per_week=src.lessons_per_week,
                        is_active=src.is_active,
                    )
                    created += 1
                    continue

                changed = (
                    existing.lessons_per_week != src.lessons_per_week
                    or existing.teacher_id != src.teacher_id
                    or not existing.is_active
                )
                if changed:
                    existing.lessons_per_week = src.lessons_per_week
                    existing.teacher = src.teacher
                    existing.is_active = True
                    existing.save(
                        update_fields=[
                            "lessons_per_week",
                            "teacher",
                            "is_active",
                        ]
                    )
                    updated += 1
                else:
                    unchanged += 1

            # Deactivate orphans (present in target, absent from source)
            for lr in (
                LessonRequirement.objects
                .filter(term=target, is_active=True)
                .select_related("subject", "instructional_group")
            ):
                key = (
                    lr.instructional_group_id,
                    lr.subject_id,
                    lr.requirement_type,
                )
                if key in source_keys:
                    continue
                gc = (
                    lr.instructional_group.code
                    if lr.instructional_group else "<none>"
                )
                self.stdout.write(
                    f"  DEACT {gc:8s}  {lr.subject.code:8s}  "
                    f"{lr.requirement_type}"
                )
                lr.is_active = False
                lr.save(update_fields=["is_active"])
                deactivated += 1

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CLONE COMPLETE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Created:     {created}")
        self.stdout.write(f"  Updated:     {updated}")
        self.stdout.write(f"  Unchanged:   {unchanged}")
        self.stdout.write(f"  Deactivated: {deactivated}")
        active = LessonRequirement.objects.filter(
            term=target, is_active=True
        ).count()
        self.stdout.write(f"  Target active: {active}")
