"""Clone TeacherAssignments from a source term to a target term.

Term-agnostic, idempotent, non-destructive. For each active
TeacherAssignment in the source term, finds the equivalent target-term
LessonRequirement by (instructional_group, subject, requirement_type)
and upserts a TeacherAssignment pointing at it with the same teacher.

Any target-term TeacherAssignment whose LR is not represented in the
source set is deactivated (never deleted — TeacherAssignment.teacher
is PROTECT and there is no benefit to deleting historical rows).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import LessonRequirement
from apps.core.models import Term
from apps.scheduling.models import TeacherAssignment


def _lr_key(lr):
    return (
        lr.instructional_group_id,
        lr.subject_id,
        lr.requirement_type,
    )


class Command(BaseCommand):
    help = "Clone TeacherAssignments from a source term to a target term."

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

        src_tas = list(
            TeacherAssignment.objects
            .filter(
                lesson_requirement__term=source,
                lesson_requirement__is_active=True,
                is_active=True,
            )
            .select_related(
                "teacher",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
            )
        )
        self.stdout.write(f"Source active TAs: {len(src_tas)}")

        if not src_tas:
            raise CommandError("Source term has no active TeacherAssignments.")

        # Build map: LR key -> (teacher_id, group_code, subject_code)
        src_map: dict = {}
        for ta in src_tas:
            lr = ta.lesson_requirement
            key = _lr_key(lr)
            src_map[key] = {
                "teacher_id": ta.teacher_id,
                "teacher_code": getattr(ta.teacher, "employee_code", "?"),
                "group_code": lr.instructional_group.code
                    if lr.instructional_group else "?",
                "subject_code": lr.subject.code if lr.subject else "?",
                "requirement_type": lr.requirement_type,
            }

        # Target LRs indexed by the same key
        tgt_lr_by_key = {
            _lr_key(lr): lr
            for lr in LessonRequirement.objects
            .filter(term=target)
            .select_related("subject", "instructional_group")
        }
        self.stdout.write(f"Target LRs: {len(tgt_lr_by_key)}")

        missing_lr = [
            k for k in src_map.keys() if k not in tgt_lr_by_key
        ]
        if missing_lr:
            self.stdout.write(self.style.WARNING(
                f"  {len(missing_lr)} source TAs have no matching "
                f"target LR — these will be skipped."
            ))
            for k in missing_lr[:10]:
                info = src_map[k]
                self.stdout.write(
                    f"    MISSING LR: {info['group_code']:6s}  "
                    f"{info['subject_code']:6s}  "
                    f"{info['requirement_type']:10s}  "
                    f"teacher={info['teacher_code']}"
                )
            if len(missing_lr) > 10:
                self.stdout.write(f"    ... and {len(missing_lr) - 10} more")

        if not options["apply"]:
            self.stdout.write("")
            self.stdout.write("DRY RUN - pass --apply to write.")
            preview = [
                (k, v) for k, v in src_map.items() if k in tgt_lr_by_key
            ][:20]
            for k, v in preview:
                self.stdout.write(
                    f"  {v['group_code']:6s}  {v['subject_code']:6s}  "
                    f"{v['requirement_type']:10s}  "
                    f"teacher={v['teacher_code']}"
                )
            if len(src_map) > 20:
                self.stdout.write(
                    f"  ... and {len(src_map) - 20} more"
                )
            return

        created = 0
        updated = 0
        unchanged = 0
        skipped_no_lr = 0
        deactivated_stale = 0

        with transaction.atomic():
            for key, info in src_map.items():
                tgt_lr = tgt_lr_by_key.get(key)
                if tgt_lr is None:
                    skipped_no_lr += 1
                    continue

                source_teacher_id = info["teacher_id"]

                # Any TA on this LR with a DIFFERENT teacher is stale
                # (residue from earlier materialize runs that used a
                # different teacher). Deactivate before inserting the
                # source-of-truth row so the unique constraint
                # uq_teacher_assignment_teacher_requirement cannot
                # collide.
                stale = TeacherAssignment.objects.filter(
                    lesson_requirement=tgt_lr,
                    is_active=True,
                ).exclude(teacher_id=source_teacher_id)
                stale_n = stale.count()
                if stale_n:
                    stale.update(is_active=False)
                    deactivated_stale += stale_n

                existing = TeacherAssignment.objects.filter(
                    lesson_requirement=tgt_lr,
                    teacher_id=source_teacher_id,
                ).first()

                if existing is None:
                    TeacherAssignment.objects.create(
                        lesson_requirement=tgt_lr,
                        teacher_id=source_teacher_id,
                        is_active=True,
                    )
                    created += 1
                elif not existing.is_active:
                    existing.is_active = True
                    existing.save(update_fields=["is_active"])
                    updated += 1
                else:
                    unchanged += 1

            # Deactivate orphans — TAs on target LRs whose key is not
            # in the source set.
            orphaned = 0
            for ta in (
                TeacherAssignment.objects
                .filter(
                    lesson_requirement__term=target,
                    is_active=True,
                )
                .select_related(
                    "lesson_requirement__subject",
                    "lesson_requirement__instructional_group",
                )
            ):
                key = _lr_key(ta.lesson_requirement)
                if key in src_map:
                    continue
                ta.is_active = False
                ta.save(update_fields=["is_active"])
                orphaned += 1

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CLONE COMPLETE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Created:        {created}")
        self.stdout.write(f"  Updated:        {updated}")
        self.stdout.write(f"  Unchanged:      {unchanged}")
        self.stdout.write(f"  Skipped (no LR): {skipped_no_lr}")
        self.stdout.write(f"  Deact. stale:   {deactivated_stale}")
        self.stdout.write(f"  Orphaned:       {orphaned}")
        final = TeacherAssignment.objects.filter(
            lesson_requirement__term=target,
            is_active=True,
        ).count()
        self.stdout.write(f"  Target active:  {final}")
