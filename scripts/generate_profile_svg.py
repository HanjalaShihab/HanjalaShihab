#!/usr/bin/env python3

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

USERNAME = os.environ.get("GITHUB_USERNAME", "HanjalaShihab")

ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_FILE = ROOT / "assets" / "profile-header.template.svg"
OUTPUT_FILE = ROOT / "assets" / "profile-header.svg"


API_BASE = "https://api.github.com"

API_VERSION = "2026-03-10"


# ============================================================
# GitHub API
# ============================================================

def github_request(endpoint: str):
    """
    Make a request to the GitHub REST API.
    """

    token = os.environ.get("GITHUB_TOKEN")

    url = f"{API_BASE}{endpoint}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": f"{USERNAME}-profile-generator",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        print(
            f"GitHub API error: HTTP {error.code}",
            file=sys.stderr,
        )

        print(body, file=sys.stderr)

        raise


# ============================================================
# Fetch user
# ============================================================

def get_user():
    return github_request(
        f"/users/{urllib.parse.quote(USERNAME)}"
    )


# ============================================================
# Fetch repositories
# ============================================================

def get_repositories():
    """
    Fetch all public repositories owned by the user.

    Forks are excluded from the displayed repository count.
    """

    repositories = []

    page = 1

    while True:

        endpoint = (
            f"/users/{urllib.parse.quote(USERNAME)}/repos"
            f"?per_page=100"
            f"&page={page}"
            f"&type=owner"
            f"&sort=updated"
        )

        data = github_request(endpoint)

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    # Only repositories actually owned by the user.
    # Forks are excluded.
    repositories = [
        repo
        for repo in repositories
        if not repo.get("fork", False)
    ]

    return repositories


# ============================================================
# Commit count
# ============================================================

def get_commit_count():
    """
    Get the number of commits attributed to the GitHub user
    using GitHub's commit search endpoint.

    This is a GitHub search count, not a raw sum of every commit
    across every repository.
    """

    query = urllib.parse.quote(
        f"author:{USERNAME}"
    )

    endpoint = (
        f"/search/commits"
        f"?q={query}"
        f"&per_page=1"
    )

    data = github_request(endpoint)

    return int(data.get("total_count", 0))


# ============================================================
# Format numbers
# ============================================================

def format_number(value: int) -> str:
    """
    Format large numbers for the SVG.

    Examples:

    42      -> 42
    1284    -> 1.3K
    15320   -> 15.3K
    1200000 -> 1.2M
    """

    if value < 1000:
        return str(value)

    if value < 1_000_000:
        return f"{value / 1000:.1f}K"

    return f"{value / 1_000_000:.1f}M"


# ============================================================
# Generate SVG
# ============================================================

def generate_svg(stats):
    """
    Load the SVG template and replace placeholders.
    """

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Template not found: {TEMPLATE_FILE}"
        )

    template = TEMPLATE_FILE.read_text(
        encoding="utf-8"
    )

    replacements = {
        "{{USERNAME}}": stats["username"],
        "{{REPOS}}": stats["repos"],
        "{{COMMITS}}": stats["commits"],
        "{{STARS}}": stats["stars"],
        "{{FOLLOWERS}}": stats["followers"],
        "{{BUILD}}": stats["build"],
    }

    svg = template

    for placeholder, value in replacements.items():

        svg = svg.replace(
            placeholder,
            str(value),
        )

    # Prevent accidentally leaving unresolved variables.
    unresolved = re.findall(
        r"\{\{[A-Z0-9_]+\}\}",
        svg,
    )

    if unresolved:
        raise RuntimeError(
            "Unresolved SVG placeholders: "
            + ", ".join(sorted(set(unresolved)))
        )

    OUTPUT_FILE.write_text(
        svg,
        encoding="utf-8",
    )


# ============================================================
# Main
# ============================================================

def main():

    print(
        f"Updating GitHub profile for @{USERNAME}"
    )

    user = get_user()

    repositories = get_repositories()

    repo_count = len(repositories)

    stars = sum(
        int(repo.get("stargazers_count", 0))
        for repo in repositories
    )

    followers = int(
        user.get("followers", 0)
    )

    commits = get_commit_count()

    build = os.environ.get(
        "GITHUB_RUN_NUMBER",
        "local",
    )

    stats = {
        "username": USERNAME,
        "repos": format_number(repo_count),
        "commits": format_number(commits),
        "stars": format_number(stars),
        "followers": format_number(followers),
        "build": build,
    }

    print()
    print("GitHub statistics")
    print("-----------------")
    print(f"Username:  {USERNAME}")
    print(f"Repos:     {repo_count}")
    print(f"Commits:   {commits}")
    print(f"Stars:     {stars}")
    print(f"Followers: {followers}")
    print(f"Build:     {build}")
    print()

    generate_svg(stats)

    print(
        f"Generated: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
