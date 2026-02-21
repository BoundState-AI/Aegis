@echo off
setlocal

set "ROOT=%~dp0"
pushd "%ROOT%"

echo.
echo ============================================
echo AEGIS Monitor Intelligence Test Runner
echo Root: %ROOT%
echo Date: %DATE% %TIME%
echo ============================================
echo.

set "TEST_FILES=tests/test_normalize.py tests/test_diff.py tests/test_trigger_policy.py tests/test_signal_analyzer_schema.py tests/test_impact_assessor.py tests/test_source_policy.py tests/test_monitor_endpoint.py tests/test_assertion_store.py tests/test_hash_store_hmac.py tests/test_regulatory_apac.py tests/test_regulatory_western.py tests/test_run_lock_store.py tests/test_recursive_resolver.py tests/test_resolver_endpoint.py tests/test_hitl_gates.py"

set "PY_CMD="

REM Prefer currently active Python (works when shell is already in boundstate-intent).
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python -c "import pytest" >nul 2>&1
    if %ERRORLEVEL%==0 (
        if defined CONDA_DEFAULT_ENV (
            echo [ENV] Using active python from conda env: %CONDA_DEFAULT_ENV%
        ) else (
            echo [ENV] Using active python on PATH
        )
        set "PY_CMD=python"
    )
)

REM Fallback to explicit conda run if active python lacks pytest.
if not defined PY_CMD (
    where conda >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo [ENV] Falling back to conda run env: boundstate-intent
        call conda run --no-banner -n boundstate-intent python -c "import pytest" >nul 2>&1
        if %ERRORLEVEL%==0 (
            set "PY_CMD=call conda run --no-banner -n boundstate-intent python"
        )
    )
)

if not defined PY_CMD (
    echo [FATAL] pytest is not available in active python or conda env.
    echo         Try:
    echo         python -m pip install pytest
    echo         conda run -n boundstate-intent python -m pip install pytest
    popd
    exit /b 1
)

echo [RUN] pytest -q %TEST_FILES%
%PY_CMD% -m pytest -q %TEST_FILES%
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo [PASS] Selected monitor/regulatory tests passed.
) else (
    echo [FAIL] Test run failed with exit code %EXITCODE%.
)

popd
exit /b %EXITCODE%
