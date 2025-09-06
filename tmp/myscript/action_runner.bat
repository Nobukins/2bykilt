@echo off
REM Windows用action_runner実行バッチファイル
REM 仮想環境とモジュールパスを確実に設定

echo 🔧 Windows Batch: Starting action_runner
echo 🔧 Python executable: %~dp0..\..\venv\Scripts\python.exe

REM 仮想環境のPythonを確認
if exist "%~dp0..\..\venv\Scripts\python.exe" (
    echo ✅ Found venv Python
    set PYTHON_EXE=%~dp0..\..\venv\Scripts\python.exe
) else if exist "%~dp0..\..\venv312\Scripts\python.exe" (
    echo ✅ Found venv312 Python
    set PYTHON_EXE=%~dp0..\..\venv312\Scripts\python.exe
) else if exist "%~dp0..\..\env\Scripts\python.exe" (
    echo ✅ Found env Python
    set PYTHON_EXE=%~dp0..\..\env\Scripts\python.exe
) else (
    echo ⚠️ Using system Python
    set PYTHON_EXE=python
)

REM 環境変数設定
set PYTHONPATH=%~dp0;%~dp0..\..;%~dp0..\..\src;%PYTHONPATH%

echo 🔧 PYTHONPATH: %PYTHONPATH%
echo 🚀 Executing: %PYTHON_EXE% %~dp0action_runner.py %*

REM action_runner.py実行
"%PYTHON_EXE%" "%~dp0action_runner.py" %*

echo 🏁 Exit code: %ERRORLEVEL%
exit /b %ERRORLEVEL%
