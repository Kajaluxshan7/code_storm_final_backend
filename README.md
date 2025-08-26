# Financial Statement Processor (Backend)

This repository contains the FastAPI backend for the Financial Statement Processor MVP.

## Quick setup (Windows / PowerShell)

Checklist:

- Clone repository from GitHub
- Create and activate a virtual environment
- Install Python dependencies
- Copy `.env.example` to `.env` and update values (especially `DATABASE_URL`, AWS keys, and `SECRET_KEY`)
- Run database migrations
- Start the development server

## Requirements

- Recommended Python: 3.12
- Recommended pip: 24.0

Notes: use a virtual environment (example below) that matches the recommended Python version.

### 1) Clone the repo

```powershell
# Replace <your-github-url> with the repository URL
git clone <your-github-url> .
```

### 2) Create and activate a virtual environment

```powershell
python -m venv .venv
# Activate the venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, enable it for the session with:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Environment variables

Copy the example env and edit values:

```powershell
copy .env.example .env
notepad .env
```

Make sure `DATABASE_URL` points to your Postgres instance and `SECRET_KEY` is set to a secure value.

### 5) Database migrations (Alembic)

Initialize migrations (already done in this project) and apply them:

```powershell
alembic upgrade head
```

If you need to create a migration after model changes:

```powershell
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

### 6) Run the development server

There are two common ways to run the application locally. Pick one depending on whether you need automatic reloads while developing.

- Normal run (no auto-reload): runs the package/module directly. This executes the code in `app/main.py` and starts the server with the settings defined there.

```powershell
python -m app.main
```

This is a simple, deterministic way to start the app. It uses the `if __name__ == "__main__"` block in `app/main.py` which calls `uvicorn.run(...)`. By default this will respect `DEBUG` in your environment (the project sets reload based on `settings.DEBUG`).

- Development run with auto-reload: use Uvicorn's `--reload` option to automatically reload the server when source files change. This is recommended during development.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Visit http://127.0.0.1:8000/api/v1/openapi.json (or the docs at `/docs`) to confirm the app is running.

### 7) Run tests

```powershell
pytest
```

## Useful notes

- The project uses SQLAlchemy and Alembic for migrations. The migrations folder is present under `migrations/`.
- S3 integration is present in `app/integrations/storage/` and uses `boto3`. Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `S3_BUCKET_NAME` in `.env` if you need S3 features.
- Keep `.env` out of version control. The repository includes `.env.example` as a template.

## Troubleshooting

- If you see import errors for `pydantic-settings`, ensure the installed version is compatible with your Python version.
- Ensure PostgreSQL is running and accessible via the `DATABASE_URL` in your `.env`.

## Contact

For more help, open an issue or contact the maintainers in the repository.
