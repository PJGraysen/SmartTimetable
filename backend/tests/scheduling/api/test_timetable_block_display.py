"""
S1 — synchronized-block display DTO tests.

These tests exercise the serializer's get_block method and the pure
functions in block_display. They do not touch the database: the
teacher-map resolver is patched where needed so we can assert the DTO
shape independently of fixture data.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


# ----------------------------------------------------------------------
# Test 1 — Grade 10 block entry yields a block DTO with teacher codes
# ----------------------------------------------------------------------
def test_block_dto_present_for_grade10_block_entry():
    from apps.scheduling.api.serializers import (
        TimetableEntryResultSerializer,
    )

    entry = SimpleNamespace(
        lesson_requirement=SimpleNamespace(
            subject=SimpleNamespace(code="CHEM"),
        ),
        instructional_group=SimpleNamespace(code="10E"),
        timetable_version=SimpleNamespace(
            term=SimpleNamespace(id="test-term"),
        ),
    )
    serializer = TimetableEntryResultSerializer(context={})

    with patch.object(
        serializer,
        "_resolve_member_teachers",
        return_value={
            "CHEM": "T005",
            "LIT": "T011",
            "PHY": "T009",
        },
    ):
        dto = serializer.get_block(entry)

    assert dto is not None
    assert dto["namespace"] == "GRADE10"
    assert dto["code"] == "OPTION_2"
    assert dto["display"] == "CHEM / PHY / LIT"
    assert dto["has_any_teacher"] is True
    assert len(dto["members"]) == 3
    by_subject = {m["subject_code"]: m["teacher_code"] for m in dto["members"]}
    assert by_subject == {"CHEM": "T005", "LIT": "T011", "PHY": "T009"}


# ----------------------------------------------------------------------
# Test 2 — Senior block entry yields a block DTO without teacher codes
# ----------------------------------------------------------------------
def test_block_dto_present_for_senior_block_entry():
    from apps.scheduling.api.serializers import (
        TimetableEntryResultSerializer,
    )

    entry = SimpleNamespace(
        lesson_requirement=SimpleNamespace(
            subject=SimpleNamespace(code="AGR"),
        ),
        instructional_group=SimpleNamespace(code="3E"),
        timetable_version=SimpleNamespace(
            term=SimpleNamespace(id="test-term"),
        ),
    )
    serializer = TimetableEntryResultSerializer(context={})

    with patch.object(
        serializer,
        "_resolve_member_teachers",
        return_value={"AGR": None, "BUS": None, "CS": None},
    ):
        dto = serializer.get_block(entry)

    assert dto is not None
    assert dto["namespace"] == "SENIOR"
    assert dto["code"] == "TECHNICALS_APPLIED"
    assert dto["display"] == "AGR / BUS / CS"
    assert dto["has_any_teacher"] is False
    assert all(m["teacher_code"] is None for m in dto["members"])


# ----------------------------------------------------------------------
# Test 3 — Standalone entry yields no block DTO
# ----------------------------------------------------------------------
def test_block_dto_absent_for_standalone_entry():
    from apps.scheduling.api.serializers import (
        TimetableEntryResultSerializer,
    )

    entry = SimpleNamespace(
        lesson_requirement=SimpleNamespace(
            subject=SimpleNamespace(code="ENG"),
        ),
        instructional_group=SimpleNamespace(code="10E"),
        timetable_version=SimpleNamespace(
            term=SimpleNamespace(id="test-term"),
        ),
    )
    serializer = TimetableEntryResultSerializer(context={})

    assert serializer.get_block(entry) is None


# ----------------------------------------------------------------------
# Test 4 — Same block, different streams: stable DTO (identical code,
# display, has_any_teacher) across 10E and 10W
# ----------------------------------------------------------------------
def test_block_dto_stable_across_10e_and_10w():
    from apps.scheduling.api.serializers import (
        TimetableEntryResultSerializer,
    )

    teachers = {"BIO": "T016", "MUS": "T019", "FRE": "TXXX"}

    def _dto_for(group_code):
        entry = SimpleNamespace(
            lesson_requirement=SimpleNamespace(
                subject=SimpleNamespace(code="MUS"),
            ),
            instructional_group=SimpleNamespace(code=group_code),
            timetable_version=SimpleNamespace(
                term=SimpleNamespace(id="test-term"),
            ),
        )
        ser = TimetableEntryResultSerializer(context={})
        with patch.object(
            ser, "_resolve_member_teachers", return_value=dict(teachers),
        ):
            return ser.get_block(entry)

    dto_e = _dto_for("10E")
    dto_w = _dto_for("10W")

    assert dto_e is not None and dto_w is not None
    assert dto_e["code"] == dto_w["code"]
    assert dto_e["namespace"] == dto_w["namespace"]
    assert dto_e["display"] == dto_w["display"]
    assert dto_e["has_any_teacher"] == dto_w["has_any_teacher"]


# ----------------------------------------------------------------------
# Test 5 — No teacher is manufactured where the domain has none
# ----------------------------------------------------------------------
def test_block_dto_does_not_manufacture_teacher_codes():
    from apps.scheduling.engine.application.block_display import (
        build_display,
    )

    dto = build_display(
        namespace="SENIOR",
        block_code="SCIENCE",
        subject_codes=("BIO", "CHEM", "PHY"),
        teacher_map={"BIO": None, "CHEM": None, "PHY": None},
    )

    assert dto.has_any_teacher is False
    assert [m.teacher_code for m in dto.members] == [None, None, None]
    assert dto.display == "BIO / CHEM / PHY"
