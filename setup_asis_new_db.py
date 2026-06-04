import pymysql

ROOT_PASSWORD = "Thehardys95!"
APP_USER = "asis_app"
APP_PASSWORD = "GarajPro2025!"
DB_NAME = "asis_new_db"

conn = pymysql.connect(
    host="localhost",
    user="root",
    password=ROOT_PASSWORD,
    charset="utf8mb4",
    autocommit=True
)

with conn.cursor() as cur:
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}'")
    cur.execute(f"ALTER USER '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}'")
    cur.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{APP_USER}'@'localhost'")
    cur.execute("FLUSH PRIVILEGES")

conn.close()
print("OK - asis_new_db yaradıldı və asis_app icazəsi verildi.")
