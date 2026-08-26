from django.core.management.base import BaseCommand

from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingProblemLoader


class Command(BaseCommand):
    help = "Audit lesson requirements against teacher assignments."

    def handle(self, *args, **options):
        loader = DjangoSchedulingProblemLoader()
        problem = loader.load()

        print("\n=== LESSON REQUIREMENT / TEACHER ASSIGNMENT AUDIT ===")

        assignment_by_requirement = {}

        for assignment in problem.teacher_assignments:
            assignment_by_requirement.setdefault(
                assignment.lesson_requirement_id,
                []
            ).append(assignment.teacher_id)

        total_required = 0

        for requirement in problem.lesson_requirements:
            teachers = assignment_by_requirement.get(
                requirement.id,
                []
            )

            print(
                f"REQ {requirement.id} | "
                f"periods_per_week={requirement.periods_per_week} | "
                f"teachers={len(teachers)}"
            )

            total_required += requirement.periods_per_week

            if not teachers:
                print("  !!! NO TEACHER ASSIGNMENT !!!")

        print("\n=== TOTALS ===")
        print(f"Lesson requirements: {len(problem.lesson_requirements)}")
        print(f"Teacher assignments: {len(problem.teacher_assignments)}")
        print(f"Required weekly lessons: {total_required}")
        print(f"Teaching slots: {len(problem.teaching_periods) * 5}")

        print("\n=== END AUDIT ===")
