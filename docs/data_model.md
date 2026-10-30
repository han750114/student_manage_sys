# 資料模型草案

> 2026-10-17：目前 F1 與 data/ 的實際格式已統一，請以
> [F1 介面與格式](f1_interfaces.md) 為準。下列舊示例保留作為未來設計參考，
> 其中 `credit_limit`、`required`、`slots`、獨立年級及每時段教室不是目前 F1 的輸入格式。

狀態：待團隊確認；以下為示意資料，尚未寫入 data/，也未由程式驗證。
五份資料檔均使用 UTF-8 JSON 清單。代號作為關聯鍵，避免在多處複製完整物件。

> 2026-10-30：F2／F3 已沿用現有 F1 資料格式與 enrollments 關聯，沒有新增學生已選課程或目前學分欄位。
> 活動時間整合與驗證範圍見 [F2／F3 實作介面](f2_f3_interfaces.md)。節次時間為執行時參數，不新增資料檔。

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
本次 F2／F3 讀取與驗證的活動欄位為 activity_id、name、date、start_time、end_time、
classroom_id、participant_ids、status；代號須唯一，教室與參加者須存在。
狀態使用 scheduled／cancelled，取消後不占用時段；本次暫不支援跨午夜。
只讀整合要求教室已配置；F4 未配置教室的表示方式、容量與設備配置介面仍待設計。
上述容量、設備等額外欄位保留供 F4 使用，不能因為時間整合完成便宣稱 F4 已驗收。

## 後續擴充

F9 需另行建立建築物與路線資料（至少 10 個節點、15 條路線）。
節次實際時間及學期日期應在 F2/F4 整合前確定。
上述兩類資料目前尚未建立，不使用示例中的建築物代號假裝已有地圖。
