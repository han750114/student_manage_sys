"""F4 acceptance: simulate one campus week with at least 10 activities.

Covers the four required situations: many registrations, a cancelled activity,
a room that is too small for everyone, and a venue conflict. The data below is
an isolated test fixture; application files in data/ are never touched.
"""
import unittest
from itertools import combinations

from modules.activities import (add_activity, cancel_activity, find_activities,
                               find_available_classrooms, register_participant)
from modules.scheduling import intervals_overlap, time_minutes
from modules.system_data import validate_system


def period_times():
    """Synthetic test clocks (period 1 = 08:00-08:50, ...); not a school timetable."""
    return {p: (f"{8 + i:02d}:00", f"{8 + i:02d}:50") for i, p in enumerate("123456789abc")}


def make_activity(activity_id, name, date, start, end, room, capacity,
                  equipment=(), participants=()):
    return dict(activity_id=activity_id, name=name, date=date, start_time=start,
                end_time=end, classroom_id=room, participant_ids=list(participants),
                status="scheduled", capacity=capacity, required_equipment=list(equipment))


def make_data():
    """Five rooms like data/classrooms.json, one weekly course and eight students."""
    rooms = [("C101", 50, ["projector"]), ("C102", 40, ["projector"]),
             ("C103", 30, []), ("C104", 60, ["projector", "speaker"]), ("C105", 25, [])]
    return {
        "classrooms": [{"classroom_id": r, "capacity": c, "equipment": e} for r, c, e in rooms],
        "courses": [{"course_id": "CS101", "name": "Python程式設計", "credits": 3,
                     "course_type": "必修", "teacher": "張老師", "capacity": 50,
                     "classroom": "C101", "time_slots": [[1, "3"], [1, "4"]]}],
        "students": [{"student_id": f"S00{i}", "name": f"學生{i}", "department": "資訊工程系",
                      "max_credits": 25} for i in range(1, 9)],
        "enrollments": [],
        "activities": [],
    }


# Ten activities across Monday 2026-11-09 to Friday 2026-11-13.
WEEK = [
    make_activity("A01", "程式讀書會", "2026-11-09", "08:00", "09:50", "C101", 30, ["projector"]),
    make_activity("A02", "社團幹部會議", "2026-11-09", "13:00", "14:00", "C103", 3),
    make_activity("A03", "專題討論", "2026-11-10", "09:00", "10:00", "C102", 20, ["projector"]),
    make_activity("A04", "期中複習", "2026-11-10", "15:00", "17:00", "C104", 55,
                  ["projector", "speaker"]),
    make_activity("A05", "英文會話", "2026-11-11", "10:00", "11:00", "C105", 20),
    make_activity("A06", "演講練習", "2026-11-11", "13:00", "14:30", "C102", 25, ["projector"]),
    make_activity("A07", "系學會迎新", "2026-11-12", "18:00", "20:00", "C104", 60, ["speaker"]),
    make_activity("A08", "桌遊社", "2026-11-12", "12:00", "13:00", "C103", 15),
    make_activity("A09", "數學解題", "2026-11-13", "09:00", "10:00", "C105", 10),
    make_activity("A10", "電影欣賞", "2026-11-13", "14:00", "16:00", "C101", 40, ["projector"]),
]


class TestF4AcceptanceSimulation(unittest.TestCase):
    def setUp(self):
        self.data = make_data()
        self.times = period_times()

    def add(self, activity):
        result = add_activity(activity, self.data, self.times)
        if result["ok"]:
            self.data["activities"] = result["data"]
        return result

    def register(self, activity_id, student_id):
        result = register_participant(activity_id, student_id, self.data)
        if result["ok"]:
            self.data["activities"] = result["data"]
        return result

    def test_campus_week_with_ten_activities(self):
        # 1. Add ten activities one by one; every one must be accepted.
        for activity in WEEK:
            result = self.add(activity)
            self.assertTrue(result["ok"], f"{activity['activity_id']}: {result['errors']}")
        self.assertEqual(len(self.data["activities"]), 10)

        # 2. Venue conflict: C101 is taken by A01 on Monday morning.
        clash = make_activity("A11", "臨時小組", "2026-11-09", "09:00", "10:00", "C101", 10)
        self.assertEqual(self.add(clash)["errors"], ["與活動衝突：A01 程式讀書會 08:00-09:50"])
        #    ... and with the CS101 course in C101 (Monday period 3, 10:00-10:50).
        course_clash = dict(clash, start_time="10:00", end_time="10:30")
        self.assertEqual(self.add(course_clash)["errors"],
                         ["與課程衝突：星期1第3節 CS101 Python程式設計"])
        #    The organizer asks for another room and takes the smallest one that fits.
        rooms = find_available_classrooms(clash, self.data["classrooms"], self.data, self.times)
        self.assertTrue(rooms["ok"])
        best = rooms["data"]["available"][0]["classroom_id"]
        self.assertEqual(best, "C105")
        self.assertTrue(self.add(dict(clash, classroom_id=best))["ok"])

        # 3. Room too small: nobody can host 70 people, and every reason is listed.
        huge = make_activity("A12", "全系大會", "2026-11-12", "10:00", "12:00", "C104", 70)
        rooms = find_available_classrooms(huge, self.data["classrooms"], self.data, self.times)
        self.assertFalse(rooms["ok"])
        self.assertEqual(rooms["errors"][0], "沒有符合條件的教室。")
        self.assertEqual(len(rooms["data"]["unavailable"]), 5)
        self.assertIn("C104：容量不足：教室 60 人，活動需要 70 人", rooms["errors"])

        # 4. Many registrations: A02 has 3 seats; the fourth student is refused.
        for student in ("S001", "S002", "S003"):
            self.assertTrue(self.register("A02", student)["ok"])
        self.assertEqual(self.register("A02", "S004")["errors"], ["活動已額滿（3 人）。"])
        self.assertEqual(self.register("A02", "S001")["errors"],
                         ["已報名此活動，不得重複報名。", "活動已額滿（3 人）。"])

        # 5. Cancel A05; its room and time become free for a new activity.
        replacement = make_activity("A13", "日文會話", "2026-11-11", "10:00", "11:00", "C105", 20)
        self.assertFalse(self.add(replacement)["ok"])
        result = cancel_activity("A05", self.data)
        self.assertTrue(result["ok"])
        self.data["activities"] = result["data"]
        self.assertTrue(self.add(replacement)["ok"])
        self.assertEqual(self.register("A05", "S005")["errors"], ["活動已取消，無法報名。"])

        # 6. Final checks on the whole week.
        acts = self.data["activities"]
        scheduled = find_activities(acts, status="scheduled")["data"]
        self.assertEqual(len(acts), 12)
        self.assertEqual(len(scheduled), 11)
        self.assertEqual(find_activities(acts, student_id="S002")["data"][0]["activity_id"], "A02")
        #    No room is ever double-booked by two scheduled activities.
        for a, b in combinations(scheduled, 2):
            if a["classroom_id"] == b["classroom_id"] and a["date"] == b["date"]:
                self.assertFalse(intervals_overlap(
                    time_minutes(a["start_time"]), time_minutes(a["end_time"]),
                    time_minutes(b["start_time"]), time_minutes(b["end_time"])),
                    f"{a['activity_id']} and {b['activity_id']} share a room")
        #    The team's shared snapshot validation accepts the final data.
        self.assertEqual(validate_system(self.data), [])


if __name__ == "__main__":
    unittest.main()