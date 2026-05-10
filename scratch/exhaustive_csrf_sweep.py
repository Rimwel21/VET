import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# Every mutation endpoint from our registry dump
MUTATION_ENDPOINTS = [
    ("/auth/signup", "POST"),
    ("/auth/login", "POST"),
    ("/book", "POST"),
    ("/booking/cancel/1", "POST"),
    ("/staff/reports/edit/1", "POST"),
    ("/staff/booking/1/status", "POST"),
    ("/staff/booking/1/delete", "POST"),
    ("/staff/availability", "POST"),
    ("/predict", "POST"),
    ("/api/v1/auth/login", "POST"),
    ("/api/v1/auth/send-otp", "POST"),
    ("/api/v1/auth/verify-otp", "POST"),
    ("/api/v1/auth/forgot-password", "POST"),
    ("/api/v1/auth/verify-reset-otp", "POST"),
    ("/api/v1/auth/reset-password", "POST"),
    ("/api/v1/appointments", "POST"),
    ("/api/v1/appointments/1", "PUT"),
    ("/api/v1/appointments/1", "DELETE"),
    ("/api/v1/users", "POST"),
    ("/api/v1/users/1", "PUT"),
    ("/api/v1/users/1", "DELETE"),
    ("/api/v1/notifications", "POST"),
    ("/api/v1/schedule/block", "POST"),
    ("/api/v1/schedule/unblock", "DELETE"),
    ("/api/v1/push/subscribe", "POST"),
    ("/api/v1/reports", "POST"),
    ("/api/v1/reports/1", "PUT"),
    ("/api/v1/reports/1", "DELETE"),
    ("/api/v1/reports/1/review", "PUT"),
    ("/api/v1/chatbot/astrid", "POST"),
    ("/api/v1/chatbot/health", "POST")
]

def test_exhaustive_csrf():
    print(f"--- [DEEP-QA] Exhaustive CSRF Sweep ({len(MUTATION_ENDPOINTS)} endpoints) ---")
    session = requests.Session()
    
    passed = 0
    failed = 0
    
    for rule, method in MUTATION_ENDPOINTS:
        url = f"{BASE_URL}{rule}"
        print(f"Testing {method.ljust(6)} {rule} ...", end=" ")
        
        try:
            # We send NO CSRF token
            if method == "POST":
                resp = session.post(url, data={"test": "data"})
            elif method == "PUT":
                resp = session.put(url, json={"test": "data"})
            elif method == "DELETE":
                resp = session.delete(url)
                
            if resp.status_code == 403:
                print("PASSED (403 Blocked)")
                passed += 1
            elif resp.status_code == 404:
                # Some IDs (like /reports/1) might not exist, but middleware should run first
                # Actually, in Flask, before_request runs even for 404s if the route matches.
                # If it's 404, it might mean the ID wasn't found but the route matched.
                # But CSRF check happens in before_request.
                print("INFO (404 - Not Found but bypassed 403?)")
                failed += 1
            else:
                print(f"FAILED (Status: {resp.status_code})")
                failed += 1
        except Exception as e:
            print(f"ERROR ({str(e)})")
            failed += 1

    print(f"\nSweep Complete: {passed} PASSED, {failed} FAILED.")

if __name__ == "__main__":
    test_exhaustive_csrf()
