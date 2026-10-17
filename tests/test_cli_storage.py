"""Exercise CLI persistence and failure recovery with temporary fixtures."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from main import main
from modules.storage import load_records, save_records
from modules.system_data import load_system


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for name in ('courses', 'students', 'enrollments', 'activities'):
            save_records(self.directory / f'{name}.json', [])
        save_records(self.directory / 'classrooms.json', [{'classroom_id': 'R1', 'capacity': 40}])

    def run_cli(self, answers):
        output = io.StringIO()
        with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(output):
            main(self.directory)
        return output.getvalue()

    def add_course(self):
        return self.run_cli(['1', '1', 'C1', 'Python', '3', '必修', 'Teacher', '20', 'R1', '1:1', '0', '0'])

    def test_course_crud_restart(self):
        self.assertIn('成功', self.add_course())
        self.assertIn('C1', self.run_cli(['1', '4', '', '', '', '', '', '0', '0']))
        self.run_cli(['1', '2', 'C1', 'New', '', '', '', '', '', '', '0', '0'])
        self.assertEqual(load_records(self.directory / 'courses.json')[0][0]['name'], 'New')
        self.run_cli(['1', '3', 'C1', 'y', '0', '0'])
        self.assertEqual(load_records(self.directory / 'courses.json')[0], [])

    def test_student_crud_restart(self):
        self.run_cli(['2', '1', 'S1', 'Student', 'CS', '24', '0', '0'])
        self.run_cli(['2', '2', 'S1', 'New', '', '', '0', '0'])
        self.assertIn('New', self.run_cli(['2', '4', 'S1', '', '', '0', '0']))
        self.run_cli(['2', '3', 'S1', 'y', '0', '0'])
        self.assertEqual(load_records(self.directory / 'students.json')[0], [])

    def test_cancel_delete(self):
        self.add_course()
        self.run_cli(['1', '3', 'C1', 'n', '0', '0'])
        self.assertEqual(len(load_records(self.directory / 'courses.json')[0]), 1)

    def test_save_failure_preserves_memory(self):
        with patch('main.save_records', side_effect=OSError('disk full')):
            output = self.run_cli(['2', '1', 'S1', 'Student', 'CS', '24', '4', '', '', '', '0', '0'])
        self.assertIn('存檔失敗', output)
        self.assertIn('沒有符合', output)

    def test_corrupt_file_preserved(self):
        path = self.directory / 'courses.json'
        path.write_text('{broken', encoding='utf-8')
        self.assertIn('無法載入', self.run_cli([]))
        self.assertEqual(path.read_text(encoding='utf-8'), '{broken')

    def test_invalid_record_blocks_session(self):
        save_records(self.directory / 'courses.json', [{}])
        self.assertIn('無法載入', self.run_cli([]))

    def test_invalid_number_recovers(self):
        self.assertIn('整數', self.run_cli(['2', '1', 'S1', 'Student', 'CS', 'abc', '0', '0']))

    def test_invalid_option_recovers(self):
        self.assertIn('無效選項', self.run_cli(['z', '0']))

    def test_eof(self):
        with patch('builtins.input', side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()):
            main(self.directory)

    def test_ctrl_c(self):
        with patch('builtins.input', side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            main(self.directory)

    def test_atomic_failure_preserves_file(self):
        path = self.directory / 'courses.json'
        with patch('modules.storage.os.replace', side_effect=OSError('blocked')):
            with self.assertRaises(OSError):
                save_records(path, [{'name': '課程'}])
        self.assertEqual(load_records(path)[0], [])
        self.assertEqual(list(self.directory.glob('*.tmp')), [])

    def test_unicode_round_trip(self):
        path = self.directory / 'students.json'
        save_records(path, [{'name': '學生'}])
        self.assertEqual(load_records(path), ([{'name': '學生'}], []))

    def test_missing_file(self):
        self.assertTrue(load_records(self.directory / 'missing.json')[1])

    def test_wrong_top_level(self):
        path = self.directory / 'courses.json'
        path.write_text('{}', encoding='utf-8')
        self.assertTrue(load_records(path)[1])

    def test_invalid_reference(self):
        save_records(self.directory / 'enrollments.json', [{'student_id': 'S1', 'course_id': 'C1'}])
        self.assertTrue(load_system(self.directory)[1])

    def test_duplicate_enrollment(self):
        self.add_course()
        self.run_cli(['2', '1', 'S1', 'Student', 'CS', '24', '0', '0'])
        row = {'student_id': 'S1', 'course_id': 'C1'}
        save_records(self.directory / 'enrollments.json', [row, row])
        self.assertTrue(load_system(self.directory)[1])
