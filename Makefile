.DEFAULT_GOAL := help
.PHONY: test lint format check bump cluster demo help

help: ## Show available commands
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sed 's/^\([a-zA-Z_-]*\):.*## \(.*\)/  \1                \2/' | \
		sed 's/^\(.\{16\}\) *\(.\)/\1\2/'
	@echo ""

test: ## Run all tests
	poetry run pytest

format: ## Format code and fix lint errors with Ruff
	poetry run ruff format
	poetry run ruff check --fix

lint: ## Lint and format check without fixing (mirrors CI)
	poetry run ruff check
	poetry run ruff format --check


bump: ## Bump version (v=patch|minor|major)
	@test -n "$(v)" || (echo "Usage: make bump v=patch|minor|major" && exit 1)
	scripts/bump_version.sh $(v)

cluster: ## Create local Kind cluster
	scripts/run-local-cluster.sh kubectl-portfwd kubectl-envx

demo: ## Regenerate VHS demo GIFs
	vhs kubectl-portfwd/docs/tapes/demo.tape
	vhs kubectl-envx/docs/tapes/demo.tape
