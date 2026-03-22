# 🎯 TalentAI — AI Talent Sourcing Dashboard

AI-powered candidate sourcing from GitHub and the open web.
Automatically discovers, extracts, and stores candidate profiles with zero duplicates.

---

## 📁 Project Structure

```
talentai_mvp/
├── app.py                    ← Main Streamlit dashboard
├── agents/
│   ├── github_agent.py       ← GitHub talent sourcing
│   └── search_agent.py       ← Web/LinkedIn sourcing
├── database/
│   └── db.py                 ← SQLite + deduplication
├── requirements.txt
├── .env.example              ← Copy to .env
└── .gitignore
```

---

## 🔑 API Keys

| Key | Service | Cost | Get It |
|---|---|---|---|
| `GROQ_API_KEY` | LLM extraction | **Free** | [console.groq.com](https://console.groq.com) |
| `GITHUB_TOKEN` | GitHub sourcing | **Free** | [github.com/settings/tokens](https://github.com/settings/tokens) |
| `SERPER_API_KEY` | Web/LinkedIn search | Free tier / $50/mo | [serper.dev](https://serper.dev) |

**Minimum to run:** Only `GROQ_API_KEY` + `GITHUB_TOKEN` needed.
`SERPER_API_KEY` is optional (enables LinkedIn/web sourcing).

---

## 🚀 Local Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/talentai-mvp.git
cd talentai-mvp

# 2. Install
pip install -r requirements.txt

# 3. Add keys
cp .env.example .env
# Edit .env with your keys

# 4. Run
streamlit run app.py
```

---

## ☁️ Streamlit Cloud Deployment

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from GitHub repo
4. Settings → Secrets → Add:
```toml
GROQ_API_KEY = "gsk_..."
GITHUB_TOKEN = "ghp_..."
SERPER_API_KEY = "..."
```

---

## 🤖 How It Works

```
User enters role + location
        ↓
GitHub Agent searches developers
        ↓
Web Agent searches LinkedIn/web via Google
        ↓
Groq AI extracts structured profiles
        ↓
Deduplication (no duplicates ever)
        ↓
SQLite database stores candidates
        ↓
Dashboard shows results + analytics
```

---

## 📊 Dashboard Pages

- **Dashboard** — Recent candidates + sourcing logs
- **Candidates** — Full list with filters + status management
- **Search** — Full-text search across database
- **Analytics** — Charts by source, seniority, location + CSV export
