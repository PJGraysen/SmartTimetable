from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import transaction

from apps.academics.models import InstructionalGroup, LessonRequirement, Subject
from apps.core.models import Term


class CurriculumContractError(ValueError):
    """Raised when a Senior School curriculum contract is invalid."""


@dataclass(frozen=True)
class SubjectContract:
    code: str
    name: str
    lessons_per_week: int
    category: str = "standalone"
    required: bool = True


@dataclass(frozen=True)
class ParallelBlockContract:
    code: str
    label: str
    subject_codes: tuple[str, ...]
    weekly_shared_slots: int

    @property
    def lessons_per_week(self) -> int:
        return self.weekly_shared_slots


@dataclass(frozen=True)
class ActivityContract:
    code: str
    label: str
    weekly_slots: int

    @property
    def lessons_per_week(self) -> int:
        return self.weekly_slots


@dataclass(frozen=True)
class SeniorSchoolClassCurriculumContract:
    code: str
    level: str
    standalone_subjects: tuple[SubjectContract, ...]
    parallel_blocks: tuple[ParallelBlockContract, ...]
    activities: tuple[ActivityContract, ...]
    weekly_total: int

    @property
    def total_weekly_periods(self) -> int:
        return self.weekly_total

    @property
    def block_lessons(self) -> int:
        return sum(
            block.weekly_shared_slots
            for block in self.parallel_blocks
        )

    @property
    def activity_lessons(self) -> int:
        return sum(
            activity.weekly_slots
            for activity in self.activities
        )

    @property
    def standalone_lessons(self) -> int:
        return sum(
            subject.lessons_per_week
            for subject in self.standalone_subjects
        )

    @property
    def total_lessons(self) -> int:
        return (
            self.standalone_lessons
            + self.block_lessons
            + self.activity_lessons
        )


@dataclass(frozen=True)
class SeniorSchoolCurriculumContract:
    level: str
    subjects: tuple[SubjectContract, ...]
    elective_blocks: tuple[ParallelBlockContract, ...]
    weekly_teaching_slots: int

    @property
    def core_subjects(self) -> tuple[SubjectContract, ...]:
        return tuple(
            subject
            for subject in self.subjects
            if subject.category == "core"
        )

    @property
    def parallel_blocks(self) -> tuple[ParallelBlockContract, ...]:
        return self.elective_blocks

    @property
    def core_lessons(self) -> int:
        return sum(
            subject.lessons_per_week
            for subject in self.core_subjects
        )

    @property
    def elective_block_lessons(self) -> int:
        return sum(
            block.weekly_shared_slots
            for block in self.elective_blocks
        )

    @property
    def total_weekly_periods(self) -> int:
        return self.weekly_teaching_slots


# ============================================================================
# GRADE 10 AUTHORITATIVE CONTRACT
# ============================================================================

GRADE10_SUBJECTS = (
    ("ENG", "English", 5, "core", True),
    ("KIS", "Kiswahili", 5, "core", True),
    ("ESS", "Essential Mathematics", 5, "core", True),
    ("CORE", "Core Mathematics", 5, "core", True),
    ("CRE", "Christian Religious Education", 4, "core", True),
    ("PE", "Physical Education", 3, "core", True),
    ("CSL", "Community Service Learning", 3, "core", True),
    ("ICT", "ICT Skills", 2, "core", True),
    ("PRP", "Pastoral/Religious Programme", 1, "core", True),
    ("GST", "Group Study / Life Skills", 1, "core", True),
    ("BIO", "Biology", 5, "elective", False),
    ("MUS", "Music", 5, "elective", False),
    ("FRE", "French", 5, "elective", False),
    ("CHEM", "Chemistry", 5, "elective", False),
    ("PHY", "Physics", 5, "elective", False),
    ("LIT", "Literature in English", 5, "elective", False),
    ("GEO", "Geography", 5, "elective", False),
    ("HIS", "History", 5, "elective", False),
    ("CS", "Computer Science", 5, "elective", False),
    ("BUS", "Business Studies", 5, "elective", False),
    ("AGR", "Agriculture", 5, "elective", False),
)

GRADE10_CORE_SUBJECTS = tuple(
    subject
    for subject in GRADE10_SUBJECTS
    if subject[3] == "core"
)

GRADE10_ELECTIVE_SUBJECTS = tuple(
    subject
    for subject in GRADE10_SUBJECTS
    if subject[3] == "elective"
)

# Authoritative Grade 10 elective block contract.
# MUST match the runtime parallel-block definitions in
# apps.scheduling.engine.application.grade10_parallel_blocks.
# That runtime module is the single source of truth for the solver;
# this tuple mirrors it so materialize produces the LRs the solver
# actually enforces.
GRADE10_ELECTIVE_BLOCKS = (
    ("OPTION_1", "COMP / CHEM", ("COMP", "CHEM")),
    ("OPTION_2", "BIO / GEO / HIS", ("BIO", "GEO", "HIS")),
    ("OPTION_3", "PHY / LIT / MUSD", ("PHY", "LIT", "MUSD")),
    ("OPTION_4", "AGR / BUS", ("AGR", "BUS")),
)

GRADE10_PARALLEL_BLOCKS = tuple(
    ParallelBlockContract(
        code=code,
        label=label,
        subject_codes=subject_codes,
        weekly_shared_slots=5,
    )
    for code, label, subject_codes in GRADE10_ELECTIVE_BLOCKS
)

GRADE10_GROUP_CODES = ("10E", "10W")

TEMPORARILY_INACTIVE_SUBJECTS = {"FRE"}

GRADE10_WEEKLY_TEACHING_SLOTS = 49


# ============================================================================
# FORM 3 / FORM 4 PARALLEL BLOCK CONTRACTS
# ============================================================================

FORM3_PARALLEL_BLOCKS = (
    ParallelBlockContract(
        code="SCIENCE",
        label="Science Elective Block",
        subject_codes=("CHEM", "BIO", "PHY"),
        weekly_shared_slots=5,
    ),
    ParallelBlockContract(
        code="HUMANITIES",
        label="Humanities Elective Block",
        subject_codes=("GEO", "HIS"),
        weekly_shared_slots=4,
    ),
    ParallelBlockContract(
        code="RELIGIOUS_EDUCATION",
        label="Religious Education Block",
        subject_codes=("CRE",),
        weekly_shared_slots=4,
    ),
    ParallelBlockContract(
        code="TECHNICALS_APPLIED",
        label="Technicals Block",
        subject_codes=("AGR", "BUS"),
        weekly_shared_slots=4,
    ),
)

FORM4_PARALLEL_BLOCKS = (
    ParallelBlockContract(
        code="SCIENCE",
        label="Science Elective Block",
        subject_codes=("CHEM", "BIO", "PHY"),
        weekly_shared_slots=5,
    ),
    ParallelBlockContract(
        code="HUMANITIES",
        label="Humanities Elective Block",
        subject_codes=("GEO", "HIS"),
        weekly_shared_slots=4,
    ),
    ParallelBlockContract(
        code="RELIGIOUS_EDUCATION",
        label="Religious Education Block",
        subject_codes=("CRE",),
        weekly_shared_slots=4,
    ),
    ParallelBlockContract(
        code="TECHNICALS_APPLIED",
        label="Technicals Block",
        subject_codes=("AGR", "BUS"),
        weekly_shared_slots=4,
    ),
)


def _subject(
    code: str,
    name: str,
    lessons: int,
) -> SubjectContract:
    return SubjectContract(
        code=code,
        name=name,
        lessons_per_week=lessons,
        category="standalone",
        required=True,
    )


# ============================================================================
# FORM 3 EAST / WEST
# ============================================================================

FORM3E_STANDALONE_SUBJECTS = (
    _subject("MAT", "Mathematics", 5),
    _subject("ENG", "English", 5),
    _subject("KIS", "Kiswahili", 5),
    _subject("CHEM", "Chemistry", 2),
    _subject("BIO", "Biology", 2),
    _subject("PHY", "Physics", 2),
    _subject("PPI", "PPI", 1),
)
FORM3W_STANDALONE_SUBJECTS = (
    _subject("MAT", "Mathematics", 5),
    _subject("ENG", "English", 5),
    _subject("KIS", "Kiswahili", 5),
    _subject("BIO", "Biology", 2),
    _subject("CS", "Computer Studies", 2),
    _subject("PE", "Physical Education", 1),
    _subject("PPI", "Pastoral Programme of Instruction", 1),
)

FORM3E_ACTIVITIES = (
    ActivityContract(
        code="GUIDED_STUDY",
        label="Group Study / Library",
        weekly_slots=10,
    ),
)
FORM3W_ACTIVITIES = (
    ActivityContract(
        code="GUIDED_STUDY",
        label="Group Study / Library",
        weekly_slots=11,
    ),
)


# ============================================================================
# FORM 4 EAST / WEST
# ============================================================================

FORM4E_STANDALONE_SUBJECTS = (
    _subject("MAT", "Mathematics", 5),
    _subject("ENG", "English", 5),
    _subject("KIS", "Kiswahili", 5),
    _subject("CHEM", "Chemistry", 3),
    _subject("BIO", "Biology", 2),
    _subject("PHY", "Physics", 2),
    _subject("PE", "Physical Education", 1),
    _subject("PPI", "Pastoral Programme of Instruction", 1),
)

FORM4W_STANDALONE_SUBJECTS = (
    _subject("MAT", "Mathematics", 5),
    _subject("ENG", "English", 5),
    _subject("KIS", "Kiswahili", 5),
    _subject("BIO", "Biology", 2),
    _subject("PHY", "Physics", 2),
    _subject("CS", "Computer Studies", 2),
    _subject("PE", "Physical Education", 1),
    _subject("PPI", "Pastoral Programme of Instruction", 1),
)

FORM4E_ACTIVITIES = (
    ActivityContract(
        code="GUIDED_STUDY",
        label="Group Study / Revision",
        weekly_slots=8,
    ),
)

FORM4W_ACTIVITIES = (
    ActivityContract(
        code="GUIDED_STUDY",
        label="Group Study / Revision",
        weekly_slots=9,
    ),
)


# ============================================================================
# CLASS-GROUP CONTRACTS
# ============================================================================

SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS = {
    "3E": SeniorSchoolClassCurriculumContract(
        code="3E",
        level="Form 3",
        standalone_subjects=FORM3E_STANDALONE_SUBJECTS,
        parallel_blocks=FORM3_PARALLEL_BLOCKS,
        activities=FORM3E_ACTIVITIES,
        weekly_total=49,
    ),
    "3W": SeniorSchoolClassCurriculumContract(
        code="3W",
        level="Form 3",
        standalone_subjects=FORM3W_STANDALONE_SUBJECTS,
        parallel_blocks=FORM3_PARALLEL_BLOCKS,
        activities=FORM3W_ACTIVITIES,
        weekly_total=49,
    ),
    "4E": SeniorSchoolClassCurriculumContract(
        code="4E",
        level="Form 4",
        standalone_subjects=FORM4E_STANDALONE_SUBJECTS,
        parallel_blocks=FORM4_PARALLEL_BLOCKS,
        activities=FORM4E_ACTIVITIES,
        weekly_total=49,
    ),
    "4W": SeniorSchoolClassCurriculumContract(
        code="4W",
        level="Form 4",
        standalone_subjects=FORM4W_STANDALONE_SUBJECTS,
        parallel_blocks=FORM4_PARALLEL_BLOCKS,
        activities=FORM4W_ACTIVITIES,
        weekly_total=49,
    ),
}


EXPECTED_SENIOR_SCHOOL_GROUP_CODES = (
    "10E",
    "10W",
    "3E",
    "3W",
    "4E",
    "4W",
)


# ============================================================================
# LEVEL NORMALIZATION
# ============================================================================

def normalize_senior_school_level(level: str) -> str:
    normalized = str(level).strip().upper().replace("_", " ")

    aliases = {
        "GRADE 10": "Grade 10",
        "GRADE10": "Grade 10",
        "10": "Grade 10",
        "FORM 3": "Form 3",
        "FORM3": "Form 3",
        "F3": "Form 3",
        "3": "Form 3",
        "FORM 4": "Form 4",
        "FORM4": "Form 4",
        "F4": "Form 4",
        "4": "Form 4",
    }

    try:
        return aliases[normalized]
    except KeyError as exc:
        raise CurriculumContractError(
            f"Unsupported Senior School level: {level!r}."
        ) from exc


# ============================================================================
# LEVEL CONTRACT BUILDERS
# ============================================================================

def _grade10_subject_contracts() -> tuple[SubjectContract, ...]:
    return tuple(
        SubjectContract(
            code=code,
            name=name,
            lessons_per_week=lessons,
            category=category,
            required=required,
        )
        for code, name, lessons, category, required
        in GRADE10_SUBJECTS
    )


def _form_level_subjects(
    level: str,
) -> tuple[SubjectContract, ...]:
    contracts = tuple(
        contract
        for contract in SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS.values()
        if contract.level == level
    )

    if not contracts:
        raise CurriculumContractError(
            f"No class contracts exist for {level}."
        )

    subjects: dict[str, SubjectContract] = {}

    for contract in contracts:
        for subject in contract.standalone_subjects:
            subjects.setdefault(subject.code, subject)

    return tuple(
        subjects[code]
        for code in sorted(subjects)
    )


def build_contract(
    level: str,
) -> SeniorSchoolCurriculumContract:
    normalized = normalize_senior_school_level(level)

    if normalized == "Grade 10":
        return SeniorSchoolCurriculumContract(
            level="Grade 10",
            subjects=_grade10_subject_contracts(),
            elective_blocks=GRADE10_PARALLEL_BLOCKS,
            weekly_teaching_slots=49,
        )

    if normalized == "Form 3":
        return SeniorSchoolCurriculumContract(
            level="Form 3",
            subjects=_form_level_subjects("Form 3"),
            elective_blocks=FORM3_PARALLEL_BLOCKS,
            weekly_teaching_slots=49,
        )

    if normalized == "Form 4":
        return SeniorSchoolCurriculumContract(
            level="Form 4",
            subjects=_form_level_subjects("Form 4"),
            elective_blocks=FORM4_PARALLEL_BLOCKS,
            weekly_teaching_slots=49,
        )

    raise CurriculumContractError(
        f"Unsupported Senior School level: {level!r}."
    )


def build_class_contract(
    group_code: str,
) -> SeniorSchoolClassCurriculumContract:
    code = str(group_code).strip().upper()

    try:
        return SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS[code]
    except KeyError as exc:
        raise CurriculumContractError(
            f"No Senior School class curriculum contract exists "
            f"for {code!r}."
        ) from exc


# ============================================================================
# GRADE 10 SUBJECT COMBINATION VALIDATION
# ============================================================================

def validate_subject_combination(
    level: str,
    subject_codes: Iterable[str],
) -> None:
    normalized = normalize_senior_school_level(level)

    if normalized != "Grade 10":
        raise CurriculumContractError(
            "Subject-combination validation currently applies "
            "to Grade 10."
        )

    codes = tuple(
        str(code).strip().upper()
        for code in subject_codes
    )

    if len(codes) != len(set(codes)):
        raise CurriculumContractError(
            f"Duplicate subject codes are not permitted: {codes!r}."
        )

    known = {
        subject[0]
        for subject in GRADE10_SUBJECTS
    }

    unknown = sorted(set(codes) - known)

    if unknown:
        raise CurriculumContractError(
            f"Unknown Grade 10 subject code(s): {unknown!r}."
        )

    for block_code, _label, options in GRADE10_ELECTIVE_BLOCKS:
        selected = [
            code
            for code in codes
            if code in options
        ]

        if len(selected) != 1:
            raise CurriculumContractError(
                f"{block_code} requires exactly one selected subject; "
                f"received {selected!r}."
            )

    if "FRE" in codes:
        raise CurriculumContractError(
            "FRE is temporarily inactive because no active teacher "
            "is assigned."
        )


# ============================================================================
# INSTRUCTIONAL GROUP RESOLUTION
# ============================================================================

def resolve_instructional_group(
    group_code: str,
) -> InstructionalGroup:
    code = str(group_code).strip().upper()

    matches = (
        InstructionalGroup.objects
        .select_related(
            "teaching_group__stream__grade__academic_year"
        )
        .filter(
            code=code,
            is_active=True,
        )
    )

    count = matches.count()

    if count == 0:
        raise CurriculumContractError(
            f"Active instructional group {code!r} was not found."
        )

    if count > 1:
        raise CurriculumContractError(
            f"Instructional group code {code!r} resolves to "
            f"{count} active groups."
        )

    return matches.get()


def resolve_senior_school_instructional_groups(
) -> dict[str, InstructionalGroup]:
    return {
        code: resolve_instructional_group(code)
        for code in EXPECTED_SENIOR_SCHOOL_GROUP_CODES
    }


def validate_senior_school_group_mapping(
) -> dict[str, InstructionalGroup]:
    groups = resolve_senior_school_instructional_groups()

    for code, group in groups.items():
        if not group.is_active:
            raise CurriculumContractError(
                f"Senior School instructional group {code} is inactive."
            )

        if group.code != code:
            raise CurriculumContractError(
                f"Senior School instructional group mapping mismatch "
                f"for {code}."
            )

        if group.teaching_group is None:
            raise CurriculumContractError(
                f"Senior School instructional group {code} has no "
                f"teaching group."
            )

    return groups


# ============================================================================
# LESSON REQUIREMENT CONTRACT SUBJECT RESOLUTION
# ============================================================================

def _lesson_requirement_subjects_for_group(
    group_code: str,
) -> tuple[SubjectContract, ...]:
    """
    Return only subjects that should become LessonRequirement rows.

    Grade 10:
        Only required/core subjects are materialized here.
        Elective subjects belong to synchronized scheduler-owned
        elective blocks and must not be duplicated as ordinary
        LessonRequirement rows.

    Form 3 / Form 4:
        Only standalone subjects are materialized.
        Parallel blocks and activities remain scheduler-owned.
    """
    code = str(group_code).strip().upper()

    if code in GRADE10_GROUP_CODES:
        contract = build_contract("Grade 10")

        return tuple(
            subject
            for subject in contract.subjects
            if subject.required
        )

    contract = build_class_contract(code)

    return contract.standalone_subjects


# ============================================================================
# LESSON REQUIREMENT PAYLOADS
# ============================================================================

def build_lesson_requirement_payloads(
    group_code: str,
    term: Term,
) -> list[dict]:
    code = str(group_code).strip().upper()

    if code not in EXPECTED_SENIOR_SCHOOL_GROUP_CODES:
        raise CurriculumContractError(
            f"Unsupported Senior School instructional group "
            f"{group_code!r}."
        )

    subjects = _lesson_requirement_subjects_for_group(code)

    payloads: list[dict] = []

    for subject in subjects:
        payloads.append(
            {
                "term": term,
                "instructional_group": code,
                "subject_code": subject.code,
                "lessons_per_week": subject.lessons_per_week,
                "is_active": True,
            }
        )

    validate_lesson_requirement_payloads(payloads)

    return payloads


def validate_lesson_requirement_payloads(
    payloads: Iterable[dict],
) -> None:
    seen: set[tuple[object, str, str]] = set()

    for payload in payloads:
        term = payload.get("term")

        group_code = str(
            payload.get("instructional_group", "")
        ).strip().upper()

        subject_code = str(
            payload.get("subject_code", "")
        ).strip().upper()

        lessons = payload.get("lessons_per_week")

        if term is None:
            raise CurriculumContractError(
                "Lesson requirement payload is missing term."
            )

        if not group_code:
            raise CurriculumContractError(
                "Lesson requirement payload is missing "
                "instructional group."
            )

        if not subject_code:
            raise CurriculumContractError(
                "Lesson requirement payload is missing subject code."
            )

        if not isinstance(lessons, int) or lessons < 1:
            raise CurriculumContractError(
                f"Invalid lessons_per_week for {subject_code}: "
                f"{lessons!r}."
            )

        key = (
            term,
            group_code,
            subject_code,
        )

        if key in seen:
            raise CurriculumContractError(
                "Duplicate lesson requirement payload for "
                f"{group_code}/{subject_code}."
            )

        seen.add(key)


# ============================================================================
# LESSON REQUIREMENT APPLICATION
# ============================================================================

@transaction.atomic
def apply_lesson_requirements(
    term: Term,
    group_code: str,
    *,
    commit: bool = True,
) -> list[LessonRequirement]:
    """
    Apply standalone subject requirements only.

    Grade 10 core subjects are materialized as LessonRequirement rows.
    Grade 10 elective blocks remain scheduler-owned.

    Form 3 / Form 4 standalone subjects are materialized as
    LessonRequirement rows.
    Their parallel blocks and activities remain scheduler-owned.
    """
    group = resolve_instructional_group(group_code)
    code = group.code.strip().upper()

    subjects_contract = _lesson_requirement_subjects_for_group(code)

    subject_codes = {
        subject.code
        for subject in subjects_contract
    }

    subjects = {
        subject.code: subject
        for subject in Subject.objects.filter(
            code__in=subject_codes,
            is_active=True,
        )
    }

    missing = sorted(
        subject_codes - set(subjects)
    )

    if missing:
        raise CurriculumContractError(
            f"Missing active Subject rows for {code}: "
            f"{missing!r}."
        )

    payloads = build_lesson_requirement_payloads(
        code,
        term,
    )

    validate_lesson_requirement_payloads(payloads)

    created: list[LessonRequirement] = []

    for payload in payloads:
        if not commit:
            continue

        requirement, _created = (
            LessonRequirement.objects.update_or_create(
                term=term,
                instructional_group=group,
                subject=subjects[payload["subject_code"]],
                defaults={
                    "lessons_per_week": payload["lessons_per_week"],
                    "is_active": True,
                },
            )
        )

        created.append(requirement)

    return created


# ============================================================================
# SUMMARIES
# ============================================================================

def class_contract_summary(
    group_code: str,
) -> dict[str, int | str]:
    contract = build_class_contract(group_code)

    return {
        "code": contract.code,
        "level": contract.level,
        "standalone_lessons": contract.standalone_lessons,
        "parallel_block_lessons": contract.block_lessons,
        "activity_lessons": contract.activity_lessons,
        "total_weekly_periods": contract.total_weekly_periods,
    }


def contract_summary(
    level: str,
) -> dict:
    normalized = normalize_senior_school_level(level)

    if normalized == "Grade 10":
        contract = build_contract(normalized)

        return {
            "level": contract.level,
            "core_lessons": contract.core_lessons,
            "elective_block_lessons": (
                contract.elective_block_lessons
            ),
            "weekly_teaching_slots": (
                contract.weekly_teaching_slots
            ),
            "subjects": len(contract.subjects),
            "elective_blocks": len(contract.elective_blocks),
        }

    class_groups = {
        code: class_contract_summary(code)
        for code, contract
        in SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS.items()
        if contract.level == normalized
    }

    return {
        "level": normalized,
        "class_groups": class_groups,
        "weekly_teaching_slots": 49,
    }


# ============================================================================
# CROSS-CONTRACT VALIDATION
# ============================================================================

def validate_synchronized_block_contracts() -> None:
    for level in ("Form 3", "Form 4"):
        contracts = [
            contract
            for contract
            in SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS.values()
            if contract.level == level
        ]

        if len(contracts) != 2:
            raise CurriculumContractError(
                f"{level} must have exactly two class-group contracts."
            )

        first_blocks = contracts[0].parallel_blocks
        second_blocks = contracts[1].parallel_blocks

        if first_blocks != second_blocks:
            raise CurriculumContractError(
                f"{level} East/West parallel block contracts "
                "are not synchronized."
            )


def validate_senior_school_contracts() -> None:
    grade10 = build_contract("Grade 10")

    if grade10.core_lessons != 29:
        raise CurriculumContractError(
            f"Grade 10 core workload must be 29, got "
            f"{grade10.core_lessons}."
        )

    if grade10.elective_block_lessons != 20:
        raise CurriculumContractError(
            f"Grade 10 elective block workload must be 20, got "
            f"{grade10.elective_block_lessons}."
        )

    if grade10.weekly_teaching_slots != 49:
        raise CurriculumContractError(
            f"Grade 10 weekly workload must be 49, got "
            f"{grade10.weekly_teaching_slots}."
        )

    if len(grade10.subjects) != 20:
        raise CurriculumContractError(
            f"Grade 10 must define 20 subjects, got "
            f"{len(grade10.subjects)}."
        )

    if len(grade10.elective_blocks) != 4:
        raise CurriculumContractError(
            "Grade 10 must define exactly four elective blocks."
        )

    for code, contract in (
        SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS.items()
    ):
        if contract.total_weekly_periods != 49:
            raise CurriculumContractError(
                f"{code} must total 49 weekly periods; got "
                f"{contract.total_weekly_periods}."
            )

        if contract.block_lessons != 17:
            raise CurriculumContractError(
                f"{code} must contain 17 parallel-block periods; "
                f"got {contract.block_lessons}."
            )

        if contract.total_lessons != 49:
            raise CurriculumContractError(
                f"{code} contract components must total 49; "
                f"got {contract.total_lessons}."
            )

    expected_activity_lessons = {
        "3E": 10,
        "3W": 11,
        "4E": 8,
        "4W": 9,
    }

    for code, expected in expected_activity_lessons.items():
        actual = build_class_contract(code).activity_lessons

        if actual != expected:
            raise CurriculumContractError(
                f"{code} activity workload must be {expected}; "
                f"got {actual}."
            )

    validate_synchronized_block_contracts()
