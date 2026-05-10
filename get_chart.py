import urllib.request
import os

url = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"
save_path = os.path.join("app", "static", "js", "chart.min.js")

print(f"Downloading Chart.js from {url}...")
try:
    urllib.request.urlretrieve(url, save_path)
    print(f"✅ Successfully downloaded and saved to {save_path}")
except Exception as e:
    print(f"❌ Failed to download: {e}")
