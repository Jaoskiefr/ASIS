import pymysql

# Verilənlər bazası tənzimləmələri
DB_CONFIG = {
    'host': 'localhost',
    'user': 'asis_app',
    'password': 'GarajPro2025!',  # Parolunuzun düzgün olduğundan əmin olun
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
        raise e

def check_and_update_tables():
    """
    Bu funksiya tətbiq işə düşəndə cədvəlləri yoxlayır
    və 'is_deleted' və 'is_active' sütunları yoxdursa, əlavə edir.
    """
    print("Verilənlər bazası strukturu yoxlanılır...")
    conn = get_connection()
    # Yoxlanacaq cədvəllər
    tables_to_check = ['drivers', 'assistants', 'planners', 'cars']
    
    try:
        with conn.cursor() as cursor:
            for table in tables_to_check:
                # 1. is_deleted yoxlanışı
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'is_deleted'")
                if not cursor.fetchone():
                    print(f"-> '{table}' cədvəlinə 'is_deleted' sütunu əlavə edilir...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_deleted TINYINT(1) DEFAULT 0")
                
                # 2. is_active yoxlanışı (YENİ)
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'is_active'")
                if not cursor.fetchone():
                    print(f"-> '{table}' cədvəlinə 'is_active' sütunu əlavə edilir...")
                    # Default olaraq 1 (Aktiv) olsun
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_active TINYINT(1) DEFAULT 1")
                    
        conn.commit()
        print("Baza yoxlanışı tamamlandı.")
    except Exception as e:
        print(f"Baza miqrasiya xətası: {e}")
    finally:
        conn.close()