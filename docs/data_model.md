# 資料模型草案

狀態：待團隊確認；以下為示意資料，尚未寫入 data/，也未由程式驗證。
五份資料檔均使用 UTF-8 JSON 清單。代號作為關聯鍵，避免在多處複製完整物件。

## 學生：students.json

```json
[
  {
    "student_id": "S001",
    "name": "範例學生",
    "department": "資訊工程系",
    "year": 1,
    "credit_limit": 24
  }
]
```

已選課程由選課紀錄查出，不在學生資料中重複維護。

## 教室：classrooms.json

```json
[
  {
    "classroom_id": "R101",
    "building_id": "B01",
    "capacity": 40,
    "equipment": [
      "projector"
    ],
    "available_slots": [
      {
        "day": 2,
        "periods": [
          "3",
          "4"
        ]
      }
    ],
    "enabled": true
  }
]
```

available_slots 示例代表可用節次；實際範圍、日期停用與設備名稱規則待確認。

## 課程：courses.json

```json
[
  {
    "course_id": "CS101",
    "name": "Python 程式設計",
    "credits": 3,
    "required": false,
    "teacher": "範例教師",
    "capacity": 30,
    "slots": [
      {
        "day": 2,
        "periods": [
          "3",
          "4"
        ],
        "classroom_id": "R101"
      }
    ]
  }
]
```

學分為正整數、人數上限至少 1；每個時段使用合法星期與節次。
教室需存在，課程上限與場地容量如何共同限制，須於需求文件確認。
學生數由 enrollments 計算，同一課程多個時段只計算一次學分。

## 選課：enrollments.json

```json
[
  {
    "student_id": "S001",
    "course_id": "CS101"
  }
]
```

學號與課程代號須存在，同一配對不得重複；退選時移除配對。

## 活動：activities.json

```json
[
  {
    "activity_id": "A001",
    "name": "程式讀書會",
    "date": "2026-10-06",
    "start_time": "15:00",
    "end_time": "16:00",
    "expected_attendees": 20,
    "capacity": 30,
    "activity_type": "study_group",
    "required_equipment": [
      "projector"
    ],
    "classroom_id": "R101",
    "participant_ids": [
      "S001"
    ],
    "status": "scheduled"
  }
]
```

日期為 YYYY-MM-DD、時間為 HH:MM。報名者需存在且不得重複。
人數不得超過活動與教室容量；取消活動後不再占用時段。
狀態名稱、未配置教室的表示方式及跨午夜活動規則待確認。

## 後續擴充

F9 需另行建立建築物與路線資料（至少 10 個節點、15 條路線）。
節次實際時間及學期日期應在 F2/F4 整合前確定。
上述兩類資料目前尚未建立，不使用示例中的建築物代號假裝已有地圖。
