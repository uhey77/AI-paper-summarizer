.PHONY: lint
lint: ## run tests with poetry (isort, black, pflake8, mypy)
	poetry run black .
	poetry run isort .
	poetry run flake8 . --exclude=.venv,.git,__pycache__,.mypy_cache --ignore=E203,E501,W503,E704
	poetry run mypy . --explicit-package-bases


.PHONY: test
test: ## run tests with poetry
	poetry run pytest .