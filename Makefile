.PHONY: install run test lint format migrate
install:
	pip install -r requirements-dev.txt
run:
	uvicorn app.main:app --reload
test:
	pytest --cov=app --cov-report=term-missing
lint:
	ruff check . && mypy app
format:
	ruff format . && ruff check --fix .
migrate:
	alembic revision --autogenerate -m "$(m)" && alembic upgrade head
