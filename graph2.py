from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv("board.env")

app = Flask(__name__)

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")

def fetch_all_issues(jql):
    issues = []
    start_at = 0
    max_results = 100
    url = f"{JIRA_URL}/rest/api/2/search"
    auth = (JIRA_USER, JIRA_TOKEN)
    headers = {"Accept": "application/json"}

    while True:
        params = {
            "jql": jql,
            "fields": "created,resolutiondate",
            "startAt": start_at,
            "maxResults": max_results
        }
        response = requests.get(url, headers=headers, params=params, auth=auth)
        if response.status_code != 200:
            raise Exception(f"Jira API error: {response.status_code} - {response.text}")
        
        data = response.json()
        issues.extend(data.get("issues", []))
        if start_at + max_results >= data.get("total", 0):
            break
        start_at += max_results
    return issues

@app.route("/resolution-trend")
def resolution_time_trend():
    jql = f'project = {PROJECT_KEY} AND resolved >= -30d ORDER BY resolved ASC'

    try:
        issues = fetch_all_issues(jql)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    trend_data = {}

    for issue in issues:
        created_str = issue["fields"].get("created")
        resolved_str = issue["fields"].get("resolutiondate")

        if not created_str or not resolved_str:
            continue

        created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        resolved_date = datetime.fromisoformat(resolved_str.replace("Z", "+00:00"))

        resolution_days = (resolved_date - created_date).days
        resolved_day = resolved_date.date()

        trend_data.setdefault(resolved_day, []).append(resolution_days)

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)

    avg_trend = []
    for n in range(30):
        day = start_date + timedelta(days=n)
        resolutions = trend_data.get(day, [])
        avg_days = round(sum(resolutions) / len(resolutions), 2) if resolutions else 0
        resolved_count = len(resolutions)
        avg_trend.append({
            "date": day.isoformat(),
            "avg_resolution_days": avg_days,
            "resolved_count": resolved_count
        })

    return jsonify(avg_trend)


if __name__ == "__main__":
    app.run(debug=True)
