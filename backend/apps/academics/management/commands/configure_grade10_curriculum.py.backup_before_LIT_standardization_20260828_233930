from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import InstructionalGroup, LessonRequirement, Subject, TeachingGroup
from apps.core.models import Term
from apps.scheduling.models import TeacherAssignment
from apps.users.models import Teacher


COMMON = {
    "ENG": ("English", 5, "T015"),
    "KIS": ("Kiswahili", 4, "T020"),
    "CRE": ("Christian Religious Education", 4, "T020"),
    "EMCM": ("Essential Mathematics / Core Mathematics", 3, "T013"),
    "CSL": ("Community Service Learning", 2, "T016"),
    "ICT": ("ICT Skills", 2, "T019"),
    "PE": ("Physical Education", 1, "T014"),
    "LIFE": ("Life Skills", 1, None),
}

ELECTIVE_BLOCKS = {
    "BLOCK_1": {
        "AGR": ("Agriculture", 3, "T010"),
        "BUS": ("Business Studies", 3, "T019"),
    },
    "BLOCK_2": {
        "BIO": ("Biology", 3, "T016"),
        "MUS": ("Music", 3, "T019"),
        "FRE": ("French", 3, None),
    },
    "BLOCK_3": {
        "CHEM": ("Chemistry", 3, "T005"),
        "PHY": ("Physics", 3, "T009"),
        "LITENG": ("Literature in English", 3, "T011"),
    },
    "BLOCK_4": {
        "GEO": ("Geography", 3, "T018"),
        "HISTGOV": ("History and Government", 3, "T017"),
        "COMP": ("Computer Studies", 3, "T019"),
    },
}


class Command(BaseCommand):
    help = "Configure the Grade 10E/10W curriculum and teacher assignments."

    @transaction.atomic
    def handle(self, *args, **options):
        term = (
            Term.objects.filter(is_active=True)
            .order_by("-start_date", "-created_at")
            .first()
        )
        if term is None:
            raise CommandError("No active academic term exists.")

        teachers = {
            teacher.employee_code: teacher
            for teacher in Teacher.objects.filter(is_active=True)
        }
        required_teacher_codes = {
            teacher_code
            for subject_name, weekly_count, teacher_code in COMMON.values()
            if teacher_code
        }
        required_teacher_codes.update(
            teacher_code
            for block in ELECTIVE_BLOCKS.values()
            for subject_name, weekly_count, teacher_code in block.values()
            if teacher_code
        )
        missing_teachers = sorted(required_teacher_codes - teachers.keys())
        if missing_teachers:
            raise CommandError(
                "Missing active teacher codes: " + ", ".join(missing_teachers)
            )

        target_groups = list(
            InstructionalGroup.objects.filter(
                code__in=("10E", "10W"),
                name__in=("Grade 10E", "Grade 10W"),
            )
        )
        if {group.code for group in target_groups} != {"10E", "10W"}:
            raise CommandError("Grade 10E and Grade 10W instructional groups are required.")

        # The legacy cohort is retained for history but no longer schedulable.
        legacy_groups = InstructionalGroup.objects.filter(
            code="G10A",
            name="Grade 10",
        )
        legacy_requirements = LessonRequirement.objects.filter(
            instructional_group__in=legacy_groups,
            term=term,
        )
        legacy_requirements.update(is_active=False)
        TeacherAssignment.objects.filter(
            lesson_requirement__in=legacy_requirements,
        ).update(is_active=False)
        legacy_groups.update(is_active=False)
        TeachingGroup.objects.filter(code="G10A").update(is_active=False)

        definitions = dict(COMMON)
        for block in ELECTIVE_BLOCKS.values():
            definitions.update(block)

        created = 0
        updated = 0
        muted = []
        for group in target_groups:
            for code, (subject_name, weekly_count, teacher_code) in definitions.items():
                subject, _ = Subject.objects.get_or_create(
                    code=code,
                    defaults={"name": subject_name, "is_active": True},
                )
                if subject.name != subject_name:
                    subject.name = subject_name
                    subject.save(update_fields=["name", "updated_at"])

                requirement, was_created = LessonRequirement.objects.update_or_create(
                    term=term,
                    instructional_group=group,
                    subject=subject,
                    defaults={
                        "lessons_per_week": weekly_count,
                        # Subjects without a teacher remain intentionally muted.
                        "is_active": teacher_code is not None,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                TeacherAssignment.objects.filter(
                    lesson_requirement=requirement,
                ).update(is_active=False)
                if teacher_code is None:
                    muted.append(f"{group.name}: {code}")
                    continue

                TeacherAssignment.objects.update_or_create(
                    lesson_requirement=requirement,
                    teacher=teachers[teacher_code],
                    defaults={"is_active": True},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Configured Grade 10E/10W for {term}. "
                f"Requirements created: {created}; updated: {updated}."
            )
        )
        self.stdout.write("Muted requirements: " + (", ".join(muted) or "none"))
        self.stdout.write("Legacy Grade 10 cohort deactivated.")