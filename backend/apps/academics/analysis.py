"""
Academic analysis engine.

Pure computation over Assessment / Result data. No ORM writes.
All functions return JSON-safe dicts (str / int / float / None / list / dict).
"""
import statistics
from collections import defaultdict
from decimal import Decimal

from apps.academics.models import (
    Assessment,
    GradingScheme,
    Result,
    ResultStatus,
    Student,
    Subject,
)


PASS_THRESHOLD = 50.0
INTERVENTION_THRESHOLD = 45.0


from functools import lru_cache
from django.core.cache import cache


# ---------------------------------------------------------------------
# Grading-band cache
# ---------------------------------------------------------------------
# grade_for() used to hit the DB on every single call ? 20k+ queries
# per analytics request. We now cache the scheme's bands for 5 minutes
# and expose invalidate_grading_cache() for the admin CRUD endpoints.
# ---------------------------------------------------------------------
_SCHEME_CACHE_KEY = "academics:active_scheme_id"
_BANDS_VERSION_KEY = "academics:bands:version"
_SCHEME_TTL = 300


def _bands_version() -> int:
    v = cache.get(_BANDS_VERSION_KEY)
    if v is None:
        v = 1
        cache.set(_BANDS_VERSION_KEY, v, None)
    return v


def _bands_for_scheme(scheme_id):
    """Cached tuple of (grade, min_score, max_score, points, descriptor)."""
    v = _bands_version()
    key = f"academics:bands:{scheme_id}:v{v}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    from apps.academics.models import GradingBand
    bands = tuple(
        GradingBand.objects
        .filter(scheme_id=scheme_id)
        .order_by("-min_score")
        .values_list("grade", "min_score", "max_score", "points", "descriptor")
    )
    cache.set(key, bands, _SCHEME_TTL)
    return bands


def invalidate_grading_cache():
    """Drop cached scheme + bands. Call after admin changes grading."""
    cache.set(_BANDS_VERSION_KEY, _bands_version() + 1, None)
    cache.delete(_SCHEME_CACHE_KEY)


def _active_scheme():
    cached_id = cache.get(_SCHEME_CACHE_KEY)
    if cached_id:
        s = GradingScheme.objects.filter(pk=cached_id).first()
        if s:
            return s
    s = GradingScheme.objects.filter(is_active=True).order_by("-created_at").first()
    if s:
        cache.set(_SCHEME_CACHE_KEY, s.pk, _SCHEME_TTL)
    return s


def grade_for(scheme, score):
    if scheme is None or score is None:
        return None
    score_f = float(score)
    for grade, min_s, max_s, points, descriptor in _bands_for_scheme(scheme.pk):
        if float(min_s) <= score_f <= float(max_s):
            return {
                "grade": grade,
                "points": float(points),
                "descriptor": descriptor,
            }
    return None


def _pct(score, max_mark):
    if score is None or max_mark <= 0:
        return None
    return round(float(score) / float(max_mark) * 100, 2)


def _a_dict(a):
    return {
        "id": str(a.id),
        "name": a.name,
        "type": a.assessment_type,
        "date": a.date.isoformat(),
        "max_mark": a.max_mark,
        "status": a.status,
    }


def _collect(assessment):
    scheme = _active_scheme()
    rows = list(
        Result.objects.filter(assessment=assessment)
        .select_related("student", "subject")
    )
    by_student = defaultdict(list)
    by_subject = defaultdict(list)
    for r in rows:
        if r.status != ResultStatus.VALID:
            continue
        pct = _pct(r.raw_mark, assessment.max_mark)
        if pct is None:
            continue
        by_student[r.student_id].append((r.subject_id, pct))
        by_subject[r.subject_id].append((r.student_id, pct))
    return scheme, by_student, by_subject


def _grade_counts(pcts, scheme):
    counts = defaultdict(int)
    for p in pcts:
        g = grade_for(scheme, p)
        counts[g["grade"] if g else "?"] += 1
    return dict(sorted(counts.items()))


def dashboard(assessment_id):
    a = Assessment.objects.get(id=assessment_id)
    scheme, by_student, by_subject = _collect(a)

    all_pcts = [p for v in by_student.values() for _, p in v]
    if not all_pcts:
        return {"assessment": _a_dict(a), "empty": True}

    student_means = {
        sid: round(statistics.mean([p for _, p in v]), 2)
        for sid, v in by_student.items() if v
    }

    subjects = Subject.objects.in_bulk(list(by_subject.keys()))

    subject_rows = []
    for sid, pairs in by_subject.items():
        pcts = [p for _, p in pairs]
        s = subjects.get(sid)
        if not s:
            continue
        mean = round(statistics.mean(pcts), 2)
        sd = round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0
        passes = sum(1 for p in pcts if p >= PASS_THRESHOLD)
        subject_rows.append({
            "subject_id": str(sid),
            "subject_code": s.code,
            "subject_name": s.name,
            "candidates": len(pcts),
            "mean": mean,
            "median": round(statistics.median(pcts), 2),
            "std_dev": sd,
            "highest": round(max(pcts), 2),
            "lowest": round(min(pcts), 2),
            "pass_count": passes,
            "pass_rate": round(passes / len(pcts) * 100, 2),
            "grade_counts": _grade_counts(pcts, scheme),
        })
    subject_rows.sort(key=lambda r: -r["mean"])

    overall_mean = round(statistics.mean(all_pcts), 2)
    overall_sd = round(statistics.pstdev(all_pcts), 2) if len(all_pcts) > 1 else 0.0
    passes = sum(1 for p in all_pcts if p >= PASS_THRESHOLD)

    # Rankings
    students = Student.objects.in_bulk(list(student_means.keys()))
    ranking = []
    for sid, m in student_means.items():
        st = students.get(sid)
        if not st:
            continue
        g = grade_for(scheme, m)
        ranking.append({
            "student_id": str(sid),
            "admission_number": st.admission_number,
            "name": st.full_name,
            "mean": m,
            "grade": g["grade"] if g else "-",
        })
    ranking.sort(key=lambda r: -r["mean"])
    # Competition ranking (ties get same rank, next rank skips)
    prev = None
    for i, r in enumerate(ranking, start=1):
        if prev is not None and r["mean"] == prev[0]:
            r["rank"] = prev[1]
        else:
            r["rank"] = i
        prev = (r["mean"], r["rank"])

    grade_dist = _grade_counts(all_pcts, scheme)

    # Interpretations
    insights = []
    if subject_rows:
        top = subject_rows[0]
        bottom = subject_rows[-1]
        insights.append({
            "severity": "positive",
            "title": f"Strongest subject: {top['subject_name']}",
            "detail": f"Mean {top['mean']}% — {top['pass_rate']}% pass rate across {top['candidates']} candidates.",
        })
        if bottom["mean"] < overall_mean - 3:
            insights.append({
                "severity": "warning",
                "title": f"{bottom['subject_name']} underperforming",
                "detail": f"Mean {bottom['mean']}% ({round(overall_mean - bottom['mean'], 2)} pts below overall {overall_mean}%).",
            })
        for s in subject_rows:
            if s["std_dev"] > 15:
                insights.append({
                    "severity": "info",
                    "title": f"Wide dispersion in {s['subject_name']}",
                    "detail": f"SD {s['std_dev']} — mixed ability, consider differentiated teaching.",
                })
        below = [s for s in subject_rows if s["pass_rate"] < 60]
        for s in below:
            insights.append({
                "severity": "warning",
                "title": f"{s['subject_name']}: low pass rate {s['pass_rate']}%",
                "detail": f"{s['candidates'] - s['pass_count']} of {s['candidates']} candidates below {int(PASS_THRESHOLD)}%.",
            })
    at_risk = [r for r in ranking if r["mean"] < INTERVENTION_THRESHOLD]
    if at_risk:
        insights.append({
            "severity": "danger",
            "title": f"{len(at_risk)} students need intervention",
            "detail": "Mean below " + str(int(INTERVENTION_THRESHOLD)) + "%. Prioritise support.",
        })
    top3 = [r for r in ranking[:3]]
    if top3:
        insights.append({
            "severity": "positive",
            "title": "Top performers",
            "detail": " · ".join(f"{r['name']} ({r['mean']}%)" for r in top3),
        })

    return {
        "assessment": _a_dict(a),
        "students": len(student_means),
        "results": len(all_pcts),
        "overall_mean": overall_mean,
        "overall_median": round(statistics.median(all_pcts), 2),
        "overall_std_dev": overall_sd,
        "pass_rate": round(passes / len(all_pcts) * 100, 2),
        "highest": round(max(all_pcts), 2),
        "lowest": round(min(all_pcts), 2),
        "subject_rows": subject_rows,
        "grade_distribution": grade_dist,
        "ranking": ranking,
        "insights": insights,
    }


def trend(assessment_ids):
    """Mean percentage per assessment, ordered by assessment date."""
    rows = []
    for aid in assessment_ids:
        try:
            a = Assessment.objects.get(id=aid)
        except Assessment.DoesNotExist:
            continue
        pcts = [
            _pct(r.raw_mark, a.max_mark)
            for r in Result.objects.filter(assessment=a, status=ResultStatus.VALID)
        ]
        pcts = [p for p in pcts if p is not None]
        if not pcts:
            continue
        rows.append({
            "assessment_id": str(a.id),
            "assessment_name": a.name,
            "date": a.date.isoformat(),
            "mean": round(statistics.mean(pcts), 2),
            "pass_rate": round(
                sum(1 for p in pcts if p >= PASS_THRESHOLD) / len(pcts) * 100, 2
            ),
        })
    rows.sort(key=lambda r: r["date"])
    return rows


def list_assessments():
    return [_a_dict(a) for a in Assessment.objects.all().order_by("date")]


# ---------------------------------------------------------------------
# Deep individual student analysis (added 2026-09-16)
# ---------------------------------------------------------------------
def student_deep_analysis(student_id):
    from apps.academics.models import Student, Result, ResultStatus
    from apps.core.models import Term  # noqa

    student = Student.objects.get(id=student_id)
    scheme = _active_scheme()

    enrollment = (
        student.enrollments.filter(is_current=True)
        .select_related("teaching_group").first()
    )
    teaching_group = enrollment.teaching_group if enrollment else None

    results = (
        Result.objects.filter(student=student, status=ResultStatus.VALID)
        .select_related("assessment", "subject")
        .order_by("assessment__date", "subject__name")
    )

    subjects = {}
    for r in results:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        key = r.subject.code
        if key not in subjects:
            subjects[key] = {
                "subject_id": str(r.subject.id),
                "subject_code": r.subject.code,
                "subject_name": r.subject.name,
                "marks": [],
            }
        g = grade_for(scheme, pct) or {}
        subjects[key]["marks"].append({
            "assessment_id": str(r.assessment.id),
            "assessment_name": r.assessment.name,
            "date": r.assessment.date.isoformat(),
            "raw_mark": float(r.raw_mark),
            "max_mark": r.assessment.max_mark,
            "pct": pct,
            "grade": g.get("grade", "-"),
        })

    subject_rows = []
    for subj in subjects.values():
        pcts = [m["pct"] for m in subj["marks"]]
        if not pcts:
            continue
        mean = round(statistics.mean(pcts), 2)
        sd = round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0
        g = grade_for(scheme, mean) or {}
        trend = "stable"
        delta = 0.0
        if len(pcts) >= 2:
            delta = round(pcts[-1] - pcts[0], 2)
            if delta > 3:
                trend = "improving"
            elif delta < -3:
                trend = "declining"
        subject_rows.append({
            "subject_id": subj["subject_id"],
            "subject_code": subj["subject_code"],
            "subject_name": subj["subject_name"],
            "mean": mean,
            "median": round(statistics.median(pcts), 2),
            "std_dev": sd,
            "highest": round(max(pcts), 2),
            "lowest": round(min(pcts), 2),
            "assessments_count": len(pcts),
            "grade": g.get("grade", "-"),
            "points": float(g.get("points", 0)),
            "descriptor": g.get("descriptor", ""),
            "trend": trend,
            "delta": delta,
            "marks": sorted(subj["marks"], key=lambda x: x["date"]),
        })
    subject_rows.sort(key=lambda r: -r["mean"])

    all_pcts = [m["pct"] for subj in subjects.values() for m in subj["marks"]]
    overall_mean = round(statistics.mean(all_pcts), 2) if all_pcts else 0
    overall_median = round(statistics.median(all_pcts), 2) if all_pcts else 0
    overall_sd = round(statistics.pstdev(all_pcts), 2) if len(all_pcts) > 1 else 0
    overall_grade = (grade_for(scheme, overall_mean) or {}).get("grade", "-")

    totals_per_assessment = {}
    for r in results:
        aid = r.assessment.id
        if aid not in totals_per_assessment:
            totals_per_assessment[aid] = {
                "assessment_id": str(aid),
                "assessment_name": r.assessment.name,
                "date": r.assessment.date.isoformat(),
                "total": 0.0,
                "total_max": 0,
                "pcts": [],
            }
        if r.raw_mark is not None:
            totals_per_assessment[aid]["total"] += float(r.raw_mark)
            totals_per_assessment[aid]["total_max"] += r.assessment.max_mark
            pct = _pct(r.raw_mark, r.assessment.max_mark)
            if pct is not None:
                totals_per_assessment[aid]["pcts"].append(pct)

    history = []
    for t in sorted(totals_per_assessment.values(), key=lambda x: x["date"]):
        mean_pct = round(statistics.mean(t["pcts"]), 2) if t["pcts"] else 0
        history.append({
            "assessment_id": t["assessment_id"],
            "assessment_name": t["assessment_name"],
            "date": t["date"],
            "total": round(t["total"], 2),
            "total_max": t["total_max"],
            "mean_pct": mean_pct,
            "grade": (grade_for(scheme, mean_pct) or {}).get("grade", "-"),
            "subjects_sat": len(t["pcts"]),
        })

    rank = None
    class_size = None
    class_mean = None
    percentile = None
    class_subject_means = {}

    if teaching_group:
        peers = list(
            Student.objects.filter(
                enrollments__teaching_group=teaching_group,
                enrollments__is_current=True,
            ).distinct().values_list("id", flat=True)
        )
        peer_results = (
            Result.objects.filter(student_id__in=peers, status=ResultStatus.VALID)
            .select_related("assessment", "subject")
        )
        peer_means = {}
        peer_by_subject = {}
        for r in peer_results:
            pct = _pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            peer_means.setdefault(r.student_id, []).append(pct)
            peer_by_subject.setdefault(r.subject_id, []).append(pct)

        peer_overall = {sid: statistics.mean(p) for sid, p in peer_means.items() if p}
        if peer_overall:
            class_mean = round(statistics.mean(peer_overall.values()), 2)
            sorted_peers = sorted(peer_overall.items(), key=lambda x: -x[1])
            prev_score = None
            prev_rank = 0
            for i, (sid, mean) in enumerate(sorted_peers, start=1):
                if prev_score is not None and mean == prev_score:
                    current_rank = prev_rank
                else:
                    current_rank = i
                if sid == student.id:
                    rank = current_rank
                    break
                prev_score = mean
                prev_rank = current_rank
            class_size = len(peer_overall)
            if rank and class_size > 1:
                percentile = round((class_size - rank) / (class_size - 1) * 100, 1)

        for sid, pcts in peer_by_subject.items():
            class_subject_means[str(sid)] = round(statistics.mean(pcts), 2)

    for row in subject_rows:
        cm = class_subject_means.get(row["subject_id"])
        row["class_mean"] = cm
        row["vs_class"] = round(row["mean"] - cm, 2) if cm is not None else None

    strengths = subject_rows[:3]
    weaknesses = [r for r in subject_rows if r["mean"] < overall_mean - 3][:3]
    if not weaknesses and len(subject_rows) > 3:
        weaknesses = subject_rows[-3:]

    improving = [r for r in subject_rows if r["trend"] == "improving"]
    declining = [r for r in subject_rows if r["trend"] == "declining"]

    grade_dist = {}
    for row in subject_rows:
        grade_dist[row["grade"]] = grade_dist.get(row["grade"], 0) + 1

    insights = []
    if subject_rows:
        top = subject_rows[0]
        detail = f"Mean {top['mean']}% ({top['grade']}) across {top['assessments_count']} assessment(s)."
        if top.get("vs_class") is not None:
            sign = "+" if top["vs_class"] >= 0 else ""
            detail += f" {sign}{top['vs_class']} pts vs class."
        insights.append({"severity": "positive", "title": f"Top strength: {top['subject_name']}", "detail": detail})

        if weaknesses:
            w = weaknesses[0]
            detail = f"Mean {w['mean']}% ({w['grade']})."
            if w.get("vs_class") is not None:
                sign = "+" if w["vs_class"] >= 0 else ""
                detail += f" {sign}{w['vs_class']} pts vs class."
            insights.append({"severity": "warning", "title": f"Development area: {w['subject_name']}", "detail": detail})

        if improving:
            insights.append({
                "severity": "positive",
                "title": f"Improving in {len(improving)} subject(s)",
                "detail": " · ".join(f"{r['subject_name']} (+{r['delta']} pts)" for r in improving),
            })
        if declining:
            insights.append({
                "severity": "warning",
                "title": f"Declining in {len(declining)} subject(s)",
                "detail": " · ".join(f"{r['subject_name']} ({r['delta']} pts)" for r in declining),
            })

        if overall_sd < 6:
            insights.append({
                "severity": "positive",
                "title": "Highly consistent performance",
                "detail": f"Standard deviation {overall_sd} across all results.",
            })
        elif overall_sd > 15:
            insights.append({
                "severity": "info",
                "title": "Variable performance",
                "detail": f"Standard deviation {overall_sd} — results swing between assessments.",
            })

        if rank and class_size and rank <= 3:
            insights.append({
                "severity": "positive",
                "title": f"Top {rank} of {class_size} in class",
                "detail": f"Percentile {percentile}% among peers.",
            })

    total_points = sum(r["points"] for r in subject_rows)
    avg_points = round(total_points / len(subject_rows), 2) if subject_rows else 0
    total_marks = round(sum(m["raw_mark"] for subj in subjects.values() for m in subj["marks"]), 2)
    total_max = sum(m["max_mark"] for subj in subjects.values() for m in subj["marks"])

    return {
        "student": {
            "id": str(student.id),
            "admission_number": student.admission_number,
            "first_name": student.first_name,
            "middle_name": student.middle_name,
            "last_name": student.last_name,
            "name": student.full_name,
            "status": student.status,
            "gender": student.gender,
        },
        "teaching_group": (
            {"id": str(teaching_group.id), "name": teaching_group.name}
            if teaching_group else None
        ),
        "summary": {
            "subjects_count": len(subject_rows),
            "assessments_count": len(history),
            "total_marks": total_marks,
            "total_max": total_max,
            "overall_mean": overall_mean,
            "overall_median": overall_median,
            "overall_std_dev": overall_sd,
            "overall_grade": overall_grade,
            "overall_points": avg_points,
            "rank": rank,
            "class_size": class_size,
            "percentile": percentile,
            "class_mean": class_mean,
            "vs_class_mean": (
                round(overall_mean - class_mean, 2) if class_mean is not None else None
            ),
        },
        "subject_rows": subject_rows,
        "history": history,
        "grade_distribution": grade_dist,
        "strengths": [r["subject_name"] for r in strengths],
        "weaknesses": [r["subject_name"] for r in weaknesses],
        "insights": insights,
    }



# ---------------------------------------------------------------------
# Class / stream comparison (RoE Level 3)
# ---------------------------------------------------------------------
def class_comparison(assessment_id):
    from collections import defaultdict as _dd

    a = Assessment.objects.get(id=assessment_id)
    scheme = _active_scheme()

    rows = (
        Result.objects.filter(assessment=a, status=ResultStatus.VALID)
        .select_related("student", "subject")
    )

    by_student = _dd(list)
    for r in rows:
        pct = _pct(r.raw_mark, a.max_mark)
        if pct is None:
            continue
        by_student[r.student_id].append((r.subject.code, pct))

    from apps.academics.models import StudentEnrollment
    enrollments = (
        StudentEnrollment.objects.filter(is_current=True)
        .select_related("teaching_group")
    )
    student_group = {}
    for e in enrollments:
        student_group[e.student_id] = (e.teaching_group_id, e.teaching_group.name)

    groups = _dd(lambda: {"students": [], "subjects": _dd(list)})
    for sid, marks in by_student.items():
        g = student_group.get(sid)
        if not g:
            continue
        gid, gname = g
        groups[(gid, gname)]["students"].append(sid)
        for code, pct in marks:
            groups[(gid, gname)]["subjects"][code].append(pct)

    class_rows = []
    for (gid, gname), data in groups.items():
        all_pcts = [p for sid in data["students"] for _, p in by_student[sid]]
        if not all_pcts:
            continue
        student_means = [
            statistics.mean([p for _, p in by_student[sid]]) for sid in data["students"]
        ]
        passes = sum(1 for p in all_pcts if p >= PASS_THRESHOLD)
        class_rows.append({
            "group_id": str(gid),
            "group_name": gname,
            "students": len(data["students"]),
            "overall_mean": round(statistics.mean(all_pcts), 2),
            "overall_median": round(statistics.median(all_pcts), 2),
            "overall_std_dev": round(statistics.pstdev(all_pcts), 2) if len(all_pcts) > 1 else 0.0,
            "overall_pass_rate": round(passes / len(all_pcts) * 100, 2),
            "best_student_mean": round(max(student_means), 2),
            "worst_student_mean": round(min(student_means), 2),
            "subject_means": {code: round(statistics.mean(ps), 2) for code, ps in data["subjects"].items()},
        })

    class_rows.sort(key=lambda r: -r["overall_mean"])
    for i, r in enumerate(class_rows, start=1):
        r["rank"] = i

    all_codes = sorted({code for r in class_rows for code in r["subject_means"]})

    subject_gaps = []
    for code in all_codes:
        pairs = [(r["group_name"], r["subject_means"].get(code)) for r in class_rows if code in r["subject_means"]]
        if len(pairs) < 2:
            continue
        pairs.sort(key=lambda x: -x[1])
        subject_gaps.append({
            "subject_code": code,
            "best_class": pairs[0][0],
            "best_mean": pairs[0][1],
            "worst_class": pairs[-1][0],
            "worst_mean": pairs[-1][1],
            "gap": round(pairs[0][1] - pairs[-1][1], 2),
        })
    subject_gaps.sort(key=lambda x: -x["gap"])

    insights = []
    if len(class_rows) >= 2:
        best = class_rows[0]
        worst = class_rows[-1]
        gap = round(best["overall_mean"] - worst["overall_mean"], 2)
        insights.append({
            "severity": "positive",
            "title": f"{best['group_name']} leads",
            "detail": f"Mean {best['overall_mean']}% vs {worst['group_name']} {worst['overall_mean']}% — {gap} pt gap.",
        })
        if gap > 5:
            insights.append({
                "severity": "warning",
                "title": "Wide inter-class gap",
                "detail": f"{gap} points between top and bottom class. Prioritise {worst['group_name']}.",
            })
        elif gap < 2:
            insights.append({
                "severity": "info",
                "title": "Classes perform comparably",
                "detail": f"Only {gap} points separate the top and bottom class.",
            })
        if subject_gaps:
            sg = subject_gaps[0]
            insights.append({
                "severity": "info",
                "title": f"Largest subject gap: {sg['subject_code']}",
                "detail": f"{sg['best_class']} {sg['best_mean']}% vs {sg['worst_class']} {sg['worst_mean']}% ({sg['gap']} pts).",
            })

    return {
        "assessment": _a_dict(a),
        "classes": class_rows,
        "subjects": all_codes,
        "subject_gaps": subject_gaps,
        "insights": insights,
    }



# ---------------------------------------------------------------------
# Report form (school template renderer)
# ---------------------------------------------------------------------
def report_form(student_id):
    from apps.academics.models import Student, Result, ResultStatus
    from apps.core.models import Term

    student = Student.objects.get(id=student_id)
    scheme = _active_scheme()

    enrollment = (
        student.enrollments.filter(is_current=True)
        .select_related("teaching_group").first()
    )
    teaching_group = enrollment.teaching_group if enrollment else None
    class_name = teaching_group.name if teaching_group else ""

    assessments = list(Assessment.objects.all().order_by("date")[:3])

    results = (
        Result.objects.filter(student=student, status=ResultStatus.VALID)
        .select_related("assessment", "subject")
    )

    by_subject = {}
    for r in results:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        code = r.subject.code
        if code not in by_subject:
            by_subject[code] = {
                "code": code,
                "name": r.subject.name,
                "marks": {},
            }
        g = grade_for(scheme, pct) or {}
        by_subject[code]["marks"][str(r.assessment_id)] = {
            "raw": float(r.raw_mark),
            "pct": pct,
            "grade": g.get("grade", "-"),
            "points": float(g.get("points", 0)),
        }

    for code, row in by_subject.items():
        marks = list(row["marks"].values())
        if marks:
            avg_pct = round(statistics.mean([m["pct"] for m in marks]), 2)
            avg_pts = round(statistics.mean([m["points"] for m in marks]), 2)
            g = grade_for(scheme, avg_pct) or {}
            row["average"] = {
                "pct": avg_pct,
                "grade": g.get("grade", "-"),
                "points": avg_pts,
            }
        else:
            row["average"] = {"pct": 0, "grade": "-", "points": 0}

    assessment_columns = []
    for a in assessments:
        marks_a = []
        for row in by_subject.values():
            m = row["marks"].get(str(a.id))
            if m:
                marks_a.append(m)
        if marks_a:
            total_mark = round(sum(m["raw"] for m in marks_a), 2)
            avg_pct = round(statistics.mean([m["pct"] for m in marks_a]), 2)
            avg_pts = round(statistics.mean([m["points"] for m in marks_a]), 2)
            g = grade_for(scheme, avg_pct) or {}
            assessment_columns.append({
                "assessment_id": str(a.id),
                "name": a.name,
                "total_mark": total_mark,
                "avg_pct": avg_pct,
                "grade": g.get("grade", "-"),
                "points": avg_pts,
            })
        else:
            assessment_columns.append({
                "assessment_id": str(a.id),
                "name": a.name,
                "total_mark": 0,
                "avg_pct": 0,
                "grade": "-",
                "points": 0,
            })

    total_avg_pct = round(
        statistics.mean([c["avg_pct"] for c in assessment_columns]), 2
    ) if assessment_columns else 0
    total_avg_points = round(
        statistics.mean([c["points"] for c in assessment_columns]), 2
    ) if assessment_columns else 0

    perf_level = "—"
    if total_avg_pct >= 76: perf_level = "EE"
    elif total_avg_pct >= 60: perf_level = "ME"
    elif total_avg_pct >= 40: perf_level = "AE"
    elif total_avg_pct > 0: perf_level = "BE"

    rank = None
    class_size = None
    if teaching_group:
        peers = list(Student.objects.filter(
            enrollments__teaching_group=teaching_group,
            enrollments__is_current=True,
        ).distinct())
        assessment_ids = [a.id for a in assessments]
        peer_means = {}
        for p in peers:
            prs = Result.objects.filter(
                student=p, status=ResultStatus.VALID,
                assessment_id__in=assessment_ids,
            )
            pcts = [_pct(r.raw_mark, r.assessment.max_mark) for r in prs.select_related("assessment")]
            pcts = [x for x in pcts if x is not None]
            if pcts:
                peer_means[p.id] = statistics.mean(pcts)
        sorted_peers = sorted(peer_means.items(), key=lambda x: -x[1])
        for i, (pid, _) in enumerate(sorted_peers, start=1):
            if pid == student.id:
                rank = i
                break
        class_size = len(sorted_peers)

    if "Form 3" in class_name or "Form 4" in class_name:
        template = "kcse"
        subject_order = ["ENG", "KIS", "MAT", "BIO", "PHY", "CHEM",
                         "HIS", "CRE", "GEO", "AGR", "BUS", "COMP"]
    elif "Grade 8" in class_name or "Grade 7" in class_name or "Grade 9" in class_name:
        template = "cbe_junior"
        subject_order = ["ENG", "KIS", "MAT", "INTSCI", "PRETECH",
                         "HSC", "CRE", "SOCIAL", "CAS"]
    else:
        template = "cbe_secondary"
        subject_order = ["ENG", "KIS", "MAT", "EMCM", "CSL", "BIO", "PHY",
                         "CHEM", "GEO", "CRE", "AGR", "COMP", "BUS", "LIT", "ICT"]

    ordered = []
    seen = set()
    for code in subject_order:
        if code in by_subject:
            ordered.append(by_subject[code])
            seen.add(code)
    for code, row in by_subject.items():
        if code not in seen:
            ordered.append(row)

    current_term = Term.objects.filter(is_active=True).first()
    term_name = current_term.name if current_term else "Term 1"
    year_name = "2026"
    if current_term and hasattr(current_term, "academic_year") and current_term.academic_year:
        year_name = current_term.academic_year.name

    return {
        "student": {
            "id": str(student.id),
            "admission_number": student.admission_number,
            "name": student.full_name,
            "kcpe_mark": student.kcpe_mark,
            "class_name": class_name,
            "class_level": class_name.replace("E", "").replace("W", "").strip(),
        },
        "context": {
            "template": template,
            "term": term_name,
            "year": year_name,
            "assessment_columns": assessment_columns,
            "total_avg_pct": total_avg_pct,
            "total_avg_points": total_avg_points,
            "performance_level": perf_level,
            "rank": rank,
            "class_size": class_size,
        },
        "subjects": ordered,
        "school": {
            "name": "QUEEN OF APOSTLES SEMINARY, RUARAKA",
            "address": "P.O. BOX 65071-00618. NAIROBI. TEL: 0731615441/0724308879",
            "email": "queenofapostlessem@yahoo.com, qas@qas.ac.ke",
        },
    }



# ---------------------------------------------------------------------
# Configurable ranking engine (RoE §17-18)
# ---------------------------------------------------------------------
def _apply_tie_policy(scored, tie_policy):
    """
    scored: list of dicts with 'score' (already sorted desc).
    Returns the same list with 'rank' filled in.
    """
    prev_score = None
    prev_rank = 0
    dense_rank = 0
    for i, row in enumerate(scored, start=1):
        s = row["score"]
        if prev_score is not None and s == prev_score:
            if tie_policy == "ORDINAL":
                row["rank"] = i
            elif tie_policy == "DENSE":
                row["rank"] = prev_rank
            else:  # COMPETITION
                row["rank"] = prev_rank
        else:
            if tie_policy == "DENSE":
                dense_rank += 1
                row["rank"] = dense_rank
            else:
                row["rank"] = i
            prev_rank = row["rank"]
        prev_score = s
    return scored


def compute_ranking(rule_id, assessment_id=None, teaching_group_id=None,
                    persist=False, request=None, notes=""):
    """
    Apply the given rule to the student cohort and return the ranked list.

    scope:
      - if teaching_group_id is given -> CLASS scope
      - else if assessment_id given -> assessment-wide (SCHOOL)
      - else -> SCHOOL (all active students)

    If persist=True, a RankingRun row is created (audit trail).
    """
    from apps.academics.models import (
        RankingRule, RankingRun, StudentEnrollment, Student,
        Result, ResultStatus, Assessment as _A,
    )

    rule = RankingRule.objects.get(id=rule_id)

    # Determine student cohort
    qs = Student.objects.filter(is_active=True)
    scope_type = "SCHOOL"
    scope_label = "All students"
    scope_id = None

    if teaching_group_id:
        qs = qs.filter(
            enrollments__teaching_group_id=teaching_group_id,
            enrollments__is_current=True,
        ).distinct()
        scope_type = "CLASS"
        scope_id = teaching_group_id
        from apps.academics.models import TeachingGroup
        tg = TeachingGroup.objects.filter(id=teaching_group_id).first()
        scope_label = tg.name if tg else "Class"

    students = list(qs)

    # Get results (per-student aggregation)
    results_qs = Result.objects.filter(
        student__in=students, status=ResultStatus.VALID,
    ).select_related("assessment", "subject")

    if assessment_id:
        results_qs = results_qs.filter(assessment_id=assessment_id)

    if rule.method == "SUBJECT_COMBO" and rule.subject_codes:
        results_qs = results_qs.filter(subject__code__in=rule.subject_codes)

    scheme = _active_scheme()

    per_student = {}
    for r in results_qs:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        g = grade_for(scheme, pct) or {}
        entry = per_student.setdefault(r.student_id, {
            "total": 0.0,
            "pcts": [],
            "points": [],
            "subjects": set(),
        })
        entry["total"] += float(r.raw_mark)
        entry["pcts"].append(pct)
        entry["points"].append(float(g.get("points", 0)))
        entry["subjects"].add(r.subject.code)

    scored = []
    for s in students:
        agg = per_student.get(s.id)
        if not agg:
            continue
        n_subj = len(agg["subjects"])
        if n_subj < rule.min_subjects:
            continue
        mean_pct = round(statistics.mean(agg["pcts"]), 2) if agg["pcts"] else 0
        mean_pts = round(statistics.mean(agg["points"]), 2) if agg["points"] else 0
        total = round(agg["total"], 2)

        if rule.method == "TOTAL":
            score = total
        elif rule.method == "MEAN_POINTS":
            score = mean_pts
        elif rule.method == "SUBJECT_COMBO":
            score = mean_pct
        else:
            score = mean_pct

        scored.append({
            "student_id": str(s.id),
            "admission_number": s.admission_number,
            "name": s.full_name,
            "score": score,
            "total": total,
            "mean_pct": mean_pct,
            "mean_points": mean_pts,
            "subjects_count": n_subj,
            "grade": (grade_for(scheme, mean_pct) or {}).get("grade", "-"),
        })

    scored.sort(key=lambda r: -r["score"])
    scored = _apply_tie_policy(scored, rule.tie_policy)

    # Percentile
    n = len(scored)
    for row in scored:
        row["percentile"] = round(
            (n - row["rank"]) / (n - 1) * 100, 1
        ) if n > 1 else 100.0

    run_id = None
    if persist:
        run = RankingRun.objects.create(
            rule=rule,
            rule_snapshot=rule.to_snapshot(),
            assessment_id=assessment_id,
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
            entries=scored,
            student_count=n,
            notes=notes,
        )
        run_id = str(run.id)
        try:
            from apps.academics.audit_util import log_event as _log
            _log(
                request,
                action="CREATE",
                entity_type="RankingRun",
                entity_label=f"{rule.name} — {scope_label} ({n} students)",
                entity_id=run.id,
                meta={
                    "rule": rule.name,
                    "rule_version": rule.version,
                    "method": rule.method,
                    "tie_policy": rule.tie_policy,
                    "assessment_id": str(assessment_id) if assessment_id else None,
                    "scope": scope_label,
                },
            )
        except Exception:
            pass

    return {
        "rule": rule.to_snapshot(),
        "run_id": run_id,
        "scope_type": scope_type,
        "scope_label": scope_label,
        "assessment_id": str(assessment_id) if assessment_id else None,
        "count": n,
        "entries": scored,
    }



# ---------------------------------------------------------------------
# Class / stream comparison v2 — leaderboards + per-class detail
# ---------------------------------------------------------------------
def class_comparison_v2(assessment_id):
    from collections import defaultdict as _dd
    from apps.academics.models import (
        Student, StudentEnrollment, TeachingGroup,
    )

    a = Assessment.objects.get(id=assessment_id)
    scheme = _active_scheme()

    # ---------- full history (for improvement tracking) ----------
    hist = _dd(lambda: _dd(list))   # sid -> subject_code -> [(date, pct)]
    all_res = (
        Result.objects.filter(status=ResultStatus.VALID)
        .select_related("assessment", "subject")
    )
    for r in all_res:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        hist[r.student_id][r.subject.code].append((r.assessment.date, pct))

    # ---------- current assessment results ----------
    rows = (
        Result.objects.filter(assessment=a, status=ResultStatus.VALID)
        .select_related("student", "subject")
    )
    by_student_subj = _dd(dict)   # sid -> code -> {pct, name, sub_id}
    by_student_all = _dd(list)    # sid -> [pct,...]
    for r in rows:
        pct = _pct(r.raw_mark, a.max_mark)
        if pct is None:
            continue
        by_student_subj[r.student_id][r.subject.code] = {
            "pct": pct,
            "name": r.subject.name,
            "sub_id": str(r.subject.id),
        }
        by_student_all[r.student_id].append(pct)

    # ---------- enrollments ----------
    student_group = {}
    for e in StudentEnrollment.objects.filter(is_current=True).select_related("teaching_group"):
        student_group[e.student_id] = (e.teaching_group_id, e.teaching_group.name)

    students_by_id = {s.id: s for s in Student.objects.all()}

    # ---------- group into classes ----------
    groups = _dd(lambda: {
        "students": set(),
        "subject_data": _dd(list),   # code -> [(sid, pct)]
        "all_pcts": [],
    })
    for sid, subs in by_student_subj.items():
        g = student_group.get(sid)
        if not g:
            continue
        gid, gname = g
        bucket = groups[(gid, gname)]
        bucket["students"].add(sid)
        for code, d in subs.items():
            bucket["subject_data"][code].append((sid, d["pct"]))
            bucket["all_pcts"].append(d["pct"])

    # ---------- per-class rows ----------
    class_rows = []
    for (gid, gname), data in groups.items():
        pcts = data["all_pcts"]
        if not pcts:
            continue
        students_in = list(data["students"])
        student_means = []
        for sid in students_in:
            if by_student_all[sid]:
                student_means.append((sid, statistics.mean(by_student_all[sid])))
        best_student = None
        worst_student = None
        if student_means:
            bsid, bmean = max(student_means, key=lambda x: x[1])
            ws = min(student_means, key=lambda x: x[1])
            bs = students_by_id.get(bsid)
            ws_s = students_by_id.get(ws[0])
            if bs:
                best_student = {"name": bs.full_name, "admission_number": bs.admission_number, "mean": round(bmean, 2)}
            if ws_s:
                worst_student = {"name": ws_s.full_name, "admission_number": ws_s.admission_number, "mean": round(ws[1], 2)}

        subject_full = []
        for code, pairs in data["subject_data"].items():
            ps = [p for _, p in pairs]
            sub_name = ""
            # find subject name via a result row
            for r in rows:
                if r.subject.code == code:
                    sub_name = r.subject.name
                    break
            subject_full.append({
                "code": code,
                "name": sub_name or code,
                "mean": round(statistics.mean(ps), 2),
                "median": round(statistics.median(ps), 2),
                "std_dev": round(statistics.pstdev(ps), 2) if len(ps) > 1 else 0.0,
                "highest": round(max(ps), 2),
                "lowest": round(min(ps), 2),
                "count": len(ps),
                "grade_counts": _grade_counts(ps, scheme),
            })
        subject_full.sort(key=lambda x: -x["mean"])
        leading = subject_full[0] if subject_full else None
        trailing = subject_full[-1] if subject_full else None

        class_rows.append({
            "group_id": str(gid),
            "group_name": gname,
            "students": len(students_in),
            "overall_mean": round(statistics.mean(pcts), 2),
            "overall_median": round(statistics.median(pcts), 2),
            "overall_std_dev": round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0,
            "overall_pass_rate": round(
                sum(1 for p in pcts if p >= PASS_THRESHOLD) / len(pcts) * 100, 2
            ),
            "best_student": best_student,
            "worst_student": worst_student,
            "subject_means": {s["code"]: s["mean"] for s in subject_full},
            "subject_full": subject_full,
            "leading_subject": ({"code": leading["code"], "name": leading["name"], "mean": leading["mean"]} if leading else None),
            "trailing_subject": ({"code": trailing["code"], "name": trailing["name"], "mean": trailing["mean"]} if trailing else None),
        })

    class_rows.sort(key=lambda r: -r["overall_mean"])
    for i, r in enumerate(class_rows, start=1):
        r["rank"] = i

    all_codes = sorted({s["code"] for r in class_rows for s in r["subject_full"]})

    # ---------- subject gaps ----------
    subject_gaps = []
    for code in all_codes:
        pairs = [(r["group_name"], r["subject_means"].get(code)) for r in class_rows if code in r["subject_means"]]
        if len(pairs) < 2:
            continue
        pairs.sort(key=lambda x: -x[1])
        subject_gaps.append({
            "subject_code": code,
            "best_class": pairs[0][0],
            "best_mean": pairs[0][1],
            "worst_class": pairs[-1][0],
            "worst_mean": pairs[-1][1],
            "gap": round(pairs[0][1] - pairs[-1][1], 2),
        })
    subject_gaps.sort(key=lambda x: -x["gap"])

    # ---------- leaderboards ----------
    leaderboards = {"per_subject": []}
    for code in all_codes:
        subj_name = code
        for r in rows:
            if r.subject.code == code:
                subj_name = r.subject.name
                break

        by_class = []
        for cls in class_rows:
            if code not in cls["subject_means"]:
                continue
            gid = cls["group_id"]
            # students in class who sat this subject
            entries = []
            for sid, subs in by_student_subj.items():
                if str(student_group.get(sid, (None, None))[0]) != gid:
                    continue
                d = subs.get(code)
                if not d:
                    continue
                s = students_by_id.get(sid)
                if not s:
                    continue
                entries.append({
                    "student_id": str(sid),
                    "name": s.full_name,
                    "admission_number": s.admission_number,
                    "pct": d["pct"],
                })
            if not entries:
                continue
            entries.sort(key=lambda x: -x["pct"])
            best = entries[0]
            worst = entries[-1]

            # improvement/decline: first vs last assessment for this subject
            improved = []
            for sid, subs in by_student_subj.items():
                if str(student_group.get(sid, (None, None))[0]) != gid:
                    continue
                series = hist.get(sid, {}).get(code, [])
                if len(series) < 2:
                    continue
                series_sorted = sorted(series, key=lambda x: x[0])
                delta = round(series_sorted[-1][1] - series_sorted[0][1], 2)
                s = students_by_id.get(sid)
                if not s:
                    continue
                improved.append({
                    "student_id": str(sid),
                    "name": s.full_name,
                    "admission_number": s.admission_number,
                    "delta": delta,
                })
            most_improved = max(improved, key=lambda x: x["delta"]) if improved else None
            most_declined = min(improved, key=lambda x: x["delta"]) if improved else None
            # Suppress "no change at 0" improvements/declines
            if most_improved and most_improved["delta"] <= 0:
                most_improved = None
            if most_declined and most_declined["delta"] >= 0:
                most_declined = None

            by_class.append({
                "group_id": gid,
                "group_name": cls["group_name"],
                "best": {
                    "name": best["name"],
                    "admission_number": best["admission_number"],
                    "pct": best["pct"],
                },
                "worst": {
                    "name": worst["name"],
                    "admission_number": worst["admission_number"],
                    "pct": worst["pct"],
                },
                "most_improved": most_improved,
                "most_declined": most_declined,
            })

        leaderboards["per_subject"].append({
            "subject_code": code,
            "subject_name": subj_name,
            "by_class": by_class,
        })

    # ---------- insights ----------
    insights = []
    if len(class_rows) >= 2:
        best = class_rows[0]
        worst = class_rows[-1]
        gap = round(best["overall_mean"] - worst["overall_mean"], 2)
        insights.append({
            "severity": "positive",
            "title": f"{best['group_name']} leads",
            "detail": f"Mean {best['overall_mean']}% vs {worst['group_name']} {worst['overall_mean']}% — {gap} pt gap.",
        })
        if gap > 5:
            insights.append({
                "severity": "warning",
                "title": "Wide inter-class gap",
                "detail": f"{gap} points between top and bottom class. Prioritise {worst['group_name']}.",
            })
        elif gap < 2:
            insights.append({
                "severity": "info",
                "title": "Classes perform comparably",
                "detail": f"Only {gap} points separate the top and bottom class.",
            })
        if subject_gaps:
            sg = subject_gaps[0]
            insights.append({
                "severity": "info",
                "title": f"Largest subject gap: {sg['subject_code']}",
                "detail": f"{sg['best_class']} {sg['best_mean']}% vs {sg['worst_class']} {sg['worst_mean']}% ({sg['gap']} pts).",
            })
        for cls in class_rows:
            if cls["leading_subject"] and cls["trailing_subject"]:
                insights.append({
                    "severity": "info",
                    "title": f"{cls['group_name']} — strongest {cls['leading_subject']['code']}",
                    "detail": f"Mean {cls['leading_subject']['mean']}%. Weakest: {cls['trailing_subject']['code']} at {cls['trailing_subject']['mean']}%.",
                })

    # ---------- school-wide leaderboard per subject ----------
    school_wide = []
    for code in all_codes:
        subj_name = code
        for r in rows:
            if r.subject.code == code:
                subj_name = r.subject.name
                break
        entries = []
        improved = []
        for sid, subs in by_student_subj.items():
            d = subs.get(code)
            if not d:
                continue
            s = students_by_id.get(sid)
            if not s:
                continue
            entries.append({
                "student_id": str(sid),
                "name": s.full_name,
                "admission_number": s.admission_number,
                "pct": d["pct"],
            })
            series = hist.get(sid, {}).get(code, [])
            if len(series) >= 2:
                ss = sorted(series, key=lambda x: x[0])
                delta = round(ss[-1][1] - ss[0][1], 2)
                improved.append({
                    "student_id": str(sid),
                    "name": s.full_name,
                    "admission_number": s.admission_number,
                    "delta": delta,
                })
        if not entries:
            continue
        entries.sort(key=lambda x: -x["pct"])
        mi = max(improved, key=lambda x: x["delta"]) if improved else None
        md = min(improved, key=lambda x: x["delta"]) if improved else None
        if mi and mi["delta"] <= 0: mi = None
        if md and md["delta"] >= 0: md = None
        school_wide.append({
            "subject_code": code,
            "subject_name": subj_name,
            "best": {"name": entries[0]["name"], "admission_number": entries[0]["admission_number"], "pct": entries[0]["pct"]},
            "worst": {"name": entries[-1]["name"], "admission_number": entries[-1]["admission_number"], "pct": entries[-1]["pct"]},
            "most_improved": mi,
            "most_declined": md,
            "count": len(entries),
        })
    leaderboards["school_wide"] = school_wide
    # ---------- school-wide overall (all subjects combined) ----------
    overall_scored = []
    overall_improved = []
    for sid, pcts in by_student_all.items():
        if not pcts:
            continue
        s = students_by_id.get(sid)
        if not s:
            continue
        overall_scored.append({
            "student_id": str(sid),
            "name": s.full_name,
            "admission_number": s.admission_number,
            "mean": round(statistics.mean(pcts), 2),
            "subjects_count": len(by_student_subj.get(sid, {})),
        })
        firsts, lasts = [], []
        for code, series in hist.get(sid, {}).items():
            if len(series) >= 2:
                ss = sorted(series, key=lambda x: x[0])
                firsts.append(ss[0][1])
                lasts.append(ss[-1][1])
        if firsts:
            overall_improved.append({
                "student_id": str(sid),
                "name": s.full_name,
                "admission_number": s.admission_number,
                "delta": round(statistics.mean(lasts) - statistics.mean(firsts), 2),
            })

    overall_scored.sort(key=lambda x: -x["mean"])
    overall_improved.sort(key=lambda x: -x["delta"])

    school_wide_overall = None
    if overall_scored:
        mi = overall_improved[0] if overall_improved and overall_improved[0]["delta"] > 0 else None
        md = overall_improved[-1] if overall_improved and overall_improved[-1]["delta"] < 0 else None
        school_wide_overall = {
            "best": overall_scored[0],
            "worst": overall_scored[-1],
            "most_improved": mi,
            "most_declined": md,
            "count": len(overall_scored),
        }
    leaderboards["overall"] = school_wide_overall

    # ---------- per-class overall (all subjects combined) ----------
    per_class_overall = []
    for cls in class_rows:
        gid = cls["group_id"]
        class_students = [sid for sid, (g, _) in student_group.items() if str(g) == gid]
        c_scored = []
        c_improved = []
        for sid in class_students:
            pcts = by_student_all.get(sid, [])
            if not pcts:
                continue
            s = students_by_id.get(sid)
            if not s:
                continue
            c_scored.append({
                "student_id": str(sid),
                "name": s.full_name,
                "admission_number": s.admission_number,
                "mean": round(statistics.mean(pcts), 2),
            })
            firsts, lasts = [], []
            for code, series in hist.get(sid, {}).items():
                if len(series) >= 2:
                    ss = sorted(series, key=lambda x: x[0])
                    firsts.append(ss[0][1])
                    lasts.append(ss[-1][1])
            if firsts:
                c_improved.append({
                    "student_id": str(sid),
                    "name": s.full_name,
                    "admission_number": s.admission_number,
                    "delta": round(statistics.mean(lasts) - statistics.mean(firsts), 2),
                })
        c_scored.sort(key=lambda x: -x["mean"])
        c_improved.sort(key=lambda x: -x["delta"])
        per_class_overall.append({
            "group_id": gid,
            "group_name": cls["group_name"],
            "best": c_scored[0] if c_scored else None,
            "worst": c_scored[-1] if c_scored else None,
            "most_improved": c_improved[0] if c_improved and c_improved[0]["delta"] > 0 else None,
            "most_declined": c_improved[-1] if c_improved and c_improved[-1]["delta"] < 0 else None,
            "count": len(c_scored),
        })
    leaderboards["overall_per_class"] = per_class_overall
    return {
        "assessment": _a_dict(a),
        "classes": class_rows,
        "subjects": all_codes,
        "subject_gaps": subject_gaps,
        "leaderboards": leaderboards,
        "insights": insights,
    }



# ---------------------------------------------------------------------
# Stream summary — printable class + per-student + per-subject report
# ---------------------------------------------------------------------
def stream_summary(assessment_id, teaching_group_id):
    """Complete analysis packet for one stream (class)."""
    from collections import defaultdict as _dd
    from apps.academics.models import StudentEnrollment

    a = Assessment.objects.get(id=assessment_id)
    scheme = _active_scheme()

    enrollments = list(
        StudentEnrollment.objects.filter(
            teaching_group_id=teaching_group_id, is_current=True,
        ).select_related("student", "teaching_group")
    )
    if not enrollments:
        return {
            "assessment": _a_dict(a), "stream": None,
            "class_stats": None, "students": [], "subjects": [],
            "leaderboards": {},
        }
    stream = enrollments[0].teaching_group
    students = [e.student for e in enrollments]
    student_ids = {s.id for s in students}

    rows = list(
        Result.objects.filter(
            assessment=a, status=ResultStatus.VALID, student_id__in=student_ids,
        ).select_related("student", "subject")
    )

    all_results = list(
        Result.objects.filter(
            status=ResultStatus.VALID, student_id__in=student_ids,
        ).select_related("assessment", "subject")
    )

    cur_by_student = _dd(dict)
    cur_by_subject = _dd(list)
    for r in rows:
        pct = _pct(r.raw_mark, a.max_mark)
        if pct is None:
            continue
        g = grade_for(scheme, pct) or {}
        cur_by_student[r.student_id][r.subject.code] = {
            "pct": pct, "grade": g.get("grade", "-"), "name": r.subject.name,
        }
        cur_by_subject[r.subject.code].append((r.student_id, pct))

    hist = _dd(lambda: _dd(list))
    for r in all_results:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        hist[r.student_id][r.subject.code].append((r.assessment.date, pct))

    # Subject means
    subject_means = {}
    subject_details = {}
    for code, pairs in cur_by_subject.items():
        pcts = [p for _, p in pairs]
        if not pcts:
            continue
        nm = code
        for sid, _ in pairs:
            if code in cur_by_student.get(sid, {}):
                nm = cur_by_student[sid][code]["name"]
                break
        subject_means[code] = round(statistics.mean(pcts), 2)
        passes = sum(1 for p in pcts if p >= PASS_THRESHOLD)
        subject_details[code] = {
            "code": code, "name": nm,
            "candidates": len(pcts),
            "mean": round(statistics.mean(pcts), 2),
            "median": round(statistics.median(pcts), 2),
            "std_dev": round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0,
            "highest": round(max(pcts), 2),
            "lowest": round(min(pcts), 2),
            "pass_count": passes,
            "pass_rate": round(passes / len(pcts) * 100, 2),
        }

    # Per-student summary
    summaries = []
    for s in students:
        subs = cur_by_student.get(s.id, {})
        if not subs:
            continue
        pcts = [v["pct"] for v in subs.values()]
        mean = round(statistics.mean(pcts), 2)
        std = round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0
        g = grade_for(scheme, mean) or {}

        subj_rows = []
        for code, d in subs.items():
            cm = subject_means.get(code)
            subj_rows.append({
                "code": code, "name": d["name"],
                "pct": d["pct"], "grade": d["grade"],
                "class_mean": cm,
                "vs_class": round(d["pct"] - cm, 2) if cm is not None else None,
            })
        subj_rows.sort(key=lambda r: -r["pct"])

        firsts, lasts = [], []
        for code, series in hist.get(s.id, {}).items():
            if len(series) >= 2:
                ss = sorted(series, key=lambda x: x[0])
                firsts.append(ss[0][1]); lasts.append(ss[-1][1])
        delta = round(statistics.mean(lasts) - statistics.mean(firsts), 2) if firsts else 0.0
        trend = "improving" if delta > 3 else "declining" if delta < -3 else "stable"

        summaries.append({
            "id": str(s.id),
            "admission_number": s.admission_number,
            "name": s.full_name,
            "mean": mean, "std": std, "grade": g.get("grade", "-"),
            "subjects_count": len(subj_rows),
            "strengths": [r["code"] for r in subj_rows[:3]],
            "weaknesses": [r["code"] for r in subj_rows[-3:]] if len(subj_rows) > 3 else [],
            "subjects": subj_rows,
            "radar": [
                {"subject": r["code"], "student": r["pct"], "class": r["class_mean"] or 0}
                for r in subj_rows
            ],
            "trend": trend, "delta": delta,
        })

    summaries.sort(key=lambda r: -r["mean"])
    prev_score, prev_rank = None, None
    for i, r in enumerate(summaries, start=1):
        if prev_score is not None and r["mean"] == prev_score:
            r["rank"] = prev_rank
        else:
            r["rank"] = i
        prev_score, prev_rank = r["mean"], r["rank"]

    # Per-subject leaders / improvers / decliners / stable
    for code, det in subject_details.items():
        pairs = cur_by_subject.get(code, [])
        if not pairs:
            continue
        pairs_sorted = sorted(pairs, key=lambda x: -x[1])
        top_sid = pairs_sorted[0][0]
        worst_sid = pairs_sorted[-1][0]
        ts = next((s for s in students if s.id == top_sid), None)
        ws = next((s for s in students if s.id == worst_sid), None)
        det["top_student"] = {
            "id": str(top_sid),
            "name": ts.full_name if ts else "?",
            "admission_number": ts.admission_number if ts else "?",
            "pct": pairs_sorted[0][1],
        }
        det["weakest_student"] = {
            "id": str(worst_sid),
            "name": ws.full_name if ws else "?",
            "admission_number": ws.admission_number if ws else "?",
            "pct": pairs_sorted[-1][1],
        }
        deltas = []
        stables = []
        for sid, _ in pairs:
            series = hist.get(sid, {}).get(code, [])
            if len(series) >= 2:
                ss = sorted(series, key=lambda x: x[0])
                d = round(ss[-1][1] - ss[0][1], 2)
                st = next((x for x in students if x.id == sid), None)
                if st:
                    deltas.append({
                        "id": str(sid), "name": st.full_name,
                        "admission_number": st.admission_number, "delta": d,
                    })
                    pp = [x[1] for x in ss]
                    stables.append({
                        "id": str(sid), "name": st.full_name,
                        "admission_number": st.admission_number,
                        "std": round(statistics.pstdev(pp), 2) if len(pp) > 1 else 0.0,
                    })
        deltas.sort(key=lambda x: -x["delta"])
        stables.sort(key=lambda x: x["std"])
        det["most_improved"] = deltas[0] if deltas and deltas[0]["delta"] > 0 else None
        det["most_declined"] = deltas[-1] if deltas and deltas[-1]["delta"] < 0 else None
        det["most_stable"] = stables[0] if stables else None

    subject_list = list(subject_details.values())
    subject_list.sort(key=lambda r: -r["mean"])

    all_pcts = [v["pct"] for sid, subs in cur_by_student.items() for v in subs.values()]
    class_stats = None
    if all_pcts:
        passes = sum(1 for p in all_pcts if p >= PASS_THRESHOLD)
        class_stats = {
            "mean": round(statistics.mean(all_pcts), 2),
            "median": round(statistics.median(all_pcts), 2),
            "std_dev": round(statistics.pstdev(all_pcts), 2) if len(all_pcts) > 1 else 0.0,
            "highest": round(max(all_pcts), 2),
            "lowest": round(min(all_pcts), 2),
            "pass_rate": round(passes / len(all_pcts) * 100, 2),
            "count": len(all_pcts),
            "student_count": len([s for s in students if cur_by_student.get(s.id)]),
        }

    improvers = sorted([s for s in summaries if s["trend"] == "improving"], key=lambda s: -s["delta"])
    decliners = sorted([s for s in summaries if s["trend"] == "declining"], key=lambda s: s["delta"])
    consistent = sorted([s for s in summaries if s["subjects_count"] >= 3], key=lambda s: s["std"])

    leaderboards = {
        "best_overall": summaries[:3],
        "most_improved": improvers[:3],
        "most_declined": decliners[:3],
        "most_consistent": consistent[:3],
        "best_per_subject": [
            {"subject": s["code"], "subject_name": s["name"], "student": s.get("top_student")}
            for s in subject_list
        ],
    }

    return {
        "assessment": _a_dict(a),
        "stream": {"id": str(stream.id), "name": stream.name},
        "class_stats": class_stats,
        "students": summaries,
        "subjects": subject_list,
        "leaderboards": leaderboards,
    }



# ---------------------------------------------------------------------
# Stream trend — last N assessments at class / student / subject level
# ---------------------------------------------------------------------
def stream_trend(teaching_group_id, assessment_limit=3):
    from collections import defaultdict as _dd
    from apps.academics.models import StudentEnrollment

    enrollments = list(
        StudentEnrollment.objects.filter(
            teaching_group_id=teaching_group_id, is_current=True,
        ).select_related("student")
    )
    empty = {"assessments": [], "class_trend": [], "student_trends": {}, "subject_trends": {}}
    if not enrollments:
        return empty
    student_ids = [e.student_id for e in enrollments]

    assessments = list(Assessment.objects.order_by("-date")[:assessment_limit])
    assessments.reverse()

    results = Result.objects.filter(
        assessment__in=assessments, status=ResultStatus.VALID,
        student_id__in=student_ids,
    ).select_related("assessment", "subject")

    by_a_student = _dd(lambda: _dd(list))
    by_a_subject = _dd(lambda: _dd(list))
    by_a_all = _dd(list)

    for r in results:
        pct = _pct(r.raw_mark, r.assessment.max_mark)
        if pct is None:
            continue
        aid = r.assessment.id
        by_a_student[aid][r.student_id].append(pct)
        by_a_subject[aid][r.subject.code].append(pct)
        by_a_all[aid].append(pct)

    assessment_cols = [
        {"id": str(a.id), "name": a.name, "date": a.date.isoformat()} for a in assessments
    ]

    class_trend = []
    for a in assessments:
        pcts = by_a_all.get(a.id, [])
        if not pcts:
            class_trend.append({
                "assessment_id": str(a.id), "name": a.name, "date": a.date.isoformat(),
                "mean": 0, "pass_rate": 0, "count": 0,
            })
            continue
        passes = sum(1 for p in pcts if p >= PASS_THRESHOLD)
        class_trend.append({
            "assessment_id": str(a.id), "name": a.name, "date": a.date.isoformat(),
            "mean": round(statistics.mean(pcts), 2),
            "pass_rate": round(passes / len(pcts) * 100, 2),
            "count": len(pcts),
        })

    student_trends = {}
    for sid in student_ids:
        rows = []
        for a in assessments:
            pcts = by_a_student[a.id].get(sid, [])
            if pcts:
                rows.append({
                    "assessment_id": str(a.id), "name": a.name, "date": a.date.isoformat(),
                    "mean": round(statistics.mean(pcts), 2),
                })
        if rows:
            delta = round(rows[-1]["mean"] - rows[0]["mean"], 2) if len(rows) >= 2 else 0.0
            trend = "improving" if delta > 3 else "declining" if delta < -3 else "stable"
            student_trends[str(sid)] = {"points": rows, "delta": delta, "trend": trend}

    subject_trends = {}
    for a in assessments:
        for code, pcts in by_a_subject[a.id].items():
            subject_trends.setdefault(code, []).append({
                "assessment_id": str(a.id), "name": a.name, "date": a.date.isoformat(),
                "mean": round(statistics.mean(pcts), 2),
            })
    for code, rows in subject_trends.items():
        if len(rows) >= 2:
            delta = round(rows[-1]["mean"] - rows[0]["mean"], 2)
            trend = "improving" if delta > 3 else "declining" if delta < -3 else "stable"
        else:
            delta, trend = 0.0, "stable"
        subject_trends[code] = {"points": rows, "delta": delta, "trend": trend}

    return {
        "assessments": assessment_cols,
        "class_trend": class_trend,
        "student_trends": student_trends,
        "subject_trends": subject_trends,
    }
