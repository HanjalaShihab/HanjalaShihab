#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = os.environ.get("GITHUB_USERNAME", "HanjalaShihab")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_FILE = ROOT / "assets" / "profile-header.template.svg"
OUTPUT_FILE = ROOT / "assets" / "profile-header.svg"

API_BASE = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "HanjalaShihab-GitHub-Profile-Updater",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


# ============================================================
# GITHUB API
# ============================================================

def github_get(endpoint):
    """Make a GET request to GitHub's REST API."""

    url = f"{API_BASE}{endpoint}"

    request = urllib.request.Request(
        url,
        headers=HEADERS,
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        print(f"\nGitHub API error: HTTP {error.code}")
        print(body)

        raise

    except Exception as error:
        print(f"\nRequest failed: {error}")
        raise


# ============================================================
# FETCH USER
# ============================================================

def get_user():
    print(f"Fetching GitHub user: {USERNAME}")

    user = github_get(f"/users/{USERNAME}")

    print(f"User found: {user.get('login')}")
    print(f"Followers: {user.get('followers', 0)}")

    return user


# ============================================================
# FETCH REPOSITORIES
# ============================================================

def get_repositories():
    print("Fetching repositories...")

    repositories = []
    page = 1

    while True:

        data = github_get(
            f"/users/{USERNAME}/repos"
            f"?per_page=100"
            f"&page={page}"
            f"&type=owner"
            f"&sort=updated"
        )

        if not data:
            break

        repositories.extend(data)

        print(
            f"Fetched repository page {page}: "
            f"{len(data)} repositories"
        )

        if len(data) < 100:
            break

        page += 1

    # Exclude forks
    repositories = [
        repo
        for repo in repositories
        if not repo.get("fork", False)
    ]

    print(f"Total original repositories: {len(repositories)}")

    return repositories


# ============================================================
# FETCH COMMITS
# ============================================================

def get_commit_count():
    print("Fetching commit count...")

    endpoint = (
        f"/search/commits"
        f"?q=author:{USERNAME}"
        f"&per_page=1"
    )

    result = github_get(endpoint)

    count = result.get("total_count", 0)

    print(f"Total commits: {count}")

    return count


# ============================================================
# FORMAT NUMBERS
# ============================================================

def format_number(number):

    if number is None:
        return "0"

    number = int(number)

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:
        return f"{number / 1_000:.1f}K"

    return str(number)


# ============================================================
# CALCULATE STATS
# ============================================================

def collect_stats():

    user = get_user()

    repositories = get_repositories()

    commits = get_commit_count()

    repo_count = len(repositories)

    stars = sum(
        int(repo.get("stargazers_count", 0))
        for repo in repositories
    )

    followers = int(user.get("followers", 0))

    stats = {
        "REPOS": format_number(repo_count),
        "COMMITS": format_number(commits),
        "STARS": format_number(stars),
        "FOLLOWERS": format_number(followers),
    }

    print("\n==============================")
    print("GitHub Profile Stats")
    print("==============================")
    print(f"Username : {USERNAME}")
    print(f"Repos    : {stats['REPOS']}")
    print(f"Commits  : {stats['COMMITS']}")
    print(f"Stars    : {stats['STARS']}")
    print(f"Followers: {stats['FOLLOWERS']}")
    print("==============================\n")

    return stats


# ============================================================
# GENERATE SVG
# ============================================================

def generate_svg(stats):

    if not TEMPLATE_FILE.exists():
        print(f"ERROR: Template not found:")
        print(TEMPLATE_FILE)
        sys.exit(1)

    template = TEMPLATE_FILE.read_text(
        encoding="utf-8"
    )

    replacements = {
        "{{REPOS}}": stats["REPOS"],
        "{{COMMITS}}": stats["COMMITS"],
        "{{STARS}}": stats["STARS"],
        "{{FOLLOWERS}}": stats["FOLLOWERS"],

        # GitHub Actions run number
        "{{BUILD}}": os.environ.get(
            "GITHUB_RUN_NUMBER",
            "1"
        ),
    }

    svg = template

    for placeholder, value in replacements.items():
        svg = svg.replace(
            placeholder,
            str(value)
        )

    # Make sure no dynamic placeholders remain
    unresolved = [
        "{{REPOS}}",
        "{{COMMITS}}",
        "{{STARS}}",
        "{{FOLLOWERS}}",
        "{{BUILD}}",
    ]

    remaining = [
        placeholder
        for placeholder in unresolved
        if placeholder in svg
    ]

    if remaining:
        print("ERROR: Unresolved placeholders:")
        for placeholder in remaining:
            print(f"  - {placeholder}")

        sys.exit(1)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        svg,
        encoding="utf-8"
    )

    print(f"SVG generated successfully:")
    print(OUTPUT_FILE)


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n======================================")
    print(" GitHub Profile SVG Generator")
    print("======================================")
    print(f"Username: {USERNAME}")
    print()

    try:

        stats = collect_stats()

        generate_svg(stats)

        print("\nSUCCESS")
        print("Profile SVG generated successfully.")

    except Exception as error:

        print("\n======================================")
        print(" GENERATION FAILED")
        print("======================================")
        print(error)

        sys.exit(1)


if __name__ == "__main__":
    main()
