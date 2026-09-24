"""
S1 — Synchronized block display DTO.

Pure functions to resolve a synchronized-block membership and build a
display DTO for the API. No DB access; no side effects.

The serializer is the intended caller. Teacher codes are supplied by
the caller via a subject -> teacher_code map so this module remains
testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    get_grade10_parallel_block_for_subject,
    get_senior_school_block_for_subject,
    is_grade10_instructional_group,
    is_senior_school_instructional_group,
)


@dataclass(frozen=True)
class BlockMemberDisplay:
    subject_code: str
    teacher_code: str | None


@dataclass(frozen=True)
class BlockDisplay:
    code: str
    namespace: str
    display: str
    members: tuple[BlockMemberDisplay, ...]
    has_any_teacher: bool

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "namespace": self.namespace,
            "display": self.display,
            "members": [
                {
                    "subject_code": m.subject_code,
                    "teacher_code": m.teacher_code,
                }
                for m in self.members
            ],
            "has_any_teacher": self.has_any_teacher,
        }


def resolve_block_membership(
    *,
    subject_code,
    group,
) -> tuple[str, str, tuple[str, ...]] | None:
    """
    Return (namespace, block_code, subject_codes) or None.

    Namespace is "GRADE10" or "SENIOR".
    """
    if subject_code is None or group is None:
        return None

    code = str(subject_code).strip().upper()
    if not code:
        return None

    if is_grade10_instructional_group(group):
        block = get_grade10_parallel_block_for_subject(code)
        if block is None:
            return None
        return ("GRADE10", block.code, tuple(block.subject_codes))

    if is_senior_school_instructional_group(group):
        block = get_senior_school_block_for_subject(code)
        if block is None:
            return None
        return ("SENIOR", block.code, tuple(block.subject_codes))

    return None


def build_display(
    *,
    namespace: str,
    block_code: str,
    subject_codes,
    teacher_map: dict[str, str | None],
) -> BlockDisplay:
    """
    Assemble a BlockDisplay.

    teacher_map: {subject_code_upper: teacher_code | None}
    """
    members = tuple(
        BlockMemberDisplay(
            subject_code=str(sc).strip().upper(),
            teacher_code=teacher_map.get(str(sc).strip().upper()),
        )
        for sc in subject_codes
    )
    display = " / ".join(m.subject_code for m in members)
    has_any = any(m.teacher_code is not None for m in members)
    return BlockDisplay(
        code=block_code,
        namespace=namespace,
        display=display,
        members=members,
        has_any_teacher=has_any,
    )
