# file_operations.py
# Responsibility: All file handling logic.
#   - Text files  : create, write, append, read, rename, copy, delete, size
#   - CSV files   : read, import to MySQL, export from MySQL, validate rows
#   - JSON files  : read, write, export from MySQL, handle invalid JSON
#   - Upload      : save uploaded file to /uploads, validate ext + size
#   - Download    : return a saved file for download
#
# main.py calls these functions — this file never handles HTTP directly.

import os
import csv
import json
import shutil                        # built-in: copy / rename files
from pathlib import Path             # built-in: safe, cross-platform paths

import employee_queries as eq        # to export/import employee data


# ─────────────────────────────────────────────
# FOLDER SETUP
# All paths are relative to this file's location.
# Using Path(__file__).parent makes sure paths work
# regardless of where you run the server from.
# ─────────────────────────────────────────────

BASE_DIR     = Path(__file__).parent          # .../employee_api/
UPLOADS_DIR  = BASE_DIR / "uploads"           # .../employee_api/uploads/
REPORTS_DIR  = BASE_DIR / "reports"           # .../employee_api/reports/

# Create the folders if they don't exist yet
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Allowed file extensions for upload — prevents arbitrary file execution
ALLOWED_EXTENSIONS = {".txt", ".csv", ".json"}

# Max upload size: 5 MB in bytes
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


# ══════════════════════════════════════════════
# TEXT FILE OPERATIONS
# ══════════════════════════════════════════════

def text_create_file(filename: str) -> dict:
    """
    Creates an empty text file in /reports.
    Raises FileExistsError if the file already exists.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if file_path.exists():
        raise FileExistsError(f"File '{filename}' already exists.")

    # 'x' mode = exclusive create — fails if file exists (extra safety)
    with open(file_path, "x", encoding="utf-8") as f:
        pass  # just create it empty

    return {"message": f"File '{filename}' created.", "path": str(file_path)}


def text_write_file(filename: str, content: str) -> dict:
    """
    Writes content to a file, OVERWRITING any existing content.
    'w' mode truncates the file first, then writes.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    # 'w' = write mode: creates the file if missing, overwrites if present
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"message": f"Content written to '{filename}'.", "characters": len(content)}


def text_append_file(filename: str, content: str) -> dict:
    """
    Appends content to an existing file without erasing existing data.
    'a' mode = append: moves the cursor to the END of the file before writing.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist.")

    # 'a' = append mode: never overwrites; adds to the end
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)

    return {"message": f"Content appended to '{filename}'."}


def text_read_file(filename: str) -> dict:
    """
    Reads and returns the entire content of a file as one string.
    'r' mode = read mode (default).
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist.")

    # 'r' = read mode
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()   # reads everything at once

    return {"filename": filename, "content": content}


def text_read_lines(filename: str) -> dict:
    """
    Reads a file line by line and returns a list of lines.
    Useful for large files — you process one line at a time.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist.")

    with open(file_path, "r", encoding="utf-8") as f:
        # readlines() returns a list like ["line1\n", "line2\n", ...]
        # strip() removes the newline character from each line
        lines = [line.rstrip("\n") for line in f.readlines()]

    return {"filename": filename, "total_lines": len(lines), "lines": lines}


def text_file_exists(filename: str) -> dict:
    """
    Checks whether a file exists in /reports.
    Returns True or False — never raises an error.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename
    exists = file_path.exists()
    return {"filename": filename, "exists": exists}


def text_rename_file(old_name: str, new_name: str) -> dict:
    """
    Renames a file inside /reports.
    os.rename() moves the file to the new name — both must be in /reports.
    """
    _validate_safe_filename(old_name)
    _validate_safe_filename(new_name)

    old_path = REPORTS_DIR / old_name
    new_path = REPORTS_DIR / new_name

    if not old_path.exists():
        raise FileNotFoundError(f"File '{old_name}' does not exist.")
    if new_path.exists():
        raise FileExistsError(f"A file named '{new_name}' already exists.")

    os.rename(old_path, new_path)
    return {"message": f"Renamed '{old_name}' → '{new_name}'."}


def text_copy_file(source_name: str, dest_name: str) -> dict:
    """
    Copies a file within /reports.
    shutil.copy2() copies content AND metadata (timestamps).
    """
    _validate_safe_filename(source_name)
    _validate_safe_filename(dest_name)

    source_path = REPORTS_DIR / source_name
    dest_path   = REPORTS_DIR / dest_name

    if not source_path.exists():
        raise FileNotFoundError(f"Source file '{source_name}' does not exist.")
    if dest_path.exists():
        raise FileExistsError(f"Destination file '{dest_name}' already exists.")

    shutil.copy2(source_path, dest_path)
    return {"message": f"Copied '{source_name}' → '{dest_name}'."}


def text_delete_file(filename: str) -> dict:
    """
    Deletes a file from /reports.
    Only deletes files INSIDE /reports — cannot delete arbitrary system files.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist.")

    os.remove(file_path)
    return {"message": f"File '{filename}' deleted."}


def text_file_size(filename: str) -> dict:
    """
    Returns the size of a file in bytes and kilobytes.
    os.path.getsize() returns the file size in bytes.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist.")

    size_bytes = os.path.getsize(file_path)
    size_kb    = round(size_bytes / 1024, 2)   # convert bytes → KB

    return {"filename": filename, "size_bytes": size_bytes, "size_kb": size_kb}


# ══════════════════════════════════════════════
# CSV FILE OPERATIONS
# ══════════════════════════════════════════════

# Expected CSV column headers — any other layout is rejected
CSV_HEADERS = ["name", "email", "department", "salary"]


def csv_read_file(filename: str) -> dict:
    """
    Reads a CSV file from /reports and returns its rows as a list of dicts.
    csv.DictReader maps each row to a dict using the header row as keys.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file '{filename}' does not exist.")

    rows = []
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        # DictReader reads the first row as column names (headers)
        # Each subsequent row becomes a dict: {"name": "Alice", "email": "..."}
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))

    return {"filename": filename, "total_rows": len(rows), "rows": rows}


def csv_import_to_mysql(filename: str) -> dict:
    """
    Reads a CSV file from /reports, validates each row, and inserts
    valid rows into MySQL. Returns a summary of success/failure counts.

    Validation rules per row:
      - All 4 headers must be present
      - name, email, department must not be empty
      - salary must be a positive number
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file '{filename}' does not exist.")

    imported   = 0   # count of successfully inserted rows
    skipped    = 0   # count of invalid/duplicate rows
    errors     = []  # list of error messages for skipped rows

    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        # Validate that the CSV has the correct headers
        if reader.fieldnames is None or not all(h in reader.fieldnames for h in CSV_HEADERS):
            raise ValueError(
                f"CSV must have headers: {CSV_HEADERS}. "
                f"Found: {reader.fieldnames}"
            )

        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is headers
            # Strip whitespace from all values
            name       = row.get("name", "").strip()
            email      = row.get("email", "").strip()
            department = row.get("department", "").strip()
            salary_str = row.get("salary", "").strip()

            # Validate: no empty fields
            if not name or not email or not department or not salary_str:
                skipped += 1
                errors.append(f"Row {row_num}: empty field(s) — skipped.")
                continue

            # Validate: salary must be a valid positive number
            try:
                salary = float(salary_str)
                if salary <= 0:
                    raise ValueError()
            except ValueError:
                skipped += 1
                errors.append(f"Row {row_num}: invalid salary '{salary_str}' — skipped.")
                continue

            # Try inserting into MySQL
            try:
                eq.add_employee(name, email, department, salary)
                imported += 1
            except ValueError as e:
                # Duplicate email
                skipped += 1
                errors.append(f"Row {row_num}: {e}")
            except Exception as e:
                skipped += 1
                errors.append(f"Row {row_num}: database error — {e}")

    return {
        "message"  : f"CSV import complete.",
        "imported" : imported,
        "skipped"  : skipped,
        "errors"   : errors
    }


def csv_export_from_mysql(filename: str) -> dict:
    """
    Fetches all employees from MySQL and writes them to a CSV file in /reports.
    csv.DictWriter writes dicts as rows using the fieldnames as column headers.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    employees = eq.get_all_employees()

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        # fieldnames defines the column order in the CSV
        fieldnames = ["id", "name", "email", "department", "salary"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()          # writes the header row
        writer.writerows(employees)   # writes one row per employee dict

    return {
        "message"       : f"Exported {len(employees)} employees to '{filename}'.",
        "file"          : filename,
        "total_exported": len(employees)
    }


# ══════════════════════════════════════════════
# JSON FILE OPERATIONS
# ══════════════════════════════════════════════

def json_read_file(filename: str) -> dict:
    """
    Reads a JSON file from /reports and returns its parsed content.
    json.load() converts JSON text → Python dict/list.
    Raises ValueError if the file contains invalid JSON.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"JSON file '{filename}' does not exist.")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)   # parses the whole file as JSON
        except json.JSONDecodeError as e:
            # JSONDecodeError tells us exactly where the JSON is broken
            raise ValueError(f"Invalid JSON in '{filename}': {e}")

    return {"filename": filename, "data": data}


def json_write_file(filename: str, data: dict | list) -> dict:
    """
    Writes a Python dict or list to a JSON file in /reports.
    json.dump() converts Python object → formatted JSON text.
    indent=4 makes the output human-readable (pretty-printed).
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    with open(file_path, "w", encoding="utf-8") as f:
        # indent=4 adds 4-space indentation — makes JSON easy to read
        # ensure_ascii=False preserves non-ASCII characters (e.g. accented names)
        json.dump(data, f, indent=4, ensure_ascii=False)

    return {"message": f"Data written to '{filename}'.", "file": filename}


def json_export_from_mysql(filename: str) -> dict:
    """
    Fetches all employees from MySQL and exports them as a JSON file.
    """
    _validate_safe_filename(filename)
    file_path = REPORTS_DIR / filename

    employees = eq.get_all_employees()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=4, ensure_ascii=False)

    return {
        "message"       : f"Exported {len(employees)} employees to '{filename}'.",
        "file"          : filename,
        "total_exported": len(employees)
    }


# ══════════════════════════════════════════════
# FILE UPLOAD & DOWNLOAD
# ══════════════════════════════════════════════

def save_uploaded_file(file_bytes: bytes, filename: str) -> dict:
    """
    Saves an uploaded file to /uploads.

    Validations:
      1. Extension must be .txt, .csv, or .json
      2. File size must not exceed 5 MB
      3. Filename must not contain path traversal characters

    Args:
        file_bytes (bytes) : raw file content
        filename   (str)   : original filename from the upload

    Returns:
        dict with saved filename and size info
    """
    _validate_safe_filename(filename)

    # Check extension
    ext = Path(filename).suffix.lower()   # e.g. ".csv"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Check size
    size_bytes = len(file_bytes)
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File too large: {round(size_bytes/1024/1024, 2)} MB. "
            f"Max allowed: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )

    # Save to /uploads
    save_path = UPLOADS_DIR / filename

    # 'wb' = write binary — works for text and binary files alike
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    return {
        "message"   : f"File '{filename}' uploaded successfully.",
        "filename"  : filename,
        "size_bytes": size_bytes,
        "size_kb"   : round(size_bytes / 1024, 2)
    }


def get_upload_path(filename: str) -> Path:
    """
    Returns the full Path object for a file in /uploads.
    Raises FileNotFoundError if the file doesn't exist.
    This is used by the download route in main.py.
    """
    _validate_safe_filename(filename)
    file_path = UPLOADS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"File '{filename}' not found in uploads."
        )

    return file_path


def list_uploaded_files() -> dict:
    """
    Returns a list of all files currently in /uploads.
    """
    files = []
    for f in UPLOADS_DIR.iterdir():
        if f.is_file():
            files.append({
                "filename"  : f.name,
                "size_bytes": f.stat().st_size,
                "size_kb"   : round(f.stat().st_size / 1024, 2)
            })

    return {"total": len(files), "files": files}


# ══════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════

def _validate_safe_filename(filename: str) -> None:
    """
    Security check: reject filenames that try to escape the target folder.

    Path traversal attack example:
        filename = "../../etc/passwd"
        REPORTS_DIR / filename  →  /etc/passwd  ← DANGEROUS

    This function blocks any filename containing:
        - ".."   (go up a directory)
        - "/"    (absolute path separator on Linux/Mac)
        - "\\"   (absolute path separator on Windows)

    Raises:
        ValueError — if the filename looks suspicious
    """
    if not filename:
        raise ValueError("Filename cannot be empty.")

    # Check for path traversal characters
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(
            f"Invalid filename '{filename}'. "
            "Filenames cannot contain '..', '/', or '\\'."
        )

    # Check that the filename has an extension
    if "." not in filename:
        raise ValueError(
            f"Filename '{filename}' must include an extension (e.g. .txt, .csv, .json)."
        )
