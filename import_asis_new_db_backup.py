import getpass
from pathlib import Path
import pymysql
from pymysql.constants import CLIENT

SQL_FILE = Path(__file__).with_name("asis_new_db_import_from_backup.sql")
ROOT_USER = "root"
APP_USER = "asis_app"
APP_PASSWORD = "GarajPro2025!"
DB_NAME = "asis_new_db"

if not SQL_FILE.exists():
    raise SystemExit(f"SQL faylı tapılmadı: {SQL_FILE}")

root_password = getpass.getpass("MySQL root parolunu yaz: ")

print("1/3 Root ilə qoşuluram və baza/user hazırlayıram...")
root_conn = pymysql.connect(
    host="localhost",
    user=ROOT_USER,
    password=root_password,
    charset="utf8mb4",
    autocommit=True,
)
with root_conn.cursor() as cur:
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}'")
    cur.execute(f"ALTER USER '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}'")
    cur.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{APP_USER}'@'localhost'")
    cur.execute("FLUSH PRIVILEGES")
root_conn.close()

print("2/3 SQL backup asis_new_db bazasına import olunur...")
sql = SQL_FILE.read_text(encoding="utf-8-sig")
conn = pymysql.connect(
    host="localhost",
    user=ROOT_USER,
    password=root_password,
    charset="utf8mb4",
    autocommit=True,
    client_flag=CLIENT.MULTI_STATEMENTS,
)
with conn.cursor() as cur:
    cur.execute(sql)
    while cur.nextset():
        pass
conn.close()

print("3/3 Yoxlama edilir...")
app_conn = pymysql.connect(
    host="localhost",
    user=APP_USER,
    password=APP_PASSWORD,
    database=DB_NAME,
    charset="utf8mb4",
    autocommit=True,
)
with app_conn.cursor() as cur:
    for table in ["users", "cars", "drivers", "assistants", "planners", "expense_types", "expenses", "audit_logs", "app_settings"]:
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cur.fetchone()[0]
        print(f"{table}: {count}")
app_conn.close()
print("OK - asis_new_db hazırdır. İndi python app.py işlədə bilərsən.")
