# FlexBind-DevSafe

**Ensemble-aware binder design with developability gating.**

Upload a target structure and a binder template PDB.  The pipeline generates binding-competent conformational ensembles, designs robust sequences across multiple states, and gates designs for aggregation / self-association risk — all using open-source tools, no proprietary licenses.

---

## Features

| Step | What it does |
|------|-------------|
| **A. Preprocess** | Clean PDBs, auto-detect interface residues or CDR loops (antibody Fv) |
| **B. Ensemble** | Backbone perturbations + harmonic relaxation → RMSD clustering → representative states |
| **C. Score** | Contact score, clash penalty, H-bond proxy, SASA burial across every ensemble state |
| **D. Design** | Beam-search sequence optimiser with multi-state objective, glycosylation filter |
| **E. Developability** | Hydrophobic patches, charge/pI, β-sheet propensity, self-dock risk → composite 0–100 |
| **F. Output** | Ranked CSV, FASTA, PDB ensemble, JSON report, downloadable ZIP |

---

## Quick Start (Local)

### Prerequisites

- Docker + Docker Compose (v2)

### One-command launch

```bash
# Clone and enter the repo
git clone https://github.com/your-org/flexbind-devsafe.git
cd flexbind-devsafe

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Build and start everything
docker compose up --build
```

The UI is at **http://localhost:5173**.  
The API docs are at **http://localhost:8000/docs**.  
The health endpoint is at **http://localhost:8000/health**.

### Without Docker

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Redis (must be running on localhost:6379)
# On macOS: brew services start redis
# On Ubuntu: sudo systemctl start redis

# Terminal 1: Celery worker
celery -A app.worker worker --loglevel=info --concurrency=2

# Terminal 2: API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Demo Script

### 1. Generate test PDB files

The test fixtures include minimal synthetic PDBs.  To extract them for a quick smoke test:

```bash
cd backend
python -c "
from tests.conftest import MINI_TARGET_PDB, MINI_BINDER_PDB
with open('test_target.pdb', 'w') as f: f.write(MINI_TARGET_PDB)
with open('test_binder.pdb', 'w') as f: f.write(MINI_BINDER_PDB)
print('Created test_target.pdb and test_binder.pdb')
"
```

### 2. Submit via the UI

1. Open **http://localhost:5173**.
2. Upload `test_target.pdb` as the Target PDB.
3. Upload `test_binder.pdb` as the Binder PDB.
4. Select **Other binder**, **Fast** mode, seed **42**.
5. Click **Run Design Pipeline**.
6. Navigate to the **Jobs** tab to watch progress in real time.

### 3. Submit via the API

```bash
curl -X POST http://localhost:8000/api/jobs \
  -F target_pdb=@test_target.pdb \
  -F binder_pdb=@test_binder.pdb \
  -F binder_type=other \
  -F mode=fast \
  -F seed=42

# Poll status:
curl http://localhost:8000/api/jobs/<job_id>

# Download results:
curl -o results.zip http://localhost:8000/api/jobs/<job_id>/download
```

### 4. Run tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Deploy on Render

### Backend (Docker Web Service)

1. Create a **Web Service** on Render.
2. Set the **Root Directory** to `backend`.
3. Set **Environment** to **Docker**.
4. Add environment variables:
   - `CELERY_BROKER_URL` — Use a Render Redis instance URL (e.g. `redis://red-xxx:6379`)
   - `CELERY_RESULT_BACKEND` — Same as above
   - `JOBS_DIR` — `/app/jobs` (default)
   - `CORS_ORIGINS` — Your frontend URL (e.g. `https://flexbind-devsafe.onrender.com`)
5. Set the **Start Command** to:
   ```
   sh -c "celery -A app.worker worker --loglevel=info --concurrency=1 & uvicorn app.main:app --host 0.0.0.0 --port $PORT"
   ```
6. Attach a **Render Disk** mounted at `/app/jobs` for persistent job storage.

### Redis

1. Create a **Redis** instance on Render.
2. Copy its Internal URL into the backend env vars above.

### Frontend (Static Site)

1. Create a **Static Site** on Render.
2. Set the **Root Directory** to `frontend`.
3. Set the **Build Command** to `npm install && npm run build`.
4. Set the **Publish Directory** to `dist`.
5. Add environment variable:
   - `VITE_API_URL` — Your backend URL (e.g. `https://flexbind-api.onrender.com`)
6. Add a rewrite rule: `/* → /index.html` (for SPA routing).

---

## Project Structure

```
flexbind-devsafe/
├── docker-compose.yml          # Local orchestration
├── .github/workflows/ci.yml    # GitHub Actions CI
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # Env-based configuration
│   │   ├── models.py           # Pydantic schemas
│   │   ├── utils.py            # Job persistence helpers
│   │   ├── worker.py           # Celery worker + task
│   │   ├── routes/
│   │   │   ├── health.py       # /health endpoint
│   │   │   └── jobs.py         # /api/jobs/* CRUD + SSE + download
│   │   └── pipeline/
│   │       ├── preprocess.py   # Step A — PDB cleaning
│   │       ├── ensemble.py     # Step B — Conformational ensemble
│   │       ├── scoring.py      # Step C — Interface scoring
│   │       ├── sequence_design.py # Step D — Sequence design
│   │       ├── developability.py  # Step E — Developability gates
│   │       └── runner.py       # Step F — Pipeline orchestrator
│   └── tests/
│       ├── conftest.py         # Fixtures with mini PDBs
│       ├── test_preprocess.py
│       └── test_scoring.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx             # Hash-based router
        ├── api.ts              # Backend API client
        ├── types.ts            # TypeScript interfaces
        ├── index.css           # Tailwind + custom styles
        ├── components/
        │   ├── Layout.tsx
        │   ├── NewJobForm.tsx
        │   ├── JobsList.tsx
        │   ├── JobDetail.tsx
        │   └── ScoreChart.tsx
        └── pages/
            ├── Home.tsx
            └── Jobs.tsx
```

---

## Common Failure Modes & Fixes

| Problem | Fix |
|---------|-----|
| `Connection refused` on Redis | Make sure Redis is running. Docker Compose handles this; without Docker, run `redis-server` first. |
| Celery task stays `PENDING` | The worker might not be running. Check `celery -A app.worker worker` is started. |
| Frontend proxy errors in dev | Vite proxies `/api` to `http://backend:8000` inside Docker. Outside Docker, change `vite.config.ts` target to `http://localhost:8000`. |
| File upload rejected | PDB files must end in `.pdb` and be under 50 MB. |
| `No flexible residues detected` | The auto-detect cutoff (8 Å) may miss residues if structures are far apart. Increase the cutoff or specify residues manually. |
| Import errors for OpenMM | OpenMM is optional. The pipeline uses geometric perturbations as a fallback. |
| Tests fail with import error | Run tests from the `backend/` directory so `app` is on the Python path. |

---

## License

MIT
