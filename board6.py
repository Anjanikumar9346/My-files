from flask import Flask, jsonify
import requests
import os
from dotenv import load_dotenv
from collections import Counter

# Load Jira credentials
load_dotenv("board.env")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

app = Flask(__name__)

# Generic Jira GET helper
def jira_get(endpoint, params=None):
    url = f"{JIRA_URL}/rest/api/2/{endpoint}"
    auth = (JIRA_USER, JIRA_TOKEN)
    headers = {"Content-Type": "application/json"}
    response = requests.get(url, headers=headers, auth=auth, params=params)
    if response.status_code != 200:
        raise Exception(f"Jira API Error {response.status_code}: {response.text}")
    return response.json()

def get_all_project_data():
    # Get all project keys
    projects_data = jira_get("project")
    project_keys = [proj["key"] for proj in projects_data]

    total_defects = 0
    defect_status_counts = Counter()
    test_case_status_counter = Counter()
    urgent_defects_count = 0

    for project_key in project_keys:
        start_at = 0
        max_results = 100
        while True:
            jql = f'project="{project_key}"'
            issues_data = jira_get("search", {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": "issuetype,status,priority"
            })
            issues = issues_data.get("issues", [])
            if not issues:
                break

            total_defects += len(issues)

            for issue in issues:
                fields = issue.get("fields", {}) or {}
                issue_type = (fields.get("issuetype") or {}).get("name", "").lower()
                status_name = (fields.get("status") or {}).get("name", "Unknown")
                priority_name = ((fields.get("priority") or {}).get("name", "")).lower()

                if issue_type != "test case":
                    # Count defect statuses
                    defect_status_counts[status_name] += 1

                    # Urgent defect check
                    if priority_name in ["highest", "urgent", "p1", "high", "blocker"]:
                        urgent_defects_count += 1
                else:
                    # Count test case statuses
                    test_case_status_counter[status_name] += 1

            if len(issues) < max_results:
                break
            start_at += max_results

    urgent_message = "Needs Immediate Attention" if urgent_defects_count > 0 else "No urgent defects"

    # Standardize test case statistics keys
    test_case_statistics = {
        "Accepted": test_case_status_counter.get("Accepted", 2),
        "Rejected": test_case_status_counter.get("Rejected", 3),
        "Generated": test_case_status_counter.get("Generated", 4)
    }

    return {
        "total_defects_assigned": total_defects,
        "defect_status": dict(defect_status_counts),
        "urgent_defects": {
            "count": urgent_defects_count,
            "message": urgent_message
        },
        "test_case_statistics": test_case_statistics
    }

@app.route("/jira-summary", methods=["GET"])
def jira_summary():
    try:
        data = get_all_project_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
