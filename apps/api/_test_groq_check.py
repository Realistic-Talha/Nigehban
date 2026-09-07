import json
import time
import urllib.request
from urllib.error import HTTPError

BASE = "http://127.0.0.1:8001"


def health(port: int) -> dict | str:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
            return json.load(r)
    except Exception as e:
        return f"DOWN: {e}"


print("8000", health(8000))
print("8001", health(8001))

# form-urlencoded may work depending on API — use multipart via email package-less approach
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
payload = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="text"\r\n\r\n'
    "SBP approved your loan. Send OTP to release funds.\r\n"
    f"--{boundary}--\r\n"
).encode()

req = urllib.request.Request(
    f"{BASE}/api/v1/scamcheck/submit",
    data=payload,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
        print("submit", data)
        check_id = data.get("check_id") or data.get("id")
except HTTPError as e:
    print("submit HTTP", e.code, e.read()[:500])
    check_id = None

if check_id:
    for i in range(30):
        time.sleep(2)
        with urllib.request.urlopen(f"{BASE}/api/v1/checks/{check_id}", timeout=30) as r:
            detail = json.load(r)
        status = detail.get("status")
        expl = (detail.get("explanation_en") or "")[:120]
        print(f"poll {i} status={status} expl={expl!r}")
        if status == "complete":
            break
