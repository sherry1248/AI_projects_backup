@echo off
setlocal

REM Always run from this script's directory.
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"

echo [1/6] Python virtual environment check
if not exist "%VENV_PY%" (
    echo Virtual environment not found. Creating .venv ...
    py -3 -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
        if errorlevel 1 (
            echo Failed to create virtual environment.
            echo Make sure Python is installed and available in PATH.
            pause
            exit /b 1
        )
    )
)

echo [2/6] Checking pip in virtual environment
"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is missing in .venv. Bootstrapping with ensurepip ...
    "%VENV_PY%" -m ensurepip --upgrade
)

"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Failed to prepare pip in .venv.
    pause
    exit /b 1
)

echo [3/6] Upgrading pip
"%VENV_PY%" -m pip install --upgrade pip

echo [4/6] Installing core Django dependencies
"%VENV_PY%" -m pip install "Django==3.2.13" "asgiref==3.4.1" "pytz==2021.1" "sqlparse==0.4.2"
if errorlevel 1 (
    echo Failed while installing core Django dependencies.
    pause
    exit /b 1
)

echo [5/6] Installing chatbot dependencies
"%VENV_PY%" -m pip install "djangorestframework==3.13.1" "requests==2.31.0" "transformers==4.37.2" "torch" "kss" "psycopg2-binary"
if errorlevel 1 (
    echo Failed while installing chatbot dependencies.
    pause
    exit /b 1
)

echo [6/6] Applying migrations and starting server
"%VENV_PY%" manage.py migrate
if errorlevel 1 (
    echo Migration failed.
    pause
    exit /b 1
)

echo Server starting at http://127.0.0.1:8010
"%VENV_PY%" manage.py runserver 8010

endlocal