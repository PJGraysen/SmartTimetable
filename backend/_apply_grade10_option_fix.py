from pathlib import Path
import re

path = Path(r"C:\Projects\SmartTimetable\backend\apps\scheduling\engine\solver\model.py")
text = path.read_text(encoding="utf-8")

# ================================================================
# LESSON REQUIREMENT CONSTRAINTS
# ================================================================

new_method = '''    def _add_lesson_requirement_constraints(
        self,
        model: cp_model.CpModel,
        variables: list[AssignmentVariable],
        problem: SchedulingProblem,
    ) -> None:
        """
        Enforce weekly lesson demand.

        Ordinary requirements retain their exact weekly demand.

        Grade 10 elective subjects are alternatives within a shared
        physical option block. Each block therefore consumes exactly
        its authoritative weekly_shared_slots.
        """
        variables_by_requirement: dict[UUID, list[AssignmentVariable]] = {}

        for variable in variables:
            variables_by_requirement.setdefault(
                variable.lesson_requirement_id,
                [],
            ).append(variable)

        grade10_blocks: dict[
            tuple[UUID, str],
            list[LessonRequirementEntity],
        ] = {}

        for requirement in problem.lesson_requirements:
            if not requirement.is_active:
                continue

            subject_code = getattr(requirement, "subject_code", None)

            block = None

            if (
                _is_grade10_group(
                    problem,
                    requirement.instructional_group_id,
                )
                and subject_code in GRADE10_PARALLEL_SUBJECT_TO_BLOCK
            ):
                block = get_grade10_parallel_block_for_subject(
                    subject_code
                )

            if block is not None:
                key = (
                    requirement.instructional_group_id,
                    block.code,
                )
                grade10_blocks.setdefault(key, []).append(requirement)
                continue

            requirement_variables = variables_by_requirement.get(
                requirement.id,
                [],
            )

            model.add(
                sum(
                    variable.variable
                    for variable in requirement_variables
                )
                == requirement.periods_per_week
            )

        for (group_id, block_code), requirements in grade10_blocks.items():
            block = get_grade10_parallel_block(block_code)

            block_variables = []

            for requirement in requirements:
                block_variables.extend(
                    variable.variable
                    for variable in variables_by_requirement.get(
                        requirement.id,
                        [],
                    )
                )

            model.add(
                sum(block_variables) == block.weekly_shared_slots
            )
'''

pattern = re.compile(
    r"    def _add_lesson_requirement_constraints\(.*?(?=\n    def _add_grade10_option_block_constraints\()",
    re.DOTALL,
)

match = pattern.search(text)

if not match:
    raise RuntimeError(
        "Could not locate _add_lesson_requirement_constraints()"
    )

text = (
    text[:match.start()]
    + new_method
    + "\n"
    + text[match.end():]
)

# ================================================================
# OPTION BLOCK CONSTRAINTS
# ================================================================

new_option_method = '''    def _add_grade10_option_block_constraints(
        self,
        model: cp_model.CpModel,
        variables: list[AssignmentVariable],
        problem: SchedulingProblem,
    ) -> None:
        """
        Ensure Grade 10 alternatives share physical block slots.

        At a given group/day/period, at most one subject from an
        option block may occupy the physical slot.
        """
        by_location: dict[
            tuple[UUID, object, str, object],
            list[AssignmentVariable],
        ] = {}

        for variable in variables:
            if not _is_grade10_group(
                problem,
                variable.instructional_group_id,
            ):
                continue

            subject_code = getattr(variable, "subject_code", None)

            if subject_code not in GRADE10_PARALLEL_SUBJECT_TO_BLOCK:
                continue

            block = get_grade10_parallel_block_for_subject(subject_code)

            slot = problem.slot_by_id.get(variable.slot_id)

            if slot is None:
                continue

            key = (
                variable.instructional_group_id,
                slot.day,
                block.code,
                variable.period_id,
            )

            by_location.setdefault(key, []).append(variable)

        for location_variables in by_location.values():
            model.add_at_most_one(
                variable.variable
                for variable in location_variables
            )
'''

pattern = re.compile(
    r"    def _add_grade10_option_block_constraints\(.*?(?=\n    def _add_simultaneous_subject_constraints\()",
    re.DOTALL,
)

match = pattern.search(text)

if not match:
    raise RuntimeError(
        "Could not locate _add_grade10_option_block_constraints()"
    )

text = (
    text[:match.start()]
    + new_option_method
    + "\n"
    + text[match.end():]
)

path.write_text(text, encoding="utf-8")

print("MODEL REWRITE COMPLETE")