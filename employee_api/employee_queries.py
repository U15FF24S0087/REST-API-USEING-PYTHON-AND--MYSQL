# employee_queries.py
# Responsibility: All SQL queries for the employees table.
# main.py imports these functions and calls them.
# This file never handles HTTP — only database logic.

from database import get_connection   # our connection function from Stage 2
import mysql.connector                # to catch DB-specific errors


# ─────────────────────────────────────────────
# CREATE — Insert a new employee
# ─────────────────────────────────────────────

def add_employee(name, email, department, salary):
    """
    Inserts one new employee row into the employees table.

    Args:
        name       (str)   : employee full name
        email      (str)   : unique email address
        department (str)   : department name
        salary     (float) : monthly salary

    Returns:
        dict with the new employee's auto-generated id

    Raises:
        ValueError  — if the email already exists (duplicate)
        Exception   — for any other database error
    """

    # The SQL query uses %s as placeholders — NEVER use f-strings for SQL.
    # f-strings open the door to SQL injection attacks.
    # mysql.connector replaces %s safely with the values tuple.
    sql = """
        INSERT INTO employees (name, email, department, salary)
        VALUES (%s, %s, %s, %s)
    """

    # Pack the values into a tuple — order must match the %s placeholders
    values = (name, email, department, salary)

    connection = None

    try:
        connection = get_connection()

        # cursor() opens a query channel on this connection
        cursor = connection.cursor()

        # execute() sends the SQL + values to MySQL
        cursor.execute(sql, values)

        # commit() saves the INSERT permanently.
        # Without commit(), the row is written temporarily but rolled back
        # when the connection closes.
        connection.commit()

        # cursor.lastrowid gives us the AUTO_INCREMENT id MySQL assigned
        new_id = cursor.lastrowid
        cursor.close()

        return {"id": new_id, "message": "Employee added successfully"}

    except mysql.connector.IntegrityError as error:
        # IntegrityError is raised when a UNIQUE constraint is violated.
        # In our case: duplicate email address.
        # Error code 1062 is MySQL's "Duplicate entry" code.
        if error.errno == 1062:
            raise ValueError(f"Email '{email}' already exists.")
        raise Exception(f"Database integrity error: {error}")

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ─────────────────────────────────────────────
# READ ALL — Get every employee
# ─────────────────────────────────────────────

def get_all_employees():
    """
    Fetches every row from the employees table.

    Returns:
        list of dicts — one dict per employee row
        Empty list [] if no employees exist yet.
    """

    sql = "SELECT id, name, email, department, salary FROM employees ORDER BY id"

    connection = None

    try:
        connection = get_connection()

        # cursor(dictionary=True) makes fetchall() return
        # a list of dicts like {"id": 1, "name": "Alice"} instead of tuples.
        # Dicts are much easier to work with than positional tuples.
        cursor = connection.cursor(dictionary=True)

        cursor.execute(sql)

        # fetchall() retrieves every row at once as a list
        employees = cursor.fetchall()
        cursor.close()

        # Convert salary (Decimal type from MySQL) to float for JSON serialization
        for emp in employees:
            emp["salary"] = float(emp["salary"])

        return employees

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ─────────────────────────────────────────────
# READ ONE — Get a single employee by ID
# ─────────────────────────────────────────────

def get_employee_by_id(employee_id):
    """
    Fetches one employee row by primary key.

    Args:
        employee_id (int): the employee's id

    Returns:
        dict — the employee's data
        None — if no employee with that id exists
    """

    sql = "SELECT id, name, email, department, salary FROM employees WHERE id = %s"

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Pass employee_id as a tuple — even for a single value
        # (employee_id,) is a one-element tuple in Python
        cursor.execute(sql, (employee_id,))

        # fetchone() returns one row dict, or None if not found
        employee = cursor.fetchone()
        cursor.close()

        if employee:
            employee["salary"] = float(employee["salary"])

        return employee  # could be None — the caller checks for this

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ─────────────────────────────────────────────
# UPDATE — Modify an existing employee
# ─────────────────────────────────────────────

def update_employee(employee_id, name, email, department, salary):
    """
    Updates all fields of an existing employee row.

    Args:
        employee_id (int)  : which employee to update
        name        (str)  : new name
        email       (str)  : new email (must still be unique)
        department  (str)  : new department
        salary      (float): new salary

    Returns:
        dict with success message
        None if no employee with that id was found

    Raises:
        ValueError  — if the new email conflicts with another employee
        Exception   — for other database errors
    """

    sql = """
        UPDATE employees
        SET name = %s, email = %s, department = %s, salary = %s
        WHERE id = %s
    """

    # Note: id goes at the END because it matches the WHERE clause %s
    values = (name, email, department, salary, employee_id)

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(sql, values)
        connection.commit()

        # cursor.rowcount tells us how many rows were actually changed.
        # If it's 0, no row had that id — the employee doesn't exist.
        if cursor.rowcount == 0:
            cursor.close()
            return None  # caller will raise 404

        cursor.close()
        return {"message": f"Employee {employee_id} updated successfully"}

    except mysql.connector.IntegrityError as error:
        if error.errno == 1062:
            raise ValueError(f"Email '{email}' is already used by another employee.")
        raise Exception(f"Database integrity error: {error}")

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ─────────────────────────────────────────────
# DELETE — Remove an employee
# ─────────────────────────────────────────────

def delete_employee(employee_id):
    """
    Deletes one employee row by primary key.

    Args:
        employee_id (int): which employee to delete

    Returns:
        dict with success message
        None if no employee with that id was found
    """

    sql = "DELETE FROM employees WHERE id = %s"

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(sql, (employee_id,))
        connection.commit()

        if cursor.rowcount == 0:
            cursor.close()
            return None  # employee not found

        cursor.close()
        return {"message": f"Employee {employee_id} deleted successfully"}

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ─────────────────────────────────────────────
# SEARCH — Find employees by name or department
# ─────────────────────────────────────────────

def search_employees(keyword):
    """
    Searches employees whose name OR department contains the keyword.
    Case-insensitive because LIKE in MySQL is case-insensitive by default.

    Args:
        keyword (str): search term, e.g. "Alice" or "Engineering"

    Returns:
        list of matching employee dicts (empty list if no matches)
    """

    # The % around the keyword is SQL wildcard syntax:
    # LIKE '%eng%' matches "Engineering", "frontend", "Senior Eng", etc.
    sql = """
        SELECT id, name, email, department, salary
        FROM employees
        WHERE name LIKE %s OR department LIKE %s
        ORDER BY name
    """

    # We build the wildcard pattern in Python, not in SQL
    pattern = f"%{keyword}%"

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Pass the pattern twice — once for name, once for department
        cursor.execute(sql, (pattern, pattern))
        results = cursor.fetchall()
        cursor.close()

        for emp in results:
            emp["salary"] = float(emp["salary"])

        return results

    except mysql.connector.Error as error:
        raise Exception(f"Database error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()
