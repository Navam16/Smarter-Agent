"""
╔══════════════════════════════════════════════════════════════╗
║         AI TALENT SOURCING AGENT — MVP DASHBOARD             ║
║         GitHub + Web Search · Groq AI · SQLite DB            ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import os
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
# 🔑  KEY HELPERS (Secured)
# ─────────────────────────────────────────────────────────────────────────────
def get_key(name: str) -> str:
    """Tries to get keys securely from secrets first, then .env, then UI."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    
    env_key = os.getenv(name)
    if env_key:
        return env_key
        
    return st.session_state.get(f"key_{name}", "")

# ─────────────────────────────────────────────────────────────────────────────
# 🎨  PAGE CONFIG & SOOTHING BLUISH CSS
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

/* Base Soothing Blue App Background */
.stApp {
    background: #0B1121 !important; 
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    border-right: 1px solid #334155;
}
section[data-testid="stSidebar"] * { color: #94A3B8 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #F8FAFC !important;
    font-family: 'Syne', sans-serif !important;
}

/* Inputs & Select Boxes */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
}

/* Top Dashboard Header */
.dash-header {
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    border: 1px solid #334155;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.dash-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 2.2rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -1px;
    margin: 0;
    line-height: 1.1;
}
.dash-title span { color: #38BDF8; } /* Bright Blue Accent */
.dash-sub { font-size: 0.95rem; color: #94A3B8; margin-top: 6px; }

/* Horizontal Menu Navigation Styling */
div[role="radiogroup"] {
    display: flex;
    justify-content: flex-start;
    gap: 15px;
    background: #1E293B;
    padding: 8px;
    border-radius: 12px;
    border: 1px solid #334155;
    margin-bottom: 20px;
}
div[role="radiogroup"] label {
    background: transparent !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    border: none !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
}
div[role="radiogroup"] label:hover {
    background: #334155 !important;
    color: #FFFFFF !important;
}
div[role="radiogroup"] label[data-checked="true"] {
    background: #0284C7 !important; /* Ocean Blue */
    color: #FFFFFF !important;
}
div[role="radiogroup"] label [data-testid="stRadioAction"] {
    display: none !important; /* Hides the native radio circle */
}

/* Cards */
.stat-card, .cand-card {
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 20px 24px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.cand-card:hover {
    border-color: #38BDF855;
    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.1);
}
.stat-number { font-family: 'Syne', sans-serif; font-size: 2.4rem; font-weight: 800; color: #38BDF8; }
.stat-label { font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; }

/* Buttons & Tags */
.skill-tag {
    background: #0F172A; color: #38BDF8; font-size: 0.7rem; font-weight: 600;
    padding: 4px 10px; border-radius: 20px; margin: 2px; border: 1px solid #334155;
}
.stButton > button {
    background: linear-gradient(135deg, #0284C7, #0369A1) !important;
    color: white !important; font-weight: 700 !important; border-radius: 8px !important;
    padding: 10px 20px !important; border: none !important;
}

.log-box { background: #0F172A; border: 1px solid #334155; border-radius: 10px; padding: 16px; }
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
# ⚙️  SIDEBAR (Cleaned up, Keys secured)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Sourcing Engine")
    st.markdown("---")
    
    role_input = st.text_input("Job Role / Skills", placeholder="Python Developer", value="Python Developer")
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
    
    # Secure API Keys Section
    with st.expander("🔑 Advanced: API Settings", expanded=False):
        groq_key = get_key("GROQ_API_KEY")
        gh_key = get_key("GITHUB_TOKEN")
        serper_key = get_key("SERPER_API_KEY")
        
        if groq_key and gh_key:
            st.success("✅ Keys loaded securely from secrets/env.")
        
        if not groq_key:
            st.text_input("Groq API Key", type="password", key="key_GROQ_API_KEY")
        if not gh_key:
            st.text_input("GitHub Token", type="password", key="key_GITHUB_TOKEN")
        if not serper_key:
            st.text_input("Serper API Key", type="password", key="key_SERPER_API_KEY")


# ─────────────────────────────────────────────────────────────────────────────
# 📊  TOP HEADER & NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────
stats = get_stats()
now_str = datetime.now().strftime("%d %b %Y · %H:%M")

st.markdown(f"""
<div class="dash-header">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div class="dash-title">Talent<span>AI</span> Sourcing</div>
            <div class="dash-sub">AI-powered candidate discovery · {now_str}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;color:#38BDF8;">{stats['total']:,}</div>
            <div style="font-size:0.75rem;color:#94A3B8;letter-spacing:1px;text-transform:uppercase;">Total Candidates</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Menu (Website Style)
page = st.radio(
    "Navigation", 
    ["📊 Dashboard", "👥 Candidates", "🔍 Search", "📈 Analytics"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ▶️  RUN SOURCING LOGIC
# ─────────────────────────────────────────────────────────────────────────────
if run_btn:
    if not groq_key:
        st.error("❌ Groq API key required. Check the Advanced sidebar tab.")
    elif not role_input:
        st.error("❌ Enter a job role to search for.")
    else:
        st.session_state.is_sourcing = True
        st.session_state.sourcing_logs = []
        log_placeholder = st.empty()
        progress_bar = st.progress(0, text="Starting sourcing agent...")

        def add_log(msg: str):
            ts = datetime.now().strftime("%H:%M:%S")
            cls = "log-success" if "✅" in msg else ("log-warning" if "⚠️" in msg else "log-info")
            st.session_state.sourcing_logs.append(f'<div class="log-entry {cls}" style="color:white;">[{ts}] {msg}</div>')
            logs_html = "\n".join(st.session_state.sourcing_logs[-20:])
            log_placeholder.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)

        total_new = 0
        skills = [s.strip() for s in role_input.split(",")]

        if "GitHub" in platforms:
            progress_bar.progress(0.1, text="🐙 Sourcing from GitHub...")
            os.environ["GITHUB_TOKEN"] = gh_key or ""
            os.environ["GROQ_API_KEY"] = groq_key
            result = run_github_sourcing(skills=skills, location=location_input, groq_key=groq_key, progress_callback=add_log)
            total_new += result["new"]
            progress_bar.progress(0.5, text="GitHub done...")

        if any(p in platforms for p in ["LinkedIn (via Google)", "Stack Overflow"]):
            if not serper_key:
                add_log("⚠️ Serper API key missing — web search skipped")
            else:
                progress_bar.progress(0.6, text="🌐 Sourcing from Web...")
                plat_map = {"LinkedIn (via Google)": "linkedin", "Stack Overflow": "stackoverflow"}
                active_platforms = [plat_map[p] for p in platforms if p in plat_map]
                os.environ["SERPER_API_KEY"] = serper_key
                result = run_web_sourcing(role=role_input, location=location_input, groq_key=groq_key, serper_key=serper_key, platforms=active_platforms, progress_callback=add_log)
                total_new += result["new"]

        progress_bar.progress(1.0, text="✅ Sourcing complete!")
        st.session_state.is_sourcing = False
        st.session_state.last_run = datetime.now().strftime("%H:%M:%S")
        time.sleep(1)
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 📄  PAGES CONTENT
# ─────────────────────────────────────────────────────────────────────────────

if page == "📊 Dashboard":
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    stat_data = [
        (c1, "🆕", stats["today"], "Added Today"), (c2, "✨", stats["new"], "New"),
        (c3, "📧", stats["contacted"], "Contacted"), (c4, "🐙", stats["github"], "From GitHub"),
        (c5, "🌐", stats["web"], "From Web"), (c6, "📊", stats["total"], "Total"),
    ]
    for col, icon, val, label in stat_data:
        with col:
            st.markdown(f"""
            <div class="stat-card" style="text-align:center;">
                <span style="font-size: 1.4rem;">{icon}</span>
                <div class="stat-number">{val:,}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div style="font-family:\'Syne\'; font-size: 1.2rem; color: #F8FAFC; margin-bottom: 15px;">🕒 Recent Candidates</div>', unsafe_allow_html=True)
        recent = get_all_candidates(limit=8)
        if not recent:
            st.info("No candidates yet. Configure a role in the sidebar and click 'Source Now'!")
        else:
            for c in recent:
                skills_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in (c["skills"] or [])[:6]])
                st.markdown(f"""
                <div class="cand-card">
                    <div style="font-family:'Syne'; font-size:1.1rem; font-weight:700; color:#F8FAFC;">{c['name']}</div>
                    <div style="color:#94A3B8; font-size:0.9rem; margin-bottom: 10px;">{c['role'] or '—'} · {c.get('company') or '—'} · 📍 {c.get('location') or '—'}</div>
                    <div>{skills_html}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div style="font-family:\'Syne\'; font-size: 1.2rem; color: #F8FAFC; margin-bottom: 15px;">📋 Sourcing Log</div>', unsafe_allow_html=True)
        if st.session_state.sourcing_logs:
            logs_html = "\n".join(st.session_state.sourcing_logs[-30:])
            st.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)
        else:
            st.info("Logs will appear here when sourcing runs.")

elif page == "👥 Candidates":
    st.markdown("### 👥 All Candidates")
    candidates = get_all_candidates(limit=200)
    for c in candidates:
        with st.expander(f"{c['name']} — {c.get('role', '')}"):
            st.write(f"**Location:** {c.get('location')} | **Company:** {c.get('company')}")
            st.write(f"**Skills:** {', '.join(c.get('skills', []))}")
            if c.get("profile_url"): st.write(f"[View Profile]({c['profile_url']})")

elif page == "🔍 Search":
    st.markdown("### 🔍 Search Candidates")
    search_q = st.text_input("Search by name, skill, role, location...")
    if search_q:
        results = search_candidates(search_q)
        for c in results:
            st.write(f"**{c['name']}** - {c.get('role')} at {c.get('company')}")

elif page == "📈 Analytics":
    st.markdown("### 📈 Analytics")
    all_cands = get_all_candidates(limit=1000)
    if all_cands:
        df = pd.DataFrame(all_cands)
        st.dataframe(df, use_container_width=True)
