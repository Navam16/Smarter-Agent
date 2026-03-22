"""
agents/search_agent.py
───────────────────────
Sources candidates via Google Search (Serper.dev API).
Finds LinkedIn, GitHub, and other public profiles.

╔══════════════════════════════════════════════════════╗
║  SERVICE  →  Serper.dev (Google Search API)          ║
║  KEY      →  SERPER_API_KEY  (set in .env)           ║
║  GET IT   →  serper.dev  → Sign up free              ║
║  COST     →  Free: 2,500 searches                    ║
║             Paid: $50/month = 50,000 searches        ║
║                                                      ║
║  SERVICE  →  Groq (LLM extraction)                   ║
║  KEY      →  GROQ_API_KEY  (set in .env)             ║
╚══════════════════════════════════════════════════════╝
"""

import os
import requests
import json
import re
import time
from groq import Groq
from database.db import upsert_candidate, log_search, was_recently_searched

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")


def google_search(query: str, num: int = 10) -> list[dict]:
    """
    Execute Google search via Serper.dev.
    Returns list of result dicts with title, link, snippet.
    """
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": num},
            timeout=10
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("organic", [])
    except Exception as e:
        print(f"Serper search error: {e}")
        return []


def extract_candidate_from_result(groq_key: str, result: dict, source_query: str) -> dict | None:
    """Use Groq LLM to extract structured candidate data from search result."""
    if not groq_key:
        return None
    try:
        prompt = f"""Extract candidate information from this search result.
Return ONLY valid JSON. If this is not a person's profile, return null.

Title: {result.get('title', '')}
URL: {result.get('link', '')}
Snippet: {result.get('snippet', '')}

Return JSON:
{{
  "name": "...",
  "role": "...",
  "company": "...",
  "location": "...",
  "skills": ["skill1", "skill2"],
  "linkedin_url": "..." or null,
  "github_url": "..." or null,
  "job_seeking": true/false,
  "bio": "brief summary"
}}

If not a person profile, return: null"""

        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        raw = resp.choices[0].message.content.strip()
        if raw.lower() == "null" or "null" in raw[:10]:
            return None
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
        data = json.loads(raw)
        if not data or not data.get("name"):
            return None

        # Determine profile URL
        url = result.get("link", "")
        if not data.get("linkedin_url") and "linkedin.com/in/" in url:
            data["linkedin_url"] = url
        if not data.get("github_url") and "github.com/" in url:
            data["github_url"] = url

        data["profile_url"]  = url
        data["source"]       = "Web Search"
        data["source_query"] = source_query
        return data
    except Exception:
        return None


def build_search_queries(role: str, location: str = "", platform: str = "linkedin") -> list[str]:
    """Build targeted search queries for finding candidates."""
    queries = []

    if platform == "linkedin":
        base = f'site:linkedin.com/in "{role}"'
        queries.append(base)
        if location:
            queries.append(f'{base} "{location}"')
        queries.append(f'{base} "open to work"')
        queries.append(f'{base} "looking for opportunities"')
        if location:
            queries.append(f'{base} "{location}" "open to work"')

    elif platform == "github":
        queries.append(f'site:github.com "{role}"')
        if location:
            queries.append(f'site:github.com "{role}" "{location}"')

    elif platform == "stackoverflow":
        queries.append(f'site:stackoverflow.com/users "{role}"')

    return queries


def run_web_sourcing(
    role: str,
    location: str = "",
    groq_key: str = "",
    serper_key: str = "",
    platforms: list[str] = None,
    progress_callback=None
) -> dict:
    """
    Run web-based candidate sourcing across platforms.
    Uses Google search to find public profiles.
    """
    if platforms is None:
        platforms = ["linkedin", "github", "stackoverflow"]

    # Use provided keys or fall back to env
    gk = groq_key or GROQ_API_KEY
    sk = serper_key or SERPER_API_KEY

    if not sk:
        if progress_callback:
            progress_callback("⚠️ No Serper API key — web search skipped. Add SERPER_API_KEY to .env")
        return {"new": 0, "total": 0, "source": "Web Search", "error": "No API key"}

    total_new   = 0
    total_found = 0

    for platform in platforms:
        queries = build_search_queries(role, location, platform)

        for query in queries:
            cache_key = f"web:{query}"
            if was_recently_searched(cache_key, hours=24):
                if progress_callback:
                    progress_callback(f"⏭️ Already searched recently — skipping")
                continue

            if progress_callback:
                progress_callback(f"🌐 Searching {platform.title()}: {role}" + (f" in {location}" if location else ""))

            results = google_search(query, num=10)
            log_search(cache_key, "Web Search", len(results))

            for result in results:
                candidate = extract_candidate_from_result(gk, result, f"{role} {location}".strip())
                if candidate:
                    total_found += 1
                    is_new, _ = upsert_candidate(candidate)
                    if is_new:
                        total_new += 1
                time.sleep(0.2)

            time.sleep(1)  # between queries

    if progress_callback:
        progress_callback(f"✅ Web Search: {total_new} new candidates ({total_found - total_new} duplicates skipped)")

    return {"new": total_new, "total": total_found, "source": "Web Search"}
