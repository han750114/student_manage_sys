"""Exercise selection, persistence, queries and rollback with temporary stores."""
import contextlib
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import main, save_result
from modules.conflicts import add_enrollment
from modules.storage import save_records
from modules.system_data import load_system
from modules.timetable import build_timetable
from tests.test_f2 import activity, make_data, period_times


class Iteration2IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.data = make_data()
        for name, records in self.data.items():
            save_records(self.directory / f"{name}.json", records)

    def cli(self, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(output):
            main(self.directory)
        return output.getvalue()

    def test_selection_cli_restart_and_timetable(self):
        output = self.cli(["3", "2", "S1", "C2", "0", "4", "S1", "", "1", "0", "0"])
        self.assertIn("操作成功", output)
        self.assertIn("C2", output)
        loaded, errors = load_system(self.directory)
        self.assertEqual(errors, [])
        self.assertEqual(loaded["enrollments"], [dict(student_id="S1", course_id="C2")])
        self.assertEqual(build_timetable("S1", loaded)["data"][0][0]["id"], "C2")
        self.assertIn("C2", self.cli(["4", "S1", "", "1", "0", "0"]))

    def test_check_only_does_not_persist(self):
        self.assertIn("檢查通過", self.cli(["3", "1", "S1", "C2", "0", "0"]))
        self.assertEqual(load_system(self.directory)[0]["enrollments"], [])

    def test_failed_selection_preserves_files(self):
        self.data["enrollments"] = [dict(student_id="S2", course_id="C2")]
        save_records(self.directory / "enrollments.json", self.data["enrollments"])
        before = {p.name: p.read_bytes() for p in self.directory.glob("*.json")}
        self.assertIn("額滿", self.cli(["3", "2", "S1", "C2", "0", "0"]))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.glob("*.json")})

    def test_save_failure_preserves_selection_memory_and_file(self):
        result = add_enrollment("S1", "C2", self.data)
        before = deepcopy(self.data)
        with patch("main.save_records", side_effect=OSError("disk full")):
            with contextlib.redirect_stdout(io.StringIO()):
                save_result(self.data, "enrollments", result, self.directory)
        self.assertEqual(self.data, before)
        self.assertEqual(load_system(self.directory)[0]["enrollments"], [])

    def test_failed_cli_save_does_not_show_selected_course(self):
        with patch("main.save_records", side_effect=OSError("disk full")):
            output = self.cli(["3", "2", "S1", "C2", "0", "4", "S1", "", "6", "0", "0"])
        self.assertIn("存檔失敗", output)
        self.assertIn("每週總學分：0", output)

    def test_timetable_queries_and_invalid_input_recovery(self):
        output = self.cli(["4", "S1", "", "2", "bad", "2", "7", "3", "7", "c",
                           "4", "C2", "5", "1,7", "1", "c", "3", "6", "0", "0"])
        self.assertIn("輸入錯誤", output)
        self.assertIn("length", output)
        self.assertIn("每週總學分：0", output)

    def test_invalid_activity_blocks_writable_session_and_preserves_file(self):
        path = self.directory / "activities.json"
        save_records(path, [activity(date="invalid")])
        before = path.read_bytes()
        self.assertIn("無法載入", self.cli([]))
        self.assertEqual(path.read_bytes(), before)

    def test_dated_activity_cli_uses_explicit_times(self):
        save_records(self.directory / "activities.json", [activity()])
        mapping_inputs = [f"{a}-{b}" for a, b in period_times().values()]
        output = self.cli(["4", "S1", "2026-10-26", *mapping_inputs, "1", "0", "0"])
        self.assertIn("A1", output)
        self.assertIn("Study", output)

    def test_activity_unknown_participant_and_room_are_load_errors(self):
        save_records(self.directory / "activities.json",
                     [activity(participant_ids=["UNKNOWN"], classroom_id="UNKNOWN")])
        self.assertEqual(len(load_system(self.directory)[1]), 2)

    def test_selection_checks_activity_and_room_in_cli(self):
        save_records(self.directory / "activities.json", [activity()])
        mapping_inputs = [f"{a}-{b}" for a, b in period_times().values()]
        output = self.cli(["3", "2", "S1", "C2", *mapping_inputs, "0", "0"])
        self.assertIn("與已參加活動衝突", output)
        self.assertIn("教室活動衝突", output)
        self.assertEqual(load_system(self.directory)[0]["enrollments"], [])

    def test_invalid_times_return_to_main_without_changing_files(self):
        save_records(self.directory / "activities.json", [activity()])
        output = self.cli(["4", "S1", "2026-10-26", *(["bad"] * 12), "0"])
        self.assertIn("輸入錯誤", output)
        self.assertEqual(load_system(self.directory)[0]["enrollments"], [])


if __name__ == "__main__":
    unittest.main()
