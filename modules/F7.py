F7
"""F7 多條件最佳課表搜尋模組。

介面：
validate_search_request(...) -> list[str]
score_schedule(selected_courses, preferences=None, weights=None) -> dict
search_best_schedules(...) -> dict
"""

from copy import deepcopy

try:
    from .scheduling import PERIODS, project_activities
    from .timetable import DAYS, create_empty_timetable, day_to_index, period_to_index
    from .validation import positive_integer
except ImportError:
    from scheduling import PERIODS, project_activities
    from timetable import DAYS, create_empty_timetable, day_to_index, period_to_index
    from validation import positive_integer

DEFAULT_WEIGHTS = {
    "fewer_days": 2.0,        # 減少每週到校天數
    "fewer_gaps": 2.0,        # 減少空堂數
    "avoid_early": 1.5,       # 避免早八（第 1 節）課程
    "concentration": 1.5,     # 集中上課時段（降低單日跨度分散）
    "preferred_courses": 3.0, # 提高偏好課程選課比例
}


def _result(data, errors=()):
    return {"ok": not errors, "data": data, "errors": list(errors)}


def _normalize_slot(slot):
    if not isinstance(slot, (list, tuple)) or len(slot) != 2:
        return None
    day, period = slot
    if day_to_index(day) is None or period_to_index(period) is None:
        return None
    return (day, period)


def validate_search_request(
    data,
    required_course_ids=None,
    candidate_course_ids=None,
    min_credits=0,
    max_credits=None,
    forbidden_slots=None,
    preferences=None,
    weights=None,
    student_id=None,
):
    """驗證 F7 搜尋輸入與限制條件；回傳錯誤訊息清單（空清單代表合法）。"""
    errors = []
    if not isinstance(data, dict):
        return ["系統資料須為字典。"]

    for key in ("courses", "enrollments"):
        rows = data.get(key)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            errors.append(f"{key} 必須為物件清單。")
    if errors:
        return errors

    courses_by_id = {c.get("course_id"): c for c in data["courses"] if isinstance(c.get("course_id"), str)}
    if len(courses_by_id) != len(data["courses"]):
        errors.append("課程資料存在空值或重複的 course_id。")

    if student_id is not None:
        students = data.get("students")
        if not isinstance(students, list):
            errors.append("students 必須為物件清單。")
        elif not any(isinstance(s, dict) and s.get("student_id") == student_id for s in students):
            errors.append(f"學生不存在：{student_id}")

    req_ids = [] if required_course_ids is None else list(required_course_ids)
    cand_ids = [] if candidate_course_ids is None else list(candidate_course_ids)
    if not isinstance(req_ids, list) or any(not isinstance(cid, str) or not cid.strip() for cid in req_ids):
        errors.append("required_course_ids 須為非空字串課程代號清單。")
    if not isinstance(cand_ids, list) or any(not isinstance(cid, str) or not cid.strip() for cid in cand_ids):
        errors.append("candidate_course_ids 須為非空字串課程代號清單。")

    if not errors:
        for cid in req_ids:
            if cid not in courses_by_id:
                errors.append(f"必修課程不存在：{cid}")
        for cid in cand_ids:
            if cid not in courses_by_id:
                errors.append(f"候選選修課程不存在：{cid}")

    if type(min_credits) is not int or min_credits < 0:
        errors.append("min_credits 須為非負整數。")
    if max_credits is not None and not positive_integer(max_credits):
        errors.append("max_credits 須為正整數。")
    if (
        type(min_credits) is int
        and min_credits >= 0
        and max_credits is not None
        and positive_integer(max_credits)
        and min_credits > max_credits
    ):
        errors.append(f"最低學分（{min_credits}）不可大於最高學分（{max_credits}）。")

    if forbidden_slots is not None:
        if not isinstance(forbidden_slots, (list, set, tuple)):
            errors.append("forbidden_slots 須為時段集合或清單。")
        else:
            for slot in forbidden_slots:
                if _normalize_slot(slot) is None:
                    errors.append(f"禁止上課時段格式或數值無效：{slot}")

    if preferences is not None:
        if not isinstance(preferences, dict):
            errors.append("preferences 須為字典。")
        else:
            pref_cids = preferences.get("preferred_course_ids")
            if pref_cids is not None:
                if not isinstance(pref_cids, (list, set, tuple)) or any(
                    not isinstance(cid, str) or cid not in courses_by_id for cid in pref_cids
                ):
                    errors.append("preferences.preferred_course_ids 含有無效或不存在的課程代號。")
            early_periods = preferences.get("early_periods")
            if early_periods is not None:
                if not isinstance(early_periods, (list, set, tuple)) or any(
                    period_to_index(p) is None for p in early_periods
                ):
                    errors.append("preferences.early_periods 含有無效節次。")

    if weights is not None:
        if not isinstance(weights, dict):
            errors.append("weights 須為字典。")
        else:
            unknown = set(weights) - set(DEFAULT_WEIGHTS)
            if unknown:
                errors.append(f"不支援的權重鍵值：{sorted(unknown)}")
            for k, v in weights.items():
                if type(v) not in (int, float) or v < 0:
                    errors.append(f"權重 {k} 須為非負數值。")

    return errors


def score_schedule(selected_courses, preferences=None, weights=None):
    """計算單一可行課表的偏好子指標與加權總分（0.0 ~ 100.0）。"""
    prefs = preferences or {}
    active_weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    early_set = set(prefs.get("early_periods") or ("1",))
    pref_course_set = set(prefs.get("preferred_course_ids") or ())

    occupied_slots = set()
    day_rows = {d: [] for d in range(1, DAYS + 1)}
    early_slots_count = 0
    selected_ids = set()

    for course in selected_courses:
        selected_ids.add(course["course_id"])
        for slot in course.get("time_slots", []):
            norm = _normalize_slot(slot)
            if norm is None:
                continue
            day, period = norm
            if norm in occupied_slots:
                continue
            occupied_slots.add(norm)
            r_idx = period_to_index(period)
            day_rows[day].append(r_idx)
            if period in early_set:
                early_slots_count += 1

    active_days = [d for d, rows in day_rows.items() if rows]
    days_attended = len(active_days)
    total_periods = len(occupied_slots)

    total_gaps = 0
    total_span = 0
    for d in active_days:
        rows = sorted(day_rows[d])
        span = rows[-1] - rows[0] + 1
        total_span += span
        gaps = sum(1 for r in range(rows[0], rows[-1] + 1) if r not in set(rows))
        total_gaps += gaps

    # 各偏好子分數皆正規化至 [0.0, 1.0]
    fewer_days_score = 1.0 if days_attended == 0 else max(0.0, 1.0 - (days_attended - 1) / (DAYS - 1))
    fewer_gaps_score = 1.0 / (1.0 + total_gaps)
    avoid_early_score = 1.0 / (1.0 + early_slots_count)
    concentration_score = 1.0 if total_span == 0 else total_periods / total_span

    if pref_course_set:
        preferred_courses_score = len(selected_ids & pref_course_set) / len(pref_course_set)
    else:
        preferred_courses_score = 1.0

    metrics = {
        "fewer_days": round(fewer_days_score, 4),
        "fewer_gaps": round(fewer_gaps_score, 4),
        "avoid_early": round(avoid_early_score, 4),
        "concentration": round(concentration_score, 4),
        "preferred_courses": round(preferred_courses_score, 4),
    }
    stats = {
        "days_attended": days_attended,
        "total_periods": total_periods,
        "gap_periods": total_gaps,
        "early_periods_count": early_slots_count,
        "preferred_matched": len(selected_ids & pref_course_set),
        "preferred_total": len(pref_course_set),
    }

    weight_sum = sum(active_weights.values())
    if weight_sum <= 0:
        weighted_score = 0.0
    else:
        weighted_score = (
            sum(active_weights[k] * metrics[k] for k in DEFAULT_WEIGHTS) / weight_sum
        ) * 100.0

    return {
        "score": round(weighted_score, 2),
        "metrics": metrics,
        "stats": stats,
    }


def _course_slots_set(course):
    slots = set()
    for s in course.get("time_slots", []):
        norm = _normalize_slot(s)
        if norm is not None:
            slots.add(norm)
    return slots


def search_best_schedules(
    data,
    required_course_ids=None,
    candidate_course_ids=None,
    min_credits=0,
    max_credits=None,
    forbidden_slots=None,
    preferences=None,
    weights=None,
    student_id=None,
    period_times=None,
    week_start=None,
    limit=None,
):
    """搜尋所有符合必要條件的可行課表，並依自訂評分函式由高到低排序。

    回傳標準格式 {"ok": bool, "data": dict | None, "errors": list[str]}。
    """
    errors = validate_search_request(
        data=data,
        required_course_ids=required_course_ids,
        candidate_course_ids=candidate_course_ids,
        min_credits=min_credits,
        max_credits=max_credits,
        forbidden_slots=forbidden_slots,
        preferences=preferences,
        weights=weights,
        student_id=student_id,
    )
    if errors:
        return _result(None, errors)

    # 若未指定 max_credits 且有指定 student_id，預設採用該生 max_credits
    effective_max_credits = max_credits
    if effective_max_credits is None and student_id is not None:
        student = next(s for s in data["students"] if s["student_id"] == student_id)
        effective_max_credits = student["max_credits"]

    blocked_slots = set()
    if forbidden_slots:
        for slot in forbidden_slots:
            norm = _normalize_slot(slot)
            if norm is not None:
                blocked_slots.add(norm)

    # 若有 student_id 與排程活動，將學生參與的活動時段視為不可排課時段
    activities = data.get("activities") or []
    if student_id is not None and activities:
        projected_acts, act_errors = project_activities(
            activities, period_times=period_times, week_start=week_start, require_week=False
        )
        if act_errors:
            return _result(None, act_errors)
        for act in projected_acts:
            if student_id in act.get("participant_ids", []):
                for d, p in act.get("time_slots", []):
                    blocked_slots.add((d, p))

    courses_by_id = {c["course_id"]: c for c in data["courses"]}
    enrollments = data["enrollments"]

    # 計算各課程剩餘名額（排除已額滿課程）
    enrolled_counts = {}
    for e in enrollments:
        cid = e.get("course_id")
        enrolled_counts[cid] = enrolled_counts.get(cid, 0) + 1

    def is_course_available(course):
        cid = course["course_id"]
        remaining = course["capacity"] - enrolled_counts.get(cid, 0)
        if remaining <= 0:
            return False, f"{cid}（{course['name']}）已額滿"
        slots = _course_slots_set(course)
        hit_forbidden = sorted(slots & blocked_slots)
        if hit_forbidden:
            return False, f"{cid}（{course['name']}）位於禁止時段 {hit_forbidden}"
        return True, None

    req_unique = list(dict.fromkeys(required_course_ids or []))
    cand_unique = [
        cid for cid in dict.fromkeys(candidate_course_ids or []) if cid not in set(req_unique)
    ]

    # 預先檢查必修課是否可用與互衝
    req_courses = []
    req_slots = set()
    req_credits = 0
    for cid in req_unique:
        course = courses_by_id[cid]
        ok, reason = is_course_available(course)
        if not ok:
            return _result(
                {"schedules": [], "total_feasible": 0, "evaluated_combinations": 0},
                [f"必修課無法納入：{reason}"],
            )
        c_slots = _course_slots_set(course)
        if req_slots & c_slots:
            overlap = sorted(req_slots & c_slots)
            return _result(
                {"schedules": [], "total_feasible": 0, "evaluated_combinations": 0},
                [f"必修課之間存在衝堂（{overlap}），無可行課表。"],
            )
        req_slots |= c_slots
        req_credits += course["credits"]
        req_courses.append(course)

    if effective_max_credits is not None and req_credits > effective_max_credits:
        return _result(
            {"schedules": [], "total_feasible": 0, "evaluated_combinations": 0},
            [f"必修課總學分（{req_credits}）已超過學分上限（{effective_max_credits}）。"],
        )

    # 篩選可用的候選選修課（排除額滿、禁止時段、或直接與必修課衝堂者）
    valid_candidates = []
    for cid in cand_unique:
        course = courses_by_id[cid]
        ok, _ = is_course_available(course)
        if not ok:
            continue
        c_slots = _course_slots_set(course)
        if req_slots & c_slots:
            continue
        if effective_max_credits is not None and req_credits + course["credits"] > effective_max_credits:
            continue
        valid_candidates.append((course, c_slots))

    feasible_solutions = []
    evaluated = 0

    def backtrack(idx, chosen_electives, used_slots, current_credits):
        nonlocal evaluated
        if idx == len(valid_candidates):
            evaluated += 1
            if current_credits >= min_credits and (
                effective_max_credits is None or current_credits <= effective_max_credits
            ):
                full_selection = req_courses + chosen_electives
                scoring = score_schedule(full_selection, preferences=preferences, weights=weights)
                feasible_solutions.append({
                    "course_ids": [c["course_id"] for c in full_selection],
                    "courses": deepcopy(full_selection),
                    "total_credits": current_credits,
                    "score": scoring["score"],
                    "metrics": scoring["metrics"],
                    "stats": scoring["stats"],
                })
            return

        course, c_slots = valid_candidates[idx]
        next_credits = current_credits + course["credits"]

        # 分支 1：選修此門候選課（需不衝堂且不超上限）
        can_take = not (used_slots & c_slots) and (
            effective_max_credits is None or next_credits <= effective_max_credits
        )
        if can_take:
            backtrack(
                idx + 1,
                chosen_electives + [course],
                used_slots | c_slots,
                next_credits,
            )

        # 分支 2：不選修此門候選課（剪枝：若剩餘最大可能學分仍小於 min_credits 可提前停止）
        remaining_max_credits = sum(c["credits"] for c, _ in valid_candidates[idx + 1 :])
        if current_credits + remaining_max_credits >= min_credits:
            backtrack(idx + 1, chosen_electives, used_slots, current_credits)

    backtrack(0, [], set(req_slots), req_credits)

    # 依總分由高到低排序；同分時以較高學分、較少衝堂/較字典序代號穩定排序
    feasible_solutions.sort(
        key=lambda item: (-item["score"], -item["total_credits"], tuple(item["course_ids"]))
    )

    total_feasible = len(feasible_solutions)
    ranked = feasible_solutions[:limit] if isinstance(limit, int) and limit >= 0 else feasible_solutions

    return _result({
        "schedules": ranked,
        "total_feasible": total_feasible,
        "evaluated_combinations": evaluated,
        "applied_credit_bounds": {
            "min_credits": min_credits,
            "max_credits": effective_max_credits,
        },
    })


def render_weekly_grid(selected_courses):
    """將選定課程轉為 12 節 x 7 天二維課表矩陣（與 F3 格式一致）。"""
    grid = create_empty_timetable()
    for course in selected_courses:
        for slot in course.get("time_slots", []):
            norm = _normalize_slot(slot)
            if norm is None:
                continue
            day, period = norm
            r = period_to_index(period)
            c = day_to_index(day)
            grid[r][c] = {
                "kind": "course",
                "id": course["course_id"],
                "name": course["name"],
            }
    return grid


if __name__ == "__main__":
    import json
    from pathlib import Path

    base = Path(__file__).parent
    sample_data = {
        "classrooms": json.loads((base / "classrooms.json").read_text(encoding="utf-8")),
        "courses": json.loads((base / "courses.json").read_text(encoding="utf-8")),
        "enrollments": json.loads((base / "enrollments.json").read_text(encoding="utf-8")),
        "students": json.loads((base / "students.json").read_text(encoding="utf-8")),
        "activities": [],
    }

    res = search_best_schedules(
        data=sample_data,
        required_course_ids=["CS101", "CS102"], # 必修 6 學分
        candidate_course_ids=["CS103", "CS104", "CS109", "CS111", "CS112", "CS114"],
        min_credits=9,
        max_credits=15,
        forbidden_slots=[[1, "1"], [5, "7"], [5, "8"]],
        preferences={
            "preferred_course_ids": ["CS109", "CS112", "CS114"],
            "early_periods": ["1"],
        },
        weights={
            "fewer_days": 2.5,
            "fewer_gaps": 2.0,
            "avoid_early": 2.0,
            "concentration": 1.5,
            "preferred_courses": 3.0,
        },
        student_id="S001",
        limit=5,
    )
    print("ok:", res["ok"], "errors:", res["errors"])
    if res["ok"]:
        print("可行課表總數:", res["data"]["total_feasible"])
        for rank, item in enumerate(res["data"]["schedules"], 1):
            print(f"#{rank} 分數={item['score']} 學分={item['total_credits']} 課程={item['course_ids']} 指標={item['metrics']}")
