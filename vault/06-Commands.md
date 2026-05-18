# Commands cheatsheet

## Project setup (one-time)

```powershell
cd Documents\daily-buy-candidates
uv sync                           # creates .venv/ and installs deps
Copy-Item .env.example .env       # then edit .env with real values
```

## Run the pipeline locally

```powershell
uv run python -m buy_candidates.main
```

## Preview the dashboard

Double-click `docs/index.html` to open in your browser.

After wiring `render.py`, a quick sample preview will be:
```powershell
uv run python -c "from buy_candidates.render import render_sample; render_sample()"
```

## Git

```powershell
git status
git add docs/ archive/
git commit -m "Daily update"
git push
```

## GitHub Actions (via `gh` CLI)

```powershell
gh workflow run daily.yml          # trigger manually
gh run list --workflow=daily.yml   # see recent runs
gh run watch                       # follow latest run live
gh run view --log                  # logs of most recent run
```

## Obsidian

Open this vault: **File → Open vault → `Documents\daily-buy-candidates\vault\`**

Daily log convention: create `vault/04-Daily-log/YYYY-MM-DD.md` per session.

## Cache management

```powershell
# Wipe yfinance cache (forces fresh pull next run)
Remove-Item -Recurse cache\*.parquet

# Wipe Claude narrative cache (forces re-narration on next pick re-entry)
Remove-Item -Recurse cache\narratives\*.json
```
