from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Term
from apps.scheduling.models import Teacher, TeacherFreeAfternoon


class Command(BaseCommand):
    help = (
        "Assign exactly one free afternoon to every teacher for the "
        "current academic term."
    )

    DAYS = ["MON", "TUE", "WED", "THU", "FRI"]

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== ASSIGN TEACHER FREE AFTERNOONS ===\n"
        )

        term = (
            Term.objects
            .order_by("-start_date", "name")
            .first()
        )

        if term is None:
            raise CommandError("No academic term exists.")

        self.stdout.write(
            f"Term: {term.pk} | {term.name}"
        )

        teachers = list(
            Teacher.objects
            .all()
            .order_by("teacher_number")
        )

        if not teachers:
            raise CommandError("No teachers exist.")

        created = 0
        preserved = 0

        for index, teacher in enumerate(teachers):

            assignments = list(
                TeacherFreeAfternoon.objects.filter(
                    teacher=teacher,
                    term=term,
                    is_active=True,
                ).order_by("id")
            )

            if len(assignments) > 1:
                raise CommandError(
                    f"{teacher.employee_code} already has "
                    f"{len(assignments)} active free-afternoon assignments. "
                    "Resolve duplicates before continuing."
                )

            if len(assignments) == 1:
                assignment = assignments[0]

                self.stdout.write(
                    f"PRESERVE | {teacher.employee_code} | "
                    f"{assignment.day}"
                )

                preserved += 1
                continue

            day = self.DAYS[index % len(self.DAYS)]

            TeacherFreeAfternoon.objects.create(
                term=term,
                teacher=teacher,
                day=day,
                is_active=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"CREATE   | {teacher.employee_code} | {day}"
                )
            )

            created += 1

        self.stdout.write(
            "\n=== RESULT ==="
        )

        self.stdout.write(
            f"Preserved existing assignments: {preserved}"
        )

        self.stdout.write(
            f"Created missing assignments: {created}"
        )

        total = TeacherFreeAfternoon.objects.filter(
            term=term,
            is_active=True,
        ).count()

        self.stdout.write(
            f"Total active free-afternoon assignments: {total}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== FREE-AFTERNOON ASSIGNMENT COMPLETE ==="
            )
        )
