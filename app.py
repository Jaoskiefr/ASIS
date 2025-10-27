from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

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

# Sürücü Məlumatları
DRIVERS_DATA = [
    {"id": 101, "name": "Cavid Məmmədov Əli oğlu", "license_no": "AZE12345", "phone": "050-111-22-33"},
    {"id": 102, "name": "Nigar Əliyeva Zaur qızı", "license_no": "AZE67890", "phone": "051-444-55-66"},
    {"id": 103, "name": "Rəşad Həsənov Samir oğlu", "license_no": "AZE10111", "phone": "055-777-88-99"},
]

# Köməkçi və Planlamaçı kataloqları (operator idarə edir)
ASSISTANTS_DATA = [
    # {"id": 201, "name": "Elvin Quliyev"}
]
PLANNERS_DATA = [
    # {"id": 301, "name": "Rüfət Məmmədli"}
]

def _next_id(seq, start):
    return (max([x["id"] for x in seq]) + 1) if seq else start

# Avtomobil Məlumatları
# Yeni sahələr: brand, model_name, category, assistant_id, planner_id, notes
CARS_DATA = [
    {"id": 1, "driver_id": 101, "car_number": "99-XX-001", "model": "Toyota Prius", 
     "brand": "", "model_name": "", "category": "", "assistant_id": None, "planner_id": None, "notes": ""},
    {"id": 2, "driver_id": 102, "car_number": "90-ZZ-999", "model": "Kia Optima", 
     "brand": "", "model_name": "", "category": "", "assistant_id": None, "planner_id": None, "notes": ""},
    {"id": 3, "driver_id": None, "car_number": "10-RA-321", "model": "Ford Transit", 
     "brand": "", "model_name": "", "category": "", "assistant_id": None, "planner_id": None, "notes": ""},
]

# Xərc/Yanacaq Məlumatları
EXPENSES = [
    {"car_id": 1, "amount": 85.50, "type": "Yanacaq", "litr": 15.0, "description": "AI-92", "entered_by": "operator", "timestamp": datetime(2025, 10, 20, 9, 30)},
    {"car_id": 2, "amount": 40.00, "type": "Xərc", "litr": 0, "description": "Yuma xərci", "entered_by": "admin", "timestamp": datetime(2025, 10, 21, 14, 15)}, 
    {"car_id": 1, "amount": 250.00, "type": "Xərc", "litr": 0, "description": "Yağ dəyişimi", "entered_by": "operator", "timestamp": datetime(2025, 10, 22, 17, 0)},
    {"car_id": 3, "amount": 100.00, "type": "Yanacaq", "litr": 20.0, "description": "AI-95", "entered_by": "operator", "timestamp": datetime.now()},
]

# ----------------------------------------------------
# 3. KÖMƏKÇİ FUNKSİYALAR
# ----------------------------------------------------
def get_car_by_id(car_id):
    car_id = int(car_id) if car_id else None 
    return next((car for car in CARS_DATA if car['id'] == car_id), None)

def get_driver_by_id(driver_id):
    driver_id = int(driver_id) if driver_id else None
    return next((driver for driver in DRIVERS_DATA if driver['id'] == driver_id), None)

def get_user_by_id(user_id):
    user_id = int(user_id) if user_id else None
    return next((user for user in USERS if user['id'] == user_id), None)

def get_user_by_username(username):
    return next((user for user in USERS if user['username'] == username), None)

def get_assistant_by_id(aid):
    aid = int(aid) if aid is not None and aid != "" else None
    return next((a for a in ASSISTANTS_DATA if a['id'] == aid), None)

def get_planner_by_id(pid):
    pid = int(pid) if pid is not None and pid != "" else None
    return next((p for p in PLANNERS_DATA if p['id'] == pid), None)

def _derive_brand_and_model(car):
    # Əgər boşdursa, model mətnindən ayırmağa cəhd et
    brand = car.get('brand') or ""
    model_name = car.get('model_name') or ""
    if (not brand or not model_name) and car.get('model'):
        parts = car['model'].split(' ', 1)
        if not brand and parts:
            brand = parts[0]
        if not model_name and len(parts) > 1:
            model_name = parts[1]
    return brand, model_name

def get_dashboard_data():
    """Əsas cədvəl üçün məlumatları birləşdirir (Operator üçün)"""
    full_data = []
    for car in CARS_DATA:
        driver = get_driver_by_id(car['driver_id'])
        car_expenses = [e for e in EXPENSES if e['car_id'] == car['id']]
        total_expense = sum(e['amount'] for e in car_expenses)
        last_expense_entered_by = car_expenses[-1]['entered_by'] if car_expenses else "Yoxdur"

        detailed_expenses = []
        for e in sorted(car_expenses, key=lambda x: x['timestamp'], reverse=True):
            detailed_expenses.append({
                "type": e['type'], "amount": e['amount'], "litr": e.get('litr', 0), 
                "description": e['description'], "entered_by": e['entered_by'],
                "timestamp_str": e['timestamp'].strftime('%d.%m.%Y %H:%M')
            })

        brand, model_name = _derive_brand_and_model(car)
        assistant = get_assistant_by_id(car.get('assistant_id'))
        planner = get_planner_by_id(car.get('planner_id'))

        full_data.append({
            "id": car['id'],
            "driver_id": car['driver_id'],
            "car_number": car['car_number'],

            # Cədvəl sütunları üçün
            "brand_model": f"{brand} / {model_name}".strip(" /"),
            "category": car.get('category', ""),
            "assistant_name": assistant['name'] if assistant else "",
            "planner_name": planner['name'] if planner else "",

            # Digərləri
            "driver_name": driver['name'] if driver else "TƏYİN OLUNMAYIB",
            "total_expense": total_expense, 
            "entered_by": last_expense_entered_by, 
            "notes": car.get('notes', ""),
            "expenses": detailed_expenses,

            # Modal üçün xam dəyərlər
            "brand_raw": brand, "model_name_raw": model_name,
            "assistant_id": car.get('assistant_id'),
            "planner_id": car.get('planner_id'),
        })
    return full_data

# ----------------------------------------------------
# 4. GİRİŞ VƏ İCAZƏ FUNKSİYALARI
# ----------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']; password = request.form['password']
        user = get_user_by_username(username)
        if user and user['password'] == password:
            session['user'] = user['username']; session['role'] = user['role']; session['fullname'] = user['fullname']
            return redirect(url_for('index'))
        else:
            error = 'Yanlış istifadəçi adı və ya parol.'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None); session.pop('role', None); session.pop('fullname', None)
    return redirect(url_for('login'))

def is_admin():
    return session.get('role') == 'admin'

def is_operator():
    return session.get('role') == 'user'

# ----------------------------------------------------
# 5. ƏSAS SƏHİFƏ
# ----------------------------------------------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session['role'] == 'admin':
        total_operator_count = len([u for u in USERS if u['role'] == 'user'])
        total_car_count = len(CARS_DATA)
        total_driver_count = len(DRIVERS_DATA)
        now = datetime.now()
        current_month_expenses = [
            e for e in EXPENSES 
            if e['timestamp'].month == now.month 
            and e['timestamp'].year == now.year
            and get_user_by_username(e['entered_by']) 
            and get_user_by_username(e['entered_by'])['role'] == 'user'
        ]
        monthly_total = sum(e['amount'] for e in current_month_expenses)
        expense_data = {} 
        for e in current_month_expenses:
            e_type = e.get('type', 'Digər') 
            expense_data[e_type] = expense_data.get(e_type, 0) + e['amount']
        chart_labels = list(expense_data.keys())
        chart_data_values = list(expense_data.values())

        return render_template(
            'dashboard.html', 
            user_role=session['role'],
            stats={
                'operator_count': total_operator_count,
                'car_count': total_car_count,
                'driver_count': total_driver_count,
                'monthly_total': monthly_total
            },
            chart_data={'labels': chart_labels, 'data': chart_data_values}
        )
    
    # Operator görünüşü
    dashboard_data = get_dashboard_data()
    return render_template(
        'dashboard.html', 
        user_role=session['role'], 
        cars=dashboard_data, 
        drivers=DRIVERS_DATA,
        assistants=ASSISTANTS_DATA,
        planners=PLANNERS_DATA
    )

# ----------------------------------------------------
# 6. OPERATOR FUNKSİYALARI (CRUD)
# ----------------------------------------------------
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not is_operator(): return redirect(url_for('login'))
    car_id = request.form.get('car_id'); expense_type = request.form.get('expense_type')
    amount = request.form.get('amount'); litr = request.form.get('litr', 0)
    description = request.form.get('description')
    new_expense = {
        "car_id": int(car_id),
        "type": expense_type,
        "amount": float(amount),
        "litr": float(litr) if litr else 0.0,
        "description": description,
        "entered_by": session['user'],
        "timestamp": datetime.now()
    }
    EXPENSES.append(new_expense)
    return redirect(url_for('index'))

@app.route('/assign_car', methods=['POST'])
def assign_car():
    if not is_operator(): return redirect(url_for('login'))
    car_id = request.form.get('car_id'); driver_id = request.form.get('driver_id')
    car_to_assign = get_car_by_id(car_id)
    if car_to_assign:
        car_to_assign['driver_id'] = int(driver_id) if driver_id else None
    return redirect(url_for('index'))

@app.route('/update_car_meta', methods=['POST'])
def update_car_meta():
    """Avtomobil meta: brand/model_name/category/assistant_id/planner_id/notes"""
    if not is_operator(): return redirect(url_for('login'))
    car_id = request.form.get('car_id')
    car = get_car_by_id(car_id)
    if car:
        car['brand'] = request.form.get('brand', '').strip()
        car['model_name'] = request.form.get('model_name', '').strip()
        car['category'] = request.form.get('category', '').strip()
        # Seçilən köməkçi/planlamaçı
        a_id = request.form.get('assistant_id'); p_id = request.form.get('planner_id')
        car['assistant_id'] = int(a_id) if a_id else None
        car['planner_id'] = int(p_id) if p_id else None
        car['notes'] = request.form.get('notes', '').strip()
    return redirect(url_for('index'))

# --- İdarəetmə səhifələri (hamısı operator səlahiyyətində) ---
@app.route('/admin/drivers')
def admin_drivers():
    if not is_operator(): return redirect(url_for('index'))
    return render_template('admin_drivers.html', drivers=DRIVERS_DATA)

@app.route('/admin/cars')
def admin_cars():
    if not is_operator(): return redirect(url_for('index'))
    return render_template('admin_cars.html', cars=CARS_DATA, drivers=DRIVERS_DATA) 

# Köməkçi idarəetməsi
@app.route('/admin/assistants')
def admin_assistants():
    if not is_operator(): return redirect(url_for('index'))
    return render_template('admin_assistants.html', assistants=ASSISTANTS_DATA)

@app.route('/admin/assistants/add', methods=['POST'])
def add_assistant():
    if not is_operator(): return redirect(url_for('index'))
    name = request.form['name'].strip()
    if name:
        new_id = _next_id(ASSISTANTS_DATA, 201)
        ASSISTANTS_DATA.append({"id": new_id, "name": name})
    return redirect(url_for('admin_assistants'))

@app.route('/admin/assistant/edit/<int:aid>', methods=['GET', 'POST'])
def edit_assistant(aid):
    if not is_operator(): return redirect(url_for('index'))
    assistant = get_assistant_by_id(aid)
    if not assistant: return redirect(url_for('admin_assistants'))
    if request.method == 'POST':
        assistant['name'] = request.form['name'].strip()
        return redirect(url_for('admin_assistants'))
    return render_template('edit_assistant.html', assistant=assistant)

@app.route('/admin/assistant/delete/<int:aid>', methods=['POST'])
def delete_assistant(aid):
    if not is_operator(): return redirect(url_for('index'))
    assistant = get_assistant_by_id(aid)
    if assistant:
        ASSISTANTS_DATA.remove(assistant)
        # Bağlı maşınlardan kənarlaşdır
        for car in CARS_DATA:
            if car.get('assistant_id') == aid:
                car['assistant_id'] = None
    return redirect(url_for('admin_assistants'))

# Planlamaçı idarəetməsi
@app.route('/admin/planners')
def admin_planners():
    if not is_operator(): return redirect(url_for('index'))
    return render_template('admin_planners.html', planners=PLANNERS_DATA)

@app.route('/admin/planners/add', methods=['POST'])
def add_planner():
    if not is_operator(): return redirect(url_for('index'))
    name = request.form['name'].strip()
    if name:
        new_id = _next_id(PLANNERS_DATA, 301)
        PLANNERS_DATA.append({"id": new_id, "name": name})
    return redirect(url_for('admin_planners'))

@app.route('/admin/planner/edit/<int:pid>', methods=['GET', 'POST'])
def edit_planner(pid):
    if not is_operator(): return redirect(url_for('index'))
    planner = get_planner_by_id(pid)
    if not planner: return redirect(url_for('admin_planners'))
    if request.method == 'POST':
        planner['name'] = request.form['name'].strip()
        return redirect(url_for('admin_planners'))
    return render_template('edit_planner.html', planner=planner)

@app.route('/admin/planner/delete/<int:pid>', methods=['POST'])
def delete_planner(pid):
    if not is_operator(): return redirect(url_for('index'))
    planner = get_planner_by_id(pid)
    if planner:
        PLANNERS_DATA.remove(planner)
        for car in CARS_DATA:
            if car.get('planner_id') == pid:
                car['planner_id'] = None
    return redirect(url_for('admin_planners'))

# --- Mövcud operator səhifələri (sürücü/avto redaktə) ---
@app.route('/admin/drivers/add', methods=['POST'])
def add_driver():
    if not is_operator(): return redirect(url_for('index'))
    name = request.form['name']; license_no = request.form['license_no']; phone = request.form['phone']
    new_id = _next_id(DRIVERS_DATA, 101)
    DRIVERS_DATA.append({"id": new_id, "name": name, "license_no": license_no, "phone": phone})
    return redirect(url_for('admin_drivers'))

@app.route('/admin/cars/add', methods=['POST'])
def add_car():
    if not is_operator():
        return redirect(url_for('index'))
    car_number = request.form['car_number']
    model = request.form['model']
    driver_id = int(request.form['driver_id']) if request.form.get('driver_id') else None
    assistant_id = int(request.form['assistant_id']) if request.form.get('assistant_id') else None
    planner_id = int(request.form['planner_id']) if request.form.get('planner_id') else None

    new_id = max([c['id'] for c in CARS_DATA]) + 1 if CARS_DATA else 1
    CARS_DATA.append({
        "id": new_id,
        "driver_id": driver_id,
        "assistant_id": assistant_id,
        "planner_id": planner_id,
        "car_number": car_number,
        "model": model,
        "brand": "", "model_name": "", "category": "",
        "notes": ""
    })
    return redirect(url_for('admin_cars'))


@app.route('/admin/driver/delete/<int:id>', methods=['POST'])
def delete_driver(id):
    if not is_operator(): return redirect(url_for('index'))
    driver = get_driver_by_id(id)
    if driver:
        DRIVERS_DATA.remove(driver)
        for car in CARS_DATA:
            if car['driver_id'] == id: car['driver_id'] = None
    return redirect(url_for('admin_drivers'))

@app.route('/admin/car/delete/<int:id>', methods=['POST'])
def delete_car(id):
    if not is_operator(): return redirect(url_for('index'))
    car = get_car_by_id(id)
    if car:
        CARS_DATA.remove(car)
        global EXPENSES
        EXPENSES = [e for e in EXPENSES if e['car_id'] != id]
    if 'admin/cars' in request.referrer:
        return redirect(url_for('admin_cars'))
    return redirect(url_for('index'))

@app.route('/admin/driver/edit/<int:id>', methods=['GET', 'POST'])
def edit_driver(id):
    if not is_operator(): return redirect(url_for('index'))
    driver = get_driver_by_id(id)
    if not driver: return redirect(url_for('admin_drivers'))
    if request.method == 'POST':
        driver['name'] = request.form['name']
        driver['license_no'] = request.form['license_no']
        driver['phone'] = request.form['phone']
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
        if 'admin/cars' in request.referrer:
             return redirect(url_for('admin_cars'))
        return redirect(url_for('index'))
    return render_template('edit_car.html', car=car, drivers=DRIVERS_DATA)

# ----------------------------------------------------
# 7. YALNIZ ADMİN FUNKSİYALARI (İstifadəçi idarəetməsi)
# ----------------------------------------------------
@app.route('/admin/users')
def admin_users():
    if not is_admin(): return redirect(url_for('index'))
    users_list = [user for user in USERS if user['role'] != 'admin']
    return render_template('admin_users.html', users=users_list)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    global next_user_id
    if not is_admin(): return redirect(url_for('index'))
    fullname = request.form['fullname']; username = request.form['username']; password = request.form['password']; role = request.form['role']
    if get_user_by_username(username):
        flash('Bu istifadəçi adı artıq mövcuddur!', 'danger')
        return redirect(url_for('admin_users'))
    USERS.append({"id": next_user_id, "fullname": fullname, "username": username, "password": password, "role": role})
    next_user_id += 1
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
        user['fullname'] = request.form['fullname']; user['username'] = new_username; user['role'] = request.form['role']
        new_password = request.form.get('password')
        if new_password: user['password'] = new_password
        return redirect(url_for('admin_users'))
    return render_template('edit_user.html', user=user)

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
def delete_user(id):
    if not is_admin(): return redirect(url_for('index'))
    user = get_user_by_id(id)
    if user and user['role'] != 'admin':
        USERS.remove(user)
    return redirect(url_for('admin_users'))

# ----------------------------------------------------
# 8. HESABATLAR
# ----------------------------------------------------
@app.route('/admin/reports', methods=['GET'])
def admin_reports():
    if not is_admin(): return redirect(url_for('index'))
    f_driver_id = request.args.get('driver_id', default=None, type=int)
    f_car_id = request.args.get('car_id', default=None, type=int)
    f_user_username = request.args.get('user_username', default=None, type=str)
    f_start_date_str = request.args.get('start_date', default=None, type=str)
    f_end_date_str = request.args.get('end_date', default=None, type=str)

    all_expenses_enriched = []
    for expense in EXPENSES:
        car = get_car_by_id(expense['car_id'])
        driver = get_driver_by_id(car['driver_id']) if car else None
        user = get_user_by_username(expense['entered_by'])
        if user and user['role'] == 'user':
            all_expenses_enriched.append({"expense": expense, "car": car, "driver": driver, "user": user})

    filtered_expenses = all_expenses_enriched
    if f_driver_id:
        filtered_expenses = [e for e in filtered_expenses if e['driver'] and e['driver']['id'] == f_driver_id]
    if f_car_id:
        filtered_expenses = [e for e in filtered_expenses if e['car'] and e['car']['id'] == f_car_id]
    if f_user_username:
        filtered_expenses = [e for e in filtered_expenses if e['user'] and e['user']['username'] == f_user_username]

    if f_start_date_str:
        try:
            start_date = datetime.strptime(f_start_date_str, '%Y-%m-%d').date()
            filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() >= start_date]
        except ValueError:
            flash("Başlanğıc tarix formatı yanlışdır.", "warning")

    if f_end_date_str:
        try:
            end_date = datetime.strptime(f_end_date_str, '%Y-%m-%d').date()
            filtered_expenses = [e for e in filtered_expenses if e['expense']['timestamp'].date() <= end_date]
        except ValueError:
            flash("Bitmə tarix formatı yanlışdır.", "warning")

    total_amount = sum(e['expense']['amount'] for e in filtered_expenses)
    operators = [user for user in USERS if user['role'] == 'user']
    return render_template(
        'admin_reports.html',
        reports=sorted(filtered_expenses, key=lambda x: x['expense']['timestamp'], reverse=True),
        total_amount=total_amount,
        drivers=DRIVERS_DATA, cars=CARS_DATA, operators=operators,
        selected_filters={'driver_id': f_driver_id,'car_id': f_car_id,'user_username': f_user_username,'start_date': f_start_date_str,'end_date': f_end_date_str}
    )

# ----------------------------------------------------
# 9. TƏTBİQİ BAŞLATMA
# ----------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
