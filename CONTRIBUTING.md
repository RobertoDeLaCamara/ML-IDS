# Contributing to ML-IDS

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/ML-IDS.git
   cd ML-IDS
   ```
3. Set up the development environment:
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # if applicable
   ```
4. Start the infrastructure:
   ```bash
   docker-compose up -d
   docker-compose exec ml-ids python src/inference_server/init_db.py
   ```

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature` or `git checkout -b fix/issue-description`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Commit with a clear message: `git commit -m "feat: add new feature"`
5. Push and open a Pull Request

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

For integration tests that require PostgreSQL, ensure Docker Compose services are running.

All new code should include tests. Aim to maintain or improve coverage.

## Database Migrations

This project uses Alembic for database migrations:
```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

Always create a migration when modifying SQLAlchemy models.

## Key API Endpoints

- `POST /predict` — submit network flow for classification
- `GET /api/alerts` — retrieve detected alerts
- `WS /api/dashboard/live` — real-time WebSocket dashboard
- `GET /health` — service health check

## Code Style

- Follow PEP 8
- Use async/await consistently for I/O-bound operations (SQLAlchemy 2.0 async)
- Add docstrings to public functions and API endpoints
- Use type hints for all function signatures
- Use clear, descriptive variable names

## Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` adding or updating tests
- `refactor:` code restructuring

## Reporting Issues

- Use the issue templates (Bug Report or Feature Request)
- Include steps to reproduce for bugs
- Mention Docker and Python versions when relevant
- Check existing issues before creating a new one

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to learn and build.
