import sqlite3

def get_connection():
    conn = sqlite3.connect('snow-jira.db')
    return conn

def createTables(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS avit (
        id TEXT PRIMARY KEY,
        num TEXT NOT NULL,
        version TEXT NOT NULL
    )
    ''')
    conn.commit()

def dropTable(conn):
    cursor = conn.cursor()
    cursor.execute('drop TABLE IF EXISTS avit')
    conn.commit()

def insert(conn):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO avit (id, num, version) VALUES (?, ?,?)', ('DSFSDFSDFDSFDSF', 'A12324', "A001"))
    conn.commit()

def update(conn):
    cursor = conn.cursor()
    cursor.execute('UPDATE avit SET version = ? WHERE id = ?', ("v2", 'DSFSDFSDFDSFDSF'))
    conn.commit()

def query(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM avit')
    rows = cursor.fetchall()
    for row in rows:
        print(row)

dropTable(get_connection())
createTables(get_connection())
insert(get_connection())
update(get_connection())
query(get_connection())
