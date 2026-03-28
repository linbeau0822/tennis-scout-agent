```mermaid
sequenceDiagram
    participant User
    participant FE as "Frontend (React)"
    participant BE as "Backend (FastAPI)"
    participant DBPG as "DB (PostgreSQL)"
    participant StatsService
    participant LLM as "LLM (GPT-4o mini)"

    User->>FE: Select Player A vs Player B
    FE->>BE: POST /match-analysis (player_ids)

    BE->>DBPG: Fetch player data
    DBPG-->>BE: Raw player + match data

    BE->>StatsService: Compute derived stats
    StatsService-->>BE: Structured stats JSON

    BE->>LLM: Send structured stats + prompt
    LLM-->>BE: Scouting report + prediction

    BE-->>FE: JSON response
    FE-->>User: Render report UI
```