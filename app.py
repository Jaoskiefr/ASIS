# -*- coding: utf-8 -*-
from db import get_connection
# check_and_update_tables funksiyasını təhlükəsiz çağırmaq üçün
try:
    from db import check_and_update_tables
    HAS_MIGRATION = True
except ImportError:
    HAS_MIGRATION = False

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from functools import wraps
import socket
import json
import io
import re
import traceback # Xətanı ekrana çıxarmaq üçün

app = Flask(__name__)
app.secret_key = 'ASIS_Sizin_Real_Gizli_Acariniz_Burada_Olsun' 

# Proqram işə düşəndə bazanı yoxlayır (əgər funksiya varsa)
if HAS_MIGRATION:
    try:
        check_and_update_tables()
    except Exception as e:
        print(f"Migration error: {e}")

# --- SABİT SİYAHILAR ---
EXPENSE_TYPES = [
    'Yanacaq',
    'Təmir',
    'Yol xərci',
    'Yuyulma',
    'Sığorta',
    'Cərimə',
    'Digər'
]

FINE_TYPES = [
    'Avtobus zolağı',
    'Sürət həddini aşma',
    'Dayanma-durma qaydası',
    'Qırmızı işıq',
    'Təhlükəsizlik kəməri',
    'Texniki baxış / Sığorta yoxdur',
    'Digər'
]

REPAIR_TYPES = [
    'Təkər təmiri / Yenisi',
    'Akumulyator',
    'Yağ dəyişimi',
    'Nakladka / Əyləc sistemi',
    'Mühərrik təmiri',
    'Kosmetik / Dəmirçi işi',
    'Digər'
]

FUEL_TYPES = [
    'Dizel',
    'AI-92',
    'AI-95'
]

DEFAULT_EXPENSE_SUBTYPES = {
    'Yanacaq': FUEL_TYPES,
    'Cərimə': FINE_TYPES,
    'Təmir': REPAIR_TYPES
}

# --- KÖMƏKÇİ PARSE FUNKSİYASI ---
def parse_expense_description(description):
    if not description: return "-", "-"
    try:
        match = re.match(r'^\[(.*?)\]\s*(.*)', description, re.DOTALL)
        if match:
            subtype = match.group(1)
            clean_desc = match.group(2)
            if not clean_desc: clean_desc = "-"
            return subtype, clean_desc
        else:
            return "-", description
    except:
        return "-", str(description)

# --- VERİLƏNLƏR BAZASI GETTERS ---
def get_connection_safe():
    # Helper to prevent crashes if DB fails
    return get_connection()

def get_car_by_id(car_id):
    if not car_id: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
            return cursor.fetchone()
    finally: conn.close()

def get_driver_by_id(driver_id):
    if not driver_id: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
            return cursor.fetchone()
    finally: conn.close()

def get_assistant_by_id(aid):
    if not aid: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assistants WHERE id = %s", (aid,))
            return cursor.fetchone()
    finally: conn.close()

def get_planner_by_id(pid):
    if not pid: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM planners WHERE id = %s", (pid,))
            return cursor.fetchone()
    finally: conn.close()

def get_user_by_username(username):
    if not username: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    finally: conn.close()

def get_user_by_id(user_id):
    if not user_id: return None
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally: conn.close()

# --- SİYAHI FUNKSİYALARI (AKTİV/PASSİV) ---
def get_all_drivers(only_active=False):
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM drivers WHERE is_deleted = 0"
            if only_active: sql += " AND is_active = 1"
            sql += " ORDER BY name"
            cursor.execute(sql)
            return cursor.fetchall()
    finally: conn.close()

def get_all_assistants(only_active=False):
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM assistants WHERE is_deleted = 0"
            if only_active: sql += " AND is_active = 1"
            sql += " ORDER BY name"
            cursor.execute(sql)
            return cursor.fetchall()
    finally: conn.close()

def get_all_planners(only_active=False):
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM planners WHERE is_deleted = 0"
            if only_active: sql += " AND is_active = 1"
            sql += " ORDER BY name"
            cursor.execute(sql)
            return cursor.fetchall()
    finally: conn.close()

def get_all_cars(only_active=False):
    conn = get_connection_safe()
    try:
        with conn.cursor() as cursor:
            # is_deleted yoxdursa xəta verməsin deyə sadə select
            sql = "SELECT * FROM cars WHERE 1=1"
            try:
                sql += " AND (is_deleted = 0)"
            except: pass
            
            if only_active: sql += " AND is_active = 1"
            sql += " ORDER BY car_number"
            cursor.execute(sql)
            return cursor.fetchall()
    except:
        # Fallback if columns missing
        conn = get_connection_safe()
        with conn.cursor() as c:
            c.execute("SELECT * FROM cars ORDER BY car_number")
            return c.fetchall()
    finally: conn.close()

def get_operators():
    conn = get_connection_safe()
    try:
        with conn.cursor() as c: c.execute("SELECT * FROM users WHERE role = 'user' ORDER BY fullname"); return c.fetchall()
    finally: conn.close()

def get_all_users():
    conn = get_connection_safe()
    try:
        with conn.cursor() as c: c.execute("SELECT * FROM users ORDER BY fullname"); return c.fetchall()
    finally: conn.close()

def get_setting(setting_key, default_value=None):
    """Sistem ayarını oxuyur. Cədvəl yoxdursa default qaytarır ki proqram dayanmasın."""
    conn = None
    try:
        conn = get_connection_safe()
        with conn.cursor() as c:
            c.execute("SELECT setting_value FROM app_settings WHERE setting_key=%s", (setting_key,))
            row = c.fetchone()
            return row['setting_value'] if row else default_value
    except Exception:
        return default_value
    finally:
        try:
            if conn: conn.close()
        except Exception:
            pass

def set_setting(setting_key, setting_value):
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), updated_at=NOW()
            """, (setting_key, str(setting_value)))
        conn.commit()
    finally:
        conn.close()

def is_past_expense_allowed():
    return str(get_setting('allow_past_expense_date', '1')) == '1'

def _safe_json_load(value, default):
    try:
        if not value:
            return default
        loaded = json.loads(value)
        return loaded if loaded else default
    except Exception:
        return default

def _clean_lines(raw):
    items = []
    seen = set()
    for line in (raw or '').splitlines():
        val = line.strip()
        if not val:
            continue
        key = val.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(val)
    return items

def parse_subtype_settings(raw, known_types=None):
    """Ayar səhifəsindəki 'Növ: alt1, alt2' formatını dict-ə çevirir."""
    known_types = known_types or []
    data = {}
    for line in (raw or '').splitlines():
        line = line.strip()
        if not line or ':' not in line:
            continue
        name, values = line.split(':', 1)
        name = name.strip()
        if not name:
            continue
        vals = []
        seen = set()
        for part in values.replace(';', ',').split(','):
            val = part.strip()
            if not val:
                continue
            key = val.casefold()
            if key not in seen:
                vals.append(val)
                seen.add(key)
        data[name] = vals
    for t in known_types:
        data.setdefault(t, [])
    return data

def get_expense_types():
    types = _safe_json_load(get_setting('expense_types_json', None), EXPENSE_TYPES)
    return [str(x).strip() for x in types if str(x).strip()] or EXPENSE_TYPES

def get_expense_subtypes():
    defaults = {k: list(v) for k, v in DEFAULT_EXPENSE_SUBTYPES.items()}
    data = _safe_json_load(get_setting('expense_subtypes_json', None), defaults)
    if not isinstance(data, dict):
        data = defaults
    clean = {}
    for t in get_expense_types():
        vals = data.get(t, [])
        if isinstance(vals, str):
            vals = [x.strip() for x in vals.replace(';', ',').split(',') if x.strip()]
        clean[t] = [str(x).strip() for x in vals if str(x).strip()]
    return clean

def get_all_subtype_values():
    vals = []
    seen = set()
    for group in get_expense_subtypes().values():
        for val in group:
            key = val.casefold()
            if key not in seen:
                vals.append(val)
                seen.add(key)
    return vals

def parse_expense_datetime(value):
    """Formadan gələn tarix/saatı təhlükəsiz datetime-a çevirir."""
    if not value:
        return datetime.now()
    value = value.strip()
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(value, fmt)
            if fmt == '%Y-%m-%d':
                now = datetime.now()
                parsed = parsed.replace(hour=now.hour, minute=now.minute, second=0)
            return parsed
        except ValueError:
            continue
    raise ValueError('Xərc tarixi düzgün formatda deyil.')

# --- LOG & EXPENSE ---
def log_action(action, details, status='success'):
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        u = session.get('user', 'System')
        conn = get_connection_safe()
        with conn.cursor() as c:
            c.execute("INSERT INTO audit_logs (timestamp, username, ip, hostname, action, details, status) VALUES (NOW(), %s, %s, %s, %s, %s, %s)",
                      (u, ip, ip, action, details, status))
        conn.commit(); conn.close()
    except: pass

def insert_expense(car_id, expense_type, amount, litr, description, did, aid, pid, entered_by, expense_datetime=None):
    if expense_datetime is None:
        expense_datetime = datetime.now()
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("""INSERT INTO expenses (car_id, type, amount, litr, description, entered_by, driver_id_at_expense, assistant_id_at_expense, planner_id_at_expense, created_at, is_deleted)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                      (int(car_id), expense_type, float(amount), float(litr), description, entered_by, did, aid, pid, expense_datetime))
        conn.commit()
    finally: conn.close()

def get_dashboard_data():
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT c.*, d.name as driver_name, a.name as assistant_name, p.name as planner_name
                         FROM cars c LEFT JOIN drivers d ON c.driver_id=d.id LEFT JOIN assistants a ON c.assistant_id=a.id LEFT JOIN planners p ON c.planner_id=p.id
                         WHERE (c.is_deleted=0 OR c.is_deleted IS NULL) ORDER BY c.car_number""")
            cars = c.fetchall()
            data = []
            for car in cars:
                # Burada da COLLATE əlavə edə bilərik, amma sürücü adları ilə xərclər arasında join yoxdur, birbaşa expense cədvəlindən götürülür
                # JOIN expenses on drivers
                c.execute("""SELECT e.*, d.name as driver_name, a.name as assistant_name, p.name as planner_name
                             FROM expenses e 
                             LEFT JOIN drivers d ON e.driver_id_at_expense=d.id 
                             LEFT JOIN assistants a ON e.assistant_id_at_expense=a.id 
                             LEFT JOIN planners p ON e.planner_id_at_expense=p.id
                             WHERE e.car_id=%s AND e.is_deleted=0 ORDER BY e.created_at DESC""", (car['id'],))
                expenses = c.fetchall()
                total = sum(float(e['amount'] or 0) for e in expenses)
                proc_exp = []
                for e in expenses:
                    d_e = dict(e)
                    # Tarix NULL olarsa
                    if e['created_at']:
                        d_e['timestamp_str'] = e['created_at'].strftime("%d.%m.%Y %H:%M")
                    else:
                        d_e['timestamp_str'] = "-"
                    
                    sub, clean = parse_expense_description(d_e.get('description', ''))
                    d_e.update({'subtype': sub, 'clean_description': clean})
                    proc_exp.append(d_e)
                
                brand = car.get('brand') or ""
                model = car.get('model_name') or ""
                if (not brand or not model) and car.get('model'):
                    parts = car['model'].split(' ', 1)
                    brand = parts[0] if not brand else brand
                    model = parts[1] if not model and len(parts)>1 else model

                data.append({
                    "id": car['id'], "car_number": car['car_number'], "brand_model": f"{brand} / {model}".strip(" /"),
                    "category": car.get('category') or "", "driver_name": car['driver_name'] or "TƏYİN OLUNMAYIB",
                    "assistant_name": car['assistant_name'] or "", "planner_name": car['planner_name'] or "",
                    "total_expense": total, "entered_by": proc_exp[0]['entered_by'] if proc_exp else "Yoxdur",
                    "notes": car.get('notes') or "", "expenses": proc_exp,
                    "brand_raw": brand, "model_name_raw": model,
                    "driver_id": car['driver_id'], "assistant_id": car['assistant_id'], "planner_id": car['planner_id'],
                    "has_expenses": total > 0, "is_active": car.get('is_active', 1)
                })
            return data
    finally: conn.close()



def get_management_counts(table_name, id_field):
    """Kart görünüşü üçün xərcləri və toplamları hesablayır."""
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            if table_name == 'cars':
                c.execute("""
                    SELECT c.*, d.name AS driver_name, a.name AS assistant_name, p.name AS planner_name,
                           COUNT(e.id) AS expense_count, COALESCE(SUM(e.amount),0) AS total_amount
                    FROM cars c
                    LEFT JOIN drivers d ON c.driver_id=d.id
                    LEFT JOIN assistants a ON c.assistant_id=a.id
                    LEFT JOIN planners p ON c.planner_id=p.id
                    LEFT JOIN expenses e ON e.car_id=c.id AND e.is_deleted=0
                    WHERE (c.is_deleted=0 OR c.is_deleted IS NULL)
                    GROUP BY c.id
                    ORDER BY c.car_number
                """)
            elif table_name == 'drivers':
                c.execute("""
                    SELECT d.*,
                           (SELECT COUNT(*) FROM expenses e WHERE e.driver_id_at_expense=d.id AND e.is_deleted=0) AS expense_count,
                           (SELECT COALESCE(SUM(e.amount),0) FROM expenses e WHERE e.driver_id_at_expense=d.id AND e.is_deleted=0) AS total_amount,
                           (SELECT COUNT(*) FROM cars c2 WHERE c2.driver_id=d.id AND (c2.is_deleted=0 OR c2.is_deleted IS NULL)) AS car_count
                    FROM drivers d
                    WHERE d.is_deleted=0
                    ORDER BY d.name
                """)
            elif table_name == 'assistants':
                c.execute("""
                    SELECT a.*,
                           (SELECT COUNT(*) FROM expenses e WHERE e.assistant_id_at_expense=a.id AND e.is_deleted=0) AS expense_count,
                           (SELECT COALESCE(SUM(e.amount),0) FROM expenses e WHERE e.assistant_id_at_expense=a.id AND e.is_deleted=0) AS total_amount,
                           (SELECT COUNT(*) FROM cars c2 WHERE c2.assistant_id=a.id AND (c2.is_deleted=0 OR c2.is_deleted IS NULL)) AS car_count
                    FROM assistants a
                    WHERE a.is_deleted=0
                    ORDER BY a.name
                """)
            elif table_name == 'planners':
                c.execute("""
                    SELECT p.*,
                           (SELECT COUNT(*) FROM expenses e WHERE e.planner_id_at_expense=p.id AND e.is_deleted=0) AS expense_count,
                           (SELECT COALESCE(SUM(e.amount),0) FROM expenses e WHERE e.planner_id_at_expense=p.id AND e.is_deleted=0) AS total_amount,
                           (SELECT COUNT(*) FROM cars c2 WHERE c2.planner_id=p.id AND (c2.is_deleted=0 OR c2.is_deleted IS NULL)) AS car_count
                    FROM planners p
                    WHERE p.is_deleted=0
                    ORDER BY p.name
                """)
            else:
                return []
            return c.fetchall()
    finally:
        conn.close()


def get_entity_report(entity_type, entity_id, page=1, per_page=100):
    """Maşın/sürücü/köməkçi/planlamaçı/operator üçün detallı xərc info səhifəsi."""
    entity_id = int(entity_id)
    page = max(int(page or 1), 1)
    per_page = max(min(int(per_page or 100), 200), 20)
    offset = (page - 1) * per_page

    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            entity = None
            icon = 'fa-circle-info'
            title = 'Məlumat'
            subtitle = ''
            where = ''
            params = []

            if entity_type == 'car':
                c.execute("""SELECT c.*, d.name AS driver_name, a.name AS assistant_name, p.name AS planner_name
                             FROM cars c
                             LEFT JOIN drivers d ON c.driver_id=d.id
                             LEFT JOIN assistants a ON c.assistant_id=a.id
                             LEFT JOIN planners p ON c.planner_id=p.id
                             WHERE c.id=%s""", (entity_id,))
                entity = c.fetchone(); icon='fa-car-side'; title='Avtomobil məlumatı'; subtitle=(entity or {}).get('car_number','')
                where = 'e.car_id=%s'; params=[entity_id]
            elif entity_type == 'driver':
                c.execute("SELECT * FROM drivers WHERE id=%s", (entity_id,))
                entity = c.fetchone(); icon='fa-id-card'; title='Sürücü məlumatı'; subtitle=(entity or {}).get('name','')
                where = 'e.driver_id_at_expense=%s'; params=[entity_id]
            elif entity_type == 'assistant':
                c.execute("SELECT * FROM assistants WHERE id=%s", (entity_id,))
                entity = c.fetchone(); icon='fa-user-friends'; title='Köməkçi məlumatı'; subtitle=(entity or {}).get('name','')
                where = 'e.assistant_id_at_expense=%s'; params=[entity_id]
            elif entity_type == 'planner':
                c.execute("SELECT * FROM planners WHERE id=%s", (entity_id,))
                entity = c.fetchone(); icon='fa-user-tie'; title='Planlamaçı məlumatı'; subtitle=(entity or {}).get('name','')
                where = 'e.planner_id_at_expense=%s'; params=[entity_id]
            elif entity_type == 'operator':
                c.execute("SELECT * FROM users WHERE id=%s", (entity_id,))
                entity = c.fetchone(); icon='fa-user-gear'; title='Operator məlumatı'; subtitle=(entity or {}).get('fullname','')
                where = 'e.entered_by=%s'; params=[(entity or {}).get('username','')]
            else:
                return None

            if not entity:
                return None

            c.execute(f"""SELECT COUNT(*) AS c,
                                COALESCE(SUM(e.amount),0) AS total_amount,
                                COALESCE(SUM(e.litr),0) AS fuel_litr
                         FROM expenses e
                         WHERE e.is_deleted=0 AND {where}""", tuple(params))
            summary = c.fetchone() or {}
            total_count = int(summary.get('c') or 0)
            total_amount = float(summary.get('total_amount') or 0)
            fuel_litr = float(summary.get('fuel_litr') or 0)

            c.execute(f"""
                SELECT e.*, c.car_number, c.model,
                       d.name AS driver_name, a.name AS assistant_name, p.name AS planner_name,
                       u.fullname AS user_fullname
                FROM expenses e
                LEFT JOIN cars c ON e.car_id=c.id
                LEFT JOIN drivers d ON e.driver_id_at_expense=d.id
                LEFT JOIN assistants a ON e.assistant_id_at_expense=a.id
                LEFT JOIN planners p ON e.planner_id_at_expense=p.id
                LEFT JOIN users u ON e.entered_by = u.username COLLATE utf8mb4_unicode_ci
                WHERE e.is_deleted=0 AND {where}
                ORDER BY e.created_at DESC
                LIMIT %s OFFSET %s
            """, tuple(params + [per_page, offset]))
            rows = c.fetchall()

            expenses = []
            for r in rows:
                sub, clean = parse_expense_description(r.get('description',''))
                r['subtype'] = sub
                r['clean_description'] = clean
                r['timestamp_str'] = r['created_at'].strftime('%d.%m.%Y %H:%M') if r.get('created_at') else '-'
                expenses.append(r)

            total_pages = max((total_count + per_page - 1) // per_page, 1)
            return {
                'entity_type': entity_type,
                'entity': entity,
                'title': title,
                'subtitle': subtitle,
                'icon': icon,
                'expenses': expenses,
                'total_amount': total_amount,
                'expense_count': total_count,
                'fuel_litr': fuel_litr,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages,
                    'prev_page': max(page - 1, 1),
                    'next_page': min(page + 1, total_pages)
                }
            }
    finally:
        conn.close()

def calculate_experience(start_date_input):
    if not start_date_input: return "-"
    try:
        if isinstance(start_date_input, str):
            if not start_date_input.strip(): return "-"
            start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
        elif isinstance(start_date_input, (datetime, date)):
            start_date = start_date_input if isinstance(start_date_input, date) else start_date_input.date()
        else: return "-"
        today = datetime.now().date()
        delta = relativedelta(today, start_date)
        parts = []
        if delta.years > 0: parts.append(f"{delta.years} il")
        if delta.months > 0: parts.append(f"{delta.months} ay")
        return ", ".join(parts) if parts else ("Yeni" if delta.days >= 0 else "-")
    except: return "Xəta"

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)): return o.isoformat()
        return super().default(o)

# --- DECORATORS ---
def login_required(f):
    @wraps(f)
    def d(*a, **k):
        if 'user' not in session: return redirect(url_for('login'))
        return f(*a, **k)
    return d

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def d(*a, **k):
            if session.get('role') not in roles:
                flash('İcazə yoxdur.', 'danger'); return redirect(url_for('index'))
            return f(*a, **k)
        return d
    return decorator

def admin_required(f): return role_required(['admin'])(f)
def supervisor_required(f): return role_required(['supervisor'])(f)
def operator_required(f): return role_required(['user', 'admin', 'supervisor'])(f)

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = get_user_by_username(request.form['username'])
        if u and u['password'] == request.form['password']:
            if not u.get('is_active', True): flash('Hesab deaktivdir.', 'danger'); return render_template('login.html')
            session.update({'user': u['username'], 'role': u['role'], 'fullname': u['fullname']})
            log_action('LOGIN', f"Giriş: {u['username']}")
            return redirect(url_for('supervisor_dashboard' if u['role']=='supervisor' else 'index'))
        return render_template('login.html', error='Yanlış məlumat.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    log_action('LOGOUT', f"Çıxış: {session.get('user')}"); session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if session['role'] == 'supervisor': return redirect(url_for('supervisor_dashboard'))
    if session['role'] == 'admin':
        conn = get_connection_safe()
        try:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) as c FROM users WHERE role='user'"); op_c = c.fetchone()['c']
                c.execute("SELECT COUNT(*) as c FROM cars WHERE is_deleted=0"); car_c = c.fetchone()['c']
                c.execute("SELECT COUNT(*) as c FROM drivers WHERE is_deleted=0"); dr_c = c.fetchone()['c']
                c.execute("SELECT COUNT(*) as c FROM assistants WHERE is_deleted=0"); as_c = c.fetchone()['c']
                c.execute("SELECT COUNT(*) as c FROM planners WHERE is_deleted=0"); pl_c = c.fetchone()['c']

                now = datetime.now()
                c.execute("SELECT SUM(amount) as total FROM expenses WHERE is_deleted=0 AND MONTH(created_at)=%s AND YEAR(created_at)=%s", (now.month, now.year))
                res = c.fetchone()
                mt = float(res['total'] or 0)

                prev = now - relativedelta(months=1)
                c.execute("SELECT SUM(amount) as total FROM expenses WHERE is_deleted=0 AND MONTH(created_at)=%s AND YEAR(created_at)=%s", (prev.month, prev.year))
                prev_total = float((c.fetchone() or {}).get('total') or 0)

                months = []
                for i in range(11, -1, -1):
                    d = now - relativedelta(months=i)
                    months.append({
                        'year': d.year,
                        'month': d.month,
                        'key': f"{d.year}-{d.month:02d}",
                        'label': d.strftime('%b %Y')
                    })

                c.execute("""
                    SELECT YEAR(created_at) AS y, MONTH(created_at) AS m, SUM(amount) AS total
                    FROM expenses
                    WHERE is_deleted=0 AND created_at >= %s
                    GROUP BY YEAR(created_at), MONTH(created_at)
                    ORDER BY y, m
                """, ((now - relativedelta(months=11)).strftime('%Y-%m-01 00:00:00'),))
                raw_months = c.fetchall()
                month_map = {f"{int(r['y'])}-{int(r['m']):02d}": float(r['total'] or 0) for r in raw_months}
                trend_labels = [m['label'] for m in months]
                trend_data = [month_map.get(m['key'], 0) for m in months]

                c.execute("SELECT type, SUM(amount) as total FROM expenses WHERE is_deleted=0 AND MONTH(created_at)=%s AND YEAR(created_at)=%s GROUP BY type", (now.month, now.year))
                rows = c.fetchall()
        finally:
            conn.close()

        delta = mt - prev_total
        delta_percent = ((delta / prev_total) * 100) if prev_total else (100 if mt else 0)
        return render_template(
            'admin_dashboard.html',
            stats={
                'operator_count': op_c,
                'car_count': car_c,
                'driver_count': dr_c,
                'assistant_count': as_c,
                'planner_count': pl_c,
                'monthly_total': mt,
                'previous_month_total': prev_total,
                'monthly_delta': delta,
                'monthly_delta_percent': delta_percent
            },
            chart_data={'labels': [r['type'] for r in rows], 'data': [float(r['total']) for r in rows]},
            monthly_trend={'labels': trend_labels, 'data': trend_data}
        )

    now = datetime.now()
    return render_template(
        'operator_dashboard.html',
        cars=get_dashboard_data(),
        drivers=get_all_drivers(True),
        assistants=get_all_assistants(True),
        planners=get_all_planners(True),
        fine_types=get_expense_subtypes().get('Cərimə', FINE_TYPES),
        repair_types=get_expense_subtypes().get('Təmir', REPAIR_TYPES),
        expense_types=get_expense_types(),
        expense_subtypes=get_expense_subtypes(),
        allow_past_expense_date=is_past_expense_allowed(),
        default_expense_datetime=now.strftime('%Y-%m-%dT%H:%M'),
        today_start_datetime=now.strftime('%Y-%m-%dT00:00'),
        today_display=now.strftime('%d.%m.%Y')
    )

@app.route('/add_expense', methods=['POST'])
@operator_required
def add_expense():
    try:
        desc = request.form.get('description', '')
        et = request.form.get('expense_type')
        expense_dt = parse_expense_datetime(request.form.get('expense_date'))
        now = datetime.now()

        if expense_dt > now + timedelta(minutes=2):
            flash('Gələcək tarixə xərc yazmaq olmaz.', 'danger')
            return redirect(url_for('index'))

        if session.get('role') == 'user' and expense_dt.date() < now.date() and not is_past_expense_allowed():
            flash('Keçmiş tarixə xərc yazmaq üçün admin icazəsi bağlıdır.', 'danger')
            return redirect(url_for('index'))

        sub = request.form.get('expense_subtype') or (request.form.get('fuel_subtype') if et=='Yanacaq' else (request.form.get('fine_subtype') if et=='Cərimə' else (request.form.get('repair_subtype') if et=='Təmir' else '')))
        if sub: desc = f"[{sub}] {desc}"
        car = get_car_by_id(request.form.get('car_id'))
        if car:
            insert_expense(car['id'], et, request.form.get('amount'), request.form.get('litr') or 0, desc, car['driver_id'], car['assistant_id'], car['planner_id'], session['user'], expense_dt)
            log_action('ADD_EXPENSE', f"{car['car_number']} - {request.form.get('amount')} AZN - Xərc tarixi: {expense_dt.strftime('%d.%m.%Y %H:%M')}")
            flash('Xərc əlavə edildi.', 'success')
    except Exception as e: flash(f'Xəta: {e}', 'danger')
    return redirect(url_for('index'))

@app.route('/update_car_meta', methods=['POST'])
@operator_required
def update_car_meta():
    def val(f): v = request.form.get(f); return int(v) if v else None
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE cars SET brand=%s, model_name=%s, category=%s, driver_id=%s, assistant_id=%s, planner_id=%s, notes=%s WHERE id=%s",
                      (request.form.get('brand'), request.form.get('model_name'), request.form.get('category'), val('driver_id'), val('assistant_id'), val('planner_id'), request.form.get('notes'), request.form.get('car_id')))
        conn.commit(); log_action('UPDATE_CAR', f"Car {request.form.get('car_id')} updated"); flash('Yeniləndi', 'success')
    finally: conn.close()
    return redirect(url_for('index'))
@app.route('/pivot_reports')
def pivot_reports():
    if 'user' not in session or session.get('role') not in ['admin', 'supervisor']:
        return redirect(url_for('login'))
    
    sd = request.args.get('start_date')
    ed = request.args.get('end_date')
    
    # Bazadan məlumatları çəkmək üçün SQL sorğusu
    sql = """SELECT e.*, e.created_at as timestamp, e.id as expense_id, c.car_number, c.model, u.fullname as user_fullname,
             d.name as driver_name_at_expense, a.name as assistant_name_at_expense, p.name as planner_name_at_expense
             FROM expenses e
             LEFT JOIN cars c ON e.car_id = c.id
             LEFT JOIN users u ON e.entered_by = u.username COLLATE utf8mb4_unicode_ci
             LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
             LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
             LEFT JOIN planners p ON e.planner_id_at_expense = p.id
             WHERE e.is_deleted = 0"""
    p = []
    
    if sd: 
        sql += " AND DATE(e.created_at) >= %s"
        p.append(sd)
    if ed: 
        sql += " AND DATE(e.created_at) <= %s"
        p.append(ed)
        
    sql += " ORDER BY e.created_at DESC"

    conn = get_connection_safe()
    fmt_reports = []
    try:
        with conn.cursor() as c:
            c.execute(sql, tuple(p))
            reports = c.fetchall()
            
            for r in reports:
                if not r.get('created_at'):
                    r['timestamp'] = datetime.now()
                else:
                    r['timestamp'] = r['created_at']
                
                sub, clean = parse_expense_description(r.get('description', ''))
                
                item = {
                    'expense': r,
                    'car': {'car_number': r['car_number'], 'model': r['model']} if r.get('car_number') else None,
                    'user': {'fullname': r['user_fullname']},
                    'username': r['user_fullname'] or r['entered_by'],
                    'driver_name_at_expense': r['driver_name_at_expense'] or "-",
                    'assistant_name_at_expense': r['assistant_name_at_expense'] or "-",
                    'planner_name_at_expense': r['planner_name_at_expense'] or "-",
                    'timestamp': r['timestamp'],
                    'subtype': sub,
                    'clean_description': clean
                }
                fmt_reports.append(item)
    finally: 
        conn.close()
        
    return render_template('pivot_reports.html', reports=fmt_reports)
# --- ADMIN REPORTS ---
@app.route('/admin/reports')
def admin_reports():
    if session.get('role') not in ['admin', 'supervisor']: return redirect(url_for('index'))
    
    try:
        f_car = request.args.get('car_id'); f_dr = request.args.get('driver_id'); f_as = request.args.get('assistant_id'); f_pl = request.args.get('planner_id'); f_op = request.args.get('operator_id'); f_t = request.args.get('expense_type'); f_sub = request.args.get('subtype_filter')
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        ten_days_ago_str = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        sd = request.args.get('start_date')
        ed = request.args.get('end_date')
        
        if not sd and not ed:
            sd = ten_days_ago_str
        
        sql = """SELECT e.*, e.created_at as timestamp, e.id as expense_id, c.car_number, c.model, u.fullname as user_fullname,
                 d.name as driver_name_at_expense, a.name as assistant_name_at_expense, p.name as planner_name_at_expense
                 FROM expenses e
                 LEFT JOIN cars c ON e.car_id = c.id
                 LEFT JOIN users u ON e.entered_by = u.username COLLATE utf8mb4_unicode_ci
                 LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
                 LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
                 LEFT JOIN planners p ON e.planner_id_at_expense = p.id
                 WHERE e.is_deleted = 0"""
        p = []
        if f_car: sql += " AND e.car_id=%s"; p.append(f_car)
        if f_dr: sql += " AND e.driver_id_at_expense=%s"; p.append(f_dr)
        if f_as: sql += " AND e.assistant_id_at_expense=%s"; p.append(f_as)
        if f_pl: sql += " AND e.planner_id_at_expense=%s"; p.append(f_pl)
        if f_op:
            sql += " AND e.entered_by=(SELECT username FROM users WHERE id=%s)"; p.append(f_op)
        if f_t: sql += " AND e.type=%s"; p.append(f_t)
        if f_sub: sql += " AND e.description LIKE %s"; p.append(f"%[{f_sub}]%")
        
        if sd: 
            sql += " AND DATE(e.created_at) >= %s"
            p.append(sd)
        if ed: 
            sql += " AND DATE(e.created_at) <= %s"
            p.append(ed)
            
        sql += " ORDER BY e.created_at DESC"

        conn = get_connection_safe()
        try:
            with conn.cursor() as c:
                c.execute(sql, tuple(p))
                reports = c.fetchall()
                
                fmt_reports = []
                for r in reports:
                    if not r.get('created_at'):
                        r['timestamp'] = datetime.now()
                    else:
                        r['timestamp'] = r['created_at']
                    
                    sub, clean = parse_expense_description(r.get('description', ''))
                    
                    item = {
                        'expense': r,
                        'car': {'car_number': r['car_number'], 'model': r['model']} if r.get('car_number') else None,
                        'user': {'fullname': r['user_fullname']},
                        'driver_name_at_expense': r['driver_name_at_expense'] or "-",
                        'assistant_name_at_expense': r['assistant_name_at_expense'] or "-",
                        'planner_name_at_expense': r['planner_name_at_expense'] or "-",
                        'timestamp': r['timestamp'],
                        'subtype': sub,
                        'clean_description': clean
                    }
                    fmt_reports.append(item)
                
                total = sum(float(x['expense']['amount'] or 0) for x in fmt_reports)
                
                c.execute("SELECT * FROM cars ORDER BY car_number"); cars = c.fetchall()
                c.execute("SELECT * FROM drivers WHERE is_deleted=0 ORDER BY name"); drivers = c.fetchall()
                c.execute("SELECT * FROM assistants WHERE is_deleted=0 ORDER BY name"); assts = c.fetchall()
                c.execute("SELECT * FROM planners WHERE is_deleted=0 ORDER BY name"); plans = c.fetchall()
                c.execute("SELECT * FROM users WHERE role='user'"); ops = c.fetchall()
                
        finally: conn.close()
        
        current_filters = request.args.copy()
        if not request.args.get('start_date'): current_filters['start_date'] = sd
        
        return render_template('admin_reports.html', reports=fmt_reports, total_amount=total, cars=cars, drivers=drivers, assistants=assts, planners=plans, operators=ops, expense_types=get_expense_types(), fine_types=get_expense_subtypes().get('Cərimə', FINE_TYPES), repair_types=get_expense_subtypes().get('Təmir', REPAIR_TYPES), expense_subtypes=get_expense_subtypes(), all_subtypes=get_all_subtype_values(), selected_filters=current_filters)
    except Exception:
        return f"<h1>SİSTEM XƏTASI (DEBUG)</h1><pre>{traceback.format_exc()}</pre>"
@app.route('/admin/reports/export')
def admin_reports_export():
    if session.get('role') not in ['admin', 'supervisor']: return redirect(url_for('index'))
    
    # Filtrləri alırıq (Axtarışda nə seçilibsə, onu Excel-ə çəkəcək)
    f_car = request.args.get('car_id'); f_dr = request.args.get('driver_id'); f_as = request.args.get('assistant_id'); f_pl = request.args.get('planner_id'); f_op = request.args.get('operator_id'); f_t = request.args.get('expense_type'); f_sub = request.args.get('subtype_filter')
    sd = request.args.get('start_date')
    ed = request.args.get('end_date')
    
    sql = """SELECT e.*, e.created_at as timestamp, c.car_number, c.model, u.fullname as user_fullname,
             d.name as driver_name_at_expense, a.name as assistant_name_at_expense, p.name as planner_name_at_expense
             FROM expenses e
             LEFT JOIN cars c ON e.car_id = c.id
             LEFT JOIN users u ON e.entered_by = u.username COLLATE utf8mb4_unicode_ci
             LEFT JOIN drivers d ON e.driver_id_at_expense = d.id
             LEFT JOIN assistants a ON e.assistant_id_at_expense = a.id
             LEFT JOIN planners p ON e.planner_id_at_expense = p.id
             WHERE e.is_deleted = 0"""
    p = []
    
    if f_car: sql += " AND e.car_id=%s"; p.append(f_car)
    if f_dr: sql += " AND e.driver_id_at_expense=%s"; p.append(f_dr)
    if f_as: sql += " AND e.assistant_id_at_expense=%s"; p.append(f_as)
    if f_pl: sql += " AND e.planner_id_at_expense=%s"; p.append(f_pl)
    if f_op:
        sql += " AND e.entered_by=(SELECT username FROM users WHERE id=%s)"; p.append(f_op)
    if f_t: sql += " AND e.type=%s"; p.append(f_t)
    if f_sub: sql += " AND e.description LIKE %s"; p.append(f"%[{f_sub}]%")
    if sd: sql += " AND DATE(e.created_at) >= %s"; p.append(sd)
    if ed: sql += " AND DATE(e.created_at) <= %s"; p.append(ed)
        
    sql += " ORDER BY e.created_at DESC"

    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute(sql, tuple(p))
            reports = c.fetchall()
    finally: conn.close()

    # Excel (CSV) faylını yaratmaq üçün lazımi modullar
    import csv
    import io
    from flask import make_response

    si = io.StringIO()
    # Excel-də Azərbaycan şriftlərinin düzgün görünməsi üçün UTF-8 BOM əlavə edirik
    si.write('\ufeff')
    # Sütunları ayırmaq üçün nöqtəli-vergül (Excel üçün standartdır)
    cw = csv.writer(si, delimiter=';')
    
    # Başlıq sətiri
    cw.writerow(['Tarix / Saat', 'Maşın', 'Sürücü', 'Köməkçi', 'Planlamaçı', 'Xərc Növü', 'Alt Növ', 'Məbləğ (AZN)', 'Litr', 'Açıqlama', 'Operator'])
    
    # Məlumatların fayla yazılması
    for r in reports:
        t_stamp = r['timestamp'].strftime('%d.%m.%Y %H:%M') if r.get('timestamp') else datetime.now().strftime('%d.%m.%Y %H:%M')
        car_info = r['car_number'] if r.get('car_number') else 'Bilinmir'
        sub, clean = parse_expense_description(r.get('description', ''))
        
        cw.writerow([
            t_stamp,
            car_info,
            r['driver_name_at_expense'] or "-",
            r['assistant_name_at_expense'] or "-",
            r['planner_name_at_expense'] or "-",
            r['type'] or "-",
            sub,
            r['amount'] or "0",
            r['litr'] or "-",
            clean,
            r['user_fullname'] or r['entered_by'] or "-"
        ])
        
    output = make_response(si.getvalue())
    filename = f"Xerc_Hesabatlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return output
@app.route('/admin/expense/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    if session.get('role') not in ['admin', 'supervisor']: return redirect(url_for('index'))
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE expenses SET is_deleted=1, deleted_by_user=%s, deleted_at=NOW() WHERE id=%s", (session['fullname'], id))
        conn.commit(); log_action('DELETE_EXPENSE', f"ID {id}"); flash('Silindi', 'success')
    finally: conn.close()
    return redirect(url_for('admin_reports'))

# --- DELETED REPORTS (FIXED) ---
@app.route('/admin/deleted_reports')
@admin_required
def admin_deleted_reports():
    page = request.args.get('page', 1, type=int) or 1
    per_page = 100
    offset = (max(page, 1) - 1) * per_page

    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS c FROM expenses WHERE is_deleted=1")
            total = int((c.fetchone() or {}).get('c') or 0)

            c.execute("""SELECT e.*, e.id as expense_id, e.created_at as timestamp, c.car_number, c.model, u.fullname as user_fullname, 
                         d.name as driver_name_at_expense, a.name as assistant_name_at_expense, p.name as planner_name_at_expense
                         FROM expenses e 
                         LEFT JOIN cars c ON e.car_id=c.id 
                         LEFT JOIN users u ON e.entered_by=u.username COLLATE utf8mb4_unicode_ci
                         LEFT JOIN drivers d ON e.driver_id_at_expense=d.id 
                         LEFT JOIN assistants a ON e.assistant_id_at_expense=a.id 
                         LEFT JOIN planners p ON e.planner_id_at_expense=p.id
                         WHERE e.is_deleted=1 ORDER BY e.deleted_at DESC
                         LIMIT %s OFFSET %s""", (per_page, offset))
            rows = c.fetchall()
            rep = []
            for r in rows:
                if not r.get('created_at'):
                    r['timestamp'] = datetime.now()
                else:
                    r['timestamp'] = r['created_at']

                sub, clean = parse_expense_description(r.get('description', ''))

                item = {
                    'expense': r, 
                    'car': {'car_number': r['car_number'], 'model': r.get('model')} if r.get('car_number') else None, 
                    'user': {'fullname': r['user_fullname']}, 
                    'driver_name_at_expense': r['driver_name_at_expense'] or "-", 
                    'assistant_name_at_expense': r['assistant_name_at_expense'] or "-", 
                    'planner_name_at_expense': r['planner_name_at_expense'] or "-",
                    'timestamp': r['timestamp'],
                    'subtype': sub,
                    'clean_description': clean
                }
                rep.append(item)
    finally:
        conn.close()

    total_pages = max((total + per_page - 1) // per_page, 1)
    pagination = {
        'page': max(page, 1),
        'per_page': per_page,
        'total': total,
        'pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': max(page - 1, 1),
        'next_page': min(page + 1, total_pages)
    }
    return render_template('admin_deleted_reports.html', reports=rep, pagination=pagination)

@app.route('/admin/expense/restore/<int:id>', methods=['POST'])
@admin_required
def restore_expense(id):
    conn = get_connection_safe()
    try:
        with conn.cursor() as c: c.execute("UPDATE expenses SET is_deleted=0 WHERE id=%s", (id,)); conn.commit()
        flash('Bərpa edildi', 'success')
    finally: conn.close()
    return redirect(url_for('admin_deleted_reports'))

# --- SUPERVISOR SECTION ---
@app.route('/supervisor/dashboard')
@supervisor_required
def supervisor_dashboard():
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as c FROM users"); u_c = c.fetchone()['c']
            c.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1"); a_c = c.fetchone()['c']
            c.execute("SELECT COUNT(*) as c FROM users WHERE is_active=0"); p_c = c.fetchone()['c']
            c.execute("SELECT COUNT(*) as c FROM audit_logs"); l_c = c.fetchone()['c']
            c.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role"); rd = c.fetchall()
            labels = [r['role'] for r in rd]; data = [r['count'] for r in rd]
    finally: conn.close()
    return render_template('supervisor_dashboard.html', stats={'total_users': u_c, 'active_users': a_c, 'passive_users': p_c, 'total_logs': l_c}, chart_data={'labels': labels, 'data': data})

@app.route('/supervisor/reports')
@supervisor_required
def supervisor_reports():
    u = request.args.get('username')
    a = request.args.get('action')
    h = request.args.get('hostname')
    sd = request.args.get('start_date')
    page = request.args.get('page', 1, type=int) or 1
    per_page = 100
    offset = (max(page, 1) - 1) * per_page

    sql = " FROM audit_logs WHERE 1=1"
    p = []
    if u:
        sql += " AND username=%s"; p.append(u)
    if a:
        sql += " AND action=%s"; p.append(a)
    if h:
        sql += " AND hostname=%s"; p.append(h)
    if sd:
        sql += " AND DATE(timestamp)>=%s"; p.append(sd)

    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS c" + sql, tuple(p))
            total = int((c.fetchone() or {}).get('c') or 0)

            c.execute("SELECT *" + sql + " ORDER BY timestamp DESC LIMIT %s OFFSET %s", tuple(p + [per_page, offset]))
            r = c.fetchall()

            c.execute("SELECT DISTINCT username FROM audit_logs ORDER BY username"); au = [x['username'] for x in c.fetchall()]
            c.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action"); aa = [x['action'] for x in c.fetchall()]
            c.execute("SELECT DISTINCT hostname FROM audit_logs ORDER BY hostname"); ah = [x['hostname'] for x in c.fetchall()]
    finally:
        conn.close()

    total_pages = max((total + per_page - 1) // per_page, 1)
    pagination = {
        'page': max(page, 1),
        'per_page': per_page,
        'total': total,
        'pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': max(page - 1, 1),
        'next_page': min(page + 1, total_pages)
    }
    return render_template('supervisor_reports.html', reports=r, all_usernames=au, all_actions=aa, all_hostnames=ah, selected_filters=request.args, pagination=pagination)

@app.route('/supervisor/data')
@supervisor_required
def supervisor_data(): return render_template('supervisor_data.html')

@app.route('/supervisor/export')
@supervisor_required
def export_db():
    tabs = ['users', 'cars', 'drivers', 'assistants', 'planners', 'expenses', 'expense_types', 'audit_logs', 'app_settings']
    d = {}
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            for t in tabs: c.execute(f"SELECT * FROM {t}"); d[t] = c.fetchall()
    finally: conn.close()
    mem = io.BytesIO(); mem.write(json.dumps(d, cls=DateTimeEncoder, default=str).encode('utf-8')); mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=f"backup_{datetime.now().strftime('%Y%m%d')}.json", mimetype='application/json')

@app.route('/supervisor/import', methods=['POST'])
@supervisor_required
def import_db():
    f = request.files.get('backup_file')
    if not f: flash('Fayl yoxdur', 'danger'); return redirect(url_for('supervisor_data'))
    try:
        d = json.load(f); conn = get_connection_safe()
        try:
            with conn.cursor() as c:
                c.execute("SET FOREIGN_KEY_CHECKS=0")
                for t in ['users', 'cars', 'drivers', 'assistants', 'planners', 'expenses', 'expense_types', 'audit_logs', 'app_settings']:
                    if t in d and d[t]:
                        c.execute(f"TRUNCATE TABLE {t}")
                        for row in d[t]:
                            cols = ', '.join(row.keys()); ph = ', '.join(['%s']*len(row))
                            c.execute(f"INSERT INTO {t} ({cols}) VALUES ({ph})", list(row.values()))
                c.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit(); flash('Bərpa olundu', 'success')
        finally: conn.close()
    except Exception as e: flash(f"Xəta: {e}", 'danger')
    return redirect(url_for('supervisor_data'))

@app.route('/supervisor/operations')
@supervisor_required
def supervisor_operations(): return render_template('supervisor_operations.html', users=get_all_users())

# --- SUPERVISOR ADD/DELETE USER FIX ---
@app.route('/supervisor/operations/add_user', methods=['POST'])
@supervisor_required
def supervisor_add_user():
    conn = get_connection_safe()
    try:
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        with conn.cursor() as c:
            c.execute("INSERT INTO users (fullname, username, password, role, is_active) VALUES (%s, %s, %s, %s, 1)", 
                      (fullname, username, password, role))
        conn.commit()
        log_action('ADD_USER_SUPERVISOR', f"Supervisor added user: {username} ({role})")
        flash('Yeni istifadəçi uğurla əlavə edildi.', 'success')
    except Exception as e:
        flash(f'Xəta: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('supervisor_operations'))

@app.route('/supervisor/user/edit/<int:id>', methods=['GET', 'POST'])
@supervisor_required
def supervisor_edit_user(id):
    if request.method == 'POST':
        act = 1 if request.form.get('is_active')=='on' else 0
        conn = get_connection_safe()
        with conn.cursor() as c:
            sql = "UPDATE users SET fullname=%s, username=%s, role=%s, is_active=%s"
            p = [request.form['fullname'], request.form['username'], request.form['role'], act]
            if request.form['password']: sql+=", password=%s"; p.append(request.form['password'])
            c.execute(sql+" WHERE id=%s", tuple(p + [id]))
        conn.commit(); conn.close(); return redirect(url_for('supervisor_operations'))
    return render_template('supervisor_edit_user.html', user=get_user_by_id(id))

@app.route('/supervisor/user/delete/<int:id>', methods=['POST'])
@supervisor_required
def supervisor_delete_user(id):
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM users WHERE id=%s", (id,))
        conn.commit()
        log_action('DELETE_USER_SUPERVISOR', f"Supervisor deleted user ID: {id}")
        flash('İstifadəçi silindi.', 'success')
    except Exception as e:
        flash(f'Xəta: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('supervisor_operations'))

# --- STANDARD CRUD ---
@app.route('/admin/drivers')
@operator_required
def admin_drivers():
    drs = get_management_counts('drivers', 'id')
    for d in drs:
        d['experience_str'] = calculate_experience(d.get('start_date'))
    return render_template('admin_drivers.html', drivers=drs)

@app.route('/admin/drivers/add', methods=['POST'])
@operator_required
def add_driver():
    conn = get_connection_safe()
    try:
        # Formadan gələn məlumatları təhlükəsiz şəkildə alırıq
        name = request.form.get('name', '').strip()
        license_no = request.form.get('license_no', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        start_date = request.form.get('start_date', '').strip() or None
        
        with conn.cursor() as c: 
            c.execute("INSERT INTO drivers (name, license_no, phone, start_date, is_active, is_deleted) VALUES (%s, %s, %s, %s, 1, 0)", 
                      (name, license_no, phone, start_date))
        conn.commit()
        flash('Sürücü uğurla əlavə edildi.', 'success')
        
    except Exception as e:
        # Hər hansı MySQL və ya kod xətası baş verərsə 500 error əvəzinə ekrana səbəbini yazacaq
        flash(f'Sürücü əlavə edilərkən xəta baş verdi: {e}', 'danger')
    finally: 
        conn.close()
        
    return redirect(url_for('admin_drivers'))

@app.route('/admin/driver/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_driver(id):
    if request.method == 'POST':
        conn = get_connection_safe()
        try:
            name = request.form.get('name', '').strip()
            license_no = request.form.get('license_no', '').strip() or None
            phone = request.form.get('phone', '').strip() or None
            start_date = request.form.get('start_date', '').strip() or None
            
            with conn.cursor() as c: 
                c.execute("UPDATE drivers SET name=%s, license_no=%s, phone=%s, start_date=%s WHERE id=%s", 
                          (name, license_no, phone, start_date, id))
            conn.commit()
            flash('Sürücü məlumatları yeniləndi.', 'success')
        except Exception as e:
            flash(f'Xəta baş verdi: {e}', 'danger')
        finally:
            conn.close()
            
        return redirect(url_for('admin_drivers'))
        
    return render_template('edit_driver.html', driver=get_driver_by_id(id))

@app.route('/admin/driver/toggle_status/<int:id>', methods=['POST'])
@operator_required
def toggle_driver_status(id):
    conn = get_connection_safe(); 
    with conn.cursor() as c: c.execute("UPDATE drivers SET is_active = NOT is_active WHERE id=%s", (id,)); conn.commit()
    conn.close(); return redirect(url_for('admin_drivers'))

@app.route('/admin/driver/delete/<int:id>', methods=['POST'])
@operator_required
def delete_driver(id):
    conn = get_connection_safe(); 
    with conn.cursor() as c: 
        c.execute("UPDATE cars SET driver_id=NULL WHERE driver_id=%s", (id,))
        c.execute("UPDATE drivers SET is_deleted=1, name=CONCAT(name, ' (silinmiş)') WHERE id=%s", (id,))
        conn.commit()
    conn.close(); flash('Silindi', 'success'); return redirect(url_for('admin_drivers'))

@app.route('/admin/drivers/bulk_add', methods=['POST'])
@operator_required
def bulk_add_driver():
    bd = request.form.get('bulk_data', '')
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT license_no FROM drivers"); ex = {r['license_no'] for r in c.fetchall() if r['license_no']}
            for l in bd.splitlines():
                p = l.split(';')
                if not p[0].strip(): continue
                nm = p[0].strip(); lic = p[1].strip() if len(p)>1 else None
                ph = p[2].strip() if len(p)>2 else None
                sd = p[3].strip() if len(p)>3 else None
                if lic and lic in ex: continue
                c.execute("INSERT INTO drivers (name, license_no, phone, start_date, is_active, is_deleted) VALUES (%s, %s, %s, %s, 1, 0)", (nm, lic, ph, sd or None))
                if lic: ex.add(lic)
        conn.commit()
    finally: conn.close()
    return redirect(url_for('admin_drivers'))

@app.route('/admin/cars')
@operator_required
def admin_cars(): return render_template('admin_cars.html', cars=get_management_counts('cars', 'id'), drivers=get_all_drivers(True), assistants=get_all_assistants(True), planners=get_all_planners(True))

@app.route('/admin/cars/add', methods=['POST'])
@operator_required
def add_car():
    conn = get_connection_safe()
    try:
        def v(f): x = request.form.get(f); return int(x) if x else None
        with conn.cursor() as c: c.execute("INSERT INTO cars (car_number, model, driver_id, assistant_id, planner_id, is_active, is_deleted) VALUES (%s, %s, %s, %s, %s, 1, 0)", (request.form['car_number'], request.form['model'], v('driver_id'), v('assistant_id'), v('planner_id'))); conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('admin_cars'))

@app.route('/admin/car/toggle_status/<int:id>', methods=['POST'])
@operator_required
def toggle_car_status(id):
    conn = get_connection_safe(); 
    with conn.cursor() as c: c.execute("UPDATE cars SET is_active = NOT is_active WHERE id=%s", (id,)); conn.commit()
    conn.close(); return redirect(url_for('admin_cars'))

@app.route('/admin/car/edit/<int:id>', methods=['GET', 'POST'])
@operator_required
def edit_car(id):
    if request.method == 'POST':
        def v(f): x = request.form.get(f); return int(x) if x else None
        conn = get_connection_safe()
        with conn.cursor() as c: c.execute("UPDATE cars SET car_number=%s, model=%s, driver_id=%s, assistant_id=%s, planner_id=%s WHERE id=%s", (request.form['car_number'], request.form['model'], v('driver_id'), v('assistant_id'), v('planner_id'), id)); conn.commit()
        return redirect(url_for('admin_cars'))
    return render_template('edit_car.html', car=get_car_by_id(id), drivers=get_all_drivers(True), assistants=get_all_assistants(True), planners=get_all_planners(True))

@app.route('/admin/car/delete/<int:id>', methods=['POST'])
@operator_required
def delete_car(id):
    conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS c FROM expenses WHERE car_id=%s AND is_deleted=0", (id,))
            if c.fetchone()['c'] > 0:
                flash('Bu avtomobilə xərc yazıldığı üçün silmək olmaz. Əvvəlcə info bölməsindən tarixçəyə baxın.', 'warning')
                return redirect(url_for('admin_cars'))
            c.execute("UPDATE cars SET is_deleted=1 WHERE id=%s", (id,))
            conn.commit()
            flash('Avtomobil silindi.', 'success')
    finally:
        conn.close()
    return redirect(url_for('admin_cars'))

@app.route('/admin/cars/bulk_add', methods=['POST'])
@operator_required
def bulk_add_car():
    bd = request.form.get('bulk_data', ''); conn = get_connection_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT car_number FROM cars"); ex = {r['car_number'] for r in c.fetchall()}
            for l in bd.splitlines():
                p = l.split(';')
                if len(p)>=2:
                    cn, md = p[0].strip(), p[1].strip()
                    if cn and cn not in ex: c.execute("INSERT INTO cars (car_number, model, is_active, is_deleted) VALUES (%s, %s, 1, 0)", (cn, md)); ex.add(cn)
        conn.commit()
    finally: conn.close()
    return redirect(url_for('admin_cars'))

@app.route('/admin/assistants')
@operator_required
def admin_assistants(): return render_template('admin_assistants.html', assistants=get_management_counts('assistants', 'id'))
@app.route('/admin/assistants/add', methods=['POST'])
@operator_required
def add_assistant(): conn=get_connection_safe(); conn.cursor().execute("INSERT INTO assistants (name, is_active, is_deleted) VALUES (%s, 1, 0)", (request.form['name'],)); conn.commit(); conn.close(); return redirect(url_for('admin_assistants'))
@app.route('/admin/assistant/toggle_status/<int:id>', methods=['POST'])
@operator_required
def toggle_assistant_status(id): conn=get_connection_safe(); conn.cursor().execute("UPDATE assistants SET is_active = NOT is_active WHERE id=%s", (id,)); conn.commit(); conn.close(); return redirect(url_for('admin_assistants'))
@app.route('/admin/assistant/edit/<int:aid>', methods=['GET', 'POST'])
@operator_required
def edit_assistant(aid): 
    if request.method=='POST': conn=get_connection_safe(); conn.cursor().execute("UPDATE assistants SET name=%s WHERE id=%s", (request.form['name'], aid)); conn.commit(); conn.close(); return redirect(url_for('admin_assistants'))
    return render_template('edit_assistant.html', assistant=get_assistant_by_id(aid))
@app.route('/admin/assistant/delete/<int:aid>', methods=['POST'])
@operator_required
def delete_assistant(aid): conn=get_connection_safe(); c=conn.cursor(); c.execute("UPDATE cars SET assistant_id=NULL WHERE assistant_id=%s", (aid,)); c.execute("UPDATE assistants SET is_deleted=1, name=CONCAT(name, ' (silinmiş)') WHERE id=%s", (aid,)); conn.commit(); conn.close(); return redirect(url_for('admin_assistants'))
@app.route('/admin/assistants/bulk_add', methods=['POST'])
@operator_required
def bulk_add_assistant(): 
    conn=get_connection_safe(); c=conn.cursor()
    for l in request.form.get('bulk_data','').splitlines(): c.execute("INSERT INTO assistants (name, is_active, is_deleted) VALUES (%s, 1, 0)", (l.strip(),))
    conn.commit(); conn.close(); return redirect(url_for('admin_assistants'))

@app.route('/admin/planners')
@operator_required
def admin_planners(): return render_template('admin_planners.html', planners=get_management_counts('planners', 'id'))
@app.route('/admin/planners/add', methods=['POST'])
@operator_required
def add_planner(): conn=get_connection_safe(); conn.cursor().execute("INSERT INTO planners (name, is_active, is_deleted) VALUES (%s, 1, 0)", (request.form['name'],)); conn.commit(); conn.close(); return redirect(url_for('admin_planners'))
@app.route('/admin/planner/toggle_status/<int:id>', methods=['POST'])
@operator_required
def toggle_planner_status(id): conn=get_connection_safe(); conn.cursor().execute("UPDATE planners SET is_active = NOT is_active WHERE id=%s", (id,)); conn.commit(); conn.close(); return redirect(url_for('admin_planners'))
@app.route('/admin/planner/edit/<int:pid>', methods=['GET', 'POST'])
@operator_required
def edit_planner(pid):
    if request.method=='POST': conn=get_connection_safe(); conn.cursor().execute("UPDATE planners SET name=%s WHERE id=%s", (request.form['name'], pid)); conn.commit(); conn.close(); return redirect(url_for('admin_planners'))
    return render_template('edit_planner.html', planner=get_planner_by_id(pid))
@app.route('/admin/planner/delete/<int:pid>', methods=['POST'])
@operator_required
def delete_planner(pid): conn=get_connection_safe(); c=conn.cursor(); c.execute("UPDATE cars SET planner_id=NULL WHERE planner_id=%s", (pid,)); c.execute("UPDATE planners SET is_deleted=1, name=CONCAT(name, ' (silinmiş)') WHERE id=%s", (pid,)); conn.commit(); conn.close(); return redirect(url_for('admin_planners'))
@app.route('/admin/planners/bulk_add', methods=['POST'])
@operator_required
def bulk_add_planner(): 
    conn=get_connection_safe(); c=conn.cursor()
    for l in request.form.get('bulk_data','').splitlines(): c.execute("INSERT INTO planners (name, is_active, is_deleted) VALUES (%s, 1, 0)", (l.strip(),))
    conn.commit(); conn.close(); return redirect(url_for('admin_planners'))


@app.route('/admin/info/<entity_type>/<int:entity_id>')
@operator_required
def entity_info(entity_type, entity_id):
    page = request.args.get('page', 1, type=int)
    report = get_entity_report(entity_type, entity_id, page=page, per_page=100)
    if not report:
        flash('Məlumat tapılmadı.', 'warning')
        return redirect(url_for('index'))
    return render_template('entity_info.html', report=report)

@app.route('/admin/settings', methods=['GET', 'POST'])
@role_required(['admin', 'supervisor'])
def admin_settings():
    if request.method == 'POST':
        allow_past = '1' if request.form.get('allow_past_expense_date') == 'on' else '0'
        set_setting('allow_past_expense_date', allow_past)

        expense_types = _clean_lines(request.form.get('expense_types_text', ''))
        if not expense_types:
            expense_types = EXPENSE_TYPES
        subtype_map = parse_subtype_settings(request.form.get('expense_subtypes_text', ''), expense_types)

        set_setting('expense_types_json', json.dumps(expense_types, ensure_ascii=False))
        set_setting('expense_subtypes_json', json.dumps(subtype_map, ensure_ascii=False))

        status_text = 'AÇIQ' if allow_past == '1' else 'BAĞLI'
        log_action('UPDATE_SETTINGS', f"Sistem ayarları yeniləndi. Keçmiş tarix: {status_text}. Xərc növləri: {len(expense_types)}")
        flash('Sistem ayarları yadda saxlandı.', 'success')
        return redirect(url_for('admin_settings'))

    expense_types = get_expense_types()
    expense_subtypes = get_expense_subtypes()
    subtype_lines = []
    for t in expense_types:
        vals = expense_subtypes.get(t, [])
        subtype_lines.append(f"{t}: {', '.join(vals)}" if vals else f"{t}:")
    return render_template(
        'admin_settings.html',
        allow_past_expense_date=is_past_expense_allowed(),
        expense_types_text='\n'.join(expense_types),
        expense_subtypes_text='\n'.join(subtype_lines),
        expense_types=expense_types,
        expense_subtypes=expense_subtypes
    )

@app.route('/admin/users')
@login_required
def admin_users():
    if session.get('role') not in ['admin', 'supervisor']:
        flash('İcazə yoxdur.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin_users.html', users=get_operators())
@app.route('/admin/users/add', methods=['POST'])
@admin_required
def add_user(): conn=get_connection_safe(); conn.cursor().execute("INSERT INTO users (fullname, username, password, role) VALUES (%s, %s, %s, %s)", (request.form['fullname'], request.form['username'], request.form['password'], request.form['role'])); conn.commit(); conn.close(); return redirect(url_for('admin_users'))
@app.route('/admin/user/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    if request.method=='POST': 
        conn=get_connection_safe(); sql="UPDATE users SET fullname=%s, username=%s, role=%s"; p=[request.form['fullname'], request.form['username'], request.form['role']]
        if request.form['password']: sql+=", password=%s"; p.append(request.form['password'])
        conn.cursor().execute(sql+" WHERE id=%s", tuple(p+[id])); conn.commit(); conn.close(); return redirect(url_for('admin_users'))
    return render_template('edit_user.html', user=get_user_by_id(id))
@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id): conn=get_connection_safe(); conn.cursor().execute("DELETE FROM users WHERE id=%s", (id,)); conn.commit(); conn.close(); return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)