import pymysql

# Verilənlər bazası tənzimləmələri
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Thehardys95!',  # Parolunuzun düzgün olduğundan əmin olun
    'database': 'asis_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10
}

def get_connection():
    try:
        # MySQL serverinə qoşulmağa çalışırıq
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except pymysql.MySQLError as e:
        # Əgər xəta baş verərsə, terminalda bunu çap edirik
        print(f"\n!!! MYSQL BAĞLANTI XƏTASI !!!\nSəbəb: {e}\n")
        
        # Xətanı app.py tərəfə ötürürük ki, proqram niyə dayandığını bilsin
        # Bu sayədə 'AttributeError' əvəzinə əsl problemi görəcəksiniz
        raise e