"""Shared dated-activity validation and explicit period-time projection."""
from datetime import date, datetime, timedelta

PERIODS = tuple("123456789abc")


def intervals_overlap(start_a, end_a, start_b, end_b):
    """Return whether two half-open intervals overlap; touching ends do not."""
    return start_a < end_b and start_b < end_a


def parse_date(value):
    """Require a canonical YYYY-MM-DD date; raise ValueError on invalid input."""
    if not isinstance(value, str):
        raise ValueError("日期須為 YYYY-MM-DD。")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("日期須為 YYYY-MM-DD。")
    return parsed


def time_minutes(value):
    """Require HH:MM and return minutes after midnight, or raise ValueError."""
    if not isinstance(value, str) or len(value) != 5:
        raise ValueError("時間須為 HH:MM。")
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def validate_period_times(period_times):
    """Require all twelve periods, with ordered, non-overlapping day intervals."""
    if not isinstance(period_times, dict) or set(period_times) != set(PERIODS):
        return ["請明確提供全部 12 節的實際開始與結束時間。"]
    errors, previous_end = [], -1
    for period in PERIODS:
        pair = period_times[period]
        try:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError("須提供開始與結束時間。")
            start, end = (time_minutes(value) for value in pair)
            if start >= end or start < previous_end:
                raise ValueError("節次須依序排列、不重疊且不可跨午夜。")
            previous_end = end
        except ValueError as error:
            errors.append(f"第 {period} 節：{error}")
    return errors


def validate_activity(activity):
    """Validate the scheduling subset of the draft activity schema."""
    if not isinstance(activity, dict):
        return ["活動必須為物件。"]
    errors = []
    for key in ("activity_id", "name", "classroom_id"):
        if not isinstance(activity.get(key), str) or not activity[key].strip():
            errors.append(f"活動 {key} 必須為非空字串。")
    try:
        parse_date(activity.get("date"))
        start, end = (time_minutes(activity.get(key)) for key in ("start_time", "end_time"))
        if start >= end:
            errors.append("活動結束須晚於開始，暫不支援跨午夜。")
    except ValueError:
        errors.append("活動日期或時間無效，須為 YYYY-MM-DD 與 HH:MM。")
    participants = activity.get("participant_ids")
    if (not isinstance(participants, list) or
            any(not isinstance(p, str) or not p.strip() for p in participants)):
        errors.append("活動 participant_ids 須為非空學號字串的清單。")
    elif len(participants) != len(set(participants)):
        errors.append("活動參加者不得重複。")
    if activity.get("status") not in ("scheduled", "cancelled"):
        errors.append("活動狀態須為 scheduled 或 cancelled。")
    return errors


def project_activities(activities, period_times=None, week_start=None, require_week=False):
    """Return (projected activity copies, errors) without changing input records.

    A week, when supplied, starts on Monday. Without a week, every scheduled
    activity is checked against recurring courses; no semester dates are assumed.
    A partial overlap occupies that period. No school clock times are built in.
    """
    if not isinstance(activities, list):
        return [], ["活動資料須為清單。"]
    errors = [f"活動第 {i} 筆：{e}" for i, a in enumerate(activities, 1)
              for e in validate_activity(a)]
    if errors:
        return [], errors
    active = [a for a in activities if a["status"] == "scheduled"]
    week = None
    if week_start is not None:
        try:
            week = parse_date(week_start)
            if week.weekday() != 0:
                raise ValueError("查詢週起始日期須為星期一。")
        except ValueError:
            return [], ["查詢週須為星期一的 YYYY-MM-DD 日期。"]
    elif active and require_week:
        return [], ["有活動時，請指定查詢週的星期一日期。"]
    if week is not None:
        active = [a for a in active if week <= parse_date(a["date"]) < week + timedelta(days=7)]
    if period_times is not None or active:
        errors = validate_period_times(period_times)
        if errors:
            return [], errors
    projected = []
    for activity in active:
        start, end = (time_minutes(activity[k]) for k in ("start_time", "end_time"))
        day = parse_date(activity["date"]).isoweekday()
        slots = [[day, p] for p in PERIODS
                 if intervals_overlap(start, end, *(time_minutes(t) for t in period_times[p]))]
        projected.append({**activity, "time_slots": slots})
    return projected, []
