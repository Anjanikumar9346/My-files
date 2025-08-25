from flask import Flask, jsonify
import requests
import os
from dotenv import load_dotenv
from collections import Counter

load_dotenv("board.env")
app = Flask(__name__)

# Jira credentials from .env
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")

def fetch_all_issues(jql):
    """Fetch all issues for a JQL query (with pagination)."""
    url = f"{JIRA_URL}/rest/api/2/search"
    headers = {"Content-Type": "application/json"}
    auth = (JIRA_USER, JIRA_TOKEN)

    start_at = 0
    max_results = 100
    all_issues = []

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "issuetype,status,priority"
        }
        response = requests.get(url, headers=headers, params=params, auth=auth)
        if response.status_code != 200:
            print("Error:", response.text)
            break

        data = response.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)

        if start_at + max_results >= data.get("total", 0):
            break
        start_at += max_results

    return all_issues

@app.route("/jira-dashboard-task", methods=["GET"])
def jira_dashboard_task():
    # Fetch only "Task" issues from the project
    issues = fetch_all_issues(f'project={PROJECT_KEY} AND issuetype="Task"')

    total_tasks = len(issues)
    status_counter = Counter()
    urgent_count = 0

    for issue in issues:
        status_name = issue["fields"]["status"]["name"]
        priority_name = issue["fields"]["priority"]["name"] if issue["fields"]["priority"] else ""
        
        status_counter[status_name] += 1

        if priority_name.lower() in ["highest", "urgent", "p1"]:
            urgent_count += 1

    # Dynamic urgent message
    urgent_message = "Needs Immediate Attention" if urgent_count > 0 else "No urgent defects — all good!"

    return jsonify({
        "total_tasks": total_tasks,
        "status_counts": dict(status_counter),
        "urgent_defects": {
            "count": urgent_count,
            "message": urgent_message
        }
    })

if __name__ == "__main__":
    app.run(debug=True)
