import sqlite3
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            title TEXT,
            downloads INTEGER DEFAULT 0,
            added_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------- MOVIES ----------

def add_movie(code, file_id, title):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO movies (code, file_id, title, downloads, added_at) "
        "VALUES (?, ?, ?, COALESCE((SELECT downloads FROM movies WHERE code=?), 0), ?)",
        (code, file_id, title, code, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_movie(code):
    conn = get_conn()
    row = conn.execute("SELECT * FROM movies WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row


def delete_movie(code):
    conn = get_conn()
    cur = conn.execute("DELETE FROM movies WHERE code = ?", (code,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def increment_downloads(code):
    conn = get_conn()
    conn.execute("UPDATE movies SET downloads = downloads + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()


def get_top_movies(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY downloads DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_all_movies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM movies ORDER BY added_at DESC").fetchall()
    conn.close()
    return rows


def movie_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM movies").fetchone()["c"]
    conn.close()
    return n


def total_downloads():
    conn = get_conn()
    n = conn.execute("SELECT COALESCE(SUM(downloads),0) c FROM movies").fetchone()["c"]
    conn.close()
    return n


# ---------- USERS ----------

def add_user(user_id, username):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?, ?, ?)",
        (user_id, username, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def user_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    conn.close()
    return n
