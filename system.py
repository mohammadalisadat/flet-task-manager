import flet as ft
import flet_charts as fc
import sqlite3
import datetime

# ==========================================
# 1. اتصال به دیتابیس SQLite و ساخت جداول
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

db_connection.commit()


CATEGORIES = ["پروژه‌های دانشگاهی", "ترجمه و مطالعه", "کدنویسی و توسعه", "امور شخصی"]

try:
    import flet_charts as fc
    CHARTS_AVAILABLE = True
except:
    CHARTS_AVAILABLE = False

def main(page: ft.Page):
    page.title = "سیستم مدیریت شخصی - نسخه پرو"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1100
    page.window_height = 750

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
        )

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

            if CHARTS_AVAILABLE:
                cat_chart = fc.PieChart(
                    sections=[
                        fc.PieChartSection(value=c_comp if c_total > 0 else 1, color=ft.Colors.BLUE_400, radius=20,
                                           title=""),
                        fc.PieChartSection(value=c_pend if c_total > 0 else 0, color=ft.Colors.GREY_300, radius=20,
                                           title=""),
                    ],
                    sections_space=1,
                    center_space_radius=15,
                )
            else:
                cat_chart = ft.Text("Chart unavailable", size=10)

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
                        ft.Checkbox(label=s_title, value=bool(s_comp), on_change=make_update_sub(s_id))
                    )

                sub_input = ft.TextField(hint_text="افزودن زیرهدف جدید...", height=40, expand=True, text_size=12)

                goal_card = ft.Card(content=ft.Container(padding=15, content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Text(cat, size=11, color=ft.Colors.WHITE),
                                     bgcolor=ft.Colors.BLUE_GREY_800, padding=4, border_radius=4),
                        ft.Text(text, expand=True, weight=ft.FontWeight.BOLD, size=16),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_300, on_click=make_del_goal(g_id))
                    ]),
                    ft.ProgressBar(value=progress_val, color=ft.Colors.GREEN_500, bgcolor=ft.Colors.GREY_200),
                    ft.Text(f"پیشرفت: {comp_subs} از {total_subs} زیرهدف انجام شده", size=11, color=ft.Colors.GREY_500),
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
        task_title_input = ft.TextField(label="عنوان کار", width=350)

        selected_date_lbl = ft.Text("تاریخ: انتخاب نشده", color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD)
        selected_time_lbl = ft.Text("ساعت: انتخاب نشده", color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD)

        def update_date_lbl(e):
            if date_picker.value:
                selected_date_lbl.value = f"تاریخ: {date_picker.value.strftime('%Y-%m-%d')}"
            page.update()

        def update_time_lbl(e):
            if time_picker.value:
                selected_time_lbl.value = f"ساعت: {time_picker.value.strftime('%H:%M')}"
            page.update()

        date_picker.on_change = update_date_lbl
        time_picker.on_change = update_time_lbl

        def open_date(e):
            date_picker.open = True
            page.update()

        def open_time(e):
            time_picker.open = True
            page.update()

        date_btn = ft.ElevatedButton("انتخاب تقویم", icon=ft.Icons.CALENDAR_MONTH, on_click=open_date)
        time_btn = ft.ElevatedButton("انتخاب ساعت", icon=ft.Icons.ACCESS_TIME, on_click=open_time)

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

                db_cursor.execute("INSERT INTO tasks (title, deadline, category, is_completed) VALUES (?, ?, ?, 0)",
                                  (task_title_input.value, deadline_str, task_cat_dropdown.value))
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
            ft.Row([task_cat_dropdown, task_title_input]),
            ft.Row([date_btn, selected_date_lbl, ft.Container(width=20), time_btn, selected_time_lbl]),
            ft.Container(height=10),
            ft.Row([ft.ElevatedButton("ذخیره تسک", icon=ft.Icons.SAVE, on_click=save_task_to_db), feedback_text])
        ])

    def create_tasks_list_view():
        tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        search_input = ft.TextField(hint_text="جستجو در عنوان...", prefix_icon=ft.Icons.SEARCH, expand=True)
        filter_dropdown = ft.Dropdown(options=[ft.dropdown.Option("همه")] + [ft.dropdown.Option(c) for c in CATEGORIES],
                                      value="همه", width=180)

        def load_tasks(e=None):
            tasks_column.controls.clear()
            query = "SELECT id, title, deadline, category, is_completed FROM tasks WHERE 1=1"
            params = []
            if search_input.value:
                query += " AND title LIKE ?"
                params.append(f"%{search_input.value}%")
            if filter_dropdown.value != "همه":
                query += " AND category = ?"
                params.append(filter_dropdown.value)

            query += " ORDER BY is_completed ASC, id DESC"
            db_cursor.execute(query, params)

            for task in db_cursor.fetchall():
                t_id, title, deadline, cat, is_completed = task

                def update_status(e, task_id=t_id):
                    new_status = 1 if e.control.value else 0
                    db_cursor.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (new_status, task_id))
                    db_connection.commit()

                def delete_task(e, task_id=t_id):
                    db_cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                    db_connection.commit()
                    load_tasks()
                    page.update()

                task_row = ft.Row([
                    ft.Container(content=ft.Text(cat, size=11, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                                 bgcolor=ft.Colors.TEAL_600, padding=4, border_radius=4, width=110),
                    ft.Checkbox(label=f"{title} (مهلت: {deadline})", value=bool(is_completed), on_change=update_status,
                                expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=delete_task)
                ])
                tasks_column.controls.append(task_row)
            page.update()

        search_input.on_change = load_tasks
        filter_dropdown.on_change = load_tasks
        load_tasks()

        return ft.Column([
            ft.Text("لیست و جستجوی کارها", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([search_input, filter_dropdown]),
            ft.Divider(),
            tasks_column
        ], expand=True)

    def create_recurring_tasks_view():
        base_date = datetime.date.today()
        today_str = base_date.strftime('%Y-%m-%d')
        new_routine_input = ft.TextField(label="تعریف روتین جدید", width=300)
        routines_column = ft.Column(spacing=10)
        chart_container = ft.Container(height=200, expand=True)

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
            routines_column.controls.clear()

            # 1. مکانیزم ماشین زمان: اطمینان از وجود دیتای 7 روز گذشته (حتی روزهایی که برنامه باز نشده)
            db_cursor.execute("SELECT id FROM routines")
            all_routines = db_cursor.fetchall()

            for i in range(7):
                day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                for r in all_routines:
                    db_cursor.execute(
                        "INSERT OR IGNORE INTO routine_logs (routine_id, log_date, is_completed) VALUES (?, ?, 0)",
                        (r[0], day_str))
            db_connection.commit()

            # 2. فراخوانی لیست امروز برای تیک زدن
            db_cursor.execute("""
                SELECT r.id, r.title, l.is_completed 
                FROM routines r JOIN routine_logs l ON r.id = l.routine_id 
                WHERE l.log_date = ?
            """, (today_str,))

            for routine in db_cursor.fetchall():
                r_id, title, is_completed = routine
                routines_column.controls.append(ft.Row([
                    ft.Checkbox(label=title, value=bool(is_completed), on_change=make_update_routine(r_id),
                                expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=make_delete_routine(r_id))
                ]))

            # 3. ساخت چارت پیوسته برای دقیقا 7 روز اخیر
            bar_groups_list = []
            for i in range(6, -1, -1):  # از 6 روز پیش تا امروز (0)
                day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                db_cursor.execute("SELECT SUM(is_completed) FROM routine_logs WHERE log_date=?", (day_str,))
                res = db_cursor.fetchone()
                comp = res[0] if res[0] else 0

                bar_groups_list.append(
                    fc.BarChartGroup(
                        x=6 - i,
                        rods=[fc.BarChartRod(to_y=comp, width=20, color=ft.Colors.BLUE_400, border_radius=4)]
                    )
                )

            # پیدا کردن حداکثر مقدار محور Y برای تنظیم ارتفاع چارت
            db_cursor.execute(
                "SELECT log_date, SUM(is_completed) FROM routine_logs GROUP BY log_date ORDER BY log_date DESC LIMIT 7")
            data = db_cursor.fetchall()
            max_val = max([r[1] for r in data]) if data else 5

            if bar_groups_list:
                chart_container.content = fc.BarChart(
                    groups=bar_groups_list,
                    max_y=max_val + 1
                )

            page.update()

        def add_new_routine(e):
            if new_routine_input.value:
                db_cursor.execute("INSERT INTO routines (title) VALUES (?)", (new_routine_input.value,))
                r_id = db_cursor.lastrowid

                # پر کردن 7 روز گذشته با صفر برای این روتین جدید
                for i in range(7):
                    day_str = (base_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    db_cursor.execute("INSERT INTO routine_logs (routine_id, log_date, is_completed) VALUES (?, ?, 0)",
                                      (r_id, day_str))

                db_connection.commit()
                new_routine_input.value = ""
                load_routines()

        load_routines()
        return ft.Column([
            ft.Text(f"روتین‌های روزانه - تاریخ امروز: {today_str}", size=24, weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Row([new_routine_input,
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE, on_click=add_new_routine)]),
            ft.Divider(),
            ft.Row([
                ft.Container(content=routines_column, expand=1),
                ft.VerticalDivider(),
                ft.Container(
                    content=ft.Column([ft.Text("عملکرد ۷ روز گذشته", weight=ft.FontWeight.BOLD), chart_container]),
                    expand=1)
            ], expand=True)
        ], expand=True)

    # محاسبه سن از تاریخ تولد
    def calculate_age_from_birthdate(birthdate_str):
        """
        دریافت تاریخ تولد و تبدیل آن به سن
        فرمت تاریخ: YYYY-MM-DD
        """
        try:
            birthdate = datetime.datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.date.today()

            age = today.year - birthdate.year

            if (today.month, today.day) < (birthdate.month, birthdate.day):
                age -= 1

            return age
        except:
            return "-"

    # ==========================================
    # بخش آنالیز و وضعیت جسمانی (اصلاح شده و ماندگار)
    # ==========================================
    def create_profile_view():

        # خواندن اطلاعات
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

        birthdate_text = ft.Text(
            value=f"تاریخ تولد: {birthdate_val if birthdate_val else 'ثبت نشده'}",
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )

        # DatePicker
        birth_picker = ft.DatePicker()
        page.overlay.append(birth_picker)

        # محاسبه سن
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

        # محاسبه BMI
        def calculate_bmi(h, w):
            try:
                h = float(h) / 100
                w = float(w)

                bmi = w / (h * h)

                if bmi < 18.5:
                    status = "کمبود وزن"
                    color = ft.Colors.ORANGE
                elif bmi < 25:
                    status = "نرمال"
                    color = ft.Colors.GREEN
                elif bmi < 30:
                    status = "اضافه وزن"
                    color = ft.Colors.ORANGE_700
                else:
                    status = "چاقی"
                    color = ft.Colors.RED

                bmi_text.color = color
                return f"BMI: {bmi:.1f} ({status})"

            except:
                return "برای محاسبه BMI قد و وزن وارد کنید"

        # مقدار اولیه
        if birthdate_val:
            age_text.value = f"سن: {calculate_age(birthdate_val)}"
        else:
            age_text.value = "سن: -"

        bmi_text.value = calculate_bmi(height_val, weight_val)

        # باز کردن تقویم
        def open_birth_picker(e):
            if not birthdate_val:
                birth_picker.open = True
                page.update()

        # وقتی تاریخ انتخاب شد
        def birth_selected(e):

            if birth_picker.value:
                selected = birth_picker.value.strftime("%Y-%m-%d")

                db_cursor.execute(
                    "UPDATE user_profile SET value=? WHERE key='birthdate'",
                    (selected,)
                )

                db_connection.commit()

                birthdate_text.value = f"تاریخ تولد: {selected}"
                age_text.value = f"سن: {calculate_age(selected)}"

                birth_button.disabled = True

                page.update()

        birth_picker.on_change = birth_selected

        # دکمه انتخاب تاریخ
        birth_button = ft.ElevatedButton(
            "انتخاب تاریخ تولد",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=open_birth_picker,
            disabled=True if birthdate_val else False
        )

        # ذخیره قد و وزن
        def save_profile(e):

            db_cursor.execute(
                "UPDATE user_profile SET value=? WHERE key='height'",
                (height_input.value,)
            )

            db_cursor.execute(
                "UPDATE user_profile SET value=? WHERE key='weight'",
                (weight_input.value,)
            )

            db_connection.commit()

            bmi_text.value = calculate_bmi(height_input.value, weight_input.value)

            page.update()

        save_button = ft.ElevatedButton(
            "ذخیره تغییرات",
            icon=ft.Icons.SAVE,
            on_click=save_profile
        )

        info_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("اطلاعات فعلی", size=20, weight=ft.FontWeight.BOLD),
                    age_text,
                    bmi_text
                ],
                spacing=10
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.BLUE_50
        )

        edit_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("ویرایش اطلاعات", size=20, weight=ft.FontWeight.BOLD),
                    birth_button,
                    birthdate_text,
                    height_input,
                    weight_input,
                    save_button
                ],
                spacing=15
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.GREY_100
        )

        return ft.Column(
            [
                info_card,
                edit_card
            ],
            spacing=20
        )

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
        ], horizontal_alignment="center"),
        padding=15
    )

    main_content_area = ft.Container(content=create_dashboard_view(), expand=True, padding=20)

    def handle_menu_selection(e):
        selected_index = e.control.selected_index
        views = [create_dashboard_view, create_goals_view, create_add_task_view, create_tasks_list_view,
                 create_recurring_tasks_view, create_profile_view]
        main_content_area.content = views[selected_index]()
        main_content_area.update()

    sidebar_menu = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        extended=True,
        min_width=120,
        min_extended_width=220,
        leading=profile_section,
        trailing=theme_button,
        on_change=handle_menu_selection,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="داشبورد"),
            ft.NavigationRailDestination(icon=ft.Icons.FLAG, label="اهداف"),
            ft.NavigationRailDestination(icon=ft.Icons.ADD_BOX, label="افزودن کار"),
            ft.NavigationRailDestination(icon=ft.Icons.LIST, label="لیست کارها"),
            ft.NavigationRailDestination(icon=ft.Icons.REPEAT, label="کارهای روزانه"),
            ft.NavigationRailDestination(icon=ft.Icons.PERSON, label="وضعیت جسمانی"),
        ]
    )

    page.add(ft.Row([sidebar_menu, ft.VerticalDivider(width=1), main_content_area], expand=True))
    page.update()


# اجرا
ft.run(main, view=ft.AppView.WEB_BROWSER)