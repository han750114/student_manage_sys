"""F4/F5 CLI integration checks using temporary stores and synthetic clocks."""
import contextlib
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import main
from modules.course_filter import check_course_feasibility
from modules.storage import save_records
from modules.system_data import load_system
from modules.timetable import build_timetable
from tests.test_f4 import period_times
from tests.test_f5 import make_data


class F4F5CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.data = make_data()
        self.data['classrooms'][1]['equipment'] = ['projector']
        self.times = [f'{start}-{end}' for start, end in period_times().values()]
        self.write_data()

    def write_data(self):
        for name, records in self.data.items():
            save_records(self.directory / f'{name}.json', records)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.directory.glob('*.json')}

    def cli(self, answers):
        output = io.StringIO()
        with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(output):
            main(self.directory)
        return output.getvalue()

    def activity_fields(self, identifier='A1', capacity='2', equipment=''):
        return [identifier, 'Study', '2026-11-09', '08:10', '08:40', capacity, 'R2', equipment]

    def add_activity(self):
        return self.cli(['5', '1', *self.activity_fields(), *self.times, '0', '0'])

    def test_activity_add_register_restart_and_timetable(self):
        output = self.cli(['5', '1', *self.activity_fields(), *self.times,
                           '6', 'A1', 'S1', '0', '0'])
        self.assertEqual(output.count('操作成功，已存檔。'), 2)
        data, errors = load_system(self.directory)
        self.assertEqual(errors, [])
        self.assertEqual(data['activities'][0]['participant_ids'], ['S1'])
        grid = build_timetable('S1', data, '2026-11-09', period_times())
        self.assertTrue(grid['ok'], grid['errors'])
        self.assertEqual(grid['data'][0][0]['id'], 'A1')
        output = self.cli(['5', '4', '2026-11-09', 'R2', 'scheduled', 'S1', '0', '0'])
        self.assertIn('activity_id: A1', output)

    def test_activity_update_preserves_blank_fields_and_can_clear_equipment(self):
        self.cli(['5', '1', *self.activity_fields(equipment='projector'), *self.times, '0', '0'])
        output = self.cli(['5', '2', 'A1', 'Renamed', '', '', '', '', '', '-',
                           *self.times, '0', '0'])
        self.assertIn('操作成功', output)
        row = load_system(self.directory)[0]['activities'][0]
        self.assertEqual(row['name'], 'Renamed')
        self.assertEqual(row['date'], '2026-11-09')
        self.assertEqual(row['classroom_id'], 'R2')
        self.assertEqual(row['required_equipment'], [])

    def test_activity_cancel_persists_and_disappears_from_timetable(self):
        self.add_activity()
        output = self.cli(['5', '3', 'A1', 'y', '0', '0'])
        self.assertIn('操作成功', output)
        data, errors = load_system(self.directory)
        self.assertEqual(errors, [])
        self.assertEqual(data['activities'][0]['status'], 'cancelled')
        self.assertTrue(build_timetable('S1', data)['ok'])

    def test_declining_cancellation_preserves_files(self):
        self.add_activity()
        before = self.snapshot()
        self.cli(['5', '3', 'A1', 'n', '0', '0'])
        self.assertEqual(self.snapshot(), before)

    def test_activity_duplicate_does_not_write(self):
        self.add_activity()
        before = self.snapshot()
        output = self.add_activity()
        self.assertIn('活動代號已存在', output)
        self.assertEqual(self.snapshot(), before)

    def test_activity_invalid_capacity_recovers(self):
        before = self.snapshot()
        output = self.cli(['5', '1', *self.activity_fields(capacity='bad')[:6], '0', '0'])
        self.assertIn('請輸入整數', output)
        self.assertEqual(self.snapshot(), before)

    def test_first_activity_requires_valid_explicit_clocks(self):
        before = self.snapshot()
        output = self.cli(['5', '1', *self.activity_fields(), *(['bad'] * 12), '0', '0'])
        self.assertIn('輸入錯誤', output)
        self.assertEqual(self.snapshot(), before)

    def test_activity_room_conflict_is_rejected(self):
        before = self.snapshot()
        fields = self.activity_fields()
        fields[6] = 'R1'
        output = self.cli(['5', '1', *fields, *self.times, '0', '0'])
        self.assertIn('與課程衝突', output)
        self.assertEqual(self.snapshot(), before)

    def test_activity_search_invalid_date_recovers(self):
        before = self.snapshot()
        output = self.cli(['5', '4', 'bad', '', '', '', '0', '0'])
        self.assertIn('日期須為', output)
        self.assertEqual(self.snapshot(), before)

    def test_room_filter_shows_equipment_and_course_rejections_without_saving(self):
        before = self.snapshot()
        fields = self.activity_fields(equipment='projector')
        del fields[6]
        output = self.cli(['5', '5', *fields, *self.times, '0', '0'])
        self.assertIn('可用教室：R2', output)
        self.assertNotIn('可用教室：R1', output)
        self.assertIn('缺少設備', output)
        self.assertIn('與課程衝突', output)
        self.assertEqual(self.snapshot(), before)

    def test_room_filter_reports_no_matching_room(self):
        fields = self.activity_fields(capacity='61')
        del fields[6]
        output = self.cli(['5', '5', *fields, *self.times, '0', '0'])
        self.assertIn('沒有符合條件的教室', output)
        self.assertIn('容量不足', output)

    def test_registration_last_seat_then_full(self):
        self.add_activity()
        output = self.cli(['5', '6', 'A1', 'S1', '6', 'A1', 'S2',
                           '6', 'A1', 'S3', '0', '0'])
        self.assertIn('活動已額滿', output)
        self.assertEqual(load_system(self.directory)[0]['activities'][0]['participant_ids'], ['S1', 'S2'])

    def test_activity_save_failure_preserves_disk_and_session(self):
        before = self.snapshot()
        with patch('main.save_records', side_effect=OSError('disk full')):
            output = self.cli(['5', '1', *self.activity_fields(), *self.times,
                               '4', '', '', '', '', '0', '0'])
        self.assertIn('存檔失敗', output)
        self.assertIn('沒有符合的活動', output)
        self.assertEqual(self.snapshot(), before)

    def test_f5_filter_marks_preferences_and_mandatory_courses(self):
        before = self.snapshot()
        output = self.cli(['6', '1', 'C3,C5', 'C1', '7:c', '3', '0', '0'])
        self.assertIn('course_id: C1', output)
        self.assertIn('course_id: C3', output)
        self.assertNotIn('course_id: C5', output)
        self.assertIn('列於必修清單: 是', output)
        self.assertIn('符合偏好星期: 是', output)
        self.assertEqual(self.snapshot(), before)

    def test_f5_filter_missing_mandatory_is_reported(self):
        output = self.cli(['6', '1', '', 'C1', '1:1', '', '0', '0'])
        self.assertIn('必修課未列入候選：C1', output)

    def test_f5_filter_empty_preferences_lists_all_open_courses(self):
        output = self.cli(['6', '1', '', '', '', '', '0', '0'])
        for identifier in ('C1', 'C2', 'C3', 'C4', 'C5'):
            self.assertIn(f'course_id: {identifier}', output)

    def test_f5_invalid_slots_and_preferred_day_recover(self):
        for answers in (['6', '1', '', '', '8:z', '0', '0'],
                        ['6', '1', '', '', '', '8', '0', '0'],
                        ['6', '1', '', '', '', 'bad', '0', '0']):
            with self.subTest(answers=answers):
                self.assertIn('輸入錯誤', self.cli(answers))

    def test_f5_feasibility_uses_activity_clocks_without_enrolling(self):
        self.add_activity()
        before = self.snapshot()
        output = self.cli(['6', '2', 'S1', 'C3', '', *self.times, '0', '0'])
        self.assertIn('可行性檢查通過，尚未加選或存檔', output)
        self.assertEqual(self.snapshot(), before)

    def test_f5_feasibility_reports_activity_room_conflict(self):
        self.add_activity()
        self.data, _ = load_system(self.directory)
        self.data['courses'][1]['time_slots'] = [[1, '1']]
        self.write_data()
        output = self.cli(['6', '2', 'S1', 'C2', '', *self.times, '0', '0'])
        self.assertIn('教室活動衝突', output)

    def test_f5_feasibility_forbidden_slot_and_unknown_student(self):
        self.assertIn('違反不可上課時段', self.cli(['6', '2', 'S1', 'C3', '3:c', '0', '0']))
        self.assertIn('學生不存在', self.cli(['6', '2', 'UNKNOWN', 'C3', '', '0', '0']))

    def test_f5_credit_check_exact_limits_and_empty_selection(self):
        before = self.snapshot()
        output = self.cli(['6', '3', 'C1,C3', '5', '5', '3', '', '1', '', '0', '0'])
        self.assertIn('清單總學分：5', output)
        self.assertIn('學分檢查通過', output)
        self.assertIn('總學分 0 低於最低限制 1', output)
        self.assertEqual(self.snapshot(), before)

    def test_f5_credit_check_unknown_duplicate_and_contradictory_limits(self):
        for answers, message in (
            (['6', '3', 'MISSING', '0', '0'], '課程不存在'),
            (['6', '3', 'C1,C1', '0', '0'], '課程代號不可重複'),
            (['6', '3', 'C1', '6', '3', '0', '0'], '最低學分不可大於'),
        ):
            with self.subTest(message=message):
                self.assertIn(message, self.cli(answers))

    def test_new_submenus_reject_invalid_choices(self):
        output = self.cli(['5', 'bad', '0', '6', 'bad', '0', '0'])
        self.assertEqual(output.count('無效選項'), 2)

    def test_feasibility_optional_clocks_preserve_existing_callers(self):
        self.assertTrue(check_course_feasibility('S1', 'C3', self.data, {})['ok'])
        self.add_activity()
        data, _ = load_system(self.directory)
        before = deepcopy(data)
        result = check_course_feasibility('S1', 'C3', data, {}, period_times())
        self.assertTrue(result['ok'], result['errors'])
        self.assertEqual(data, before)


if __name__ == '__main__':
    unittest.main()
