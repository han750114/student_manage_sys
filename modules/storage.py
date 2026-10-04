"""F6 資料存取模組（尚未實作）。

預計介面：
load_records(path) -> (records, errors)
save_records(path, records) -> None

載入時區分不存在、整份 JSON 損壞與單筆資料錯誤。
不得將損壞檔案默默當成空資料再覆寫。
"""
