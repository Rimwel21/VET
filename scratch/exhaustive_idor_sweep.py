import requests

BASE_URL = "http://127.0.0.1:5000"

# Endpoints that take an ID and should be protected by ownership or role
IDOR_TARGETS = [
    ("/api/v1/users/1", "GET"),
    ("/api/v1/users/1", "PUT"),
    ("/api/v1/users/1", "DELETE"),
    ("/api/v1/appointments/1", "PUT"),
    ("/api/v1/appointments/1", "DELETE"),
    ("/api/v1/reports/1", "PUT"),
    ("/api/v1/reports/1", "DELETE"),
    ("/api/v1/reports/1/review", "PUT"),
]

def test_exhaustive_idor():
    print("--- [DEEP-QA] Exhaustive IDOR Sweep ---")
    session = requests.Session()
    
    # 1. Login as a normal Client (demo@vetsync.com)
    # We use web login to get a session
    resp = session.post(f"{BASE_URL}/login", 
                        data={"email": "demo@vetsync.com", "password": "demo123"})
    
    # Get CSRF token for the session
    import re
    resp_home = session.get(BASE_URL)
    match = re.search(r'meta name="csrf-token" content="([^"]+)"', resp_home.text)
    csrf_token = match.group(1) if match else ""

    passed = 0
    failed = 0
    
    for rule, method in IDOR_TARGETS:
        url = f"{BASE_URL}{rule}"
        print(f"Testing {method.ljust(6)} {rule} ...", end=" ")
        
        # Note: These are API routes but they also accept session auth 
        # via the role_required / jwt_required decorators (which check session if token is missing)
        headers = {"X-CSRF-Token": csrf_token}
        
        try:
            if method == "GET":
                resp = session.get(url, headers=headers)
            elif method == "PUT":
                resp = session.put(url, json={"test": "data"}, headers=headers)
            elif method == "DELETE":
                resp = session.delete(url, headers=headers)
            
            # Successful IDOR block should be 403 (Forbidden) or 401 (Unauthorized)
            if resp.status_code in [403, 401, 302]:
                print(f"PASSED ({resp.status_code} Blocked)")
                passed += 1
            else:
                # If it's 200, we check the content to see if it's actual data or an error
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if "error" in data or "message" in data:
                             print(f"PASSED (200 with error: {data.get('message') or data.get('error')})")
                             passed += 1
                        else:
                             print("FAILED (200 - Data Leaked!)")
                             failed += 1
                    except:
                        print("FAILED (200 - Non-JSON response leaked?)")
                        failed += 1
                else:
                    print(f"FAILED (Status: {resp.status_code})")
                    failed += 1
        except Exception as e:
            print(f"ERROR ({str(e)})")
            failed += 1

    print(f"\nSweep Complete: {passed} PASSED, {failed} FAILED.")

if __name__ == "__main__":
    test_exhaustive_idor()
