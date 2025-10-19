"""
🌱 RecyConnect Selenium Test
"""

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class RecyConnectTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.test_results = {"total": 0, "passed": 0, "failed": 0, "details": []}
        self.created_test_users = []
        self.admin = {"email": "recyconnect314@gmail.com", "password": "RecycleNow"}
        self.dummy_users = {}

    # ------------------------
    # SETUP / TEARDOWN
    # ------------------------
    def setup_driver(self):
        print("🌍 Setting up Chrome...")
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1366,768")
            # options.add_argument("--headless")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 15)
            print("✅ Chrome setup complete.\n")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Chrome: {e}")
            return False

    def teardown_driver(self):
        try:
            if self.driver:
                self.driver.quit()
                print("🧹 Browser closed successfully.")
        except Exception:
            pass

    # ------------------------
    # UTILS
    # ------------------------
    def record(self, name, success, details=""):
        self.test_results["total"] += 1
        if success:
            self.test_results["passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results["failed"] += 1
            status = "❌ FAIL"
        print(f"{status}: {name}")
        if details:
            print(f"   ↳ {details}")
        self.test_results["details"].append((name, status, details))

    def gen_email(self, prefix):
        return f"{prefix}_{random.randint(1000,9999)}@testmail.com"

    def safe_get(self, path):
        try:
            self.driver.get(f"{self.base_url}{path}")
            time.sleep(1)
            return True
        except WebDriverException:
            return False

    # ------------------------
    # TEST CASES
    # ------------------------
    def test_landing_page(self):
        print("🧩 1. Testing Landing Page...")
        self.safe_get("/")
        if "RecyConnect" in self.driver.title or "RecyConnect" in self.driver.page_source:
            self.record("Landing Page", True)
        else:
            self.record("Landing Page", False, "Missing keyword 'RecyConnect'")

    def register_user(self, role):
        """Register dummy user (no image required)."""
        print(f"📝 Registering dummy {role} user...")
        email = self.gen_email(role)
        password = "password123"
        self.dummy_users[role] = {"email": email, "password": password}

        if not self.safe_get("/user/register/"):
            self.record(f"{role.capitalize()} Registration", False, "Could not open registration page")
            return False

        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            time.sleep(1)

            # Select role if dropdown exists
            try:
                role_select = self.driver.find_element(By.NAME, "role")
                self.driver.execute_script(f"arguments[0].value = '{role}';", role_select)
            except Exception:
                pass

            # Fill fields
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "password1").send_keys(password)
            self.driver.find_element(By.NAME, "password2").send_keys(password)

            # Submit
            submit = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"))
            )
            self.driver.execute_script("arguments[0].click();", submit)
            time.sleep(3)

            if any(k in self.driver.page_source.lower() for k in ["login", "thank", "success", "approval", "registered"]):
                self.record(f"{role.capitalize()} Registration", True)
                self.created_test_users.append(email)
                return True
            else:
                self.record(f"{role.capitalize()} Registration", False, "No success message found")
                return False

        except Exception as e:
            self.record(f"{role.capitalize()} Registration", False, f"Error: {e}")
            return False

    # ------------------------
    # ADMIN PAGES
    # ------------------------
    def test_admin_login_and_pages(self):
        print("🧭 2. Testing Admin Dashboard Pages...")
        self.safe_get("/user/login/")
        try:
            self.driver.execute_script(f"""
                document.querySelector('input[name="email"]').value = '{self.admin["email"]}';
                document.querySelector('input[name="password"]').value = '{self.admin["password"]}';
            """)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(3)

            if "dashboard" in self.driver.page_source.lower():
                self.record("Admin Login", True)
                pages = [
                    ("/panel/community/", "Community"),
                    ("/marketplace/admin/", "Marketplace"),
                    ("/panel/learn/", "Learn"),
                    ("/rewards/admin/", "Rewards"),
                    ("/panel/my-profile/", "Profile"),
                    ("/panel/settings/", "Settings"),
                ]
                for url, name in pages:
                    self.safe_get(url)
                    time.sleep(1)
                    if "error" not in self.driver.page_source.lower():
                        self.record(f"Admin {name} Page", True)
                    else:
                        self.record(f"Admin {name} Page", False, "Error content found")
            else:
                self.record("Admin Login", False, "Redirected elsewhere")
        except Exception as e:
            self.record("Admin Login", False, str(e))

    # ------------------------
    # HOUSEHOLD TESTS
    # ------------------------
    def test_household_pages(self):
        print("🏠 3. Testing Household Pages...")
        if not self._login_user("household"):
            return

        pages = [
            ("/household/dashboard/", "Dashboard"),
            ("/household/community/", "Community"),
            ("/marketplace/household/", "Marketplace"),
            ("/education/household/", "Learn"),
            ("/rewards/household/", "Rewards"),
            ("/notifications/", "Notifications"),
            ("/household/profile/", "Profile"),
            ("/household/settings/", "Settings"),
        ]

        for url, name in pages:
            self.safe_get(url)
            time.sleep(1.5)
            if "error" not in self.driver.page_source.lower():
                self.record(f"Household {name} Page", True)
            else:
                self.record(f"Household {name} Page", False, "Page failed to load")

    # ------------------------
    # COLLECTOR TESTS
    # ------------------------
    def test_collector_login(self):
        print("♻️ 4. Testing Collector Login...")
        self._login_user("collector")

    # ------------------------
    # BUYER TESTS
    # ------------------------
    def test_buyer_marketplace(self):
        print("🛒 5. Testing Buyer Marketplace Buy Flow...")
        if not self._login_user("buyer"):
            return

        self.safe_get("/marketplace/buyer/")
        time.sleep(2)

        buy_buttons = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Buy')] | //button[contains(text(), 'Buy')]")
        if not buy_buttons:
            self.record("Marketplace Buy", False, "No Buy buttons found")
            return

        try:
            self.driver.execute_script("arguments[0].click();", buy_buttons[0])
            time.sleep(2)
            current_url = self.driver.current_url.lower()
            if "detail" in current_url or "view" in current_url:
                self.record("Marketplace Buy", True, "Redirected to product detail page ✅")
            else:
                self.record("Marketplace Buy", False, "Did not redirect correctly")
        except Exception as e:
            self.record("Marketplace Buy", False, str(e))

    # ------------------------
    # LOGIN HELPER
    # ------------------------
    def _login_user(self, role):
        creds = self.dummy_users.get(role)
        if not creds:
            self.record(f"{role.capitalize()} Login", False, "User not registered")
            return False

        self.safe_get("/user/login/")
        try:
            email_field = self.wait.until(EC.element_to_be_clickable((By.NAME, "email")))
            email_field.clear()
            email_field.send_keys(creds["email"])

            pw_field = self.driver.find_element(By.NAME, "password")
            pw_field.clear()
            pw_field.send_keys(creds["password"])

            submit_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"))
            )
            self.driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(3)

            if any(k in self.driver.page_source.lower() for k in ["dashboard", "logout", "welcome"]):
                self.record(f"{role.capitalize()} Login", True)
                return True
            else:
                self.record(f"{role.capitalize()} Login", False, "No dashboard found")
                return False
        except Exception as e:
            self.record(f"{role.capitalize()} Login", False, str(e))
            return False

    # ------------------------
    # CLEANUP
    # ------------------------
    def cleanup_users(self):
        print("🧹 Cleaning up dummy users...")
        try:
            import django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Recycle.settings")
            django.setup()
            from User.models import User
            deleted = 0
            for email in self.created_test_users:
                try:
                    User.objects.get(email=email).delete()
                    deleted += 1
                except User.DoesNotExist:
                    pass
            print(f"✅ Deleted {deleted} dummy users")
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

    # ------------------------
    # MAIN TEST RUNNER
    # ------------------------
    def run_all_tests(self):
        print("=" * 60)
        print("🚀 Starting RecyConnect Selenium Tests")
        print("=" * 60)

        if not self.setup_driver():
            print("❌ Browser setup failed.")
            return

        try:
            self.test_landing_page()
            for role in ["household", "collector", "buyer"]:
                self.register_user(role)
            self.test_admin_login_and_pages()
            self.test_household_pages()
            self.test_collector_login()
            self.test_buyer_marketplace()
        finally:
            self.cleanup_users()
            self.teardown_driver()
            self.print_summary()

    def print_summary(self):
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        success = (passed / total * 100) if total > 0 else 0
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print(f"Total: {total} | ✅ Passed: {passed} | ❌ Failed: {failed}")
        print(f"📈 Success Rate: {success:.1f}%")
        for name, status, detail in self.test_results["details"]:
            print(f"{status} → {name}")
            if detail:
                print(f"   ↳ {detail}")
        print("=" * 60)


if __name__ == "__main__":
    tester = RecyConnectTester()
    tester.run_all_tests()
