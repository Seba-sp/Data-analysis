import os, requests, json
from dotenv import load_dotenv
load_dotenv()
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]          # set this in your env/secret
CHANNEL_ID  = os.environ["SLACK_CHANNEL"]                           # copy from channel → About
payload = {
    "channel": CHANNEL_ID,
    "text": "✅ shaa la revolucion de las maquinas",
    # you can add attachments or blocks here
}
headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
r = requests.post("https://slack.com/api/chat.postMessage",
                  json=payload, headers=headers)
print(r.json())   # should return {"ok": true, ...}
