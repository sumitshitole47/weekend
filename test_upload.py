import urllib.request
import json
import os

def test_upload():
    boundary = "----AeroTwinBoundary987654321"
    body = bytearray()

    video_path = "data/raw_video/uploaded_video.mp4"
    srt_path = "data/raw_video/uploaded_video.srt"

    with open(video_path, "rb") as f:
        v_bytes = f.read()
    with open(srt_path, "rb") as f:
        s_bytes = f.read()

    # Video Part
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="video"; filename="random_drone_footage.mp4"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: video/mp4\r\n\r\n")
    body.extend(v_bytes)
    body.extend(b"\r\n")

    # SRT Part
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="srt"; filename="flight_telemetry.srt"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: text/plain\r\n\r\n")
    body.extend(s_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request("http://127.0.0.1:8000/api/upload", data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        print("[+] SUCCESS: /api/upload response:", data)
    except Exception as e:
        print("[-] ERROR:", e)

if __name__ == "__main__":
    test_upload()
