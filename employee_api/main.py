# main.py
# Entry point of the FastAPI application.
# Defines ALL API routes — employee CRUD + file operations.
# All business logic lives in employee_queries.py and file_operations.py.

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from contextlib import asynccontextmanager
from typing import Optional, List, Any
from database import get_connection, initialize_database
import mysql.connector
import employee_queries as eq
import file_operations as fo


# ─────────────────────────────────────────────
# STARTUP — auto-create DB and table
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Initializing database...")
    initialize_database()
    print("[Startup] Database ready. Server is accepting requests.")
    yield


# ─────────────────────────────────────────────
# APP INSTANCE
# ─────────────────────────────────────────────

app = FastAPI(
    title="Employee Management API",
    description=(
        "A beginner-friendly REST API covering:\n\n"
        "- **Employee CRUD** — Add, list, get, update, delete, search\n"
        "- **Text Files**    — Create, write, append, read, rename, copy, delete\n"
        "- **CSV Files**     — Read, import to MySQL, export from MySQL\n"
        "- **JSON Files**    — Read, write, export from MySQL\n"
        "- **Upload/Download** — Upload .txt/.csv/.json, download by filename"
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ══════════════════════════════════════════════
# PYDANTIC SCHEMAS
# Input models  → validate request body
# Output models → document response shape in /docs
# ══════════════════════════════════════════════

# ── Employee schemas ──────────────────────────

class EmployeeInput(BaseModel):
    """Request body for POST /employees and PUT /employees/{id}"""
    name:       str      = Field(..., min_length=1, max_length=100, example="Alice Johnson")
    email:      EmailStr = Field(..., example="alice@example.com")
    department: str      = Field(..., min_length=1, max_length=100, example="Engineering")
    salary:     float    = Field(..., gt=0, example=55000.00)


class EmployeeOut(BaseModel):
    """Single employee record returned from the database"""
    id:         int
    name:       str
    email:      str
    department: str
    salary:     float


class EmployeeListOut(BaseModel):
    """Response for GET /employees and search"""
    total:     int
    employees: List[EmployeeOut]


class MessageOut(BaseModel):
    """Generic success message response"""
    message: str


class AddEmployeeOut(BaseModel):
    """Response for POST /employees"""
    id:      int
    message: str


# ── Text file schemas ─────────────────────────

class TextWriteInput(BaseModel):
    """Request body for write/append text file routes"""
    content: str = Field(..., min_length=1, example="Hello, this is line one.\n")


class TextFileOut(BaseModel):
    """Response for read-file routes"""
    filename: str
    content:  str


class TextLinesOut(BaseModel):
    """Response for read-lines route"""
    filename:    str
    total_lines: int
    lines:       List[str]


class FileExistsOut(BaseModel):
    """Response for file-exists check"""
    filename: str
    exists:   bool


class FileSizeOut(BaseModel):
    """Response for file-size route"""
    filename:   str
    size_bytes: int
    size_kb:    float


class RenameInput(BaseModel):
    """Request body for rename route"""
    old_name: str = Field(..., example="notes.txt")
    new_name: str = Field(..., example="notes_v2.txt")


class CopyInput(BaseModel):
    """Request body for copy route"""
    source_name: str = Field(..., example="notes.txt")
    dest_name:   str = Field(..., example="notes_backup.txt")


# ── CSV schemas ───────────────────────────────

class CsvRowOut(BaseModel):
    """A single row from a CSV file (all values as strings before parsing)"""
    name:       str
    email:      str
    department: str
    salary:     str


class CsvReadOut(BaseModel):
    """Response for read-CSV route"""
    filename:   str
    total_rows: int
    rows:       List[Any]   # flexible — CSV rows may have extra columns


class CsvImportOut(BaseModel):
    """Response for CSV import route"""
    message:  str
    imported: int
    skipped:  int
    errors:   List[str]


class CsvExportOut(BaseModel):
    """Response for CSV export route"""
    message:        str
    file:           str
    total_exported: int


# ── JSON schemas ──────────────────────────────

class JsonReadOut(BaseModel):
    """Response for read-JSON route"""
    filename: str
    data:     Any   # JSON can be a dict, list, string, etc.


class JsonWriteInput(BaseModel):
    """Request body for write-JSON route"""
    data: Any = Field(..., example=[{"name": "Alice", "dept": "Eng"}])


class JsonExportOut(BaseModel):
    """Response for JSON export route"""
    message:        str
    file:           str
    total_exported: int


# ── Upload schemas ────────────────────────────

class UploadOut(BaseModel):
    """Response for file upload"""
    message:    str
    filename:   str
    size_bytes: int
    size_kb:    float


class UploadedFileInfo(BaseModel):
    """Info about one uploaded file in the list"""
    filename:   str
    size_bytes: int
    size_kb:    float


class UploadListOut(BaseModel):
    """Response for list-uploads route"""
    total: int
    files: List[UploadedFileInfo]


# ══════════════════════════════════════════════
# HEALTH ROUTES
# ══════════════════════════════════════════════

@app.get("/", tags=["Health"], response_model=MessageOut)
def root():
    """Confirms the server is running."""
    return {"message": "Employee Management API is running!"}


@app.get("/db-test", tags=["Health"])
def test_database_connection():
    """Tests whether Python can connect to MySQL."""
    connection = None
    try:
        connection = get_connection()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            cursor.close()
            return {
                "status": "success",
                "message": "Connected to MySQL successfully!",
                "mysql_version": version[0],
                "database": current_db[0]
            }
    except mysql.connector.Error as error:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(error)}")
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# ══════════════════════════════════════════════
# EMPLOYEE ROUTES
# ══════════════════════════════════════════════

@app.post("/employees", status_code=201, tags=["Employees"], response_model=AddEmployeeOut)
def add_employee(employee: EmployeeInput):
    """Add a new employee. Returns the auto-generated ID."""
    try:
        return eq.add_employee(
            name=employee.name, email=employee.email,
            department=employee.department, salary=employee.salary
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/employees", tags=["Employees"], response_model=EmployeeListOut)
def get_all_employees():
    """Returns all employees."""
    try:
        employees = eq.get_all_employees()
        return {"total": len(employees), "employees": employees}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/employees/search/query", tags=["Employees"], response_model=EmployeeListOut)
def search_employees(
    keyword: str = Query(..., min_length=1, description="Search by name or department")
):
    """Search employees by name or department (case-insensitive)."""
    try:
        results = eq.search_employees(keyword)
        return {"keyword": keyword, "total": len(results), "employees": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/employees/{employee_id}", tags=["Employees"], response_model=EmployeeOut)
def get_employee(employee_id: int):
    """Get one employee by ID. Returns 404 if not found."""
    try:
        employee = eq.get_employee_by_id(employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/employees/{employee_id}", tags=["Employees"], response_model=MessageOut)
def update_employee(employee_id: int, employee: EmployeeInput):
    """Update all fields of an employee. Returns 404 if not found."""
    try:
        result = eq.update_employee(
            employee_id=employee_id, name=employee.name, email=employee.email,
            department=employee.department, salary=employee.salary
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/employees/{employee_id}", tags=["Employees"], response_model=MessageOut)
def delete_employee(employee_id: int):
    """Delete an employee by ID. Returns 404 if not found."""
    try:
        result = eq.delete_employee(employee_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════
# TEXT FILE ROUTES
# ══════════════════════════════════════════════

@app.post("/files/text/create/{filename}", tags=["Text Files"], response_model=MessageOut)
def create_text_file(filename: str):
    """
    Creates an empty text file in /reports.
    Example: POST /files/text/create/notes.txt
    """
    try:
        return fo.text_create_file(filename)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/files/text/write/{filename}", tags=["Text Files"], response_model=MessageOut)
def write_text_file(filename: str, body: TextWriteInput):
    """
    Overwrites a file with new content.
    Creates the file if it does not exist yet.
    """
    try:
        return fo.text_write_file(filename, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/files/text/append/{filename}", tags=["Text Files"], response_model=MessageOut)
def append_text_file(filename: str, body: TextWriteInput):
    """
    Appends content to an existing file without erasing existing data.
    Returns 404 if the file does not exist.
    """
    try:
        return fo.text_append_file(filename, body.content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/text/read/{filename}", tags=["Text Files"], response_model=TextFileOut)
def read_text_file(filename: str):
    """Returns the full content of a text file as a single string."""
    try:
        return fo.text_read_file(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/text/lines/{filename}", tags=["Text Files"], response_model=TextLinesOut)
def read_text_lines(filename: str):
    """Returns the content of a text file as a list of lines."""
    try:
        return fo.text_read_lines(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/text/exists/{filename}", tags=["Text Files"], response_model=FileExistsOut)
def file_exists(filename: str):
    """Checks whether a file exists in /reports. Never raises a 404."""
    try:
        return fo.text_file_exists(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/files/text/rename", tags=["Text Files"], response_model=MessageOut)
def rename_text_file(body: RenameInput):
    """Renames a file inside /reports."""
    try:
        return fo.text_rename_file(body.old_name, body.new_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/text/copy", tags=["Text Files"], response_model=MessageOut)
def copy_text_file(body: CopyInput):
    """Copies a file within /reports."""
    try:
        return fo.text_copy_file(body.source_name, body.dest_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/files/text/delete/{filename}", tags=["Text Files"], response_model=MessageOut)
def delete_text_file(filename: str):
    """Deletes a file from /reports. Returns 404 if not found."""
    try:
        return fo.text_delete_file(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/text/size/{filename}", tags=["Text Files"], response_model=FileSizeOut)
def text_file_size(filename: str):
    """Returns the size of a file in /reports in bytes and KB."""
    try:
        return fo.text_file_size(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════
# CSV FILE ROUTES
# ══════════════════════════════════════════════

@app.get("/files/csv/read/{filename}", tags=["CSV Files"], response_model=CsvReadOut)
def read_csv_file(filename: str):
    """
    Reads a CSV file from /reports and returns its rows.
    The CSV must have headers: name, email, department, salary.
    """
    try:
        return fo.csv_read_file(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/csv/import/{filename}", tags=["CSV Files"], response_model=CsvImportOut)
def import_csv_to_mysql(filename: str):
    """
    Reads a CSV file from /reports and inserts valid rows into MySQL.
    Invalid rows (empty fields, bad salary, duplicate email) are skipped.
    Returns a summary: how many were imported vs skipped, and why.
    """
    try:
        return fo.csv_import_to_mysql(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/csv/export/{filename}", tags=["CSV Files"], response_model=CsvExportOut)
def export_mysql_to_csv(filename: str):
    """
    Exports all employees from MySQL to a CSV file in /reports.
    Example: POST /files/csv/export/employees.csv
    """
    try:
        return fo.csv_export_from_mysql(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════
# JSON FILE ROUTES
# ══════════════════════════════════════════════

@app.get("/files/json/read/{filename}", tags=["JSON Files"], response_model=JsonReadOut)
def read_json_file(filename: str):
    """
    Reads a JSON file from /reports and returns its parsed content.
    Returns 400 if the file contains invalid JSON.
    """
    try:
        return fo.json_read_file(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/json/write/{filename}", tags=["JSON Files"], response_model=MessageOut)
def write_json_file(filename: str, body: JsonWriteInput):
    """
    Writes JSON data to a file in /reports.
    The body can be any valid JSON — a dict, a list, etc.
    Example body: [{"name": "Alice", "dept": "Engineering"}]
    """
    try:
        return fo.json_write_file(filename, body.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files/json/export/{filename}", tags=["JSON Files"], response_model=JsonExportOut)
def export_mysql_to_json(filename: str):
    """
    Exports all employees from MySQL to a JSON file in /reports.
    Example: POST /files/json/export/employees.json
    """
    try:
        return fo.json_export_from_mysql(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════
# FILE UPLOAD & DOWNLOAD ROUTES
# ══════════════════════════════════════════════

@app.post("/files/upload", tags=["Upload & Download"], response_model=UploadOut)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a .txt, .csv, or .json file (max 5 MB).
    The file is saved to /uploads with its original filename.

    UploadFile is FastAPI's built-in type for multipart/form-data uploads.
    file.filename — the original name of the file
    file.read()   — reads the raw bytes of the uploaded file
    """
    try:
        # Read the raw bytes of the uploaded file
        file_bytes = await file.read()

        result = fo.save_uploaded_file(file_bytes, file.filename)
        return result

    except ValueError as e:
        # Invalid extension or file too large
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/upload/list", tags=["Upload & Download"], response_model=UploadListOut)
def list_uploads():
    """Lists all files currently saved in /uploads."""
    try:
        return fo.list_uploaded_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/download/{filename}", tags=["Upload & Download"])
def download_file(filename: str):
    """
    Downloads a file from /uploads by filename.
    Returns 404 if the file does not exist.

    FileResponse streams the file directly to the client —
    the browser will show a download dialog for binary files.
    """
    try:
        file_path = fo.get_upload_path(filename)

        # FileResponse is FastAPI's built-in way to send a file to the client.
        # media_type="application/octet-stream" tells the browser:
        # "treat this as a raw download, not a web page"
        return FileResponse(
            path       = str(file_path),
            filename   = filename,
            media_type = "application/octet-stream"
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
