"""Database initialisation and connection helper."""

import sqlite3
from flask import g
import os

DATABASE = "finance.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id),
    type     TEXT NOT NULL CHECK(type IN ('income','expense')),
    category TEXT NOT NULL,
    amount   REAL NOT NULL,
    note     TEXT,
    date     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    category      TEXT NOT NULL,
    monthly_limit REAL NOT NULL,
    UNIQUE(user_id, category)
);
"""

# Seed data is inserted for user_id=1 (created at runtime if DB is fresh)
SEED_TRANSACTIONS = """
INSERT OR IGNORE INTO transactions (user_id, type, category, amount, note, date) VALUES
  (1, 'income',  'Salary',        45000, 'Monthly salary',      date('now', '-5 days')),
  (1, 'expense', 'Rent',          12000, 'Monthly rent',        date('now', '-4 days')),
  (1, 'expense', 'Groceries',      2400, 'Supermarket',         date('now', '-3 days')),
  (1, 'expense', 'Transport',       800, 'Cab & bus',           date('now', '-2 days')),
  (1, 'income',  'Freelance',      8000, 'Web project payment', date('now', '-1 days')),
  (1, 'expense', 'Entertainment',  1200, 'Movies & dining',     date('now'));
"""

SEED_BUDGETS = """
INSERT OR IGNORE INTO budgets (user_id, category, monthly_limit) VALUES
  (1, 'Groceries',     5000),
  (1, 'Entertainment', 2000),
  (1, 'Transport',     1500);
"""


def init_db():
    fresh = not os.path.exists(DATABASE)
    conn  = sqlite3.connect(DATABASE)
    conn.executescript(SCHEMA)

    if fresh:
        # Create a demo account (username: demo, password: demo123)
        import hashlib
        pw_hash = hashlib.sha256("demo123".encode()).hexdigest()
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
            ("demo", pw_hash)
        )
        conn.commit()
        conn.executescript(SEED_TRANSACTIONS)
        conn.executescript(SEED_BUDGETS)
        conn.commit()
        print("[DB] Database initialised. Demo account → username: demo  password: demo123")

    conn.commit()
    conn.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
