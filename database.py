import sqlite3
from datetime import datetime, timedelta

DB_PATH = "volgograd_fuel.db"


def init_db():
    """Создаёт таблицы, если их ещё нет"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station TEXT NOT NULL,
            address TEXT,
            fuel_type TEXT NOT NULL,
            price REAL,
            available INTEGER DEFAULT 1,
            user_id INTEGER,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fuel_type ON reports(fuel_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON reports(created_at)")
    conn.commit()
    conn.close()
    print("✅ База готова")


def add_report(station, fuel_type, price=None, address=None,
               available=1, user_id=None, username="anon"):
    """Добавляет новый отчёт о топливе"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports
        (station, fuel_type, price, address, available, user_id, username)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (station, fuel_type, price, address, available, user_id, username))
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def get_fuel(fuel_type, hours=24, only_available=True):
    """Получает данные по типу топлива"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    since = datetime.now() - timedelta(hours=hours)
    if only_available:
        cur.execute("""
            SELECT station, address, fuel_type, price, username, created_at
            FROM reports
            WHERE fuel_type = ? AND available = 1 AND created_at > ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (fuel_type, since))
    else:
        cur.execute("""
            SELECT station, address, fuel_type, price, available, username, created_at
            FROM reports
            WHERE fuel_type = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (fuel_type, since))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_recent(hours=24):
    """Все отчёты за период"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    since = datetime.now() - timedelta(hours=hours)
    cur.execute("""
        SELECT station, address, fuel_type, price, available, username, created_at
        FROM reports
        WHERE created_at > ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (since,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_stats():
    """Базовая статистика"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reports")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT username) FROM reports WHERE username IS NOT NULL")
    users = cur.fetchone()[0]
    cur.execute("SELECT MAX(created_at) FROM reports")
    last = cur.fetchone()[0]
    conn.close()
    return {"total": total, "users": users, "last": last}


if __name__ == "__main__":
    init_db()
