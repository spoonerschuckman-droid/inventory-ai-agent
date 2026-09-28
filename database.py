import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "inventory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def insert_record(material, type, quantity, unit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inventory_records
        (material, type, quantity, unit)
        VALUES (?, ?, ?, ?)
    """, (material, type, quantity, unit))

    conn.commit()
    conn.close()


def fetch_records():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, material, type, quantity, unit
        FROM inventory_records
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def fetch_records_by_material(material, unit):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, material, type, quantity, unit
        FROM inventory_records
        WHERE material = ? AND unit = ?
    """, (material, unit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def delete_record(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM inventory_records WHERE id = ?",
        (record_id,)
    )

    conn.commit()
    conn.close()


def clear_records():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM inventory_records")

    conn.commit()
    conn.close()


init_db()