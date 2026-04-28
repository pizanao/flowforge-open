import requests
import json

url = "http://127.0.0.1:8006/api/workflows/e026052a-66dd-4649-adf0-3133dc8858eb/webhook/"

payload = json.dumps({
  "message": "Olá!",
  "from": "5511999999999"
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic cGl6YW5pOiMxMjM='
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
