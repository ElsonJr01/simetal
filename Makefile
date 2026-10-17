.PHONY: install run admin test lint format migrate
install:
	pip install -r requirements-dev.txt
run:
	python -m uvicorn app.main:app --reload
admin:
	python -m app.cli create-admin --email $(email)
test:
	pytest --cov=app --cov-report=term-missing
lint:
	ruff check . && mypy app
format:
	ruff format . && ruff check --fix .
migrate:
	alembic revision --autogenerate -m "$(m)" && alembic upgrade head
