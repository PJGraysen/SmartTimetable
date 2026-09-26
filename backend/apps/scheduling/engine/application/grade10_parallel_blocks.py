"""Canonical Senior School parallel elective and timetable contract."""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================================
# SENIOR SCHOOL STRUCTURE
# ============================================================================

SENIOR_SCHOOL_WEEKLY_PERIODS = 49

SENIOR_SCHOOL_GROUP_CODES = ("4E", "4W")

SENIOR_SCHOOL_PARALLEL_GROUPS = (
    ("3E", "3W"),
    ("4E", "4W"),
)


@dataclass(frozen=True, slots=True)
class SeniorSchoolBlock:
    """Subjects that occupy synchronized physical timetable slots."""

    code: str
    subject_codes: tuple[str, ...]
    weekly_shared_slots: int
    instructional_group_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SeniorSchoolScheduledLesson:
    """A fixed business-contract lesson position."""

    subject_code: str
    day: str
    lesson_number: int


@dataclass(frozen=True, slots=True)
class SeniorSchoolClassContract:
    """Authoritative weekly contract for one senior-school stream."""

    group_code: str
    standalone_core: tuple[SeniorSchoolScheduledLesson, ...]
    practical_support: tuple[SeniorSchoolScheduledLesson, ...]


# ============================================================================
# GRADE 10 CONTRACT
# ============================================================================

GRADE10_INSTRUCTIONAL_GROUP_CODES = ("10E", "10W")


@dataclass(frozen=True, slots=True)
class Grade10ParallelBlock:
    """Subjects that share one physical timetable slot each week."""

    code: str
    subject_codes: tuple[str, ...]
    weekly_shared_slots: int


GRADE10_PARALLEL_BLOCKS: tuple[Grade10ParallelBlock, ...] = (
    Grade10ParallelBlock(
        code="OPTION_1",
        subject_codes=("COMP", "CHEM"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_2",
        subject_codes=("BIO", "GEO", "HIS"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_3",
        subject_codes=("PHY", "LIT", "MUSD"),
        weekly_shared_slots=5,
    ),
    Grade10ParallelBlock(
        code="OPTION_4",
        subject_codes=("AGR", "BUS"),
        weekly_shared_slots=5,
    ),
)


GRADE10_PARALLEL_SUBJECT_TO_BLOCK = {
    subject_code: block.code
    for block in GRADE10_PARALLEL_BLOCKS
    for subject_code in block.subject_codes
}

GRADE10_BLOCKS = {
    block.code: frozenset(block.subject_codes)
    for block in GRADE10_PARALLEL_BLOCKS
}

GRADE10_BLOCK_LEARNER_GROUPS = {
    block.code: GRADE10_INSTRUCTIONAL_GROUP_CODES
    for block in GRADE10_PARALLEL_BLOCKS
}

_BLOCK_BY_CODE = {
    block.code: block
    for block in GRADE10_PARALLEL_BLOCKS
}


# ============================================================================
# SENIOR SCHOOL ELECTIVE BLOCKS
# ============================================================================

SENIOR_SCHOOL_GEO_HIS_BLOCK = SeniorSchoolBlock(
    code="GEO_HIS",
    subject_codes=("GEO", "HIS"),
    weekly_shared_slots=5,
    instructional_group_codes=("4E", "4W"),
)

SENIOR_SCHOOL_AGR_BST_BLOCK = SeniorSchoolBlock(
    code="AGR_BST",
    subject_codes=("AGR", "BUS"),
    weekly_shared_slots=4,
    instructional_group_codes=("4E", "4W"),
)

# Legacy names — mapped to nearest contract equivalent for import compatibility.
SENIOR_SCHOOL_SCIENCE_BLOCK = SENIOR_SCHOOL_GEO_HIS_BLOCK
SENIOR_SCHOOL_HUMANITIES_BLOCK = SENIOR_SCHOOL_GEO_HIS_BLOCK
SENIOR_SCHOOL_RELIGIOUS_EDUCATION_BLOCK = SENIOR_SCHOOL_AGR_BST_BLOCK
SENIOR_SCHOOL_TECHNICALS_APPLIED_BLOCK = SENIOR_SCHOOL_AGR_BST_BLOCK

SENIOR_SCHOOL_ELECTIVE_BLOCKS: tuple[SeniorSchoolBlock, ...] = (
    SENIOR_SCHOOL_GEO_HIS_BLOCK,
    SENIOR_SCHOOL_AGR_BST_BLOCK,
)

SENIOR_SCHOOL_PARALLEL_BLOCKS = SENIOR_SCHOOL_ELECTIVE_BLOCKS

SENIOR_SCHOOL_SUBJECT_TO_BLOCK = {
    subject_code: block.code
    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
    for subject_code in block.subject_codes
}

SENIOR_SCHOOL_BLOCKS = {
    block.code: frozenset(block.subject_codes)
    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
}

SENIOR_SCHOOL_BLOCK_LEARNER_GROUPS = {
    block.code: block.instructional_group_codes
    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
}

SENIOR_SCHOOL_BLOCK_BY_CODE = {
    block.code: block
    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
}


# ============================================================================
# SENIOR SCHOOL ELECTIVE SYNCHRONIZATION
# ============================================================================

SENIOR_SCHOOL_SYNCHRONIZED_STREAM_PAIRS = (("4E", "4W"),)

SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES = tuple(
    block.code
    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
)


# ============================================================================
# FIXED FORM 3 ELECTIVE BLOCK POSITIONS
# ============================================================================

FORM3_SCIENCE_SLOTS = (
    ("MON", 8),
    ("MON", 9),
    ("TUE", 3),
    ("TUE", 6),
    ("WED", 4),
    ("WED", 9),
    ("THU", 8),
    ("THU", 9),
    ("FRI", 1),
    ("FRI", 9),
)

FORM3_HUMANITIES_SLOTS = (
    ("MON", 6),
    ("TUE", 7),
    ("WED", 2),
    ("FRI", 10),
)

FORM3_RELIGIOUS_EDUCATION_SLOTS = (
    ("MON", 7),
    ("WED", 8),
    ("THU", 7),
    ("FRI", 4),
)

FORM3_TECHNICALS_APPLIED_SLOTS = (
    ("TUE", 9),
    ("WED", 3),
    ("THU", 6),
    ("FRI", 2),
)


# ============================================================================
# FIXED FORM 4 ELECTIVE BLOCK POSITIONS
# ============================================================================

FORM4_SCIENCE_SLOTS = (
    ("MON", 8),
    ("MON", 9),
    ("TUE", 8),
    ("TUE", 9),
    ("WED", 5),
    ("WED", 10),
    ("THU", 1),
    ("THU", 9),
    ("FRI", 9),
    ("FRI", 10),
)

FORM4_HUMANITIES_SLOTS = (
    ("MON", 6),
    ("TUE", 7),
    ("WED", 7),
    ("FRI", 9),
)

FORM4_RELIGIOUS_EDUCATION_SLOTS = (
    ("MON", 7),
    ("TUE", 4),
    ("WED", 1),
    ("THU", 8),
)

FORM4_TECHNICALS_APPLIED_SLOTS = (
    ("MON", 2),
    ("TUE", 2),
    ("WED", 6),
    ("THU", 10),
)


# Teaching period numbers (from Period table):
#   1,2,3,4 = morning before break
#   6,7,8   = morning after break
#   10,11,12 = afternoon
# Excluded: 5 (Break), 9 (Lunch), 13/14/15 (non-teaching)
# MON period 1 excluded (Assembly).
# All slots sit in the morning to avoid free-afternoon conflicts.
SENIOR_SCHOOL_BLOCK_SLOTS = {
    "4E": {
        "GEO_HIS": (("MON", 2), ("TUE", 2), ("WED", 2), ("THU", 2), ("FRI", 2)),
        "AGR_BST": (("MON", 3), ("TUE", 3), ("WED", 3), ("THU", 3)),
    },
    "4W": {
        "GEO_HIS": (("MON", 2), ("TUE", 2), ("WED", 2), ("THU", 2), ("FRI", 2)),
        "AGR_BST": (("MON", 3), ("TUE", 3), ("WED", 3), ("THU", 3)),
    },
}


# ============================================================================
# FORM 3E CONTRACT
# ============================================================================

FORM3E_STANDALONE_CORE = (
    SeniorSchoolScheduledLesson("MAT", "MON", 2),
    SeniorSchoolScheduledLesson("MAT", "TUE", 1),
    SeniorSchoolScheduledLesson("MAT", "WED", 4),
    SeniorSchoolScheduledLesson("MAT", "THU", 1),
    SeniorSchoolScheduledLesson("MAT", "FRI", 7),
    SeniorSchoolScheduledLesson("ENG", "MON", 4),
    SeniorSchoolScheduledLesson("ENG", "TUE", 5),
    SeniorSchoolScheduledLesson("ENG", "WED", 7),
    SeniorSchoolScheduledLesson("ENG", "THU", 4),
    SeniorSchoolScheduledLesson("ENG", "FRI", 10),
    SeniorSchoolScheduledLesson("KIS", "MON", 3),
    SeniorSchoolScheduledLesson("KIS", "TUE", 8),
    SeniorSchoolScheduledLesson("KIS", "WED", 3),
    SeniorSchoolScheduledLesson("KIS", "THU", 1),
    SeniorSchoolScheduledLesson("KIS", "FRI", 8),
)

FORM3E_PRACTICAL_SUPPORT = (
    SeniorSchoolScheduledLesson("CHEM", "MON", 1),
    SeniorSchoolScheduledLesson("CHEM", "THU", 2),
    SeniorSchoolScheduledLesson("BIO", "TUE", 4),
    SeniorSchoolScheduledLesson("BIO", "THU", 3),
    SeniorSchoolScheduledLesson("PHY", "WED", 7),
    SeniorSchoolScheduledLesson("PHY", "THU", 7),
    SeniorSchoolScheduledLesson("CSL", "WED", 6),
    SeniorSchoolScheduledLesson("CSL", "FRI", 10),
    SeniorSchoolScheduledLesson("PPI", "MON", 4),
)


# ============================================================================
# FORM 3W CONTRACT
# ============================================================================

FORM3W_STANDALONE_CORE = (
    SeniorSchoolScheduledLesson("MAT", "MON", 3),
    SeniorSchoolScheduledLesson("MAT", "TUE", 7),
    SeniorSchoolScheduledLesson("MAT", "WED", 1),
    SeniorSchoolScheduledLesson("MAT", "THU", 2),
    SeniorSchoolScheduledLesson("MAT", "FRI", 8),
    SeniorSchoolScheduledLesson("ENG", "MON", 2),
    SeniorSchoolScheduledLesson("ENG", "TUE", 4),
    SeniorSchoolScheduledLesson("ENG", "WED", 3),
    SeniorSchoolScheduledLesson("ENG", "THU", 5),
    SeniorSchoolScheduledLesson("ENG", "FRI", 1),
    SeniorSchoolScheduledLesson("KIS", "MON", 8),
    SeniorSchoolScheduledLesson("KIS", "TUE", 8),
    SeniorSchoolScheduledLesson("KIS", "WED", 2),
    SeniorSchoolScheduledLesson("KIS", "THU", 8),
    SeniorSchoolScheduledLesson("KIS", "FRI", 9),
)

FORM3W_PRACTICAL_SUPPORT = (
    SeniorSchoolScheduledLesson("BIO", "TUE", 4),
    SeniorSchoolScheduledLesson("BIO", "THU", 3),
    SeniorSchoolScheduledLesson("CS", "WED", 6),
    SeniorSchoolScheduledLesson("CS", "FRI", 9),
    SeniorSchoolScheduledLesson("PE", "WED", 7),
)


# ============================================================================
# FORM 4E CONTRACT
# ============================================================================

FORM4E_STANDALONE_CORE = (
    SeniorSchoolScheduledLesson("MAT", "MON", 2),
    SeniorSchoolScheduledLesson("MAT", "TUE", 4),
    SeniorSchoolScheduledLesson("MAT", "WED", 1),
    SeniorSchoolScheduledLesson("MAT", "THU", 7),
    SeniorSchoolScheduledLesson("MAT", "FRI", 8),
    SeniorSchoolScheduledLesson("MAT", "MON", 9),
    SeniorSchoolScheduledLesson("ENG", "MON", 5),
    SeniorSchoolScheduledLesson("ENG", "TUE", 2),
    SeniorSchoolScheduledLesson("ENG", "WED", 4),
    SeniorSchoolScheduledLesson("ENG", "THU", 5),
    SeniorSchoolScheduledLesson("ENG", "FRI", 10),
    SeniorSchoolScheduledLesson("KIS", "MON", 1),
    SeniorSchoolScheduledLesson("KIS", "TUE", 3),
    SeniorSchoolScheduledLesson("KIS", "WED", 8),
    SeniorSchoolScheduledLesson("KIS", "THU", 5),
    SeniorSchoolScheduledLesson("KIS", "FRI", 7),
)

FORM4E_PRACTICAL_SUPPORT = (
    SeniorSchoolScheduledLesson("CHEM", "TUE", 1),
    SeniorSchoolScheduledLesson("CHEM", "THU", 4),
    SeniorSchoolScheduledLesson("CHEM", "FRI", 1),
    SeniorSchoolScheduledLesson("CHEM", "MON", 6),
    SeniorSchoolScheduledLesson("CHEM", "WED", 5),
    SeniorSchoolScheduledLesson("PHY", "MON", 3),
    SeniorSchoolScheduledLesson("PHY", "THU", 6),
    SeniorSchoolScheduledLesson("PHY", "TUE", 8),
    SeniorSchoolScheduledLesson("PHY", "FRI", 9),
    SeniorSchoolScheduledLesson("BIO", "WED", 2),
    SeniorSchoolScheduledLesson("BIO", "WED", 8),
    SeniorSchoolScheduledLesson("BIO", "THU", 9),
    SeniorSchoolScheduledLesson("BIO", "FRI", 4),
    SeniorSchoolScheduledLesson("CRE", "MON", 7),
    SeniorSchoolScheduledLesson("CRE", "TUE", 6),
    SeniorSchoolScheduledLesson("CRE", "FRI", 5),
)


# ============================================================================
# FORM 4W CONTRACT
# ============================================================================

FORM4W_STANDALONE_CORE = (
    SeniorSchoolScheduledLesson("MAT", "MON", 2),
    SeniorSchoolScheduledLesson("MAT", "TUE", 1),
    SeniorSchoolScheduledLesson("MAT", "WED", 4),
    SeniorSchoolScheduledLesson("MAT", "THU", 7),
    SeniorSchoolScheduledLesson("MAT", "FRI", 1),
    SeniorSchoolScheduledLesson("MAT", "MON", 10),
    SeniorSchoolScheduledLesson("ENG", "MON", 5),
    SeniorSchoolScheduledLesson("ENG", "TUE", 1),
    SeniorSchoolScheduledLesson("ENG", "WED", 3),
    SeniorSchoolScheduledLesson("ENG", "THU", 6),
    SeniorSchoolScheduledLesson("ENG", "FRI", 8),
    SeniorSchoolScheduledLesson("KIS", "MON", 1),
    SeniorSchoolScheduledLesson("KIS", "TUE", 8),
    SeniorSchoolScheduledLesson("KIS", "WED", 2),
    SeniorSchoolScheduledLesson("KIS", "THU", 6),
    SeniorSchoolScheduledLesson("KIS", "FRI", 7),
)

FORM4W_PRACTICAL_SUPPORT = (
    SeniorSchoolScheduledLesson("CHEM", "TUE", 2),
    SeniorSchoolScheduledLesson("CHEM", "WED", 7),
    SeniorSchoolScheduledLesson("CHEM", "THU", 3),
    SeniorSchoolScheduledLesson("CHEM", "FRI", 6),
    SeniorSchoolScheduledLesson("CHEM", "MON", 8),
    SeniorSchoolScheduledLesson("PHY", "MON", 5),
    SeniorSchoolScheduledLesson("PHY", "TUE", 10),
    SeniorSchoolScheduledLesson("PHY", "WED", 5),
    SeniorSchoolScheduledLesson("PHY", "FRI", 2),
    SeniorSchoolScheduledLesson("BIO", "WED", 3),
    SeniorSchoolScheduledLesson("BIO", "THU", 1),
    SeniorSchoolScheduledLesson("BIO", "THU", 5),
    SeniorSchoolScheduledLesson("BIO", "FRI", 9),
    SeniorSchoolScheduledLesson("CRE", "MON", 7),
    SeniorSchoolScheduledLesson("CRE", "TUE", 9),
    SeniorSchoolScheduledLesson("CRE", "FRI", 4),
)


SENIOR_SCHOOL_CLASS_CONTRACTS = {
    "4E": SeniorSchoolClassContract(
        group_code="4E",
        standalone_core=FORM4E_STANDALONE_CORE,
        practical_support=FORM4E_PRACTICAL_SUPPORT,
    ),
    "4W": SeniorSchoolClassContract(
        group_code="4W",
        standalone_core=FORM4W_STANDALONE_CORE,
        practical_support=FORM4W_PRACTICAL_SUPPORT,
    ),
}


# ============================================================================
# NORMALIZATION / LOOKUP
# ============================================================================

def _normalized_subject_code(value: object | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().upper()
    return normalized or None


def _normalized_group_code(value: object | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().upper().replace("-", " ")
    return normalized or None


def get_block_for_subject(subject_code: object | None) -> str | None:
    """Return the Grade 10 block for a subject, if configured."""
    normalized = _normalized_subject_code(subject_code)

    if normalized is None:
        return None

    return GRADE10_PARALLEL_SUBJECT_TO_BLOCK.get(normalized)


def get_grade10_parallel_block(
    block_code: object | None,
) -> Grade10ParallelBlock | None:
    """Return a configured Grade 10 parallel block."""
    if block_code is None:
        return None

    return _BLOCK_BY_CODE.get(str(block_code).strip().upper())


def get_grade10_parallel_block_for_subject(
    subject_code: object | None,
) -> Grade10ParallelBlock | None:
    """Return the Grade 10 block containing a subject."""
    block_code = get_block_for_subject(subject_code)
    return get_grade10_parallel_block(block_code)


def get_subjects_in_block(block_name: object | None) -> frozenset[str]:
    """Return Grade 10 subjects in a block."""
    if block_name is None:
        return frozenset()

    return GRADE10_BLOCKS.get(
        str(block_name).strip().upper(),
        frozenset(),
    )


def get_groups_in_block(block_name: object | None) -> tuple[str, ...]:
    """Return Grade 10 groups governed by a block."""
    if block_name is None:
        return ()

    return GRADE10_BLOCK_LEARNER_GROUPS.get(
        str(block_name).strip().upper(),
        (),
    )


def get_senior_school_block_for_subject(
    subject_code: object | None,
) -> SeniorSchoolBlock | None:
    """Return the senior-school elective block containing a subject."""
    normalized = _normalized_subject_code(subject_code)

    if normalized is None:
        return None

    block_code = SENIOR_SCHOOL_SUBJECT_TO_BLOCK.get(normalized)

    if block_code is None:
        return None

    return SENIOR_SCHOOL_BLOCK_BY_CODE[block_code]


# ------------------------------------------------------------------
# Per-generation block-slot rotation (SmartTimetable Pro)
# ------------------------------------------------------------------
# The contract pins Form 4 GEO_HIS to period 2 and AGR_BST to period 3
# on each teaching day. Rotation preserves the day pattern but shifts
# the period index by a per-generation offset, so successive runs get
# different physical placements. 4E and 4W always rotate together.

_BLOCK_ROTATION_OFFSET = 0

# Teaching periods available for block placement (Period 1 reserved for
# Monday assembly; enforced elsewhere).
_BLOCK_ROTATION_POOL = (2, 3, 4, 5, 6, 7)  # morning slots only


def set_block_rotation_offset(offset: int) -> None:
    global _BLOCK_ROTATION_OFFSET
    n = len(_BLOCK_ROTATION_POOL)
    _BLOCK_ROTATION_OFFSET = int(offset) % n


def get_block_rotation_offset() -> int:
    return _BLOCK_ROTATION_OFFSET


def _rotate_period(period: int, offset: int) -> int:
    if offset == 0:
        return period
    try:
        idx = _BLOCK_ROTATION_POOL.index(int(period))
    except (ValueError, TypeError):
        return period
    return _BLOCK_ROTATION_POOL[(idx + offset) % len(_BLOCK_ROTATION_POOL)]


def _shift_period(period: int, offset: int) -> int:
    if offset == 0:
        return period
    try:
        idx = _BLOCK_ROTATION_POOL.index(int(period))
    except (ValueError, TypeError):
        return period
    return _BLOCK_ROTATION_POOL[(idx + offset) % len(_BLOCK_ROTATION_POOL)]


def get_senior_school_block_slots(
    group_code: object | None,
    block_code: object | None,
) -> tuple[tuple[str, int], ...]:
    """Return synchronized slots for a stream/block.

    Per-day rotation: each teaching day shifts by a different offset,
    so the block moves to a different period each day AND each
    generation. Combined with the generation offset, this gives
    much stronger variation than a straight P2<->P3 swap.
    """
    normalized_group = _normalized_group_code(group_code)
    if normalized_group is None or block_code is None:
        return ()
    normalized_block = str(block_code).strip().upper()
    base = SENIOR_SCHOOL_BLOCK_SLOTS.get(normalized_group, {}).get(normalized_block, ())
    if not base:
        return ()

    offset = _BLOCK_ROTATION_OFFSET
    pool_size = len(_BLOCK_ROTATION_POOL)
    return tuple(
        (day, _shift_period(period, (offset + day_idx) % pool_size))
        for day_idx, (day, period) in enumerate(base)
    )


def get_senior_school_class_contract(
    group_code: object | None,
) -> SeniorSchoolClassContract | None:
    """Return the authoritative contract for a senior-school stream."""
    normalized = _normalized_group_code(group_code)

    if normalized is None:
        return None

    return SENIOR_SCHOOL_CLASS_CONTRACTS.get(normalized)


def is_senior_school_instructional_group(
    group: object | None,
) -> bool:
    """Return whether a group is Form 3 or Form 4 East/West."""
    if isinstance(group, str):
        values = (group,)
    elif group is None:
        values = ()
    else:
        values = (
            getattr(group, "code", None),
            getattr(group, "name", None),
        )

    normalized_values = {
        _normalized_group_code(value)
        for value in values
    }

    return bool(
        normalized_values
        & {
            "3E",
            "3W",
            "4E",
            "4W",
            "FORM 3E",
            "FORM 3W",
            "FORM 4E",
            "FORM 4W",
        }
    )


def is_subject_in_senior_school_blocks(
    subject_code: object | None,
) -> bool:
    """Return whether a subject belongs to a senior-school block."""
    return get_senior_school_block_for_subject(subject_code) is not None


def are_senior_school_subjects_in_same_block(
    subject_code_1: object | None,
    subject_code_2: object | None,
) -> bool:
    """Return whether two senior-school subjects share a block."""
    block_1 = get_senior_school_block_for_subject(subject_code_1)
    block_2 = get_senior_school_block_for_subject(subject_code_2)

    return (
        block_1 is not None
        and block_2 is not None
        and block_1.code == block_2.code
    )


def is_subject_in_grade10_blocks(subject_code: object | None) -> bool:
    """Return whether a subject belongs to a Grade 10 block."""
    return get_block_for_subject(subject_code) is not None


def are_subjects_in_same_block(
    subject_code_1: object | None,
    subject_code_2: object | None,
) -> bool:
    """Return whether two Grade 10 subjects share a block."""
    block_1 = get_block_for_subject(subject_code_1)
    block_2 = get_block_for_subject(subject_code_2)

    return block_1 is not None and block_1 == block_2


def is_grade10_instructional_group(
    group: object | None,
) -> bool:
    """
    Return whether a group uses the Grade 10 option-block machinery.

    Grade 10 and Grade 11 share the same elective-block contract:
        Option 1 = COMP / CHEM
        Option 2 = BIO / GEO / HIS
        Option 3 = PHY / LIT / MUSD
        Option 4 = AGR / BUS
    ICT remains STANDALONE.
    """
    if isinstance(group, str):
        values = (group,)
    elif group is None:
        values = ()
    else:
        values = (
            getattr(group, "code", None),
            getattr(group, "name", None),
        )

    return any(
        _normalized_group_code(value)
        in {
            "10E",
            "10W",
            "GRADE 10E",
            "GRADE 10W",
            "11E",
            "11W",
            "GRADE 11E",
            "GRADE 11W",
        }
        for value in values
    )


# ============================================================================
# VALIDATION
# ============================================================================

def validate_grade10_parallel_blocks() -> None:
    """Validate the static Grade 10 parallel-block contract."""
    block_codes: set[str] = set()
    subject_codes: set[str] = set()

    for block in GRADE10_PARALLEL_BLOCKS:
        if not block.code:
            raise ValueError(
                "Grade 10 parallel blocks require a code."
            )

        if block.code in block_codes:
            raise ValueError(
                f"Duplicate Grade 10 parallel block code: {block.code}."
            )

        if block.weekly_shared_slots <= 0:
            raise ValueError(
                f"Grade 10 block {block.code} must have a positive "
                "weekly shared-slot count."
            )

        if len(block.subject_codes) < 2:
            raise ValueError(
                f"Grade 10 block {block.code} must contain at least two "
                "subjects."
            )

        for subject_code in block.subject_codes:
            normalized = _normalized_subject_code(subject_code)

            if normalized is None:
                raise ValueError(
                    f"Grade 10 block {block.code} contains an empty "
                    "subject code."
                )

            if normalized in subject_codes:
                raise ValueError(
                    "A Grade 10 parallel subject may belong to only one "
                    f"block: {normalized}."
                )

            subject_codes.add(normalized)

        block_codes.add(block.code)


def validate_senior_school_blocks() -> None:
    """Validate the senior-school elective-block contract."""
    block_codes: set[str] = set()
    subject_codes: set[str] = set()

    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS:
        if not block.code:
            raise ValueError(
                "Senior-school blocks require a code."
            )

        if block.code in block_codes:
            raise ValueError(
                f"Duplicate senior-school block code: {block.code}."
            )

        if block.weekly_shared_slots <= 0:
            raise ValueError(
                f"Senior-school block {block.code} must have a positive "
                "weekly shared-slot count."
            )

        if len(block.subject_codes) < 2:
            raise ValueError(
                f"Senior-school block {block.code} must contain at least "
                "two subjects."
            )

        if not block.instructional_group_codes:
            raise ValueError(
                f"Senior-school block {block.code} has no instructional "
                "groups."
            )

        for subject_code in block.subject_codes:
            normalized = _normalized_subject_code(subject_code)

            if normalized is None:
                raise ValueError(
                    f"Senior-school block {block.code} contains an empty "
                    "subject code."
                )

            if normalized in subject_codes:
                raise ValueError(
                    "A senior-school elective subject may belong to only "
                    f"one block: {normalized}."
                )

            subject_codes.add(normalized)

        block_codes.add(block.code)


def validate_senior_school_stream_synchronization() -> None:
    """Ensure paired East/West streams use identical supplied block positions."""
    for east, west in SENIOR_SCHOOL_SYNCHRONIZED_STREAM_PAIRS:
        for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS:
            east_slots = get_senior_school_block_slots(
                east,
                block.code,
            )
            west_slots = get_senior_school_block_slots(
                west,
                block.code,
            )

            if not east_slots:
                raise ValueError(
                    f"Senior-school block {block.code} has no supplied "
                    f"slot positions for {east}."
                )

            if not west_slots:
                raise ValueError(
                    f"Senior-school block {block.code} has no supplied "
                    f"slot positions for {west}."
                )

            if east_slots != west_slots:
                raise ValueError(
                    f"Senior-school synchronization violation: "
                    f"{east}/{west} block {block.code} does not use "
                    "identical day/lesson slots."
                )

            if len(set(east_slots)) != len(east_slots):
                raise ValueError(
                    f"Senior-school block {block.code} contains duplicate "
                    f"day/lesson positions for {east}."
                )

            if len(set(west_slots)) != len(west_slots):
                raise ValueError(
                    f"Senior-school block {block.code} contains duplicate "
                    f"day/lesson positions for {west}."
                )


def senior_school_contract_warnings() -> tuple[str, ...]:
    """
    Return explicit warnings where the supplied business contract contains
    a lesson-count/position-count discrepancy.

    The supplied contract is preserved exactly. No interpretation is made
    here about whether a listed range represents one lesson or two physical
    periods.
    """
    warnings: list[str] = []

    for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS:
        expected = block.weekly_shared_slots

        for group_code in SENIOR_SCHOOL_GROUP_CODES:
            supplied = len(
                get_senior_school_block_slots(
                    group_code,
                    block.code,
                )
            )

            if supplied != expected:
                warnings.append(
                    f"{group_code} {block.code}: contract declares "
                    f"{expected} weekly shared lessons but supplies "
                    f"{supplied} day/lesson positions."
                )

    return tuple(warnings)


def validate_senior_school_contract() -> None:
    """Validate the complete static senior-school contract."""
    validate_senior_school_blocks()
    validate_senior_school_stream_synchronization()

    if SENIOR_SCHOOL_WEEKLY_PERIODS != 49:
        raise ValueError(
            "Senior School must contain exactly 49 weekly periods."
        )

    expected_groups = {"4E", "4W"}

    if set(SENIOR_SCHOOL_CLASS_CONTRACTS) != expected_groups:
        raise ValueError(
            "Senior School class contracts must cover exactly "
            "4E and 4W."
        )

    for group_code, contract in SENIOR_SCHOOL_CLASS_CONTRACTS.items():
        if contract.group_code != group_code:
            raise ValueError(
                f"Senior-school contract key mismatch for {group_code}."
            )

        if len(contract.standalone_core) != 16:
            raise ValueError(
                f"{group_code} must have exactly 16 standalone core "
                "lessons."
            )

    validate_grade10_parallel_blocks()


# ============================================================================
# DISPLAY / COUNTS
# ============================================================================

def describe_grade10_parallel_blocks() -> tuple[str, ...]:
    """Return display-ready Grade 10 block descriptions."""
    return tuple(
        f"{block.code}: {' / '.join(block.subject_codes)} = "
        f"{block.weekly_shared_slots} shared slots/week"
        for block in GRADE10_PARALLEL_BLOCKS
    )


def describe_senior_school_blocks() -> tuple[str, ...]:
    """Return display-ready senior-school block descriptions."""
    return tuple(
        f"{block.code}: {' / '.join(block.subject_codes)} = "
        f"{block.weekly_shared_slots} shared slots/week"
        for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
    )


def grade10_parallel_slot_count() -> int:
    """Return weekly Grade 10 physical slots occupied by parallel blocks."""
    return sum(
        block.weekly_shared_slots
        for block in GRADE10_PARALLEL_BLOCKS
    )


def grade10_parallel_subject_count() -> int:
    """Return independently represented Grade 10 block subjects."""
    return len(GRADE10_PARALLEL_SUBJECT_TO_BLOCK)


def senior_school_elective_slot_count() -> int:
    """Return weekly physical slots occupied by senior-school blocks."""
    return sum(
        block.weekly_shared_slots
        for block in SENIOR_SCHOOL_ELECTIVE_BLOCKS
    )


def senior_school_elective_subject_count() -> int:
    """Return independently represented senior-school block subjects."""
    return len(SENIOR_SCHOOL_SUBJECT_TO_BLOCK)


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "FORM3E_PRACTICAL_SUPPORT",
    "FORM3E_STANDALONE_CORE",
    "FORM3W_PRACTICAL_SUPPORT",
    "FORM3W_STANDALONE_CORE",
    "FORM4E_PRACTICAL_SUPPORT",
    "FORM4E_STANDALONE_CORE",
    "FORM4W_PRACTICAL_SUPPORT",
    "FORM4W_STANDALONE_CORE",
    "FORM3_HUMANITIES_SLOTS",
    "FORM3_RELIGIOUS_EDUCATION_SLOTS",
    "FORM3_SCIENCE_SLOTS",
    "FORM3_TECHNICALS_APPLIED_SLOTS",
    "FORM4_HUMANITIES_SLOTS",
    "FORM4_RELIGIOUS_EDUCATION_SLOTS",
    "FORM4_SCIENCE_SLOTS",
    "FORM4_TECHNICALS_APPLIED_SLOTS",
    "GRADE10_BLOCK_LEARNER_GROUPS",
    "GRADE10_BLOCKS",
    "GRADE10_INSTRUCTIONAL_GROUP_CODES",
    "GRADE10_PARALLEL_BLOCKS",
    "GRADE10_PARALLEL_SUBJECT_TO_BLOCK",
    "Grade10ParallelBlock",
    "SENIOR_SCHOOL_BLOCK_BY_CODE",
    "SENIOR_SCHOOL_BLOCK_LEARNER_GROUPS",
    "SENIOR_SCHOOL_BLOCK_SLOTS",
    "SENIOR_SCHOOL_BLOCKS",
    "SENIOR_SCHOOL_CLASS_CONTRACTS",
    "SENIOR_SCHOOL_ELECTIVE_BLOCKS",
    "SENIOR_SCHOOL_ELECTIVE_SUBJECT_TO_BLOCK",
    "SENIOR_SCHOOL_GROUP_CODES",
    "SENIOR_SCHOOL_HUMANITIES_BLOCK",
    "SENIOR_SCHOOL_PARALLEL_BLOCKS",
    "SENIOR_SCHOOL_PARALLEL_GROUPS",
    "SENIOR_SCHOOL_RELIGIOUS_EDUCATION_BLOCK",
    "SENIOR_SCHOOL_SCIENCE_BLOCK",
    "SENIOR_SCHOOL_SUBJECT_TO_BLOCK",
    "SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES",
    "SENIOR_SCHOOL_SYNCHRONIZED_STREAM_PAIRS",
    "SENIOR_SCHOOL_TECHNICALS_APPLIED_BLOCK",
    "SENIOR_SCHOOL_WEEKLY_PERIODS",
    "SeniorSchoolBlock",
    "SeniorSchoolClassContract",
    "SeniorSchoolScheduledLesson",
    "are_senior_school_subjects_in_same_block",
    "are_subjects_in_same_block",
    "describe_grade10_parallel_blocks",
    "describe_senior_school_blocks",
    "get_block_for_subject",
    "get_grade10_parallel_block",
    "get_grade10_parallel_block_for_subject",
    "get_groups_in_block",
    "get_senior_school_block_for_subject",
    "get_senior_school_block_slots",
    "get_senior_school_class_contract",
    "get_subjects_in_block",
    "grade10_parallel_slot_count",
    "grade10_parallel_subject_count",
    "is_grade10_instructional_group",
    "is_subject_in_grade10_blocks",
    "is_subject_in_senior_school_blocks",
    "is_senior_school_instructional_group",
    "senior_school_elective_slot_count",
    "senior_school_elective_subject_count",
    "senior_school_contract_warnings",
    "validate_grade10_parallel_blocks",
    "validate_senior_school_blocks",
    "validate_senior_school_contract",
    "validate_senior_school_stream_synchronization",
]
