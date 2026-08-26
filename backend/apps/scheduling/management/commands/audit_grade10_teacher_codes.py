from django.core.management.base import BaseCommand

from apps.scheduling.models import TeacherAssignment


class Command(BaseCommand):
    help = "Audit the current Grade 10 teacher-code assignments against the established timetable mapping."

    ESTABLISHED = {
        "Community Service Learning": {"T016"},
        "ICT Skills": {"T014"},
        "Physical Education": {"T014"},
    }

    CANDIDATES = {
        "Christian Religious Education": {"T002", "T007"},
        "English": {"T011", "T015"},
        "Essential Mathematics / Core Mathematics": {"T004", "T012"},
        "Kiswahili": {"T001", "T017", "T018"},
    }

    def handle(self, *args, **options):
        assignments = (
            TeacherAssignment.objects
            .select_related(
                "teacher",
                "lesson_requirement",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
            )
            .filter(
                lesson_requirement__instructional_group__name="Grade 10",
                lesson_requirement__is_active=True,
            )
        )

        self.stdout.write("\n=== GRADE 10 ASSIGNMENT AUDIT ===\n")

        seen = set()

        for assignment in assignments:
            subject = assignment.lesson_requirement.subject.name
            code = assignment.teacher.employee_code

            seen.add(subject)

            if subject in self.ESTABLISHED:
                status = "CONFIRMED"
            elif subject in self.CANDIDATES:
                status = "CANDIDATE"
            else:
                status = "REVIEW"

            self.stdout.write(
                f"{status:<10} | {code:<5} | {subject}"
            )

        self.stdout.write("\n=== UNASSIGNED GRADE 10 SUBJECTS ===")

        for subject, candidates in self.CANDIDATES.items():
            if subject not in seen:
                self.stdout.write(
                    f"UNASSIGNED | {subject} | "
                    f"possible codes: {', '.join(sorted(candidates))}"
                )

        unresolved = {
            "Group Study",
            "Pastoral/Religious Programme",
        }

        for subject in sorted(unresolved):
            if subject not in seen:
                self.stdout.write(
                    f"UNRESOLVED | {subject} | "
                    f"no teacher code established yet"
                )

        self.stdout.write(
            "\n=== NO DATABASE CHANGES WERE MADE ==="
        )
