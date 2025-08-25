from flask import Flask, request, jsonify
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv("app.env")

app = Flask(__name__)

# Load config from environment
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Validate required environment variables
if not all([JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN]):
    raise EnvironmentError("JIRA_DOMAIN, JIRA_EMAIL, or JIRA_API_TOKEN not set in environment.")

# Optional: Mapping UI project names → Jira keys
PROJECT_KEY_MAPPING = {
    "Project Alpha": "ALPHA"
}

@app.route('/get_defectdetails', methods=['POST'])
def get_defectdetails():
    data = request.get_json()

    projectname = data.get("projectname")
    defectid = data.get("defectid")

    if not projectname or not defectid:
        return jsonify({"error": "Both 'projectname' and 'defectid' are required."}), 400

    if not defectid.startswith(f"{projectname}-"):
        return jsonify({
            "error": f"Defect ID '{defectid}' does not match project '{projectname}'."
        }), 400

    # Construct Jira API URL
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{defectid}"
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch defect info from Jira",
            "status_code": response.status_code,
            "details": response.json()
        }), response.status_code

    issue = response.json()
    fields = issue.get("fields", {})

    result = {
        "defectid": defectid,
        "projectname": fields.get("project", {}).get("key"),
        "summary": fields.get("summary"),
        "reported_by": fields.get("reporter", {}).get("displayName"),
        "assigned_to": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
        "issue_type": fields.get("issuetype", {}).get("name"),
        "priority": fields["priority"]["name"] if fields.get("priority") else None,
        "status": fields.get("status", {}).get("name"),
        "description": extract_description(fields.get("description")) if fields.get("description") else "No description available"
    }


    return jsonify(result)

def extract_description(desc):
    if not isinstance(desc, dict):
        return "No description available"
    try:
        content = desc.get("content", [])
        description_text = ""
        for block in content:
            for inner in block.get("content", []):
                description_text += inner.get("text", "") + " "
        return description_text.strip() or "No description available"
    except Exception:
        return "No description available"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
