import pymysql

def get_connection():
    connection = pymysql.connect(
        host='localhost',
        user='asis_app',
        password='GarajPro2025!',
        database='asis_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection