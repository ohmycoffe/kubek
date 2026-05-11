# Agent instructions

## Project

`kubepf` is a Python 3.11+ CLI that wraps `kubectl port-forward`. Users pick Kubernetes services
via fuzzy search; the tool forwards multiple service ports simultaneously and shows a live status table.

Key modules:
- `src/kubepf/cli/main.py` — Typer CLI entry point
- `src/kubepf/cli/port_forward.py` — async port-forward orchestration
- `src/kubepf/kube.py` — kubectl subprocess wrappers
- `src/kubepf/config.py` — TOML + env-var config loading

## Rules

- before modifying `pyproject.toml` (adding, removing, or changing any package),
stop and confirm with the user.
- use `asyncio` only. Do not use `threading`, `concurrent.futures`, or
`multiprocessing`. Before modifying `src/kubepf/cli/port_forward.py`, read `docs/async.md`.
- Always use `rich` for all user-facing output. Do not call `print()` directly.
- Commit format: `type(scope): description`
Example: `fix(port-forward): handle kubectl crash without breaking live table`
- Always put design docs and ADRs in `docs/`. Add a link to them here.
- Do not drop docstring when you edit a file. If a function doesn't have a docstring, add one when you edit it.
- Always add a docstring to any new test function you create. The docstring should explain what the test is verifying and any important details about the test setup or expected behavior.

## Setup

```bash
poetry install
poetry run kubepf --help
```

## Configuration

Resolution order (first match wins): CLI flag → env var → TOML file → built-in default.

Default config path: `~/.config/kpf/config.toml`
Accepts env vars

See `README.md` for the full TOML schema.

## Validation

Config parsing has unit tests in `tests/`. Run with:

```bash
poetry run pytest
```

For CLI/cluster behaviour, tell the user what to run — do not assume access to a cluster.
