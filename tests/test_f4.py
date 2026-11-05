"""F4 room checks: capacity, equipment, course and activity clashes."""
import unittest
from copy import deepcopy

from modules.activities import (add_activity, cancel_activity, check_room,
                               find_available_classrooms, update_activity)

def period_times():
    """Synthetic test clocks (period 1 = 08:00-08:50, ...); not a school timetable."""
    return {p: (f"{8 + i:02d}:00", f"{8 + i:02d}:50") for i, p in enumerate("123456789abc")}


def activity(**changes):
    """A Monday (2026-11-09) activity, 08:30-09:50, needing 30 seats and a projector."""
    row = dict(activity_id="A1", name="讀書會", date="2026-11-09",
               start_time="08:30", end_time="09:50", classroom_id="C101",
               participant_ids=["S001"], status="scheduled",
               capacity=30, required_equipment=["projector"])
    row.update(changes)
    return row


class TestCheckRoom(unittest.TestCase):
    def setUp(self):
        self.room = {"classroom_id": "C101", "capacity": 50, "equipment": ["projector"]}
        self.data = {
            "courses": [{"course_id": "CS101", "name": "Python", "classroom": "C101",
                         "time_slots": [[1, "3"], [1, "4"]]}],
            "activities": [activity(activity_id="A2", name="社團",
                                    start_time="08:00", end_time="08:20")],
        }
        self.times = period_times()

    def check(self, act, room=None, data=None):
        return check_room(act, room or self.room, data or self.data, self.times)

    # Normal cases
    def test_suitable_room_has_no_errors(self):
        self.assertEqual(self.check(activity()), [])

    def test_course_in_other_room_is_ignored(self):
        self.data["courses"][0]["classroom"] = "C102"
        self.assertEqual(self.check(activity(start_time="10:00", end_time="11:30")), [])

    # Boundary cases
    def test_capacity_exactly_equal_is_allowed(self):
        self.assertEqual(self.check(activity(capacity=50)), [])

    def test_touching_activity_is_not_a_clash(self):
        self.assertEqual(self.check(activity(start_time="08:20")), [])

    def test_activity_is_not_compared_with_itself(self):
        self.assertEqual(self.check(activity(activity_id="A2", start_time="08:00",
                                             end_time="08:20")), [])

    def test_cancelled_activity_does_not_hold_the_room(self):
        self.data["activities"][0]["status"] = "cancelled"
        self.assertEqual(self.check(activity(start_time="08:10")), [])

    # Error and conflict cases
    def test_room_too_small(self):
        self.assertEqual(self.check(activity(capacity=51)),
                         ["容量不足：教室 50 人，活動需要 51 人"])

    def test_missing_equipment_listed_one_by_one(self):
        errors = self.check(activity(required_equipment=["projector", "speaker", "mic"]))
        self.assertEqual(errors, ["缺少設備：speaker", "缺少設備：mic"])

    def test_room_without_equipment_field(self):
        room = {"classroom_id": "C101", "capacity": 50}
        self.assertEqual(self.check(activity(), room=room), ["缺少設備：projector"])

    def test_course_clash_reports_every_period(self):
        errors = self.check(activity(start_time="10:00", end_time="11:30"))
        self.assertEqual(errors, ["與課程衝突：星期1第3節 CS101 Python",
                                  "與課程衝突：星期1第4節 CS101 Python"])

    def test_activity_clash_same_room_same_date(self):
        self.assertEqual(self.check(activity(start_time="08:10")),
                         ["與活動衝突：A2 社團 08:00-08:20"])

    def test_activity_on_other_date_is_not_a_clash(self):
        self.assertEqual(self.check(activity(date="2026-11-10", start_time="08:10")), [])

    def test_all_problems_reported_together(self):
        room = {"classroom_id": "C101", "capacity": 10}
        errors = self.check(activity(start_time="08:10", end_time="11:30"), room=room)
        self.assertEqual(len(errors), 5)

    def test_invalid_capacity(self):
        self.assertIn("活動容量必須為正整數。", self.check(activity(capacity=0)))

    def test_missing_period_times_is_an_error_not_a_crash(self):
        errors = check_room(activity(), self.room, self.data, None)
        self.assertTrue(errors)

    def test_inputs_are_not_modified(self):
        act = activity(start_time="08:10")
        before = deepcopy((act, self.room, self.data))
        self.check(act)
        self.assertEqual(before, (act, self.room, self.data))


class TestFindAvailableClassrooms(unittest.TestCase):
    def setUp(self):
        self.rooms = [
            {"classroom_id": "C101", "capacity": 50, "equipment": ["projector"]},
            {"classroom_id": "C102", "capacity": 40, "equipment": ["projector"]},
            {"classroom_id": "C105", "capacity": 25},
        ]
        self.data = {
            "courses": [{"course_id": "CS101", "name": "Python", "classroom": "C101",
                         "time_slots": [[1, "3"], [1, "4"]]}],
            "activities": [],
        }
        self.times = period_times()

    def find(self, act, rooms=None):
        return find_available_classrooms(act, rooms or self.rooms, self.data, self.times)

    # Normal
    def test_lists_usable_rooms_smallest_first(self):
        result = self.find(activity())
        self.assertTrue(result["ok"])
        self.assertEqual([r["classroom_id"] for r in result["data"]["available"]],
                         ["C102", "C101"])

    def test_unusable_rooms_keep_their_reasons(self):
        result = self.find(activity())
        self.assertEqual(result["data"]["unavailable"],
                         [{"classroom_id": "C105",
                           "reasons": ["容量不足：教室 25 人，活動需要 30 人",
                                       "缺少設備：projector"]}])

    # Boundary
    def test_only_one_room_fits(self):
        result = self.find(activity(capacity=45))
        self.assertEqual([r["classroom_id"] for r in result["data"]["available"]], ["C101"])

    def test_course_clash_removes_room(self):
        result = self.find(activity(start_time="10:00", end_time="10:30"))
        self.assertEqual([r["classroom_id"] for r in result["data"]["available"]], ["C102"])

    # Error
    def test_no_room_fits_lists_every_unmet_condition(self):
        result = self.find(activity(capacity=60))
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["available"], [])
        self.assertEqual(result["errors"][0], "沒有符合條件的教室。")
        self.assertIn("C101：容量不足：教室 50 人，活動需要 60 人", result["errors"])
        self.assertIn("C105：缺少設備：projector", result["errors"])

    def test_inputs_are_not_modified(self):
        before = deepcopy((self.rooms, self.data))
        result = self.find(activity())
        result["data"]["available"][0]["capacity"] = 999
        self.assertEqual(before, (self.rooms, self.data))

class TestActivityManagement(unittest.TestCase):
    def setUp(self):
        self.data = {
            "classrooms": [{"classroom_id": "C101", "capacity": 50, "equipment": ["projector"]},
                           {"classroom_id": "C102", "capacity": 40, "equipment": ["projector"]}],
            "courses": [{"course_id": "CS101", "name": "Python", "classroom": "C101",
                         "time_slots": [[1, "3"], [1, "4"]]}],
            "students": [{"student_id": "S001"}, {"student_id": "S002"}],
            "activities": [activity(activity_id="A2", name="社團",
                                    start_time="08:00", end_time="08:20")],
        }
        self.times = period_times()

    def add(self, act):
        return add_activity(act, self.data, self.times)

    # add_activity
    def test_add_returns_new_list_and_keeps_input(self):
        before = deepcopy(self.data)
        result = self.add(activity())
        self.assertTrue(result["ok"])
        self.assertEqual([a["activity_id"] for a in result["data"]], ["A2", "A1"])
        self.assertEqual(before, self.data)

    def test_add_duplicate_id(self):
        result = self.add(activity(activity_id="A2", start_time="12:00", end_time="13:00"))
        self.assertFalse(result["ok"])
        self.assertIn("活動代號已存在。", result["errors"])

    def test_add_unknown_room(self):
        self.assertIn("教室不存在。", self.add(activity(classroom_id="X999"))["errors"])

    def test_add_unknown_student(self):
        result = self.add(activity(participant_ids=["S001", "S999"]))
        self.assertIn("學生不存在：S999", result["errors"])

    def test_add_participants_equal_to_capacity_is_allowed(self):
        self.assertTrue(self.add(activity(capacity=2, participant_ids=["S001", "S002"]))["ok"])

    def test_add_participants_over_capacity(self):
        result = self.add(activity(capacity=1, participant_ids=["S001", "S002"]))
        self.assertIn("報名人數 2 超過活動容量 1。", result["errors"])

    def test_add_room_clash_is_rejected(self):
        result = self.add(activity(start_time="08:10"))
        self.assertEqual(result["errors"], ["與活動衝突：A2 社團 08:00-08:20"])

    def test_add_invalid_time(self):
        self.assertFalse(self.add(activity(start_time="25:00"))["ok"])

    # cancel_activity
    def test_cancel_marks_cancelled_without_deleting(self):
        result = cancel_activity("A2", self.data)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["status"], "cancelled")
        self.assertEqual(self.data["activities"][0]["status"], "scheduled")

    def test_cancel_unknown_or_twice(self):
        self.assertEqual(cancel_activity("A9", self.data)["errors"], ["找不到指定活動。"])
        self.data["activities"] = cancel_activity("A2", self.data)["data"]
        self.assertEqual(cancel_activity("A2", self.data)["errors"], ["活動已取消。"])

    def test_cancelled_activity_frees_the_room(self):
        self.assertFalse(self.add(activity(start_time="08:10"))["ok"])
        self.data["activities"] = cancel_activity("A2", self.data)["data"]
        self.assertTrue(self.add(activity(start_time="08:10"))["ok"])

    # update_activity
    def test_update_time_without_self_conflict(self):
        result = update_activity("A2", {"end_time": "08:40"}, self.data, self.times)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"][0]["end_time"], "08:40")
        self.assertEqual(self.data["activities"][0]["end_time"], "08:20")

    def test_update_into_course_clash_is_rejected(self):
        result = update_activity("A2", {"start_time": "10:00", "end_time": "10:30"},
                                 self.data, self.times)
        self.assertEqual(result["errors"], ["與課程衝突：星期1第3節 CS101 Python"])

    def test_update_cannot_change_id_or_unknown(self):
        self.assertEqual(update_activity("A2", {"activity_id": "A3"}, self.data,
                                         self.times)["errors"], ["活動代號不可修改。"])
        self.assertEqual(update_activity("A9", {}, self.data, self.times)["errors"],
                         ["找不到指定活動。"])

    def test_update_cancelled_activity_is_rejected(self):
        self.data["activities"] = cancel_activity("A2", self.data)["data"]
        result = update_activity("A2", {"name": "新名稱"}, self.data, self.times)
        self.assertEqual(result["errors"], ["已取消的活動不可修改。"])

if __name__ == "__main__":
    unittest.main()