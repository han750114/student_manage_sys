"""CLI presentation and input; no application data is stored in globals."""
from pathlib import Path
from modules import management as management
from modules.storage import save_records
from modules.system_data import load_system
from modules.conflicts import add_enrollment, check_enrollment
from modules.scheduling import PERIODS, validate_period_times
from modules.timetable import (
    build_timetable, find_course_slots, find_free_slots, get_cell, get_day,
    summarize_timetable,
)


def read_fields(kind, updating=False):
    """Collect allowed fields; blank update values keep the old value."""
    fields = ([('name', '名稱'), ('credits', '學分'), ('course_type', '必修／選修'),
               ('teacher', '教師'), ('capacity', '人數上限'), ('classroom', '教室代號'),
               ('time_slots', '時段（例如 1:3,1:4,2:a）')] if kind == 'courses' else
              [('name', '姓名'), ('department', '系級'), ('max_credits', '學分上限')])
    values = {}
    if not updating:
        key = 'course_id' if kind == 'courses' else 'student_id'
        values[key] = input('課程代號：' if kind == 'courses' else '學號：').strip()
    for key, label in fields:
        text = input(f'{label}' + ('（留空不改）：' if updating else '：')).strip()
        if updating and not text:
            continue
        if key in ('credits', 'capacity', 'max_credits'):
            try:
                values[key] = int(text)
            except ValueError:
                raise ValueError(f'{label}請輸入整數。') from None
        elif key == 'time_slots':
            try:
                
                values[key] = [[int(day), period.strip().lower()] for day, period in
                               (part.strip().split(':') for part in text.split(','))]
            except ValueError:
                raise ValueError('時段格式為 星期:節次，以逗號分隔。') from None
        else:
            values[key] = text
    return values


def show_result(result, kind, data):
    """Display derived selections, credits and remaining seats without storing them."""
    if not result['ok']:
        print('\n'.join(result['errors']))
        return
    if not result['data']:
        print('沒有符合的資料。')
    for original in result['data']:
        row = dict(original)
        if kind == 'courses':
            row['remaining_seats'] = row['capacity'] - sum(
                e['course_id'] == row['course_id'] for e in data['enrollments'])
        else:
            selected = [e['course_id'] for e in data['enrollments'] if e['student_id'] == row['student_id']]
            row['selected_courses'] = selected
            row['total_credits'] = sum(c['credits'] for c in data['courses'] if c['course_id'] in selected)
        print(' | '.join(f'{key}: {value}' for key, value in row.items()))


def save_result(data, kind, result, directory):
    """Commit to memory only after the atomic file save succeeds."""
    if not result['ok']:
        print('\n'.join(result['errors']))
        return
    try:
        save_records(directory / f'{kind}.json', result['data'])
    except (OSError, ValueError) as error:
        print(f'存檔失敗，本次操作未套用：{error}')
        return
    data[kind] = result['data']
    print('操作成功，已存檔。')


def query(kind, data):
    """Collect optional filters and call the core query functions."""
    fields = ([('course_id', '課程代號'), ('teacher', '教師'), ('weekday', '星期'),
               ('course_type', '必修／選修'), ('min_remaining', '最低剩餘名額')]
              if kind == 'courses' else [('student_id', '學號'), ('name', '姓名'), ('department', '系級')])
    filters = {}
    for key, label in fields:
        value = input(f'{label}（留空不限）：').strip()
        if value:
            # by UncleAmra show a message instead of python int() error 
            try:
                filters[key] = int(value) if key in ('weekday', 'min_remaining') else value
            except ValueError:
                raise ValueError(f'{label}請輸入整數。') from None
    if kind == 'courses':
        result = management.find_courses(data[kind], **filters, enrollments=data['enrollments'])
    else:
        result = management.find_students(data[kind], **filters)
    show_result(result, kind, data)


def manage_menu(kind, data, directory):
    """Run one CRUD submenu; reject bad input without leaving the application."""
    title = '課程' if kind == 'courses' else '學生'
    while True:
        print(f'\n{title}管理\n1. 新增\n2. 修改\n3. 刪除\n4. 查詢\n0. 返回')
        choice = input('請選擇：').strip()
        try:
            if choice == '0':
                return
            if choice == '4':
                query(kind, data)
                continue
            if choice not in ('1', '2', '3'):
                print('無效選項。')
                continue
            identifier = input(f'{title}代號：').strip() if choice in ('2', '3') else None
            if choice == '3':
                if input('確認刪除？輸入 y：').strip().lower() != 'y':
                    continue
                function = management.remove_course if kind == 'courses' else management.remove_student
                result = function(data[kind], identifier, data['enrollments'])
            else:
                values = read_fields(kind, updating=choice == '2')
                if kind == 'courses':
                    if choice == '1':
                        result = management.add_course(data[kind], values, data['classrooms'])
                    else:
                        result = management.update_course(data[kind], identifier, values, data['classrooms'])
                elif choice == '1':
                    result = management.add_student(data[kind], values)
                else:
                    result = management.update_student(data[kind], identifier, values)
            save_result(data, kind, result, directory)
        except ValueError as error:
            print(f'輸入錯誤：{error}')


def read_period_times(data):
    """Collect explicit clock times only when scheduled activities exist."""
    if not any(a['status'] == 'scheduled' for a in data['activities']):
        return None
    print('活動需使用實際節次時間；本次輸入只供此功能使用，不寫入資料檔。')
    mapping = {}
    for period in PERIODS:
        parts = input(f'第 {period} 節（HH:MM-HH:MM）：').strip().split('-')
        mapping[period] = parts
    errors = validate_period_times(mapping)
    if errors:
        raise ValueError('\n'.join(errors))
    return mapping


def enrollment_menu(data, directory):
    """Check or add selections; reuse the F1 atomic save/commit path."""
    while True:
        print('\n選課\n1. 只檢查\n2. 加選並存檔\n0. 返回')
        choice = input('請選擇：').strip()
        if choice == '0':
            return
        if choice not in ('1', '2'):
            print('無效選項。')
            continue
        try:
            student_id = input('學號：').strip()
            course_id = input('課程代號：').strip()
            times = read_period_times(data)
            if choice == '2':
                save_result(data, 'enrollments', add_enrollment(student_id, course_id, data, times), directory)
            else:
                result = check_enrollment(student_id, course_id, data, times)
                print('檢查通過，尚未加選或存檔。' if result['ok'] else '\n'.join(result['errors']))
                if result['data'] is not None:
                    stats = result['data']
                    print(f'目前學分：{stats["current_credits"]}，加選後：{stats["future_credits"]}，'
                          f'學分上限：{stats["max_credits"]}，剩餘名額：{stats["remaining_seats"]}')
        except ValueError as error:
            print(f'輸入錯誤：{error}')


def show_timetable_result(result):
    """Display query data including all occupants of a cell."""
    if not result['ok']:
        print('\n'.join(result['errors']))
    elif result['data'] is None or result['data'] == []:
        print('此時段空閒或沒有符合的資料。')
    else:
        print(result['data'])


def timetable_menu(data):
    """Display a weekly grid, day/cell/course queries, free runs and statistics."""
    try:
        student_id = input('學號：').strip()
        week = input('查詢週星期一（YYYY-MM-DD；無活動可留空）：').strip() or None
        times = read_period_times(data)
        result = build_timetable(student_id, data, week, times)
    except ValueError as error:
        print(f'輸入錯誤：{error}')
        return
    if not result['ok']:
        print('\n'.join(result['errors']))
        return
    grid = result['data']
    while True:
        print('\n個人課表\n1. 完整課表\n2. 依星期查詢\n3. 依星期及節次查詢\n'
              '4. 依課程代號查詢\n5. 連續空閒時段\n6. 統計\n0. 返回')
        choice = input('請選擇：').strip()
        try:
            if choice == '0':
                return
            if choice == '1':
                print('節次 | 星期1 | 星期2 | 星期3 | 星期4 | 星期5 | 星期6 | 星期7')
                for period, row in zip(PERIODS, grid):
                    labels = []
                    for cell in row:
                        occupants = [] if cell is None else cell.get('items', [cell])
                        labels.append(' / '.join(f'{c["id"]} {c["name"]}' for c in occupants) or '-')
                    print(period + ' | ' + ' | '.join(labels))
            elif choice == '2':
                show_timetable_result(get_day(grid, int(input('星期（1～7）：'))))
            elif choice == '3':
                day = int(input('星期（1～7）：'))
                show_timetable_result(get_cell(grid, day, input('節次：').strip().lower()))
            elif choice == '4':
                show_timetable_result(find_course_slots(grid, input('課程代號：').strip()))
            elif choice == '5':
                text = input('星期（逗號分隔，留空為全部）：').strip()
                days = [int(d.strip()) for d in text.split(',')] if text else list(range(1, 8))
                start = input('開始節次（留空為 1）：').strip().lower() or '1'
                end = input('結束節次（留空為 c）：').strip().lower() or 'c'
                minimum = input('最少連續節數（留空為 1）：').strip() or '1'
                show_timetable_result(find_free_slots(grid, dict(days=days, start_period=start,
                                                                 end_period=end, min_length=int(minimum))))
            elif choice == '6':
                stats = summarize_timetable(student_id, data, grid)['data']
                print(f'每日上課節數：{stats["periods_per_day"]}')
                print(f'每週總學分：{stats["weekly_credits"]}')
                print(f'每日課間空堂數：{stats["gaps_per_day"]}')
            else:
                print('無效選項。')
        except ValueError as error:
            print(f'輸入錯誤（數字欄位請輸入整數）：{error}')


def main(data_dir=None):
    """Start the CLI; data_dir is injectable for isolated tests and demonstrations."""
    directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent / 'data'
    data, errors = load_system(directory)
    if errors:
        print('無法載入資料，請修正後重啟；原檔保留。')
        print('\n'.join(errors))
        return
    try:
        while True:
            print('\n學生選課與校園規劃系統\n1. 課程管理\n2. 學生管理\n3. 選課檢查與加選\n4. 個人課表與空閒查詢\n0. 離開')
            choice = input('請選擇：').strip()
            if choice == '0':
                return
            if choice in ('1', '2'):
                manage_menu('courses' if choice == '1' else 'students', data, directory)
            elif choice == '3':
                enrollment_menu(data, directory)
            elif choice == '4':
                timetable_menu(data)
            else:
                print('無效選項。')
    except (EOFError, KeyboardInterrupt):
        print('\n已結束；成功的操作均已存檔。')


if __name__ == '__main__':
    main()
