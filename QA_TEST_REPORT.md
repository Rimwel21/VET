# VetSync System Test Run Report

Date: 2026-05-02

## Scope

This run covered end-to-end functionality, navigation, role access, UI/UX responsiveness, PWA shell assets, and information-assurance controls for the VetSync Clinical Ecosystem.

Validated modules:

- Public pages: Home, About, Services, Contact, Login, Signup, Forgot Password, VetScan, Offline
- Client: dashboard, booking flow, appointment history
- Staff: dashboard, appointments, pet records, submitted reports, control panel, schedule actions
- Admin: dashboard, users API, appointments API, reports API, audit logs
- Shared shell: navbar, hamburger menu, footer, service worker, manifest, static assets
- Security: RBAC, session protection, SQL injection rejection, login/signup attack payloads, brute-force throttling, password/OTP hashing, HTTPS/HSTS enforcement mode, security headers

## System Documentation With Code Location Mapping

Target industry: Veterinary Healthcare Services

This section maps the VetSync defense documentation to the actual implementation folders, blueprints, classes, functions, templates, and static assets in this repository.

### 1. Executive Summary And Problem Definition

The problem addressed by VetSync is fragmented veterinary clinic operations: appointment scheduling, patient medical records, account recovery, client communication, and staff workflows can become inconsistent when handled through separate tools. VetSync centralizes these workflows into one Flask application so the web dashboard and mobile PWA share the same backend, database models, and API layer.

Implementation locations:

| Area | Where it is implemented |
| --- | --- |
| Flask application factory | `app/__init__.py`, function `create_app()` |
| Central extension setup | `app/extensions.py` |
| Web route registration | `app/routes/__init__.py`, function `register_blueprints()` |
| API gateway registration | `app/api/__init__.py`, blueprint `api_v1` with prefix `/api/v1` |
| Database models | `app/models/` |
| Homepage | `app/templates/index.html`, served by `app/routes/main.py`, function `index()` at `/` |
| Shared page shell | `app/templates/base.html` |
| PWA shell | `app/static/manifest.json` and `app/static/service-worker.js` |

### 2. System Integration And Architecture

VetSync uses a modular RESTful Flask architecture. Each business area is separated into a Blueprint, but all Blueprints are registered into the same Flask app and use the same SQLAlchemy database session.

Blueprint and module map:

| Blueprint / Module | File | Main responsibility |
| --- | --- | --- |
| `main_bp` | `app/routes/main.py` | Public pages, homepage, services, contact, offline page, service worker, favicon |
| `auth_bp` | `app/routes/auth.py` | Web login, signup, forgot password, logout |
| `dashboard_bp` | `app/routes/dashboard.py` | Role-based dashboard routing for client, staff, and admin |
| `booking_bp` | `app/routes/booking.py` | Web booking page and form-based booking actions |
| `staff_bp` | `app/routes/staff.py` | Staff appointments, pet records, reports, control panel, schedule actions |
| `vetscan_bp` | `app/routes/vetscan.py` | VetScan page, prediction endpoint, breed lookup |
| `api_v1` | `app/api/__init__.py` | Parent API gateway for `/api/v1/*` endpoints |
| `api_auth_bp` | `app/api/auth.py` | API login, OTP, password reset |
| `api_appointments_bp` | `app/api/appointments.py` | Appointment API create/read/update/delete |
| `api_availability_bp` | `app/api/availability.py` | Staff schedule and slot blocking API |
| `api_chatbot_bp` | `app/api/chatbot.py` | ASTRID chatbot and medical redirect behavior |
| `api_users_bp` | `app/api/users.py` | Admin/user API operations |
| `api_reports_bp` | `app/api/reports.py` | Staff/admin report API operations |
| `api_notifications_bp` | `app/api/notifications.py` | Notifications API |
| `api_push_bp` | `app/api/push.py` | PWA push notification API |

One-system logic:

- The web dashboard and mobile PWA are not separate systems. They are separate interfaces served by the same Flask application.
- Both interfaces use the same SQLAlchemy models in `app/models/`.
- API requests are routed through the same parent gateway in `app/api/__init__.py`.
- Shared authentication and security behavior is implemented in `app/middleware/` and `app/services/`.
- The mobile/PWA layer has no separate database. Its configuration is in `app/static/manifest.json`, its offline/runtime shell is in `app/static/service-worker.js`, and its pages are still served by Flask templates in `app/templates/`.

Architecture diagram explanation mapped to code:

| Architecture layer | Repository location | Defense explanation |
| --- | --- | --- |
| Presentation layer | `app/templates/*.html`, `app/static/css/`, `app/static/js/` | Jinja2 templates and JavaScript render the web and PWA interfaces. These are thin clients because they call Flask routes/APIs instead of owning clinical data. |
| Application layer | `app/routes/`, `app/api/`, `app/services/`, `app/middleware/` | Flask Blueprints receive requests, decorators enforce roles, services perform auth/OTP/prediction logic, and middleware applies session and transport protections. |
| Data layer | `app/models/`, migrations in `migrations/` | SQLAlchemy models define the single source of truth for users, bookings, OTPs, availability, reports, notifications, contacts, and services. |

### 3. Technical Implementation: Python Web And Mobile

Backend core:

| Feature | Location |
| --- | --- |
| Python/Flask app startup | `run.py` |
| App creation and Blueprint wiring | `app/__init__.py`, `create_app()` |
| Configuration | `config.py` |
| SQLAlchemy/Mail/Migration extensions | `app/extensions.py` |
| JWT token creation/verification | `app/services/auth_service.py`, functions `create_jwt_token()` and `decode_jwt_token()` |
| Login rate limiting | `app/services/rate_limiter.py` and usage in `app/api/auth.py` / `app/routes/auth.py` |
| Input sanitization | `app/utils/sanitize.py`, function `clean_input()` |

Endpoint map:

| Endpoint | Method | File / function | Purpose |
| --- | --- | --- | --- |
| `/` | GET | `app/routes/main.py`, `index()` | Homepage, rendered by `app/templates/index.html` |
| `/login` | GET/POST | `app/routes/auth.py`, `login()` | Web login page and form login |
| `/signup` | GET/POST | `app/routes/auth.py`, `signup()` | Web registration with OTP validation |
| `/forgot-password` | GET | `app/routes/auth.py`, `forgot_password()` | Password recovery page |
| `/dashboard` | GET | `app/routes/dashboard.py`, `dashboard()` | Role-aware dashboard redirect |
| `/dashboard/client` | GET | `app/routes/dashboard.py`, `client_dashboard()` | Client dashboard, `app/templates/dashboard.html` |
| `/staff/dashboard` | GET | `app/routes/dashboard.py`, `staff_dashboard()` | Staff dashboard, `app/templates/staff_dashboard.html` |
| `/admin/dashboard` | GET | `app/routes/dashboard.py`, `admin_dashboard()` | Admin dashboard, `app/templates/admin_dashboard.html` |
| `/booking` | GET | `app/routes/booking.py`, `booking_page()` | Booking UI, `app/templates/booking_page.html` |
| `/book` | POST | `app/routes/booking.py`, `book()` | Form-based appointment creation |
| `/vetscan` | GET | `app/routes/vetscan.py`, `vetscan()` | VetScan UI, `app/templates/vetscan.html` |
| `/predict` | POST | `app/routes/vetscan.py`, `predict()` | VetScan disease prediction API |
| `/api/v1/auth/login` | POST | `app/api/auth.py`, `api_login()` | API authentication and JWT issuing |
| `/api/v1/auth/send-otp` | POST | `app/api/auth.py`, `send_otp_endpoint()` | Signup/account OTP request |
| `/api/v1/auth/verify-otp` | POST | `app/api/auth.py`, `verify_otp_endpoint()` | OTP verification |
| `/api/v1/auth/forgot-password` | POST | `app/api/auth.py`, `forgot_password_endpoint()` | Password reset OTP request |
| `/api/v1/auth/verify-reset-otp` | POST | `app/api/auth.py`, `verify_reset_otp_endpoint()` | Reset OTP verification and reset-token issue |
| `/api/v1/auth/reset-password` | POST | `app/api/auth.py`, `reset_password_endpoint()` | Password reset completion |
| `/api/v1/appointments` | GET/POST | `app/api/appointments.py`, `appointments()` | Fetch or create appointments |
| `/api/v1/appointments/<booking_id>` | PUT/DELETE | `app/api/appointments.py`, `update_appointment()` / `delete_appointment()` | Staff/admin appointment updates |
| `/api/v1/chatbot/astrid` | POST | `app/api/chatbot.py`, `astrid()` | ASTRID system navigation chatbot |
| `/api/v1/schedule` | GET | `app/api/availability.py`, `get_schedule()` | Staff schedule lookup |
| `/api/v1/schedule/block` | POST | `app/api/availability.py`, `block_time()` | Block appointment slots |
| `/api/v1/schedule/unblock` | DELETE | `app/api/availability.py`, `unblock_time()` | Unblock appointment slots |

Core data models:

| Model class | File | Purpose |
| --- | --- | --- |
| `User` | `app/models/user.py` | User identity, role, password hash, active status |
| `Booking` | `app/models/booking.py` | Appointment, owner, pet, medical, payment, status, handler fields |
| `OtpVerification` | `app/models/otp_verification.py` | Hashed OTP code, expiry, attempts, reset token, single-use status |
| `DoctorAvailability` | `app/models/availability.py` | Staff schedule and blocked time-slot state |
| `Service` | `app/models/service.py` | Clinic service catalog |
| `Report` | `app/models/report.py` | Clinical/operational report records |
| `Notification` | `app/models/notification.py` | User notifications |
| `Contact` | `app/models/contact.py` | Contact form submissions |

### 4. Information Assurance And Security Strategy

Security implementation map:

| Control | Location | Implementation detail |
| --- | --- | --- |
| Password hashing | `app/models/user.py`, methods `set_password()` and `check_password()` | Uses Werkzeug password hashing, not plaintext storage |
| OTP hashing | `app/services/otp_service.py`, function `create_otp()` | Generates 6-digit OTP through `secrets`, stores only `generate_password_hash(raw_otp)` |
| OTP verification | `app/services/otp_service.py`, function `verify_otp_code()` | Enforces expiry, single use, and max attempts |
| OTP reset token | `app/services/otp_service.py`, functions `verify_reset_otp()` and `reset_password_with_token()` | Issues short-lived token after OTP verification |
| Brute-force login throttle | `app/services/rate_limiter.py`, used by `app/api/auth.py` and `app/routes/auth.py` | Returns `429` after repeated failed login attempts |
| RBAC decorators | `app/middleware/decorators.py` | `login_required`, `admin_required`, `staff_required`, `jwt_required`, `role_required()` |
| Session integrity | `app/middleware/security.py`, `register_security_hooks()` | Checks session IP and User-Agent fingerprint |
| HTTPS/HSTS/security headers | `app/middleware/security.py`, `add_security_headers()` and `_https_required()` | Enforces production HTTPS and emits security headers |
| SQL injection reduction | `app/models/` queried through SQLAlchemy ORM | Tested auth and booking flows use ORM queries instead of raw string SQL |

Data classification mapped to storage:

| Classification | Data examples | Location |
| --- | --- | --- |
| Critical | Password hashes, OTP hashes, reset tokens | `app/models/user.py`, `app/models/otp_verification.py` |
| Critical | Medical notes, clinical diagnosis output, visit reasons | `app/models/booking.py`, `app/models/report.py`, `app/services/prediction_service.py` |
| Confidential | Names, emails, phone numbers, address, pet details | `app/models/user.py`, `app/models/booking.py`, `app/models/contact.py` |
| Public | Services, about/contact clinic content, PWA metadata | `app/templates/services.html`, `app/templates/about.html`, `app/templates/contact.html`, `app/static/manifest.json` |

### 5. Reliability And Sustainability Plan

Maintainability is achieved through folder-level separation:

| Concern | Location |
| --- | --- |
| Route handlers | `app/routes/` |
| JSON APIs | `app/api/` |
| Business services | `app/services/` |
| Database models | `app/models/` |
| Security middleware and decorators | `app/middleware/` |
| HTML templates | `app/templates/` |
| Static CSS/JavaScript/images/PWA files | `app/static/` |
| ML source and datasets | `ml/` |
| Database migrations | `migrations/` |
| QA automation | `scratch/full_system_qa.py` |

The ML logic is isolated from page rendering. VetScan routing lives in `app/routes/vetscan.py`, but prediction logic lives in `app/services/prediction_service.py`. ASTRID API behavior lives in `app/api/chatbot.py`, while the more advanced hybrid ML class is in `ml/chatbot_ml.py`.

### 6. Machine Learning Implementation: ASTRID And VetScan

ASTRID navigation chatbot:

| Feature | Location |
| --- | --- |
| API endpoint `/api/v1/chatbot/astrid` | `app/api/chatbot.py`, function `astrid()` |
| Medical intercept keywords | `app/api/chatbot.py`, constant `MEDICAL_KEYWORDS` |
| Scripted navigation FAQ responses | `app/api/chatbot.py`, constant `FAQ_ANSWERS` |
| Hybrid ML class | `ml/chatbot_ml.py`, class `AstridHybridML` |
| Hybrid response methods | `ml/chatbot_ml.py`, methods `check_emergency_override()` and `get_smart_response()` |
| Processed knowledge base | `ml/dataset/processed/knowledge_base.json` |
| Cached embeddings | `ml/dataset/processed/embeddings.npy` |

ASTRID safety behavior:

- It is documented and implemented as a system navigation assistant, not a medical diagnosis bot.
- Symptom or disease-related text is intercepted by `MEDICAL_KEYWORDS` in `app/api/chatbot.py`.
- Medical inputs return `mode: vetscan_redirect`, pushing the user toward VetScan instead of a free-form chatbot answer.

VetScan diagnostic engine:

| Feature | Location |
| --- | --- |
| VetScan page route | `app/routes/vetscan.py`, function `vetscan()` |
| Prediction API route | `app/routes/vetscan.py`, function `predict()` |
| Prediction service | `app/services/prediction_service.py`, function `predict_disease()` |
| Feature builder | `app/services/prediction_service.py`, function `build_features()` |
| Severity mapper | `app/services/prediction_service.py`, function `get_severity()` |
| Model metadata | `ml/model/metadata.json` |
| Serialized model | `ml/model/disease_model.pkl` |
| Serialized encoders | `ml/model/encoders.pkl` |
| Clinical datasets | `ml/dataset/clinical/` |
| VetScan frontend JavaScript | `app/static/js/vetscan.js` |
| VetScan styles | `app/static/css/vetscan.css` |

### 7. Secure OTP Authentication System

OTP implementation details:

| Requirement | Location |
| --- | --- |
| 6-digit OTP generation | `app/services/otp_service.py`, function `generate_secure_otp()` |
| Secure random source | `secrets.choice()` in `app/services/otp_service.py` |
| Hashed OTP storage | `app/services/otp_service.py`, function `create_otp()` |
| OTP database table/model | `app/models/otp_verification.py`, class `OtpVerification` |
| 5-minute expiration | `app/services/otp_service.py`, `expires_at = datetime.utcnow() + timedelta(minutes=5)` |
| Max 5 verification attempts | `app/services/otp_service.py`, function `verify_otp_code()` |
| Max 3 OTP requests per minute | `app/services/otp_service.py`, function `create_otp()` |
| Single-use OTP | `app/models/otp_verification.py`, field `is_used`; enforced by `verify_otp_code()` |
| OTP modal component | `app/templates/components/otp_modal.html` |
| Forgot password modal component | `app/templates/components/forgot_password_modal.html` |
| OTP frontend logic | `app/static/js/otp_handler.js` |
| Forgot password frontend logic | `app/static/js/forgot_password_handler.js` |

### 8. UI/UX Design And Navigation Flow

Template and route mapping:

| User-facing area | Route | Template |
| --- | --- | --- |
| Landing page / homepage | `/` | `app/templates/index.html` |
| About page | `/about` | `app/templates/about.html` |
| Services page | `/services` | `app/templates/services.html` |
| Contact page | `/contact` | `app/templates/contact.html` |
| Login | `/login` | `app/templates/login.html` |
| Signup | `/signup` | `app/templates/signup.html` |
| Forgot password | `/forgot-password` | `app/templates/forgot_password.html` |
| Client dashboard | `/dashboard/client` | `app/templates/dashboard.html` |
| Staff dashboard | `/staff/dashboard` | `app/templates/staff_dashboard.html` |
| Staff appointments | `/staff/appointments` | `app/templates/staff_appointments.html` |
| Staff pet records | `/staff/pet-records` | `app/templates/staff_pet_records.html` |
| Staff control panel | `/staff/control-panel` | `app/templates/staff_control_panel.html` |
| Admin dashboard | `/admin/dashboard` | `app/templates/admin_dashboard.html` |
| Admin audit logs | `/staff/audit-logs` | `app/templates/admin_audit_logs.html` |
| VetScan | `/vetscan` | `app/templates/vetscan.html` |
| Appointment booking | `/booking` | `app/templates/booking_page.html` |
| Offline PWA fallback | `/offline` | `app/templates/offline.html` |
| ASTRID chatbot component | included where rendered | `app/templates/chatbot.html` |

Visual implementation:

| Asset type | Location |
| --- | --- |
| Shared UI styles | `app/static/css/style.css` |
| VetScan-specific styles | `app/static/css/vetscan.css` |
| Shared JavaScript | `app/static/js/main.js` |
| VetScan JavaScript | `app/static/js/vetscan.js` |
| PWA manifest | `app/static/manifest.json` |
| Service worker | `app/static/service-worker.js` |
| PWA icons/images | `app/static/images/` |

### 9. Code Structure Mapping

| Component | Folder / file | Class / function / object |
| --- | --- | --- |
| Flask application factory | `app/__init__.py` | `create_app()` |
| Blueprint registration | `app/routes/__init__.py` | `register_blueprints()` |
| API gateway | `app/api/__init__.py` | `api_v1`, `register_api()` |
| Homepage | `app/templates/index.html` and `app/routes/main.py` | `index()` |
| Authentication web routes | `app/routes/auth.py` | `auth_bp`, `signup()`, `login()`, `forgot_password()`, `logout()` |
| Authentication API | `app/api/auth.py` | `api_auth_bp`, `api_login()`, OTP/reset functions |
| OTP service | `app/services/otp_service.py` | `generate_secure_otp()`, `create_otp()`, `verify_otp_code()` |
| Auth/JWT service | `app/services/auth_service.py` | `create_jwt_token()`, `decode_jwt_token()` |
| Rate limiter | `app/services/rate_limiter.py` | `is_limited()`, `record_failure()`, `clear_attempts()` |
| Security middleware | `app/middleware/security.py` | `register_security_hooks()` |
| RBAC decorators | `app/middleware/decorators.py` | `login_required`, `admin_required`, `staff_required`, `jwt_required`, `role_required()` |
| Staff logic | `app/routes/staff.py` | `staff_bp`, appointment/report/control-panel functions |
| Booking logic | `app/routes/booking.py`, `app/services/booking_service.py` | `booking_bp`, booking helper logic |
| Appointment API | `app/api/appointments.py` | `api_appointments_bp` |
| Schedule API | `app/api/availability.py` | `api_availability_bp` |
| ASTRID API | `app/api/chatbot.py` | `api_chatbot_bp`, `astrid()` |
| ASTRID hybrid ML | `ml/chatbot_ml.py` | `AstridHybridML` |
| VetScan route | `app/routes/vetscan.py` | `vetscan_bp`, `vetscan()`, `predict()` |
| VetScan ML service | `app/services/prediction_service.py` | `predict_disease()`, `build_features()`, `get_severity()` |
| User model | `app/models/user.py` | `User` |
| Booking model | `app/models/booking.py` | `Booking` |
| OTP model | `app/models/otp_verification.py` | `OtpVerification` |
| Availability model | `app/models/availability.py` | `DoctorAvailability` |
| UI styles | `app/static/css/style.css` | Shared CSS rules |
| PWA config | `app/static/manifest.json` | Web app manifest |
| Service worker | `app/static/service-worker.js` | Offline/PWA shell behavior |

## Environment

- Local app: Flask test client
- Test database: isolated SQLite database at `scratch/qa_test.sqlite`
- Existing development/production database data was not mutated by the automated QA runner.
- Browser screenshots were not captured because Playwright is not installed in this workspace.
- True TLS 1.3 certificate negotiation cannot be proven with Flask's local test client; deployment must still be checked with a real HTTPS endpoint.

## Automated Result

- Full QA runner: `scratch/full_system_qa.py`
- Total checks: 102
- Failures after fixes: 0

Validation commands:

```powershell
python scratch\full_system_qa.py
python -m compileall app scratch\full_system_qa.py config.py
node --check app\static\js\main.js
node --check app\static\js\vetscan.js
node --check app\static\service-worker.js
```

All passed.

## Issues Found, Fixes, And Retest

### 1. Staff Control Panel page had no registered route

Impact level: Medium

Description:

`staff_control_panel.html` existed but `/staff/control-panel` was not registered.

Steps to reproduce:

1. Log in as staff or admin.
2. Visit `/staff/control-panel`.
3. The page was unreachable before the fix.

Impact:

Staff/admin users could not reliably access schedule management and operational reporting controls.

Fix applied:

Added `staff.control_panel` at `/staff/control-panel`, protected by staff/admin access, and supplied the `bookings_json` data expected by the template.

Retest result:

- Staff `/staff/control-panel`: `200`
- Admin `/staff/control-panel`: `200`
- Anonymous `/staff/control-panel`: `302` redirect to login

### 2. Staff Offers route pointed to a missing template

Impact level: Medium

Description:

`/staff/offers` attempted to render `staff_offers.html`, but the template does not exist.

Steps to reproduce:

1. Log in as staff.
2. Visit `/staff/offers`.
3. The route could fail with a missing template error before the fix.

Impact:

This was a broken staff route and a future navigation hazard.

Fix applied:

Changed `/staff/offers` to redirect to the existing Staff Control Panel.

Retest result:

- Staff `/staff/offers`: `302` safe redirect
- Anonymous `/staff/offers`: `302` redirect to login

### 3. Staff Control Panel schedule loader used a non-existent API path

Impact level: Medium

Description:

The Control Panel requested:

```text
/api/v1/schedule/blocked
```

The actual endpoint is:

```text
/api/v1/schedule
```

Steps to reproduce:

1. Log in as staff.
2. Open Staff Control Panel.
3. Open Manage Schedule.
4. Existing blocked-slot state could fail to load.

Impact:

Staff could see incorrect slot availability, creating scheduling errors.

Fix applied:

Updated the Control Panel JavaScript to request `/api/v1/schedule`.

Retest result:

- Staff `/api/v1/schedule`: `200`
- Staff `/api/v1/schedule/block`: `201`
- Staff `/api/v1/schedule/unblock`: `200`

### 4. Staff/Admin navigation did not expose Control Panel

Impact level: Low

Description:

The Control Panel template existed, but authenticated staff/admin navigation did not include a visible link.

Steps to reproduce:

1. Log in as staff or admin.
2. Inspect top navigation.
3. Control Panel was not reachable through normal navigation before the fix.

Impact:

The module was hidden from normal user workflows.

Fix applied:

Added Control Panel links for staff and admin users in the shared base template.

Retest result:

- Staff navigation renders with Control Panel link.
- Admin navigation renders with Control Panel link.
- Rendered internal link scan checked 243 references and found 0 broken links/assets.

### 5. Production transport security was not explicitly enforced

Impact level: Critical for production deployment

Description:

The system had secure cookie production settings, but there was no explicit production HTTPS redirect or HSTS header emission in middleware.

Steps to reproduce:

1. Enable production-like transport enforcement.
2. Request an HTTP URL.
3. Before the fix, the app did not enforce an application-level redirect/HSTS policy.

Impact:

Without HTTPS enforcement and HSTS, users are more exposed to downgrade and man-in-the-middle risks if deployment infrastructure is misconfigured.

Fix applied:

Added `ENFORCE_HTTPS` configuration. Production defaults to enabled. Middleware now redirects HTTP to HTTPS when enforcement is enabled and emits:

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

Also added:

- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

Retest result:

- Production HTTP request redirects to HTTPS: `301`
- HSTS emitted when HTTPS enforcement is active: passed
- Required security headers present: passed

### 6. Login brute-force protection was missing

Impact level: Critical for public authentication endpoints

Description:

Login failures were handled safely, but repeated failed attempts were not throttled.

Steps to reproduce:

1. Submit repeated invalid login attempts to `/api/v1/auth/login`.
2. Before the fix, attempts continued to return normal invalid-credential responses without a lockout or delay response.

Impact:

Attackers could automate credential guessing with no application-level slowing mechanism.

Fix applied:

Added a lightweight failed-login limiter keyed by client IP and email. Both web login and API login now return `429` after repeated failed attempts. Successful login clears the failed-attempt bucket.

Retest result:

- Six rapid failed API login attempts returned `[401, 401, 401, 401, 401, 429]`.
- No session was created during failed attempts.

### 7. API login malformed JSON could fail unsafely

Impact level: Medium

Description:

`/api/v1/auth/login` expected a JSON object and could error if a malformed JSON payload was sent.

Steps to reproduce:

1. POST malformed JSON to `/api/v1/auth/login`.
2. Before the fix, the route could attempt `.get()` on invalid/missing JSON.

Impact:

Malformed input could cause a server error instead of a safe authentication failure.

Fix applied:

Changed API login parsing to `request.get_json(silent=True) or {}`.

Retest result:

- Malformed JSON login attempt returned `401`.
- No stack trace or internal error was exposed.

### 8. Sign-up server-side validation needed hardening

Impact level: Medium

Description:

The sign-up form had client-side password length validation, but server-side validation needed to enforce password length and malformed email rejection consistently.

Steps to reproduce:

1. Submit `/signup` directly with a short password, bypassing browser validation.
2. Submit OTP request with malformed email such as `javascript:alert(1)`.

Impact:

Attackers can bypass browser-only validation by sending direct HTTP requests.

Fix applied:

Added server-side email format validation and minimum password length checks for sign-up. Added email sanitization/validation to OTP-related auth endpoints.

Retest result:

- Direct short-password sign-up was rejected.
- Malformed OTP email request returned `400`.
- Duplicate sign-up was rejected safely.

## Functional Validation

Public routes passed:

- `/`
- `/about`
- `/services`
- `/contact`
- `/login`
- `/signup`
- `/forgot-password`
- `/vetscan`
- `/offline`
- `/service-worker.js`
- `/favicon.ico`
- `/static/manifest.json`

Protected unauthenticated routes redirected correctly:

- `/booking`
- `/dashboard`
- `/dashboard/client`
- `/staff/dashboard`
- `/staff/appointments`
- `/staff/pet-records`
- `/staff/control-panel`
- `/staff/offers`
- `/staff/audit-logs`
- `/admin/dashboard`

Booking workflow passed:

- Client created an appointment through `/api/v1/appointments`.
- Duplicate booking for the same date/slot was rejected with `409`.
- Staff updated appointment status.
- Staff deleted the appointment.
- Database retest confirmed the booking was removed.

VetScan passed:

- `/vetscan` rendered successfully.
- `/predict` returned `200` with successful prediction output.

PWA shell passed:

- Service worker route: `200`
- Manifest route: `200`
- Favicon route: `200`
- Service worker syntax: passed

## Role-Based Access Validation

Client:

- Login passed.
- `/dashboard` routes to the client dashboard.
- Booking page loads.
- Staff dashboard is blocked.
- Admin dashboard is blocked.
- Client token is blocked from admin users API with `403`.

Staff:

- Login passed.
- `/dashboard` routes to the staff dashboard.
- Staff Dashboard loads.
- Staff Appointments loads.
- Staff Pet Records loads.
- Staff Control Panel loads.
- Staff Offers redirects safely.
- Admin Dashboard is blocked.
- Schedule and report APIs pass.

Admin:

- Login passed.
- `/dashboard` routes to the admin dashboard.
- Admin Dashboard loads.
- Staff Dashboard access is allowed.
- Staff Control Panel access is allowed.
- Audit Logs load.
- Users, appointments, and reports APIs pass.

## Navigation And UI Stress Validation

Validated:

- Public navigation routes render.
- Role dashboard routing is accurate.
- Protected routes redirect correctly.
- Rendered internal links/assets checked: 243.
- Broken rendered links/assets: 0.
- Hamburger menu has tap-outside close behavior.
- Hamburger menu has Escape-key close behavior.
- Blur overlay is wired to close and is not permanently blocking by code path.
- CSS includes keyboard `focus-visible` states.
- Tap target sizing uses common 44px minimum patterns.

Manual browser interaction still recommended:

- Verify actual hamburger animation in Chrome/Edge/Firefox/Safari.
- Confirm no UI freeze during rapid menu open/close.
- Confirm hover/tap visual states with physical touch devices.

## Responsive And Design Validation

Automated/static checks confirmed:

- Responsive media queries are present.
- 300px-class small mobile support is covered by the `320px` breakpoint.
- Horizontal page overflow is guarded.
- Major pages render without server-side template failure.
- Static assets resolve correctly.
- Shared typography and page shell CSS are loaded.

Responsive areas covered by static/template checks:

- Dashboards
- Booking flow
- Staff calendar/dashboard
- Admin dashboard
- Services page
- Public layout shell

Manual visual checks still recommended:

- 300px small mobile
- 320px mobile
- 390px standard mobile
- 768px tablet
- 1366px laptop
- 1920px desktop/widescreen
- Installed PWA mode after clearing old service worker cache

## Information Assurance And Security Validation

### Data Classification

Critical Data:

- Password hashes
- OTP hashes
- Reset/password recovery credentials
- Authentication sessions/JWTs
- Medical notes and clinical diagnosis data

Confidential Data:

- Client names
- Client emails and phone numbers
- Client address
- Pet records
- Appointment history
- Visit reasons
- Medical history fields
- Staff/admin operational reports

Public Data:

- Home page content
- Services page content
- About page content
- General clinic contact information
- PWA manifest metadata

### Threat Modeling Checks

SQL Injection:

- Login injection attempt using `' OR '1'='1` was rejected with `401`.
- Additional login SQL payloads were rejected: `admin@example.com' --`, `SELECT * FROM users`, `DROP TABLE users;`, and `" OR "1"="1`.
- SQLAlchemy ORM parameterization is used for tested login and booking flows.

Man-in-the-Middle:

- Production HTTPS enforcement was added and tested.
- HSTS is emitted when enforcement is enabled.
- Secure cookies are enabled in production config.
- TLS 1.3 must still be verified at the deployment/load-balancer certificate layer.

Session Hijacking:

- Session is bound to IP and User-Agent.
- Reusing an authenticated session with a different User-Agent redirected to login.
- Session cookie is HTTP-only.

Unauthorized Access:

- Anonymous admin API access returned `401`.
- Client access to admin users API returned `403`.
- Staff access to admin dashboard is blocked.
- Client access to staff/admin dashboards is blocked.

Device Theft / Session Reuse:

- Session lifetime is limited.
- Session fingerprint mismatch clears the session.
- Logout clears the session.
- Recommendation: add server-side session revocation or token denylist if high-risk production devices are shared.

### Data At Rest

Verified:

- Passwords are stored as secure Werkzeug hashes, not plaintext.
- OTP codes are stored as hashes, not plaintext.
- OTP verification works once and replay is blocked.

Residual deployment requirement:

- Database/disk-level encryption was not verifiable from the Flask test client. Use encrypted managed database storage or encrypted server volumes for production medical/client data.

### Data In Transit

Verified in application configuration:

- Production HTTPS redirect is available through `ENFORCE_HTTPS`.
- HSTS is emitted when HTTPS enforcement is active.
- Production session cookies are marked secure.

Residual deployment requirement:

- TLS 1.3 and certificate configuration must be verified against the real production domain using browser/devops tooling.

## Login And Sign-Up Security Validation

Validated input fields:

- Login email
- Login password
- API login JSON body
- Sign-up first name
- Sign-up last name
- Sign-up email
- Sign-up contact
- Sign-up password and confirmation
- OTP email request

Attack payload results:

- SQL-like login payloads were treated as plain text and rejected.
- Login bypass attempts did not create a session.
- Malformed JSON did not crash API login.
- XSS payload `<script>alert(1)</script>` in sign-up name was sanitized before storage.
- `javascript:` email input was rejected by OTP request validation.
- Duplicate account creation was rejected without stack traces.
- Passwords were not echoed in responses.
- Failed login errors were generic and did not reveal whether the email exists.
- Brute-force login attempts were throttled with `429`.
- Repeated sign-up OTP requests were throttled with `429`.

Authentication security status:

- No SQL injection bypass was possible in tested login paths.
- No unauthorized login was achieved.
- No raw database errors or stack traces were exposed.
- No password values were reflected in responses.
- Sign-up requires OTP verification before account creation.
- Passwords and OTPs are stored as hashes.

## Final Status

The full system test run passed after fixes.

Current verified status:

- Functional routes: passed
- Booking workflow: passed
- VetScan prediction: passed
- Client/staff/admin navigation: passed
- Role-based access control: passed
- Staff schedule/report workflows: passed
- Admin APIs: passed
- PWA shell assets: passed
- Rendered internal links/assets: passed
- Static UI/responsive safeguards: passed
- SQL injection login rejection: passed
- Login/signup injection and malformed input rejection: passed
- Login brute-force throttling: passed
- Sign-up OTP throttling: passed
- XSS sign-up payload sanitization: passed
- Session hijack mismatch protection: passed
- Password and OTP hashing: passed
- HTTPS/HSTS enforcement mode: passed
- Required security headers: passed

Production readiness conclusion:

The application-level QA and security checks pass. Remaining production-only validations are real browser/device screenshots and real TLS 1.3 certificate verification on the deployed HTTPS domain.
