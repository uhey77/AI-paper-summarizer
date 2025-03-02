.PHONY: lint
lint: ## run lint with poetry (ruff, mypy)
	poetry run ruff format .
	poetry run ruff check --fix .
	poetry run mypy . --explicit-package-bases


.PHONY: test
test: ## run tests with poetry
	PYTHONPATH=. poetry run pytest tests/