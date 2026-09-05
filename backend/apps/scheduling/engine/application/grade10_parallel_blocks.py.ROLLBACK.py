"""
SMARTTIMETABLE PRO
AUTHORITATIVE GRADE 10 PARALLEL ELECTIVE BLOCKS

This module defines the business meaning of Grade 10 elective blocks.

IMPORTANT:
- Each subject remains an independent LessonRequirement.
- Subjects in one block share the same timetable slots.
- A 5/week block means FIVE shared timetable slots.
- It does NOT mean 15 independent slots for a three-subject block.
- Teacher and room identity remain independent for every subject.
- French may remain inactive until an active teacher is assigned.
- This module contains business configuration only.
- It does not create database records.
- It does not modify timetable entries.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Grade10ParallelBlock:
    code: str
    subject_codes: tuple[str, ...]
    weekly_shared_slots: int = 5


GRADE10_PARALLEL_BLOCKS: Final[tuple[Grade10ParallelBlock, ...]] = (
    Grade10ParallelBlock(
        code="OPTION_1",
        subject_codes=("BIO", "MUS", "FRE"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_2",
        subject_codes=("CHEM", "PHY", "LIT"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_3",
        subject_codes=("GEO", "HIS", "CS"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_4",
        subject_codes=("BUS", "AGR"),
        weekly_shared_slots=5,
    ),
)


GRADE10_PARALLEL_BLOCK_BY_CODE: Final = {
    block.code: block
    for block in GRADE10_PARALLEL_BLOCKS
}


GRADE10_PARALLEL_SUBJECT_TO_BLOCK: Final = {
    subject_code: block.code
    for block in GRADE10_PARALLEL_BLOCKS
    for subject_code in block.subject_codes
}


def get_grade10_parallel_block(block_code: str) -> Grade10ParallelBlock:
    """Return the authoritative block definition."""
    try:
        return GRADE10_PARALLEL_BLOCK_BY_CODE[block_code]
    except KeyError as exc:
        raise ValueError(
            f"Unknown Grade 10 parallel block: {block_code}"
        ) from exc


def get_grade10_parallel_block_for_subject(
    subject_code: str,
) -> Grade10ParallelBlock:
    """Return the authoritative block containing a subject."""
    try:
        block_code = GRADE10_PARALLEL_SUBJECT_TO_BLOCK[subject_code]
    except KeyError as exc:
        raise ValueError(
            f"Subject {subject_code} is not a Grade 10 parallel elective."
        ) from exc

    return get_grade10_parallel_block(block_code)


def validate_grade10_parallel_blocks() -> None:
    """
    Validate the immutable Grade 10 block contract.

    This validates configuration only. It does not inspect or modify
    database state.
    """
    expected = {
        "OPTION_1": ("BIO", "MUS", "FRE"),
        "OPTION_2": ("CHEM", "PHY", "LIT"),
        "OPTION_3": ("GEO", "HIS", "CS"),
        "OPTION_4": ("BUS", "AGR"),
    }

    if len(GRADE10_PARALLEL_BLOCKS) != 4:
        raise ValueError(
            "Grade 10 must contain exactly four parallel elective blocks."
        )

    seen_subjects: set[str] = set()

    for block in GRADE10_PARALLEL_BLOCKS:
        expected_subjects = expected.get(block.code)

        if expected_subjects is None:
            raise ValueError(
                f"Unexpected Grade 10 parallel block: {block.code}"
            )

        if block.subject_codes != expected_subjects:
            raise ValueError(
                f"{block.code} subjects are incorrect: "
                f"{block.subject_codes!r}"
            )

        if block.weekly_shared_slots != 5:
            raise ValueError(
                f"{block.code} must have exactly 5 shared slots/week."
            )

        overlap = seen_subjects.intersection(block.subject_codes)

        if overlap:
            raise ValueError(
                "A Grade 10 elective subject belongs to multiple blocks: "
                f"{sorted(overlap)}"
            )

        seen_subjects.update(block.subject_codes)

    expected_subject_count = sum(
        len(subjects)
        for subjects in expected.values()
    )

    if len(seen_subjects) != expected_subject_count:
        raise ValueError(
            "Grade 10 parallel-block subject coverage is inconsistent."
        )


def grade10_parallel_slot_count() -> int:
    """Return the number of shared timetable slots contributed by blocks."""
    validate_grade10_parallel_blocks()

    return sum(
        block.weekly_shared_slots
        for block in GRADE10_PARALLEL_BLOCKS
    )


def grade10_parallel_subject_count() -> int:
    """Return the number of independently represented elective subjects."""
    validate_grade10_parallel_blocks()

    return len(GRADE10_PARALLEL_SUBJECT_TO_BLOCK)


def describe_grade10_parallel_blocks() -> list[str]:
    """Return human-readable authoritative block descriptions."""
    validate_grade10_parallel_blocks()

    return [
        (
            f"{block.code}: "
            f"{' / '.join(block.subject_codes)} = "
            f"{block.weekly_shared_slots} shared timetable slots/week"
        )
        for block in GRADE10_PARALLEL_BLOCKS
    ]
