import os
import sqlite3

from werkzeug.security import generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "inventory.db")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS User (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'staff'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Product (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                min_quantity INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Inventory (
                product_id TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS StockLog (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                change_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Alert (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
            )
            """
        )

        existing_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(StockLog)").fetchall()
        }
        if "username" not in existing_columns:
            connection.execute(
                "ALTER TABLE StockLog ADD COLUMN username TEXT NOT NULL DEFAULT 'system'"
            )

        ensure_default_users(connection)
        sync_low_stock_alerts(connection)


def upsert_product(product_id: str, name: str, min_quantity: int) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO Product (product_id, name, min_quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                name = excluded.name,
                min_quantity = excluded.min_quantity
            """,
            (product_id, name, min_quantity),
        )
        connection.execute(
            """
            INSERT INTO Inventory (product_id, quantity)
            VALUES (?, 0)
            ON CONFLICT(product_id) DO NOTHING
            """,
            (product_id,),
        )


def get_product(product_id: str):
    with connect() as connection:
        row = connection.execute(
            "SELECT product_id, name, min_quantity FROM Product WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


def list_inventory():
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.min_quantity,
                COALESCE(i.quantity, 0) AS quantity
            FROM Product p
            LEFT JOIN Inventory i ON i.product_id = p.product_id
            ORDER BY p.name COLLATE NOCASE ASC, p.product_id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_inventory_item(product_id: str):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.min_quantity,
                COALESCE(i.quantity, 0) AS quantity
            FROM Product p
            LEFT JOIN Inventory i ON i.product_id = p.product_id
            WHERE p.product_id = ?
            """,
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


def set_inventory_quantity(product_id: str, quantity: int) -> int:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO Inventory (product_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(product_id) DO UPDATE SET quantity = excluded.quantity
            """,
            (product_id, quantity),
        )
    return quantity


def ensure_default_users(connection: sqlite3.Connection) -> None:
    default_users = [
        ("admin", "admin123", "admin"),
        ("staff", "staff123", "staff"),
    ]

    for username, password, role in default_users:
        exists = connection.execute(
            "SELECT 1 FROM User WHERE username = ?",
            (username,),
        ).fetchone()
        if not exists:
            connection.execute(
                """
                INSERT INTO User (username, password_hash, role)
                VALUES (?, ?, ?)
                """,
                (username, generate_password_hash(password), role),
            )


def get_user(username: str):
    with connect() as connection:
        row = connection.execute(
            "SELECT username, password_hash, role FROM User WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def add_stock_log(product_id: str, change_type: str, quantity: int, username: str = "system") -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO StockLog (product_id, change_type, quantity, username)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, change_type, quantity, username or "system"),
        )


def add_alert(product_id: str, message: str) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO Alert (product_id, message)
            VALUES (?, ?)
            """,
            (product_id, message),
        )


def list_low_stock_products():
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.min_quantity,
                COALESCE(i.quantity, 0) AS quantity
            FROM Product p
            LEFT JOIN Inventory i ON i.product_id = p.product_id
            WHERE COALESCE(i.quantity, 0) < p.min_quantity
            ORDER BY p.name COLLATE NOCASE ASC, p.product_id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def sync_low_stock_alerts(connection: sqlite3.Connection | None = None) -> None:
    owns_connection = connection is None
    active_connection = connection or connect()

    try:
        low_stock_rows = active_connection.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.min_quantity,
                COALESCE(i.quantity, 0) AS quantity
            FROM Product p
            LEFT JOIN Inventory i ON i.product_id = p.product_id
            WHERE COALESCE(i.quantity, 0) < p.min_quantity
            ORDER BY p.name COLLATE NOCASE ASC, p.product_id ASC
            """
        ).fetchall()

        active_connection.execute("DELETE FROM Alert")
        for row in low_stock_rows:
            active_connection.execute(
                """
                INSERT INTO Alert (product_id, message)
                VALUES (?, ?)
                """,
                (
                    row["product_id"],
                    f"{row['name']}의 재고가 부족합니다. 현재 {row['quantity']}, 기준 {row['min_quantity']}",
                ),
            )
    finally:
        if owns_connection:
            active_connection.close()


def list_logs(limit: int = 100):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT log_id, product_id, change_type, quantity, username, created_at
            FROM StockLog
            ORDER BY log_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_alerts(limit: int = 100):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT alert_id, product_id, message, created_at
            FROM Alert
            ORDER BY alert_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]