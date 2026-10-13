# database.py
# Responsibility: Open and close the MySQL connection.
# Also auto-creates the database and employees table if they don't exist.
# Every other file imports get_connection() from here.

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Opens and returns a MySQL connection to employee_db.
    """
    connection = mysql.connector.connect(
        host     = os.getenv("DB_HOST"),
        port     = int(os.getenv("DB_PORT")),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        database = os.getenv("DB_NAME")
    )
    return connection


def _get_root_connection():
    """
    Opens a connection WITHOUT specifying a database.
    Used only during setup — so we can create the database itself.
    """
    connection = mysql.connector.connect(
        host     = os.getenv("DB_HOST"),
        port     = int(os.getenv("DB_PORT")),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD")
        # No 'database' key here — we haven't created it yet
    )
    return connection


def initialize_database():
    """
    Automatically creates the database and employees table if they don't exist.
    Called once when the application starts (from main.py startup event).

    Steps:
      1. Connect without selecting a database
      2. CREATE DATABASE IF NOT EXISTS employee_db
      3. Switch to employee_db
      4. CREATE TABLE IF NOT EXISTS employees (...)
    """

    connection = None

    try:
        # Connect without a database — because it may not exist yet
        connection = _get_root_connection()
        cursor = connection.cursor()

        db_name = os.getenv("DB_NAME")  # "employee_db"

        # CREATE DATABASE IF NOT EXISTS — safe to run even if DB already exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"[DB] Database '{db_name}' is ready.")

        # Switch into that database
        cursor.execute(f"USE {db_name}")

        # CREATE TABLE IF NOT EXISTS — safe to run even if table already exists
        # This is the exact same schema we designed in Stage 1
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS employees (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                name        VARCHAR(100)   NOT NULL,
                email       VARCHAR(150)   NOT NULL UNIQUE,
                department  VARCHAR(100)   NOT NULL,
                salary      DECIMAL(10, 2) NOT NULL,
                created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
            )
        """

        cursor.execute(create_table_sql)
        print("[DB] Table 'employees' is ready.")

        cursor.close()

    except mysql.connector.Error as error:
        # If this fails, print the error clearly so the developer can fix it
        print(f"[DB] Initialization failed: {error}")
        raise  # re-raise so FastAPI startup also fails loudly

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def test_connection():
    """
    Diagnostic function — run this file directly to check connectivity.
    Usage: python database.py
    """
    connection = None
    try:
        connection = get_connection()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            print(f"Connected successfully!")
            print(f"MySQL version : {version[0]}")
            print(f"Database      : {current_db[0]}")
            cursor.close()

    except mysql.connector.Error as error:
        print(f"Connection failed: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()
            print("Connection closed.")


if __name__ == "__main__":
    initialize_database()
    test_connection()
