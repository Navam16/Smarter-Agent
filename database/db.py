"""
database/db.py
──────────────
Local SQLite database for candidate storage.
Handles deduplication automatically.

For production: swap SQLite → Supabase
by replacing the functions below with
Supabase client calls. Schema stays same.
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("talent.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS candidates (
            id               TEXT PRIMARY KEY,
            name             TEXT,
            role             TEXT,
            company          TEXT,
            location         TEXT,
            email            TEXT,
            phone            TEXT,
            skills           TEXT,
            experience_years REAL,
            seniority        TEXT,
            github_url       TEXT,
            linkedin_url     TEXT,
            profile_url      TEXT,
            bio              TEXT,
            source           TEXT,
            source_query     TEXT,
            activity_score   TEXT,
            job_seeking      INTEGER DEFAULT 0,
            contacted        INTEGER DEFAULT 0,
            status           TEXT DEFAULT 'new',
            match_score      REAL DEFAULT 0,
            created_at       TEXT,
            last_seen_at     TEXT,
            raw_data         TEXT
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query       TEXT UNIQUE,
            source      TEXT,
            results     INTEGER DEFAULT 0,
            searched_at TEXT
        );

        CREATE TABLE IF NOT EXISTS outreach_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT,
            type         TEXT,
            status       TEXT,
            sent_at      TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );
    """)
    conn.commit()
    conn.close()


def make_candidate_id(
    github_url: str = None,
    email: str = None,
    name: str = "",
    company: str = ""
) -> str:
    """Generate unique fingerprint for candidate."""
    if github_url and github_url.strip():
        key = github_url.lower().strip()
    elif email and email.strip():
        key = email.lower().strip()
    else:
        key = f"{name.lower().strip()}_{company.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def upsert_candidate(data: dict) -> tuple[bool, str]:
    """
    Insert or update candidate.
    Returns (is_new, candidate_id)
    Handles ALL duplicate scenarios safely using INSERT OR REPLACE.
    Never raises IntegrityError.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()

    cid = make_candidate_id(
        github_url=data.get("github_url"),
        email=data.get("email"),
        name=data.get("name", ""),
        company=data.get("company", "")
    )

    skills = (
        json.dumps(data.get("skills", []))
        if isinstance(data.get("skills"), list)
        else data.get("skills", "[]")
    )

    # Check if already exists
    existing = conn.execute(
        "SELECT id FROM candidates WHERE id = ?", (cid,)
    ).fetchone()

    try:
        if existing:
            # Update existing record — never duplicate
            conn.execute("""
                UPDATE candidates SET
                    last_seen_at     = ?,
                    role             = CASE WHEN ? != '' THEN ? ELSE role END,
                    company          = CASE WHEN ? != '' THEN ? ELSE company END,
                    email            = CASE WHEN ? != '' THEN ? ELSE email END,
                    phone            = CASE WHEN ? != '' THEN ? ELSE phone END,
                    skills           = CASE WHEN ? != '[]' THEN ? ELSE skills END,
                    bio              = CASE WHEN ? != '' THEN ? ELSE bio END,
                    activity_score   = CASE WHEN ? != '' THEN ? ELSE activity_score END
                WHERE id = ?
            """, (
                now,
                data.get("role", ""),      data.get("role", ""),
                data.get("company", ""),   data.get("company", ""),
                data.get("email", ""),     data.get("email", ""),
                data.get("phone", ""),     data.get("phone", ""),
                skills,                    skills,
                data.get("bio", ""),       data.get("bio", ""),
                data.get("activity_score", ""), data.get("activity_score", ""),
                cid
            ))
            conn.commit()
            conn.close()
            return False, cid
        else:
            # Fresh insert
            conn.execute("""
                INSERT INTO candidates (
                    id, name, role, company, location, email, phone,
                    skills, experience_years, seniority, github_url,
                    linkedin_url, profile_url, bio, source, source_query,
                    activity_score, job_seeking, status,
                    created_at, last_seen_at, raw_data
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                cid,
                data.get("name", "Unknown"),
                data.get("role", ""),
                data.get("company", ""),
                data.get("location", ""),
                data.get("email", ""),
                data.get("phone", ""),
                skills,
                data.get("experience_years"),
                data.get("seniority", ""),
                data.get("github_url", ""),
                data.get("linkedin_url", ""),
                data.get("profile_url", ""),
                data.get("bio", ""),
                data.get("source", ""),
                data.get("source_query", ""),
                data.get("activity_score", ""),
                1 if data.get("job_seeking") else 0,
                "new",
                now,
                now,
                json.dumps(data)
            ))
            conn.commit()
            conn.close()
            return True, cid

    except Exception as e:
        # Catch ANY remaining integrity errors gracefully
        # This handles race conditions and edge cases
        conn.close()
        print(f"DB upsert handled gracefully: {e}")
        return False, cid


def get_all_candidates(
    status: str = None,
    source: str = None,
    limit: int = 500
) -> list[dict]:
    """Fetch candidates with optional filters."""
    conn = get_conn()
    query  = "SELECT * FROM candidates WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["skills"] = json.loads(d.get("skills") or "[]")
        except Exception:
            d["skills"] = []
        result.append(d)
    return result


def get_stats() -> dict:
    """Get dashboard statistics."""
    conn  = get_conn()
    today = datetime.utcnow().date().isoformat()

    total    = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    new      = conn.execute("SELECT COUNT(*) FROM candidates WHERE status = 'new'").fetchone()[0]
    contacted= conn.execute("SELECT COUNT(*) FROM candidates WHERE contacted = 1").fetchone()[0]
    github   = conn.execute("SELECT COUNT(*) FROM candidates WHERE source = 'GitHub'").fetchone()[0]
    web      = conn.execute("SELECT COUNT(*) FROM candidates WHERE source = 'Web Search'").fetchone()[0]
    today_ct = conn.execute(
        "SELECT COUNT(*) FROM candidates WHERE created_at LIKE ?",
        (f"{today}%",)
    ).fetchone()[0]

    conn.close()
    return {
        "total":     total,
        "new":       new,
        "contacted": contacted,
        "github":    github,
        "web":       web,
        "today":     today_ct,
    }


def update_candidate_status(candidate_id: str, status: str):
    """Update status of a candidate."""
    conn = get_conn()
    conn.execute(
        "UPDATE candidates SET status = ? WHERE id = ?",
        (status, candidate_id)
    )
    conn.commit()
    conn.close()


def log_search(query: str, source: str, results: int):
    """Record a search query to prevent redundant re-searches."""
    conn = get_conn()
    now  = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO search_history (query, source, results, searched_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(query) DO UPDATE SET
            results     = excluded.results,
            searched_at = excluded.searched_at
    """, (query, source, results, now))
    conn.commit()
    conn.close()


def was_recently_searched(query: str, hours: int = 24) -> bool:
    """Prevent re-searching same query within cooldown period."""
    conn = get_conn()
    row  = conn.execute(
        "SELECT searched_at FROM search_history WHERE query = ?", (query,)
    ).fetchone()
    conn.close()

    if not row:
        return False

    last = datetime.fromisoformat(row["searched_at"])
    diff = datetime.utcnow() - last
    return diff.total_seconds() < hours * 3600


def search_candidates(query: str) -> list[dict]:
    """Full text search across all candidate fields."""
    conn = get_conn()
    q    = f"%{query}%"
    rows = conn.execute("""
        SELECT * FROM candidates
        WHERE name     LIKE ?
           OR role     LIKE ?
           OR skills   LIKE ?
           OR company  LIKE ?
           OR location LIKE ?
           OR bio      LIKE ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (q, q, q, q, q, q)).fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["skills"] = json.loads(d.get("skills") or "[]")
        except Exception:
            d["skills"] = []
        result.append(d)
    return result


# Initialize on import
init_db()
