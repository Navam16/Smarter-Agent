"""
agents/github_agent.py
──────────────────────
Sources candidates from GitHub using the free GitHub API.

╔══════════════════════════════════════════════════════╗
║  SERVICE  →  GitHub API                              ║
║  KEY      →  GITHUB_TOKEN  (set in .env)             ║
║  GET IT   →  github.com/settings/tokens              ║
║  COST     →  FREE (5000 requests/hour with token)    ║
║  FREE     →  60 requests/hour without token          ║
╚══════════════════════════════════════════════════════╝
"""

import os
import requests
import time
from groq import Groq
import json
import re
from database.db import upsert_candidate, log_search, was_recently_searched

# ── GitHub API setup ──────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def gh_get(url: str, params: dict = None) -> dict | list | None:
    """Safe GitHub API GET with rate limit handling."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 403:
            print("⚠️ GitHub rate limit hit. Waiting 60s...")
            time.sleep(60)
            return None
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        print(f"GitHub API error: {e}")
        return None


def extract_skills_with_ai(groq_key: str, bio: str, repos: list) -> list[str]:
    """Use Groq LLM to extract skills from bio and repos."""
    if not groq_key:
        return []
    try:
        repo_names = [r.get("name", "") + " " + (r.get("description") or "") for r in repos[:10]]
        langs = list(set([r.get("language") for r in repos if r.get("language")]))
        topics = []
        for r in repos[:5]:
            topics.extend(r.get("topics", []))

        prompt = f"""Extract technical skills from this developer profile.
Return ONLY a JSON array of skill strings. Max 15 skills.
No markdown, no explanation.

Bio: {bio[:300]}
Languages: {langs}
Repo names: {repo_names[:5]}
Topics: {list(set(topics))[:20]}

Return: ["skill1", "skill2", ...]"""

        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return langs[:10]


def determine_seniority(public_repos: int, followers: int, years_active: int) -> str:
    score = public_repos * 0.3 + followers * 0.1 + years_active * 2
    if score > 50:
        return "Senior"
    elif score > 20:
        return "Mid-level"
    else:
        return "Junior"


def estimate_experience(created_at: str) -> float:
    """Estimate years of experience from account creation date."""
    try:
        from datetime import datetime
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(created.tzinfo)
        return round((now - created).days / 365, 1)
    except Exception:
        return 0


def search_github_users(
    skill: str,
    location: str = "",
    groq_key: str = "",
    max_results: int = 30,
    progress_callback=None
) -> tuple[int, int]:
    """
    Search GitHub for developers matching skill + location.
    Returns (new_count, total_found)
    """
    query = f"{skill} in:bio,readme"
    if location:
        query += f" location:{location}"

    cache_key = f"github:{query}"
    if was_recently_searched(cache_key, hours=12):
        if progress_callback:
            progress_callback(f"⏭️ Already searched '{skill}' recently — skipping")
        return 0, 0

    if progress_callback:
        progress_callback(f"🔍 Searching GitHub for: {skill}" + (f" in {location}" if location else ""))

    url = "https://api.github.com/search/users"
    params = {"q": query, "per_page": min(max_results, 30), "sort": "followers"}
    data = gh_get(url, params)

    if not data or "items" not in data:
        return 0, 0

    users = data["items"]
    total_found = len(users)
    new_count = 0

    for i, user in enumerate(users):
        if progress_callback:
            progress_callback(f"👤 Processing {user['login']} ({i+1}/{total_found})")

        # Get full profile
        profile = gh_get(f"https://api.github.com/users/{user['login']}")
        if not profile:
            continue

        # Get repos for skill extraction
        repos = gh_get(
            f"https://api.github.com/users/{user['login']}/repos",
            {"per_page": 20, "sort": "updated"}
        ) or []

        # Extract skills
        skills = extract_skills_with_ai(groq_key, profile.get("bio") or "", repos)
        if not skills:
            # Fallback to top languages
            langs = list(set([r.get("language") for r in repos if r.get("language")]))
            skills = langs[:10]

        years = estimate_experience(profile.get("created_at", ""))
        seniority = determine_seniority(
            profile.get("public_repos", 0),
            profile.get("followers", 0),
            int(years)
        )

        candidate = {
            "name":             profile.get("name") or user["login"],
            "role":             profile.get("bio", "")[:100] if profile.get("bio") else f"{skill} Developer",
            "company":          (profile.get("company") or "").replace("@", "").strip(),
            "location":         profile.get("location") or location or "",
            "email":            profile.get("email") or "",
            "github_url":       profile.get("html_url", ""),
            "profile_url":      profile.get("html_url", ""),
            "bio":              profile.get("bio") or "",
            "skills":           skills,
            "experience_years": years,
            "seniority":        seniority,
            "activity_score":   f"{profile.get('public_repos', 0)} repos · {profile.get('followers', 0)} followers",
            "job_seeking":      False,
            "source":           "GitHub",
            "source_query":     f"{skill} {location}".strip()
        }

        is_new, cid = upsert_candidate(candidate)
        if is_new:
            new_count += 1

        time.sleep(0.3)  # gentle rate limiting

    log_search(cache_key, "GitHub", total_found)

    if progress_callback:
        progress_callback(f"✅ GitHub: {new_count} new candidates added ({total_found - new_count} duplicates skipped)")

    return new_count, total_found


def run_github_sourcing(
    skills: list[str],
    location: str = "",
    groq_key: str = "",
    progress_callback=None
) -> dict:
    """Run GitHub sourcing for multiple skills."""
    total_new = 0
    total_found = 0

    for skill in skills:
        new, found = search_github_users(
            skill=skill,
            location=location,
            groq_key=groq_key,
            progress_callback=progress_callback
        )
        total_new += new
        total_found += found
        time.sleep(1)

    return {"new": total_new, "total": total_found, "source": "GitHub"}
