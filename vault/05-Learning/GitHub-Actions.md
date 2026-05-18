# GitHub Actions

## What it is

GitHub's hosted CI/CD service. Workflows live in `.github/workflows/*.yml` and run on triggers (push, PR, schedule, manual).

## In this project

The single workflow `daily.yml` runs daily at 21:30 UTC (= 22:30 CET / 23:30 CEST):

1. Checkout repo
2. Install `uv`
3. `uv sync` to install deps
4. Run `python -m buy_candidates.main` with secrets injected as env vars
5. Commit + push the regenerated `docs/` and new `archive/YYYY-MM-DD.json`

## Cron gotchas

- Cron is in **UTC** — no timezone support. Mentally translate to Berlin time and accept DST drift.
- Scheduled runs can be **delayed by up to ~15 min during peak hours** (the GH cron queue gets busy). Don't rely on second-precise timing.
- The `schedule:` trigger only runs on the **default branch**.

## Permissions

Default `GITHUB_TOKEN` is read-only for content. To commit/push from a workflow:

```yaml
permissions:
  contents: write
```

Then configure git user inside the workflow before pushing (see `.github/workflows/daily.yml`).

## Secrets

Settings → Secrets and variables → Actions. Available in workflows as `${{ secrets.NAME }}`. They're encrypted at rest and never echoed in logs (GH masks them in output). Don't `echo $SECRET` to log — even masked, it's a footgun.

## Free tier limits

- **2,000 minutes/month** for private repos, unlimited for public repos
- This project: ~5 min/day × 30 = 150 min/month — well under the cap even on private

## Useful commands (via `gh` CLI)

```powershell
gh workflow run daily.yml         # trigger manually
gh run list --workflow=daily.yml  # recent runs
gh run watch                      # follow latest run live
gh run view --log                 # logs of most recent run
```
