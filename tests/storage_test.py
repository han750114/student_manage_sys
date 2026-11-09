"""storage 模組單元測試（load_records / save_records）。

命名規則：test_<類型>_<描述>
  類型 = normal（正常）／boundary（邊界）／error（錯誤及衝突）
只測儲存模組自己的職責：依路徑讀、依路徑存。資料欄位內容的正確性不在此範圍。
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules.storage import load_records, save_records   # 若檔名不同，請修改這一行


class StorageTestBase(unittest.TestCase):
    """每個測試都在全新的暫存資料夾中進行，不碰專案的真實資料。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "data.json"

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def assert_load_fails(self):
        """讀取失敗的共同檢查：records 為空，且恰有一則錯誤訊息。"""
        records, errors = load_records(self.path)
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 1)


# ======================================================================
# load_records
# ======================================================================
class TestLoadRecords(StorageTestBase):

    # ---------- 正常案例 ----------
    def test_normal_load_multiple_records(self):
        self.write('[{"id": 1}, {"id": 2}, {"id": 3}]')
        records, errors = load_records(self.path)
        self.assertEqual(records, [{"id": 1}, {"id": 2}, {"id": 3}])
        self.assertEqual(errors, [])

    def test_normal_load_chinese_content(self):
        self.write('[{"name": "資料結構", "room": "教室一"}]')
        records, errors = load_records(self.path)
        self.assertEqual(records, [{"name": "資料結構", "room": "教室一"}])
        self.assertEqual(errors, [])

    def test_normal_load_accepts_str_path(self):
        self.write('[{"id": 1}]')
        records, errors = load_records(str(self.path))
        self.assertEqual(records, [{"id": 1}])
        self.assertEqual(errors, [])

    def test_normal_load_accepts_path_object(self):
        self.write('[{"id": 1}]')
        records, errors = load_records(self.path)
        self.assertEqual(records, [{"id": 1}])
        self.assertEqual(errors, [])

    def test_normal_load_preserves_record_order(self):
        self.write('[{"id": 3}, {"id": 1}, {"id": 2}]')
        records, _ = load_records(self.path)
        self.assertEqual([r["id"] for r in records], [3, 1, 2])

    def test_normal_load_keeps_value_types(self):
        self.write('[{"i": 1, "f": 1.5, "s": "a", "b": true}]')
        records, _ = load_records(self.path)
        row = records[0]
        self.assertIsInstance(row["i"], int)
        self.assertIsInstance(row["f"], float)
        self.assertIsInstance(row["s"], str)
        self.assertIs(row["b"], True)

    # ---------- 邊界案例 ----------
    def test_boundary_load_empty_list(self):
        self.write("[]")
        records, errors = load_records(self.path)
        self.assertEqual(records, [])
        self.assertEqual(errors, [])

    def test_boundary_load_single_record(self):
        self.write('[{"id": 1}]')
        records, errors = load_records(self.path)
        self.assertEqual(records, [{"id": 1}])
        self.assertEqual(errors, [])

    def test_boundary_load_zero_byte_file(self):
        self.write("")
        self.assert_load_fails()

    def test_boundary_load_whitespace_only_file(self):
        self.write("   \n\t  \n")
        self.assert_load_fails()

    def test_boundary_load_empty_dict_element(self):
        self.write("[{}]")
        records, errors = load_records(self.path)
        self.assertEqual(records, [{}])
        self.assertEqual(errors, [])

    def test_boundary_load_none_empty_string_and_nested_values(self):
        data = [{"a": None, "b": "", "c": {"x": [1, 2, {"y": None}]}, "d": []}]
        self.write(json.dumps(data))
        records, errors = load_records(self.path)
        self.assertEqual(records, data)
        self.assertEqual(errors, [])

    def test_boundary_load_many_records(self):
        data = [{"id": i} for i in range(1000)]
        self.write(json.dumps(data))
        records, errors = load_records(self.path)
        self.assertEqual(len(records), 1000)
        self.assertEqual(errors, [])

    # ---------- 錯誤及衝突案例 ----------
    def test_error_load_missing_file(self):
        # 故意不建立檔案
        self.assert_load_fails()

    def test_error_load_malformed_json(self):
        self.write("{bad")
        self.assert_load_fails()

    def test_error_load_truncated_json(self):
        self.write('[{"id": 1}, {"id": 2')
        self.assert_load_fails()

    def test_error_load_top_level_object(self):
        self.write('{"id": 1}')
        self.assert_load_fails()

    def test_error_load_top_level_null(self):
        self.write("null")
        self.assert_load_fails()

    def test_error_load_list_of_non_dicts(self):
        self.write("[1, 2, 3]")
        self.assert_load_fails()

    def test_error_load_list_mixing_dict_and_non_dict(self):
        self.write('[{"id": 1}, "oops"]')
        self.assert_load_fails()

    def test_error_load_non_utf8_bytes(self):
        self.path.write_bytes(b"\xff\xfe\x00\x01")
        self.assert_load_fails()

    def test_error_load_path_is_directory(self):
        records, errors = load_records(self.dir)   # 傳入的是資料夾而不是檔案
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 1)

    def test_error_load_never_raises_on_bad_input(self):
        """load_records 的約定：壞檔案只回報錯誤，不拋例外。"""
        self.write("{bad")
        try:
            load_records(self.path)
        except Exception as exc:   # pragma: no cover
            self.fail(f"load_records 不應拋出例外，但拋出了 {exc!r}")


# ======================================================================
# save_records
# ======================================================================
class TestSaveRecords(StorageTestBase):

    # ---------- 正常案例 ----------
    def test_normal_save_multiple_records(self):
        data = [{"id": 1}, {"id": 2}]
        save_records(self.path, data)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), data)

    def test_normal_save_then_load_round_trip(self):
        data = [{"id": 1, "name": "測試"}, {"id": 2, "name": "abc"}]
        save_records(self.path, data)
        records, errors = load_records(self.path)
        self.assertEqual(records, data)
        self.assertEqual(errors, [])

    def test_normal_save_writes_real_chinese_not_escaped(self):
        save_records(self.path, [{"name": "資料結構"}])
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("資料結構", text)
        self.assertNotIn("\\u", text)

    def test_normal_save_overwrites_existing_file(self):
        self.write('[{"old": true}]')
        save_records(self.path, [{"new": True}])
        records, _ = load_records(self.path)
        self.assertEqual(records, [{"new": True}])

    def test_normal_save_creates_file_when_absent(self):
        self.assertFalse(self.path.exists())
        save_records(self.path, [{"id": 1}])
        self.assertTrue(self.path.exists())

    def test_normal_save_accepts_str_path(self):
        save_records(str(self.path), [{"id": 1}])
        records, _ = load_records(self.path)
        self.assertEqual(records, [{"id": 1}])

    def test_normal_save_ends_with_newline(self):
        save_records(self.path, [{"id": 1}])
        self.assertTrue(self.path.read_text(encoding="utf-8").endswith("\n"))

    def test_normal_save_leaves_no_tmp_file_behind(self):
        save_records(self.path, [{"id": 1}])
        self.assertEqual([p.name for p in self.dir.iterdir()], ["data.json"])

    # ---------- 邊界案例 ----------
    def test_boundary_save_empty_list(self):
        save_records(self.path, [])
        self.assertEqual(self.path.read_text(encoding="utf-8").strip(), "[]")
        records, errors = load_records(self.path)
        self.assertEqual((records, errors), ([], []))

    def test_boundary_save_single_record(self):
        save_records(self.path, [{"id": 1}])
        records, _ = load_records(self.path)
        self.assertEqual(records, [{"id": 1}])

    def test_boundary_save_empty_dict_element(self):
        save_records(self.path, [{}])
        records, _ = load_records(self.path)
        self.assertEqual(records, [{}])

    def test_boundary_save_none_empty_string_and_nested_values(self):
        data = [{"a": None, "b": "", "c": {"x": [1, 2, {"y": None}]}, "d": []}]
        save_records(self.path, data)
        records, _ = load_records(self.path)
        self.assertEqual(records, data)

    def test_boundary_save_uses_indent_of_four_spaces(self):
        save_records(self.path, [{"id": 1}])
        self.assertIn('\n    {\n        "id": 1\n    }', self.path.read_text(encoding="utf-8"))

    def test_boundary_save_many_records(self):
        data = [{"id": i} for i in range(1000)]
        save_records(self.path, data)
        records, _ = load_records(self.path)
        self.assertEqual(records, data)

    def test_boundary_save_twice_keeps_only_latest(self):
        save_records(self.path, [{"id": 1}, {"id": 2}])
        save_records(self.path, [{"id": 9}])
        records, _ = load_records(self.path)
        self.assertEqual(records, [{"id": 9}])

    # ---------- 錯誤及衝突案例 ----------
    def test_error_save_rejects_dict(self):
        with self.assertRaises(ValueError):
            save_records(self.path, {"id": 1})

    def test_error_save_rejects_none(self):
        with self.assertRaises(ValueError):
            save_records(self.path, None)

    def test_error_save_rejects_list_of_non_dicts(self):
        with self.assertRaises(ValueError):
            save_records(self.path, [1, 2, 3])

    def test_error_save_rejects_list_mixing_dict_and_non_dict(self):
        with self.assertRaises(ValueError):
            save_records(self.path, [{"id": 1}, "oops"])

    def test_error_save_rejects_nan(self):
        with self.assertRaises(ValueError):
            save_records(self.path, [{"score": float("nan")}])

    def test_error_save_rejects_infinity(self):
        with self.assertRaises(ValueError):
            save_records(self.path, [{"score": float("inf")}])

    def test_error_save_rejects_non_serializable_value(self):
        with self.assertRaises(TypeError):
            save_records(self.path, [{"tags": {1, 2, 3}}])   # set 不能轉成 JSON

    def test_error_save_to_missing_directory(self):
        bad_path = self.dir / "no_such_dir" / "data.json"
        with self.assertRaises(OSError):
            save_records(bad_path, [{"id": 1}])

    def test_error_save_invalid_input_keeps_original_file(self):
        self.write('[{"id": 1}]')
        with self.assertRaises(ValueError):
            save_records(self.path, "not a list")
        self.assertEqual(self.path.read_text(encoding="utf-8"), '[{"id": 1}]')

    def test_error_save_nan_keeps_original_file(self):
        self.write('[{"id": 1}]')
        with self.assertRaises(ValueError):
            save_records(self.path, [{"score": float("nan")}])
        self.assertEqual(self.path.read_text(encoding="utf-8"), '[{"id": 1}]')

    def test_error_save_replace_failure_keeps_original_and_cleans_tmp(self):
        """模擬寫到最後一步（os.replace）失敗：原檔不變、暫存檔被清掉。"""
        self.write('[{"id": 1}]')
        with mock.patch("os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                save_records(self.path, [{"id": 2}])
        self.assertEqual(self.path.read_text(encoding="utf-8"), '[{"id": 1}]')
        self.assertEqual([p.name for p in self.dir.iterdir()], ["data.json"])

    def test_error_save_replace_failure_without_original_leaves_nothing(self):
        with mock.patch("os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                save_records(self.path, [{"id": 2}])
        self.assertEqual(list(self.dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()