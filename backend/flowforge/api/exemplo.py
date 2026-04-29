import hmac
import hashlib
import json
import os
import time

import requests

url = "http://127.0.0.1:8006/api/workflows/e026052a-66dd-4649-adf0-3133dc8858eb/webhook/"

payload = json.dumps({
  "message": "Olá!",
  "from": "5511999999999"
})
timestamp = str(int(time.time()))
secret = os.environ["WEBHOOK_SIGNING_SECRET"]
signature = hmac.new(
    secret.encode(),
    f"{timestamp}.{payload}".encode(),
    hashlib.sha256,
).hexdigest()
headers = {
  'Content-Type': 'application/json',
  'X-FlowForge-Timestamp': timestamp,
  'X-FlowForge-Signature': f"sha256={signature}",
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
