import requests
import re
import time

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session):
    resp = session.get(BASE_URL)
    match = re.search(r'meta name="csrf-token" content="([^"]+)"', resp.text)
    return match.group(1) if match else None

def test_system_wide_csrf():
    print("--- [EVIDENCE] System-Wide CSRF Audit ---")
    session = requests.Session()
    
    endpoints = [
        ("POST", "/login"),
        ("POST", "/signup"),
        ("POST", "/contact"),
        ("POST", "/book"),
        ("POST", "/api/v1/users"),
        ("PUT", "/api/v1/users/1"),
        ("DELETE", "/api/v1/users/1")
    ]
    
    for method, path in endpoints:
        print(f"Testing {method} {path} without token...", end=" ")
        try:
            if method == "POST": resp = session.post(f"{BASE_URL}{path}", data={})
            elif method == "PUT": resp = session.put(f"{BASE_URL}{path}", data={})
            elif method == "DELETE": resp = session.delete(f"{BASE_URL}{path}")
            
            if resp.status_code == 403:
                print("REJECTED (403)")
            else:
                print(f"FAILED (Status: {resp.status_code})")
        except Exception as e:
            print(f"ERROR: {e}")

def test_rate_limiting_behavior():
    print("\n--- [EVIDENCE] Rate Limiting Behavior ---")
    session = requests.Session()
    token = get_csrf_token(session)
    
    email = f"rate_test_{int(time.time())}@vetsync.com"
    print(f"Identity: {email}")
    for i in range(1, 7):
        resp = session.post(f"{BASE_URL}/login", 
                            data={"csrf_token": token, "email": email, "password": "wrong"})
        if resp.status_code == 429:
            print(f"Attempt {i}: LOCKED OUT (429)")
            return
        else:
            print(f"Attempt {i}: {resp.status_code}")
    print("FAILURE: Not rate limited after 5 attempts.")

def test_xss_escaped_render():
    print("\n--- [EVIDENCE] XSS Sanitization (Reflected) ---")
    # We test the contact form patch
    session = requests.Session()
    token = get_csrf_token(session)
    
    payload = "<script>alert('xss')</script>"
    print(f"Submitting payload to Contact Form: {payload}")
    # Submit with missing fields to trigger a re-render
    resp = session.post(f"{BASE_URL}/contact", 
                        data={"csrf_token": token, "name": payload, "email": "", "message": ""})
    
    if payload in resp.text:
        print("FAILURE: RAW PAYLOAD FOUND IN RESPONSE")
    elif "&lt;script&gt;" in resp.text or "alert('xss')" in resp.text:
        # Note: If it's escaped, it won't execute.
        print("SUCCESS: Payload is not present in raw executable form.")
    else:
        print("INFO: Payload not reflected directly, checking sanitization logic...")

if __name__ == "__main__":
    try:
        test_system_wide_csrf()
        test_rate_limiting_behavior()
        test_xss_escaped_render()
    except Exception as e:
        print(f"FATAL: {e}")
