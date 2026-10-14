from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.enums import SolverStatus as DomainSolverStatus
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
    SolverStatus as DjangoSolverStatus,
    TimetableEntry,
    TimetableVersion,
)


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    """Result of persisting a generated timetable."""

    timetable_version: TimetableVersion
    scheduling_run: SchedulingRun
    entries_created: int

class TimetablePersistenceService:
    """
    Persist a successful solver result as a timetable version.

    This service is responsible for the application/persistence boundary.

    Solver construction and execution remain independent of Django
    persistence. The service guarantees that timetable version creation,
    timetable entry creation, and scheduling-run completion occur as one
    atomic operation.
    """

    @transaction.atomic
    def persist(
        self,
        *,
        scheduling_run: SchedulingRun,
        solver_result: SolverResult,
        version_name: str,
        version_number: int,
    ) -> PersistenceResult:
        """
        Persist a successful solver result.

        The complete persistence operation is atomic. If validation,
        timetable-version creation, timetable-entry creation, or
        scheduling-run update fails, the entire transaction is rolled back.
        """

        self._validate_solver_result(solver_result)

        self._validate_scheduling_run(scheduling_run)

        self._validate_version_details(
            version_name=version_name,
            version_number=version_number,
        )

        version_number, version_name = self._resolve_version_details(
            term=scheduling_run.term,
            requested_version_number=version_number,
            requested_version_name=version_name,
        )

        assignments = tuple(solver_result.assignments)

        self._validate_assignments(assignments)

        # --------------------------------------------------------------
        # Create the timetable version.
        #
        # _resolve_version_details() has already guaranteed that both
        # the name and number are unique within the term.
        # --------------------------------------------------------------

        TimetableVersion.objects.filter(
            term=scheduling_run.term,
            is_active=True,
        ).update(
            is_active=False,
        )

        timetable_version = TimetableVersion.objects.create(
            term=scheduling_run.term,
            name=version_name,
            version_number=version_number,
            is_published=False,
            is_active=True,
        )

        # --------------------------------------------------------------
        # Convert solver assignments into timetable entries.
        # --------------------------------------------------------------

        entries = self._build_entries(
            timetable_version=timetable_version,
            assignments=assignments,
        )

        entries.extend(
            self._inject_gst_filler(
                entries=entries,
                timetable_version=timetable_version,
            )
        )

        if entries:
            TimetableEntry.objects.bulk_create(entries)

        # --------------------------------------------------------------
        # Complete the scheduling run and explicitly associate it with
        # the timetable version that was just created.
        # --------------------------------------------------------------

        self._complete_scheduling_run(
            scheduling_run=scheduling_run,
            timetable_version=timetable_version,
            solver_result=solver_result,
            entries_created=len(entries),
        )

        return PersistenceResult(
            timetable_version=timetable_version,
            scheduling_run=scheduling_run,
            entries_created=len(entries),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_solver_result(
        solver_result: SolverResult,
    ) -> None:
        """Validate that the solver produced a persistable result."""

        if not solver_result.is_successful:
            raise ValueError(
                "Only FEASIBLE or OPTIMAL solver results can be persisted."
            )

        if solver_result.status not in {
            DomainSolverStatus.FEASIBLE,
            DomainSolverStatus.OPTIMAL,
        }:
            raise ValueError(
                "Unsupported solver status for persistence: "
                f"{solver_result.status!r}"
            )

    @staticmethod
    def _validate_scheduling_run(
        scheduling_run: SchedulingRun,
    ) -> None:
        """Validate the scheduling-run lifecycle state."""

        if scheduling_run.status not in {
            SchedulingRunStatus.PENDING,
            SchedulingRunStatus.RUNNING,
        }:
            raise ValueError(
                "Scheduling run must be PENDING or RUNNING before "
                "timetable persistence."
            )

    @staticmethod
    def _validate_version_details(
        *,
        version_name: str,
        version_number: int,
    ) -> None:
        """Validate timetable-version metadata."""

        if not version_name.strip():
            raise ValueError(
                "Timetable version name cannot be empty."
            )

        if version_number < 1:
            raise ValueError(
                "Timetable version number must be greater than zero."
            )

    @staticmethod
    def _resolve_version_details(
        *,
        term,
        requested_version_number: int,
        requested_version_name: str,
    ) -> tuple[int, str]:
        """
        Resolve both timetable version number and name.

        TimetableVersion has two independent uniqueness constraints:

            (term, version_number)
            (term, name)

        Both values must therefore be unique for the term.
        """

        base_name = requested_version_name.strip()

        # ----------------------------------------------------------
        # Resolve version number.
        # ----------------------------------------------------------

        if TimetableVersion.objects.filter(
            term=term,
            version_number=requested_version_number,
        ).exists():
            highest_version = (
                TimetableVersion.objects.filter(term=term)
                .order_by("-version_number")
                .values_list("version_number", flat=True)
                .first()
            )

            version_number = (highest_version or 0) + 1
        else:
            version_number = requested_version_number

        # ----------------------------------------------------------
        # Resolve version name.
        # ----------------------------------------------------------

        if not TimetableVersion.objects.filter(
            term=term,
            name=base_name,
        ).exists():
            return version_number, base_name

        suffix = 2

        while True:
            candidate_name = f"{base_name} v{suffix}"

            if not TimetableVersion.objects.filter(
                term=term,
                name=candidate_name,
            ).exists():
                return version_number, candidate_name

            suffix += 1

    @staticmethod
    def _validate_assignments(
        assignments: Iterable[SchedulingAssignment],
    ) -> None:
        """
        Validate all solver assignments before database insertion.

        This deliberately validates foreign-key references at the
        application boundary instead of allowing PostgreSQL to discover
        invalid references during transaction teardown.

        The validation also ensures that a solver assignment is internally
        consistent with its lesson requirement and related entities.
        """

        assignments = tuple(assignments)

        if not assignments:
            return

        lesson_requirement_ids = {
            assignment.lesson_requirement_id
            for assignment in assignments
        }

        teacher_ids = {
            assignment.teacher_id
            for assignment in assignments
            if assignment.teacher_id is not None
        }

        instructional_group_ids = {
            assignment.instructional_group_id
            for assignment in assignments
        }

        period_ids = {
            assignment.period_id
            for assignment in assignments
        }

        from apps.academics.models import LessonRequirement, InstructionalGroup
        from apps.scheduling.models import Period
        from apps.users.models import Teacher

        # --------------------------------------------------------------
        # Validate lesson requirements.
        # --------------------------------------------------------------

        existing_requirement_ids = set(
            LessonRequirement.objects.filter(
                id__in=lesson_requirement_ids,
            ).values_list("id", flat=True)
        )

        missing_requirements = (
            lesson_requirement_ids - existing_requirement_ids
        )

        if missing_requirements:
            raise ValueError(
                "Solver assignment references unknown lesson "
                "requirement(s): "
                f"{sorted(str(value) for value in missing_requirements)}"
            )

        # --------------------------------------------------------------
        # Validate teachers.
        # --------------------------------------------------------------

        existing_teacher_ids = set(
            Teacher.objects.filter(
                id__in=teacher_ids,
            ).values_list("id", flat=True)
        )

        missing_teachers = teacher_ids - existing_teacher_ids

        if missing_teachers:
            raise ValueError(
                "Solver assignment references unknown teacher(s): "
                f"{sorted(str(value) for value in missing_teachers)}"
            )

        # --------------------------------------------------------------
        # Validate instructional groups.
        # --------------------------------------------------------------

        existing_group_ids = set(
            InstructionalGroup.objects.filter(
                id__in=instructional_group_ids,
            ).values_list("id", flat=True)
        )

        missing_groups = instructional_group_ids - existing_group_ids

        if missing_groups:
            raise ValueError(
                "Solver assignment references unknown instructional "
                "group(s): "
                f"{sorted(str(value) for value in missing_groups)}"
            )

        # --------------------------------------------------------------
        # Validate periods.
        # --------------------------------------------------------------

        existing_period_ids = set(
            Period.objects.filter(
                id__in=period_ids,
            ).values_list("id", flat=True)
        )

        missing_periods = period_ids - existing_period_ids

        if missing_periods:
            raise ValueError(
                "Solver assignment references unknown period(s): "
                f"{sorted(str(value) for value in missing_periods)}"
            )

        # --------------------------------------------------------------
        # Validate lesson-requirement relationships.
        # --------------------------------------------------------------

        requirements = {
            requirement.id: requirement
            for requirement in LessonRequirement.objects.filter(
                id__in=lesson_requirement_ids,
            )
        }

        for assignment in assignments:
            requirement = requirements[assignment.lesson_requirement_id]

            if (
                assignment.instructional_group_id
                != requirement.instructional_group_id
            ):
                raise ValueError(
                    "Solver assignment instructional group does not match "
                    "the lesson requirement instructional group for lesson "
                    f"requirement {requirement.id}."
                )

    # ------------------------------------------------------------------
    # Timetable entry construction
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_gst_filler(
        *,
        entries: list,
        timetable_version,
    ) -> list:
        """
        Return GST entries for every (group, day, teaching-period) cell
        in the group's active grid that has no real lesson.

        GST slots carry no teacher and no room; they represent guided
        self-study. A per-group LessonRequirement(subject=GST,
        lessons_per_week=1, is_active=False) is created lazily so the
        FK on TimetableEntry.lesson_requirement resolves. The
        requirement carries lessons_per_week=1 only to satisfy the
        ck_lesson_requirement_lessons_positive check constraint;
        because is_active=False the solver never loads it and never
        places it. This is a persistence-only projection.
        """
        from apps.academics.models import (
            LessonRequirement as _LR,
            Subject as _Subject,
        )
        from apps.scheduling.models import Period as _Period

        gst_subject = _Subject.objects.filter(
            code="GST", is_active=True
        ).first()
        if gst_subject is None:
            return []

        group_ids = {
            e.instructional_group_id
            for e in entries
            if e.instructional_group_id
        }
        if not group_ids:
            return []

        teaching_periods = list(
            _Period.objects.filter(
                is_active=True, is_teaching_period=True
            ).order_by("number")
        )
        if not teaching_periods:
            return []

        occupied = {
            (e.instructional_group_id, e.day, e.period_id)
            for e in entries
        }
        days_by_group: dict = {}
        for e in entries:
            if e.instructional_group_id:
                days_by_group.setdefault(e.instructional_group_id, set()).add(
                    e.day
                )

        term = timetable_version.term
        gst_lr_by_group: dict = {}
        for gid in group_ids:
            lr, _ = _LR.objects.get_or_create(
                term=term,
                instructional_group_id=gid,
                subject=gst_subject,
                defaults={
                    "lessons_per_week": 1,
                    "requirement_type": "STANDALONE",
                    "is_active": False,
                },
            )
            gst_lr_by_group[gid] = lr

        filled: list = []
        for gid, days in days_by_group.items():
            lr = gst_lr_by_group[gid]
            for day in sorted(days):
                for period in teaching_periods:
                    if (gid, day, period.id) in occupied:
                        continue
                    filled.append(
                        type(entries[0])(
                            timetable_version=timetable_version,
                            day=day,
                            period_id=period.id,
                            instructional_group_id=gid,
                            teacher_id=None,
                            lesson_requirement_id=lr.id,
                            room_id=None,
                        )
                    )
        return filled

    @staticmethod
    def _build_entries(
        *,
        timetable_version: TimetableVersion,
        assignments: Iterable[SchedulingAssignment],
    ) -> list[TimetableEntry]:
        """
        Project solver assignments into the persisted physical timetable.

        Two-layer projection:

        1. Physical-cell collapse (P3 R1): one row per
           (day, period_id, instructional_group_id). Multi-member
           synchronized block cells keep the minimum lesson_requirement_id
           as the representative.

        2. Teacher-event de-duplication (P4-A): RC#3 B2 collapses a
           synchronized same-teacher cross-stream pair (10E SUBJ + 10W SUBJ,
           same teacher) into one physical teacher event, but the persisted
           table still receives one row per group because
           uq_timetable_entry_group_slot requires it.
           uq_timetable_entry_teacher_slot forbids two rows with the same
           (day, period, teacher). The row with the minimum
           instructional_group_id keeps the teacher; sibling rows are
           written with teacher_id=None, signalling that teacher identity
           is shared via the sibling row of the same physical event.

        This is a persistence projection only. It does not alter solver
        assignments, synchronized-block semantics, or curriculum data.
        """

        cells: dict[tuple, SchedulingAssignment] = {}

        # OPTION C: keep one entry per (day, period, group, lesson_requirement).
        # Block subjects scheduled in parallel all survive; only exact
        # duplicates (same LR at the same slot) are collapsed.
        for assignment in assignments:
            key = (
                assignment.day,
                assignment.period_id,
                assignment.instructional_group_id,
                assignment.lesson_requirement_id,
            )
            current = cells.get(key)
            if current is None:
                cells[key] = assignment
                continue
            if str(assignment.lesson_requirement_id) < str(current.lesson_requirement_id):
                cells[key] = assignment

        entries: list[TimetableEntry] = []

        for assignment in cells.values():
            entries.append(
                TimetableEntry(
                    timetable_version=timetable_version,
                    day=(
                        assignment.day.value
                        if hasattr(assignment.day, "value")
                        else assignment.day
                    ),
                    period_id=assignment.period_id,
                    instructional_group_id=assignment.instructional_group_id,
                    teacher_id=assignment.teacher_id,
                    lesson_requirement_id=assignment.lesson_requirement_id,
                    room_id=assignment.room_id,
                )
            )

        # Teacher slots are no longer collapsed — each block sibling
        # retains its teacher. The (day, period, teacher) unique constraint
        # was never applied in this database, so multiple rows with the
        # same teacher in the same slot are permitted.

        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Room assignment (v2 — sibling-aware, 2026-09-21)
        #
        # 1. Sibling rule: entries that share (day, period, teacher)
        #    represent ONE physical class and MUST share the same room.
        # 2. Preferred room per subject (Chemistry/Biology/IntSci ->
        #    BIOCHEM LAB; Physics -> PHY-LAB; COMP/ICT -> LAB1;
        #    MUSD -> BDRM; PE -> DHL).
        # 3. Fallback: class home room.
        # 4. Final fallback: any unoccupied room.
        # ------------------------------------------------------------------
        from apps.academics.models import LessonRequirement as _LR
        from apps.scheduling.models import Room as _Room

        HOME_ROOM = {
            "Form 4E": "F4E", "Form 4W": "F4W",
            "Grade 10E": "G10E", "Grade 10W": "G10W",
            "Grade 8E": "G8E", "Grade 8W": "G8W",
            "Grade 9E": "G9E", "Grade 9W": "G9W",
        }
        PREFERRED_ROOM = {
            "CHEM": "CHEM/BIO LAB",
            "BIO": "CHEM/BIO LAB",
            "INTSCI": "CHEM/BIO LAB",
            "PHY": "PHY-LAB",
            "COMP": "LAB1",
            "ICT": "LAB1",
            "MUSD": "BDRM",
            "PE": "DHL",
            # Practicals must use their specialist labs
            "BIOPRAC": "CHEM/BIO LAB",
            "CHEMPRAC": "CHEM/BIO LAB",
            "PHYPRAC": "PHY-LAB",
        }

        rooms_by_code = {r.code: r for r in _Room.objects.filter(is_active=True)}

        lr_ids = {e.lesson_requirement_id for e in entries if e.lesson_requirement_id}
        lrs = _LR.objects.filter(id__in=lr_ids).select_related(
            "subject", "instructional_group__teaching_group"
        )
        lr_meta = {
            lr.id: (
                lr.subject.code if lr.subject else "",
                lr.instructional_group.teaching_group.name
                if lr.instructional_group and lr.instructional_group.teaching_group else "",
            )
            for lr in lrs
        }

        entries.sort(
            key=lambda e: (e.day, str(e.period_id), str(e.instructional_group_id))
        )

        occupied: set = set()
        sibling_room: dict = {}

        for entry in entries:
            subj_code, class_name = lr_meta.get(entry.lesson_requirement_id, ("", ""))
            day = entry.day
            period_id = entry.period_id

            teacher_key = (day, period_id, entry.teacher_id) if entry.teacher_id else None

            # Sibling propagation
            if teacher_key and teacher_key in sibling_room:
                entry.room_id = sibling_room[teacher_key]
                continue

            candidates = []
            pref_code = PREFERRED_ROOM.get(subj_code)
            home_code = HOME_ROOM.get(class_name)
            if pref_code and pref_code in rooms_by_code:
                candidates.append(rooms_by_code[pref_code])
            if home_code and home_code in rooms_by_code:
                candidates.append(rooms_by_code[home_code])
            for r in rooms_by_code.values():
                candidates.append(r)

            chosen = None
            for room in candidates:
                key = (day, period_id, room.id)
                if key not in occupied:
                    chosen = room
                    break

            if chosen is None:
                chosen = rooms_by_code.get("PRJ") or next(iter(rooms_by_code.values()), None)

            if chosen is not None:
                entry.room_id = chosen.id
                occupied.add((day, period_id, chosen.id))
                if teacher_key:
                    sibling_room[teacher_key] = chosen.id

        return entries





    # ------------------------------------------------------------------
    # Scheduling-run completion
    # ------------------------------------------------------------------

    @staticmethod
    def _complete_scheduling_run(
        *,
        scheduling_run: SchedulingRun,
        timetable_version: TimetableVersion,
        solver_result: SolverResult,
        entries_created: int,
    ) -> None:
        """
        Mark the scheduling run as successfully completed.

        The scheduling run is explicitly linked to the timetable version
        produced by this execution.
        """

        objective_value: Decimal | None = None

        if solver_result.statistics.objective_value is not None:
            objective_value = Decimal(
                str(solver_result.statistics.objective_value)
            )

        # --------------------------------------------------------------
        # Update scheduling-run lifecycle information.
        # --------------------------------------------------------------

        scheduling_run.status = SchedulingRunStatus.COMPLETED

        scheduling_run.timetable_version = timetable_version

        scheduling_run.solver_status = (
            TimetablePersistenceService._solver_status(
                solver_result.status
            )
        )

        scheduling_run.completed_at = timezone.now()

        scheduling_run.objective_value = objective_value

        scheduling_run.statistics = {
            "wall_time_seconds": (
                solver_result.statistics.wall_time_seconds
            ),
            "branches": solver_result.statistics.branches,
            "conflicts": solver_result.statistics.conflicts,
            "entries_created": entries_created,
        }

        scheduling_run.error_message = ""

        # --------------------------------------------------------------
        # IMPORTANT:
        # timetable_version MUST be included in update_fields.
        #
        # Without this, Django will not write the newly assigned
        # TimetableVersion foreign key to scheduling_run.
        # --------------------------------------------------------------

        scheduling_run.save(
            update_fields=[
                "timetable_version",
                "status",
                "solver_status",
                "completed_at",
                "objective_value",
                "statistics",
                "error_message",
                "updated_at",
            ]
        )

    # ------------------------------------------------------------------
    # Solver-status conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _solver_status(
        status: DomainSolverStatus,
    ) -> str:
        """
        Convert the domain solver status into the Django choice value.
        """

        if status == DomainSolverStatus.FEASIBLE:
            return DjangoSolverStatus.FEASIBLE

        if status == DomainSolverStatus.OPTIMAL:
            return DjangoSolverStatus.OPTIMAL

        raise ValueError(
            "Unsupported solver status for persistence: "
            f"{status!r}"
        )