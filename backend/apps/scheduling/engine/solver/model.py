from __future__ import annotations
import math
# ============================================================================
# AUTHORITATIVE SENIOR SCHOOL / GRADE 10 CONTRACT
# ============================================================================
#
# Business-contract definitions live in:
# apps.scheduling.engine.application.grade10_parallel_blocks
#
# This solver module imports the authoritative definitions rather than
# silently maintaining a second copy of the curriculum/timetable contract.
#
# ============================================================================

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_STANDALONE_SYNCHRONIZED,
    FORM3E_PRACTICAL_SUPPORT,
    FORM3E_STANDALONE_CORE,
    FORM3W_PRACTICAL_SUPPORT,
    FORM3W_STANDALONE_CORE,
    FORM4E_PRACTICAL_SUPPORT,
    FORM4E_STANDALONE_CORE,
    FORM4W_PRACTICAL_SUPPORT,
    FORM4W_STANDALONE_CORE,
    FORM3_HUMANITIES_SLOTS,
    FORM3_RELIGIOUS_EDUCATION_SLOTS,
    FORM3_SCIENCE_SLOTS,
    FORM3_TECHNICALS_APPLIED_SLOTS,
    FORM4_HUMANITIES_SLOTS,
    FORM4_RELIGIOUS_EDUCATION_SLOTS,
    FORM4_SCIENCE_SLOTS,
    FORM4_TECHNICALS_APPLIED_SLOTS,
    GRADE10_BLOCK_LEARNER_GROUPS,
    GRADE10_BLOCKS,
    GRADE10_INSTRUCTIONAL_GROUP_CODES,
    GRADE10_PARALLEL_BLOCKS,
    GRADE10_PARALLEL_SUBJECT_TO_BLOCK,
    Grade10ParallelBlock,
    SENIOR_SCHOOL_BLOCK_BY_CODE,
    SENIOR_SCHOOL_BLOCK_LEARNER_GROUPS,
    SENIOR_SCHOOL_BLOCK_SLOTS,
    SENIOR_SCHOOL_BLOCKS,
    SENIOR_SCHOOL_CLASS_CONTRACTS,
    SENIOR_SCHOOL_ELECTIVE_BLOCKS,
    SENIOR_SCHOOL_GEO_HIS_BLOCK,
    SENIOR_SCHOOL_PARALLEL_BLOCKS,
    SENIOR_SCHOOL_PARALLEL_GROUPS,
    SENIOR_SCHOOL_AGR_BST_BLOCK,
    SENIOR_SCHOOL_SCIENCE_BLOCK,
    SENIOR_SCHOOL_SUBJECT_TO_BLOCK,
    SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES,
    SENIOR_SCHOOL_SYNCHRONIZED_STREAM_PAIRS,
    SENIOR_SCHOOL_TECHNICALS_APPLIED_BLOCK,
    SENIOR_SCHOOL_WEEKLY_PERIODS,
    SeniorSchoolBlock,
    SeniorSchoolClassContract,
    SeniorSchoolScheduledLesson,
    are_senior_school_subjects_in_same_block,
    are_subjects_in_same_block,
    describe_grade10_parallel_blocks,
    describe_senior_school_blocks,
    get_block_for_subject,
    get_grade10_parallel_block,
    get_grade10_parallel_block_for_subject,
    get_groups_in_block,
    get_senior_school_block_for_subject,
    get_senior_school_block_slots,
    get_senior_school_class_contract,
    get_subjects_in_block,
    grade10_parallel_slot_count,
    grade10_parallel_subject_count,
    is_grade10_instructional_group,
    is_subject_in_grade10_blocks,
    is_subject_in_senior_school_blocks,
    is_senior_school_instructional_group,
    senior_school_elective_slot_count,
    senior_school_elective_subject_count,
    senior_school_contract_warnings,
    validate_grade10_parallel_blocks,
    validate_senior_school_blocks,
    validate_senior_school_contract,
    validate_senior_school_stream_synchronization,
)

# Canonical contract validation is intentionally explicit.
# The solver must never proceed while the static business contract is invalid.
validate_grade10_parallel_blocks()
validate_senior_school_contract()


from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.objective import (
    COMPLEX_CODES,
    PRACTICAL_CODES,
    apply_solver_objectives,
)
from apps.scheduling.engine.solver.variables import AssignmentVariable


# ------------------------------------------------------------------
# Senior School group recognition
# ------------------------------------------------------------------

SENIOR_SCHOOL_GROUP_CODES: frozenset[str] = frozenset(
    {
        # Authoritative database codes.
        "10",
        "10E",
        "10W",
        "3E",
        "3W",
        "4E",
        "4W",

        # Expanded / compatibility representations.
        "FORM 3",
        "FORM 3E",
        "FORM 3W",
        "FORM3",
        "FORM3E",
        "FORM3W",
        "FORM 4",
        "FORM 4E",
        "FORM 4W",
        "FORM4",
        "FORM4E",
        "FORM4W",
    }
)


def _normalized_group_code(group: object | None) -> str | None:
    if group is None:
        return None

    code = getattr(group, "code", None)

    if code is None:
        return None

    return str(code).strip().upper()


def is_senior_school_instructional_group(
    group: object | None,
) -> bool:
    """
    Return True when an instructional group belongs to Senior School.

    Authoritative database contract:

        10E / 10W -> Grade 10 Senior School
        3E  / 3W  -> Form 3 Senior School
        4E  / 4W  -> Form 4 Senior School

    Grade 10 retains its established Grade 10-specific
    synchronization contract.

    Form 3 and Form 4 use their own authoritative Senior School
    elective-block contract.
    """
    normalized_code = _normalized_group_code(group)

    if not normalized_code:
        return False

    if normalized_code in SENIOR_SCHOOL_GROUP_CODES:
        return True

    compact_code = normalized_code.replace(" ", "")

    return compact_code in {
        "10",
        "10E",
        "10W",
        "3E",
        "3W",
        "4E",
        "4W",
        "FORM3",
        "FORM3E",
        "FORM3W",
        "FORM4",
        "FORM4E",
        "FORM4W",
    }


def is_form3_instructional_group(
    group: object | None,
) -> bool:
    """
    Return True for the authoritative Form 3 instructional groups.

    Database codes:
        3E
        3W
    """
    normalized_code = _normalized_group_code(group)

    if not normalized_code:
        return False

    return normalized_code.replace(" ", "") in {
        "3E",
        "3W",
        "FORM3",
        "FORM3E",
        "FORM3W",
    }


def is_form4_instructional_group(
    group: object | None,
) -> bool:
    """
    Return True for the authoritative Form 4 instructional groups.

    Database codes:
        4E
        4W
    """
    normalized_code = _normalized_group_code(group)

    if not normalized_code:
        return False

    return normalized_code.replace(" ", "") in {
        "4E",
        "4W",
        "FORM4",
        "FORM4E",
        "FORM4W",
    }


# ------------------------------------------------------------------
# Grade 10 synchronized curriculum blocks
# ------------------------------------------------------------------

GRADE10_SYNCHRONIZED_BLOCKS: tuple[frozenset[str], ...] = tuple(
    frozenset(block.subject_codes)
    for block in GRADE10_PARALLEL_BLOCKS
)


def _normalized_subject_code(requirement) -> str | None:
    code = getattr(requirement, "subject_code", None)

    if code is None:
        return None

    return str(code).strip().upper()


def _synchronized_block_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for block in GRADE10_SYNCHRONIZED_BLOCKS:
        if normalized in block:
            return block

    return None


# ------------------------------------------------------------------
# Grade 10 synchronized option blocks
# ------------------------------------------------------------------

GRADE10_OPTION_BLOCKS = GRADE10_SYNCHRONIZED_BLOCKS


def _is_block_requirement(requirement) -> bool:
    """
    Return True only for requirements structurally classified as BLOCK.

    Requirement type is authoritative. Subject code alone is insufficient
    because the same subject may have both BLOCK and PRACTICAL requirements.
    """
    return (
        str(
            getattr(requirement, "requirement_type", "")
        ).strip().upper()
        == "BLOCK"
    )


def option_block_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    """Return the established Grade 10 option block for a subject code."""

    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for block in GRADE10_OPTION_BLOCKS:
        if normalized in block:
            return block

    return None


# ====================================================================
# SENIOR SCHOOL BLOCK RESOLUTION
# ====================================================================

def senior_school_block_for_subject(
    subject_code: str | None,
) -> SeniorSchoolBlock | None:
    """
    Resolve a subject to the authoritative Senior School elective block.

    This is deliberately separate from Grade 10 option-block resolution.

    Form 3 / Form 4 blocks are:

        SCIENCE
        HUMANITIES
        RELIGIOUS EDUCATION
        TECHNICALS_APPLIED
    """
    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    try:
        return get_senior_school_block_for_subject(normalized)
    except (KeyError, ValueError):
        return None


def senior_school_block_code_for_subject(
    subject_code: str | None,
) -> str | None:
    block = senior_school_block_for_subject(subject_code)

    if block is None:
        return None

    code = getattr(block, "code", None)

    if code is None:
        return None

    return str(code).strip().upper()


def _senior_school_block_slots_for_code(
    block_code: str,
    *,
    group_code: str | None = None,
) -> tuple[tuple[str, object], ...]:
    """
    Return the authoritative physical slot positions for one Senior
    School block.

    Senior School block positions are class-specific in the canonical
    contract. Therefore the group code must be supplied whenever the
    canonical helper requires it.

    The legacy mapping is retained only as a defensive fallback.
    """
    normalized_block = str(block_code).strip().upper()
    normalized_group = (
        str(group_code).strip().upper()
        if group_code is not None
        else None
    )

    if normalized_group:
        try:
            slots = get_senior_school_block_slots(
                normalized_group,
                normalized_block,
            )
            return tuple(slots)
        except (KeyError, ValueError, TypeError):
            pass

    legacy_slots = SENIOR_SCHOOL_BLOCK_SLOTS.get(
        normalized_block,
        (),
    )

    return tuple(legacy_slots)
def _slot_key(day: object, period_id: UUID) -> tuple[str, UUID]:
    day_value = (
        day.value
        if hasattr(day, "value")
        else str(day)
    )
    return (
        str(day_value).strip().upper(),
        period_id,
    )


def _contract_slot_keys(
    slots: tuple[tuple[str, object], ...],
    problem: SchedulingProblem,
) -> frozenset[tuple[str, UUID]]:
    """
    Convert authoritative (DAY, PERIOD_ORDINAL) block positions into
    the actual (DAY, period_id) keys used by AssignmentVariable.

    The business contract stores teaching-period ordinals
    (1 = first active teaching period, 2 = second, ...), not raw
    PeriodEntity numbers. Break/Lunch periods and any other
    non-teaching periods are excluded from the ordinal sequence.

    This matters whenever the term contains non-teaching periods
    between teaching periods: raw numbers and teaching-ordinals
    diverge from the first non-teaching slot onwards.
    """
    ordered_periods = sorted(
        (
            period
            for period in problem.periods
            if period.is_active and period.is_teaching_period
        ),
        key=lambda period: int(period.number),
    )

    period_ids_by_ordinal: dict[int, UUID] = {
        ordinal: period.id
        for ordinal, period in enumerate(ordered_periods, start=1)
    }

    resolved: set[tuple[str, UUID]] = set()

    for day, period_ordinal in slots:
        normalized_day = str(day).strip().upper()

        try:
            ordinal = int(period_ordinal)
        except (TypeError, ValueError):
            continue

        period_id = period_ids_by_ordinal.get(ordinal)

        if period_id is not None:
            resolved.add(
                (
                    normalized_day,
                    period_id,
                )
            )

    return frozenset(resolved)


def _senior_school_group_block_code(
    group: object | None,
    subject_code: str | None,
) -> str | None:
    """
    Resolve a Senior School block only for Form 3/Form 4 groups.

    Grade 10 continues through its separate Grade 10 option-block
    machinery.
    """
    if group is None:
        return None

    if not (
        is_form3_instructional_group(group)
        or is_form4_instructional_group(group)
    ):
        return None

    return senior_school_block_code_for_subject(subject_code)


def _senior_school_block_definition(
    block_code: str,
) -> SeniorSchoolBlock:
    normalized = str(block_code).strip().upper()

    definition = SENIOR_SCHOOL_BLOCK_BY_CODE.get(normalized)

    if definition is None:
        raise ValueError(
            "Missing Senior School elective block definition: "
            f"{normalized}"
        )

    return definition


def _senior_school_block_subject_codes(
    block_code: str,
) -> frozenset[str]:
    definition = _senior_school_block_definition(block_code)

    subject_codes = getattr(
        definition,
        "subject_codes",
        (),
    )

    return frozenset(
        str(code).strip().upper()
        for code in subject_codes
    )


def _senior_school_block_weekly_shared_slots(
    block_code: str,
) -> int:
    definition = _senior_school_block_definition(block_code)

    value = getattr(
        definition,
        "weekly_shared_slots",
        None,
    )

    if value is None:
        value = getattr(
            definition,
            "weekly_lessons",
            None,
        )

    if value is None:
        raise ValueError(
            "Senior School block definition has no weekly quota: "
            f"{block_code}"
        )

    return int(value)


# ====================================================================
# LEGACY SIMULTANEOUS SUBJECT CONTRACT
# ====================================================================
#
# This remains available for any future independently-authorized
# simultaneous subject contract. It is intentionally NOT used as the
# Senior School elective-block mechanism.
# ====================================================================

SIMULTANEOUS_SUBJECT_GROUPS: tuple[frozenset[str], ...] = ()


def simultaneous_group_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for group in SIMULTANEOUS_SUBJECT_GROUPS:
        if normalized in group:
            return group

    return None


@dataclass(slots=True)
class SolverModel:
    """
    CP-SAT model together with the assignment variables created for it.
    """

    model: cp_model.CpModel
    variables: tuple[AssignmentVariable, ...]
    available_room_ids_by_slot: dict[
        tuple[str, UUID],
        tuple[UUID, ...],
    ] = field(default_factory=dict)

    assumption_names: tuple[str, ...] = ()

    def variables_for_lesson(
        self,
        lesson_requirement_id: UUID,
    ):
        """Return variables belonging to one lesson requirement."""
        return tuple(
            variable
            for variable in self.variables
            if variable.lesson_requirement_id == lesson_requirement_id
        )


class SolverModelBuilder:
    """
    Builds a CP-SAT model from a validated SchedulingProblem.

    Grade 10 and Form 3/Form 4 use separate authoritative block
    contracts.

    Grade 10:
        - Grade 10 option-block enforcement.
        - 10E <-> 10W synchronization.

    Form 3:
        - Science block.
        - Humanities block.
        - Religious Education block.
        - Technicals / Applied block.
        - 3E <-> 3W synchronization.

    Form 4:
        - Science block.
        - Humanities block.
        - Religious Education block.
        - Technicals / Applied block.
        - 4E <-> 4W synchronization.

    Stream-specific practical requirements remain independent from
    elective block requirements and are therefore not folded into the
    block quota.
    """

    def __init__(self, objective=None):
        self.objective = objective
        self._assumption_vars: list[cp_model.IntVar] = []
        self._assumption_names: list[str] = []
        self._available_room_ids_by_slot: dict[
            tuple[str, UUID],
            tuple[UUID, ...],
        ] = {}

    def build(
        self,
        problem: SchedulingProblem,
    ) -> SolverModel:
        model = cp_model.CpModel()

        self._validate_requirement_types(problem)

        variables = self._create_assignment_variables(
            model=model,
            problem=problem,
        )

        self._add_institutional_reserved_period_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_lesson_requirement_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_grade10_option_block_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_grade10_cross_class_synchronization_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_senior_school_elective_block_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_senior_school_cross_class_synchronization_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_grade10_standalone_sync_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_simultaneous_subject_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_complex_adjacency_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_teacher_clash_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_group_clash_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_single_lesson_per_day_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        # ESS and CORE are STANDALONE subjects with independent
        # times. No synchronization constraint applies — the block
        # registry does NOT include them as a synchronized elective.

        self._add_practical_double_lesson_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_practical_cross_stream_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_room_clash_constraints(
            model=model,
            variables=variables,
        )

        self._add_teacher_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_teacher_free_afternoon_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_room_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        apply_solver_objectives(
            model=model,
            problem=problem,
            variables=tuple(variables),
            objective=self.objective,
        )

        return SolverModel(
            model=model,
            variables=tuple(variables),
            available_room_ids_by_slot=dict(
                self._available_room_ids_by_slot
            ),
            assumption_names=tuple(self._assumption_names),
        )

    # ------------------------------------------------------------------
    # Institutional reserved periods
    # ------------------------------------------------------------------

    def _add_institutional_reserved_period_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        period_numbers = {
            period.id: period.number
            for period in problem.periods
        }

        for variable in variables:
            day_value = (
                variable.day.value
                if hasattr(variable.day, "value")
                else str(variable.day)
            ).strip().upper()

            if day_value not in {"MON", "MONDAY"}:
                continue

            if period_numbers.get(variable.period_id) != 1:
                continue

            model.add(variable.variable == 0)

    # ------------------------------------------------------------------
    # Requirement type validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_requirement_types(
        problem: SchedulingProblem,
    ) -> None:
        """
        Validate the structural requirement-type contract before CP-SAT
        variables are created.

        BLOCK, PRACTICAL and STANDALONE are the only valid requirement
        classifications. This prevents malformed database data from being
        interpreted ambiguously by the solver.
        """
        valid_types = {
            "STANDALONE",
            "BLOCK",
            "PRACTICAL",
        }

        invalid = []

        for requirement in problem.lesson_requirements:
            if not requirement.is_active:
                continue

            requirement_type = str(
                getattr(
                    requirement,
                    "requirement_type",
                    "",
                )
            ).strip().upper()

            if requirement_type not in valid_types:
                invalid.append(
                    (
                        str(requirement.id),
                        str(
                            getattr(
                                requirement,
                                "subject_code",
                                "",
                            )
                        ),
                        requirement_type,
                    )
                )

        if invalid:
            raise ValueError(
                "Invalid LessonRequirement requirement_type values "
                "reached the solver: "
                f"{invalid}"
            )

    # ------------------------------------------------------------------
    # Variable creation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_available_room_ids_by_slot(
        problem: SchedulingProblem,
    ) -> dict[tuple[str, UUID], tuple[UUID, ...]]:

        active_rooms = tuple(
            sorted(
                (
                    room
                    for room in problem.rooms
                    if room.is_active
                ),
                key=lambda room: str(room.id),
            )
        )

        unavailable_slots = {
            (
                availability.room_id,
                availability.day.value,
                availability.period_id,
            )
            for availability in problem.room_availability
            if availability.is_active
            and not availability.is_available
        }

        room_ids_by_slot: dict[
            tuple[str, UUID],
            tuple[UUID, ...],
        ] = {}

        for slot in problem.slots:
            period = problem.period_by_id.get(slot.period_id)

            if (
                period is None
                or not period.is_active
                or not period.is_teaching_period
            ):
                continue

            slot_key = (
                slot.day.value,
                slot.period_id,
            )

            room_ids_by_slot[slot_key] = tuple(
                room.id
                for room in active_rooms
                if (
                    room.id,
                    slot.day.value,
                    slot.period_id,
                ) not in unavailable_slots
            )

        return room_ids_by_slot

    def _create_assignment_variables(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
    ) -> list[AssignmentVariable]:

        variables: list[AssignmentVariable] = []

        active_requirements = [
            requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        ]

        active_teachers = [
            teacher
            for teacher in problem.teachers
            if teacher.is_active
        ]

        active_groups = [
            group
            for group in problem.instructional_groups
            if group.is_active
        ]

        self._available_room_ids_by_slot = (
            self._build_available_room_ids_by_slot(problem)
        )

        teachers_by_requirement: dict[
            UUID,
            list[UUID],
        ] = defaultdict(list)

        for assignment in problem.teacher_assignments:
            if not assignment.is_active:
                continue

            teachers_by_requirement[
                assignment.lesson_requirement_id
            ].append(
                assignment.teacher_id
            )

        valid_group_ids = {
            group.id
            for group in active_groups
        }

        valid_teacher_ids = {
            teacher.id
            for teacher in active_teachers
        }

        for requirement in active_requirements:

            if requirement.instructional_group_id not in valid_group_ids:
                continue

            eligible_teacher_ids = [
                teacher_id
                for teacher_id in teachers_by_requirement[
                    requirement.id
                ]
                if teacher_id in valid_teacher_ids
            ]

            teacher_options: list[UUID | None] = (
                eligible_teacher_ids
                if eligible_teacher_ids
                else [None]
            )

            for teacher_id in teacher_options:

                for slot in problem.slots:

                    period = problem.period_by_id.get(
                        slot.period_id
                    )

                    if period is None:
                        continue

                    if not period.is_active:
                        continue

                    if not period.is_teaching_period:
                        continue

                    if (
                        slot.day.value == "MON"
                        and period.number == 1
                    ):
                        continue

                    slot_key = (
                        slot.day.value,
                        slot.period_id,
                    )

                    if not self._available_room_ids_by_slot.get(
                        slot_key
                    ):
                        continue

                    teacher_token = (
                        str(teacher_id)
                        if teacher_id is not None
                        else "NO_TEACHER"
                    )

                    name = (
                        f"assign_"
                        f"{requirement.id}_"
                        f"{teacher_token}_"
                        f"{slot.day.value}_"
                        f"{slot.period_id}"
                    )

                    variable = model.new_bool_var(name)

                    variables.append(
                        AssignmentVariable(
                            lesson_requirement_id=requirement.id,
                            teacher_id=teacher_id,
                            instructional_group_id=(
                                requirement.instructional_group_id
                            ),
                            period_id=slot.period_id,
                            day=slot.day.value,
                            room_id=None,
                            variable=variable,
                        )
                    )

        return variables

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        for requirement_id, requirement in requirements_by_id.items():
            requirement_variables = variables_by_requirement.get(
                requirement_id,
                [],
            )

            model.add(
                sum(
                    variable.variable
                    for variable in requirement_variables
                )
                == requirement.periods_per_week
            )

    def add_named_assumption(
        self,
        *,
        model: cp_model.CpModel,
        name: str,
    ) -> cp_model.IntVar:
        literal = model.new_bool_var(name)
        model.add_assumption(literal)
        self._assumption_vars.append(literal)
        self._assumption_names.append(name)
        return literal

    @property
    def assumption_names(self) -> tuple[str, ...]:
        return tuple(self._assumption_names)

    def _is_grade10_group(self, group: object | None) -> bool:
        return is_grade10_instructional_group(group)

    def _is_senior_school_group(self, group: object | None) -> bool:
        return is_senior_school_instructional_group(group)

    @staticmethod
    def _grade10_block_code(block: frozenset[str]) -> str:
        for block_definition in GRADE10_PARALLEL_BLOCKS:
            if frozenset(block_definition.subject_codes) == block:
                return block_definition.code

        raise ValueError(
            f"Unknown Grade 10 option block: {sorted(block)}"
        )

    # ------------------------------------------------------------------
    # Senior School elective blocks
    # ------------------------------------------------------------------

    def _add_senior_school_elective_block_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Enforce the authoritative Form 3/Form 4 elective blocks.

        For each block within each class:

        1. Every expected active block subject must be represented.
        2. Each block subject can occupy only authoritative block slots.
        3. Each subject can occur at most once in one physical slot.
        4. All subjects in the block occupy the same physical slots.
        5. The block selects exactly its contractual weekly quota.

        The science block intentionally uses its supplied physical slot
        list as a candidate set. Its contract currently supplies more
        physical positions than its weekly shared quota. This method
        therefore selects the contractual quota from those positions and
        does not reinterpret or rewrite the business contract.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        block_requirements: dict[
            tuple[UUID, str],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            group = groups_by_id.get(
                requirement.instructional_group_id
            )

            if not _is_block_requirement(requirement):
                continue

            block_code = _senior_school_group_block_code(
                group,
                requirement.subject_code,
            )

            if block_code is None:
                continue

            block_requirements[
                (
                    requirement.instructional_group_id,
                    block_code,
                )
            ].append(
                requirement.id
            )

        for (
            instructional_group_id,
            block_code,
        ), requirement_ids in block_requirements.items():

            definition = _senior_school_block_definition(
                block_code
            )

            expected_subject_codes = (
                _senior_school_block_subject_codes(
                    block_code
                )
            )

            actual_subject_codes = {
                _normalized_subject_code(
                    requirements_by_id[requirement_id]
                )
                for requirement_id in requirement_ids
            }

            missing_subjects = (
                expected_subject_codes
                - actual_subject_codes
            )

            if missing_subjects:
                raise ValueError(
                    "Senior School elective block is incomplete for "
                    f"instructional group {instructional_group_id}. "
                    f"Block {block_code} is missing active requirements: "
                    f"{sorted(missing_subjects)}"
                )

            weekly_quota = (
                _senior_school_block_weekly_shared_slots(
                    block_code
                )
            )

            weekly_counts = {
                int(
                    requirements_by_id[
                        requirement_id
                    ].periods_per_week
                )
                for requirement_id in requirement_ids
                if _normalized_subject_code(
                    requirements_by_id[requirement_id]
                ) in expected_subject_codes
            }

            if weekly_counts != {weekly_quota}:
                raise ValueError(
                    "Senior School elective block has an invalid "
                    f"weekly quota for instructional group "
                    f"{instructional_group_id}, block {block_code}: "
                    f"{sorted(weekly_counts)}; "
                    f"expected {weekly_quota}."
                )

            group = groups_by_id.get(instructional_group_id)
            if group is None:
                raise ValueError(
                    "Senior school elective block references an unknown "
                    f"instructional group {instructional_group_id}."
                )

            group_code = str(group.code).strip().upper()
            if not group_code:
                raise ValueError(
                    "Senior school elective block references an "
                    f"instructional group {instructional_group_id} "
                    "without a valid group code."
                )

            contract_slots = _contract_slot_keys(
                _senior_school_block_slots_for_code(
                    block_code,
                    group_code=group_code,
                ),
                problem,
            )

            if not contract_slots:
                raise ValueError(
                    "Senior School elective block has no resolvable "
                    f"physical slots for block {block_code}."
                )

            variables_by_requirement_slot: dict[
                tuple[UUID, str, UUID],
                list[cp_model.IntVar],
            ] = defaultdict(list)

            for requirement_id in requirement_ids:
                for variable in variables_by_requirement[
                    requirement_id
                ]:

                    slot_key = (
                        variable.day,
                        variable.period_id,
                    )

                    if slot_key not in contract_slots:
                        model.add(
                            variable.variable == 0
                        )
                        continue

                    variables_by_requirement_slot[
                        (
                            requirement_id,
                            variable.day,
                            variable.period_id,
                        )
                    ].append(
                        variable.variable
                    )

            for requirement_id in requirement_ids:

                for day, period_id in contract_slots:

                    slot_variables = (
                        variables_by_requirement_slot.get(
                            (
                                requirement_id,
                                day,
                                period_id,
                            ),
                            [],
                        )
                    )

                    if slot_variables:
                        model.add_at_most_one(
                            slot_variables
                        )

            representative_id = next(
                requirement_id
                for requirement_id in requirement_ids
                if _normalized_subject_code(
                    requirements_by_id[requirement_id]
                )
                == min(expected_subject_codes)
            )

            all_block_slot_keys = set(contract_slots)

            for day, period_id in all_block_slot_keys:

                representative_expression = sum(
                    variables_by_requirement_slot.get(
                        (
                            representative_id,
                            day,
                            period_id,
                        ),
                        [],
                    )
                )

                for requirement_id in requirement_ids:

                    if requirement_id == representative_id:
                        continue

                    other_expression = sum(
                        variables_by_requirement_slot.get(
                            (
                                requirement_id,
                                day,
                                period_id,
                            ),
                            [],
                        )
                    )

                    _assumption = self.add_named_assumption(
                        model=model,
                        name=(
                            f"block:{block_code}:"
                            f"{instructional_group_id}:"
                            f"{day}:{period_id}:"
                            f"{requirement_id}"
                        ),
                    )
                    model.add(
                        representative_expression
                        == other_expression
                    ).only_enforce_if(_assumption)

            representative_variables = (
                variables_by_requirement[
                    representative_id
                ]
            )

            model.add(
                sum(
                    variable.variable
                    for variable in representative_variables
                )
                == weekly_quota
            )

    # ------------------------------------------------------------------
    # Senior School cross-class synchronization
    # ------------------------------------------------------------------

    def _add_senior_school_cross_class_synchronization_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Synchronize authoritative Senior School elective blocks between:

            3E <-> 3W
            4E <-> 4W

        Synchronization is block-level and physical-slot-level.

        The subjects inside each class block are already synchronized by
        _add_senior_school_elective_block_constraints(). This method
        therefore uses one representative subject per block to synchronize
        the two parallel classes.

        STT-032-D: each class's contractual slot set is resolved
        independently using that class's own group code. The two classes
        must expose identical contract slots for the block; otherwise the
        method refuses to build a partial synchronization and raises.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        group_ids_by_code: dict[str, UUID] = {}

        for group_id, group in groups_by_id.items():

            normalized_code = _normalized_group_code(group)

            if normalized_code in {
                "3E",
                "3W",
                "4E",
                "4W",
            }:
                group_ids_by_code[
                    normalized_code
                ] = group_id

        for first_code, second_code in (
            SENIOR_SCHOOL_SYNCHRONIZED_STREAM_PAIRS
        ):

            first_group_id = group_ids_by_code.get(
                first_code
            )

            second_group_id = group_ids_by_code.get(
                second_code
            )

            if first_group_id is None or second_group_id is None:
                continue

            for block_code in (
                SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES
            ):

                expected_subject_codes = (
                    _senior_school_block_subject_codes(
                        block_code
                    )
                )

                representative_subject_code = min(
                    expected_subject_codes
                )

                representative_ids: dict[str, UUID] = {}

                for group_code, group_id in (
                    (first_code, first_group_id),
                    (second_code, second_group_id),
                ):

                    matching_requirements = [
                        requirement.id
                        for requirement in requirements_by_id.values()
                        if (
                            requirement.instructional_group_id
                            == group_id
                            and _is_block_requirement(requirement)
                            and senior_school_block_code_for_subject(
                                requirement.subject_code
                            )
                            == block_code
                            and _normalized_subject_code(
                                requirement
                            )
                            == representative_subject_code
                        )
                    ]

                    if not matching_requirements:
                        raise ValueError(
                            "Senior School cross-class elective block "
                            "has no representative requirement "
                            f"{representative_subject_code} for "
                            f"{group_code}, block {block_code}."
                        )

                    representative_ids[group_code] = (
                        matching_requirements[0]
                    )

                first_requirement_id = (
                    representative_ids[first_code]
                )

                second_requirement_id = (
                    representative_ids[second_code]
                )

                first_variables_by_slot: dict[
                    tuple[str, UUID],
                    list[cp_model.IntVar],
                ] = defaultdict(list)

                second_variables_by_slot: dict[
                    tuple[str, UUID],
                    list[cp_model.IntVar],
                ] = defaultdict(list)

                for variable in variables_by_requirement[
                    first_requirement_id
                ]:
                    first_variables_by_slot[
                        (
                            variable.day,
                            variable.period_id,
                        )
                    ].append(
                        variable.variable
                    )

                for variable in variables_by_requirement[
                    second_requirement_id
                ]:
                    second_variables_by_slot[
                        (
                            variable.day,
                            variable.period_id,
                        )
                    ].append(
                        variable.variable
                    )

                # STT-032-D: resolve each class's contractual slot set
                # independently using that class's own group code. The
                # pre-fix implementation reused a leaked loop variable
                # (always second_code) and would silently synchronize
                # only the second class's slot set when the two classes
                # diverged.
                first_contract_slots = _contract_slot_keys(
                    _senior_school_block_slots_for_code(
                        block_code,
                        group_code=first_code,
                    ),
                    problem,
                )

                second_contract_slots = _contract_slot_keys(
                    _senior_school_block_slots_for_code(
                        block_code,
                        group_code=second_code,
                    ),
                    problem,
                )

                if first_contract_slots != second_contract_slots:
                    raise ValueError(
                        "Senior School cross-class synchronization "
                        "requires symmetric contract slots for block "
                        f"{block_code} across {first_code} and "
                        f"{second_code}; got "
                        f"{sorted(first_contract_slots)} vs "
                        f"{sorted(second_contract_slots)}."
                    )

                for slot_key in first_contract_slots:

                    model.add(
                        sum(
                            first_variables_by_slot.get(
                                slot_key,
                                [],
                            )
                        )
                        ==
                        sum(
                            second_variables_by_slot.get(
                                slot_key,
                                [],
                            )
                        )
                    )

    # ------------------------------------------------------------------
    # Single lesson per day
    # ------------------------------------------------------------------

    def _add_single_lesson_per_day_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        variables_by_requirement_day: dict[
            tuple[UUID, str],
            list[tuple],
        ] = defaultdict(list)

        for variable in variables:
            variables_by_requirement_day[
                (
                    variable.lesson_requirement_id,
                    variable.day,
                )
            ].append(
                (variable.period_id, variable.variable)
            )

        active_requirements = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        period_by_id = problem.period_by_id

        for (
            requirement_id,
            _day,
        ), entries in variables_by_requirement_day.items():

            requirement = active_requirements.get(requirement_id)
            if requirement is None:
                continue

            # Contract permits more than one lesson of the same subject
            # in a single day when the weekly quota exceeds the number
            # of teaching days. The per-day cap is therefore derived
            # from the weekly quota, not fixed at 1.
            weekly = max(1, int(requirement.periods_per_week))
            _req_type = str(
                getattr(requirement, "requirement_type", "") or ""
            ).strip().upper()
            if _req_type == "PRACTICAL":
                # Practicals are delivered as adjacent double lessons.
                # Allow up to the weekly quota on the same day; the
                # dedicated practical constraint enforces the pairing.
                per_day_cap = weekly
            else:
                per_day_cap = max(1, math.ceil(weekly / 5))

            day_variables = [var for _pid, var in entries]
            model.add(sum(day_variables) <= per_day_cap)

            # Rule 5: when the per-day cap is exactly 2 (subject has
            # lpw > 5 and needs one double per week), the two
            # occurrences MUST be adjacent teaching periods.
            # Forbid every non-adjacent pair on the same day.
            if per_day_cap == 2 and _req_type != "PRACTICAL":
                by_period: dict = {}
                for pid, var in entries:
                    p = period_by_id.get(pid)
                    if p is None:
                        continue
                    n = int(getattr(p, "number", 0) or 0)
                    by_period[n] = var
                nums = sorted(by_period.keys())
                for i in range(len(nums)):
                    for j in range(i + 1, len(nums)):
                        if nums[j] != nums[i] + 1:
                            model.add(
                                by_period[nums[i]]
                                + by_period[nums[j]]
                                <= 1
                            )

    # ------------------------------------------------------------------
    # Legacy simultaneous subject combinations
    # ------------------------------------------------------------------

    def _add_simultaneous_subject_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        if not SIMULTANEOUS_SUBJECT_GROUPS:
            return

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        requirements_by_block: dict[
            tuple[UUID, frozenset[str]],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            block = simultaneous_group_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            requirements_by_block[
                (
                    requirement.instructional_group_id,
                    block,
                )
            ].append(
                requirement.id
            )

        for (
            instructional_group_id,
            block,
        ), requirement_ids in requirements_by_block.items():

            if len(requirement_ids) < 2:
                continue

            requirements = [
                requirements_by_id[requirement_id]
                for requirement_id in requirement_ids
            ]

            weekly_counts = {
                requirement.periods_per_week
                for requirement in requirements
            }

            if len(weekly_counts) != 1:
                raise ValueError(
                    "Simultaneous subject block has mismatched "
                    "weekly lesson counts for instructional group "
                    f"{instructional_group_id}: "
                    f"{sorted(weekly_counts)}."
                )

            slot_keys = {
                (
                    variable.day,
                    variable.period_id,
                )
                for requirement_id in requirement_ids
                for variable in variables_by_requirement[
                    requirement_id
                ]
            }

            for day, period_id in slot_keys:

                slot_variables_by_requirement: dict[
                    UUID,
                    list[cp_model.IntVar],
                ] = {}

                for requirement_id in requirement_ids:

                    slot_variables_by_requirement[
                        requirement_id
                    ] = [
                        variable.variable
                        for variable in variables_by_requirement[
                            requirement_id
                        ]
                        if (
                            variable.day == day
                            and variable.period_id == period_id
                        )
                    ]

                    model.add_at_most_one(
                        slot_variables_by_requirement[
                            requirement_id
                        ]
                    )

                first_requirement_id = requirement_ids[0]

                first_slot_expression = sum(
                    slot_variables_by_requirement[
                        first_requirement_id
                    ]
                )

                for other_requirement_id in requirement_ids[1:]:

                    other_slot_expression = sum(
                        slot_variables_by_requirement[
                            other_requirement_id
                        ]
                    )

                    model.add(
                        first_slot_expression
                        == other_slot_expression
                    )

    # ------------------------------------------------------------------
    # Grade 10 parallel option blocks
    # ------------------------------------------------------------------

    def _add_complex_adjacency_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Hard: no two DISTINCT complex subjects (BIO/CHEM/PHY/MAT)
        or practicals (BIOPRAC/CHEMPRAC/PHYPRAC) may occupy adjacent
        teaching periods on the same day for the same instructional
        group.

        Adjacency semantics:
          - raw Period.number adjacency (n2 == n1 + 1)
          - same-code adjacency allowed (double BIO, double CHEMPRAC)
          - a practical adjacent to a standalone science of any
            code (including its own parent) is forbidden

        Every (group, day, n1, n2, c1, c2) forbidden combination is
        tagged with a named assumption so an INFEASIBLE result can be
        attributed to the specific constraint via the unsat core.
        """
        period_by_id = problem.period_by_id

        reqs_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if getattr(requirement, "is_active", False)
        }

        subject_by_lr: dict = {}
        for lr in reqs_by_id.values():
            code = (
                getattr(lr, "subject_code", None)
                or getattr(getattr(lr, "subject", None), "code", None)
                or ""
            )
            subject_by_lr[lr.id] = str(code).upper()

        indexed: dict = {}
        for variable in variables:
            period = period_by_id.get(variable.period_id)
            if (
                period is None
                or not getattr(period, "is_active", False)
                or not getattr(period, "is_teaching_period", False)
            ):
                continue

            lr_id = getattr(variable, "lesson_requirement_id", None)
            if lr_id is None or lr_id not in reqs_by_id:
                continue

            code = subject_by_lr.get(lr_id, "")
            if not code:
                continue
            # Include both complex subjects and practicals in the
            # adjacency set. Same-code adjacency remains allowed
            # (that is the legitimate practical double).
            if (
                code not in COMPLEX_CODES
                and code not in PRACTICAL_CODES
            ):
                continue

            group_id = getattr(variable, "instructional_group_id", None)
            if group_id is None:
                continue

            day_value = (
                variable.day.value
                if hasattr(variable.day, "value")
                else variable.day
            )
            day = str(day_value).strip().upper()

            try:
                period_number = int(getattr(period, "number"))
            except (TypeError, ValueError):
                continue

            indexed.setdefault(
                (str(group_id), day), {}
            ).setdefault(
                period_number, []
            ).append((code, variable.variable))

        for (group_id, day), periods in indexed.items():
            period_numbers = sorted(periods)
            for i in range(len(period_numbers) - 1):
                n1 = period_numbers[i]
                n2 = period_numbers[i + 1]
                if n2 != n1 + 1:
                    continue
                for c1, v1 in periods[n1]:
                    for c2, v2 in periods[n2]:
                        if c1 == c2:
                            continue
                        assumption = self.add_named_assumption(
                            model=model,
                            name=(
                                f"complex_adjacent:{group_id}:{day}:"
                                f"{n1}:{n2}:{c1}-{c2}"
                            ),
                        )
                        model.add(
                            v1 + v2 <= 1
                        ).only_enforce_if(assumption)

    def _add_grade10_option_block_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        block_requirements: dict[
            tuple[UUID, str],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            group = groups_by_id.get(
                requirement.instructional_group_id
            )

            if not self._is_grade10_group(group):
                continue

            if not _is_block_requirement(requirement):
                continue

            block = option_block_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            block_code = self._grade10_block_code(block)

            block_requirements[
                (
                    requirement.instructional_group_id,
                    block_code,
                )
            ].append(
                requirement.id
            )

        for (
            instructional_group_id,
            block_code,
        ), requirement_ids in block_requirements.items():

            block_definition = next(
                (
                    definition
                    for definition in GRADE10_PARALLEL_BLOCKS
                    if definition.code == block_code
                ),
                None,
            )

            if block_definition is None:
                raise ValueError(
                    "Missing Grade 10 option block definition: "
                    f"{block_code}"
                )

            expected_subject_codes = {
                str(code).strip().upper()
                for code in block_definition.subject_codes
            }

            actual_subject_codes = {
                str(
                    requirements_by_id[
                        requirement_id
                    ].subject_code
                ).strip().upper()
                for requirement_id in requirement_ids
            }

            missing_subjects = (
                expected_subject_codes
                - actual_subject_codes
            )

            if missing_subjects:
                raise ValueError(
                    "Grade 10 option block is incomplete for "
                    f"instructional group {instructional_group_id}. "
                    f"Block {block_code} is missing active requirements: "
                    f"{sorted(missing_subjects)}"
                )

            weekly_counts = {
                requirements_by_id[
                    requirement_id
                ].periods_per_week
                for requirement_id in requirement_ids
            }

            if weekly_counts != {
                block_definition.weekly_shared_slots
            }:
                raise ValueError(
                    "Grade 10 option block has an invalid weekly quota "
                    f"for group {instructional_group_id}, block "
                    f"{block_code}: {sorted(weekly_counts)}; "
                    f"expected {block_definition.weekly_shared_slots}."
                )

            variables_by_requirement_slot: dict[
                tuple[UUID, str, UUID],
                list[cp_model.IntVar],
            ] = defaultdict(list)

            for requirement_id in requirement_ids:
                for variable in variables_by_requirement[
                    requirement_id
                ]:
                    variables_by_requirement_slot[
                        (
                            requirement_id,
                            variable.day,
                            variable.period_id,
                        )
                    ].append(
                        variable.variable
                    )

            for requirement_id in requirement_ids:

                for day in {
                    variable.day
                    for variable in variables_by_requirement[
                        requirement_id
                    ]
                }:

                    for period_id in {
                        variable.period_id
                        for variable in variables_by_requirement[
                            requirement_id
                        ]
                        if variable.day == day
                    }:

                        slot_variables = (
                            variables_by_requirement_slot.get(
                                (
                                    requirement_id,
                                    day,
                                    period_id,
                                ),
                                [],
                            )
                        )

                        if slot_variables:
                            model.add_at_most_one(
                                slot_variables
                            )

            first_requirement_id = requirement_ids[0]

            all_slot_keys = {
                (
                    variable.day,
                    variable.period_id,
                )
                for requirement_id in requirement_ids
                for variable in variables_by_requirement[
                    requirement_id
                ]
            }

            for day, period_id in all_slot_keys:

                first_expression = sum(
                    variables_by_requirement_slot.get(
                        (
                            first_requirement_id,
                            day,
                            period_id,
                        ),
                        [],
                    )
                )

                for other_requirement_id in requirement_ids[1:]:

                    other_expression = sum(
                        variables_by_requirement_slot.get(
                            (
                                other_requirement_id,
                                day,
                                period_id,
                            ),
                            [],
                        )
                    )

                    _assumption = self.add_named_assumption(
                        model=model,
                        name=(
                            f"block:{block_code}:"
                            f"{instructional_group_id}:"
                            f"{day}:{period_id}:"
                            f"{other_requirement_id}"
                        ),
                    )
                    model.add(
                        first_expression
                        == other_expression
                    ).only_enforce_if(_assumption)

            first_requirement_variables = (
                variables_by_requirement[
                    first_requirement_id
                ]
            )

            model.add(
                sum(
                    variable.variable
                    for variable in first_requirement_variables
                )
                == block_definition.weekly_shared_slots
            )

    # ------------------------------------------------------------------
    # Grade 10 cross-class synchronization
    # ------------------------------------------------------------------

    def _add_grade10_cross_class_synchronization_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Force option blocks to use identical physical slots within each
        E/W stream pair (10E<->10W, 11E<->11W, ...).

        Grade 10 and Grade 11 share the same elective-block contract:
            Option 1 = COMP/CHEM, Option 2 = BIO/GEO/HIS,
            Option 3 = PHY/LIT/MUSD, Option 4 = AGR/BUS
        ICT remains STANDALONE.

        Form 3 and Form 4 use their own Senior School synchronization
        contract in the dedicated Senior School method.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        # Discover E/W stream pairs by grade prefix (10E<->10W, 11E<->11W)
        pairs_by_grade: dict[str, dict[str, UUID]] = defaultdict(dict)

        for group_id, group in groups_by_id.items():

            if not self._is_grade10_group(group):
                continue

            group_code = getattr(group, "code", None)

            if group_code is None:
                continue

            normalized_code = str(group_code).strip().upper()

            if len(normalized_code) < 2:
                continue

            stream = normalized_code[-1]
            grade = normalized_code[:-1]

            if stream in {"E", "W"} and grade:
                pairs_by_grade[grade][stream] = group_id

        complete_pairs: dict[str, dict[str, UUID]] = {
            grade: pair
            for grade, pair in pairs_by_grade.items()
            if set(pair) == {"E", "W"}
        }

        if not complete_pairs:
            return

        allowed_codes = {
            f"{grade}{stream}"
            for grade in complete_pairs
            for stream in ("E", "W")
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        requirements_by_group_block: dict[
            tuple[str, str],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            group = groups_by_id.get(
                requirement.instructional_group_id
            )

            if not self._is_grade10_group(group):
                continue

            group_code = getattr(group, "code", None)

            if group_code is None:
                continue

            normalized_group_code = str(
                group_code
            ).strip().upper()

            if normalized_group_code not in allowed_codes:
                continue

            if not _is_block_requirement(requirement):
                continue

            block = option_block_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            requirements_by_group_block[
                (
                    normalized_group_code,
                    self._grade10_block_code(block),
                )
            ].append(requirement.id)

        for grade in complete_pairs:

            first_code = f"{grade}E"
            second_code = f"{grade}W"

            for block_definition in GRADE10_PARALLEL_BLOCKS:

                block_code = block_definition.code

                expected_subject_codes = {
                    str(code).strip().upper()
                    for code in block_definition.subject_codes
                }

                representative_subject_code = str(
                    block_definition.subject_codes[0]
                ).strip().upper()

                representative_ids: dict[str, UUID] = {}

                for group_code in (first_code, second_code):

                    requirement_ids = requirements_by_group_block.get(
                        (group_code, block_code),
                        [],
                    )

                    actual_subject_codes = {
                        _normalized_subject_code(
                            requirements_by_id[requirement_id]
                        )
                        for requirement_id in requirement_ids
                    }

                    missing_subjects = (
                        expected_subject_codes - actual_subject_codes
                    )

                    if missing_subjects:
                        raise ValueError(
                            f"{grade} cross-class option block is incomplete "
                            f"for {group_code}, block {block_code}: "
                            f"missing {sorted(missing_subjects)}"
                        )

                    matching_requirements = [
                        requirement_id
                        for requirement_id in requirement_ids
                        if _normalized_subject_code(
                            requirements_by_id[requirement_id]
                        ) == representative_subject_code
                    ]

                    if not matching_requirements:
                        raise ValueError(
                            f"{grade} cross-class option block has no "
                            f"representative requirement "
                            f"{representative_subject_code} for "
                            f"{group_code}, block {block_code}."
                        )

                    representative_ids[group_code] = (
                        matching_requirements[0]
                    )

                first_requirement_id = representative_ids[first_code]
                second_requirement_id = representative_ids[second_code]

                first_variables_by_slot: dict[
                    tuple[str, UUID],
                    list[cp_model.IntVar],
                ] = defaultdict(list)

                second_variables_by_slot: dict[
                    tuple[str, UUID],
                    list[cp_model.IntVar],
                ] = defaultdict(list)

                for variable in variables_by_requirement[
                    first_requirement_id
                ]:
                    first_variables_by_slot[
                        (
                            variable.day,
                            variable.period_id,
                        )
                    ].append(variable.variable)

                for variable in variables_by_requirement[
                    second_requirement_id
                ]:
                    second_variables_by_slot[
                        (
                            variable.day,
                            variable.period_id,
                        )
                    ].append(variable.variable)

                all_slot_keys = (
                    set(first_variables_by_slot)
                    | set(second_variables_by_slot)
                )

                for slot_key in all_slot_keys:

                    model.add(
                        sum(
                            first_variables_by_slot.get(
                                slot_key,
                                [],
                            )
                        )
                        ==
                        sum(
                            second_variables_by_slot.get(
                                slot_key,
                                [],
                            )
                        )
                    )


    # ------------------------------------------------------------------
    # Teacher clashes
    # ------------------------------------------------------------------

    @staticmethod
    def _assignment_variable_identity(
        variable: AssignmentVariable,
    ) -> tuple:
        """
        Stable identity tuple for one AssignmentVariable.
        """
        return (
            variable.lesson_requirement_id,
            variable.teacher_id,
            variable.instructional_group_id,
            variable.period_id,
            variable.day,
        )

    @staticmethod
    def _synchronized_teacher_event_groups(
        *,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> dict[tuple, tuple[AssignmentVariable, ...]]:
        """
        Return synchronized teacher-event groups relevant to teacher clash.

        Two AssignmentVariables belong to the same synchronized teacher
        event iff ALL of the following hold:
          1. Both have a teacher_id.
          2. Both are BLOCK requirements.
          3. Their instructional groups are a paired set (10E, 10W).
          4. Both map to a Grade-10 option block.
          5. They share block_code, subject_code, teacher_id, day,
             period_id, AND the group is paired (both streams present).

        Such variables represent ONE physical teaching event for the
        teacher under the synchronized Grade-10 contract. The returned
        dict maps each group key to a deterministically ordered tuple of
        members; member[0] is the representative.

        This helper adds NO constraints and does NOT affect room
        occupancy, group occupancy, or persisted workload data.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        def _grade_prefix(stream_code: str) -> str | None:
            """
            Extract the grade prefix from a stream code: 10E -> 10,
            11W -> 11, 4E -> 4. Returns None when the code is not a
            valid E/W stream code.
            """
            sc = str(stream_code).strip().upper()
            if len(sc) < 2 or sc[-1] not in ("E", "W"):
                return None
            return sc[:-1]

        def _group_code(gid: UUID) -> str | None:
            group = groups_by_id.get(gid)
            if group is None:
                return None
            code = getattr(group, "code", None)
            if code is None:
                return None
            return str(code).strip().upper()

        candidates: dict[
            tuple,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:

            if variable.teacher_id is None:
                continue

            requirement = requirements_by_id.get(
                variable.lesson_requirement_id
            )

            if requirement is None:
                continue

            stream_code = _group_code(variable.instructional_group_id)

            if stream_code is None:
                continue

            grade = _grade_prefix(stream_code)

            if grade is None:
                continue

            subject_code = str(requirement.subject_code).strip().upper()

            is_block_req = _is_block_requirement(requirement)
            is_standalone_sync = (
                grade,
                subject_code,
            ) in GRADE10_STANDALONE_SYNCHRONIZED

            if not is_block_req and not is_standalone_sync:
                continue

            if is_block_req:
                block = option_block_for_subject(
                    requirement.subject_code
                )
                if block is None:
                    continue
                block_code = SolverModelBuilder._grade10_block_code(block)
            else:
                # Standalone cross-stream sync: synthesize a unique
                # block code so the group key stays distinct from
                # any real elective block.
                block_code = f"STANDALONE_SYNC_{subject_code}"

            group_key = (
                grade,
                block_code,
                subject_code,
                variable.teacher_id,
                variable.day,
                variable.period_id,
            )

            candidates[group_key].append(variable)

        grouped: dict[tuple, tuple[AssignmentVariable, ...]] = {}

        for group_key, members in candidates.items():

            # group_key[0] is the grade prefix ("10", "11", "4").
            # Pairing is scoped to that single grade, so 10 and 11 can
            # never merge into the same synchronized teacher event.
            grade = group_key[0]

            stream_codes = {
                _group_code(v.instructional_group_id)
                for v in members
            }

            is_paired = (
                (grade + "E") in stream_codes
                and (grade + "W") in stream_codes
            )

            if not is_paired:
                continue

            ordered = tuple(
                sorted(
                    members,
                    key=lambda v: (
                        str(_group_code(v.instructional_group_id) or ""),
                        str(v.lesson_requirement_id),
                    ),
                )
            )

            grouped[group_key] = ordered

        return grouped

    @staticmethod
    def _synchronized_teacher_event_subsumed_keys(
        *,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> frozenset[tuple]:
        """
        Return the identity tuples of variables that must be skipped when
        building teacher-clash buckets because they are subsumed by a
        synchronized representative.
        """
        groups = SolverModelBuilder._synchronized_teacher_event_groups(
            problem=problem,
            variables=variables,
        )

        subsumed: set[tuple] = set()

        for _key, members in groups.items():
            for member in members[1:]:
                subsumed.add(
                    SolverModelBuilder._assignment_variable_identity(member)
                )

        return frozenset(subsumed)

    def _add_teacher_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Enforce at-most-one teacher presence per (teacher, day, period).

        Synchronized Grade-10 block pairs where the same teacher is
        assigned the same subject in both paired streams represent ONE
        physical teacher event and are collapsed to a single
        representative before the at-most-one constraint is applied.

        Room occupancy, group occupancy, and persisted workload data are
        NOT affected. Only teacher-occupancy semantics are collapsed.
        """

        subsumed_keys = self._synchronized_teacher_event_subsumed_keys(
            problem=problem,
            variables=variables,
        )

        groups: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            if variable.teacher_id is None:
                continue

            if self._assignment_variable_identity(variable) in subsumed_keys:
                continue

            groups[
                (
                    variable.teacher_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        for grouped_variables in groups.values():
            model.add_at_most_one(
                grouped_variables
            )

    def _add_group_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Prevent unrelated subjects from sharing a physical
        group/day/period.

        Grade 10 option subjects are parallel.

        Form 3/Form 4 elective-block subjects are also parallel, but
        they are resolved through the authoritative Senior School block
        contract rather than through Grade 10 option blocks.

        Practical / standalone requirements remain ordinary group
        requirements and therefore cannot collide with a block presence.

        Members of the same synchronized block MAY occupy the same
        physical group/day/period: that co-occupation is the semantic
        meaning of the block. Distinct blocks, and ordinary
        requirements, remain mutually exclusive within a physical cell.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        cells: dict[
            tuple[UUID, str, UUID],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            cells[
                (
                    variable.instructional_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(variable)

        for (
            instructional_group_id,
            day,
            period_id,
        ), cell_variables in cells.items():

            requirement_variables: dict[
                UUID,
                list[cp_model.IntVar],
            ] = defaultdict(list)

            requirement_blocks: dict[
                UUID,
                tuple[str, object] | None,
            ] = {}

            group = groups_by_id.get(
                instructional_group_id
            )

            for variable in cell_variables:

                requirement = requirements_by_id.get(
                    variable.lesson_requirement_id
                )

                block_key = None

                if requirement is not None and group is not None:

                    if (
                        _is_block_requirement(requirement)
                        and self._is_grade10_group(group)
                    ):

                        grade10_block = option_block_for_subject(
                            requirement.subject_code
                        )

                        if grade10_block is not None:
                            block_key = (
                                "GRADE10",
                                self._grade10_block_code(
                                    grade10_block
                                ),
                            )

                    elif (
                        _is_block_requirement(requirement)
                        and (
                            is_form3_instructional_group(group)
                            or is_form4_instructional_group(group)
                        )
                    ):

                        senior_block_code = (
                            senior_school_block_code_for_subject(
                                requirement.subject_code
                            )
                        )

                        if senior_block_code is not None:
                            block_key = (
                                "SENIOR",
                                senior_block_code,
                            )

                requirement_id = variable.lesson_requirement_id

                requirement_variables[
                    requirement_id
                ].append(
                    variable.variable
                )

                requirement_blocks[
                    requirement_id
                ] = block_key

            requirement_presence: dict[
                UUID,
                cp_model.IntVar,
            ] = {}

            for requirement_id, requirement_vars in (
                requirement_variables.items()
            ):

                model.add_at_most_one(
                    requirement_vars
                )

                presence = model.new_bool_var(
                    (
                        "cell_presence_"
                        f"{instructional_group_id}_"
                        f"{day}_"
                        f"{period_id}_"
                        f"{requirement_id}"
                    )
                )

                model.add(
                    presence == sum(requirement_vars)
                )

                requirement_presence[
                    requirement_id
                ] = presence

            ordinary_presence: list[cp_model.IntVar] = []

            block_requirement_ids: dict[
                tuple[str, object],
                list[UUID],
            ] = defaultdict(list)

            for requirement_id, block_key in (
                requirement_blocks.items()
            ):

                if block_key is None:

                    ordinary_presence.append(
                        requirement_presence[
                            requirement_id
                        ]
                    )

                else:

                    block_requirement_ids[
                        block_key
                    ].append(
                        requirement_id
                    )

            block_presence: list[cp_model.IntVar] = []

            for block_key, requirement_ids in (
                block_requirement_ids.items()
            ):

                if not requirement_ids:
                    continue

                namespace, block_code = block_key
                block_label = str(block_code)

                presence = model.new_bool_var(
                    (
                        "parallel_block_presence_"
                        f"{instructional_group_id}_"
                        f"{day}_"
                        f"{period_id}_"
                        f"{namespace}_"
                        f"{block_label}"
                    )
                )

                # A synchronized block is present iff ANY of its
                # member requirements is present. Using max (not
                # sum) is required: multiple members of the same
                # synchronized block may legitimately occupy the
                # same physical group/day/period, and a sum-based
                # equality would either exceed the boolean range
                # or fail to represent this case correctly.
                for _rid in requirement_ids:
                    model.add(
                        requirement_presence[_rid] == presence
                    )

                block_presence.append(presence)

            model.add_at_most_one(
                ordinary_presence + block_presence
            )

    def _add_room_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        variables: list[AssignmentVariable],
    ) -> None:

        assignments_by_slot: dict[
            tuple[str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:
            assignments_by_slot[
                (
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        for slot_key, slot_variables in assignments_by_slot.items():

            available_room_ids = (
                self._available_room_ids_by_slot.get(slot_key)
            )

            if available_room_ids is None:
                raise RuntimeError(
                    "Room candidates are missing for timetable slot "
                    f"{slot_key!r}."
                )

            model.add(
                sum(slot_variables) <= len(available_room_ids)
            )

    # ------------------------------------------------------------------
    # Teacher availability
    # ------------------------------------------------------------------

    def _add_teacher_availability_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        unavailable_slots: set[
            tuple[UUID, str, UUID]
        ] = {
            (
                availability.teacher_id,
                availability.day.value,
                availability.period_id,
            )
            for availability in problem.teacher_availability
            if availability.is_active
            and not availability.is_available
        }

        for variable in variables:

            if variable.teacher_id is None:
                continue

            key = (
                variable.teacher_id,
                variable.day,
                variable.period_id,
            )

            if key in unavailable_slots:
                model.add(
                    variable.variable == 0
                )

    # ------------------------------------------------------------------
    # Teacher free afternoon
    # ------------------------------------------------------------------

    def _add_teacher_free_afternoon_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        for teacher in problem.teachers:

            if not teacher.is_active:
                continue

            free_afternoon = problem.teacher_free_afternoon(
                teacher.id
            )

            if free_afternoon is None:
                raise ValueError(
                    f"Teacher {teacher.id} has no free-afternoon assignment."
                )

            for variable in variables:

                if variable.teacher_id is None:
                    continue

                if variable.teacher_id != teacher.id:
                    continue

                if variable.day != free_afternoon.day.value:
                    continue

                period = problem.period_by_id.get(
                    variable.period_id
                )

                if period is None:
                    continue

                if not period.is_active:
                    continue

                if not period.is_teaching_period:
                    continue

                if period.part_of_day != PartOfDay.AFTERNOON:
                    continue

                model.add(
                    variable.variable == 0
                )

    # ------------------------------------------------------------------
    # Room availability
    # ------------------------------------------------------------------

    def _add_maths_elective_sync_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        ESS (E streams) and CORE (W streams) must run at the same
        (day, period) slots. The two subjects are the E/W halves of
        the maths elective block; different students take them, so
        they must be co-scheduled.

        Applies to each E/W pair for Grade 10 and Grade 11.
        """
        from collections import defaultdict

        pairs = [
            ("10E", "10W"),
            ("11E", "11W"),
        ]

        groups_by_id = {
            g.id: g for g in problem.instructional_groups
        }
        reqs_by_id = {
            r.id: r
            for r in problem.lesson_requirements
            if getattr(r, "is_active", False)
        }

        lr_by_gs: dict = {}
        for r in reqs_by_id.values():
            gid = getattr(r, "instructional_group_id", None)
            if gid is None:
                continue
            g = groups_by_id.get(gid)
            if g is None:
                continue
            sc = str(
                getattr(r, "subject_code", "") or ""
            ).strip().upper()
            if sc not in {"ESS", "CORE"}:
                continue
            lr_by_gs[(str(g.code).strip().upper(), sc)] = r

        vars_by_lr_slot: dict = defaultdict(dict)
        for v in variables:
            lrid = getattr(v, "lesson_requirement_id", None)
            if lrid is None:
                continue
            vars_by_lr_slot[lrid][
                (v.day, v.period_id)
            ] = v.variable

        for e_code, w_code in pairs:
            e_lr = lr_by_gs.get((e_code, "ESS"))
            w_lr = lr_by_gs.get((w_code, "CORE"))
            if e_lr is None or w_lr is None:
                continue
            e_slots = vars_by_lr_slot.get(e_lr.id, {})
            w_slots = vars_by_lr_slot.get(w_lr.id, {})
            for slot in set(e_slots) | set(w_slots):
                e_var = e_slots.get(slot)
                w_var = w_slots.get(slot)
                if e_var is None or w_var is None:
                    continue
                _assumption = self.add_named_assumption(
                    model=model,
                    name=(
                        f"ess_core_sync:{e_code}_{w_code}:"
                        f"{slot[0]}:{slot[1]}"
                    ),
                )
                model.add(
                    e_var == w_var
                ).only_enforce_if(_assumption)

    def _add_grade10_standalone_sync_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Force registered STANDALONE cross-stream subjects (currently
        only Grade 10 ENG for 10E/10W) to occupy the same physical
        (day, period) across both streams of the same grade.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if getattr(requirement, "is_active", False)
        }
        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if getattr(group, "is_active", False)
        }

        def _group_code(gid):
            g = groups_by_id.get(gid)
            if g is None:
                return None
            code = getattr(g, "code", None)
            return str(code).strip().upper() if code else None

        # Bucket variables by (grade, subject_code, slot).
        buckets: dict = {}
        for v in variables:
            req = requirements_by_id.get(v.lesson_requirement_id)
            if req is None:
                continue
            if _is_block_requirement(req):
                continue
            sc = str(getattr(req, "subject_code", "") or "").strip().upper()
            gc = _group_code(v.instructional_group_id)
            if gc is None or len(gc) < 2 or gc[-1] not in ("E", "W"):
                continue
            grade = gc[:-1]
            if (grade, sc) not in GRADE10_STANDALONE_SYNCHRONIZED:
                continue
            key = (grade, sc, v.day, v.period_id)
            buckets.setdefault(key, []).append((gc, v.variable))

        for (grade, sc, day, period_id), members in buckets.items():
            by_stream: dict = {}
            for stream_code, var in members:
                by_stream.setdefault(stream_code, []).append(var)
            e_vars = by_stream.get(grade + "E", [])
            w_vars = by_stream.get(grade + "W", [])
            if not e_vars or not w_vars:
                # Only one side has a variable at this slot; nothing
                # to synchronize.
                continue
            # All vars on each side should be identical (at most one
            # LR per group per slot in practice). Force equality.
            e_repr = e_vars[0]
            w_repr = w_vars[0]
            model.add(e_repr == w_repr)

    def _add_practical_cross_stream_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Universal: within the same grade level, at most one practical
        may occupy a given (day, period) across BOTH E and W streams.

        Rationale: 4E and 4W (and future 10E/10W practical schemes)
        share lab facilities and cannot run practicals simultaneously.
        The rule is a no-op when no practical LRs exist for a grade
        level — it only constrains slots where practical variables
        actually exist.

        Applies to any E/W stream pair of the same grade prefix
        (4, 10, 11, 12, ...). Does not distinguish by subject — the
        constraint is on the physical slot, not the practical subject.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if getattr(requirement, "is_active", False)
        }
        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if getattr(group, "is_active", False)
        }

        def _group_code(gid):
            g = groups_by_id.get(gid)
            if g is None:
                return None
            code = getattr(g, "code", None)
            return str(code).strip().upper() if code else None

        buckets: dict = {}
        for v in variables:
            req = requirements_by_id.get(v.lesson_requirement_id)
            if req is None:
                continue
            rt = str(
                getattr(req, "requirement_type", "") or ""
            ).strip().upper()
            if rt != "PRACTICAL":
                continue
            gc = _group_code(v.instructional_group_id)
            if gc is None or len(gc) < 2 or gc[-1] not in ("E", "W"):
                continue
            grade = gc[:-1]
            key = (grade, v.day, v.period_id)
            buckets.setdefault(key, []).append(v.variable)

        for (grade, day, period_id), var_list in buckets.items():
            if len(var_list) <= 1:
                # Only one stream has a practical here — no cross-
                # stream constraint needed.
                continue
            model.add(sum(var_list) <= 1)

    def _add_practical_double_lesson_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """Practicals (requirement_type == 'PRACTICAL', lpw=2):
          - exactly one adjacent pair per week
          - same day, consecutive periods
          - window P5..P12 (start P5..P11); P1..P4 forbidden

        Discriminated by requirement_type, not by subject_code
        suffix. A practical LR's subject is the parent subject
        (CHEM, BIO, PHY, CS), not a PRAC-suffixed code.
        """
        PAIRS = [(5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 12)]
        DAYS = ("MON", "TUE", "WED", "THU", "FRI")

        reqs_by_id = {
            r.id: r
            for r in problem.lesson_requirements
            if getattr(r, "is_active", False)
        }
        pnum_by_id: dict = {}
        for per in problem.periods:
            try:
                pnum_by_id[getattr(per, "id")] = int(
                    getattr(per, "number", 0) or 0
                )
            except Exception:
                pass

        vars_by_req: dict = {}
        for v in variables:
            rid = getattr(v, "lesson_requirement_id", None)
            if rid in reqs_by_id:
                vars_by_req.setdefault(rid, []).append(v)

        def _new_bool(name: str):
            try:
                return model.new_bool_var(name)
            except AttributeError:
                return model.NewBoolVar(name)

        for req_id, req_vars in vars_by_req.items():
            req = reqs_by_id[req_id]
            subj = str(getattr(req, "subject_code", "") or "").strip().upper()
            if str(getattr(req, "requirement_type", "") or "").strip().upper() != "PRACTICAL":
                continue
            lpw = int(
                getattr(req, "periods_per_week", None)
                or getattr(req, "lessons_per_week", 0)
                or 0
            )
            if lpw != 2:
                continue

            # Index variables by (day, period-number)
            by_dp: dict = {}
            for v in req_vars:
                pnum = pnum_by_id.get(v.period_id)
                if pnum is None:
                    continue
                by_dp[(str(v.day).upper(), pnum)] = v

            # Forbid everything outside the P5..P12 window
            for (day, pnum), v in by_dp.items():
                if pnum < 5 or pnum > 12:
                    model.add(v.variable == 0)

            # Build candidate pair booleans
            pair_bools = []
            for day in DAYS:
                for (p1, p2) in PAIRS:
                    v1 = by_dp.get((day, p1))
                    v2 = by_dp.get((day, p2))
                    if v1 is None or v2 is None:
                        continue
                    b = _new_bool(f"prac_{str(req_id)[:8]}_{day}_{p1}")
                    # When b is true, both periods must be scheduled...
                    model.add(v1.variable == 1).only_enforce_if(b)
                    model.add(v2.variable == 1).only_enforce_if(b)
                    # ...and every other slot for this requirement must be 0
                    for (d2, p3), v_other in by_dp.items():
                        if d2 == day and p3 in (p1, p2):
                            continue
                        model.add(v_other.variable == 0).only_enforce_if(b)
                    pair_bools.append(b)

            if pair_bools:
                model.add(sum(pair_bools) == 1)
            else:
                # No valid pair — force the requirement off entirely
                for v in req_vars:
                    model.add(v.variable == 0)

    def _add_room_availability_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Room availability is applied while building candidates and
        enforcing per-slot room capacity.

        Room IDs remain unassigned at this solver-variable layer;
        the available-room candidate map therefore provides the
        authoritative capacity for each teaching slot.
        """
        return


# ----------------------------------------------------------------------
# End of authoritative solver model
# ----------------------------------------------------------------------