from db import get_connection
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta # <--- YENİ: timedelta ƏLAVƏ EDİLDİ
from dateutil.relativedelta import relativedelta # Tarix fərqini hesablamaq üçün
from functools import wraps # Dekoratorlar üçün
import socket # <--- KOMPYUTER ADINI ALMAQ ÜÇÜN İMPORT

# ----------------------------------------------------
# 1. FLASK TƏTBİQİNİN QURULMASI
# ----------------------------------------------------
app = Flask(__name__)
app.secret_key = 'ASIS_Sizin_Real_Gizli_Acariniz_Burada_Olsun' 


#  DB XƏRC ƏLAVƏ FUNKSIYASI
# ============================

def insert_expense(car_id, expense_type, amount, litr, description,
                   driver_id_at_expense, assistant_id_at_expense,
                   planner_id_at_expense, entered_by):
    """
    Yeni xərci MySQL-də expenses cədvəlinə yazır.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO expenses (
                    car_id,
                    amount,
                    type,
                    litr,
                    description,
                    entered_by,
                    driver_id_at_expense,
                    assistant_id_at_expense,
                    planner_id_at_expense
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                car_id,
                amount,
                expense_type,
                litr,
                description,
                entered_by,
                driver_id_at_expense,
                assistant_id_at_expense,
                planner_id_at_expense
            ))
        conn.commit()
    finally:
        conn.close()

# ----------------------------------------------------
# 3. KÖMƏKÇİ FUNKSİYALARI (LOGGING YENİLƏNDİ)
# ----------------------------------------------------

def log_action(action, details, status='success'):
    """Audit loqu qeydə alır (YENİLƏNİB - Kompyuter adı ilə)."""
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        hostname = ip # Əgər adı tapılmazsa, IP-ni göstər
        
        try:
            # 127.0.0.1 (localhost) üçün reverse lookup cəhd etməyə dəyməz
            if ip == '127.0.0.1' or ip.startswith('::1'):
                hostname = 'localhost'
            else:
                # IP-dən kompyuter adını (hostname) almağa cəhd et
                # QEYD: Bu əməliyyat şəbəkə ayarlarından asılı olaraq bir neçə saniyə çəkə bilər
                socket.setdefaulttimeout(0.5) # Gözləməni 0.5 saniyəyə azalt
                hostname_info = socket.gethostbyaddr(ip)
                hostname = hostname_info[0] # Nəticəni (kompyuter adını) götür
        except (socket.herror, socket.gaierror, socket.timeout):
            # Əgər adı tapa bilməsə (məs. DNS-də yoxdursa), IP adresin özü qalsın
            hostname = ip # Uğursuz olarsa, IP-ni qaytar
        finally:
            socket.setdefaulttimeout(None) # Standard zaman aşımını bərpa et

        log_entry = {
            "timestamp": datetime.now(),
            "username": session.get('user', 'System'),
            "ip": ip, # IP ünvanını hər ehtimala qarşı saxlayırıq
            "hostname": hostname, # Kompyuter adını (və ya uğursuzdursa IP)
            "action": action,
            "details": details,
            "status": status
        }
        AUDIT_LOGS.append(log_entry)
    except Exception as e:
        print(f"!!! Loq xətası: {e}")

def get_car_by_id(car_id):
    if not car_id:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, car_number, model, brand, model_name, category,
                       driver_id, assistant_id, planner_id, notes
                FROM cars
                WHERE id = %s
            """, (car_id,))
            row = cursor.fetchone()
    finally:
        conn.close()
    return row
def get_driver_by_id(driver_id):
    if not driver_id:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, license_no, phone, start_date
                FROM drivers
                WHERE id = %s
            """, (driver_id,))
            row = cursor.fetchone()
    finally:
        conn.close()
    return row

def get_user_by_id(user_id):
    """Istifadəçini ID-yə görə MySQL-dən götürür."""
    if not user_id:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, fullname, username, password, role, is_active
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "fullname": row["fullname"],
        "username": row["username"],
        "password": row["password"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
    }


def get_user_by_username(username):
    """Istifadəçini username-ə görə MySQL-dən götürür."""
    if not username:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, fullname, username, password, role, is_active
                FROM users
                WHERE username = %s
                """,
                (username,)
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "fullname": row["fullname"],
        "username": row["username"],
        "password": row["password"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
    }


def get_assistant_by_id(aid):
    if not aid:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM assistants
                WHERE id = %s
            """, (aid,))
            row = cursor.fetchone()
    finally:
        conn.close()
    return row

def get_planner_by_id(pid):
    if not pid:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM planners
                WHERE id = %s
            """, (pid,))
            row = cursor.fetchone()
    finally:
        conn.close()
    return row

def get_all_drivers():
    """Bütün sürücüləri DB-dən gətirir."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, license_no, phone, start_date
                FROM drivers
                ORDER BY name
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return rows


def get_all_assistants():
    """Bütün köməkçiləri DB-dən gətirir."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM assistants
                ORDER BY name
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return rows


def get_all_planners():
    """Bütün planlamaçıları DB-dən gətirir."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM planners
                ORDER BY name
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return rows


def get_all_cars():
    """Bütün avtomobilləri DB-dən gətirir."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    car_number,
                    model,
                    brand,
                    model_name,
                    category,
                    driver_id,
                    assistant_id,
                    planner_id,
                    notes
                FROM cars
                ORDER BY car_number
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return rows


def get_operators():
    """Yalnız operatorları (role='user') gətirir."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, fullname, username, role, is_active
                FROM users
                WHERE role = 'user'
                ORDER BY fullname
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "fullname": r["fullname"],
            "username": r["username"],
            "role": r["role"],
            "is_active": bool(r["is_active"]),
        }
        for r in rows
    ]


def get_all_users():
    """Bütün istifadəçiləri gətirir (supervisor üçün operations səhifəsində istifadə olunur)."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, fullname, username, role, is_active
                FROM users
                ORDER BY fullname
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "fullname": r["fullname"],
            "username": r["username"],
            "role": r["role"],
            "is_active": bool(r["is_active"]),
        }
        for r in rows
    ]


def _derive_brand_and_model(car):
    brand = car.get('brand') or ""
    model_name = car.get('model_name') or ""
    if (not brand or not model_name) and car.get('model'):
        parts = car['model'].split(' ', 1)
        if not brand and parts: brand = parts[0]
        if not model_name and len(parts) > 1: model_name = parts[1]
    return brand, model_name

def get_dashboard_data():
    # Bütün kataloqları DB-dən çək
    drivers = get_all_drivers()
    assistants = get_all_assistants()
    planners = get_all_planners()
    cars = get_all_cars()

    driver_map = {d["id"]: d for d in drivers}
    assistant_map = {a["id"]: a for a in assistants}
    planner_map = {p["id"]: p for p in planners}

    full_data = []
    for car in cars:
        car_id = car["id"]
        car_expenses = [e for e in EXPENSES if e["car_id"] == car_id]
        total_expense = sum(e["amount"] for e in car_expenses)
        last_expense_entered_by = car_expenses[-1]["entered_by"] if car_expenses else "Yoxdur"

        detailed_expenses = []
        for e in sorted(car_expenses, key=lambda x: x["timestamp"], reverse=True):
            driver_at_expense = get_driver_by_id(e.get("driver_id_at_expense"))
            assistant_at_expense = get_assistant_by_id(e.get("assistant_id_at_expense"))
            planner_at_expense = get_planner_by_id(e.get("planner_id_at_expense"))
            detailed_expenses.append({
                "type": e["type"],
                "amount": e["amount"],
                "litr": e.get("litr", 0),
                "description": e["description"],
                "entered_by": e["entered_by"],
                "timestamp_str": e["timestamp"].strftime("%d.%m.%Y %H:%M"),
                "driver_name": driver_at_expense["name"] if driver_at_expense else "-",
                "assistant_name": assistant_at_expense["name"] if assistant_at_expense else "-",
                "planner_name": planner_at_expense["name"] if planner_at_expense else "-",
            })

        # brand/model_name üçün köhnə məntiqi saxlayırıq
        brand = car.get("brand") or ""
        model_name = car.get("model_name") or ""
        if (not brand or not model_name) and car.get("model"):
            parts = car["model"].split(" ", 1)
            if not brand and parts:
                brand = parts[0]
            if not model_name and len(parts) > 1:
                model_name = parts[1]

        driver = driver_map.get(car.get("driver_id"))
        assistant = assistant_map.get(car.get("assistant_id"))
        planner = planner_map.get(car.get("planner_id"))

        full_data.append({
            "id": car_id,
            "driver_id": car.get("driver_id"),
            "car_number": car["car_number"],
            "brand_model": f"{brand} / {model_name}".strip(" /"),
            "category": car.get("category", ""),
            "assistant_name": assistant["name"] if assistant else "",
            "planner_name": planner["name"] if planner else "",
            "driver_name": driver["name"] if driver else "TƏYİN OLUNMAYIB",
            "total_expense": total_expense,
            "entered_by": last_expense_entered_by,
            "notes": car.get("notes", ""),
            "expenses": detailed_expenses,
            "brand_raw": brand,
            "model_name_raw": model_name,
            "assistant_id": car.get("assistant_id"),
            "planner_id": car.get("planner_id"),
            "has_expenses": total_expense > 0
        })

    return full_data


def calculate_experience(start_date_str):
    if not start_date_str: return "-"
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        if start_date > today: return "Başlamayıb"
        delta = relativedelta(today, start_date)
        years = delta.years; months = delta.months
        experience_parts = []
        if years > 0: experience_parts.append(f"{years} il")
        if months > 0: experience_parts.append(f"{months} ay")
        if not experience_parts: return "Yeni" if delta.days >= 0 else "-" 
        return ", ".join(experience_parts)
    except ValueError: return "Tarix xətası" 

# ----------------------------------------------------
# 4. GİRİŞ VƏ İCAZƏ FUNKSİYALARI (YENİLƏNİB)
# ----------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        
        if user and user['password'] == password: 
            # YENİ: Aktivlik yoxlaması
            if not user.get('is_active', True): # Əgər is_active yoxdursa, default olaraq True qəbul et
                log_action('LOGIN_FAILURE', f"İstifadəçi '{username}' aktiv deyil.", 'failure')
                flash('Sizin hesabınız deaktiv edilib. Zəhmət olmasa rəhbərliklə əlaqə saxlayın.', 'danger')
                return render_template('login.html', error=None) # Flash mesajı istifadə olunduğu üçün error=None

            session['user'] = user['username']
            session['role'] = user['role']
            session['fullname'] = user['fullname']
            
            log_action('LOGIN_SUCCESS', f"İstifadəçi '{username}' daxil oldu.", 'success')
            flash(f"Xoş gəldiniz, {user['fullname']}!", 'success')
            
            # YENİ: Rola görə yönləndirmə
            if user['role'] == 'supervisor':
                return redirect(url_for('supervisor_dashboard'))
            # Admin və Operator əvvəlki kimi index-ə gedir
            return redirect(url_for('index'))
        else:
            log_action('LOGIN_FAILURE', f"İstifadəçi '{username}' üçün yanlış parol/istifadəçi adı.", 'failure')
            error = 'Yanlış istifadəçi adı və ya parol.'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('user', 'Bilinməyən')
    log_action('LOGOUT', f"İstifadəçi '{username}' çıxış etdi.", 'success')
    session.pop('user', None); session.pop('role', None); session.pop('fullname', None)
    flash("Sistemdən çıxış etdiniz.", 'info')
    return redirect(url_for('login'))

def is_admin():
    return session.get('role') == 'admin'

def is_operator():
    return session.get('role') == 'user'

# YENİ: Supervisor yoxlaması
def is_supervisor():
    return session.get('role') == 'supervisor'

# YENİ: İcazə dekoratorları
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            log_action('AUTH_FAILURE', f"Admin icazəsi olmayan cəhd: {request.path}", 'failure')
            flash('Bu səhifəyə daxil olmaq üçün Admin icazəniz yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (is_operator() or is_admin() or is_supervisor()): # Operator, Admin və Supervisor bura daxil ola bilər
            log_action('AUTH_FAILURE', f"Operator icazəsi olmayan cəhd: {request.path}", 'failure')
            flash('Bu səhifəyə daxil olmaq üçün icazəniz yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_supervisor():
            log_action('AUTH_FAILURE', f"Supervisor icazəsi olmayan cəhd: {request.path}", 'failure')
            flash('Bu səhifəyə daxil olmaq üçün Supervisor icazəniz yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------
# 5. ƏSAS SƏHİFƏ (DASHBOARD) - YENİLƏNİB
# ----------------------------------------------------
@app.route('/')
@login_required
def index():
    # Supervisor-u öz dashboardına yönləndir
    if session['role'] == 'supervisor':
        return redirect(url_for('supervisor_dashboard'))
    
    # === ADMİN DASHBOARD MƏLUMATLARI ===
    if session['role'] == 'admin':
        log_action('VIEW_PAGE', 'Admin Dashboarduna baxış', 'success')

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # operator sayı
                cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'user'")
                total_operator_count = cursor.fetchone()["cnt"]

                # maşın sayı
                cursor.execute("SELECT COUNT(*) AS cnt FROM cars")
                total_car_count = cursor.fetchone()["cnt"]

                # sürücü sayı
                cursor.execute("SELECT COUNT(*) AS cnt FROM drivers")
                total_driver_count = cursor.fetchone()["cnt"]

                # köməkçi sayı
                cursor.execute("SELECT COUNT(*) AS cnt FROM assistants")
                total_assistant_count = cursor.fetchone()["cnt"]

                # planlamaçı sayı
                cursor.execute("SELECT COUNT(*) AS cnt FROM planners")
                total_planner_count = cursor.fetchone()["cnt"]
        finally:
            conn.close()
        
        now = datetime.now()
        current_month_expenses = [
            e for e in EXPENSES 
            if e['timestamp'].month == now.month and e['timestamp'].year == now.year
        ]
        monthly_total = sum(e['amount'] for e in current_month_expenses)
        
        expense_data = {} 
        for e in current_month_expenses:
            e_type = e.get('type', 'Digər') 
            expense_data[e_type] = expense_data.get(e_type, 0) + e['amount']
        
        chart_labels = []
        chart_data_values = []
        for expense_type in EXPENSE_TYPES:
            if expense_type in expense_data:
                chart_labels.append(expense_type)
                chart_data_values.append(expense_data[expense_type])

        return render_template(
            'admin_dashboard.html', 
            user_role=session['role'],
            stats={
                'operator_count': total_operator_count, 
                'car_count': total_car_count,
                'driver_count': total_driver_count, 
                'assistant_count': total_assistant_count,
                'planner_count': total_planner_count,
                'monthly_total': monthly_total
            },
            chart_data={'labels': chart_labels, 'data': chart_data_values}
        )
    
    # === OPERATOR DASHBOARD MƏLUMATLARI ===
    log_action('VIEW_PAGE', 'Operator Dashboarduna baxış', 'success')
    dashboard_data = get_dashboard_data()

    # Kataloqları artıq DB-dən veririk
    drivers = get_all_drivers()
    assistants = get_all_assistants()
    planners = get_all_planners()

    return render_template(
        'operator_dashboard.html', 
        user_role=session['role'], 
        cars=dashboard_data, 
        drivers=drivers,
        assistants=assistants,
        planners=planners
    )


# ----------------------------------------------------
# 6. OPERATOR FUNKSİYALARI (CRUD Əməliyyatları)
# BÜTÜN FUNKSİYALAR @operator_required İLƏ QORUNUR VƏ LOGGING ƏLAVƏ EDİLİR
# ----------------------------------------------------
@app.route('/add_expense', methods=['POST'])
@operator_required
def add_expense():
    car_id = request.form.get('car_id')
    expense_type = request.form.get('expense_type')
    amount = request.form.get('amount')
    litr = request.form.get('litr', 0)
    description = request.form.get('description', '')
    fuel_subtype = request.form.get('fuel_subtype', '')

    # Yanacaq üçün subtype ilə birləşdirilmiş təsvir
    final_description = description
    if expense_type == 'Yanacaq' and fuel_subtype:
        final_description = f"{fuel_subtype} - {description}" if description else fuel_subtype

    # Avtomobili DB-dən götür
    car = get_car_by_id(car_id)
    if not car:
        log_action('ADD_EXPENSE_FAILURE', f"Avtomobil tapılmadı (ID: {car_id})", 'failure')
        flash('Xərc əlavə edilərkən xəta baş verdi: Avtomobil tapılmadı.', 'danger')
        return redirect(url_for('index'))

    # Xərc daxil edilən anda kimlər bu maşına bağlı idi
    driver_id_at_expense = car.get('driver_id')
    assistant_id_at_expense = car.get('assistant_id')
    planner_id_at_expense = car.get('planner_id')

    # Məbləğ və litr-i rəqəmə çevir
    try:
        amount_val = float(amount)
    except (TypeError, ValueError):
        flash("Məbləğ düzgün daxil edilməyib.", "danger")
        return redirect(url_for('index'))

    try:
        litr_val = float(litr) if litr else 0.0
    except (TypeError, ValueError):
        litr_val = 0.0

    # 🔹 Əsas hissə: artıq RAM-a yox, DB-yə yazırıq
    insert_expense(
        car_id=int(car_id),
        expense_type=expense_type,
        amount=amount_val,
        litr=litr_val,
        description=final_description,
        driver_id_at_expense=driver_id_at_expense,
        assistant_id_at_expense=assistant_id_at_expense,
        planner_id_at_expense=planner_id_at_expense,
        entered_by=session['user']
    )

    log_action(
        'ADD_EXPENSE_SUCCESS',
        f"{car['car_number']} üçün {amount_val} AZN ({expense_type}) xərc əlavə edildi.",
        'success'
    )
    flash(f'{expense_type} xərci uğurla əlavə edildi.', 'success')
    return redirect(url_for('index'))



@app.route('/update_car_meta', methods=['POST'])
@operator_required
def update_car_meta():
    car_id = request.form.get('car_id')
    if not car_id:
        flash('Avtomobil ID tapılmadı.', 'danger')
        return redirect(url_for('index'))

    brand = request.form.get('brand', '').strip()
    model_name = request.form.get('model_name', '').strip()
    category = request.form.get('category', '').strip()
    notes = request.form.get('notes', '').strip()

    d_id = request.form.get('driver_id')
    a_id = request.form.get('assistant_id')
    p_id = request.form.get('planner_id')

    driver_id = int(d_id) if d_id else None
    assistant_id = int(a_id) if a_id else None
    planner_id = int(p_id) if p_id else None

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE cars
                SET brand = %s,
                    model_name = %s,
                    category = %s,
                    driver_id = %s,
                    assistant_id = %s,
                    planner_id = %s,
                    notes = %s
                WHERE id = %s
            """, (
                brand,
                model_name,
                category,
                driver_id,
                assistant_id,
                planner_id,
                notes,
                car_id
            ))
        conn.commit()
    finally:
        conn.close()

    car = get_car_by_id(car_id)
    car_number = car['car_number'] if car else car_id

    log_action('UPDATE_CAR_META',
               f"{car_number} avtomobilinin meta-məlumatları yeniləndi.",
               'success')
    flash('Avtomobil məlumatları yeniləndi.', 'success')
    return redirect(url_for('index'))


# --- Operatorun İdarəetmə Səhifələri ---

@app.route('/admin/drivers')
@operator_required
def admin_drivers():
    log_action('VIEW_PAGE', 'Sürücü idarəetmə səhifəsinə baxış', 'success')
    drivers_db = get_all_drivers()
    drivers_processed = []
    for driver in drivers_db:
        d = dict(driver)
        d['has_expenses'] = any(e.get('driver_id_at_expense') == d['id'] for e in EXPENSES)
        d['experience_str'] = calculate_experience(d.get('start_date').strftime('%Y-%m-%d') if d.get('start_date') else None)
        drivers_processed.append(d)
    return render_template('admin_drivers.html', drivers=drivers_processed)

@app.route('/admin/cars')
@operator_required
def admin_cars():
    log_action('VIEW_PAGE', 'Avtomobil idarəetmə səhifəsinə baxış', 'success')

    cars = get_all_cars()
    cars_with_expense_info = []
    for car in cars:
        c = dict(car)
        c['has_expenses'] = any(e['car_id'] == c['id'] for e in EXPENSES)
        cars_with_expense_info.append(c)

    drivers = get_all_drivers()
    assistants = get_all_assistants()
    planners = get_all_planners()

    return render_template(
        'admin_cars.html',
        cars=cars_with_expense_info,
        drivers=drivers,
        assistants=assistants,
        planners=planners
    )


@app.route('/admin/assistants')
@operator_required
def admin_assistants():
    log_action('VIEW_PAGE', 'Köməkçi idarəetmə səhifəsinə baxış', 'success')

    assistants = get_all_assistants()
    assistants_with_expense_info = []
    for a in assistants:
        a_copy = dict(a)
        a_copy['has_expenses'] = any(e.get('assistant_id_at_expense') == a_copy['id'] for e in EXPENSES)
        assistants_with_expense_info.append(a_copy)

    return render_template('admin_assistants.html', assistants=assistants_with_expense_info)


@app.route('/admin/assistants/add', methods=['POST'])
@operator_required
def add_assistant():
    name = request.form['name'].strip()
    if not name:
        flash("Köməkçi adı boş ola bilməz.", "danger")
        return redirect(url_for('admin_assistants'))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # təkrarlanan ad (case-insensitive)
            cursor.execute("SELECT id FROM assistants WHERE LOWER(name) = LOWER(%s)", (name,))
            if cursor.fetchone():
                flash("Bu adda köməkçi artıq mövcuddur.", "danger")
                return redirect(url_for('admin_assistants'))

            cursor.execute("INSERT INTO assistants (name) VALUES (%s)", (name,))
        conn.commit()
    finally:
        conn.close()

    log_action('ADD_ASSISTANT', f"Yeni köməkçi əlavə edildi: {name}", 'success')
    flash(f"Köməkçi '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_assistants'))


@app.route('/admin/assistant/edit/<int:aid>', methods=['GET', 'POST'])
@operator_required
def edit_assistant(aid):
    assistant = get_assistant_by_id(aid)
    if not assistant:
        return redirect(url_for('admin_assistants'))

    if request.method == 'POST':
        new_name = request.form['name'].strip()
        if not new_name:
            flash("Köməkçi adı boş ola bilməz.", "danger")
            return render_template('edit_assistant.html', assistant=assistant)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM assistants
                    WHERE LOWER(name) = LOWER(%s) AND id <> %s
                """, (new_name, aid))
                if cursor.fetchone():
                    flash("Bu adda köməkçi artıq mövcuddur.", "danger")
                    return render_template('edit_assistant.html', assistant=assistant)

                cursor.execute("""
                    UPDATE assistants
                    SET name = %s
                    WHERE id = %s
                """, (new_name, aid))
            conn.commit()
        finally:
            conn.close()

        log_action('EDIT_ASSISTANT', f"Köməkçi adı dəyişdirildi: '{assistant['name']}' -> '{new_name}' (ID: {aid})", 'success')
        flash(f"Köməkçi '{assistant['name']}' adı '{new_name}' olaraq dəyişdirildi.", 'success')
        return redirect(url_for('admin_assistants'))

    return render_template('edit_assistant.html', assistant=assistant)


@app.route('/admin/assistant/delete/<int:aid>', methods=['POST'])
@operator_required
def delete_assistant(aid):
    if any(e.get('assistant_id_at_expense') == aid for e in EXPENSES):
        log_action('DELETE_ASSISTANT_FAILURE', f"Köməkçi silinə bilmədi (xərc mövcuddur): ID {aid}", 'failure')
        flash('Bu köməkçi silinə bilməz! Köməkçiyə aid aktiv xərc məlumatı mövcuddur.', 'danger')
        return redirect(url_for('admin_assistants'))

    assistant = get_assistant_by_id(aid)
    if assistant:
        name = assistant['name']

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # maşınlarda bu köməkçi varsa, null et
                cursor.execute("""
                    UPDATE cars
                    SET assistant_id = NULL
                    WHERE assistant_id = %s
                """, (aid,))
                cursor.execute("DELETE FROM assistants WHERE id = %s", (aid,))
            conn.commit()
        finally:
            conn.close()

        log_action('DELETE_ASSISTANT_SUCCESS', f"Köməkçi silindi: {name} (ID: {aid})", 'success')
        flash(f"Köməkçi '{name}' silindi.", 'success')

    return redirect(url_for('admin_assistants'))

@app.route('/admin/planners')
@operator_required
def admin_planners():
    log_action('VIEW_PAGE', 'Planlamaçı idarəetmə səhifəsinə baxış', 'success')

    planners = get_all_planners()  # DB-dən gəlir
    planners_with_expense_info = []
    for p in planners:
        p_copy = dict(p)
        p_copy['has_expenses'] = any(
            e.get('planner_id_at_expense') == p_copy['id'] for e in EXPENSES
        )
        planners_with_expense_info.append(p_copy)

    return render_template('admin_planners.html', planners=planners_with_expense_info)

@app.route('/admin/planners/add', methods=['POST'])
@operator_required
def add_planner():
    name = request.form['name'].strip()
    if not name:
        flash("Planlamaçı adı boş ola bilməz.", "danger")
        return redirect(url_for('admin_planners'))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # eyni ad varmı? (case-insensitive)
            cursor.execute("""
                SELECT id FROM planners
                WHERE LOWER(name) = LOWER(%s)
            """, (name,))
            if cursor.fetchone():
                flash("Bu adda planlamaçı artıq mövcuddur.", "danger")
                return redirect(url_for('admin_planners'))

            cursor.execute("INSERT INTO planners (name) VALUES (%s)", (name,))
        conn.commit()
    finally:
        conn.close()

    log_action('ADD_PLANNER', f"Yeni planlamaçı əlavə edildi: {name}", 'success')
    flash(f"Planlamaçı '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_planners'))


@app.route('/admin/planner/edit/<int:pid>', methods=['GET', 'POST'])
@operator_required
def edit_planner(pid):
    planner = get_planner_by_id(pid)
    if not planner:
        return redirect(url_for('admin_planners'))

    if request.method == 'POST':
        new_name = request.form['name'].strip()
        if not new_name:
            flash("Planlamaçı adı boş ola bilməz.", "danger")
            return render_template('edit_planner.html', planner=planner)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # başqa planlamaçıda eyni ad varmı?
                cursor.execute("""
                    SELECT id FROM planners
                    WHERE LOWER(name) = LOWER(%s) AND id <> %s
                """, (new_name, pid))
                if cursor.fetchone():
                    flash("Bu adda planlamaçı artıq mövcuddur.", "danger")
                    return render_template('edit_planner.html', planner=planner)

                cursor.execute("""
                    UPDATE planners
                    SET name = %s
                    WHERE id = %s
                """, (new_name, pid))
            conn.commit()
        finally:
            conn.close()

        log_action(
            'EDIT_PLANNER',
            f"Planlamaçı adı dəyişdirildi: '{planner['name']}' -> '{new_name}' (ID: {pid})",
            'success'
        )
        flash(f"Planlamaçı '{planner['name']}' adı '{new_name}' olaraq dəyişdirildi.", 'success')
        return redirect(url_for('admin_planners'))

    return render_template('edit_planner.html', planner=planner)


@app.route('/admin/planner/delete/<int:pid>', methods=['POST'])
@operator_required
def delete_planner(pid):
    # Əvvəlcə xərc olub-olmadığını yoxla
    if any(e.get('planner_id_at_expense') == pid for e in EXPENSES):
        log_action(
            'DELETE_PLANNER_FAILURE',
            f"Planlamaçı silinə bilmədi (xərc mövcuddur): ID {pid}",
            'failure'
        )
        flash(
            'Bu planlamaçı silinə bilməz! Planlamacıya aid aktiv xərc məlumatı mövcuddur.',
            'danger'
        )
        return redirect(url_for('admin_planners'))

    planner = get_planner_by_id(pid)
    if planner:
        name = planner['name']

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # maşınlarda bu planlamaçı varsa, null et
                cursor.execute("""
                    UPDATE cars
                    SET planner_id = NULL
                    WHERE planner_id = %s
                """, (pid,))

                # planlamaçını sil
                cursor.execute("DELETE FROM planners WHERE id = %s", (pid,))
            conn.commit()
        finally:
            conn.close()

        log_action(
            'DELETE_PLANNER_SUCCESS',
            f"Planlamaçı silindi: {name} (ID: {pid})",
            'success'
        )
        flash(f"Planlamaçı '{name}' silindi.", 'success')

    return redirect(url_for('admin_planners'))


@app.route('/admin/drivers/add', methods=['POST'])
@operator_required
def add_driver():
    name = request.form.get('name', '').strip()
    license_no = request.form.get('license_no', '').strip()
    phone = request.form.get('phone', '').strip()
    start_date = request.form.get('start_date', '').strip()

    if not name:
        flash("Sürücü adı mütləq daxil edilməlidir.", "danger")
        return redirect(url_for('admin_drivers'))

    # License no unik
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if license_no:
                cursor.execute("SELECT id FROM drivers WHERE license_no = %s", (license_no,))
                if cursor.fetchone():
                    log_action('ADD_DRIVER_FAILURE', f"Təkrarlanan vəsiqə nömrəsi: {license_no}", 'failure')
                    flash(f"'{license_no}' vəsiqə nömrəsi artıq sistemdə mövcuddur.", 'danger')
                    return redirect(url_for('admin_drivers'))

            if start_date:
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    flash("İşə başlama tarixi formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
                    start_date_db = None
                else:
                    start_date_db = start_date
            else:
                start_date_db = None

            cursor.execute("""
                INSERT INTO drivers (name, license_no, phone, start_date)
                VALUES (%s, %s, %s, %s)
            """, (name, license_no, phone, start_date_db))
        conn.commit()
    finally:
        conn.close()

    log_action('ADD_DRIVER_SUCCESS', f"Yeni sürücü əlavə edildi: {name}", 'success')
    flash(f"Sürücü '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_drivers'))


@app.route('/admin/cars/add', methods=['POST'])
@operator_required
def add_car():
    car_number = request.form['car_number'].strip()
    model = request.form['model'].strip()
    driver_id = int(request.form['driver_id']) if request.form.get('driver_id') else None
    assistant_id = int(request.form['assistant_id']) if request.form.get('assistant_id') else None
    planner_id = int(request.form['planner_id']) if request.form.get('planner_id') else None

    if not car_number or not model:
        flash("Avtomobil nömrəsi və model boş ola bilməz.", "danger")
        return redirect(url_for('admin_cars'))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # eyni nömrə var?
            cursor.execute("SELECT id FROM cars WHERE car_number = %s", (car_number,))
            if cursor.fetchone():
                flash(f"'{car_number}' nömrəli avtomobil artıq mövcuddur.", "danger")
                return redirect(url_for('admin_cars'))

            cursor.execute("""
                INSERT INTO cars (
                    car_number, model, brand, model_name, category,
                    driver_id, assistant_id, planner_id, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                car_number,
                model,
                "",  # brand
                "",  # model_name
                "",  # category
                driver_id,
                assistant_id,
                planner_id,
                ""   # notes
            ))
        conn.commit()
    finally:
        conn.close()

    log_action('ADD_CAR_SUCCESS', f"Yeni avtomobil əlavə edildi: {car_number}", 'success')
    flash(f"Avtomobil '{car_number}' əlavə edildi.", 'success')
    return redirect(url_for('admin_cars'))


@app.route('/admin/driver/delete/<int:id>', methods=['POST'])
@operator_required
def delete_driver(id):
    if any(e.get('driver_id_at_expense') == id for e in EXPENSES):
        log_action('DELETE_DRIVER_FAILURE', f"Sürücü silinə bilmədi (xərc mövcuddur): ID {id}", 'failure')
        flash('Bu sürücü silinə bilməz! Sürücüyə aid aktiv xərc məlumatı mövcuddur.', 'danger')
        return redirect(url_for('admin_drivers'))

    driver = get_driver_by_id(id)
    if driver:
        name = driver['name']
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # Avtomobillərdə bu sürücü təyin olunubsa, null et
                cursor.execute("""
                    UPDATE cars
                    SET driver_id = NULL
                    WHERE driver_id = %s
                """, (id,))
                # Sürücünü sil
                cursor.execute("DELETE FROM drivers WHERE id = %s", (id,))
            conn.commit()
        finally:
            conn.close()

        log_action('DELETE_DRIVER_SUCCESS', f"Sürücü silindi: {name} (ID: {id})", 'success')
        flash(f"Sürücü '{name}' silindi.", 'success')

    return redirect(url_for('admin_drivers'))


@app.route('/admin/car/delete/<int:id>', methods=['POST'])
@operator_required
@app.route('/admin/car/delete/<int:id>', methods=['POST'])
@operator_required
def delete_car(id):
    redirect_url = request.referrer or url_for('index')
    car = get_car_by_id(id)
    if not car:
        flash('Avtomobil tapılmadı.', 'danger')
        return redirect(redirect_url)

    if any(e['car_id'] == id for e in EXPENSES):
        log_action('DELETE_CAR_FAILURE', f"Avtomobil silinə bilmədi (xərc mövcuddur): {car['car_number']}", 'failure')
        flash('Bu avtomobil silinə bilməz! Avtomobilə aid aktiv xərc məlumatı mövcuddur.', 'danger')
        return redirect(redirect_url)

    car_number = car['car_number']

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM cars WHERE id = %s", (id,))
        conn.commit()
    finally:
        conn.close()

    log_action('DELETE_CAR_SUCCESS', f"Avtomobil silindi: {car_number} (ID: {id})", 'success')
    flash(f"Avtomobil '{car_number}' uğurla silindi.", 'success')
    return redirect(redirect_url)


@app.route('/admin/driver/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_driver(id):
    driver = get_driver_by_id(id)
    if not driver:
        return redirect(url_for('admin_drivers'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        license_no = request.form.get('license_no', '').strip()
        phone = request.form.get('phone', '').strip()
        start_date = request.form.get('start_date', '').strip()

        if not name:
            flash("Sürücü adı mütləq daxil edilməlidir.", "danger")
            return render_template('edit_driver.html', driver=driver)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # License no unikliyi yoxla
                if license_no:
                    cursor.execute("""
                        SELECT id FROM drivers
                        WHERE license_no = %s AND id <> %s
                    """, (license_no, id))
                    if cursor.fetchone():
                        flash(f"'{license_no}' vəsiqə nömrəsi artıq başqa sürücüdə var.", 'danger')
                        return render_template('edit_driver.html', driver=driver)

                if start_date:
                    try:
                        datetime.strptime(start_date, '%Y-%m-%d')
                    except ValueError:
                        flash("İşə başlama tarixi formatı yanlışdır (YYYY-MM-DD olmalıdır). Tarix yenilənmədi.", "warning")
                        start_date_db = driver.get('start_date')
                    else:
                        start_date_db = start_date
                else:
                    start_date_db = None

                cursor.execute("""
                    UPDATE drivers
                    SET name = %s,
                        license_no = %s,
                        phone = %s,
                        start_date = %s
                    WHERE id = %s
                """, (name, license_no, phone, start_date_db, id))
            conn.commit()
        finally:
            conn.close()

        log_action('EDIT_DRIVER', f"Sürücü məlumatları yeniləndi: '{driver['name']}' -> '{name}' (ID: {id})", 'success')
        flash(f"Sürücü '{name}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_drivers'))

    return render_template('edit_driver.html', driver=driver)


@app.route('/admin/car/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_car(id):
    car = get_car_by_id(id)
    if not car:
        return redirect(url_for('admin_cars'))

    if request.method == 'POST':
        car_number = request.form['car_number'].strip()
        model = request.form['model'].strip()
        driver_id = int(request.form['driver_id']) if request.form.get('driver_id') else None

        if not car_number or not model:
            flash("Avtomobil nömrəsi və model boş ola bilməz.", "danger")
            drivers = get_all_drivers()
            return render_template('edit_car.html', car=car, drivers=drivers)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # eyni nömrə başqa maşında var?
                cursor.execute("""
                    SELECT id FROM cars
                    WHERE car_number = %s AND id <> %s
                """, (car_number, id))
                if cursor.fetchone():
                    flash(f"'{car_number}' nömrəli avtomobil artıq başqa qeydiyyatda var.", "danger")
                    drivers = get_all_drivers()
                    return render_template('edit_car.html', car=car, drivers=drivers)

                cursor.execute("""
                    UPDATE cars
                    SET car_number = %s,
                        model = %s,
                        driver_id = %s
                    WHERE id = %s
                """, (car_number, model, driver_id, id))
            conn.commit()
        finally:
            conn.close()

        log_action('EDIT_CAR', f"Avtomobil məlumatları yeniləndi: '{car['car_number']}' -> '{car_number}' (ID: {id})", 'success')
        flash(f"Avtomobil '{car_number}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_cars'))

    drivers = get_all_drivers()
    return render_template('edit_car.html', car=car, drivers=drivers)



# ----------------------------------------------------
# 7. TOPLU ƏLAVƏ ETMƏ FUNKSİYALARI (LOGGING ƏLAVƏ EDİLDİ)
# ----------------------------------------------------

@app.route('/admin/cars/bulk_add', methods=['POST'])
@operator_required
def bulk_add_car():
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0
    skipped_count = 0

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT car_number FROM cars")
            existing_car_numbers = {row["car_number"] for row in cursor.fetchall()}

            for line in bulk_data.splitlines():
                if not line.strip():
                    continue
                parts = line.split(';')
                if len(parts) < 2:
                    skipped_count += 1
                    continue

                car_number = parts[0].strip()
                model = parts[1].strip()

                if not car_number or not model:
                    skipped_count += 1
                    continue

                if car_number in existing_car_numbers:
                    skipped_count += 1
                    continue

                cursor.execute("""
                    INSERT INTO cars (
                        car_number, model, brand, model_name, category,
                        driver_id, assistant_id, planner_id, notes
                    )
                    VALUES (%s, %s, %s, %s, %s, NULL, NULL, NULL, %s)
                """, (car_number, model, "", "", "", ""))
                existing_car_numbers.add(car_number)
                added_count += 1

        conn.commit()
    finally:
        conn.close()

    log_action('BULK_ADD_CAR', f"{added_count} avtomobil toplu əlavə edildi, {skipped_count} sətir ötürüldü.", 'success')
    flash(f"{added_count} avtomobil uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan nömrə və ya səhv format) ötürüldü.", 'success')
    return redirect(url_for('admin_cars'))

@app.route('/admin/assistants/bulk_add', methods=['POST'])
@operator_required
def bulk_add_assistant():
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0
    skipped_count = 0

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # mövcud köməkçi adları (lowercase)
            cursor.execute("SELECT name FROM assistants")
            existing_assistants = {row['name'].lower() for row in cursor.fetchall()}

            for line in bulk_data.splitlines():
                name = line.strip()
                if not name:
                    continue

                lower_name = name.lower()
                if lower_name in existing_assistants:
                    skipped_count += 1
                    continue

                cursor.execute("INSERT INTO assistants (name) VALUES (%s)", (name,))
                existing_assistants.add(lower_name)
                added_count += 1

        conn.commit()
    finally:
        conn.close()

    log_action(
        'BULK_ADD_ASSISTANT',
        f"{added_count} köməkçi toplu əlavə edildi, {skipped_count} sətir ötürüldü.",
        'success'
    )
    flash(
        f"{added_count} köməkçi uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan ad və ya boş sətir) ötürüldü.",
        'success'
    )
    return redirect(url_for('admin_assistants'))


@app.route('/admin/planners/bulk_add', methods=['POST'])
@operator_required
def bulk_add_planner():
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0
    skipped_count = 0

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM planners")
            existing_planners = {row['name'].lower() for row in cursor.fetchall()}

            for line in bulk_data.splitlines():
                name = line.strip()
                if not name:
                    continue

                lower_name = name.lower()
                if lower_name in existing_planners:
                    skipped_count += 1
                    continue

                cursor.execute("INSERT INTO planners (name) VALUES (%s)", (name,))
                existing_planners.add(lower_name)
                added_count += 1

        conn.commit()
    finally:
        conn.close()

    log_action(
        'BULK_ADD_PLANNER',
        f"{added_count} planlamaçı toplu əlavə edildi, {skipped_count} sətir ötürüldü.",
        'success'
    )
    flash(
        f"{added_count} planlamaçı uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan ad və ya boş sətir) ötürüldü.",
        'success'
    )
    return redirect(url_for('admin_planners'))


# ----------------------------------------------------
# 8. YALNIZ ADMİN FUNKSİYALARI (İstifadəçi İdarəetməsi)
# ----------------------------------------------------
@app.route('/admin/users')
@admin_required
def admin_users():
    log_action('VIEW_PAGE', 'Admin -> Operator İdarəetmə səhifəsinə baxış', 'success')
    users_list = get_operators()  # yalnız operatorlar (role='user')
    return render_template('admin_users.html', users=users_list)


@app.route('/admin/users/add', methods=['POST'])
@admin_required
def add_user():
    fullname = request.form['fullname'].strip()
    username = request.form['username'].strip()
    password = request.form['password']
    role = request.form['role']

    # Admin yalnız operator və ya admin yarada bilər
    if role not in ['user', 'admin']:
        flash('Admin yalnız "Operator" və ya "Admin" rolu təyin edə bilər.', 'danger')
        return redirect(url_for('admin_users'))

    if get_user_by_username(username):
        log_action('ADD_USER_FAILURE', f"Təkrarlanan istifadəçi adı: {username}", 'failure')
        flash('Bu istifadəçi adı artıq mövcuddur!', 'danger')
        return redirect(url_for('admin_users'))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (fullname, username, password, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (fullname, username, password, role, 1))
        conn.commit()
    finally:
        conn.close()

    log_action('ADD_USER_SUCCESS', f"Admin yeni istifadəçi əlavə etdi: {username} (Rol: {role})", 'success')
    flash(f"İstifadəçi '{fullname}' ({role}) əlavə edildi.", 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/user/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = get_user_by_id(id)
    if not user:
        return redirect(url_for('admin_users'))

    # Admin supervisor-u redaktə edə bilməz
    if user['role'] == 'supervisor':
        log_action('EDIT_USER_FAILURE', f"Admin supervisor-u redaktə etməyə cəhd etdi (ID: {id})", 'failure')
        flash('Supervisor məlumatlarını redaktə edə bilməzsiniz.', 'danger')
        return redirect(url_for('admin_users'))

    if request.method == 'POST':
        new_fullname = request.form['fullname'].strip()
        new_username = request.form['username'].strip()
        new_role = request.form['role']

        existing_user = get_user_by_username(new_username)
        if existing_user and existing_user['id'] != id:
            flash('Bu istifadəçi adı artıq başqası tərəfindən istifadə olunur!', 'danger')
            return render_template('edit_user.html', user=user)

        if new_role not in ['user', 'admin']:
            flash('Admin yalnız "Operator" və ya "Admin" rolu təyin edə bilər.', 'danger')
            return render_template('edit_user.html', user=user)

        new_password = request.form.get('password')
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                if new_password:
                    cursor.execute("""
                        UPDATE users
                        SET fullname = %s,
                            username = %s,
                            role = %s,
                            password = %s
                        WHERE id = %s
                    """, (new_fullname, new_username, new_role, new_password, id))
                else:
                    cursor.execute("""
                        UPDATE users
                        SET fullname = %s,
                            username = %s,
                            role = %s
                        WHERE id = %s
                    """, (new_fullname, new_username, new_role, id))
            conn.commit()
        finally:
            conn.close()

        log_action('EDIT_USER_SUCCESS', f"Admin istifadəçi məlumatlarını yenilədi: {new_username} (ID: {id})", 'success')
        flash(f"İstifadəçi '{new_fullname}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_users'))

    return render_template('edit_user.html', user=user)


@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    user = get_user_by_id(id)
    if user and user['role'] not in ['admin', 'supervisor']:
        name = user['fullname']

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (id,))
            conn.commit()
        finally:
            conn.close()

        log_action('DELETE_USER_SUCCESS', f"Admin istifadəçini sildi: {name} (ID: {id})", 'success')
        flash(f"İstifadəçi '{name}' silindi.", 'success')
    elif user and user['role'] in ['admin', 'supervisor']:
        log_action('DELETE_USER_FAILURE', f"Admin başqa admini/supervisoru silməyə cəhd etdi (ID: {id})", 'failure')
        flash('Admin başqa Admini və ya Supervisoru silə bilməz.', 'danger')
    return redirect(url_for('admin_users'))


# ----------------------------------------------------
# 9. HESABATLAR (Yalnız Admin üçün) - YENİLƏNDİ
# ----------------------------------------------------
@app.route('/admin/reports', methods=['GET'])
@admin_required
def admin_reports():
    log_action('VIEW_PAGE', 'Admin -> Xərc Hesabatları səhifəsinə baxış', 'success')

    f_car_id = request.args.get('car_id', type=int)
    f_driver_id = request.args.get('driver_id', type=int) 
    f_assistant_id = request.args.get('assistant_id', type=int) 
    f_planner_id = request.args.get('planner_id', type=int)     
    f_user_username = request.args.get('user_username', type=str) 
    f_expense_type = request.args.get('expense_type', type=str) 
    f_start_date_str = request.args.get('start_date', type=str)
    f_end_date_str = request.args.get('end_date', type=str)
    
    # ==========================================================
    # YENİ MƏNTİQ: Default olaraq son 2 günü göstər
    # ==========================================================
    if not f_start_date_str and not f_end_date_str:
        start_date = datetime.now().date() - timedelta(days=2)
        f_start_date_str = start_date.strftime('%Y-%m-%d')
    # ==========================================================

    all_expenses_enriched = []
    # YALNIZ AKTİV EXPENSES SİYAHISINDAN GÖSTƏRİR
    for expense in EXPENSES:
        car = get_car_by_id(expense['car_id'])
        user = get_user_by_username(expense['entered_by']) 
        driver_at_expense = get_driver_by_id(expense.get('driver_id_at_expense'))
        assistant_at_expense = get_assistant_by_id(expense.get('assistant_id_at_expense'))
        planner_at_expense = get_planner_by_id(expense.get('planner_id_at_expense'))
        all_expenses_enriched.append({
            "expense": expense, "car": car, "user": user,
            "driver_name_at_expense": driver_at_expense['name'] if driver_at_expense else "-",
            "assistant_name_at_expense": assistant_at_expense['name'] if assistant_at_expense else "-",
            "planner_name_at_expense": planner_at_expense['name'] if planner_at_expense else "-"
        })

    filtered_expenses = all_expenses_enriched
    if f_car_id: filtered_expenses = [e for e in filtered_expenses if e['car'] and e['car']['id'] == f_car_id]
    if f_driver_id: filtered_expenses = [e for e in filtered_expenses if e['expense'].get('driver_id_at_expense') == f_driver_id]
    if f_assistant_id: filtered_expenses = [e for e in filtered_expenses if e['expense'].get('assistant_id_at_expense') == f_assistant_id]
    if f_planner_id: filtered_expenses = [e for e in filtered_expenses if e['expense'].get('planner_id_at_expense') == f_planner_id]
    if f_user_username: filtered_expenses = [e for e in filtered_expenses if e['user'] and e['user']['username'] == f_user_username]
    if f_expense_type: filtered_expenses = [e for e in filtered_expenses if e['expense']['type'] == f_expense_type] 
    
    # Tarix filtrləri artıq f_start_date_str default dəyər aldığı üçün həmişə işləyəcək
    if f_start_date_str:
        try: 
            start_date = datetime.strptime(f_start_date_str, '%Y-%m-%d').date()
            filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() >= start_date]
        except ValueError: 
            flash("Başlanğıc tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
    if f_end_date_str:
        try: 
            end_date = datetime.strptime(f_end_date_str, '%Y-%m-%d').date()
            filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() <= end_date]
        except ValueError: 
            flash("Bitmə tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")

    total_amount = sum(e['expense']['amount'] for e in filtered_expenses)


    # BUNLAR ARTIQ DB-DƏN GƏLİR
    operators = get_operators()
    drivers = get_all_drivers()
    cars = get_all_cars()
    assistants = get_all_assistants()
    planners = get_all_planners()

    return render_template(
        'admin_reports.html',
        reports=sorted(filtered_expenses, key=lambda x: x['expense']['timestamp'], reverse=True),
        total_amount=total_amount,
        drivers=drivers,
        cars=cars,
        operators=operators,
        assistants=assistants,
        planners=planners,
        expense_types=EXPENSE_TYPES,
        selected_filters={
            'car_id': f_car_id,
            'driver_id': f_driver_id,
            'assistant_id': f_assistant_id,
            'planner_id': f_planner_id,
            'user_username': f_user_username,
            'expense_type': f_expense_type,
            'start_date': f_start_date_str,
            'end_date': f_end_date_str
        }
    )


# ----------------------------------------------------
# 10. ADMİN FUNKSİYALARI (XƏRC SİLMƏ VƏ BƏRPA)
# ----------------------------------------------------

@app.route('/admin/expense/delete/<int:id>', methods=['POST'])
@admin_required
def delete_expense(id):
    expense_to_delete = None
    for expense in EXPENSES:
        if expense['expense_id'] == id: expense_to_delete = expense; break
    
    if expense_to_delete:
        EXPENSES.remove(expense_to_delete)
        expense_to_delete['deleted_by_user'] = session.get('fullname', 'unknown_admin')
        expense_to_delete['deleted_at'] = datetime.now()
        DELETED_EXPENSES.append(expense_to_delete)
        
        log_action('DELETE_EXPENSE', f"Xərc arxivə köçürüldü (ID: {id}, Məbləğ: {expense_to_delete['amount']})", 'success')
        flash(f"Xərc (ID: {id}) uğurla silindi və arxivə əlavə olundu.", 'success')
    else:
        log_action('DELETE_EXPENSE_FAILURE', f"Silinəcək xərc tapılmadı (ID: {id})", 'failure')
        flash(f"Xərc (ID: {id}) aktiv siyahıda tapılmadı.", 'danger')
        
    return redirect(url_for('admin_reports'))

@app.route('/admin/expense/restore/<int:id>', methods=['POST'])
@admin_required
def restore_expense(id):
    expense_to_restore = None
    for expense in DELETED_EXPENSES:
        if expense['expense_id'] == id: expense_to_restore = expense; break
    
    if expense_to_restore:
        DELETED_EXPENSES.remove(expense_to_restore)
        deleted_by = expense_to_restore.pop('deleted_by_user', None)
        expense_to_restore.pop('deleted_at', None)
        EXPENSES.append(expense_to_restore)
        
        log_action('RESTORE_EXPENSE', f"Xərc arxivdən bərpa edildi (ID: {id}, Əvvəl silən: {deleted_by})", 'success')
        flash(f"Xərc (ID: {id}) uğurla bərpa edildi.", 'success')
    else:
        log_action('RESTORE_EXPENSE_FAILURE', f"Bərpa ediləcək xərc arxivdə tapılmadı (ID: {id})", 'failure')
        flash(f"Xərc (ID: {id}) arxivdə tapılmadı.", 'danger')
        
    return redirect(url_for('admin_deleted_reports'))

@app.route('/admin/deleted_reports')
@admin_required
def admin_deleted_reports():
    log_action('VIEW_PAGE', 'Admin -> Silinən Xərclər Arxivinə baxış', 'success')
    all_expenses_enriched = []
    for expense in DELETED_EXPENSES:
        car = get_car_by_id(expense['car_id'])
        user = get_user_by_username(expense['entered_by']) 
        driver_at_expense = get_driver_by_id(expense.get('driver_id_at_expense'))
        assistant_at_expense = get_assistant_by_id(expense.get('assistant_id_at_expense'))
        planner_at_expense = get_planner_by_id(expense.get('planner_id_at_expense'))
        all_expenses_enriched.append({
            "expense": expense, "car": car, "user": user,
            "driver_name_at_expense": driver_at_expense['name'] if driver_at_expense else "-",
            "assistant_name_at_expense": assistant_at_expense['name'] if assistant_at_expense else "-",
            "planner_name_at_expense": planner_at_expense['name'] if planner_at_expense else "-"
        })
    
    return render_template(
        'admin_deleted_reports.html', 
        reports=sorted(all_expenses_enriched, key=lambda x: x['expense']['deleted_at'], reverse=True)
    )

# ----------------------------------------------------
# 11. YENİ SUPERVISOR FUNKSİYALARI (DASHBOARD VƏ REPORTS YENİLƏNDİ)
# ----------------------------------------------------

@app.route('/supervisor/dashboard')
@supervisor_required
def supervisor_dashboard():
    """Supervisor üçün əsas panel (YENİLƏNİB - STATİSTİKALARLA)."""
    log_action('VIEW_PAGE', 'Supervisor Dashboarduna baxış', 'success')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # ümumi user sayı
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            total_users = cursor.fetchone()["cnt"]

            # aktiv user sayı
            cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_active = 1")
            active_users = cursor.fetchone()["cnt"]

            # rol bölgüsü
            cursor.execute("SELECT role, COUNT(*) AS cnt FROM users GROUP BY role")
            role_rows = cursor.fetchall()
    finally:
        conn.close()

    passive_users = total_users - active_users

    roles_count = {'admin': 0, 'supervisor': 0, 'user': 0}
    for r in role_rows:
        if r["role"] in roles_count:
            roles_count[r["role"]] = r["cnt"]

    total_logs = len(AUDIT_LOGS)  # hələlik RAM-də qalır

    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'passive_users': passive_users,
        'total_logs': total_logs
    }

    chart_data = {
        'labels': list(roles_count.keys()),
        'data': list(roles_count.values())
    }

    return render_template(
        'supervisor_dashboard.html',
        stats=stats,
        chart_data=chart_data
    )


@app.route('/supervisor/reports')
@supervisor_required
def supervisor_reports():
    """Bütün audit loqlarını göstərir (YENİLƏNİB - FİLTRLƏRLƏ)."""
    log_action('VIEW_PAGE', 'Supervisor -> Audit Raporları səhifəsinə baxış', 'success')
    
    # Filtr parametrlərini al
    f_username = request.args.get('username', type=str)
    f_hostname = request.args.get('hostname', type=str) # <--- YENİ FİLTR
    f_action = request.args.get('action', type=str)
    f_status = request.args.get('status', type=str)
    f_start_date_str = request.args.get('start_date', type=str)
    f_end_date_str = request.args.get('end_date', type=str)
    
    # ==========================================================
    # YENİ MƏNTİQ: Default olaraq son 2 günü göstər
    # ==========================================================
    if not f_start_date_str and not f_end_date_str:
        start_date = datetime.now().date() - timedelta(days=2)
        f_start_date_str = start_date.strftime('%Y-%m-%d')
    # ==========================================================
    
    # Filtrlər üçün unikal dəyərləri al
    all_usernames = sorted(list(set([log['username'] for log in AUDIT_LOGS])))
    all_actions = sorted(list(set([log['action'] for log in AUDIT_LOGS])))
    all_hostnames = sorted(list(set([log.get('hostname', log['ip']) for log in AUDIT_LOGS]))) # <--- YENİ
    
    # Loqları filtrə sal
    filtered_logs = AUDIT_LOGS.copy()
    
    if f_username:
        filtered_logs = [log for log in filtered_logs if log['username'] == f_username]
    if f_hostname: # <--- YENİ
        filtered_logs = [log for log in filtered_logs if log.get('hostname', log['ip']) == f_hostname]
    if f_action:
        filtered_logs = [log for log in filtered_logs if log['action'] == f_action]
    if f_status:
        filtered_logs = [log for log in filtered_logs if log['status'] == f_status]
        
    # Tarix filtrləri artıq f_start_date_str default dəyər aldığı üçün həmişə işləyəcək
    if f_start_date_str:
        try:
            start_date = datetime.strptime(f_start_date_str, '%Y-%m-%d').date()
            filtered_logs = [log for log in filtered_logs if log['timestamp'].date() >= start_date]
        except ValueError:
            flash("Başlanğıc tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
    if f_end_date_str:
        try:
            end_date = datetime.strptime(f_end_date_str, '%Y-%m-%d').date()
            filtered_logs = [log for log in filtered_logs if log['timestamp'].date() <= end_date]
        except ValueError:
            flash("Bitmə tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
            
    selected_filters = {
        'username': f_username,
        'hostname': f_hostname, # <--- YENİ
        'action': f_action,
        'status': f_status,
        'start_date': f_start_date_str,
        'end_date': f_end_date_str
    }

    return render_template(
        'supervisor_reports.html', 
        reports=sorted(filtered_logs, key=lambda x: x['timestamp'], reverse=True),
        all_usernames=all_usernames,
        all_actions=all_actions,
        all_hostnames=all_hostnames, # <--- YENİ
        selected_filters=selected_filters
    )

@app.route('/supervisor/operations')
@supervisor_required
def supervisor_operations():
    """Bütün istifadəçiləri idarə etmə səhifəsi."""
    log_action('VIEW_PAGE', 'Supervisor -> Əməliyyatlar (İstifadəçi İdarəetmə) səhifəsinə baxış', 'success')
    users = get_all_users()
    return render_template('supervisor_operations.html', users=users)


@app.route('/supervisor/operations/add_user', methods=['POST'])
@supervisor_required
def supervisor_add_user():
    """Supervisor yeni istifadəçi əlavə edir."""
    fullname = request.form['fullname'].strip()
    username = request.form['username'].strip()
    password = request.form['password']
    role = request.form['role']

    if get_user_by_username(username):
        log_action('SUPERVISOR_ADD_USER_FAILURE', f"Təkrarlanan istifadəçi adı: {username}", 'failure')
        flash('Bu istifadəçi adı artıq mövcuddur!', 'danger')
        return redirect(url_for('supervisor_operations'))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (fullname, username, password, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (fullname, username, password, role, 1))
        conn.commit()
    finally:
        conn.close()

    log_action('SUPERVISOR_ADD_USER_SUCCESS', f"Supervisor yeni istifadəçi əlavə etdi: {username} (Rol: {role})", 'success')
    flash(f"İstifadəçi '{fullname}' ({role}) əlavə edildi.", 'success')
    return redirect(url_for('supervisor_operations'))



@app.route('/supervisor/user/edit/<int:id>', methods=['GET', 'POST'])
@supervisor_required
def supervisor_edit_user(id):
    """Supervisor istifadəçiləri (adminlər daxil) redaktə edir."""
    user = get_user_by_id(id)
    if not user:
        return redirect(url_for('supervisor_operations'))

    # Supervisor özünü redaktə edə bilməz (təhlükəsizlik üçün)
    if user['username'] == session.get('user'):
        flash('Öz hesabınızı buradan redaktə edə bilməzsiniz.', 'danger')
        return redirect(url_for('supervisor_operations'))

    if request.method == 'POST':
        new_fullname = request.form['fullname'].strip()
        new_username = request.form['username'].strip()
        new_role = request.form['role']
        new_active_status = (request.form.get('is_active') == 'on')
        new_password = request.form.get('password')

        existing_user = get_user_by_username(new_username)
        if existing_user and existing_user['id'] != id:
            flash('Bu istifadəçi adı artıq başqası tərəfindən istifadə olunur!', 'danger')
            return render_template('supervisor_edit_user.html', user=user)

        log_details = [f"İstifadəçi '{user['username']}' (ID: {id}) üçün dəyişikliklər:"]

        if user['fullname'] != new_fullname:
            log_details.append(f"Ad: '{user['fullname']}' -> '{new_fullname}'")

        if user['username'] != new_username:
            log_details.append(f"Login: '{user['username']}' -> '{new_username}'")

        if user['role'] != new_role:
            log_details.append(f"Rol: '{user['role']}' -> '{new_role}'")

        if user.get('is_active', True) != new_active_status:
            log_details.append(f"Status: '{user.get('is_active', True)}' -> '{new_active_status}'")

        if new_password:
            log_details.append("Parol yeniləndi.")

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                if new_password:
                    cursor.execute("""
                        UPDATE users
                        SET fullname = %s,
                            username = %s,
                            role = %s,
                            is_active = %s,
                            password = %s
                        WHERE id = %s
                    """, (new_fullname, new_username, new_role, int(new_active_status), new_password, id))
                else:
                    cursor.execute("""
                        UPDATE users
                        SET fullname = %s,
                            username = %s,
                            role = %s,
                            is_active = %s
                        WHERE id = %s
                    """, (new_fullname, new_username, new_role, int(new_active_status), id))
            conn.commit()
        finally:
            conn.close()

        log_action('SUPERVISOR_EDIT_USER', " ".join(log_details), 'success')
        flash(f"İstifadəçi '{new_fullname}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('supervisor_operations'))

    return render_template('supervisor_edit_user.html', user=user)

@app.route('/supervisor/user/delete/<int:id>', methods=['POST'])
@supervisor_required
def supervisor_delete_user(id):
    """Supervisor istifadəçiləri silir (özü xaric)."""
    user = get_user_by_id(id)
    if user and user['username'] == session.get('user'):
        log_action('SUPERVISOR_DELETE_USER_FAILURE', f"Supervisor özünü silməyə cəhd etdi (ID: {id})", 'failure')
        flash('Supervisor öz hesabını silə bilməz.', 'danger')
        return redirect(url_for('supervisor_operations'))

    if user:
        name = user['fullname']
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (id,))
            conn.commit()
        finally:
            conn.close()

        log_action('SUPERVISOR_DELETE_USER_SUCCESS', f"Supervisor istifadəçini sildi: {name} (ID: {id})", 'success')
        flash(f"İstifadəçi '{name}' silindi.", 'success')

    return redirect(url_for('supervisor_operations'))


# ----------------------------------------------------
# 12. TƏTBİQİ BAŞLATMA
# ----------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
