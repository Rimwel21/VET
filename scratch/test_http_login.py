import requests
import re

session = requests.Session()

# 1. Fetch login page to get CSRF token and session cookies
print("Fetching login page...")
r_get = session.get("http://127.0.0.1:5000/login")
print("GET Status:", r_get.status_code)

# Try to find CSRF token from the response text
csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', r_get.text)
if not csrf_match:
    csrf_match = re.search(r'content="([^"]+)"\s+name="csrf-token"', r_get.text)
if not csrf_match:
    csrf_match = re.search(r'name="csrf-token"\s+content="([^"]+)"', r_get.text)

if csrf_match:
    csrf_token = csrf_match.group(1)
    print("Found CSRF Token:", csrf_token)
else:
    csrf_token = None
    print("WARNING: Could not find CSRF token in HTML!")

# 2. Try POST request with JSON
payload = {
    "email": "adminvetclinic@gmail.com",
    "password": "vetadminclinic1214"
}
headers = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
}
if csrf_token:
    headers["X-CSRF-Token"] = csrf_token

print("Sending POST request to login...")
r_post = session.post("http://127.0.0.1:5000/login", json=payload, headers=headers)
print("POST Status:", r_post.status_code)
print("POST Response Body:", r_post.text)
