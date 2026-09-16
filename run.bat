@echo off
title API TEST CLI - AI Endpoint & Latency Benchmark
cls
python "%~dp0api_test.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    pause
)
