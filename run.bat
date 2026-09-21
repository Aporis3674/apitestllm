@echo off
title API TEST CLI - AI Endpoint ^& Latency Benchmark
cls
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    uv run apitestllm %*
) else (
    echo uv not found, falling back to system python.
    echo Make sure dependencies are installed: pip install -r requirements.txt
    python "%~dp0api_test.py" %*
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    pause
)
