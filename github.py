from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv("github.env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}


def get_commit_message(repo, file_path):
    commits_url = f"https://api.github.com/repos/{repo}/commits"
    params = {"path": file_path, "per_page": 1}
    res = requests.get(commits_url, headers=HEADERS, params=params)

    if res.status_code == 200 and res.json():
        full_msg = res.json()[0]["commit"]["message"]
        parts = full_msg.strip().split("\n\n", 1)  # Split title and body
        if len(parts) > 1:
            return parts[1].strip()  # Only the description
        else:
            return parts[0].strip()  # Fallback to full message if no body
    else:
        return "No commit message found"


@app.route("/get_related_docs", methods=["POST"])
def get_related_docs():
    data = request.get_json()
    file_name = data.get("file_name", "").strip()

    if not file_name:
        return jsonify({"error": "Missing 'file_name' in request"}), 400

    base_name = os.path.splitext(file_name)[0].lower()
    valid_exts = [".docx", ".pdf", ".txt", ".xlsx"]

    tree_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    response = requests.get(tree_url, headers=HEADERS)
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch repo tree", "details": response.json()}), 500

    files = response.json().get("tree", [])
    matched_files = []

    for file in files:
        if file["type"] != "blob":
            continue

        filepath = file["path"]
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()

        if filename.lower().startswith(base_name + "_") and ext in valid_exts:
            description = get_commit_message(GITHUB_REPO, filepath)

            matched_files.append({
                "file_name": filename,
                "description": description
            })

    if not matched_files:
        return jsonify({"message": "No related files found"}), 404

    return jsonify(matched_files)


if __name__ == "__main__":
    app.run(debug=True)
