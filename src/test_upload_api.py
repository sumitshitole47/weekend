import urllib.request
import urllib.parse
import json
import time

def test_upload_urllib():
    print("[TEST] Polling /api/status...")
    req = urllib.request.Request("http://localhost:8000/api/status")
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode('utf-8')
            print(f"[STATUS RESPONSE]: {body}")
    except Exception as e:
        print(f"[ERROR]: {e}")

if __name__ == "__main__":
    test_upload_urllib()
