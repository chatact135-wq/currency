# MarketMind AI — Railway + Neon Ready

FastAPI starter project for an AI-style market signal dashboard.

## Upload to GitHub
Upload the CONTENTS of this ZIP directly to the GitHub repository root. The repository root must show:

```text
app/
requirements.txt
Procfile
railway.json
README.md
.env.example
```

## Railway
Build command:
```bash
pip install -r requirements.txt
```
Start command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Variables
Add these in Railway Variables:
```env
DATABASE_URL=your_neon_connection_string
SECRET_KEY=any-random-secret
```

## Test after deploy
- `/`
- `/health`
- `/dashboard`
- `/api/signals/EURUSD`
- `/api/signals`
