import urllib.request
import os

url = "https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"
save_path = os.path.join("app", "static", "js", "chartjs-adapter-date-fns.bundle.min.js")

print(f"Downloading Date Adapter from {url}...")
try:
    urllib.request.urlretrieve(url, save_path)
    print(f"✅ Successfully downloaded and saved to {save_path}")
except Exception as e:
    print(f"❌ Failed to download: {e}")
