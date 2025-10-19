@echo off
echo Starting RecyConnect Website Tests
echo ==================================

echo Checking if Django server is running...
python -c "import requests; requests.get('http://127.0.0.1:8000', timeout=5)" 2>nul
if %errorlevel% equ 0 (
    echo Django server is running
) else (
    echo ERROR: Django server is not running!
    echo Please start the server first: python manage.py runserver
    pause
    exit /b 1
)

echo.
echo Running website functionality tests...
echo Note: Tests will open Chrome browser and clean up test data automatically.
echo The test will follow this exact sequence:
echo 1. Load landing page
echo 2. Show household registration
echo 3. Test admin login & dashboard loads
echo 4. Test household login & show all page loads for household
echo 5. Test collector login & dashboard loads
echo 6. Test buyer login & all page loads & Buy function
echo 7. Clean up test data after testing
echo.
python run_website_tests.py

echo.
echo Tests completed!
pause