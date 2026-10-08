"""
Seed academic results for testing teacher/school analytics.

Creates 4 assessments per term (CAT 1, Opener, Mid-Term, End-Term) for
Terms 1-3 of the active academic year, then generates one Result row per
student per subject they are enrolled in per assessment.

Idempotent: safe to re-run. Uses get_or_create everywhere.

Usage:
    python manage.py seed_academic_results --dry-run
    python manage.py seed_academic_results --commit
    python manage.py seed_academic_results --commit --students 20
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import (
    Assessment,
    InstructionalGroup,
    LessonRequirement,
    Result,
    ResultStatus,
    Student,
    StudentEnrollment,
)
from apps.core.models import AcademicYear, Term


# (name suffix, assessment_type, fraction_of_safe_window)
# Real school order: Opener first, then Mid-Term, then CAT 1, then End-Term.
# "Safe window" = term.start_date .. last non-holiday day of the term.
EXAM_SPECS = (
    ("Opener",   "OPENER",   0.10),
    ("Mid-Term", "MIDTERM",  0.40),
    ("CAT 1",    "CAT",      0.68),
    ("End-Term", "ENDTERM",  0.90),
)

# Last safe day per term name. Exams are placed proportionally between
# term.start_date and this date so nothing lands in a school holiday.
TERM_SAFE_END = {
    "Term 1": (3, 31),   # April is a holiday
    "Term 2": (7, 31),   # August is a holiday
    "Term 3": (10, 31),  # November/December are holidays
}

MAX_MARK = 100
BASELINE_MIN = 40
BASELINE_MAX = 85
DRIFT_RANGE = 10  # marks each exam can drift from baseline


class Command(BaseCommand):
    help = "Seed academic assessments and results for testing."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true",
                            help="Actually write to the database (default: dry-run).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Explicitly dry-run (default behaviour).")
        parser.add_argument("--terms", type=int, default=3,
                            help="Number of terms to seed (default: 3).")
        parser.add_argument("--students", type=int, default=0,
                            help="Limit to first N students (0 = all).")
        parser.add_argument("--seed", type=int, default=42,
                            help="Random seed for reproducibility.")

    def handle(self, *args, **options):
        commit = bool(options["commit"]) and not options["dry_run"]
        random.seed(options["seed"])

        year = AcademicYear.objects.filter(is_active=True).first()
        if year is None:
            self.stderr.write(self.style.ERROR("No active AcademicYear."))
            return

        terms = list(Term.objects.filter(academic_year=year).order_by("number"))
        if not terms:
            self.stderr.write(self.style.ERROR("No terms for active year."))
            return
        terms = terms[: options["terms"]]

        self.stdout.write(f"Year: {year.name} | Terms: {[t.name for t in terms]}")
        self.stdout.write("")

        # ---- Step 1: Assessments ----
        assessment_plan = []  # list of (term, name, type, date)
        for term in terms:
            # Compute the safe window for this term.
            safe_end = None
            for key, (m, d) in TERM_SAFE_END.items():
                if term.name.strip().endswith(key.replace("Term ", "")) or term.name == key:
                    try:
                        safe_end = term.start_date.replace(month=m, day=d)
                    except ValueError:
                        safe_end = term.start_date.replace(month=m, day=28)
                    break
            if safe_end is None or safe_end > term.end_date:
                safe_end = term.end_date - timedelta(days=1)

            window_days = (safe_end - term.start_date).days
            if window_days < len(EXAM_SPECS):
                window_days = len(EXAM_SPECS)

            for suffix, atype, frac in EXAM_SPECS:
                a_date = term.start_date + timedelta(days=int(round(frac * window_days)))
                if a_date > safe_end:
                    a_date = safe_end
                name = f"{term.name} {suffix}"
                assessment_plan.append((term, name, atype, a_date))

        self.stdout.write(f"Assessment plan ({len(assessment_plan)} rows):")
        for term, name, atype, a_date in assessment_plan:
            self.stdout.write(f"  {name:24s} | {atype:8s} | {a_date}")

        created_assessments = 0
        skipped_assessments = 0
        assessment_objects = []

        if commit:
            for term, name, atype, a_date in assessment_plan:
                obj, created = Assessment.objects.get_or_create(
                    academic_year=year,
                    term=term,
                    name=name,
                    defaults={
                        "assessment_type": atype,
                        "date": a_date,
                        "max_mark": MAX_MARK,
                        "status": "PUBLISHED",
                    },
                )
                if created:
                    created_assessments += 1
                else:
                    skipped_assessments += 1
                assessment_objects.append(obj)
        else:
            # In dry-run, resolve the actual objects but don't create
            for term, name, atype, a_date in assessment_plan:
                existing = Assessment.objects.filter(
                    academic_year=year, term=term, name=name
                ).first()
                if existing:
                    skipped_assessments += 1
                    assessment_objects.append(existing)
                else:
                    created_assessments += 1
                    assessment_objects.append(None)  # placeholder

        self.stdout.write("")
        self.stdout.write(
            f"Assessments: would create {created_assessments}, "
            f"reuse {skipped_assessments}"
        )

        # ---- Step 2: Student -> subjects ----
        students_qs = Student.objects.all().order_by("admission_number")
        if options["students"] > 0:
            students_qs = students_qs[: options["students"]]
        students = list(students_qs)

        enrollments = {
            e.student_id: e.teaching_group_id
            for e in StudentEnrollment.objects.filter(
                is_current=True, student__in=students
            )
        }

        # teaching_group_id -> set of subject_ids
        from apps.academics.models import Subject

        group_to_subjects: dict = {}
        igs = InstructionalGroup.objects.filter(
            teaching_group_id__in=set(enrollments.values())
        )
        for ig in igs:
            subject_ids = set(
                LessonRequirement.objects.filter(
                    instructional_group=ig, is_active=True
                ).values_list("subject_id", flat=True)
            )
            group_to_subjects.setdefault(ig.teaching_group_id, set()).update(subject_ids)

        subject_objs = {s.id: s for s in Subject.objects.all()}

        # Build the full result plan
        result_plan = []  # list of (student, subject_id, assessment_index)
        skipped_students = 0
        for student in students:
            tg_id = enrollments.get(student.id)
            if not tg_id:
                skipped_students += 1
                continue
            subject_ids = group_to_subjects.get(tg_id, set())
            if not subject_ids:
                skipped_students += 1
                continue
            for sid in subject_ids:
                for idx, _a in enumerate(assessment_plan):
                    result_plan.append((student.id, sid, idx))

        self.stdout.write("")
        self.stdout.write(
            f"Students: {len(students)} (skipped {skipped_students})"
        )
        self.stdout.write(
            f"Subjects per student group: "
            f"{ {str(k)[:8]: len(v) for k, v in list(group_to_subjects.items())[:3]} } ..."
        )
        self.stdout.write(
            f"Result plan: {len(result_plan)} rows "
            f"({len(result_plan) and 'per-term' } assessments × student × subject)"
        )

        if not commit:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "DRY-RUN. Re-run with --commit to write."
            ))
            return

        # ---- Step 3: Actually write ----
        # Baseline per (student, subject) so trends are coherent
        baselines: dict = {}
        for student_id, subject_id, _idx in result_plan:
            key = (student_id, subject_id)
            if key not in baselines:
                baselines[key] = random.randint(BASELINE_MIN, BASELINE_MAX)

        created_results = 0
        skipped_results = 0

        with transaction.atomic():
            for student_id, subject_id, idx in result_plan:
                assessment = assessment_objects[idx]
                if assessment is None:
                    continue

                base = baselines[(student_id, subject_id)]
                drift = random.randint(-DRIFT_RANGE, DRIFT_RANGE)
                mark = max(0, min(MAX_MARK, base + drift))

                _obj, created = Result.objects.get_or_create(
                    assessment=assessment,
                    student_id=student_id,
                    subject_id=subject_id,
                    defaults={
                        "raw_mark": Decimal(mark),
                        "status": ResultStatus.VALID,
                    },
                )
                if created:
                    created_results += 1
                else:
                    skipped_results += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Created {created_results} results, reused {skipped_results}."
        ))
        self.stdout.write(self.style.SUCCESS("Done."))
