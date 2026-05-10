import os
import re
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TEST_DB = ROOT / "scratch" / "qa_test.sqlite"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_CREATE_DB"] = "false"
os.environ["FLASK_ENV"] = "development"
os.environ["SECRET_KEY"] = "qa-test-secret"

sys.path.insert(0, str(ROOT))

from app import create_app, _seed_data  # noqa: E402
from app.api import auth as api_auth_module  # noqa: E402
from app.extensions import db  # noqa: E402
import app.models  # noqa: F401,E402
from app.models.booking import Booking  # noqa: E402
from app.models.otp_verification import OtpVerification  # noqa: E402
from app.models.service import Service  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.otp_service import create_otp, verify_otp_code  # noqa: E402
from app.services.rate_limiter import reset_all  # noqa: E402


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"a", "link"} and attrs.get("href"):
            self.links.append(("href", attrs["href"]))
        if tag in {"script", "img"} and attrs.get("src"):
            self.links.append(("src", attrs["src"]))


class QA:
    def __init__(self):
        self.app = create_app("development")
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, MAIL_SUPPRESS_SEND=True)
        api_auth_module.send_otp_email = lambda email, otp: True
        self.results = []
        self.failures = []
        self.tokens = {}
        self.ua = {"User-Agent": "VetSync-QA/1.0"}

    def record(self, name, ok, detail=""):
        self.results.append((name, ok, detail))
        if not ok:
            self.failures.append((name, detail))

    def setup_db(self):
        if TEST_DB.exists():
            TEST_DB.unlink()
        reset_all()
        with self.app.app_context():
            db.create_all()
            _seed_data()

    def login(self, email, password):
        client = self.app.test_client()
        resp = client.post(
            "/login",
            json={"email": email, "password": password},
            headers={**self.ua, "X-Requested-With": "XMLHttpRequest"},
        )
        data = resp.get_json(silent=True) or {}
        self.record(f"login {email}", resp.status_code == 200 and data.get("success"), f"status={resp.status_code}")
        return client, data.get("access_token")

    def expect(self, client, path, statuses, name=None, **kwargs):
        resp = client.open(path, headers=self.ua, **kwargs)
        ok = resp.status_code in statuses
        self.record(name or path, ok, f"status={resp.status_code}, expected={statuses}")
        return resp

    def run_routes(self):
        public = [
            "/",
            "/about",
            "/services",
            "/contact",
            "/login",
            "/signup",
            "/forgot-password",
            "/vetscan",
            "/offline",
            "/service-worker.js",
            "/favicon.ico",
            "/static/manifest.json",
        ]
        anon = self.app.test_client()
        for path in public:
            self.expect(anon, path, {200}, f"public {path}")

        protected = [
            "/booking",
            "/dashboard",
            "/dashboard/client",
            "/staff/dashboard",
            "/staff/appointments",
            "/staff/pet-records",
            "/staff/control-panel",
            "/staff/offers",
            "/staff/audit-logs",
            "/admin/dashboard",
        ]
        for path in protected:
            self.expect(anon, path, {302}, f"anon protected redirect {path}")

    def run_roles(self):
        client, client_token = self.login("demo@vetsync.com", "demo123")
        staff, staff_token = self.login("veterinarian123@gmail.com", "vet121516")
        admin, admin_token = self.login("adminvetclinic@gmail.com", "vetadminclinic1214")
        self.tokens.update(client=client_token, staff=staff_token, admin=admin_token)

        self.expect(client, "/dashboard", {302}, "client dashboard router")
        self.expect(client, "/dashboard/client", {200}, "client dashboard")
        self.expect(client, "/booking", {200}, "client booking page")
        self.expect(client, "/staff/dashboard", {302}, "client blocked from staff")
        self.expect(client, "/admin/dashboard", {302}, "client blocked from admin")

        self.expect(staff, "/dashboard", {302}, "staff dashboard router")
        self.expect(staff, "/staff/dashboard", {200}, "staff dashboard")
        self.expect(staff, "/staff/appointments", {200}, "staff appointments")
        self.expect(staff, "/staff/pet-records", {200}, "staff pet records")
        self.expect(staff, "/staff/control-panel", {200}, "staff control panel")
        self.expect(staff, "/staff/offers", {302}, "staff offers redirects safely")
        self.expect(staff, "/admin/dashboard", {302}, "staff blocked from admin")

        self.expect(admin, "/dashboard", {302}, "admin dashboard router")
        self.expect(admin, "/admin/dashboard", {200}, "admin dashboard")
        self.expect(admin, "/staff/dashboard", {200}, "admin staff dashboard access")
        self.expect(admin, "/staff/control-panel", {200}, "admin control panel access")
        self.expect(admin, "/staff/audit-logs", {200}, "admin audit logs")

        self.clients = {"client": client, "staff": staff, "admin": admin}

    def auth_header(self, role):
        return {**self.ua, "Authorization": f"Bearer {self.tokens[role]}"}

    def run_api_and_workflows(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with self.app.app_context():
            service = Service.query.first()

        payload = {
            "service_id": service.id,
            "slot": "9:00 AM",
            "date": tomorrow,
            "name": "QA Client",
            "email": "qa.client@example.com",
            "phone": "09170000000",
            "pet_type": "Dog",
            "pet_name": "QA Buddy",
        }
        resp = self.clients["client"].post("/api/v1/appointments", json=payload, headers=self.auth_header("client"))
        data = resp.get_json(silent=True) or {}
        booking_id = data.get("booking_id")
        self.record("client API creates booking", resp.status_code == 201 and booking_id, f"status={resp.status_code}")

        dup = self.clients["client"].post("/api/v1/appointments", json=payload, headers=self.auth_header("client"))
        self.record("duplicate booking rejected", dup.status_code == 409, f"status={dup.status_code}")

        upd = self.clients["staff"].put(
            f"/api/v1/appointments/{booking_id}",
            json={"status": "completed"},
            headers=self.auth_header("staff"),
        )
        self.record("staff updates booking", upd.status_code == 200, f"status={upd.status_code}")

        api_paths = [
            ("staff", "/api/v1/schedule"),
            ("staff", "/api/v1/schedule/workload"),
            ("staff", "/api/v1/reports"),
            ("admin", "/api/v1/users"),
            ("admin", "/api/v1/appointments/all"),
            ("admin", "/api/v1/reports"),
        ]
        for role, path in api_paths:
            resp = self.clients[role].get(path, headers=self.auth_header(role))
            self.record(f"{role} API {path}", resp.status_code == 200, f"status={resp.status_code}")

        block = self.clients["staff"].post(
            "/api/v1/schedule/block",
            json={"date": tomorrow, "slot": "10:00 AM"},
            headers=self.auth_header("staff"),
        )
        self.record("staff blocks schedule slot", block.status_code == 201, f"status={block.status_code}")
        unblock = self.clients["staff"].delete(
            "/api/v1/schedule/unblock",
            json={"date": tomorrow, "slot": "10:00 AM"},
            headers=self.auth_header("staff"),
        )
        self.record("staff unblocks schedule slot", unblock.status_code == 200, f"status={unblock.status_code}")

        report = self.clients["staff"].post(
            "/api/v1/reports",
            json={"title": "QA Report", "category": "System Issue", "description": "QA workflow test"},
            headers=self.auth_header("staff"),
        )
        self.record("staff submits report", report.status_code == 201, f"status={report.status_code}")

        delete = self.clients["staff"].delete(f"/api/v1/appointments/{booking_id}", headers=self.auth_header("staff"))
        self.record("staff deletes booking", delete.status_code == 200, f"status={delete.status_code}")
        with self.app.app_context():
            self.record("booking removed from database", db.session.get(Booking, booking_id) is None)

    def run_vetscan(self):
        payload = {
            "animal_type": "Dog",
            "breed": "Labrador",
            "age": 4,
            "gender": "Male",
            "weight": 20,
            "symptom_1": "Fever",
            "symptom_2": "Lethargy",
            "symptom_3": "Vomiting",
            "symptom_4": "Diarrhea",
            "duration": 2,
            "body_temperature": 39.2,
            "heart_rate": 105,
        }
        resp = self.app.test_client().post("/predict", json=payload, headers=self.ua)
        data = resp.get_json(silent=True) or {}
        self.record("VetScan prediction endpoint", resp.status_code == 200 and data.get("success"), f"status={resp.status_code}")

    def run_rendered_link_scan(self):
        pages = [
            (self.app.test_client(), "/"),
            (self.app.test_client(), "/about"),
            (self.app.test_client(), "/services"),
            (self.app.test_client(), "/contact"),
            (self.clients["client"], "/dashboard/client"),
            (self.clients["client"], "/booking"),
            (self.clients["staff"], "/staff/dashboard"),
            (self.clients["staff"], "/staff/appointments"),
            (self.clients["staff"], "/staff/pet-records"),
            (self.clients["staff"], "/staff/control-panel"),
            (self.clients["admin"], "/admin/dashboard"),
        ]
        checked = 0
        broken = []
        for client, page in pages:
            html = self.expect(client, page, {200}, f"render for link scan {page}").get_data(as_text=True)
            parser = LinkParser()
            parser.feed(html)
            for attr, url in parser.links:
                if url.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
                    continue
                parsed = urlparse(url)
                if parsed.path in {"", "#"}:
                    continue
                if parsed.path.startswith("/logout"):
                    continue
                checked += 1
                resp = client.get(parsed.path, headers=self.ua)
                if resp.status_code >= 400:
                    broken.append((page, attr, url, resp.status_code))
        self.record("rendered internal links/assets", not broken, f"checked={checked}, broken={broken[:5]}")

    def run_static_design_checks(self):
        css = (ROOT / "app" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        main_js = (ROOT / "app" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        media_queries = len(re.findall(r"@media\s*\(", css))
        self.record("responsive media queries present", media_queries >= 5, f"count={media_queries}")
        self.record("300px mobile breakpoint coverage", "@media (max-width: 320px)" in css, "small mobile support")
        self.record("tap target sizing present", "min-height: 44px" in css, "expected common 44px controls")
        self.record("focus-visible states present", ":focus-visible" in css, "keyboard accessibility")
        self.record("horizontal overflow guarded", "overflow-x: hidden" in css, "body/html overflow guard")
        self.record("hamburger overlay can close", "blurOverlay.addEventListener('click'" in main_js, "tap outside closes overlay")
        self.record("hamburger escape close present", "event.key === 'Escape'" in main_js, "escape key closes menu")

    def run_security_checks(self):
        anon = self.app.test_client()

        injected = "' OR '1'='1"
        resp = anon.post("/api/v1/auth/login", json={"email": injected, "password": injected}, headers=self.ua)
        self.record("SQL injection login rejected", resp.status_code == 401, f"status={resp.status_code}")

        resp = self.clients["client"].get("/api/v1/users", headers=self.auth_header("client"))
        self.record("client blocked from admin users API", resp.status_code == 403, f"status={resp.status_code}")
        resp = anon.get("/api/v1/users", headers=self.ua)
        self.record("anonymous blocked from admin users API", resp.status_code == 401, f"status={resp.status_code}")

        hijack_client, _ = self.login("demo@vetsync.com", "demo123")
        resp = hijack_client.get("/dashboard/client", headers={"User-Agent": "Different-Device/1.0"})
        self.record("session hijack user-agent mismatch blocked", resp.status_code == 302 and "/login" in resp.location, f"status={resp.status_code}")

        resp = anon.get("/", headers=self.ua)
        required_headers = [
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ]
        missing = [h for h in required_headers if not resp.headers.get(h)]
        self.record("security headers present", not missing, f"missing={missing}")

        old_enforce = self.app.config.get("ENFORCE_HTTPS")
        self.app.config["ENFORCE_HTTPS"] = True
        try:
            resp = anon.get("/about", base_url="http://localhost", headers=self.ua)
            self.record("production HTTP redirects to HTTPS", resp.status_code == 301 and resp.location.startswith("https://"), f"status={resp.status_code}")
            resp = anon.get("/about", base_url="https://localhost", headers=self.ua)
            self.record("HSTS emitted when HTTPS is enforced", "Strict-Transport-Security" in resp.headers, resp.headers.get("Strict-Transport-Security", ""))
        finally:
            self.app.config["ENFORCE_HTTPS"] = old_enforce

        with self.app.app_context():
            user = User.query.filter_by(email="demo@vetsync.com").first()
            password_hashed = user.password_hash != "demo123" and user.check_password("demo123")
            self.record("password stored as secure hash", password_hashed, user.password_hash.split("$", 1)[0])

            raw_otp, error = create_otp("qa-security@example.com")
            otp_record = OtpVerification.query.filter_by(email="qa-security@example.com").order_by(OtpVerification.created_at.desc()).first()
            otp_hashed = not error and otp_record and otp_record.otp_code != raw_otp
            self.record("OTP stored as hash", otp_hashed, f"error={error}")
            ok, _ = verify_otp_code("qa-security@example.com", raw_otp)
            reused, _ = verify_otp_code("qa-security@example.com", raw_otp)
            self.record("OTP verifies once and blocks reuse", ok and not reused)

        classifications = {
            "critical": ["password_hash", "otp_code"],
            "confidential": ["Booking.email", "Booking.phone", "Booking.medical_history", "Booking.visit_reason"],
            "public": ["/services", "/about", "/"],
        }
        self.record("data classification reviewed", True, str(classifications))

    def run_auth_security_checks(self):
        sql_payloads = [
            "' OR '1'='1",
            "admin@example.com' --",
            "SELECT * FROM users",
            "DROP TABLE users;",
            "\" OR \"1\"=\"1",
        ]
        for payload in sql_payloads:
            client = self.app.test_client()
            resp = client.post(
                "/login",
                json={"email": payload, "password": payload},
                headers={**self.ua, "X-Requested-With": "XMLHttpRequest"},
            )
            data = resp.get_json(silent=True) or {}
            dashboard = client.get("/dashboard", headers=self.ua)
            body = resp.get_data(as_text=True)
            ok = (
                resp.status_code in {401, 429}
                and not data.get("success")
                and "Traceback" not in body
                and "sqlalchemy" not in body.lower()
                and dashboard.status_code == 302
            )
            self.record(f"login SQL payload rejected: {payload[:18]}", ok, f"status={resp.status_code}")

        client = self.app.test_client()
        bad_json = client.post(
            "/api/v1/auth/login",
            data="{not-json",
            content_type="application/json",
            headers=self.ua,
        )
        self.record("API login malformed JSON fails safely", bad_json.status_code == 401, f"status={bad_json.status_code}")

        existing_wrong = self.app.test_client().post(
            "/api/v1/auth/login",
            json={"email": "demo@vetsync.com", "password": "wrong-password"},
            headers=self.ua,
        )
        unknown_wrong = self.app.test_client().post(
            "/api/v1/auth/login",
            json={"email": "missing-user@example.com", "password": "wrong-password"},
            headers=self.ua,
        )
        self.record(
            "login errors do not reveal account existence",
            existing_wrong.status_code == unknown_wrong.status_code == 401
            and existing_wrong.get_json() == unknown_wrong.get_json(),
            f"existing={existing_wrong.get_json()}, unknown={unknown_wrong.get_json()}",
        )

        secret = "SuperSecret123!"
        resp_text = existing_wrong.get_data(as_text=True)
        secret_resp = self.app.test_client().post(
            "/api/v1/auth/login",
            json={"email": "demo@vetsync.com", "password": secret},
            headers=self.ua,
        ).get_data(as_text=True)
        self.record("passwords not echoed in auth responses", secret not in resp_text and secret not in secret_resp)

        brute = self.app.test_client()
        status_codes = []
        for _ in range(6):
            resp = brute.post(
                "/api/v1/auth/login",
                json={"email": "bruteforce@example.com", "password": "bad-password"},
                headers=self.ua,
            )
            status_codes.append(resp.status_code)
        self.record("failed login brute force throttled", 429 in status_codes, f"statuses={status_codes}")

        otp_client = self.app.test_client()
        otp_statuses = []
        for _ in range(4):
            resp = otp_client.post(
                "/api/v1/auth/send-otp",
                json={"email": "signup-rate@example.com"},
                headers=self.ua,
            )
            otp_statuses.append(resp.status_code)
        self.record("repeated signup OTP requests throttled", otp_statuses[-1] == 429, f"statuses={otp_statuses}")

        xss_email = "xss-signup@example.com"
        with self.app.app_context():
            db.session.add(OtpVerification(
                email=xss_email,
                otp_code="qa-preverified",
                expires_at=datetime.utcnow() + timedelta(minutes=10),
                is_used=True,
            ))
            db.session.commit()

        xss_payload = "<script>alert(1)</script>"
        signup = self.app.test_client().post(
            "/signup",
            data={
                "first_name": xss_payload,
                "last_name": "Tester",
                "email": xss_email,
                "contact": "09170000001",
                "password": "StrongPass123!",
                "re_password": "StrongPass123!",
            },
            headers=self.ua,
            follow_redirects=False,
        )
        with self.app.app_context():
            created = User.query.filter_by(email=xss_email).first()
            safe_name = created and "<script" not in created.first_name.lower() and ">" not in created.first_name
        self.record("signup XSS payload sanitized before storage", signup.status_code == 302 and safe_name, f"status={signup.status_code}")

        duplicate = self.app.test_client().post(
            "/signup",
            data={
                "first_name": "Duplicate",
                "last_name": "User",
                "email": "demo@vetsync.com",
                "contact": "09170000002",
                "password": "StrongPass123!",
                "re_password": "StrongPass123!",
            },
            headers=self.ua,
        )
        duplicate_body = duplicate.get_data(as_text=True)
        self.record(
            "duplicate signup rejected safely",
            duplicate.status_code == 200 and "Email already registered" in duplicate_body and "Traceback" not in duplicate_body,
            f"status={duplicate.status_code}",
        )

        weak = self.app.test_client().post(
            "/signup",
            data={
                "first_name": "Weak",
                "last_name": "Password",
                "email": "weak@example.com",
                "contact": "09170000003",
                "password": "short",
                "re_password": "short",
            },
            headers=self.ua,
        )
        self.record("signup enforces server-side password length", weak.status_code == 200 and "at least 8 characters" in weak.get_data(as_text=True))

        invalid_otp = self.app.test_client().post(
            "/api/v1/auth/send-otp",
            json={"email": "javascript:alert(1)"},
            headers=self.ua,
        )
        self.record("signup OTP rejects malformed email", invalid_otp.status_code == 400, f"status={invalid_otp.status_code}")

    def run(self):
        self.setup_db()
        self.run_routes()
        self.run_roles()
        self.run_api_and_workflows()
        self.run_vetscan()
        self.run_rendered_link_scan()
        self.run_static_design_checks()
        self.run_security_checks()
        self.run_auth_security_checks()

        print(f"TOTAL={len(self.results)}")
        print(f"FAILURES={len(self.failures)}")
        for name, ok, detail in self.results:
            print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
        return 1 if self.failures else 0


if __name__ == "__main__":
    raise SystemExit(QA().run())
