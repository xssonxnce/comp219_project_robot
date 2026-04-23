import json
import urllib.request


API_KEY = "9hlH72vOCU2YyxgSkHS6QUiHiWbvOOPy"
MODEL_NAME = "mistral-small-latest"

SYSTEM_PROMPT = """
You are a navigation intent parser for a ROS2 robot.
Extract the destination from the user command.

Return ONLY valid JSON in this format:
{"destination": "<location_name_or_null>"}

Allowed destinations:
- kitchen
- office

If nothing matches, return:
{"destination": null}
"""


def parse_with_mistral(user_text: str):
    url = "https://api.mistral.ai/v1/chat/completions"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.0
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)
    return parsed.get("destination")