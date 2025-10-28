from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from dateutil.relativedelta import relativedelta # Tarix fərqini hesablamaq üçün

# ----------------------------------------------------
# 1. FLASK TƏTBİQİNİN QURULMASI
# ----------------------------------------------------
app = Flask(__name__)
app.secret_key = 'ASIS_Sizin_Real_Gizli_Acariniz_Burada_Olsun' 

# ----------------------------------------------------
# 2. MƏLUMAT BAZASININ TƏQLİDİ (REAL DB ƏVƏZİ)
# ----------------------------------------------------

# İstifadəçi bazası
USERS = [
    {"id": 1, "fullname": "Administrator", "username": "admin", "password": "adminpass", "role": "admin"},
    {"id": 2, "fullname": "Asif Atababayev", "username": "operator", "password": "operpass", "role": "user"}
]
next_user_id = 3 

# Sürücü Məlumatları - YENİLƏNİB: start_date əlavə edildi
DRIVERS_DATA = [
    {"id": 101, "name": "Cavid Məmmədov Əli oğlu", "license_no": "AZE12345", "phone": "050-111-22-33", "start_date": "2023-10-28"},
    {"id": 102, "name": "Nigar Əliyeva Zaur qızı", "license_no": "AZE67890", "phone": "051-444-55-66", "start_date": "2024-05-15"},
    {"id": 103, "name": "Rəşad Həsənov Samir oğlu", "license_no": "AZE10111", "phone": "055-777-88-99", "start_date": None}, # Başlama tarixi yoxdur
    {"id": 104, "name": "Nurlan Seyfiyev Cəyanət", "license_no": "", "phone": "050-XXX-XX-XX", "start_date": "2025-09-01"}, # Yeni sürücü
]

# Köməkçi və Planlamaçı kataloqları (operator idarə edir)
ASSISTANTS_DATA = [
    {"id": 201, "name": "Vahid Vahidli"} 
]
PLANNERS_DATA = [
    {"id": 301, "name": "Asif Atabəyov"} 
]

def _next_id(seq, start):
    # Verilmiş siyahıdakı ən böyük ID-ni tapıb üzərinə 1 gəlir, siyahı boşdursa başlanğıc dəyərini qaytarır.
    return (max([x["id"] for x in seq]) + 1) if seq else start

# Avtomobil Məlumatları
CARS_DATA = [
    {"id": 1, "driver_id": 101, "car_number": "99-XX-001", "model": "Toyota Prius", 
     "brand": "Toyota", "model_name": "Prius", "category": "Sedan", "assistant_id": None, "planner_id": None, "notes": ""},
    {"id": 2, "driver_id": 102, "car_number": "90-ZZ-999", "model": "Kia Optima", 
     "brand": "Kia", "model_name": "Optima", "category": "Sedan", "assistant_id": None, "planner_id": 301, "notes": ""},
    {"id": 3, "driver_id": None, "car_number": "10-RA-321", "model": "Ford Transit", 
     "brand": "Ford", "model_name": "Transit", "category": "Minik Avtomobili", "assistant_id": 201, "planner_id": 301, "notes": ""},
]

# Xərc Məlumatları
EXPENSES = [
    {"car_id": 1, "amount": 85.50, "type": "Yanacaq", "litr": 15.0, "description": "AI-92 - Qeyd", "entered_by": "operator", "timestamp": datetime(2025, 10, 20, 9, 30),
     "driver_id_at_expense": 101, "assistant_id_at_expense": None, "planner_id_at_expense": None},
    {"car_id": 2, "amount": 40.00, "type": "Avtoyuma", "litr": 0, "description": "Yuma xərci", "entered_by": "admin", "timestamp": datetime(2025, 10, 21, 14, 15),
     "driver_id_at_expense": 102, "assistant_id_at_expense": None, "planner_id_at_expense": 301}, 
    {"car_id": 1, "amount": 250.00, "type": "Təmir", "litr": 0, "description": "Yağ dəyişimi", "entered_by": "operator", "timestamp": datetime(2025, 10, 22, 17, 0),
     "driver_id_at_expense": 101, "assistant_id_at_expense": None, "planner_id_at_expense": None},
    {"car_id": 3, "amount": 100.00, "type": "Yanacaq", "litr": 20.0, "description": "AI-95 - Qeyd 2", "entered_by": "operator", "timestamp": datetime(2025, 10, 25, 16, 19),
     "driver_id_at_expense": None, "assistant_id_at_expense": 201, "planner_id_at_expense": 301},
    {"car_id": 2, "amount": 50.00, "type": "Cərimə", "litr": 0, "description": "Sürət həddi", "entered_by": "admin", "timestamp": datetime(2025, 10, 27, 11, 00),
     "driver_id_at_expense": 102, "assistant_id_at_expense": None, "planner_id_at_expense": 301}, 
]

# Xərc növlərinin siyahısı (filtr üçün)
EXPENSE_TYPES = ["Yanacaq", "Təmir", "Cərimə", "Avtoyuma", "Yemək", "Digər"]

# ----------------------------------------------------
# 3. KÖMƏKÇİ FUNKSİYALAR
# ----------------------------------------------------
def get_car_by_id(car_id):
    """Verilmiş ID-yə uyğun avtomobili CARS_DATA-dan tapır."""
    car_id = int(car_id) if car_id else None 
    return next((car for car in CARS_DATA if car['id'] == car_id), None)

def get_driver_by_id(driver_id):
    """Verilmiş ID-yə uyğun sürücünü DRIVERS_DATA-dan tapır."""
    driver_id = int(driver_id) if driver_id else None
    return next((driver for driver in DRIVERS_DATA if driver['id'] == driver_id), None)

def get_user_by_id(user_id):
    """Verilmiş ID-yə uyğun istifadəçini USERS-dən tapır."""
    user_id = int(user_id) if user_id else None
    return next((user for user in USERS if user['id'] == user_id), None)

def get_user_by_username(username):
    """Verilmiş istifadəçi adına uyğun istifadəçini USERS-dən tapır."""
    return next((user for user in USERS if user['username'] == username), None)

def get_assistant_by_id(aid):
    """Verilmiş ID-yə uyğun köməkçini ASSISTANTS_DATA-dan tapır."""
    aid = int(aid) if aid is not None and aid != "" else None
    return next((a for a in ASSISTANTS_DATA if a['id'] == aid), None)

def get_planner_by_id(pid):
    """Verilmiş ID-yə uyğun planlamaçını PLANNERS_DATA-dan tapır."""
    pid = int(pid) if pid is not None and pid != "" else None
    return next((p for p in PLANNERS_DATA if p['id'] == pid), None)

def _derive_brand_and_model(car):
    """Avtomobilin brand və model_name sahələrini doldurur (əgər boşdursa modeldən ayırır)."""
    brand = car.get('brand') or ""
    model_name = car.get('model_name') or ""
    if (not brand or not model_name) and car.get('model'):
        parts = car['model'].split(' ', 1)
        if not brand and parts: brand = parts[0]
        if not model_name and len(parts) > 1: model_name = parts[1]
    return brand, model_name

def get_dashboard_data():
    """Operator dashboardı üçün məlumatları hazırlayır."""
    full_data = []
    for car in CARS_DATA:
        driver = get_driver_by_id(car['driver_id'])
        car_expenses = [e for e in EXPENSES if e['car_id'] == car['id']]
        total_expense = sum(e['amount'] for e in car_expenses)
        last_expense_entered_by = car_expenses[-1]['entered_by'] if car_expenses else "Yoxdur"
        
        detailed_expenses = []
        for e in sorted(car_expenses, key=lambda x: x['timestamp'], reverse=True):
            driver_at_expense = get_driver_by_id(e.get('driver_id_at_expense'))
            assistant_at_expense = get_assistant_by_id(e.get('assistant_id_at_expense'))
            planner_at_expense = get_planner_by_id(e.get('planner_id_at_expense'))
            detailed_expenses.append({
                "type": e['type'], "amount": e['amount'], "litr": e.get('litr', 0), 
                "description": e['description'], "entered_by": e['entered_by'],
                "timestamp_str": e['timestamp'].strftime('%d.%m.%Y %H:%M'),
                "driver_name": driver_at_expense['name'] if driver_at_expense else "-",
                "assistant_name": assistant_at_expense['name'] if assistant_at_expense else "-",
                "planner_name": planner_at_expense['name'] if planner_at_expense else "-"
            })
            
        brand, model_name = _derive_brand_and_model(car)
        assistant = get_assistant_by_id(car.get('assistant_id'))
        planner = get_planner_by_id(car.get('planner_id'))
        
        full_data.append({
            "id": car['id'], "driver_id": car['driver_id'], "car_number": car['car_number'],
            "brand_model": f"{brand} / {model_name}".strip(" /"), "category": car.get('category', ""),
            "assistant_name": assistant['name'] if assistant else "", "planner_name": planner['name'] if planner else "",
            "driver_name": driver['name'] if driver else "TƏYİN OLUNMAYIB",
            "total_expense": total_expense, "entered_by": last_expense_entered_by, 
            "notes": car.get('notes', ""), "expenses": detailed_expenses,
            "brand_raw": brand, "model_name_raw": model_name,
            "assistant_id": car.get('assistant_id'), "planner_id": car.get('planner_id'),
            "has_expenses": total_expense > 0
        })
    return full_data

def calculate_experience(start_date_str):
    """Verilmiş başlama tarixindən bu günə qədər olan təcrübəni 'X il, Y ay' formatında qaytarır."""
    if not start_date_str:
        return "-"
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if start_date > today:
            return "Başlamayıb"
            
        delta = relativedelta(today, start_date)
        
        years = delta.years
        months = delta.months
        
        experience_parts = []
        if years > 0:
            experience_parts.append(f"{years} il")
        if months > 0:
            experience_parts.append(f"{months} ay")
            
        if not experience_parts: 
             if delta.days >= 0: 
                 return "Yeni" 
             else:
                 return "-" 
                 
        return ", ".join(experience_parts)
        
    except ValueError:
        return "Tarix xətası" 

# ----------------------------------------------------
# 4. GİRİŞ VƏ İCAZƏ FUNKSİYALARI
# ----------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']; password = request.form['password']
        user = get_user_by_username(username)
        if user and user['password'] == password: 
            session['user'] = user['username']
            session['role'] = user['role']
            session['fullname'] = user['fullname']
            flash(f"Xoş gəldiniz, {user['fullname']}!", 'success')
            return redirect(url_for('index'))
        else:
            error = 'Yanlış istifadəçi adı və ya parol.'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None); session.pop('role', None); session.pop('fullname', None)
    flash("Sistemdən çıxış etdiniz.", 'info')
    return redirect(url_for('login'))

def is_admin():
    return session.get('role') == 'admin'

def is_operator():
    return session.get('role') == 'user'

# ----------------------------------------------------
# 5. ƏSAS SƏHİFƏ (DASHBOARD)
# ----------------------------------------------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # === ADMİN DASHBOARD MƏLUMATLARI ===
    if session['role'] == 'admin':
        total_operator_count = len([u for u in USERS if u['role'] == 'user'])
        total_car_count = len(CARS_DATA)
        total_driver_count = len(DRIVERS_DATA)
        total_assistant_count = len(ASSISTANTS_DATA)
        total_planner_count = len(PLANNERS_DATA)
        
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
    # === ADMİN DASHBOARD BİTDİ ===
    
    # === OPERATOR DASHBOARD MƏLUMATLARI ===
    dashboard_data = get_dashboard_data()
    return render_template(
        'operator_dashboard.html', 
        user_role=session['role'], 
        cars=dashboard_data, 
        drivers=DRIVERS_DATA,
        assistants=ASSISTANTS_DATA,
        planners=PLANNERS_DATA
    )

# ----------------------------------------------------
# 6. OPERATOR FUNKSİYALARI (CRUD Əməliyyatları)
# ----------------------------------------------------
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not is_operator(): return redirect(url_for('index'))
    
    car_id = request.form.get('car_id')
    expense_type = request.form.get('expense_type') 
    amount = request.form.get('amount')
    litr = request.form.get('litr', 0)
    description = request.form.get('description', '') 
    fuel_subtype = request.form.get('fuel_subtype', '') 
    
    final_description = description
    if expense_type == 'Yanacaq' and fuel_subtype:
        final_description = f"{fuel_subtype} - {description}" if description else fuel_subtype

    car = get_car_by_id(car_id)
    driver_id_at_expense, assistant_id_at_expense, planner_id_at_expense = None, None, None
    if car:
        driver_id_at_expense = car.get('driver_id')
        assistant_id_at_expense = car.get('assistant_id')
        planner_id_at_expense = car.get('planner_id')

    new_expense = {
        "car_id": int(car_id), 
        "type": expense_type,  
        "amount": float(amount), 
        "litr": float(litr) if litr else 0.0,
        "description": final_description, 
        "entered_by": session['user'], 
        "timestamp": datetime.now(),
        "driver_id_at_expense": driver_id_at_expense, 
        "assistant_id_at_expense": assistant_id_at_expense,
        "planner_id_at_expense": planner_id_at_expense
    }
    EXPENSES.append(new_expense) 
    flash(f'{expense_type} xərci uğurla əlavə edildi.', 'success')
    return redirect(url_for('index'))

@app.route('/assign_car', methods=['POST'])
def assign_car(): 
    if not is_operator(): return redirect(url_for('login'))
    car_id = request.form.get('car_id'); driver_id = request.form.get('driver_id'); car_to_assign = get_car_by_id(car_id)
    if car_to_assign: car_to_assign['driver_id'] = int(driver_id) if driver_id else None
    return redirect(url_for('index'))

@app.route('/update_car_meta', methods=['POST'])
def update_car_meta():
    if not is_operator(): return redirect(url_for('login'))
    
    car_id = request.form.get('car_id'); car = get_car_by_id(car_id)
    if car:
        car['brand'] = request.form.get('brand', '').strip()
        car['model_name'] = request.form.get('model_name', '').strip()
        car['category'] = request.form.get('category', '').strip()
        d_id = request.form.get('driver_id'); a_id = request.form.get('assistant_id'); p_id = request.form.get('planner_id')
        
        car['driver_id'] = int(d_id) if d_id else None
        car['assistant_id'] = int(a_id) if a_id else None
        car['planner_id'] = int(p_id) if p_id else None
        
        car['notes'] = request.form.get('notes', '').strip()
        flash('Avtomobil məlumatları yeniləndi.', 'success')
    else:
        flash('Avtomobil tapılmadı və məlumatlar yenilənmədi.', 'danger')
        
    return redirect(url_for('index'))

# --- Operatorun İdarəetmə Səhifələri ---

@app.route('/admin/drivers')
def admin_drivers():
    """Sürücü siyahısını və əlavə etmə formasını göstərir."""
    if not is_operator(): return redirect(url_for('index'))
    
    drivers_processed = []
    for driver in DRIVERS_DATA:
        driver_copy = driver.copy() 
        driver_copy['has_expenses'] = any(e.get('driver_id_at_expense') == driver_copy['id'] for e in EXPENSES)
        driver_copy['experience_str'] = calculate_experience(driver_copy.get('start_date'))
        drivers_processed.append(driver_copy)
        
    return render_template('admin_drivers.html', drivers=drivers_processed)

@app.route('/admin/cars')
def admin_cars():
    if not is_operator(): return redirect(url_for('index'))
    cars_with_expense_info = []
    for car in CARS_DATA: 
        car_copy = car.copy()
        car_copy['has_expenses'] = any(e['car_id'] == car_copy['id'] for e in EXPENSES)
        cars_with_expense_info.append(car_copy)
    return render_template('admin_cars.html', cars=cars_with_expense_info, 
                           drivers=DRIVERS_DATA, assistants=ASSISTANTS_DATA, planners=PLANNERS_DATA) 

@app.route('/admin/assistants')
def admin_assistants():
    if not is_operator(): return redirect(url_for('index'))
    assistants_with_expense_info = []
    for a in ASSISTANTS_DATA:
        a_copy = a.copy()
        a_copy['has_expenses'] = any(e.get('assistant_id_at_expense') == a_copy['id'] for e in EXPENSES)
        assistants_with_expense_info.append(a_copy)
    return render_template('admin_assistants.html', assistants=assistants_with_expense_info)

@app.route('/admin/assistants/add', methods=['POST'])
def add_assistant():
    if not is_operator(): return redirect(url_for('index'))
    name = request.form['name'].strip()
    if name: 
        ASSISTANTS_DATA.append({"id": _next_id(ASSISTANTS_DATA, 201), "name": name})
        flash(f"Köməkçi '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_assistants'))

@app.route('/admin/assistant/edit/<int:aid>', methods=['GET', 'POST'])
def edit_assistant(aid):
    if not is_operator(): return redirect(url_for('index'))
    assistant = get_assistant_by_id(aid)
    if not assistant: return redirect(url_for('admin_assistants'))
    if request.method == 'POST': 
        old_name = assistant['name']
        assistant['name'] = request.form['name'].strip()
        flash(f"Köməkçi '{old_name}' adı '{assistant['name']}' olaraq dəyişdirildi.", 'success')
        return redirect(url_for('admin_assistants'))
    return render_template('edit_assistant.html', assistant=assistant)

@app.route('/admin/assistant/delete/<int:aid>', methods=['POST'])
def delete_assistant(aid):
    if not is_operator(): return redirect(url_for('index'))
    if any(e.get('assistant_id_at_expense') == aid for e in EXPENSES):
        flash('Bu köməkçi silinə bilməz! Köməkçiyə aid xərc məlumatı mövcuddur.', 'danger')
        return redirect(url_for('admin_assistants')) 
    assistant = get_assistant_by_id(aid)
    if assistant: 
        name = assistant['name']
        ASSISTANTS_DATA.remove(assistant)
        [car.update({'assistant_id': None}) for car in CARS_DATA if car.get('assistant_id') == aid]
        flash(f"Köməkçi '{name}' silindi.", 'success')
    return redirect(url_for('admin_assistants'))

@app.route('/admin/planners')
def admin_planners():
    if not is_operator(): return redirect(url_for('index'))
    planners_with_expense_info = []
    for p in PLANNERS_DATA:
        p_copy = p.copy()
        p_copy['has_expenses'] = any(e.get('planner_id_at_expense') == p_copy['id'] for e in EXPENSES)
        planners_with_expense_info.append(p_copy)
    return render_template('admin_planners.html', planners=planners_with_expense_info)

@app.route('/admin/planners/add', methods=['POST'])
def add_planner():
    if not is_operator(): return redirect(url_for('index'))
    name = request.form['name'].strip()
    if name: 
        PLANNERS_DATA.append({"id": _next_id(PLANNERS_DATA, 301), "name": name})
        flash(f"Planlamaçı '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_planners'))

@app.route('/admin/planner/edit/<int:pid>', methods=['GET', 'POST'])
def edit_planner(pid):
    if not is_operator(): return redirect(url_for('index'))
    planner = get_planner_by_id(pid)
    if not planner: return redirect(url_for('admin_planners'))
    if request.method == 'POST': 
        old_name = planner['name']
        planner['name'] = request.form['name'].strip()
        flash(f"Planlamaçı '{old_name}' adı '{planner['name']}' olaraq dəyişdirildi.", 'success')
        return redirect(url_for('admin_planners'))
    return render_template('edit_planner.html', planner=planner)

@app.route('/admin/planner/delete/<int:pid>', methods=['POST'])
def delete_planner(pid):
    if not is_operator(): return redirect(url_for('index'))
    if any(e.get('planner_id_at_expense') == pid for e in EXPENSES):
        flash('Bu planlamaçı silinə bilməz! Planlamaçıya aid xərc məlumatı mövcuddur.', 'danger')
        return redirect(url_for('admin_planners')) 
    planner = get_planner_by_id(pid)
    if planner: 
        name = planner['name']
        PLANNERS_DATA.remove(planner)
        [car.update({'planner_id': None}) for car in CARS_DATA if car.get('planner_id') == pid]
        flash(f"Planlamaçı '{name}' silindi.", 'success')
    return redirect(url_for('admin_planners'))

@app.route('/admin/drivers/add', methods=['POST'])
def add_driver():
    """Yeni sürücü əlavə edir."""
    if not is_operator(): return redirect(url_for('index'))
    
    name = request.form.get('name', '').strip()
    license_no = request.form.get('license_no', '').strip()
    phone = request.form.get('phone', '').strip()
    start_date = request.form.get('start_date', '').strip() 

    if not name:
        flash("Sürücü adı mütləq daxil edilməlidir.", "danger")
        return redirect(url_for('admin_drivers'))

    if license_no and any(d['license_no'] == license_no for d in DRIVERS_DATA if d.get('license_no')):
        flash(f"'{license_no}' vəsiqə nömrəsi artıq sistemdə mövcuddur.", 'danger')
        return redirect(url_for('admin_drivers'))
        
    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            flash("İşə başlama tarixi formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
            start_date = None 

    DRIVERS_DATA.append({
        "id": _next_id(DRIVERS_DATA, 101), 
        "name": name, 
        "license_no": license_no, 
        "phone": phone,
        "start_date": start_date 
        })
    flash(f"Sürücü '{name}' əlavə edildi.", 'success')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/cars/add', methods=['POST'])
def add_car():
    if not is_operator(): return redirect(url_for('index'))
    car_number = request.form['car_number']; model = request.form['model']
    driver_id = int(request.form['driver_id']) if request.form.get('driver_id') else None
    assistant_id = int(request.form['assistant_id']) if request.form.get('assistant_id') else None
    planner_id = int(request.form['planner_id']) if request.form.get('planner_id') else None
    
    new_id = max([c['id'] for c in CARS_DATA] + [0]) + 1 
    
    CARS_DATA.append({
        "id": new_id, "driver_id": driver_id, "assistant_id": assistant_id, "planner_id": planner_id,
        "car_number": car_number, "model": model, 
        "brand": "", "model_name": "", "category": "", "notes": "" 
    })
    flash(f"Avtomobil '{car_number}' əlavə edildi.", 'success')
    return redirect(url_for('admin_cars'))

@app.route('/admin/driver/delete/<int:id>', methods=['POST'])
def delete_driver(id):
    if not is_operator(): return redirect(url_for('index'))
    if any(e.get('driver_id_at_expense') == id for e in EXPENSES):
        flash('Bu sürücü silinə bilməz! Sürücüyə aid xərc məlumatı mövcuddur.', 'danger')
        return redirect(url_for('admin_drivers')) 
    driver = get_driver_by_id(id)
    if driver: 
        name = driver['name']
        DRIVERS_DATA.remove(driver)
        [car.update({'driver_id': None}) for car in CARS_DATA if car['driver_id'] == id]
        flash(f"Sürücü '{name}' silindi.", 'success')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/car/delete/<int:id>', methods=['POST'])
def delete_car(id):
    if not is_operator(): return redirect(url_for('login'))
    redirect_url = request.referrer or url_for('index')
    car = get_car_by_id(id)
    if not car:
        flash('Avtomobil tapılmadı.', 'danger')
        return redirect(redirect_url) 
    if any(e['car_id'] == id for e in EXPENSES):
        flash('Bu avtomobil silinə bilməz! Avtomobilə aid xərc məlumatı mövcuddur.', 'danger')
    else:
        car_number = car['car_number']
        CARS_DATA.remove(car)
        flash(f"Avtomobil '{car_number}' uğurla silindi.", 'success')
    return redirect(redirect_url) 

@app.route('/admin/driver/edit/<int:id>', methods=['GET', 'POST'])
def edit_driver(id):
    """Mövcud sürücünü redaktə edir."""
    if not is_operator(): return redirect(url_for('index'))
    driver = get_driver_by_id(id)
    if not driver: return redirect(url_for('admin_drivers'))
    
    if request.method == 'POST': 
        driver['name'] = request.form['name']
        driver['license_no'] = request.form.get('license_no', '') 
        driver['phone'] = request.form['phone']
        start_date = request.form.get('start_date', '').strip() 
        
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                driver['start_date'] = start_date 
            except ValueError:
                flash("İşə başlama tarixi formatı yanlışdır (YYYY-MM-DD olmalıdır). Tarix yenilənmədi.", "warning")
        else:
             driver['start_date'] = None 
             
        flash(f"Sürücü '{driver['name']}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_drivers'))
        
    return render_template('edit_driver.html', driver=driver)

@app.route('/admin/car/edit/<int:id>', methods=['GET', 'POST'])
def edit_car(id):
    if not is_operator(): return redirect(url_for('index'))
    car = get_car_by_id(id)
    if not car: return redirect(url_for('admin_cars')) 
    if request.method == 'POST': 
        car['car_number'] = request.form['car_number']
        car['model'] = request.form['model']
        car['driver_id'] = int(request.form['driver_id']) if request.form['driver_id'] else None 
        flash(f"Avtomobil '{car['car_number']}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_cars')) 
    return render_template('edit_car.html', car=car, drivers=DRIVERS_DATA)


# ----------------------------------------------------
# 7. TOPLU ƏLAVƏ ETMƏ FUNKSİYALARI
# ----------------------------------------------------

@app.route('/admin/drivers/bulk_add', methods=['POST'])
def bulk_add_driver():
    """Toplu şəkildə sürücüləri əlavə edir."""
    if not is_operator(): return redirect(url_for('index'))
    
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0; skipped_count = 0
    next_driver_id = _next_id(DRIVERS_DATA, 101)
    existing_licenses = {d['license_no'] for d in DRIVERS_DATA if d.get('license_no')}

    for line in bulk_data.splitlines():
        if not line.strip(): continue 
        
        parts = line.split(';')
        if not parts: continue
        
        name = parts[0].strip()
        if not name: skipped_count += 1; continue 

        license_no = parts[1].strip() if len(parts) > 1 else ""
        phone = parts[2].strip() if len(parts) > 2 else ""
        start_date = parts[3].strip() if len(parts) > 3 else None 

        if start_date:
            try: datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError: start_date = None 

        if license_no and license_no in existing_licenses:
            skipped_count += 1
            continue
            
        new_driver = {"id": next_driver_id, "name": name, "license_no": license_no, "phone": phone, "start_date": start_date }
        DRIVERS_DATA.append(new_driver)
        if license_no: existing_licenses.add(license_no)
        next_driver_id += 1; added_count += 1
            
    flash(f"{added_count} sürücü uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan vəsiqə və ya səhv format) ötürüldü.", 'success')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/cars/bulk_add', methods=['POST'])
def bulk_add_car():
    if not is_operator(): return redirect(url_for('index'))
    bulk_data = request.form.get('bulk_data', '')
    added_count = 0; skipped_count = 0
    next_car_id = _next_id(CARS_DATA, 1)
    existing_car_numbers = {c['car_number'] for c in CARS_DATA}
    for line in bulk_data.splitlines():
        if not line.strip(): continue
        parts = line.split(';')
        if len(parts) < 2: skipped_count += 1; continue 
        car_number = parts[0].strip(); model = parts[1].strip()
        if not car_number or not model: skipped_count += 1; continue
        if car_number not in existing_car_numbers:
            CARS_DATA.append({"id": next_car_id, "car_number": car_number, "model": model, "driver_id": None, "assistant_id": None, "planner_id": None, "brand": "", "model_name": "", "category": "", "notes": ""})
            existing_car_numbers.add(car_number); next_car_id += 1; added_count += 1
        else: skipped_count += 1
    flash(f"{added_count} avtomobil uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan nömrə və ya səhv format) ötürüldü.", 'success')
    return redirect(url_for('admin_cars'))

@app.route('/admin/assistants/bulk_add', methods=['POST'])
def bulk_add_assistant():
    if not is_operator(): return redirect(url_for('index'))
    bulk_data = request.form.get('bulk_data', ''); added_count = 0; skipped_count = 0
    next_assistant_id = _next_id(ASSISTANTS_DATA, 201)
    existing_assistants = {a['name'].lower() for a in ASSISTANTS_DATA}
    for line in bulk_data.splitlines():
        name = line.strip(); 
        if not name: continue
        if name.lower() not in existing_assistants:
            ASSISTANTS_DATA.append({"id": next_assistant_id, "name": name})
            existing_assistants.add(name.lower()); next_assistant_id += 1; added_count += 1
        else: skipped_count += 1
    flash(f"{added_count} köməkçi uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan ad) ötürüldü.", 'success')
    return redirect(url_for('admin_assistants'))

@app.route('/admin/planners/bulk_add', methods=['POST'])
def bulk_add_planner():
    if not is_operator(): return redirect(url_for('index'))
    bulk_data = request.form.get('bulk_data', ''); added_count = 0; skipped_count = 0
    next_planner_id = _next_id(PLANNERS_DATA, 301)
    existing_planners = {p['name'].lower() for p in PLANNERS_DATA}
    for line in bulk_data.splitlines():
        name = line.strip(); 
        if not name: continue
        if name.lower() not in existing_planners:
            PLANNERS_DATA.append({"id": next_planner_id, "name": name})
            existing_planners.add(name.lower()); next_planner_id += 1; added_count += 1
        else: skipped_count += 1
    flash(f"{added_count} planlamaçı uğurla əlavə edildi. {skipped_count} sətir (təkrarlanan ad) ötürüldü.", 'success')
    return redirect(url_for('admin_planners'))

# ----------------------------------------------------
# 8. YALNIZ ADMİN FUNKSİYALARI (İstifadəçi İdarəetməsi)
# ----------------------------------------------------
@app.route('/admin/users')
def admin_users():
    if not is_admin(): return redirect(url_for('index')) 
    users_list = [user for user in USERS if user['role'] == 'user'] 
    return render_template('admin_users.html', users=users_list)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    global next_user_id 
    if not is_admin(): return redirect(url_for('index'))
    fullname = request.form['fullname']; username = request.form['username']
    password = request.form['password']; role = request.form['role']
    if get_user_by_username(username):
        flash('Bu istifadəçi adı artıq mövcuddur!', 'danger')
        return redirect(url_for('admin_users'))
    USERS.append({"id": next_user_id, "fullname": fullname, "username": username, "password": password, "role": role })
    next_user_id += 1 
    flash(f"İstifadəçi '{fullname}' ({role}) əlavə edildi.", 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if not is_admin(): return redirect(url_for('index'))
    user = get_user_by_id(id)
    if not user: return redirect(url_for('admin_users')) 
    if request.method == 'POST':
        new_username = request.form['username']
        existing_user = get_user_by_username(new_username)
        if existing_user and existing_user['id'] != id:
            flash('Bu istifadəçi adı artıq başqası tərəfindən istifadə olunur!', 'danger')
            return render_template('edit_user.html', user=user) 
        user['fullname'] = request.form['fullname']
        user['username'] = new_username
        user['role'] = request.form['role']
        new_password = request.form.get('password')
        if new_password: user['password'] = new_password 
        flash(f"İstifadəçi '{user['fullname']}' məlumatları yeniləndi.", 'success')
        return redirect(url_for('admin_users'))
    return render_template('edit_user.html', user=user)

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
def delete_user(id):
    if not is_admin(): return redirect(url_for('index'))
    user = get_user_by_id(id)
    if user and user['role'] != 'admin': 
        name = user['fullname']
        USERS.remove(user)
        flash(f"İstifadəçi '{name}' silindi.", 'success')
    elif user and user['role'] == 'admin':
        flash('Admin özünü və ya başqa admini silə bilməz.', 'danger')
    return redirect(url_for('admin_users'))

# ----------------------------------------------------
# 9. HESABATLAR (Yalnız Admin üçün)
# ----------------------------------------------------
@app.route('/admin/reports', methods=['GET'])
def admin_reports():
    if not is_admin(): return redirect(url_for('index'))

    f_car_id = request.args.get('car_id', type=int)
    f_driver_id = request.args.get('driver_id', type=int) 
    f_assistant_id = request.args.get('assistant_id', type=int) 
    f_planner_id = request.args.get('planner_id', type=int)     
    f_user_username = request.args.get('user_username', type=str) 
    f_expense_type = request.args.get('expense_type', type=str) 
    f_start_date_str = request.args.get('start_date', type=str)
    f_end_date_str = request.args.get('end_date', type=str)

    all_expenses_enriched = []
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
    if f_start_date_str:
        try: start_date = datetime.strptime(f_start_date_str, '%Y-%m-%d').date(); filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() >= start_date]
        except ValueError: flash("Başlanğıc tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")
    if f_end_date_str:
        try: end_date = datetime.strptime(f_end_date_str, '%Y-%m-%d').date(); filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() <= end_date]
        except ValueError: flash("Bitmə tarix formatı yanlışdır (YYYY-MM-DD olmalıdır).", "warning")

    total_amount = sum(e['expense']['amount'] for e in filtered_expenses)
    operators = [user for user in USERS if user['role'] == 'user']

    return render_template(
        'admin_reports.html', 
        reports=sorted(filtered_expenses, key=lambda x: x['expense']['timestamp'], reverse=True), 
        total_amount=total_amount,
        drivers=DRIVERS_DATA, cars=CARS_DATA, operators=operators, 
        assistants=ASSISTANTS_DATA, planners=PLANNERS_DATA, 
        expense_types=EXPENSE_TYPES, 
        selected_filters={ 
            'car_id': f_car_id, 'driver_id': f_driver_id, 'assistant_id': f_assistant_id, 'planner_id': f_planner_id, 
            'user_username': f_user_username, 'expense_type': f_expense_type, 
            'start_date': f_start_date_str, 'end_date': f_end_date_str
        }
    )

# ----------------------------------------------------
# 10. TƏTBİQİ BAŞLATMA (Development üçün)
# ----------------------------------------------------
if __name__ == '__main__':
    # relativedelta üçün kitabxananı import etməyi unutmayın: pip install python-dateutil
    app.run(debug=True)