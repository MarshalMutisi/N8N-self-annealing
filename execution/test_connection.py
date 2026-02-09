import os
import requests
from dotenv import load_dotenv

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")

print(f"Testing connection to {N8N_URL}...")

try:
    headers = {"X-N8N-API-KEY": N8N_KEY}
    url = f"{N8N_URL}/api/v1/executions?limit=5&includeData=false"
    response = requests.get(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data.get('data', []))} executions.")
        for exec in data.get('data', []):
            print(f"- Execution {exec.get('id')} (Finished: {exec.get('finished')})")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Connection Failed: {e}")
