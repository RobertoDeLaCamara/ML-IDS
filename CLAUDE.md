# ML-IDS

Full-stack ML intrusion detection system. FastAPI + PostgreSQL + WebSocket dashboard. CICFlowMeter features, scikit-learn models, MLflow tracking, async SQLAlchemy 2.0.

## Key Commands

```bash
docker-compose up -d
docker-compose exec ml-ids python src/inference_server/init_db.py

pytest tests/

# Migrations
alembic upgrade head   # alembic.ini in project root
```

## Key API Endpoints

- `POST /predict`
- `GET /api/alerts`
- `WS /api/dashboard/live`
- `GET /health`

## CRITICAL: Dependency Management

**Never bump individual packages.** The lock file is fragile. When updating deps, regenerate the entire `requirements.txt` from a clean venv:

```bash
python -m venv /tmp/ml-ids-venv
/tmp/ml-ids-venv/bin/pip install -r requirements.in  # or base deps
/tmp/ml-ids-venv/bin/pip freeze > requirements.txt
```

**Known breakages from manual bumps:**
- `scapy==2.6.2` does not exist on PyPI
- `fastapi 0.115.x` requires `starlette<0.47` (conflict with other deps)
- MLflow: stay on 2.x (3.x is breaking). 3 Dependabot alerts for mlflow are dismissed.

**Current pinned versions:** fastapi 0.135.1, starlette 0.52.1, aiohttp 3.13.3, mlflow 2.22.4, scapy 2.7.0, pillow 12.1.1

## Remotes

- `origin` → Gitea (192.168.1.62:9090)
- `github` → GitHub (RobertoDeLaCamara/ML-IDS)
- License: AGPL v3

## Data

`Data.csv` (187MB CIC-IDS-2017 dataset) was removed from git history and added to `.gitignore`.
