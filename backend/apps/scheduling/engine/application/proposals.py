"""Translate deterministic diagnostics into concrete LR edits.

The generator is a pure function over the *problem*; it never writes.
Each proposal carries enough info for a caller to verify and execute
it: target id, current value, proposed value. Stale proposals are
rejected by the apply endpoint, so re-running after an apply is safe.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import UUID

from apps.scheduling.engine.solver.infeasibility_diagnostics import (
    InfeasibilityDiagnostic,
)


@dataclass(frozen=True, slots=True)
class Proposal:
    id: str
    action: str
    description: str
    rationale: str
    target_kind: str
    target_id: str
    current_value: dict
    proposed_value: dict
    severity: str = "warning"   # "critical" | "warning" | "info"


def _shortfall(detail: dict) -> int:
    try:
        req = int(
            detail.get("required_periods")
            or detail.get("required")
            or detail.get("required_total")
            or 0
        )
        avail = int(
            detail.get("available_slots")
            or detail.get("available_group_slots")
            or detail.get("available_teacher_slots")
            or detail.get("available")
            or detail.get("available_total")
            or 0
        )
        return max(0, req - avail)
    except (TypeError, ValueError):
        return 0


def _lr_candidates(*, group_id=None, teacher_id=None, limit=3):
    from apps.academics.models import LessonRequirement

    qs = LessonRequirement.objects.filter(is_active=True)
    if group_id is not None:
        qs = qs.filter(instructional_group_id=group_id)
    if teacher_id is not None:
        qs = qs.filter(teacher_id=teacher_id)
    qs = qs.order_by("-lessons_per_week")
    return list(qs[:limit])


def _reduce_lr_proposals(candidates, short, *, reason):
    out: list[Proposal] = []
    for lr in candidates:
        cur = int(lr.lessons_per_week or 0)
        new = max(1, cur - short)
        if new == cur:
            continue
        out.append(
            Proposal(
                id=f"reduce_lr:{lr.id}:{cur}->{new}",
                action="reduce_lr_periods",
                description=(
                    f"Reduce {lr.subject.code if lr.subject else '?'} "
                    f"({lr.instructional_group.code if lr.instructional_group else '?'}) "
                    f"from {cur} to {new} periods/week"
                ),
                rationale=reason + f" Reducing this LR by {cur - new} helps.",
                target_kind="lesson_requirement",
                target_id=str(lr.id),
                current_value={"lessons_per_week": cur},
                proposed_value={"lessons_per_week": new},
            )
        )
    return out


def generate_proposals_for_diagnostic(
    diag: InfeasibilityDiagnostic,
) -> tuple[Proposal, ...]:
    details = diag.details or {}

    if diag.code == "TEACHER_CAPACITY":
        tid_raw = details.get("teacher_id")
        if not tid_raw:
            return ()
        try:
            tid = UUID(str(tid_raw))
        except (TypeError, ValueError):
            return ()
        short = _shortfall(details)
        if short <= 0:
            return ()
        cands = _lr_candidates(teacher_id=tid)
        return tuple(
            Proposal(
                id=p.id, action=p.action, description=p.description,
                rationale=p.rationale, target_kind=p.target_kind,
                target_id=p.target_id, current_value=p.current_value,
                proposed_value=p.proposed_value, severity="critical",
            )
            for p in _reduce_lr_proposals(
                cands, short,
                reason=(
                    "Teacher is short by "
                    f"{short} period(s) against available slots."
                ),
            )
        )

    if diag.code in ("GROUP_CAPACITY", "INSTRUCTIONAL_GROUP_CAPACITY"):
        gid_raw = details.get("group_id") or details.get("instructional_group_id")
        if not gid_raw:
            return ()
        try:
            gid = UUID(str(gid_raw))
        except (TypeError, ValueError):
            return ()
        short = _shortfall(details)
        if short <= 0:
            return ()
        cands = _lr_candidates(group_id=gid)
        return tuple(
            Proposal(
                id=p.id, action=p.action, description=p.description,
                rationale=p.rationale, target_kind=p.target_kind,
                target_id=p.target_id, current_value=p.current_value,
                proposed_value=p.proposed_value, severity="critical",
            )
            for p in _reduce_lr_proposals(
                cands, short,
                reason=(
                    "Group is over capacity by "
                    f"{short} period(s) per week."
                ),
            )
        )

    return ()


def generate_contract_proposals(term) -> tuple[Proposal, ...]:
    """Propose LR reductions when a group exceeds its docx quota.

    Severity is 'warning' — this will not block generation (the
    solver can still fit the periods) but it deviates from the
    approved contract.
    """
    from collections import defaultdict
    from apps.academics.models import LessonRequirement
    from apps.academics.api.lr_contract import contract_for

    out: list[Proposal] = []
    by_group: dict = defaultdict(lambda: defaultdict(int))
    lrs_by_key: dict = defaultdict(list)
    for lr in (
        LessonRequirement.objects
        .filter(term=term, is_active=True)
        .select_related("instructional_group", "subject")
    ):
        if lr.instructional_group is None or lr.subject is None:
            continue
        gc = lr.instructional_group.code
        key = (lr.subject.code, lr.requirement_type)
        by_group[gc][key] += int(lr.lessons_per_week or 0)
        lrs_by_key[(gc,) + key].append(lr)

    for gc, sched in by_group.items():
        contract = contract_for(gc)
        if contract is None:
            continue
        for (sc, rt), want in contract.items():
            have = sched.get((sc, rt), 0)
            if have <= want:
                continue
            # Find the LR driving the excess.
            for lr in lrs_by_key.get((gc, sc, rt), []):
                cur = int(lr.lessons_per_week or 0)
                new = want
                if new == cur or new < 1:
                    continue
                out.append(
                    Proposal(
                        id=f"reduce_lr:{lr.id}:{cur}->{new}",
                        action="reduce_lr_periods",
                        description=(
                            f"Reduce {sc} ({gc}) from {cur} to "
                            f"{new} periods/week"
                        ),
                        rationale=(
                            f"Docx contract requires {want}/week for "
                            f"{sc} ({gc}); currently {cur}. Not a "
                            "blocking issue but relaxes the approved "
                            "curriculum."
                        ),
                        target_kind="lesson_requirement",
                        target_id=str(lr.id),
                        current_value={"lessons_per_week": cur},
                        proposed_value={"lessons_per_week": new},
                        severity="warning",
                    )
                )
    return tuple(out)


def generate_proposals(problem) -> tuple[Proposal, ...]:
    from apps.scheduling.engine.solver.infeasibility_diagnostics import (
        analyze_infeasibility,
    )
    report = analyze_infeasibility(problem)
    if report.is_empty:
        return ()
    seen: set[str] = set()
    out: list[Proposal] = []
    for diag in report.diagnostics:
        for p in generate_proposals_for_diagnostic(diag):
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(p)
    return tuple(out)
