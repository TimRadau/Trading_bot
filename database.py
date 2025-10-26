import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

# --- Verbindung zur PostgreSQL-Datenbank ---
def get_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432),
        cursor_factory=RealDictCursor
    )


# --- Setup: Tabellen anlegen ---
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            referral_code TEXT UNIQUE,
            invited_by TEXT,
            referrals_count INT DEFAULT 0,
            is_premium BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# --- Benutzer anlegen ---
def add_user(telegram_id: int, username: str, invited_by: str = None):
    conn = get_connection()
    cur = conn.cursor()
    referral_code = f"REF_{telegram_id}"
    cur.execute("""
        INSERT INTO users (telegram_id, username, referral_code, invited_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO NOTHING;
    """, (telegram_id, username, referral_code, invited_by))
    # Falls eingeladen, Zähler des Einladenden erhöhen
    if invited_by:
        cur.execute("""
            UPDATE users
            SET referrals_count = referrals_count + 1
            WHERE referral_code = %s;
        """, (invited_by,))
    conn.commit()
    cur.close()
    conn.close()

# --- Benutzer abrufen ---
def get_user(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = %s;", (telegram_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

# --- Referral Count erhöhen ---
def increment_referral(referral_code: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET referrals_count = referrals_count + 1
        WHERE referral_code = %s
        RETURNING referrals_count;
    """, (referral_code,))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result["referrals_count"] if result else 0

def get_user_by_referral(ref_code: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE referral_code = %s;", (ref_code,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# --- Premium Status setzen ---
def set_premium(telegram_id: int, status: bool):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET is_premium = %s
        WHERE telegram_id = %s;
    """, (status, telegram_id))
    conn.commit()
    cur.close()
    conn.close()


def db_select(query):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query)
    user = cur.fetchall()
    print(user)
    cur.close()
    conn.close()
    return user


db_select("Select * from users")
