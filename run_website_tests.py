"""
Simple test runner for RecyConnect website functionality tests.
This script runs the tests with proper server management.
"""

import subprocess
import time
import sys
import os
import requests
from tests.website_tester import RecyConnectTester

def check_server_running():
    """Check if Django server is running on port 8000"""
    try:
        response = requests.get("http://127.0.0.1:8000", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Main function to run tests"""
    print("RecyConnect Website Test Runner")
    print("=" * 40)
    
    # Check if server is running
    if not check_server_running():
        print("❌ Django server is not running!")
        print("Please start the server first:")
        print("  python manage.py runserver")
        print("\nThen run this test script again.")
        return
    
    print("✅ Django server is running")
    print("\nStarting website functionality tests...")
    print("Note: Tests will run in Chrome browser and clean up test data automatically.")
    print("The test will follow this exact sequence:")
    print("1. Load landing page")
    print("2. Show household registration")
    print("3. Test admin login & dashboard loads")
    print("4. Test household login & show all page loads for household")
    print("5. Test collector login & dashboard loads")
    print("6. Test buyer login & all page loads & Buy function")
    print("7. Clean up test data after testing")
    
    # Run the tests
    tester = RecyConnectTester()
    tester.run_all_tests()
    
    print("\n" + "=" * 40)
    print("Test execution completed!")
    print("All test data has been cleaned up from the database.")

if __name__ == "__main__":
    main()
