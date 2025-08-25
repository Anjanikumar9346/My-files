from flask import Flask, jsonify
import requests
import os
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv("board.env")

app = Flask(__name__)

# Jira credentials from .env
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")

headers = {"Content-Type": "application/json"}

def fetch_daily_resolution_trend():
    jql = f'project={PROJECT_KEY} AND resolutiondate >= "2025-01-01" ORDER BY resolutiondate ASC'
    url = f"{JIRA_URL}/rest/api/2/search"
    params = {
        "jql": jql,
        "fields": "created,resolutiondate",
        "maxResults": 1000
    }

    response = requests.get(url, headers=headers, params=params, auth=(JIRA_USER, JIRA_TOKEN))
    if response.status_code != 200:
        return {"error": f"Failed to fetch from JIRA: {response.text}"}, response.status_code

    issues = response.json().get("issues", [])

    # Group by resolution date
    daily_data = defaultdict(list)
    for issue in issues:
        created = datetime.strptime(issue["fields"]["created"][:10], "%Y-%m-%d")
        resolved = datetime.strptime(issue["fields"]["resolutiondate"][:10], "%Y-%m-%d")
        days_to_resolve = (resolved - created).days
        resolved_date_str = resolved.strftime("%Y-%m-%d")
        daily_data[resolved_date_str].append(days_to_resolve)

    # Build JSON output
    trend = []
    for date, times in sorted(daily_data.items()):
        avg_days = round(sum(times) / len(times), 2)
        trend.append({
            "date": date,
            "resolved_count": len(times),
            "avg_resolution_days": avg_days
        })

    return trend

@app.route("/resolution-trend", methods=["GET"])
def resolution_trend():
    data = fetch_daily_resolution_trend()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
