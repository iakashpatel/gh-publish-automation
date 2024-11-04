import os
import json
import base64
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

app = Flask(__name__)


def create_branch(branch_name):
    """
    Creates a new branch on GitHub based on the latest commit in the main branch.
    If the branch already exists, returns True without creating a new branch.
    """
    # Check if branch already exists
    branch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{branch_name}"
    branch_response = requests.get(branch_url, headers=HEADERS)

    if branch_response.status_code == 200:
        # Branch already exists, return True
        return True

    # Branch doesn't exist, so proceed to create it
    # Step 1: Get the latest commit SHA of the main branch
    main_branch_url = (
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/main"
    )
    main_branch_info = requests.get(main_branch_url, headers=HEADERS).json()
    latest_commit_sha = main_branch_info["object"]["sha"]

    # Step 2: Create a new branch based on this SHA
    create_branch_url = (
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs"
    )
    branch_data = {"ref": f"refs/heads/{branch_name}", "sha": latest_commit_sha}
    create_response = requests.post(
        create_branch_url, headers=HEADERS, json=branch_data
    )

    # Return True if the branch creation is successful
    return create_response.status_code == 201


def update_file(branch_name, file_path, file_content, commit_message):
    """
    Updates or creates a JSON file on a specified branch in GitHub.
    """
    file_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={branch_name}"
    file_info = requests.get(file_url, headers=HEADERS).json()
    file_sha = (
        file_info["sha"] if "sha" in file_info else None
    )  # For new files, SHA is not required

    # Encode the JSON content
    encoded_content = base64.b64encode(json.dumps(file_content).encode()).decode()

    # Create the request data for updating the file
    data = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch_name,
    }
    if file_sha:
        data["sha"] = file_sha  # Include SHA if updating an existing file

    response = requests.put(file_url, headers=HEADERS, json=data)
    return response.ok


def create_or_update_pull_request(branch_name, user_id, pr_comment):
    """
    Creates a pull request from the specified branch to the main branch.
    If a PR from this branch already exists, it updates the PR.
    """
    # Step 1: Check if a pull request already exists from this branch
    pr_search_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?head={REPO_OWNER}:{branch_name}&base=main"
    pr_search_response = requests.get(pr_search_url, headers=HEADERS)
    existing_pr = pr_search_response.json()

    if existing_pr:
        # If a PR already exists, update its title and body
        pr_id = existing_pr[0]["number"]
        update_pr_url = (
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_id}"
        )
        pr_data = {
            "title": f"Updated Automated PR by {user_id}",
            "body": f"{pr_comment}\n\nUpdated by {user_id}.",
        }
        response = requests.patch(update_pr_url, headers=HEADERS, json=pr_data)
        return response.json().get("html_url", "Error updating PR")

    # Step 2: If no existing PR, create a new one
    pr_data = {
        "title": f"Automated PR by {user_id}",
        "head": branch_name,
        "base": "main",
        "body": f"{pr_comment}\n\nSubmitted by {user_id}.",
    }
    pr_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    response = requests.post(pr_url, headers=HEADERS, json=pr_data)
    return response.json().get("html_url", "Error creating PR")


@app.route("/submit-changes", methods=["POST"])
def submit_changes():
    """
    API endpoint to handle JSON file updates and create a pull request.
    Expects JSON payload with 'file_path', 'file_content', 'user_id', and 'pr_comment'.
    """
    data = request.json
    file_path = data.get("file_path")
    file_content = data.get("file_content")
    user_id = data.get("user_id")
    pr_comment = data.get("pr_comment")
    branch_name = data.get("branch_name")

    if not all([file_path, file_content, user_id, pr_comment]):
        return jsonify({"error": "Missing required fields"}), 400

    # Generate a unique branch name for this user's changes
    branch_name = f"{branch_name}-{user_id}"

    # Step 1: Create a new branch
    if not create_branch(branch_name):
        return jsonify({"error": "Failed to create branch"}), 500

    # Step 2: Update file on GitHub
    commit_message = f"Update {file_path} by {user_id}"
    if not update_file(branch_name, file_path, file_content, commit_message):
        return jsonify({"error": "Failed to update file"}), 500

    # Step 3: Create a pull request
    pr_url = create_or_update_pull_request(branch_name, user_id, pr_comment)
    if "Error" in pr_url:
        return jsonify({"error": "Failed to create pull request"}), 500

    return jsonify({"message": "Pull request created successfully", "pr_url": pr_url})


if __name__ == "__main__":
    app.run(debug=True)
