# Game On Tabletop

Full-stack hello-world boilerplate proving out the entire stack end-to-end.

| Layer    | Technology                                    |
| -------- | --------------------------------------------- |
| Frontend | Vue 3 + Vite + Tailwind CSS                   |
| Backend  | FastAPI (Python 3.12, uv)                     |
| Database | PostgreSQL (Docker locally, Supabase in prod) |
| Hosting  | Vercel (frontend + backend serverless)        |
| CI/CD    | GitHub Actions                                |

---

## Local development

### Prerequisites

- [Docker + Docker Compose](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Node 20+](https://nodejs.org/)

### Start everything with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

| Service     | URL                   |
| ----------- | --------------------- |
| Frontend    | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Postgres    | localhost:5432        |

The frontend Vite dev server proxies `/api/*` requests to the backend, so the
Vue app fetches `/api/` and receives `{"message": "Hello World"}` from FastAPI.

### Run migrations (Docker)

```bash
docker compose exec backend uv run alembic upgrade head
```

### Run without Docker

**Backend:**

```bash
cd backend
uv sync --dev
cp .env.example .env          # edit DATABASE_URL to point at your local Postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Running tests

**Backend:**

```bash
cd backend
uv run pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

**Linting:**

```bash
# Python
cd backend && uv run ruff check .

# JavaScript
cd frontend && npm run lint
```

---

## Deployment

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for the full step-by-step guide covering:

- Supabase project setup and connection strings
- Vercel backend (Python serverless) and frontend (static) setup
- Running Alembic migrations against Supabase
- GitHub Actions secrets configuration
- End-to-end verification and troubleshooting

---

## Project structure

```
.
├── .github/workflows/
│   ├── pr-checks.yml      # lint + test on every PR
│   └── deploy.yml         # deploy to Vercel on merge to main
├── backend/
│   ├── alembic/           # database migrations
│   ├── api/
│   │   └── index.py       # Vercel serverless entry point
│   ├── app/
│   │   ├── config.py      # pydantic-settings (reads .env)
│   │   ├── database.py    # SQLAlchemy async engine + session
│   │   ├── main.py        # FastAPI app (GET /, GET /health)
│   │   └── models/
│   │       └── message.py # example Message table
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml     # uv-managed dependencies
│   ├── requirements.txt   # for Vercel Python runtime
│   └── vercel.json
├── frontend/
│   ├── src/
│   │   ├── App.vue        # fetches from backend, displays response
│   │   └── main.js
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js     # dev proxy: /api/* → backend
├── docker-compose.yml
└── README.md
```

## Environment variables reference

| Variable            | Used by                  | Description                                     |
| ------------------- | ------------------------ | ----------------------------------------------- |
| `DATABASE_URL`      | Backend                  | Async Postgres URL (`postgresql+asyncpg://...`) |
| `BACKEND_URL`       | Vite dev server (Docker) | Internal Docker hostname for the proxy          |
| `VITE_API_BASE_URL` | Frontend (production)    | Backend Vercel URL; leave empty in dev          |
