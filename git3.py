import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load .env values
load_dotenv("git3.env")

# Load environment variables globally
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")
BRANCH = os.getenv("BRANCH", "main")

# Global headers for GitHub API
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

app = Flask(__name__)

# --- Get Latest Commit Message for File ---
def get_latest_commit_message(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
    params = {"path": file_path, "sha": BRANCH}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        commits = response.json()
        if commits:
            full_message = commits[0]["commit"]["message"].strip()
            # Remove generic phrases
            full_message = full_message.replace("Add files via upload", "").strip()
            full_message = full_message.replace("Initial commit", "").strip()

            # Return the last non-empty line if exists
            lines = [line.strip() for line in full_message.splitlines() if line.strip()]
            if lines:
                return lines[-1]  # Most specific part of message
    return ""

# --- Main Route ---
@app.route("/get_relevant_files", methods=["POST"])
def get_relevant_files():
    data = request.get_json()
    base_names = [os.path.splitext(name)[0] for name in data.get("file_names", [])]

    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/git/trees/{BRANCH}?recursive=1"

    try:
        res = requests.get(GITHUB_API_URL, headers=HEADERS)
        res.raise_for_status()
        files = res.json().get("tree", [])

        relevant_files = []
        for item in files:
            if item["type"] == "blob":
                filename = os.path.basename(item["path"])
                for base in base_names:
                    if filename.startswith(base + "_"):
                        commit_msg = get_latest_commit_message(item["path"])
                        relevant_files.append({
                            "file_name": filename,
                            "description": commit_msg
                        })
                        break

        return jsonify(relevant_files)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to fetch files from GitHub"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
