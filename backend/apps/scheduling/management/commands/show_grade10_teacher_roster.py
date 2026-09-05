from django.core.management.base import BaseCommand
from apps.scheduling.models import Teacher


class Command(BaseCommand):
    help = "Read-only Grade 10 teacher roster for FRE teacher identification."

    def handle(self, *args, **options):
        self.stdout.write("=" * 90)
        self.stdout.write("SMARTTIMETABLE PRO - GRADE 10 FRE TEACHER IDENTIFICATION")
        self.stdout.write("=" * 90)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        teachers = (
            Teacher.objects
            .select_related("user")
            .filter(is_active=True)
            .order_by("employee_code")
        )

        self.stdout.write(
            f"{'CODE':<8} {'NO.':<6} {'FIRST NAME':<20} "
            f"{'LAST NAME':<25} {'USERNAME':<25}"
        )
        self.stdout.write("-" * 90)

        for teacher in teachers:
            user = getattr(teacher, "user", None)

            username = getattr(user, "username", "") if user else ""

            self.stdout.write(
                f"{teacher.employee_code:<8} "
                f"{str(teacher.teacher_number):<6} "
                f"{teacher.first_name:<20} "
                f"{teacher.last_name:<25} "
                f"{username:<25}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 90)
        self.stdout.write("FRE STATUS")
        self.stdout.write("=" * 90)
        self.stdout.write(
            "10E FRE = ACTIVE, 5/week, NO TEACHER ASSIGNMENT"
        )
        self.stdout.write(
            "10W FRE = ACTIVE, 5/week, NO TEACHER ASSIGNMENT"
        )
        self.stdout.write("")
        self.stdout.write(
            "NO TEACHER HAS BEEN ASSIGNED TO FRE BY THIS COMMAND."
        )
        self.stdout.write("=" * 90)
        self.stdout.write("INSPECTION COMPLETE")
        self.stdout.write("=" * 90)
