import pymysql

def get_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Thehardys95!',
        database='asis_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection
