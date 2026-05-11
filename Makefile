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

lint: ## Check code style and lint errors
	poetry run ruff check
	poetry run ruff format --check

format: ## Format code
	poetry run ruff format


bump: ## Bump version (v=patch|minor|major)
	@test -n "$(v)" || (echo "Usage: make bump v=patch|minor|major" && exit 1)
	scripts/bump_version.sh $(v)

cluster: ## Create local Kind cluster
	scripts/run-local-cluster.sh kubext-pfwd kubext-envx

demo: ## Regenerate VHS demo GIFs
	vhs kubext-pfwd/docs/tapes/demo.tape
	vhs kubext-envx/docs/tapes/demo.tape
