"""Regression tests for F1; fixtures never touch application data."""
import copy
import unittest
from modules import management as m
from modules.validation import validate_course


class F1Tests(unittest.TestCase):
    def setUp(self):
        self.rooms = [{'classroom_id': 'R1', 'capacity': 40}]
        self.course = dict(course_id='C1', name='Python', credits=3,
                           course_type='必修', teacher='Teacher', capacity=1,
                           classroom='R1', time_slots=[[1, '1']])
        self.student = dict(student_id='S1', name='Student', department='CS', max_credits=24)
        self.enrollments = [dict(student_id='S1', course_id='C1')]

    def test_course_update_cannot_change_id(self):
        rows = [self.course]
        self.assertFalse(m.update_course(rows, 'C1', {'course_id': 'C2'}, self.rooms)['ok'])
        self.assertEqual(rows[0]['course_id'], 'C1')

    def test_student_update_cannot_change_id(self):
        self.assertFalse(m.update_student([self.student], 'S1', {'student_id': 'S2'})['ok'])

    def test_course_add_does_not_mutate_input(self):
        rows = []
        self.assertTrue(m.add_course(rows, self.course, self.rooms)['ok'])
        self.assertEqual(rows, [])

    def test_update_does_not_mutate_input(self):
        rows = [self.course]
        result = m.update_course(rows, 'C1', {'name': 'New'}, self.rooms)
        self.assertTrue(result['ok'])
        self.assertEqual(rows[0]['name'], 'Python')

    def test_student_add_does_not_mutate_input(self):
        rows = []
        self.assertTrue(m.add_student(rows, self.student)['ok'])
        self.assertEqual(rows, [])

    def test_course_delete_uses_enrollments(self):
        self.assertFalse(m.remove_course([self.course], 'C1', self.enrollments)['ok'])

    def test_student_delete_uses_enrollments(self):
        self.assertFalse(m.remove_student([self.student], 'S1', self.enrollments)['ok'])

    def test_remaining_capacity_uses_enrollments(self):
        self.assertEqual(m.find_courses([self.course], min_remaining=1,
                                       enrollments=self.enrollments)['data'], [])

    def test_legacy_filter_dictionary(self):
        self.assertEqual(len(m.find_courses([self.course], {'teacher': 'Teacher'})['data']), 1)

    def test_classroom_objects_accepted(self):
        self.assertEqual(validate_course(self.course, self.rooms), [])

    def test_invalid_slots_return_errors(self):
        for slots in (None, [], [[True, '1']], [[0, '1']], [[8, '1']], [[1, []]], [[1, 'z']], [3]):
            with self.subTest(slots=slots):
                self.assertTrue(validate_course({**self.course, 'time_slots': slots}, self.rooms))

    def test_bad_course_object(self):
        self.assertTrue(validate_course(None, self.rooms))

    def test_invalid_update_preserves_original(self):
        before = copy.deepcopy(self.course)
        self.assertFalse(m.update_course([self.course], 'C1', {'credits': 0}, self.rooms)['ok'])
        self.assertEqual(before, self.course)

    def test_delete_without_enrollment_data_fails_closed(self):
        self.assertFalse(m.remove_course([self.course], 'C1')['ok'])

    def test_unknown_field_rejected(self):
        self.assertFalse(m.update_student([self.student], 'S1', {'credit_limit': 1})['ok'])
