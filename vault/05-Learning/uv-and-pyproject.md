# uv and pyproject.toml

## What uv is

A fast (Rust-written) Python package manager from Astral. Replaces pip + virtualenv + pip-tools + sometimes Poetry in one tool. Pairs with `pyproject.toml`.

## Why we use it here

- Much faster installs than pip — matters when GH Actions runs daily
- Native `uv sync` + lockfile (`uv.lock`) for reproducible builds across machines
- No separate venv ceremony — `uv run python ...` handles it transparently

## Commands I'll use

```powershell
uv sync                                  # install everything from pyproject + lockfile into .venv/
uv add yfinance                          # add a dep, updates both pyproject.toml and uv.lock
uv remove premailer                      # remove a dep
uv run python -m buy_candidates.main     # run entrypoint inside the project venv
uv lock --upgrade                        # bump all deps to latest compatible versions
```

## This project's pyproject.toml

- `[project]` — name, version, deps
- `[build-system]` — using `hatchling` so the `src/buy_candidates/` layout is installable as a package
- `[tool.hatch.build.targets.wheel]` — tells hatch where the package source lives

## Why src layout

Putting code in `src/buy_candidates/` instead of `buy_candidates/` at repo root forces you to actually install the package to import it. This catches packaging mistakes early (e.g., a forgotten `__init__.py` or a typo in `[project].name`) instead of only failing in CI.

Trade-off: imports during development require `uv sync` once at the start. Worth it.
