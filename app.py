# -*- coding: utf-8 -*-
from db import get_connection
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from functools import wraps
import socket
import json
import io
import re  # Regex modulunu əlavə etdik

app = Flask(__name__)
app.secret_key = 'ASIS_Sizin_Real_Gizli_Acariniz_Burada_Olsun' 

# SABİT SİYAHILAR (Verilənlər bazasında olmayan statik məlumatlar)
EXPENSE_TYPES = [      
    'Yanacaq',
    'Təmir',
    'Yol xərci',
    'Yuyulma',
    'Sığorta',
    'Cərimə',
    'Digər'
]

# Cərimə Növləri
FINE_TYPES = [
    'Avtobus zolağı',
    'Sürət həddini aşma',
    'Dayanma-durma qaydası',
    'Qırmızı işıq',
    'Təhlükəsizlik kəməri',
    'Texniki baxış / Sığorta yoxdur',
    'Digər'
]

# Təmir Növləri
REPAIR_TYPES = [
    'Təkər təmiri / Yenisi',
    'Akumulyator',
    'Yağ dəyişimi',
    'Nakladka / Əyləc sistemi',
    'Mühərrik təmiri',
    'Kosmetik / Dəmirçi işi',
    'Digər'
]

# --- KÖMƏKÇİ PARSE FUNKSİYASI ---
def parse_expense_description(description):
    """
    Açıqlama mətnindən [Alt Növ] hissəsini ayırır.
    Qaytarır: (alt_nov, temiz_aciqlama)
    """
    if not description:
        return "-", "-"
    
    # Regex: Sətrin əvvəlində [Hər hansı mətn] axtarır
    match = re.match(r'^\[(.*?)\]\s*(.*)', description, re.DOTALL)
    if match:
        subtype = match.group(1)
        clean_desc = match.group(2)
        if not clean_desc: clean_desc = "-"
        return subtype, clean_desc
    else:
        return "-", description

# --- VERİLƏNLƏR BAZASI KÖMƏKÇİ FUNKSİYALARI ---

def get_car_by_id(car_id):
    if not car_id: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, car_number, model, brand, model_name, category,
                       driver_id, assistant_id, planner_id, notes
                FROM cars WHERE id = %s
            """, (car_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_driver_by_id(driver_id):
    if not driver_id: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_assistant_by_id(aid):
    if not aid: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assistants WHERE id = %s", (aid,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_planner_by_id(pid):
    if not pid: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM planners WHERE id = %s", (pid,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_user_by_username(username):
    if not username: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_user_by_id(user_id):
    if not user_id: return None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_all_drivers():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drivers ORDER BY name")
            return cursor.fetchall()
    finally:
        conn.close()

def get_all_assistants():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assistants ORDER BY name")
            return cursor.fetchall()
    finally:
        conn.close()

def get_all_planners():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM planners ORDER BY name")
            return cursor.fetchall()
    finally:
        conn.close()

def get_all_cars():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cars ORDER BY car_number")
            return cursor.fetchall()
    finally:
        conn.close()

def get_operators():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE role = 'user' ORDER BY fullname")
            return cursor.fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY fullname")
            return cursor.fetchall()
    finally:
        conn.close()

# --- ƏSAS FUNKSİONALLIQ (LOG, XƏRC VƏ S.) ---

def log_action(action, details, status='success'):
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        username = session.get('user', 'System')
        hostname = ip
        try:
            if ip in ['127.0.0.1', '::1']:
                hostname = 'localhost'
            else:
                socket.setdefaulttimeout(0.5) 
                hostname_info = socket.gethostbyaddr(ip)
                hostname = hostname_info[0] 
        except:
            hostname = ip 
        finally:
            socket.setdefaulttimeout(None)

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, username, ip, hostname, action, details, status)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """, (username, ip, hostname, action, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"!!! Loq xətası: {e}")

def insert_expense(car_id, expense_type, amount, litr, description,
                   driver_id, assistant_id, planner_id, entered_by):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO expenses (
                    car_id, type, amount, litr, description, entered_by,
                    driver_id_at_expense, assistant_id_at_expense, planner_id_at_expense,
                    created_at, is_deleted
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 0)
            """, (int(car_id), expense_type, float(amount), float(litr), description, entered_by, driver_id, assistant_id, planner_id))
        conn.commit()
    finally:
        conn.close()

def get_dashboard_data():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT c.*, 
                       d.name as driver_name, 
                       a.name as assistant_name, 
                       p.name as planner_name
                FROM cars c
                LEFT JOIN drivers d ON c.driver_id = d.id
                LEFT JOIN assistants a ON c.assistant_id = a.id
                LEFT JOIN planners p ON c.planner_id = p.id
                ORDER BY c.car_number
            """)
            cars = cursor.fetchall()

            full_data = []
            for car in cars:
                brand = car.get('brand') or ""
                model_name = car.get('model_name') or ""
                if (not brand or not model_name) and car.get('model'):
                    parts = car['model'].split(' ', 1)
                    if not brand and parts: brand = parts[0]
                    if not model_name and len(parts) > 1: model_name = parts[1]

                cursor.execute("""
                    SELECT e.*, 
                           d.name as driver_name, 
                           a.name as assistant_name, 
                           p.name as planner_name
                    FROM expenses e
                    LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
                    LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
                    LEFT JOIN planners p ON e.planner_id_at_expense = p.id
                    WHERE e.car_id = %s AND e.is_deleted = 0
                    ORDER BY e.created_at DESC
                """, (int(car['id']),))
                expenses = cursor.fetchall()
                
                total_expense = sum(float(e['amount']) for e in expenses)
                
                processed_expenses = []
                for e in expenses:
                    e_dict = dict(e)
                    if isinstance(e['created_at'], str):
                         e_dict['timestamp_str'] = e['created_at']
                    elif e['created_at']:
                         e_dict['timestamp_str'] = e['created_at'].strftime("%d.%m.%Y %H:%M")
                    else:
                         e_dict['timestamp_str'] = "-"
                    
                    # YENİ: Description-u parçala (Alt növ və təmiz açıqlama)
                    subtype, clean_desc = parse_expense_description(e_dict.get('description', ''))
                    e_dict['subtype'] = subtype
                    e_dict['clean_description'] = clean_desc
                    
                    processed_expenses.append(e_dict)

                car_data = {
                    "id": car['id'],
                    "car_number": car['car_number'],
                    "brand_model": f"{brand} / {model_name}".strip(" /"),
                    "category": car.get('category') or "",
                    "driver_name": car['driver_name'] or "TƏYİN OLUNMAYIB",
                    "assistant_name": car['assistant_name'] or "",
                    "planner_name": car['planner_name'] or "",
                    "total_expense": total_expense,
                    "entered_by": processed_expenses[0]['entered_by'] if processed_expenses else "Yoxdur",
                    "notes": car.get('notes') or "",
                    "expenses": processed_expenses,
                    "brand_raw": brand,
                    "model_name_raw": model_name,
                    "driver_id": car['driver_id'],
                    "assistant_id": car['assistant_id'],
                    "planner_id": car['planner_id'],
                    "has_expenses": total_expense > 0
                }
                full_data.append(car_data)
            
            return full_data
    finally:
        conn.close()

def calculate_experience(start_date_input):
    if not start_date_input: return "-"
    try:
        start_date = None
        if isinstance(start_date_input, str):
            if start_date_input.strip() == "": return "-"
            try:
                start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
            except ValueError: return "Tarix xətası"
        elif isinstance(start_date_input, datetime):
            start_date = start_date_input.date()
        elif isinstance(start_date_input, date):
            start_date = start_date_input
        else:
            return "-"

        if not start_date: return "-"

        today = datetime.now().date()
        if start_date > today: return "Başlamayıb"
            
        delta = relativedelta(today, start_date)
        years = delta.years
        months = delta.months
        
        experience_parts = []
        if years > 0: experience_parts.append(f"{years} il")
        if months > 0: experience_parts.append(f"{months} ay")
        
        if not experience_parts: return "Yeni" if delta.days >= 0 else "-"
            
        return ", ".join(experience_parts)
    except Exception as e:
        print(f"Experience calc error: {e}")
        return "Xəta"

# --- JSON SERİALIZER HELPER ---
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)

# --- DEKORATORLAR ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Bu səhifəyə daxil olmaq üçün Admin icazəniz yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'supervisor':
            flash('İcazə yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('role') in ['user', 'admin', 'supervisor']:
            flash('İcazə yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTE-LAR ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        
        if user and user['password'] == password: 
            if not user.get('is_active', True): 
                log_action('LOGIN_FAILURE', f"Deaktiv istifadəçi cəhdi: {username}", 'failure')
                flash('Sizin hesabınız deaktiv edilib.', 'danger')
                return render_template('login.html')

            session['user'] = user['username']
            session['role'] = user['role']
            session['fullname'] = user['fullname']
            
            log_action('LOGIN_SUCCESS', f"Giriş edildi: {username}", 'success')
            
            if user['role'] == 'supervisor':
                return redirect(url_for('supervisor_dashboard'))
            return redirect(url_for('index'))
        else:
            log_action('LOGIN_FAILURE', f"Yanlış giriş cəhdi: {username}", 'failure')
            return render_template('login.html', error='Yanlış istifadəçi adı və ya parol.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    log_action('LOGOUT', f"Çıxış edildi: {session.get('user')}", 'success')
    session.clear()
    flash("Sistemdən çıxış etdiniz.", 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if session['role'] == 'supervisor':
        return redirect(url_for('supervisor_dashboard'))

    if session['role'] == 'admin':
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as c FROM users WHERE role='user'")
                op_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM cars")
                car_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM drivers")
                dr_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM assistants")
                as_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM planners")
                pl_count = cursor.fetchone()['c']
                
                now = datetime.now()
                cursor.execute("""
                    SELECT SUM(amount) as total FROM expenses 
                    WHERE is_deleted=0 AND MONTH(created_at)=%s AND YEAR(created_at)=%s
                """, (now.month, now.year))
                res = cursor.fetchone()
                monthly_total = float(res['total']) if res and res['total'] else 0.0
                
                cursor.execute("""
                    SELECT type, SUM(amount) as total FROM expenses 
                    WHERE is_deleted=0 AND MONTH(created_at)=%s AND YEAR(created_at)=%s
                    GROUP BY type
                """, (now.month, now.year))
                rows = cursor.fetchall()
                chart_labels = [r['type'] for r in rows]
                chart_data_values = [float(r['total']) for r in rows]
        finally:
            conn.close()

        return render_template('admin_dashboard.html', 
            stats={
                'operator_count': op_count, 'car_count': car_count, 'driver_count': dr_count,
                'assistant_count': as_count, 'planner_count': pl_count, 'monthly_total': monthly_total
            },
            chart_data={'labels': chart_labels, 'data': chart_data_values}
        )
    
    # Operator Dashboard
    dashboard_data = get_dashboard_data()
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drivers ORDER BY name")
            drivers = cursor.fetchall()
            cursor.execute("SELECT * FROM assistants ORDER BY name")
            assistants = cursor.fetchall()
            cursor.execute("SELECT * FROM planners ORDER BY name")
            planners = cursor.fetchall()
    finally:
        conn.close()

    return render_template('operator_dashboard.html', 
        cars=dashboard_data, drivers=drivers, assistants=assistants, planners=planners,
        fine_types=FINE_TYPES, repair_types=REPAIR_TYPES)

@app.route('/add_expense', methods=['POST'])
@operator_required
def add_expense():
    try:
        car_id = request.form.get('car_id')
        expense_type = request.form.get('expense_type')
        amount = float(request.form.get('amount', 0))
        litr = float(request.form.get('litr', 0) or 0)
        description = request.form.get('description', '')
        
        fuel_subtype = request.form.get('fuel_subtype', '')
        fine_subtype = request.form.get('fine_subtype', '')
        repair_subtype = request.form.get('repair_subtype', '')

        prefix = ""
        if expense_type == 'Yanacaq' and fuel_subtype:
            prefix = f"[{fuel_subtype}] "
        elif expense_type == 'Cərimə' and fine_subtype:
            prefix = f"[{fine_subtype}] "
        elif expense_type == 'Təmir' and repair_subtype:
            prefix = f"[{repair_subtype}] "
        
        final_description = f"{prefix}{description}"

        car = get_car_by_id(car_id)
        if car:
            insert_expense(
                car_id, expense_type, amount, litr, final_description,
                car['driver_id'], car['assistant_id'], car['planner_id'], session['user']
            )
            log_action('ADD_EXPENSE', f"{car['car_number']} - {amount} AZN ({expense_type})", 'success')
            flash('Xərc əlavə edildi.', 'success')
        else:
            flash('Avtomobil tapılmadı.', 'danger')
            
    except Exception as e:
        flash(f'Xəta baş verdi: {str(e)}', 'danger')
        print(f"Add expense error: {e}")
    
    return redirect(url_for('index'))

@app.route('/update_car_meta', methods=['POST'])
@operator_required
def update_car_meta():
    car_id = request.form.get('car_id')
    
    def get_val_or_none(field):
        val = request.form.get(field)
        return int(val) if val else None

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE cars SET brand=%s, model_name=%s, category=%s,
                driver_id=%s, assistant_id=%s, planner_id=%s, notes=%s
                WHERE id=%s
            """, (
                request.form.get('brand', ''),
                request.form.get('model_name', ''),
                request.form.get('category', ''),
                get_val_or_none('driver_id'),
                get_val_or_none('assistant_id'),
                get_val_or_none('planner_id'),
                request.form.get('notes', ''),
                car_id
            ))
        conn.commit()
    finally:
        conn.close()
    
    log_action('UPDATE_CAR', f"Avtomobil ID {car_id} məlumatları yeniləndi", 'success')
    flash('Məlumatlar yeniləndi.', 'success')
    return redirect(url_for('index'))

# --- ADMIN ROUTES ---

@app.route('/admin/drivers')
@operator_required
def admin_drivers():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drivers ORDER BY name")
            drivers = cursor.fetchall()
            for d in drivers:
                driver_id = int(d['id'])
                cursor.execute("SELECT id FROM expenses WHERE driver_id_at_expense=%s AND is_deleted=0 LIMIT 1", (driver_id,))
                d['has_expenses'] = cursor.fetchone() is not None
                d['experience_str'] = calculate_experience(d.get('start_date'))
    except Exception as e:
        flash(f"Server xətası (Sürücülər): {str(e)}", "danger")
        drivers = []
    finally:
        conn.close()
    return render_template('admin_drivers.html', drivers=drivers)

@app.route('/admin/drivers/add', methods=['POST'])
@operator_required
def add_driver():
    name = request.form.get('name')
    if not name: return redirect(url_for('admin_drivers'))
    start_date = request.form.get('start_date') or None
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO drivers (name, license_no, phone, start_date) VALUES (%s, %s, %s, %s)",
                           (name, request.form.get('license_no'), request.form.get('phone'), start_date))
        conn.commit()
    finally:
        conn.close()
    flash('Sürücü əlavə edildi', 'success')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/driver/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_driver(id):
    if request.method == 'POST':
        start_date = request.form.get('start_date') or None
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE drivers SET name=%s, license_no=%s, phone=%s, start_date=%s WHERE id=%s
                """, (request.form.get('name'), request.form.get('license_no'), request.form.get('phone'), start_date, id))
            conn.commit()
        finally:
            conn.close()
        flash('Yeniləndi', 'success')
        return redirect(url_for('admin_drivers'))
    driver = get_driver_by_id(id)
    return render_template('edit_driver.html', driver=driver)

@app.route('/admin/driver/delete/<int:id>', methods=['POST'])
@operator_required
def delete_driver(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM expenses WHERE driver_id_at_expense=%s AND is_deleted=0 LIMIT 1", (id,))
            if cursor.fetchone():
                flash('Xərcləri olan sürücünü silmək olmaz.', 'danger')
                return redirect(url_for('admin_drivers'))
            cursor.execute("UPDATE cars SET driver_id=NULL WHERE driver_id=%s", (id,))
            cursor.execute("DELETE FROM drivers WHERE id=%s", (id,))
        conn.commit()
    finally:
        conn.close()
    flash('Sürücü silindi.', 'success')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/drivers/bulk_add', methods=['POST'])
@operator_required
def bulk_add_driver():
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT license_no FROM drivers WHERE license_no IS NOT NULL AND license_no != ''")
            existing_licenses = {row['license_no'] for row in cursor.fetchall()}
            for line in bulk_data.splitlines():
                parts = line.split(';')
                if not parts or not parts[0].strip(): continue
                name = parts[0].strip()
                license_no = parts[1].strip() if len(parts) > 1 else None
                phone = parts[2].strip() if len(parts) > 2 else None
                start_date = parts[3].strip() if len(parts) > 3 else None

                if license_no and license_no in existing_licenses: continue
                if start_date:
                    try: datetime.strptime(start_date, '%Y-%m-%d')
                    except ValueError: start_date = None

                cursor.execute("""
                    INSERT INTO drivers (name, license_no, phone, start_date) 
                    VALUES (%s, %s, %s, %s)
                """, (name, license_no, phone, start_date))
                if license_no: existing_licenses.add(license_no)
                added_count += 1
        conn.commit()
    finally:
        conn.close()
    flash(f"{added_count} sürücü əlavə edildi.", 'success')
    return redirect(url_for('admin_drivers'))

# --- ADMIN REPORTS ---

@app.route('/admin/reports')
def admin_reports():
    if session.get('role') not in ['admin', 'supervisor']:
        flash('İcazə yoxdur.', 'danger')
        return redirect(url_for('index'))

    # Filtrlər
    f_car = request.args.get('car_id')
    f_driver = request.args.get('driver_id')
    f_type = request.args.get('expense_type')
    f_subtype = request.args.get('subtype_filter')

    start_date = request.args.get('start_date') or (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = request.args.get('end_date')

    sql = """
        SELECT e.*, 
               e.created_at as timestamp,
               e.id as expense_id,
               c.car_number, c.model,
               u.fullname as user_fullname,
               d.name as driver_name_at_expense,
               a.name as assistant_name_at_expense,
               p.name as planner_name_at_expense
        FROM expenses e
        LEFT JOIN cars c ON e.car_id = c.id
        LEFT JOIN users u ON e.entered_by = u.username
        LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
        LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
        LEFT JOIN planners p ON e.planner_id_at_expense = p.id
        WHERE e.is_deleted = 0
    """
    params = []

    if f_car:
        sql += " AND e.car_id = %s"
        params.append(f_car)
    if f_driver:
        sql += " AND e.driver_id_at_expense = %s"
        params.append(f_driver)
    if f_type:
        sql += " AND e.type = %s"
        params.append(f_type)
    if f_subtype:
        sql += " AND e.description LIKE %s"
        params.append(f"%[{f_subtype}]%")

    if start_date:
        sql += " AND DATE(e.created_at) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(e.created_at) <= %s"
        params.append(end_date)
    
    sql += " ORDER BY e.created_at DESC"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            reports = cursor.fetchall()
            total_amount = sum(float(r['amount']) for r in reports)

            formatted_reports = []
            for r in reports:
                expense_obj = r
                expense_obj['timestamp'] = r['created_at']
                
                # YENİ: Admin panelində də açıqlamanı parse edirik
                subtype, clean_desc = parse_expense_description(r.get('description', ''))
                expense_obj['subtype'] = subtype
                expense_obj['clean_description'] = clean_desc

                car_obj = {'car_number': r['car_number'], 'model': r['model']} if r['car_number'] else None
                user_obj = {'fullname': r['user_fullname']} if r['user_fullname'] else None
                
                formatted_reports.append({
                    'expense': expense_obj,
                    'car': car_obj,
                    'user': user_obj,
                    'driver_name_at_expense': r['driver_name_at_expense'] or "-",
                    'assistant_name_at_expense': r['assistant_name_at_expense'] or "-",
                    'planner_name_at_expense': r['planner_name_at_expense'] or "-"
                })
            
            cursor.execute("SELECT * FROM cars")
            cars = cursor.fetchall()
            cursor.execute("SELECT * FROM drivers")
            drivers = cursor.fetchall()
            cursor.execute("SELECT * FROM assistants")
            assistants = cursor.fetchall()
            cursor.execute("SELECT * FROM planners")
            planners = cursor.fetchall()
            cursor.execute("SELECT * FROM users WHERE role='user'")
            operators = cursor.fetchall()

    finally:
        conn.close()

    return render_template('admin_reports.html', 
        reports=formatted_reports, total_amount=total_amount,
        cars=cars, drivers=drivers, assistants=assistants, planners=planners, operators=operators,
        expense_types=EXPENSE_TYPES,
        fine_types=FINE_TYPES, repair_types=REPAIR_TYPES, 
        selected_filters=request.args
    )

@app.route('/admin/expense/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    if session.get('role') not in ['admin', 'supervisor']:
        flash('İcazə yoxdur.', 'danger')
        return redirect(url_for('index'))
        
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE expenses 
                SET is_deleted = 1, deleted_by_user = %s, deleted_at = NOW()
                WHERE id = %s
            """, (session['fullname'], id))
        conn.commit()
    finally:
        conn.close()
    
    log_action('DELETE_EXPENSE', f"Xərc ID {id} silindi ({session['role']})", 'success')
    flash('Xərc silindi.', 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/deleted_reports')
@admin_required
def admin_deleted_reports():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, e.id as expense_id, c.car_number, u.fullname as user_fullname,
                       d.name as driver_name_at_expense,
                       a.name as assistant_name_at_expense,
                       p.name as planner_name_at_expense
                FROM expenses e
                LEFT JOIN cars c ON e.car_id = c.id
                LEFT JOIN users u ON e.entered_by = u.username
                LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
                LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
                LEFT JOIN planners p ON e.planner_id_at_expense = p.id
                WHERE e.is_deleted = 1
                ORDER BY e.deleted_at DESC
            """)
            rows = cursor.fetchall()
            reports = []
            for r in rows:
                r['timestamp'] = r['created_at']
                reports.append({
                    'expense': r,
                    'car': {'car_number': r['car_number']},
                    'user': {'fullname': r['user_fullname']},
                    'driver_name_at_expense': r['driver_name_at_expense'],
                    'assistant_name_at_expense': r['assistant_name_at_expense'],
                    'planner_name_at_expense': r['planner_name_at_expense']
                })
    finally:
        conn.close()
    return render_template('admin_deleted_reports.html', reports=reports)

@app.route('/admin/expense/restore/<int:id>', methods=['POST'])
@admin_required
def restore_expense(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE expenses SET is_deleted=0 WHERE id=%s", (id,))
        conn.commit()
    finally:
        conn.close()
    flash('Xərc bərpa edildi.', 'success')
    return redirect(url_for('admin_deleted_reports'))

# --- SUPERVISOR SECTION ---

@app.route('/supervisor/dashboard')
@supervisor_required
def supervisor_dashboard():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as c FROM users")
            total_users = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1")
            active_users = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM users WHERE is_active=0")
            passive_users = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM audit_logs")
            total_logs = cursor.fetchone()['c']
            cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
            roles_data = cursor.fetchall()
            
            labels = [r['role'] for r in roles_data]
            data = [r['count'] for r in roles_data]
            
            stats = {'total_users': total_users, 'active_users': active_users, 'passive_users': passive_users, 'total_logs': total_logs}
            chart_data = {'labels': labels, 'data': data}
    finally:
        conn.close()
    return render_template('supervisor_dashboard.html', stats=stats, chart_data=chart_data)

@app.route('/supervisor/reports')
@supervisor_required
def supervisor_reports():
    username = request.args.get('username')
    action = request.args.get('action')
    start_date = request.args.get('start_date')
    
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if username: sql += " AND username = %s"; params.append(username)
    if action: sql += " AND action = %s"; params.append(action)
    if start_date: sql += " AND DATE(timestamp) >= %s"; params.append(start_date)
    sql += " ORDER BY timestamp DESC LIMIT 500"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            reports = cursor.fetchall()
            cursor.execute("SELECT DISTINCT username FROM audit_logs")
            all_usernames = [r['username'] for r in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT action FROM audit_logs")
            all_actions = [r['action'] for r in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT hostname FROM audit_logs")
            all_hostnames = [r['hostname'] for r in cursor.fetchall()]
    finally:
        conn.close()
    return render_template('supervisor_reports.html',
        reports=reports,
        all_usernames=all_usernames, all_actions=all_actions, all_hostnames=all_hostnames,
        selected_filters=request.args
    )

@app.route('/supervisor/data')
@supervisor_required
def supervisor_data():
    return render_template('supervisor_data.html')

@app.route('/supervisor/export')
@supervisor_required
def export_db():
    tables = ['users', 'cars', 'drivers', 'assistants', 'planners', 'expenses', 'expense_types', 'audit_logs']
    db_dump = {}
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                db_dump[table] = rows
    finally:
        conn.close()
    
    json_str = json.dumps(db_dump, cls=DateTimeEncoder, ensure_ascii=False, indent=2)
    mem = io.BytesIO()
    mem.write(json_str.encode('utf-8'))
    mem.seek(0)
    filename = f"asis_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='application/json')

@app.route('/supervisor/import', methods=['POST'])
@supervisor_required
def import_db():
    if 'backup_file' not in request.files:
        flash('Fayl seçilməyib.', 'danger')
        return redirect(url_for('supervisor_data'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('Fayl seçilməyib.', 'danger')
        return redirect(url_for('supervisor_data'))

    try:
        data = json.load(file)
        tables = ['users', 'cars', 'drivers', 'assistants', 'planners', 'expenses', 'expense_types', 'audit_logs']
        
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
                for table in tables:
                    if table in data:
                        rows = data[table]
                        if not rows: continue
                        cursor.execute(f"TRUNCATE TABLE {table}")
                        for row in rows:
                            columns = ', '.join(row.keys())
                            placeholders = ', '.join(['%s'] * len(row))
                            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                            cursor.execute(sql, list(row.values()))
                cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
            flash('Məlumat bazası uğurla bərpa edildi.', 'success')
            log_action('DB_RESTORE', 'Bazadan geri yükləmə (Import) edildi', 'success')
        except Exception as db_err:
            conn.rollback()
            flash(f"Baza xətası: {str(db_err)}", 'danger')
            print(f"Import DB Error: {db_err}")
        finally:
            conn.close()

    except Exception as e:
        flash(f"Fayl xətası: {str(e)}", 'danger')
    
    return redirect(url_for('supervisor_data'))

# --- DIGƏR ADMIN FUNKSIYALARI ---

@app.route('/admin/cars')
@operator_required
def admin_cars():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cars")
            cars = cursor.fetchall()
            drivers = get_all_drivers()
            assistants = get_all_assistants()
            planners = get_all_planners()
            for c in cars:
                cursor.execute("SELECT id FROM expenses WHERE car_id=%s AND is_deleted=0 LIMIT 1", (c['id'],))
                c['has_expenses'] = cursor.fetchone() is not None
    finally:
        conn.close()
    return render_template('admin_cars.html', cars=cars, drivers=drivers, assistants=assistants, planners=planners)

@app.route('/admin/cars/add', methods=['POST'])
@operator_required
def add_car():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO cars (car_number, model, driver_id, assistant_id, planner_id) VALUES (%s, %s, %s, %s, %s)",
                           (request.form['car_number'], request.form['model'], 
                            request.form.get('driver_id') or None, request.form.get('assistant_id') or None, request.form.get('planner_id') or None))
        conn.commit()
        conn.close()
        flash('Avtomobil əlavə edildi.', 'success')
    except Exception as e:
        flash(f'Xəta: {e}', 'danger')
    return redirect(url_for('admin_cars'))

@app.route('/admin/car/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_car(id):
    if request.method == 'POST':
        conn = get_connection()
        # Helper to handle empty strings as None
        def get_val_or_none(field):
            val = request.form.get(field)
            return int(val) if val and val.isdigit() else None

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE cars SET car_number=%s, model=%s, driver_id=%s, assistant_id=%s, planner_id=%s 
                WHERE id=%s
            """, (
                request.form['car_number'], 
                request.form['model'], 
                get_val_or_none('driver_id'),
                get_val_or_none('assistant_id'),
                get_val_or_none('planner_id'),
                id
            ))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_cars'))
    
    car = get_car_by_id(id)
    
    # 1. Dublikat yoxlanışı üçün bütün maşınları çəkirik
    all_cars = get_all_cars()
    
    # 2. Məşğul olan Sürücü və Köməkçiləri tapırıq (Cari maşını istisna etməklə)
    occupied_driver_ids = set()
    occupied_assistant_ids = set()
    
    for c in all_cars:
        if c['id'] != id: # Cari redaktə olunan maşın deyil
            if c['driver_id']: occupied_driver_ids.add(c['driver_id'])
            if c['assistant_id']: occupied_assistant_ids.add(c['assistant_id'])
    
    # 3. Bütün personalı bazadan çəkirik
    all_drivers = get_all_drivers()
    all_assistants = get_all_assistants()
    all_planners = get_all_planners() # Planlamaçılar çox maşına baxa bilər, filtrləmirik
    
    # 4. Yalnız boş olanları (və ya bu maşına təyin olunanları) siyahıda saxlayırıq
    available_drivers = [d for d in all_drivers if d['id'] not in occupied_driver_ids]
    available_assistants = [a for a in all_assistants if a['id'] not in occupied_assistant_ids]
    
    return render_template('edit_car.html', 
                           car=car, 
                           drivers=available_drivers, 
                           assistants=available_assistants, 
                           planners=all_planners)

@app.route('/admin/car/delete/<int:id>', methods=['POST'])
@operator_required
def delete_car(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM expenses WHERE car_id=%s AND is_deleted=0 LIMIT 1", (id,))
            if cursor.fetchone():
                flash('Xərci olan avtomobil silinə bilməz.', 'danger')
            else:
                cursor.execute("DELETE FROM cars WHERE id=%s", (id,))
                conn.commit()
                flash('Silindi.', 'success')
    finally:
        conn.close()
    return redirect(url_for('admin_cars'))

@app.route('/admin/cars/bulk_add', methods=['POST'])
@operator_required
def bulk_add_car():
    bulk_data = request.form.get('bulk_data', '')
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT car_number FROM cars")
            existing = {row['car_number'] for row in cursor.fetchall()}
            for line in bulk_data.splitlines():
                parts = line.split(';')
                if len(parts) >= 2:
                    num = parts[0].strip()
                    model = parts[1].strip()
                    if num and num not in existing:
                        cursor.execute("INSERT INTO cars (car_number, model) VALUES (%s, %s)", (num, model))
                        existing.add(num)
        conn.commit()
    finally:
        conn.close()
    flash('Toplu əlavə edildi.', 'success')
    return redirect(url_for('admin_cars'))

@app.route('/admin/assistants')
@operator_required
def admin_assistants():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assistants ORDER BY name")
            assistants = cursor.fetchall()
            for a in assistants:
                cursor.execute("SELECT id FROM expenses WHERE assistant_id_at_expense=%s AND is_deleted=0 LIMIT 1", (a['id'],))
                a['has_expenses'] = cursor.fetchone() is not None
    finally:
        conn.close()
    return render_template('admin_assistants.html', assistants=assistants)

@app.route('/admin/assistants/add', methods=['POST'])
@operator_required
def add_assistant():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO assistants (name) VALUES (%s)", (request.form['name'],))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_assistants'))

@app.route('/admin/assistant/edit/<int:aid>', methods=['GET', 'POST'])
@operator_required
def edit_assistant(aid):
    if request.method == 'POST':
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE assistants SET name=%s WHERE id=%s", (request.form['name'], aid))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_assistants'))
    assistant = get_assistant_by_id(aid)
    return render_template('edit_assistant.html', assistant=assistant)

@app.route('/admin/assistant/delete/<int:aid>', methods=['POST'])
@operator_required
def delete_assistant(aid):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE cars SET assistant_id=NULL WHERE assistant_id=%s", (aid,))
            cursor.execute("DELETE FROM assistants WHERE id=%s", (aid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_assistants'))

@app.route('/admin/assistants/bulk_add', methods=['POST'])
@operator_required
def bulk_add_assistant():
    bulk_data = request.form.get('bulk_data', '')
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for line in bulk_data.splitlines():
                if line.strip(): cursor.execute("INSERT INTO assistants (name) VALUES (%s)", (line.strip(),))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_assistants'))

@app.route('/admin/planners')
@operator_required
def admin_planners():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM planners ORDER BY name")
            planners = cursor.fetchall()
            for p in planners:
                cursor.execute("SELECT id FROM expenses WHERE planner_id_at_expense=%s AND is_deleted=0 LIMIT 1", (p['id'],))
                p['has_expenses'] = cursor.fetchone() is not None
    finally:
        conn.close()
    return render_template('admin_planners.html', planners=planners)

@app.route('/admin/planners/add', methods=['POST'])
@operator_required
def add_planner():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO planners (name) VALUES (%s)", (request.form['name'],))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_planners'))

@app.route('/admin/planner/edit/<int:pid>', methods=['GET', 'POST'])
@operator_required
def edit_planner(pid):
    if request.method == 'POST':
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE planners SET name=%s WHERE id=%s", (request.form['name'], pid))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_planners'))
    planner = get_planner_by_id(pid)
    return render_template('edit_planner.html', planner=planner)

@app.route('/admin/planner/delete/<int:pid>', methods=['POST'])
@operator_required
def delete_planner(pid):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE cars SET planner_id=NULL WHERE planner_id=%s", (pid,))
            cursor.execute("DELETE FROM planners WHERE id=%s", (pid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_planners'))

@app.route('/admin/planners/bulk_add', methods=['POST'])
@operator_required
def bulk_add_planner():
    bulk_data = request.form.get('bulk_data', '')
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for line in bulk_data.splitlines():
                if line.strip(): cursor.execute("INSERT INTO planners (name) VALUES (%s)", (line.strip(),))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_planners'))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = get_operators()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def add_user():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (fullname, username, password, role) VALUES (%s, %s, %s, %s)",
                           (request.form['fullname'], request.form['username'], request.form['password'], request.form['role']))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/user/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    if request.method == 'POST':
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "UPDATE users SET fullname=%s, username=%s, role=%s"
            params = [request.form['fullname'], request.form['username'], request.form['role']]
            if request.form['password']:
                sql += ", password=%s"
                params.append(request.form['password'])
            sql += " WHERE id=%s"
            params.append(id)
            cursor.execute(sql, tuple(params))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    user = get_user_by_id(id)
    return render_template('edit_user.html', user=user)

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id=%s", (id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/supervisor/operations')
@supervisor_required
def supervisor_operations():
    users = get_all_users()
    return render_template('supervisor_operations.html', users=users)

@app.route('/supervisor/operations/add_user', methods=['POST'])
@supervisor_required
def supervisor_add_user():
    return add_user() 

@app.route('/supervisor/user/edit/<int:id>', methods=['GET', 'POST'])
@supervisor_required
def supervisor_edit_user(id):
    if request.method == 'POST':
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "UPDATE users SET fullname=%s, username=%s, role=%s, is_active=%s"
            params = [request.form['fullname'], request.form['username'], request.form['role'], is_active]
            if request.form['password']:
                sql += ", password=%s"
                params.append(request.form['password'])
            sql += " WHERE id=%s"
            params.append(id)
            cursor.execute(sql, tuple(params))
        conn.commit()
        conn.close()
        return redirect(url_for('supervisor_operations'))
    user = get_user_by_id(id)
    return render_template('supervisor_edit_user.html', user=user)

@app.route('/supervisor/user/delete/<int:id>', methods=['POST'])
@supervisor_required
def supervisor_delete_user(id):
    return delete_user(id)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)