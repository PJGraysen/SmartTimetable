from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import Subject
from apps.scheduling.models import (
    LessonRequirement,
    Teacher,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = (
        "Synchronize the confirmed Grade 10 curriculum additions and "
        "teacher assignments from the QAS timetable."
    )

    # ------------------------------------------------------------
    # CONFIRMED QAS GRADE 10 ALLOCATIONS
    #
    # These counts are weekly lesson-period allocations extracted
    # from the supplied Grade 10 timetable.
    # ------------------------------------------------------------
    GRADE10_CURRICULUM = {
        "BUS": {
            "name": "Business Studies",
            "lessons_per_week": 5,
            "teacher_code": "T019",
        },
        "CS": {
            "name": "Computer Science",
            "lessons_per_week": 4,
            "teacher_code": "T019",
        },
        "ICT": {
            "name": "ICT Skills",
            "lessons_per_week": 2,
            "teacher_code": "T019",
        },
        "MUS": {
            "name": "Music",
            "lessons_per_week": 4,
            "teacher_code": "T019",
        },
        "PRP": {
            "name": "Pastoral/Religious Programme",
            "lessons_per_week": 1,
            "teacher_code": "T001",
        },
    }

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n=== GRADE 10 QAS CURRICULUM SYNCHRONIZATION ==="
            )
        )

        # --------------------------------------------------------
        # 1. Locate the single current Grade 10 instructional group
        # --------------------------------------------------------
        existing_requirements = list(
            LessonRequirement.objects
            .select_related(
                "subject",
                "instructional_group",
                "term",
            )
            .filter(
                instructional_group__name="Grade 10",
            )
            .order_by("subject__name")
        )

        if not existing_requirements:
            raise CommandError(
                "No Grade 10 LessonRequirement exists. "
                "Cannot safely determine the current Grade 10 group/term."
            )

        groups = {
            requirement.instructional_group_id
            for requirement in existing_requirements
        }

        if len(groups) != 1:
            raise CommandError(
                "More than one Grade 10 instructional group was found. "
                "Synchronization aborted."
            )

        grade10_group = existing_requirements[0].instructional_group
        default_term = existing_requirements[0].term

        self.stdout.write(
            self.style.SUCCESS(
                f"Grade 10 group verified: {grade10_group.name}"
            )
        )

        self.stdout.write(
            f"Term used for new requirements: {default_term}"
        )

        # --------------------------------------------------------
        # 2. Verify all required teacher codes
        # --------------------------------------------------------
        teacher_codes = {
            item["teacher_code"]
            for item in self.GRADE10_CURRICULUM.values()
        }

        teachers = {
            teacher.employee_code: teacher
            for teacher in Teacher.objects.filter(
                employee_code__in=teacher_codes
            )
        }

        missing_teachers = teacher_codes - set(teachers.keys())

        if missing_teachers:
            raise CommandError(
                "Required teacher code(s) do not exist: "
                + ", ".join(sorted(missing_teachers))
            )

        # --------------------------------------------------------
        # 3. Verify subject code/name integrity
        # --------------------------------------------------------
        subjects = {}

        for code, data in self.GRADE10_CURRICULUM.items():
            subject = Subject.objects.filter(
                code=code
            ).first()

            if subject is None:
                raise CommandError(
                    f"Subject code {code} does not exist. "
                    f"Expected subject: {data['name']}"
                )

            if subject.name.strip() != data["name"]:
                raise CommandError(
                    f"Subject-code mismatch: {code} is currently "
                    f"'{subject.name}', but expected '{data['name']}'."
                )

            if not subject.is_active:
                raise CommandError(
                    f"Subject {code} ({subject.name}) is inactive."
                )

            subjects[code] = subject

        self.stdout.write(
            self.style.SUCCESS(
                "Subject code/name integrity verified."
            )
        )

        # --------------------------------------------------------
        # 4. Synchronize requirements and teacher assignments
        # --------------------------------------------------------
        created_requirements = 0
        updated_requirements = 0
        unchanged_requirements = 0

        created_assignments = 0
        updated_assignments = 0
        unchanged_assignments = 0

        with transaction.atomic():

            for code, data in self.GRADE10_CURRICULUM.items():
                subject = subjects[code]
                teacher = teachers[data["teacher_code"]]

                # Find existing Grade 10 requirement.
                requirement = (
                    LessonRequirement.objects
                    .filter(
                        instructional_group=grade10_group,
                        subject=subject,
                    )
                    .first()
                )

                if requirement is None:
                    requirement = LessonRequirement.objects.create(
                        instructional_group=grade10_group,
                        term=default_term,
                        subject=subject,
                        lessons_per_week=data["lessons_per_week"],
                        is_active=True,
                    )

                    created_requirements += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"CREATED REQUIREMENT | "
                            f"{code} | "
                            f"{subject.name} | "
                            f"{data['lessons_per_week']}/week"
                        )
                    )

                else:
                    changed = False

                    if requirement.lessons_per_week != data["lessons_per_week"]:
                        requirement.lessons_per_week = data[
                            "lessons_per_week"
                        ]
                        changed = True

                    if not requirement.is_active:
                        requirement.is_active = True
                        changed = True

                    if changed:
                        requirement.save(
                            update_fields=[
                                "lessons_per_week",
                                "is_active",
                                "updated_at",
                            ]
                        )

                        updated_requirements += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"UPDATED REQUIREMENT | "
                                f"{code} | "
                                f"{subject.name} | "
                                f"{data['lessons_per_week']}/week"
                            )
                        )
                    else:
                        unchanged_requirements += 1

                # ------------------------------------------------
                # TeacherAssignment safety gate:
                # exactly zero or one existing assignment allowed.
                # Multiple assignments are never guessed/deleted.
                # ------------------------------------------------
                assignments = list(
                    TeacherAssignment.objects
                    .select_related("teacher")
                    .filter(
                        lesson_requirement=requirement
                    )
                )

                if len(assignments) > 1:
                    codes = ", ".join(
                        sorted(
                            assignment.teacher.employee_code
                            for assignment in assignments
                        )
                    )

                    raise CommandError(
                        f"Multiple teachers already assigned to "
                        f"{subject.name}: {codes}. "
                        f"Synchronization aborted."
                    )

                if len(assignments) == 0:
                    TeacherAssignment.objects.create(
                        teacher=teacher,
                        lesson_requirement=requirement,
                        is_active=True,
                    )

                    created_assignments += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"CREATED ASSIGNMENT | "
                            f"{data['teacher_code']} | "
                            f"{subject.name}"
                        )
                    )

                else:
                    assignment = assignments[0]

                    if assignment.teacher_id != teacher.pk:
                        old_code = assignment.teacher.employee_code

                        assignment.teacher = teacher
                        assignment.is_active = True
                        assignment.save(
                            update_fields=[
                                "teacher",
                                "is_active",
                            ]
                        )

                        updated_assignments += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"CORRECTED ASSIGNMENT | "
                                f"{subject.name} | "
                                f"{old_code} -> "
                                f"{data['teacher_code']}"
                            )
                        )

                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.save(
                            update_fields=["is_active"]
                        )

                        updated_assignments += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"REACTIVATED ASSIGNMENT | "
                                f"{data['teacher_code']} | "
                                f"{subject.name}"
                            )
                        )

                    else:
                        unchanged_assignments += 1

        # --------------------------------------------------------
        # 5. Final report
        # --------------------------------------------------------
        self.stdout.write("\n=== SYNCHRONIZATION RESULT ===")

        self.stdout.write(
            f"Requirements created:   {created_requirements}"
        )
        self.stdout.write(
            f"Requirements updated:   {updated_requirements}"
        )
        self.stdout.write(
            f"Requirements unchanged: {unchanged_requirements}"
        )

        self.stdout.write(
            f"Assignments created:    {created_assignments}"
        )
        self.stdout.write(
            f"Assignments updated:    {updated_assignments}"
        )
        self.stdout.write(
            f"Assignments unchanged:  {unchanged_assignments}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nGrade 10 QAS curriculum synchronization completed."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher codes were not renumbered or recreated."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Group Study remains available in the subject catalogue "
                "but is not allocated in the current QAS Grade 10 timetable."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Pastoral/Religious Programme remains supported and is "
                "allocated at 1 lesson/week for Grade 10."
            )
        )
