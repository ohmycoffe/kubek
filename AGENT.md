# Agent instructions

## Project

`kubek` is a Python 3.11+ monorepo of `kubectl` plugins. See each package's README for details:
- `kubectl-portfwd/README.md` — interactive multi-service port-forwarding
- `kubectl-export-dotenv/README.md` — export env vars from Kubernetes Deployments and Argo WorkflowTemplates

Shared library lives in `kubek-shared/src/kubek/`.

## Rules

- Before modifying `pyproject.toml` (adding, removing, or changing any package), stop and confirm with the user.
- Use `asyncio` only. Do not use `threading`, `concurrent.futures`, or `multiprocessing`.
- Always use `rich` for all user-facing output which goes to stderr.
- Commit format: `type(scope): description`. Example: `fix(portfwd): handle kubectl crash without breaking live table`
- Do not drop a docstring when you edit a file. If a function lacks one, add it when you touch the function.
- Always add a docstring to any new test function that explains what it verifies and any important setup details.
- Do not add tests for questionnaire prompts.

## Setup

```bash
poetry install
```

Run `make help` to see all available commands (test, lint, format, bump, cluster, demo).

## Validation

```bash
make test    # run all tests
make lint    # ruff check + format check
```

### Test and lint targets
- **make test**: Runs `poetry run pytest` (collects tests from all packages)
- **make lint**: Runs `poetry run ruff check` and `poetry run ruff format --check` (lint without fixing)
