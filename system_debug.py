import flet as ft
import sqlite3
import datetime
import calendar

# بررسی وجود کتابخانه چارت
try:
    import flet_charts as fc

    CHARTS_AVAILABLE = True
except:
    CHARTS_AVAILABLE = False


# ==========================================
# تابع جادویی تبدیل میلادی به شمسی (بدون نیاز به کتابخانه خارجی)
# ==========================================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy if gm > 2 else gy - 1
    days = 365 * gy + int((gy + 3) / 4) - int((gy + 99) / 100) + int((gy + 399) / 400) - 80 + gd + g_d_m[gm - 1]
    gy += 1
    if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
        if gm > 2: days += 1
    jy = -1595 + 33 * int(days / 12053)
    days %= 12053
    jy += 4 * int(days / 1461)
    days %= 1461
    if days > 365:
        jy += int((days - 1) / 365)
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + int(days / 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + int((days - 186) / 30)
        jd = 1 + ((days - 186) % 30)
    return f"{jy}/{jm:02d}/{jd:02d}"


def format_date_to_shamsi(date_str):
    if not date_str or "بدون مهلت" in date_str:
        return date_str
    try:
        parts = date_str.split(" | ")
        d_part = parts[0]
        y, m, d = map(int, d_part.split("-"))
        shamsi_date = gregorian_to_jalali(y, m, d)

        if len(parts) > 1:
            return f"{shamsi_date} | {parts[1]}"
        return shamsi_date
    except:
        return date_str


# ==========================================
# 1. اتصال به دیتابیس SQLite
# ==========================================
db_connection = sqlite3.connect("my_database_v2.db", check_same_thread=False)
db_cursor = db_connection.cursor()

db_cursor.execute(
    '''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, deadline TEXT, category TEXT, is_completed INTEGER DEFAULT 0)''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS routines (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)''')
db_cursor.execute(
    '''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, goal_text TEXT)''')
db_cursor.execute(
    '''CREATE TABLE IF NOT EXISTS sub_goals (id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, title TEXT, is_completed INTEGER DEFAULT 0)''')
db_cursor.execute(
    '''CREATE TABLE IF NOT EXISTS routine_logs (routine_id INTEGER, log_date TEXT, is_completed INTEGER DEFAULT 0, UNIQUE(routine_id, log_date))''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS user_profile (key TEXT PRIMARY KEY, value TEXT)''')

db_cursor.execute("INSERT OR IGNORE INTO user_profile (key, value) VALUES ('age', '')")
db_cursor.execute("INSERT OR IGNORE INTO user_profile (key, value) VALUES ('height', '')")
db_cursor.execute("INSERT OR IGNORE INTO user_profile (key, value) VALUES ('weight', '')")
db_cursor.execute("INSERT OR IGNORE INTO user_profile (key, value) VALUES ('birthdate', '')")

try:
    db_cursor.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 1")
except sqlite3.OperationalError:
    pass

db_connection.commit()

CATEGORIES = ["پروژه‌های دانشگاهی", "ترجمه و مطالعه", "کدنویسی و توسعه", "امور شخصی"]
PRIORITIES = {"بالا": 3, "متوسط": 2, "پایین": 1}
PRIORITY_COLORS = {3: ft.Colors.RED_400, 2: ft.Colors.ORANGE_400, 1: ft.Colors.BLUE_400}


def main(page: ft.Page):
    page.title = "سیستم مدیریت شخصی - نسخه پرو مکس"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1150
    page.window_height = 800

    date_picker = ft.DatePicker()
    time_picker = ft.TimePicker()
    page.overlay.append(date_picker)
    page.overlay.append(time_picker)

    # ==========================================
    # 2. توابع سازنده صفحات
    # ==========================================

    def create_dashboard_view():
        dashboard_content = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
        dashboard_content.controls.append(ft.Text("گزارش عملکرد کلی و تفکیکی", size=24, weight=ft.FontWeight.BOLD))
        dashboard_content.controls.append(ft.Divider())

        db_cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks")
        result = db_cursor.fetchone()
        total_tasks = result[0] if result[0] else 0
        completed_tasks = result[1] if result[1] else 0
        pending_tasks = total_tasks - completed_tasks

        main_chart = fc.PieChart(
            sections=[
                fc.PieChartSection(value=completed_tasks if total_tasks > 0 else 1, color=ft.Colors.GREEN_400,
                                   radius=40, title=f"{completed_tasks}" if total_tasks > 0 else ""),
                fc.PieChartSection(value=pending_tasks if total_tasks > 0 else 0, color=ft.Colors.RED_400, radius=40,
                                   title=f"{pending_tasks}" if pending_tasks > 0 else ""),
            ], sections_space=2, center_space_radius=30, expand=True,
        ) if CHARTS_AVAILABLE else ft.Text("چارت‌ها در دسترس نیستند")

        dashboard_content.controls.append(
            ft.Row([
                ft.Card(content=ft.Container(padding=20, width=250, content=ft.Column([
                    ft.Text("آمار کل کارها", weight=ft.FontWeight.BOLD),
                    ft.Text(f"ثبت شده: {total_tasks}"),
                    ft.Text(f"انجام شده: {completed_tasks}", color=ft.Colors.GREEN),
                    ft.Text(f"مانده: {pending_tasks}", color=ft.Colors.RED),
                ]))),
                ft.Container(content=main_chart, width=200, height=150)
            ])
        )

        dashboard_content.controls.append(ft.Text("وضعیت به تفکیک بخش‌ها:", size=18, weight=ft.FontWeight.BOLD))
        categories_row = ft.Row(wrap=True, spacing=15)

        for cat in CATEGORIES:
            db_cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE category = ?", (cat,))
            cat_res = db_cursor.fetchone()
            c_total = cat_res[0] if cat_res[0] else 0
            c_comp = cat_res[1] if cat_res[1] else 0
            c_pend = c_total - c_comp

            cat_chart = fc.PieChart(
                sections=[
                    fc.PieChartSection(value=c_comp if c_total > 0 else 1, color=ft.Colors.BLUE_400, radius=20,
                                       title=""),
                    fc.PieChartSection(value=c_pend if c_total > 0 else 0, color=ft.Colors.GREY_300, radius=20,
                                       title=""),
                ], sections_space=1, center_space_radius=15,
            ) if CHARTS_AVAILABLE else ft.Text("")

            categories_row.controls.append(
                ft.Card(content=ft.Container(padding=15, width=220, content=ft.Column([
                    ft.Text(cat, weight=ft.FontWeight.BOLD, size=14),
                    ft.Row([
                        ft.Column([ft.Text(f"کل: {c_total}", size=12),
                                   ft.Text(f"انجام: {c_comp}", size=12, color=ft.Colors.BLUE)]),
                        ft.Container(content=cat_chart, width=60, height=60)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ])))
            )

        dashboard_content.controls.append(categories_row)
        return dashboard_content

    def create_goals_view():
        goal_cat_dropdown = ft.Dropdown(label="بخش مربوطه", width=200,
                                        options=[ft.dropdown.Option(c) for c in CATEGORIES], value=CATEGORIES[0])
        goal_text_input = ft.TextField(label="هدف اصلی جدید", width=400)
        goals_column = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)

        def make_update_sub(sub_id):
            def update(e):
                val = 1 if e.control.value else 0
                db_cursor.execute("UPDATE sub_goals SET is_completed=? WHERE id=?", (val, sub_id))
                db_connection.commit()
                load_goals()

            return update

        def make_add_sub(goal_id, text_field):
            def add(e):
                if text_field.value:
                    db_cursor.execute("INSERT INTO sub_goals (goal_id, title) VALUES (?, ?)",
                                      (goal_id, text_field.value))
                    db_connection.commit()
                    load_goals()

            return add

        def make_del_goal(g_id):
            def delete(e):
                db_cursor.execute("DELETE FROM goals WHERE id=?", (g_id,))
                db_cursor.execute("DELETE FROM sub_goals WHERE goal_id=?", (g_id,))
                db_connection.commit()
                load_goals()

            return delete

        def load_goals():
            goals_column.controls.clear()
            db_cursor.execute("SELECT id, category, goal_text FROM goals ORDER BY id DESC")

            for goal in db_cursor.fetchall():
                g_id, cat, text = goal
                db_cursor.execute("SELECT id, title, is_completed FROM sub_goals WHERE goal_id=?", (g_id,))
                subs = db_cursor.fetchall()

                total_subs = len(subs)
                comp_subs = sum([1 for s in subs if s[2]])
                progress_val = comp_subs / total_subs if total_subs > 0 else 0

                subs_list = ft.Column(spacing=5)
                for s_id, s_title, s_comp in subs:
                    subs_list.controls.append(
                        ft.Checkbox(label=s_title, value=bool(s_comp), on_change=make_update_sub(s_id)))

                sub_input = ft.TextField(hint_text="افزودن زیرهدف جدید...", height=40, expand=True, text_size=12)
                goal_card = ft.Card(content=ft.Container(padding=15, content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Text(cat, size=11, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700,
                                     padding=4, border_radius=4),
                        ft.Text(text, expand=True, weight=ft.FontWeight.BOLD, size=16),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=make_del_goal(g_id))
                    ]),
                    ft.ProgressBar(value=progress_val, color=ft.Colors.GREEN, bgcolor=ft.Colors.GREY_300),
                    ft.Text(f"پیشرفت: {comp_subs} از {total_subs} زیرهدف انجام شده", size=11),
                    ft.Divider(height=1),
                    subs_list,
                    ft.Row([sub_input, ft.IconButton(icon=ft.Icons.ADD, on_click=make_add_sub(g_id, sub_input))])
                ])))
                goals_column.controls.append(goal_card)
            page.update()

        def save_goal(e):
            if goal_text_input.value:
                db_cursor.execute("INSERT INTO goals (category, goal_text) VALUES (?, ?)",
                                  (goal_cat_dropdown.value, goal_text_input.value))
                db_connection.commit()
                goal_text_input.value = ""
                load_goals()

        load_goals()
        return ft.Column([
            ft.Text("هدف‌گذاری و مدیریت مسیر", size=24, weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Row([goal_cat_dropdown, goal_text_input,
                    ft.ElevatedButton("ثبت هدف اصلی", icon=ft.Icons.FLAG, on_click=save_goal)]),
            ft.Divider(), goals_column
        ], expand=True)

    def create_add_task_view():
        task_cat_dropdown = ft.Dropdown(label="دسته‌بندی", width=200,
                                        options=[ft.dropdown.Option(c) for c in CATEGORIES], value=CATEGORIES[0])
        priority_dropdown = ft.Dropdown(label="اولویت", width=150,
                                        options=[ft.dropdown.Option(k) for k in PRIORITIES.keys()], value="پایین")
        task_title_input = ft.TextField(label="عنوان کار", width=350)

        selected_date_lbl = ft.Text("تاریخ: انتخاب نشده", weight=ft.FontWeight.BOLD)
        selected_time_lbl = ft.Text("ساعت: انتخاب نشده", weight=ft.FontWeight.BOLD)

        def update_date_lbl(e):
            if date_picker.value:
                shamsi = gregorian_to_jalali(date_picker.value.year, date_picker.value.month, date_picker.value.day)
                selected_date_lbl.value = f"تاریخ: {shamsi}"
            page.update()

        def update_time_lbl(e):
            if time_picker.value:
                selected_time_lbl.value = f"ساعت: {time_picker.value.strftime('%H:%M')}"
            page.update()

        date_picker.on_change = update_date_lbl
        time_picker.on_change = update_time_lbl

        date_btn = ft.ElevatedButton("تقویم میلادی", icon=ft.Icons.CALENDAR_MONTH,
                                     on_click=lambda _: setattr(date_picker, 'open', True) or page.update())
        time_btn = ft.ElevatedButton("ساعت", icon=ft.Icons.ACCESS_TIME,
                                     on_click=lambda _: setattr(time_picker, 'open', True) or page.update())

        feedback_text = ft.Text(color=ft.Colors.GREEN)

        def save_task_to_db(e):
            if task_title_input.value:
                deadline_str = ""
                if date_picker.value:
                    deadline_str += date_picker.value.strftime('%Y-%m-%d')
                if time_picker.value:
                    deadline_str += " | " + time_picker.value.strftime('%H:%M')
                if not deadline_str:
                    deadline_str = "بدون مهلت تعیین شده"

                p_val = PRIORITIES.get(priority_dropdown.value, 1)

                db_cursor.execute(
                    "INSERT INTO tasks (title, deadline, category, is_completed, priority) VALUES (?, ?, ?, 0, ?)",
                    (task_title_input.value, deadline_str, task_cat_dropdown.value, p_val))
                db_connection.commit()

                task_title_input.value = ""
                date_picker.value = None
                time_picker.value = None
                selected_date_lbl.value = "تاریخ: انتخاب نشده"
                selected_time_lbl.value = "ساعت: انتخاب نشده"
                feedback_text.value = "تسک با موفقیت ذخیره شد!"
                page.update()

        return ft.Column([
            ft.Text("افزودن کار جدید", size=24, weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Row([task_cat_dropdown, priority_dropdown, task_title_input]),
            ft.Text("راهنما: تاریخ را از تقویم میلادی انتخاب کنید، سیستم خودکار آن را شمسی می‌کند.", size=12,
                    color=ft.Colors.GREY_500),
            ft.Row([date_btn, selected_date_lbl, ft.Container(width=20), time_btn, selected_time_lbl]),
            ft.Container(height=10),
            ft.Row([ft.ElevatedButton("ذخیره تسک", icon=ft.Icons.SAVE, on_click=save_task_to_db), feedback_text])
        ])

    def create_tasks_list_view():
        tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        search_input = ft.TextField(hint_text="جستجو در عنوان...", prefix_icon=ft.Icons.SEARCH, expand=True)
        filter_dropdown = ft.Dropdown(options=[ft.dropdown.Option("همه")] + [ft.dropdown.Option(c) for c in CATEGORIES],
                                      value="همه", width=180)

        def get_deadline_color(deadline_str):
            if not deadline_str or "بدون مهلت" in deadline_str:
                return None
            try:
                dt_part = deadline_str.split(" | ")[0].strip()
                tm_part = deadline_str.split(" | ")[1].strip() if " | " in deadline_str else "23:59"
                dl_date = datetime.datetime.strptime(f"{dt_part} {tm_part}", "%Y-%m-%d %H:%M")
                now = datetime.datetime.now()
                delta = dl_date - now

                if delta.total_seconds() < 0:
                    return ft.Colors.RED_100 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.RED_900
                elif delta.total_seconds() <= 86400:
                    return ft.Colors.ORANGE_100 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.ORANGE_900
                return None
            except:
                return None

        def load_tasks(e=None):
            tasks_column.controls.clear()
            query = "SELECT id, title, deadline, category, is_completed, priority FROM tasks WHERE 1=1"
            params = []
            if search_input.value:
                query += " AND title LIKE ?"
                params.append(f"%{search_input.value}%")
            if filter_dropdown.value != "همه":
                query += " AND category = ?"
                params.append(filter_dropdown.value)

            query += " ORDER BY is_completed ASC, priority DESC, deadline ASC, id DESC"
            db_cursor.execute(query, params)

            for task in db_cursor.fetchall():
                t_id, title, deadline, cat, is_completed, priority = task
                p_text = "بالا" if priority == 3 else "متوسط" if priority == 2 else "پایین"

                shamsi_deadline = format_date_to_shamsi(deadline)
                row_color = get_deadline_color(deadline) if not is_completed else None

                def update_status(e, task_id=t_id):
                    new_status = 1 if e.control.value else 0
                    db_cursor.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (new_status, task_id))
                    db_connection.commit()
                    load_tasks()

                def delete_task(e, task_id=t_id):
                    db_cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                    db_connection.commit()
                    load_tasks()

                task_row = ft.Container(
                    bgcolor=row_color,
                    border_radius=8,
                    padding=5,
                    content=ft.Row([
                        ft.Container(content=ft.Text(cat, size=11, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700,
                                     padding=4, border_radius=4, width=100),
                        ft.Container(content=ft.Text(f"اولویت {p_text}", size=11, color=ft.Colors.WHITE),
                                     bgcolor=PRIORITY_COLORS.get(priority, ft.Colors.GREY), padding=4, border_radius=4),
                        ft.Checkbox(label=f"{title} (مهلت: {shamsi_deadline})", value=bool(is_completed),
                                    on_change=update_status, expand=True),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=delete_task)
                    ])
                )
                tasks_column.controls.append(task_row)
            page.update()

        search_input.on_change = load_tasks
        filter_dropdown.on_change = load_tasks
        load_tasks()

        return ft.Column([
            ft.Text("لیست کارها (مرتب شده بر اساس اولویت و زمان)", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([search_input, filter_dropdown]),
            ft.Divider(),
            tasks_column
        ], expand=True)

    def create_recurring_tasks_view():
        base_date = datetime.date.today()
        today_str = base_date.strftime('%Y-%m-%d')
        today_shamsi = gregorian_to_jalali(base_date.year, base_date.month, base_date.day)

        new_routine_input = ft.TextField(label="تعریف روتین جدید", width=300)

        today_column = ft.Column(spacing=10)
        history_column = ft.Column(spacing=20)
        chart_container = ft.Container(height=250)

        def make_update_routine(r_id):
            def update(e):
                val = 1 if e.control.value else 0
                db_cursor.execute("UPDATE routine_logs SET is_completed=? WHERE routine_id=? AND log_date=?",
                                  (val, r_id, today_str))
                db_connection.commit()
                load_routines()

            return update

        def make_delete_routine(r_id):
            def delete(e):
                db_cursor.execute("DELETE FROM routines WHERE id=?", (r_id,))
                db_cursor.execute("DELETE FROM routine_logs WHERE routine_id=?", (r_id,))
                db_connection.commit()
                load_routines()

            return delete

        def load_routines():
            today_column.controls.clear()
            history_column.controls.clear()

            db_cursor.execute("SELECT id FROM routines")
            all_routines = db_cursor.fetchall()
            for i in range(7):
                day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                for r in all_routines:
                    db_cursor.execute(
                        "INSERT OR IGNORE INTO routine_logs (routine_id, log_date, is_completed) VALUES (?, ?, 0)",
                        (r[0], day_str))
            db_connection.commit()

            db_cursor.execute(
                "SELECT r.id, r.title, l.is_completed FROM routines r JOIN routine_logs l ON r.id = l.routine_id WHERE l.log_date = ?",
                (today_str,))
            for routine in db_cursor.fetchall():
                r_id, title, is_completed = routine
                today_column.controls.append(ft.Row([
                    ft.Checkbox(label=title, value=bool(is_completed), on_change=make_update_routine(r_id),
                                expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=make_delete_routine(r_id))
                ]))

            # تاریخچه 7 روزه
            for i in range(1, 8):
                h_date = base_date - datetime.timedelta(days=i)
                h_date_str = h_date.strftime('%Y-%m-%d')
                h_date_shamsi = gregorian_to_jalali(h_date.year, h_date.month, h_date.day)

                db_cursor.execute(
                    "SELECT r.title, l.is_completed FROM routines r JOIN routine_logs l ON r.id = l.routine_id WHERE l.log_date = ?",
                    (h_date_str,))
                day_routines = db_cursor.fetchall()
                if day_routines:
                    day_card = ft.Card(content=ft.Container(padding=10, content=ft.Column([
                        ft.Text(f"تاریخ: {h_date_shamsi}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600)
                    ])))
                    for r_title, r_comp in day_routines:
                        day_card.content.content.controls.append(
                            ft.Checkbox(label=r_title, value=bool(r_comp), disabled=True))
                    history_column.controls.append(day_card)

            # چارت 7 روز
            bar_groups_list = []
            for i in range(6, -1, -1):
                day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                db_cursor.execute("SELECT SUM(is_completed) FROM routine_logs WHERE log_date=?", (day_str,))
                res = db_cursor.fetchone()
                comp = res[0] if res[0] else 0
                bar_groups_list.append(fc.BarChartGroup(x=6 - i, rods=[
                    fc.BarChartRod(to_y=comp, width=20, color=ft.Colors.BLUE_600, border_radius=4)]))

            db_cursor.execute(
                "SELECT SUM(is_completed) FROM routine_logs GROUP BY log_date ORDER BY log_date DESC LIMIT 7")
            data = db_cursor.fetchall()
            max_val = max([r[0] for r in data if r[0] is not None]) if data else 5

            if bar_groups_list and CHARTS_AVAILABLE:
                chart_container.content = fc.BarChart(groups=bar_groups_list, max_y=max_val + 1)
            else:
                chart_container.content = ft.Text("دیتایی برای چارت وجود ندارد")

            page.update()

        def add_new_routine(e):
            if new_routine_input.value:
                db_cursor.execute("INSERT INTO routines (title) VALUES (?)", (new_routine_input.value,))
                r_id = db_cursor.lastrowid
                for i in range(7):
                    day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    db_cursor.execute("INSERT INTO routine_logs (routine_id, log_date, is_completed) VALUES (?, ?, 0)",
                                      (r_id, day_str))
                db_connection.commit()
                new_routine_input.value = ""
                load_routines()

        load_routines()

        # به جای Tab که ارور می‌داد، از یک Layout عمودی یکپارچه با اسکرول استفاده کردیم
        return ft.Column([
            ft.Text(f"روتین‌های روزانه - امروز: {today_shamsi}", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([new_routine_input,
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_600, on_click=add_new_routine)]),
            ft.Divider(),
            ft.Text("کارهای امروز و چارت عملکرد", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Container(content=today_column, expand=1),
                ft.VerticalDivider(),
                ft.Container(content=chart_container, expand=1)
            ]),
            ft.Divider(),
            ft.Text("جزئیات تاریخچه (۷ روز گذشته)", size=18, weight=ft.FontWeight.BOLD),
            history_column
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def create_calendar_view():
        now = datetime.datetime.now()
        cal_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=20)

        month_days = calendar.monthcalendar(now.year, now.month)
        day_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]

        header_row = ft.Row(
            [ft.Container(content=ft.Text(d, weight=ft.FontWeight.BOLD, text_align="center"), expand=1) for d in
             day_names])
        shamsi_title = gregorian_to_jalali(now.year, now.month, 1)

        cal_col.controls.append(
            ft.Text(f"تقویم تسک‌ها (سیستم میلادی - همگام با ماه {shamsi_title})", size=24, weight=ft.FontWeight.BOLD))
        cal_col.controls.append(header_row)

        for week in month_days:
            week_row = ft.Row(expand=True)
            for day in week:
                if day == 0:
                    week_row.controls.append(ft.Container(expand=1))
                else:
                    date_str = f"{now.year}-{now.month:02d}-{day:02d}"
                    db_cursor.execute("SELECT title, is_completed FROM tasks WHERE deadline LIKE ?", (f"{date_str}%",))
                    day_tasks = db_cursor.fetchall()

                    task_indicators = ft.Column(spacing=2)
                    for t, c in day_tasks:
                        color = ft.Colors.GREEN if c else ft.Colors.BLUE_600
                        task_indicators.controls.append(ft.Text(f"• {t}", size=10, color=color, no_wrap=True))

                    # ارور border با جایگزین کردن margin و bgcolor حل شد!
                    day_container = ft.Container(
                        content=ft.Column([
                            ft.Text(str(day), weight=ft.FontWeight.BOLD),
                            task_indicators
                        ]),
                        expand=1,
                        margin=2,  # فاصله جایگزین خط حاشیه شد
                        border_radius=5,
                        padding=5,
                        height=100,
                        bgcolor=ft.Colors.GREY_200 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_GREY_900
                    )

                    # اگر در این روز تسک وجود داشت، رنگ بک‌گراند کمی روشن‌تر می‌شود
                    if day_tasks:
                        day_container.bgcolor = ft.Colors.BLUE_50 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_900

                    week_row.controls.append(day_container)
            cal_col.controls.append(week_row)

        return cal_col

    def create_profile_view():
        db_cursor.execute("SELECT value FROM user_profile WHERE key='birthdate'")
        birthdate_val = db_cursor.fetchone()[0]
        db_cursor.execute("SELECT value FROM user_profile WHERE key='height'")
        height_val = db_cursor.fetchone()[0]
        db_cursor.execute("SELECT value FROM user_profile WHERE key='weight'")
        weight_val = db_cursor.fetchone()[0]

        height_input = ft.TextField(label="قد (سانتی متر)", value=height_val, width=150)
        weight_input = ft.TextField(label="وزن (کیلوگرم)", value=weight_val, width=150)

        age_text = ft.Text(size=16)
        bmi_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)

        birth_shamsi = format_date_to_shamsi(birthdate_val) if birthdate_val else 'ثبت نشده'
        birthdate_text = ft.Text(value=f"تاریخ تولد: {birth_shamsi}", weight=ft.FontWeight.BOLD,
                                 color=ft.Colors.BLUE_700)

        birth_picker = ft.DatePicker()
        page.overlay.append(birth_picker)

        def calculate_age(birthdate_str):
            try:
                birth = datetime.datetime.strptime(birthdate_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                age = today.year - birth.year
                if (today.month, today.day) < (birth.month, birth.day):
                    age -= 1
                return age
            except:
                return "-"

        def calculate_bmi(h, w):
            try:
                h = float(h) / 100
                w = float(w)
                bmi = w / (h * h)

                if bmi < 18.5:
                    status, color = "کمبود وزن", ft.Colors.ORANGE
                elif bmi < 25:
                    status, color = "نرمال", ft.Colors.GREEN
                elif bmi < 30:
                    status, color = "اضافه وزن", ft.Colors.ORANGE_700
                else:
                    status, color = "چاقی", ft.Colors.RED

                bmi_text.color = color
                return f"BMI: {bmi:.1f} ({status})"
            except:
                return "برای محاسبه BMI قد و وزن وارد کنید"

        if birthdate_val:
            age_text.value = f"سن: {calculate_age(birthdate_val)}"
        else:
            age_text.value = "سن: -"

        bmi_text.value = calculate_bmi(height_val, weight_val)

        def open_birth_picker(e):
            birth_picker.open = True
            page.update()

        def birth_selected(e):
            if birth_picker.value:
                selected = birth_picker.value.strftime("%Y-%m-%d")
                db_cursor.execute("UPDATE user_profile SET value=? WHERE key='birthdate'", (selected,))
                db_connection.commit()
                birthdate_text.value = f"تاریخ تولد: {format_date_to_shamsi(selected)}"
                age_text.value = f"سن: {calculate_age(selected)}"
                page.update()

        birth_picker.on_change = birth_selected
        birth_button = ft.ElevatedButton("انتخاب تاریخ تولد", icon=ft.Icons.CALENDAR_MONTH, on_click=open_birth_picker)

        def save_profile(e):
            db_cursor.execute("UPDATE user_profile SET value=? WHERE key='height'", (height_input.value,))
            db_cursor.execute("UPDATE user_profile SET value=? WHERE key='weight'", (weight_input.value,))
            db_connection.commit()
            bmi_text.value = calculate_bmi(height_input.value, weight_input.value)
            page.update()

        save_button = ft.ElevatedButton("ذخیره تغییرات", icon=ft.Icons.SAVE, on_click=save_profile)

        info_card = ft.Container(
            content=ft.Column([ft.Text("اطلاعات فعلی", size=20, weight=ft.FontWeight.BOLD), age_text, bmi_text],
                              spacing=10),
            padding=20, border_radius=10,
            bgcolor=ft.Colors.BLUE_50 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_GREY_900
        )

        edit_card = ft.Container(
            content=ft.Column(
                [ft.Text("ویرایش اطلاعات", size=20, weight=ft.FontWeight.BOLD), birth_button, birthdate_text,
                 height_input, weight_input, save_button], spacing=15),
            padding=20, border_radius=10,
            bgcolor=ft.Colors.GREY_100 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_900
        )

        return ft.Column([info_card, edit_card], spacing=20)

    # ==========================================
    # 3. مدیریت قالب و منو
    # ==========================================
    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        theme_button.icon = ft.Icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE
        page.update()

    theme_button = ft.IconButton(icon=ft.Icons.DARK_MODE, on_click=toggle_theme, tooltip="تغییر تم")

    profile_section = ft.Container(
        content=ft.Column([
            ft.CircleAvatar(radius=40, bgcolor=ft.Colors.BLUE_700,
                            content=ft.Text("س.م", size=20, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)),
            ft.Text("سید محمدعلی", weight=ft.FontWeight.BOLD, size=15)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=15
    )

    main_content_area = ft.Container(content=create_dashboard_view(), expand=True, padding=20)

    def handle_menu_selection(e):
        views = [create_dashboard_view, create_goals_view, create_add_task_view, create_tasks_list_view,
                 create_calendar_view, create_recurring_tasks_view, create_profile_view]
        main_content_area.content = views[e.control.selected_index]()
        main_content_area.update()

    sidebar_menu = ft.NavigationRail(
        selected_index=0, label_type=ft.NavigationRailLabelType.ALL, extended=True, min_width=120,
        min_extended_width=220,
        leading=profile_section, trailing=theme_button, on_change=handle_menu_selection,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="داشبورد"),
            ft.NavigationRailDestination(icon=ft.Icons.FLAG, label="اهداف"),
            ft.NavigationRailDestination(icon=ft.Icons.ADD_BOX, label="افزودن کار"),
            ft.NavigationRailDestination(icon=ft.Icons.LIST, label="لیست کارها"),
            ft.NavigationRailDestination(icon=ft.Icons.CALENDAR_TODAY, label="تقویم تسک‌ها"),
            ft.NavigationRailDestination(icon=ft.Icons.REPEAT, label="کارهای روزانه"),
            ft.NavigationRailDestination(icon=ft.Icons.PERSON, label="وضعیت جسمانی"),
        ]
    )

    page.add(ft.Row([sidebar_menu, ft.VerticalDivider(width=1), main_content_area], expand=True))


# اجرا
ft.run(main, view=ft.AppView.WEB_BROWSER)