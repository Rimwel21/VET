import requests
import re
import time

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session):
    resp = session.get(BASE_URL)
    match = re.search(r'meta name="csrf-token" content="([^"]+)"', resp.text)
    return match.group(1) if match else None

def test_sqli_login():
    print("--- [PEN-TEST] SQL Injection Audit (Login) ---")
    session = requests.Session()
    token = get_csrf_token(session)
    
    payloads = [
        "' OR '1'='1",
        "admin@vetsync.com' --",
        "')) OR (('1'='1"
    ]
    
    for p in payloads:
        print(f"Testing payload: {p}", end=" ")
        # We'll use the API style login since it's easier to verify (JSON vs Redirect)
        resp = session.post(f"{BASE_URL}/login", 
                            json={"email": p, "password": "any"},
                            headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": token})
        
        try:
            result = resp.json()
            if resp.status_code == 200 and result.get('success'):
                print("FAILED (Bypassed! Token returned)")
            else:
                print(f"PASSED (Blocked: {result.get('error')})")
        except:
            # If not JSON, it might be a redirect (standard form)
            if resp.status_code == 302 and "/login" not in resp.headers.get('Location', ''):
                print(f"FAILED (Bypassed! Redirected to {resp.headers.get('Location')})")
            else:
                print("PASSED (Blocked/Error)")

def test_role_escalation():
    print("\n--- [PEN-TEST] Role Escalation Audit ---")
    session = requests.Session()
    
    # We'll use the admin account from seed data (adminvetclinic@gmail.com / vetadminclinic1214)
    # as verified in app/__init__.py
    admin_email = "adminvetclinic@gmail.com"
    admin_password = "vetadminclinic1214"
    
    resp = session.post(f"{BASE_URL}/api/v1/auth/login", 
                        json={"email": admin_email, "password": admin_password})
    
    if resp.status_code != 200:
        print(f"Could not log in as admin ({resp.status_code}). Trying alternative admin...")
        resp = session.post(f"{BASE_URL}/api/v1/auth/login", 
                            json={"email": "admin@vetsync.com", "password": "admin123"})
        if resp.status_code != 200:
            print("Admin login failed. Skipping escalation test.")
            return
            
    admin_creds = resp.json()
    admin_token = admin_creds['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Find a client
    users_resp = session.get(f"{BASE_URL}/api/v1/users", headers=admin_headers)
    users = users_resp.json()
    client = next((u for u in users if u['role'] == 'client'), None)
    
    if not client:
        print("No client found in DB. Skipping.")
        return
        
    client_id = client['id']
    client_email = client['email']
    print(f"Testing Client ID: {client_id} ({client_email})")
    
    # Login as client
    # Note: We don't know the password for Sarah Connor (seed says password123)
    login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                               json={"email": client_email, "password": "password123"})
    if login_resp.status_code != 200:
        print(f"Client login failed for {client_email}. Status: {login_resp.status_code}")
        return
        
    client_token = login_resp.json()['access_token']
    client_headers = {"Authorization": f"Bearer {client_token}"}
    
    # Try to escalate
    print("Attempting self-role-escalation to admin...")
    attack_resp = requests.put(f"{BASE_URL}/api/v1/users/{client_id}", 
                               headers=client_headers,
                               json={"role": "admin"})
    
    if attack_resp.status_code == 403:
        print("SUCCESS: Escalation rejected (403 Forbidden)")
    elif attack_resp.status_code == 200:
        # Check if role actually changed
        check = requests.get(f"{BASE_URL}/api/v1/users/{client_id}", headers=admin_headers)
        if check.json().get('role') == 'admin':
            print("CRITICAL FAILURE: Role escalated to admin!")
        else:
            print("SUCCESS: Role field ignored by server.")
    else:
        print(f"INFO: Unexpected response {attack_resp.status_code}")

def test_idor_cancellation():
    print("\n--- [PEN-TEST] IDOR Audit (Cancellation) ---")
    session_admin = requests.Session()
    # Login as admin
    resp = session_admin.post(f"{BASE_URL}/api/v1/auth/login", 
                              json={"email": "adminvetclinic@gmail.com", "password": "vetadminclinic1214"})
    if resp.status_code != 200:
        resp = session_admin.post(f"{BASE_URL}/api/v1/auth/login", 
                                  json={"email": "admin@vetsync.com", "password": "admin123"})
                                  
    admin_token = resp.json()['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get all bookings
    bookings_resp = session_admin.get(f"{BASE_URL}/api/v1/appointments/all", headers=admin_headers)
    bookings = bookings_resp.json()
    
    # Find two bookings belonging to different users
    if len(bookings) < 2:
        print("Not enough bookings for IDOR test.")
        return
        
    victim_booking = bookings[0]
    attacker_booking = bookings[1]
    
    victim_id = victim_booking['id']
    attacker_email = attacker_booking.get('email') or "sarah.connor@example.com"
    
    print(f"Victim Booking ID: {victim_id}")
    print(f"Attacker: {attacker_email}")
    
    # Login as attacker (web session)
    session_attacker = requests.Session()
    session_attacker.post(f"{BASE_URL}/login", 
                          data={"email": attacker_email, "password": "password123"})
    
    csrf_token = get_csrf_token(session_attacker)
    
    # Attempt to cancel victim's booking
    print(f"Client {attacker_email} attempting to cancel Booking {victim_id}...")
    attack_resp = session_attacker.post(f"{BASE_URL}/booking/cancel/{victim_id}", 
                                        data={"csrf_token": csrf_token},
                                        allow_redirects=False)
    
    if attack_resp.status_code == 302:
        # Check flash message on redirect destination
        target = attack_resp.headers.get('Location')
        if "/login" in target:
             print("SUCCESS: IDOR blocked (Session required)")
        else:
            follow = session_attacker.get(f"{BASE_URL}{target}")
            if "Unauthorized" in follow.text or "error" in follow.text:
                print("SUCCESS: IDOR blocked (Unauthorized flash message)")
            else:
                print("FAILURE: Redirected but no error message found.")
    else:
        print(f"INFO: Server returned {attack_resp.status_code}")

if __name__ == "__main__":
    test_sqli_login()
    test_role_escalation()
    test_idor_cancellation()
