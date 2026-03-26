# Tennis Scouting Agent - Copilot Plan

## 1. High-Level Architecture

```
[React + Tailwind Frontend]
            |
            v
[FastAPI Backend API]
            |
            v
[Postgres Database]
            |
            v
[OpenAI GPT-4 Integration]
```

**Flow:**
1. User enters player name(s) on frontend.
2. Frontend calls FastAPI endpoint (`/player/<name>`).
3. Backend queries Postgres for match history and stats.
4. Backend constructs a prompt and calls GPT-4 API.
5. GPT-4 returns a scouting report.
6. Backend sends structured stats + report to frontend.
7. Frontend displays stats (tables/charts) and AI report.

---

## 2. Folder Structure

```
tennis-scout-agent/
│
├─ frontend/
│   ├─ src/
│   │   ├─ App.jsx              # main app
│   │   ├─ components/
│   │   │   ├─ PlayerInput.jsx
│   │   │   ├─ StatsTable.jsx
│   │   │   └─ ReportDisplay.jsx
│   │   └─ utils.js             # fetch helpers
│   └─ package.json
│
├─ backend/
│   ├─ app/
│   │   ├─ main.py              # FastAPI app
│   │   ├─ routes/
│   │   │   └─ player_routes.py
│   │   ├─ services/
│   │   │   ├─ data_service.py  # Postgres queries
│   │   │   └─ llm_service.py   # GPT-4 prompt & API calls
│   │   ├─ models.py            # SQLAlchemy models
│   │   └─ config.py            # env vars, DB connection
│   └─ requirements.txt
│
├─ data/
│   ├─ seed_data.py             # populate Postgres with sample players & matches
│
├─ .env                        # OPENAI_API_KEY, POSTGRES_URL
└─ README.md
```

---

## 3. Tech Stack Justification (Resume Signal)

| Layer      | Tech           | Resume Value |
|-----------|----------------|--------------|
| Frontend  | React + Tailwind | Modern JS framework, CSS utility, polished UI |
| Backend   | FastAPI        | Python, async API, clean architecture |
| Database  | Postgres       | SQL skills, relational modeling |
| AI Layer  | OpenAI GPT-4   | LLM integration, prompt engineering |
| Deployment| Vercel / Heroku| Full-stack deployment |

---

## 4. Key Features for MVP

**Backend**
- `/player/<name>`: returns structured stats + GPT-4 report  
- `/compare` (optional): returns comparative report for multiple players  

**Frontend**
- Player search input  
- Display stats table: win %, surface trends, recent form  
- Display AI scouting report  
- Optional: trend charts (Recharts / Chart.js)  

**Database**
- `players`: id, name, ranking, country  
- `matches`: player_id, opponent, surface, score, stats, date  

**LLM**
- GPT-4 prompt template with structured stats  
- Returns concise scouting report  
- Optional: multi-player comparison reasoning  

---

## 5. Next Steps for Copilot

1. Create backend skeleton with FastAPI routes (`/player/<name>`, `/compare`).
2. Create SQLAlchemy models for `players` and `matches`.
3. Write `data_service.py` with DB query placeholders.
4. Write `llm_service.py` with GPT-4 call stub and prompt template.
5. Create React + Tailwind frontend skeleton:
   - `PlayerInput.jsx`
   - `StatsTable.jsx`
   - `ReportDisplay.jsx`
6. Write `seed_data.py` to populate Postgres with sample players & matches.
7. Set up `.env` for API keys and DB connection.
8. Connect frontend to backend using Axios / Fetch.
9. Test MVP end-to-end with sample players.
10. Optional enhancements: multi-player comparison, charts, PDF export, caching, deployment.

