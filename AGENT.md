# Agent Instructions for ilegalflow-data

This document provides everything an AI agent needs to continue development on the USPTO trademark data pipeline.

## Quick Start

```bash
# 1. Activate environment
cd ~/Projects/ilegalflow-data
source .venv/bin/activate

# 2. Verify setup
python scripts/download.py --list  # Should show USPTO files
docker ps | grep manticore         # Should show running container

# 3. Run full pipeline
python scripts/parse.py --input /media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/raw --limit 100000
python scripts/index.py
```

## Environment

### Machine: MSI Raider GE78 HX
- **User:** alex
- **Hostname:** msi-raider-linux.local
- **OS:** Ubuntu 24.04
- **Python:** 3.12 (use `.venv`)
- **Docker:** Available

### Paths
| Path | Purpose |
|------|---------|
| `~/Projects/ilegalflow-data/` | Repository |
| `/media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/` | Data storage |
| `/media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/raw/` | Raw USPTO XML |
| `/media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/releases/` | Parsed output |
| `/media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/indexes/` | Manticore data |

### Secrets
- **USPTO API Key:** Already in `.env` file
- **GitHub:** SSH key configured for push access

## Current State

### Data Downloaded (Complete)
- 86 annual files (1884-2024): 9.0 GB
- 357 daily files (2025): 11.3 GB
- **Total:** 443 files, 21 GB

### Infrastructure
- **Manticore Search:** Running in Docker on ports 9306/9308
- **Python venv:** `.venv/` with all dependencies

### Validated
- Download script: Working
- Parse script: 3,600 records/sec
- Phonetic search: "JOOSY JOOS" → "JUICY JUICE" ✓

## Scripts Reference

### download.py
```bash
python scripts/download.py --list           # List available files
python scripts/download.py --sample         # Download latest daily
python scripts/download.py --daily --days 7 # Download recent daily files
python scripts/download.py --all            # Download ALL files (caution: large)
python scripts/download.py --all --annual   # Download full annual backfile
```

### parse.py
```bash
python scripts/parse.py                      # Parse all raw files
python scripts/parse.py --limit 10000        # Parse limited records (testing)
python scripts/parse.py --input /path/to/raw # Specify input directory
```

Output goes to: `{output_path}/{YYYY-MM-DD}/marks.json`

### index.py
```bash
python scripts/index.py                      # Load latest release into Manticore
python scripts/index.py --limit 10000        # Load limited records
python scripts/index.py --test               # Run test searches after loading
```

## Manticore Search

### Start (if not running)
```bash
docker start manticore
# Or if container doesn't exist:
docker run -d --name manticore -p 9306:9306 -p 9308:9308 \
  -v /media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/indexes/manticore:/var/lib/manticore \
  manticoresearch/manticore:latest
```

### Query via HTTP
```bash
# Search
curl -s 'http://127.0.0.1:9308/cli' -d "SELECT * FROM trademarks WHERE MATCH('NIKE') LIMIT 5"

# Count records
curl -s 'http://127.0.0.1:9308/cli' -d "SELECT COUNT(*) FROM trademarks"

# Drop and recreate table
curl -s 'http://127.0.0.1:9308/cli' -d "DROP TABLE IF EXISTS trademarks"
```

## Git Workflow

```bash
# Always pull latest
git pull origin main

# Commit changes
git add .
git commit -m "feat: Description

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: [Agent Name] <noreply@anthropic.com>"

# Push
git push origin main
```

## Troubleshooting

### Python "externally-managed-environment" error
Always use the venv:
```bash
source .venv/bin/activate
```

### Manticore not responding
```bash
docker logs manticore
docker restart manticore
```

### USB drive not mounted
Check mount:
```bash
ls /media/alex/
# If missing, the USB drive needs to be reconnected
```

### Permission denied on data directory
```bash
sudo chown -R alex:alex /media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/
```

## Architecture Notes

This repo is a **producer** of data artifacts. It has no dependencies on other repos.

```
USPTO API → download.py → Raw XML → parse.py → JSON/Parquet → index.py → Manticore
```

Downstream consumers (not in scope for this repo):
- ilegalflow-web (landing page)
- ilegalflow-extension (Chrome extension)
- ilegalflow-core (search/scoring engine)

## Contact

Repository: https://github.com/llm-case-studies/ilegalflow-data
