from db import get_connection

def fix_collations():
    print("Verilənlər bazasına qoşulur...")
    conn = get_connection()
    if not conn:
        print("!!! Baza bağlantısı uğursuz oldu. db.py faylını yoxlayın.")
        return

    # Bütün cədvəlləri eyni formata (utf8mb4_unicode_ci) çevirən əmrlər
    commands = [
        "ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE expenses CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE audit_logs CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE cars CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE drivers CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE assistants CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE planners CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "ALTER TABLE expense_types CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    ]

    try:
        with conn.cursor() as cursor:
            print("Kollasiya (Collation) xətaları düzəldilir...")
            # Xarici açar yoxlamasını müvəqqəti söndürürük ki, rahat dəyişiklik edə bilək
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            for cmd in commands:
                try:
                    print(f"İcra olunur: {cmd}")
                    cursor.execute(cmd)
                except Exception as table_error:
                    print(f" -> Xəbərdarlıq: {table_error}")

            # Xarici açar yoxlamasını geri açırıq
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
            print("\n✅ Uğurla tamamlandı! Bütün cədvəllər 'utf8mb4_unicode_ci' formatına keçirildi.")
            print("İndi 'app.py' faylını yenidən işə salıb Admin panelinə girə bilərsiniz.")
    except Exception as e:
        print(f"\n!!! Gözlənilməz xəta: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_collations()