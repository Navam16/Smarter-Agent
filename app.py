"""
╔══════════════════════════════════════════════════════════════╗
║         AI TALENT SOURCING AGENT — MVP DASHBOARD             ║
║         GitHub + Web Search · Groq AI · SQLite DB            ║
╚══════════════════════════════════════════════════════════════╝

API KEYS NEEDED:
─────────────────────────────────────────────────────────────
  SERVICE         KEY               COST    PURPOSE
  ──────────────────────────────────────────────────────────
  Groq        →  GROQ_API_KEY      Free    LLM extraction
  GitHub      →  GITHUB_TOKEN      Free    Developer sourcing
  Serper.dev  →  SERPER_API_KEY    $50/mo  Google/LinkedIn search
─────────────────────────────────────────────────────────────
"""

import streamlit as st
import os
import json
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from database.db import (
    get_all_candidates, get_stats,
    update_candidate_status, search_candidates, init_db
)
from agents.github_agent import run_github_sourcing
from agents.search_agent import run_web_sourcing

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# 🔑  KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_key(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, st.session_state.get(f"key_{name}", ""))

# ─────────────────────────────────────────────────────────────────────────────
# 🎨  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TalentAI — Sourcing Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

*, html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060D18 0%, #0A1628 100%);
    border-right: 1px solid #0F2337;
}
section[data-testid="stSidebar"] * { color: #8899BB !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #E2E8F0 !important;
    font-family: 'Syne', sans-serif !important;
}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stSelectbox select {
    background: #0D1B2E !important;
    border: 1px solid #1E3A5F !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}
section[data-testid="stSidebar"] label {
    font-size: 0.68rem !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    color: #334D6E !important;
    font-weight: 700 !important;
}

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1300px;
}

.dash-header {
    background: linear-gradient(135deg, #060D18 0%, #0D1F3C 50%, #091426 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    border: 1px solid #0F2337;
    position: relative;
    overflow: hidden;
}
.dash-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, #00897B22 0%, transparent 70%);
    border-radius: 50%;
}
.dash-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -1px;
    margin: 0;
    line-height: 1.1;
}
.dash-title span { color: #00BFA5; }
.dash-sub { font-size: 0.88rem; color: #4A6FA5; margin-top: 6px; }
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00BFA5;
    margin-right: 6px;
    box-shadow: 0 0 6px #00BFA5;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.stat-card {
    background: linear-gradient(135deg, #0A1628 0%, #0D1F3C 100%);
    border: 1px solid #1A2F4E;
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
}
.stat-card:hover { border-color: #00897B; transform: translateY(-2px); }
.stat-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00897B, transparent);
}
.stat-number {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    color: #00BFA5;
    line-height: 1;
    margin-bottom: 4px;
}
.stat-label {
    font-size: 0.72rem;
    color: #4A6FA5;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.stat-icon { font-size: 1.4rem; margin-bottom: 8px; display: block; }

.cand-card {
    background: linear-gradient(135deg, #0A1628 0%, #0D1F3C 100%);
    border: 1px solid #1A2F4E;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 12px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.cand-card:hover {
    border-color: #00897B44;
    box-shadow: 0 4px 20px rgba(0,137,123,0.1);
}
.cand-name {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 2px;
}
.cand-role { font-size: 0.82rem; color: #4A6FA5; margin-bottom: 10px; }
.cand-company { color: #00BFA5; font-weight: 600; }
.skill-tag {
    display: inline-block;
    background: #0F2337;
    color: #00BFA5;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    margin: 2px 2px 2px 0;
    border: 1px solid #1A3A5C;
    letter-spacing: 0.3px;
}
.source-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}
.source-github { background: #1A2F4E; color: #58A6FF; border: 1px solid #1F4080; }
.source-web    { background: #1A3040; color: #00BFA5; border: 1px solid #1A4A5A; }

.section-head {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1A2F4E;
}

.stButton > button {
    background: linear-gradient(135deg, #00897B, #00695C) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    padding: 10px 20px !important;
    width: 100% !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #060D18;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #1A2F4E;
}
.stTabs [data-baseweb="tab"] {
    color: #4A6FA5 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 8px !important;
}
.stTabs [aria-selected="true"] { background: #00897B !important; color: white !important; }

.log-box {
    background: #060D18;
    border: 1px solid #1A2F4E;
    border-radius: 10px;
    padding: 16px;
    font-size: 0.82rem;
    color: #4A6FA5;
    max-height: 300px;
    overflow-y: auto;
}
.log-entry { margin: 4px 0; }
.log-success { color: #00BFA5; }
.log-warning { color: #FFA726; }
.log-info    { color: #58A6FF; }

.stDataFrame { border-radius: 10px; overflow: hidden; }
.stSelectbox > div { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 🔧  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for key in ["sourcing_logs", "is_sourcing", "last_run"]:
    if key not in st.session_state:
        if key == "sourcing_logs":
            st.session_state[key] = []
        elif key == "is_sourcing":
            st.session_state[key] = False
        else:
            st.session_state[key] = None


# ─────────────────────────────────────────────────────────────────────────────
# 📊  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 TalentAI")
    st.markdown("---")
    st.markdown("### 🔑 API Keys")

    groq_key = get_key("GROQ_API_KEY")
    if groq_key:
        st.success("✅ Groq connected")
    else:
        manual = st.text_input("Groq API Key", type="password", placeholder="gsk_...",
                               help="console.groq.com — Free")
        st.session_state["key_GROQ_API_KEY"] = manual

    gh_key = get_key("GITHUB_TOKEN")
    if gh_key:
        st.success("✅ GitHub connected")
    else:
        manual_gh = st.text_input("GitHub Token", type="password", placeholder="ghp_...",
                                  help="github.com/settings/tokens — Free")
        st.session_state["key_GITHUB_TOKEN"] = manual_gh

    serper_key = get_key("SERPER_API_KEY")
    if serper_key:
        st.success("✅ Serper connected")
    else:
        manual_serper = st.text_input("Serper API Key", type="password", placeholder="...",
                                      help="serper.dev — Optional for web search")
        st.session_state["key_SERPER_API_KEY"] = manual_serper

    st.markdown("---")
    st.markdown("### ⚙️ Sourcing Config")

    role_input = st.text_input("Job Role / Skills", placeholder="Python Developer",
                               value="Python Developer")
    location_input = st.text_input("Location (optional)", placeholder="Bangalore")

    platforms = st.multiselect(
        "Source Platforms",
        ["GitHub", "LinkedIn (via Google)", "Stack Overflow"],
        default=["GitHub"]
    )

    max_per_skill = st.slider("Max candidates per search", 10, 50, 20)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        run_btn = st.button("🚀 Source Now", disabled=st.session_state.is_sourcing)
    with col2:
        clear_logs = st.button("🗑️ Clear Logs")

    if clear_logs:
        st.session_state.sourcing_logs = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📁 Navigation")
    page = st.radio("", ["📊 Dashboard", "👥 Candidates", "🔍 Search", "📈 Analytics"],
                    label_visibility="collapsed")


# ─────────────────────────────────────────────────────────────────────────────
# 📊  HEADER
# ─────────────────────────────────────────────────────────────────────────────
stats = get_stats()
now_str = datetime.now().strftime("%d %b %Y · %H:%M")

st.markdown(f"""
<div class="dash-header">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div class="dash-title">Talent<span>AI</span> Sourcing</div>
            <div class="dash-sub">
                <span class="status-dot"></span>
                AI-powered candidate discovery · {now_str}
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#00BFA5;">{stats['total']:,}</div>
            <div style="font-size:0.72rem;color:#4A6FA5;letter-spacing:1px;text-transform:uppercase;">Total Candidates</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stat Cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
stat_data = [
    (c1, "🆕", stats["today"], "Added Today"),
    (c2, "✨", stats["new"], "New"),
    (c3, "📧", stats["contacted"], "Contacted"),
    (c4, "🐙", stats["github"], "From GitHub"),
    (c5, "🌐", stats["web"], "From Web"),
    (c6, "📊", stats["total"], "Total"),
]
for col, icon, val, label in stat_data:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <span class="stat-icon">{icon}</span>
            <div class="stat-number">{val:,}</div>
            <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ▶️  RUN SOURCING
# ─────────────────────────────────────────────────────────────────────────────
if run_btn:
    groq_key   = get_key("GROQ_API_KEY")
    gh_key     = get_key("GITHUB_TOKEN")
    serper_key = get_key("SERPER_API_KEY")

    if not groq_key:
        st.error("❌ Groq API key required. Add it in the sidebar.")
    elif not role_input:
        st.error("❌ Enter a job role to search for.")
    else:
        st.session_state.is_sourcing = True
        st.session_state.sourcing_logs = []

        log_placeholder = st.empty()
        progress_bar    = st.progress(0, text="Starting sourcing agent...")

        def add_log(msg: str):
            ts  = datetime.now().strftime("%H:%M:%S")
            cls = "log-success" if "✅" in msg else ("log-warning" if "⚠️" in msg else "log-info")
            st.session_state.sourcing_logs.append(
                f'<div class="log-entry {cls}">[{ts}] {msg}</div>'
            )
            logs_html = "\n".join(st.session_state.sourcing_logs[-20:])
            log_placeholder.markdown(
                f'<div class="log-box">{logs_html}</div>',
                unsafe_allow_html=True
            )

        total_new = 0
        skills = [s.strip() for s in role_input.split(",")]

        if "GitHub" in platforms:
            progress_bar.progress(0.1, text="🐙 Sourcing from GitHub...")
            add_log(f"🐙 Starting GitHub sourcing for: {role_input}")

            os.environ["GITHUB_TOKEN"] = gh_key or ""
            os.environ["GROQ_API_KEY"] = groq_key

            result = run_github_sourcing(
                skills=skills,
                location=location_input,
                groq_key=groq_key,
                progress_callback=add_log
            )
            total_new += result["new"]
            add_log(f"✅ GitHub complete: {result['new']} new candidates")
            progress_bar.progress(0.5, text="GitHub done...")

        if any(p in platforms for p in ["LinkedIn (via Google)", "Stack Overflow"]):
            if not serper_key:
                add_log("⚠️ Serper API key missing — web search skipped")
            else:
                progress_bar.progress(0.6, text="🌐 Sourcing from Web...")
                add_log(f"🌐 Starting web sourcing for: {role_input}")

                plat_map = {
                    "LinkedIn (via Google)": "linkedin",
                    "Stack Overflow": "stackoverflow"
                }
                active_platforms = [plat_map[p] for p in platforms if p in plat_map]
                os.environ["SERPER_API_KEY"] = serper_key

                result = run_web_sourcing(
                    role=role_input,
                    location=location_input,
                    groq_key=groq_key,
                    serper_key=serper_key,
                    platforms=active_platforms,
                    progress_callback=add_log
                )
                total_new += result["new"]
                add_log(f"✅ Web search complete: {result['new']} new candidates")

        progress_bar.progress(1.0, text="✅ Sourcing complete!")
        st.session_state.is_sourcing = False
        st.session_state.last_run = datetime.now().strftime("%H:%M:%S")
        add_log(f"🎯 TOTAL: {total_new} new candidates added to database")

        time.sleep(1)
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 📄  PAGES
# ─────────────────────────────────────────────────────────────────────────────

# ── DASHBOARD PAGE ────────────────────────────────────────────────────────────
if page == "📊 Dashboard":

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-head">🕒 Recent Candidates</div>', unsafe_allow_html=True)
        recent = get_all_candidates(limit=8)

        if not recent:
            st.markdown("""
            <div style="text-align:center;padding:50px;color:#2A4A6A;border:1px dashed #1A2F4E;border-radius:12px;">
                <div style="font-size:2.5rem;margin-bottom:12px;">🎯</div>
                <div style="font-family:'Syne',sans-serif;font-size:1rem;color:#4A6FA5;margin-bottom:8px;">
                    No candidates yet
                </div>
                <div style="font-size:0.85rem;color:#2A4A6A;">
                    Configure a role and click "Source Now" to begin
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for c in recent:
                skills_html = " ".join(
                    [f'<span class="skill-tag">{s}</span>' for s in (c["skills"] or [])[:6]]
                )
                src_cls  = "source-github" if c["source"] == "GitHub" else "source-web"
                src_icon = "🐙" if c["source"] == "GitHub" else "🌐"
                company_part = (
                    '<span class="cand-company"> · ' + c["company"] + '</span>'
                    if c.get("company") else ""
                )
                location_part = " · 📍 " + c["location"] if c.get("location") else ""
                exp_part = (
                    " · " + str(c["experience_years"]) + "y exp"
                    if c.get("experience_years") else ""
                )
                profile_link = (
                    '<a href="' + c["profile_url"] + '" target="_blank" '
                    'style="font-size:0.7rem;color:#00BFA5;text-decoration:none;">View Profile →</a>'
                    if c.get("profile_url") else ""
                )

                st.markdown(f"""
                <div class="cand-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div style="flex:1;">
                            <div class="cand-name">{c['name']}</div>
                            <div class="cand-role">
                                {c['role'] or '—'}{company_part}{location_part}
                            </div>
                            <div>{skills_html}</div>
                        </div>
                        <div style="text-align:right;min-width:110px;">
                            <span class="source-badge {src_cls}">{src_icon} {c['source']}</span><br>
                            <span style="font-size:0.7rem;color:#2A4A6A;margin-top:4px;display:block;">
                                {c['seniority'] or '—'}{exp_part}
                            </span>
                            {profile_link}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-head">📋 Sourcing Log</div>', unsafe_allow_html=True)

        if st.session_state.sourcing_logs:
            logs_html = "\n".join(st.session_state.sourcing_logs[-30:])
            st.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="log-box" style="text-align:center;color:#2A4A6A;padding:40px 16px;">
                Logs will appear here when sourcing runs
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.last_run:
            st.caption(f"Last run: {st.session_state.last_run}")


# ── CANDIDATES PAGE ───────────────────────────────────────────────────────────
elif page == "👥 Candidates":
    st.markdown('<div class="section-head">👥 All Candidates</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        filter_status = st.selectbox("Status", ["All", "new", "contacted", "shortlisted", "rejected"])
    with f2:
        filter_source = st.selectbox("Source", ["All", "GitHub", "Web Search"])
    with f3:
        filter_senior = st.selectbox("Seniority", ["All", "Senior", "Mid-level", "Junior"])

    candidates = get_all_candidates(
        status=None if filter_status == "All" else filter_status,
        source=None if filter_source == "All" else filter_source,
        limit=200
    )

    if filter_senior != "All":
        candidates = [c for c in candidates if c.get("seniority") == filter_senior]

    st.markdown(
        f"<div style='color:#4A6FA5;font-size:0.8rem;margin-bottom:12px;'>"
        f"{len(candidates)} candidates found</div>",
        unsafe_allow_html=True
    )

    status_options = ["new", "contacted", "shortlisted", "rejected"]

    for c in candidates:
        skills_html = " ".join(
            [f'<span class="skill-tag">{s}</span>' for s in (c["skills"] or [])[:8]]
        )
        company_str  = "· " + c["company"] if c.get("company") else ""
        role_str     = c.get("role") or "—"
        expander_label = f"{c['name']} — {role_str} {company_str}".strip()

        with st.expander(expander_label, expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**📍 Location:** {c.get('location') or '—'}")
                st.markdown(f"**🏢 Company:** {c.get('company') or '—'}")
                st.markdown(f"**💼 Seniority:** {c.get('seniority') or '—'}")
                exp_display = str(c["experience_years"]) + "y" if c.get("experience_years") else "—"
                st.markdown(f"**⏱️ Experience:** {exp_display}")

            with col2:
                st.markdown(f"**📧 Email:** {c.get('email') or '—'}")
                st.markdown(f"**📱 Phone:** {c.get('phone') or '—'}")
                if c.get("profile_url"):
                    st.markdown(f"**🔗 Profile:** [View]({c['profile_url']})")
                else:
                    st.markdown("**🔗 Profile:** —")
                st.markdown(f"**📊 Activity:** {c.get('activity_score') or '—'}")
                st.markdown(skills_html, unsafe_allow_html=True)

            with col3:
                current_status = c.get("status", "new")
                if current_status not in status_options:
                    current_status = "new"
                current_index = status_options.index(current_status)
                new_status = st.selectbox(
                    "Update Status",
                    status_options,
                    index=current_index,
                    key=f"status_{c['id']}"
                )
                if st.button("Save", key=f"save_{c['id']}"):
                    update_candidate_status(c["id"], new_status)
                    st.success("Updated!")
                    st.rerun()

            if c.get("bio"):
                st.markdown(f"**Bio:** {c['bio'][:200]}")


# ── SEARCH PAGE ───────────────────────────────────────────────────────────────
elif page == "🔍 Search":
    st.markdown('<div class="section-head">🔍 Search Candidates</div>', unsafe_allow_html=True)

    search_q = st.text_input(
        "Search by name, skill, role, company, location...",
        placeholder="e.g. Python, Bangalore, React, Senior..."
    )

    if search_q:
        results = search_candidates(search_q)
        st.markdown(
            f"<div style='color:#4A6FA5;font-size:0.8rem;margin-bottom:12px;'>"
            f"{len(results)} results for '{search_q}'</div>",
            unsafe_allow_html=True
        )

        if not results:
            st.info("No candidates found. Try different keywords.")
        else:
            for c in results:
                skills_html = " ".join(
                    [f'<span class="skill-tag">{s}</span>' for s in (c["skills"] or [])[:6]]
                )
                src_cls  = "source-github" if c["source"] == "GitHub" else "source-web"
                src_icon = "🐙" if c["source"] == "GitHub" else "🌐"
                company_part  = " · " + c["company"] if c.get("company") else ""
                location_part = " · 📍 " + c["location"] if c.get("location") else ""
                profile_link  = (
                    '<br><a href="' + c["profile_url"] + '" target="_blank" '
                    'style="font-size:0.7rem;color:#00BFA5;text-decoration:none;'
                    'margin-top:4px;display:block;">View Profile →</a>'
                    if c.get("profile_url") else ""
                )

                st.markdown(f"""
                <div class="cand-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div class="cand-name">{c['name']}</div>
                            <div class="cand-role">
                                {c.get('role') or '—'}{company_part}{location_part}
                            </div>
                            <div>{skills_html}</div>
                        </div>
                        <div style="text-align:right;">
                            <span class="source-badge {src_cls}">{src_icon} {c['source']}</span>
                            {profile_link}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#2A4A6A;
                    border:1px dashed #1A2F4E;border-radius:12px;">
            <div style="font-size:2rem;margin-bottom:10px;">🔍</div>
            <div style="color:#4A6FA5;">Type to search your talent database</div>
        </div>
        """, unsafe_allow_html=True)


# ── ANALYTICS PAGE ────────────────────────────────────────────────────────────
elif page == "📈 Analytics":
    st.markdown('<div class="section-head">📈 Analytics</div>', unsafe_allow_html=True)

    all_cands = get_all_candidates(limit=1000)

    if not all_cands:
        st.info("No data yet. Source some candidates first.")
    else:
        df = pd.DataFrame(all_cands)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Candidates by Source**")
            st.bar_chart(df["source"].value_counts())

        with col2:
            st.markdown("**Candidates by Status**")
            st.bar_chart(df["status"].value_counts())

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Candidates by Seniority**")
            st.bar_chart(df["seniority"].value_counts())

        with col4:
            st.markdown("**Top Locations**")
            st.bar_chart(df["location"].value_counts().head(10))

        st.markdown("**📋 Full Database Export**")
        export_cols = ["name", "role", "company", "location", "email",
                       "phone", "seniority", "source", "status", "profile_url"]
        export_df = df[export_cols].copy()
        st.dataframe(export_df, use_container_width=True, hide_index=True)

        csv = export_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "talent_database.csv",
            "text/csv"
        )
