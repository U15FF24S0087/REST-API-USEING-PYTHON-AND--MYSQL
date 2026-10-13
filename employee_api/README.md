# Employee Management REST API

A beginner-friendly REST API built with Python, FastAPI, MySQL, and file handling.

## Tech Stack
- Python 3.10+
- FastAPI
- MySQL
- Uvicorn

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd employee_api
```

### 2. Create and activate virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and fill in your MySQL credentials:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=employee_db
```

### 5. Create the MySQL database
Run the SQL in `database_setup.sql` in MySQL Workbench or CLI.

### 6. Run the server
```bash
uvicorn main:app --reload
```

### 7. Open API docs
Visit http://127.0.0.1:8000/docs

## API Endpoints (added as stages progress)
| Method | URL | Description |
|--------|-----|-------------|
| POST   | /employees | Add employee |
| GET    | /employees | Get all employees |
| GET    | /employees/{id} | Get employee by ID |
| PUT    | /employees/{id} | Update employee |
| DELETE | /employees/{id} | Delete employee |
