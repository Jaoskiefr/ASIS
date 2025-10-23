from flask import Flask, render_template, request, redirect, url_for, session

# ----------------------------------------------------
# 1. FLASK TƏTBİQİNİN QURULMASI
# ----------------------------------------------------
app = Flask(__name__)
# Təhlükəsizlik üçün gizli açar (Çox vacibdir!)
app.secret_key = 'ASIS_Sizin_Real_Gizli_Acariniz_Burada_Olsun' 

# ----------------------------------------------------
# 2. MƏLUMAT BAZASININ TƏQLİDİ (REAL DB ƏVƏZİ)
# Qeyd: Real layihədə bu məlumatlar PostgreSQL/MySQL-də saxlanılmalıdır.
# ----------------------------------------------------

# İstifadəçilər (Rol əsaslı giriş üçün)
USERS = {
    "admin": {"password": "adminpass", "role": "admin"},
    "operator": {"password": "operpass", "role": "user"}
}

# Sürücü Məlumatları
DRIVERS_DATA = [
    {"id": 101, "name": "Cavid Məmmədov Əli oğlu", "license_no": "AZE12345", "phone": "050-111-22-33"},
    {"id": 102, "name": "Nigar Əliyeva Zaur qızı", "license_no": "AZE67890", "phone": "051-444-55-66"},
    {"id": 103, "name": "Rəşad Həsənov Samir oğlu", "license_no": "AZE10111", "phone": "055-777-88-99"},
]

# Avtomobil Məlumatları (Sürücülərə Təyin Edilib)
CARS_DATA = [
    {"id": 1, "driver_id": 101, "car_number": "99-XX-001", "model": "Toyota Prius", "year": 2020},
    {"id": 2, "driver_id": 102, "car_number": "90-ZZ-999", "model": "Kia Optima", "year": 2022},
    {"id": 3, "driver_id": None, "car_number": "10-RA-321", "model": "Ford Transit", "year": 2018}, # Təyin olunmayıb
]
next_car_id = 4 # Yeni avtomobil əlavə etmək üçün sayğac

# Xərc/Yanacaq Məlumatları
EXPENSES = [
    {"car_id": 1, "amount": 85.50, "type": "Yanacaq", "description": "15L benzin", "entered_by": "operator"},
    {"car_id": 2, "amount": 40.00, "type": "Xərc", "description": "Yuma xərci", "entered_by": "admin"},
    {"car_id": 1, "amount": 250.00, "type": "Xərc", "description": "Yağ dəyişimi", "entered_by": "operator"},
]

# ----------------------------------------------------
# 3. KÖMƏKÇİ FUNKSİYALAR
# ----------------------------------------------------

def get_car_by_id(car_id):
    """ID ilə avtomobili tapır."""
    # car_id tipini int-ə çevirmək lazımdır, çünki formalardan string gələ bilər
    car_id = int(car_id) if car_id else None 
    return next((car for car in CARS_DATA if car['id'] == car_id), None)

def get_driver_by_id(driver_id):
    """ID ilə sürücünü tapır."""
    driver_id = int(driver_id) if driver_id else None
    return next((driver for driver in DRIVERS_DATA if driver['id'] == driver_id), None)

def get_dashboard_data():
    """Əsas cədvəl üçün Avtomobil, Sürücü və Xərc məlumatlarını birləşdirir."""
    full_data = []
    
    for car in CARS_DATA:
        driver = get_driver_by_id(car['driver_id'])
        
        # Həmin avtomobilə aid olan bütün xərcləri tapın
        car_expenses = [e for e in EXPENSES if e['car_id'] == car['id']]
        
        # Ümumi xərc məbləğini hesablayın (Son xərci yox, bütün xərclərin cəmini göstəririk)
        total_expense = sum(e['amount'] for e in car_expenses)
        
        # Son xərci daxil edən əməkdaşı tapın
        last_expense_entered_by = car_expenses[-1]['entered_by'] if car_expenses else "Yoxdur"

        # Cədvəl üçün sətir hazırlayın
        full_data.append({
            "id": car['id'],
            "car_number": car['car_number'],
            "driver_name": driver['name'] if driver else "TƏYİN OLUNMAYIB",
            "model": f"{car['model']} ({car['year']})", # Model və ili birləşdirdik
            "total_expense": total_expense, 
            "entered_by": last_expense_entered_by, 
            "notes": car['notes'] if 'notes' in car else "" # Əgər qeyd sahəsi varsa
        })
    return full_data

# ----------------------------------------------------
# 4. ƏSAS MARŞRUTLAR (Routes)
# ----------------------------------------------------

@app.route('/')
def index():
    """Əsas səhifəni (Dashboard) göstərir."""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    dashboard_data = get_dashboard_data()
    return render_template('dashboard.html', user_role=session['role'], cars=dashboard_data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """İstifadəçinin girişini idarə edir."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in USERS and USERS[username]['password'] == password:
            session['user'] = username
            session['role'] = USERS[username]['role']
            return redirect(url_for('index'))
        else:
            error = 'Yanlış istifadəçi adı və ya parol.'
            return render_template('login.html', error=error)
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """İstifadəçini sistemdən çıxarır."""
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/add_expense', methods=['POST'])
def add_expense():
    """Yanacaq və ya Xərc məlumatlarını qəbul edir və saxlayır (Operator funksiyası)."""
    if session.get('role') not in ['user', 'admin']: # Admin də xərc əlavə edə bilər
        return redirect(url_for('login'))
        
    car_id = request.form.get('car_id')
    expense_type = request.form.get('expense_type')
    amount = request.form.get('amount')
    litr = request.form.get('litr', 0)
    description = request.form.get('description')
    
    # Məlumat bazasına yazmaq (Təqlid)
    new_expense = {
        "car_id": int(car_id),
        "type": expense_type,
        "amount": float(amount),
        "litr": float(litr) if litr else 0.0,
        "description": description,
        "entered_by": session['user']
    }
    EXPENSES.append(new_expense)
    
    return redirect(url_for('index'))

# ----------------------------------------------------
# 5. ADMIN İDARƏETMƏSİ MARŞRUTLARI (CRUD)
# ----------------------------------------------------

def is_admin():
    """Admin rolunu yoxlayır və deyilsə ana səhifəyə yönləndirir."""
    if session.get('role') != 'admin':
        return False
    return True

@app.route('/admin/drivers')
def admin_drivers():
    """Admin: Sürücü əlavə et, sil, redaktə et səhifəsi."""
    if not is_admin():
        return redirect(url_for('index'))
    return render_template('admin_drivers.html', drivers=DRIVERS_DATA)

@app.route('/admin/cars')
def admin_cars():
    """Admin: Avtomobil əlavə et, sil, redaktə et səhifəsi."""
    if not is_admin():
        return redirect(url_for('index'))
    # Avtomobil əlavə edərkən sürücü siyahısı lazımdır
    return render_template('admin_cars.html', cars=CARS_DATA, drivers=DRIVERS_DATA) 

@app.route('/admin/drivers/add', methods=['POST'])
def add_driver():
    """Admin: Yeni sürücü əlavə edir."""
    global next_driver_id
    if not is_admin():
        return redirect(url_for('index'))

    # Formalı məlumatları götür
    name = request.form['name']
    license_no = request.form['license_no']
    phone = request.form['phone']
    
    # Yeni ID təyin et (Hər dəfə 1 artırırıq)
    new_id = max([d['id'] for d in DRIVERS_DATA]) + 1 if DRIVERS_DATA else 101
    
    new_driver = {
        "id": new_id, 
        "name": name, 
        "license_no": license_no, 
        "phone": phone
    }
    DRIVERS_DATA.append(new_driver)
    
    return redirect(url_for('admin_drivers'))


@app.route('/admin/cars/add', methods=['POST'])
def add_car():
    """Admin: Yeni avtomobil əlavə edir."""
    if not is_admin():
        return redirect(url_for('index'))

    # Formalı məlumatları götür
    car_number = request.form['car_number']
    model = request.form['model']
    year = int(request.form['year'])
    # Sürücü ID-si boş gələrsə None olsun
    driver_id = int(request.form['driver_id']) if request.form['driver_id'] else None 
    
    # Yeni ID təyin et
    new_id = max([c['id'] for c in CARS_DATA]) + 1 if CARS_DATA else 1
    
    new_car = {
        "id": new_id, 
        "driver_id": driver_id, 
        "car_number": car_number, 
        "model": model, 
        "year": year
    }
    CARS_DATA.append(new_car)
    
    return redirect(url_for('admin_cars'))

# Qeyd: Redaktə və Silmə (Update, Delete) funksiyaları bu nümunəyə daxil edilməyib, lakin oxşar prinsiplə qurulur.

# ----------------------------------------------------
# 6. TƏTBİQİ BAŞLATMA
# ----------------------------------------------------
if __name__ == '__main__':
    # Flask tətbiqini işə sal
    app.run(debug=True)