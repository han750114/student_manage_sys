"""CLI presentation and input; no application data is stored in globals."""
from pathlib import Path
from modules import management as management
from modules.storage import save_records
from modules.system_data import load_system
from modules.conflicts import add_enrollment, check_enrollment
from modules.activities import (
    add_activity, cancel_activity, find_activities, find_available_classrooms,
    register_participant, update_activity,
)
from modules.course_filter import (
    check_course_feasibility, check_credit_range, filter_courses, validate_preferences,
)
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
            if '_is_preferred' in row:
                row['符合偏好星期'] = '是' if row.pop('_is_preferred') else '否'
            if '_is_mandatory' in row:
                row['列於必修清單'] = '是' if row.pop('_is_mandatory') else '否'
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


def read_period_times(data, required=False):
    """Collect explicit clocks for existing activities or a proposed new activity."""
    if not required and not any(a['status'] == 'scheduled' for a in data['activities']):
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


def read_items(prompt):
    """Read comma-separated identifiers or equipment names; blank means empty."""
    return [item.strip() for item in input(prompt).split(',') if item.strip()]


def read_slots():
    """Read and validate optional forbidden weekday/period pairs."""
    text = input('不可上課時段（例如 1:3,2:a；留空不限）：').strip()
    if not text:
        return []
    try:
        slots = [[int(day), period.strip().lower()] for day, period in
                 (part.strip().split(':') for part in text.split(','))]
    except ValueError:
        raise ValueError('時段格式為 星期:節次，以逗號分隔。') from None
    if any(not 1 <= day <= 7 or period not in PERIODS for day, period in slots):
        raise ValueError('星期須為 1～7，節次須為 1～9、a、b、c。')
    return slots


def read_activity_fields(updating=False, room_search=False):
    """Collect the fields supported by F4; blank updates retain existing values."""
    values = {}
    if not updating:
        values = dict(activity_id=input('活動代號：').strip(),
                      participant_ids=[], status='scheduled')
    fields = [('name', '活動名稱'), ('date', '日期（YYYY-MM-DD）'),
              ('start_time', '開始時間（HH:MM）'), ('end_time', '結束時間（HH:MM）'),
              ('capacity', '活動人數上限')]
    if not room_search:
        fields.append(('classroom_id', '教室代號'))
    for key, label in fields:
        text = input(label + ('（留空不改）：' if updating else '：')).strip()
        if updating and not text:
            continue
        if key == 'capacity':
            try:
                values[key] = int(text)
            except ValueError:
                raise ValueError('活動人數上限請輸入整數。') from None
        else:
            values[key] = text
    text = input('所需設備（逗號分隔；' +
                 ('留空不改，輸入 - 清空）：' if updating else '留空表示無）：')).strip()
    if not updating or text:
        values['required_equipment'] = ([] if text == '-' else
                                        [item.strip() for item in text.split(',') if item.strip()])
    return values


def show_activities(result):
    """Display activity query results without course/student derived fields."""
    if not result['ok']:
        print('\n'.join(result['errors']))
    elif not result['data']:
        print('沒有符合的活動。')
    else:
        for row in result['data']:
            print(' | '.join(f'{key}: {value}' for key, value in row.items()))


def activity_menu(data, directory):
    """Expose F4 operations and persist successful mutations before memory updates."""
    while True:
        print('\n活動與教室配置\n1. 新增活動\n2. 修改活動\n3. 取消活動\n'
              '4. 查詢活動\n5. 篩選教室\n6. 活動報名\n0. 返回')
        choice = input('請選擇：').strip()
        try:
            if choice == '0':
                return
            if choice in ('1', '5'):
                activity = read_activity_fields(room_search=choice == '5')
                times = read_period_times(data, required=True)
                if choice == '1':
                    save_result(data, 'activities', add_activity(activity, data, times), directory)
                else:
                    result = find_available_classrooms(activity, data['classrooms'], data, times)
                    for room in result['data']['available']:
                        print(f"可用教室：{room['classroom_id']} | 容量：{room['capacity']}")
                    for room in result['data']['unavailable']:
                        print(f"{room['classroom_id']}：" + '；'.join(room['reasons']))
                    if not result['ok']:
                        print('沒有符合條件的教室。')
            elif choice == '2':
                identifier = input('活動代號：').strip()
                updates = read_activity_fields(updating=True)
                times = read_period_times(data, required=True)
                save_result(data, 'activities',
                            update_activity(identifier, updates, data, times), directory)
            elif choice == '3':
                identifier = input('活動代號：').strip()
                if input('確認取消？輸入 y：').strip().lower() == 'y':
                    save_result(data, 'activities', cancel_activity(identifier, data), directory)
            elif choice == '4':
                date = input('日期（YYYY-MM-DD；留空不限）：').strip() or None
                room = input('教室代號（留空不限）：').strip() or None
                status = input('狀態（scheduled/cancelled；留空不限）：').strip() or None
                student = input('學號（留空不限）：').strip() or None
                show_activities(find_activities(data['activities'], date, room, status, student))
            elif choice == '6':
                identifier = input('活動代號：').strip()
                student = input('學號：').strip()
                save_result(data, 'activities',
                            register_participant(identifier, student, data), directory)
            else:
                print('無效選項。')
        except ValueError as error:
            print(f'輸入錯誤：{error}')


def read_credit_limits():
    """Collect optional limits and reuse F5 validation before credit processing."""
    limits = {}
    for key, label in (('min_credits', '最低學分'), ('max_credits', '最高學分')):
        text = input(f'{label}（留空不限）：').strip()
        if text:
            try:
                limits[key] = int(text)
            except ValueError:
                raise ValueError(f'{label}請輸入整數。') from None
    errors = validate_preferences(limits)
    if errors:
        raise ValueError('\n'.join(errors))
    return limits


def course_filter_menu(data):
    """Expose read-only F5 filtering, individual feasibility and credit checks."""
    while True:
        print('\n課程篩選與可行性檢查\n1. 候選課程篩選\n2. 單門課程可行性\n'
              '3. 指定課程清單學分檢查\n0. 返回')
        choice = input('請選擇：').strip()
        try:
            if choice == '0':
                return
            if choice == '1':
                preferences = dict(
                    desired_courses=read_items('希望課程代號（逗號分隔；留空不限）：'),
                    mandatory_courses=read_items('必修課程代號（逗號分隔；留空無）：'),
                    unavailable_slots=read_slots(),
                )
                preferences['preferred_days'] = [int(day) for day in
                                                read_items('偏好星期（逗號分隔；留空無）：')]
                errors = validate_preferences(preferences)
                if errors:
                    raise ValueError('\n'.join(errors))
                candidates = filter_courses(data['courses'], preferences, data['enrollments'])
                show_result(dict(ok=True, data=candidates, errors=[]), 'courses', data)
                missing = set(preferences['mandatory_courses']) - {c['course_id'] for c in candidates}
                if missing:
                    print('必修課未列入候選：' + ', '.join(sorted(missing)))
                print('候選課程尚未組成課表；可另做單門可行性及清單學分檢查。')
            elif choice == '2':
                student = input('學號：').strip()
                course = input('課程代號：').strip()
                constraints = dict(unavailable_slots=read_slots())
                times = read_period_times(data)
                result = check_course_feasibility(student, course, data, constraints, times)
                print('可行性檢查通過，尚未加選或存檔。' if result['ok'] else
                      '\n'.join(result['errors']))
            elif choice == '3':
                identifiers = read_items('課程代號清單（逗號分隔）：')
                courses = {c['course_id']: c for c in data['courses']}
                unknown = set(identifiers) - set(courses)
                if unknown:
                    raise ValueError('課程不存在：' + ', '.join(sorted(unknown)))
                if len(identifiers) != len(set(identifiers)):
                    raise ValueError('課程代號不可重複。')
                limits = read_credit_limits()
                selected = [courses[cid] for cid in identifiers]
                errors = check_credit_range(selected, limits.get('min_credits'), limits.get('max_credits'))
                print(f"清單總學分：{sum(c['credits'] for c in selected)}")
                print('\n'.join(errors) if errors else '學分檢查通過。')
            else:
                print('無效選項。')
        except ValueError as error:
            print(f'輸入錯誤：{error}')


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
            print('\n學生選課與校園規劃系統\n1. 課程管理\n2. 學生管理\n3. 選課檢查與加選\n'
                  '4. 個人課表與空閒查詢\n5. 活動與教室配置\n6. 課程篩選與可行性檢查\n0. 離開')
            choice = input('請選擇：').strip()
            if choice == '0':
                return
            if choice in ('1', '2'):
                manage_menu('courses' if choice == '1' else 'students', data, directory)
            elif choice == '3':
                enrollment_menu(data, directory)
            elif choice == '4':
                timetable_menu(data)
            elif choice == '5':
                activity_menu(data, directory)
            elif choice == '6':
                course_filter_menu(data)
            else:
                print('無效選項。')
    except (EOFError, KeyboardInterrupt):
        print('\n已結束；成功的操作均已存檔。')


if __name__ == '__main__':
    main()
