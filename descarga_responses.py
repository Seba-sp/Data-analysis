import os
import json
import pandas as pd
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()

course_id = "test-de-diagnostico-m30m"
client_id = os.getenv("CLIENT_ID")
school_domain = os.getenv("SCHOOL_DOMAIN")
access_token = os.getenv("ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {access_token}",
    "Lw-Client": client_id,
    "Accept": "application/json"
}

# Create 'datos' and 'responses' folders if they don't exist
os.makedirs("datos", exist_ok=True)
os.makedirs("responses", exist_ok=True)

# Load assessments
with open("datos/assessments.json", "r", encoding="utf-8") as f:
    assessments = json.load(f)

def get_assessment_responses(assessment_id):
    rows = []
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/assessments/{assessment_id}/responses?page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch responses for assessment {assessment_id}: {response.status_code}")
            break
        data = response.json().get('data', [])
        rows.extend(data)
        total_pages = response.json().get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(1)  # Sleep to avoid overloading the API
    return rows

# Download all responses for each assessment
dict_responses = {}
for name, aid in assessments.items():
    print(f"Downloading responses for: {name}")
    responses = get_assessment_responses(aid)
    dict_responses[name] = responses
    with open(f"responses/responses_{name.replace('/', '_')}.json", "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    time.sleep(1)  # Sleep between assessments

with open("responses/all_responses.json", "w", encoding="utf-8") as f:
    json.dump(dict_responses, f, ensure_ascii=False, indent=2)

# Procesar y guardar como CSV
sep = ";"
for name, responses in dict_responses.items():
    df = pd.DataFrame(responses)
    df.to_csv(f"responses/responses_{name.replace('/', '_')}.csv", sep=sep, index=False)

print("Descarga y guardado de responses completados en la carpeta 'responses'.") 