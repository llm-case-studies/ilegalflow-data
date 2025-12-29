# Tasks for ilegalflow-data

Prioritized work items for AI agent execution. Complete in order.

---

## Phase 1: Full Dataset Processing (Priority: HIGH)

### Task 1.1: Parse All USPTO Data
**Goal:** Process all 443 XML files into structured JSON/Parquet

```bash
cd ~/Projects/ilegalflow-data
source .venv/bin/activate

# Full parse (no limit) - expect ~1 hour
python scripts/parse.py --input /media/alex/0a9193cd-6ff3-4541-8f6f-8eb12a8e241c/uspto-data/raw
```

**Expected output:**
- `/media/alex/.../uspto-data/releases/YYYY-MM-DD/marks.json`
- `/media/alex/.../uspto-data/releases/YYYY-MM-DD/MANIFEST.json`
- ~13 million records

**Success criteria:**
- [ ] MANIFEST.json shows total_records > 10,000,000
- [ ] marks.json is valid JSON
- [ ] Status distribution: ~30% live, ~70% dead (approximate)

### Task 1.2: Index Full Dataset in Manticore
**Goal:** Load all parsed records into Manticore Search

```bash
# First, recreate table to clear test data
curl -s 'http://127.0.0.1:9308/cli' -d "DROP TABLE IF EXISTS trademarks"

# Then load all records
python scripts/index.py
```

**Success criteria:**
- [ ] `SELECT COUNT(*) FROM trademarks` returns > 10,000,000
- [ ] Search queries return results in < 100ms
- [ ] Phonetic search works: "GOOGEL" should find "GOOGLE"

### Task 1.3: Install PyArrow for Parquet Output
**Goal:** Enable parquet output format for better downstream compatibility

```bash
source .venv/bin/activate
pip install pyarrow
```

Then modify `parse.py` to output parquet by default (or add `--format parquet` flag).

**Success criteria:**
- [ ] `marks.parquet` file generated
- [ ] File readable with `pyarrow.parquet.read_table()`

---

## Phase 2: Sample Export (Priority: HIGH)

### Task 2.1: Create Sample Datasets
**Goal:** Generate sample files for other repos to develop against

Create `scripts/export_samples.py`:
```python
# Export various sample sizes
# - samples/sample_1k.json (1,000 records)
# - samples/sample_10k.json (10,000 records)
# - samples/sample_100k.json (100,000 records)
# Include mix of live/dead/pending statuses
```

**Success criteria:**
- [ ] samples/ directory contains 3 JSON files
- [ ] Each file is valid JSON with correct record count
- [ ] Files committed to repo (small enough for git)

### Task 2.2: Validate Schema
**Goal:** Ensure output matches `schemas/marks.schema.json`

```bash
pip install jsonschema
# Write validation script
python scripts/validate_schema.py samples/sample_1k.json
```

**Success criteria:**
- [ ] All sample files pass schema validation
- [ ] Schema file updated if needed

---

## Phase 3: Feature Enrichment (Priority: MEDIUM)

### Task 3.1: Create features.py Script
**Goal:** Compute additional features for each trademark

Features to compute:
- `soundex_code` - Soundex encoding of mark_text
- `metaphone_code` - Metaphone encoding
- `word_count` - Number of words in mark
- `char_count` - Character length
- `has_design` - Boolean if design codes present
- `dominant_term` - Extracted main word (heuristic)

```bash
python scripts/features.py --input releases/YYYY-MM-DD/marks.json
```

**Output:** `features.parquet` or `features.json`

**Success criteria:**
- [ ] features.py script created and working
- [ ] All records have computed features
- [ ] Features validated against sample data

### Task 3.2: N-gram Generation
**Goal:** Generate character n-grams for fuzzy matching

Compute for each mark_text:
- 2-grams: "NIKE" → ["NI", "IK", "KE"]
- 3-grams: "NIKE" → ["NIK", "IKE"]

Store as JSON array or separate lookup table.

---

## Phase 4: Analysis & Patterns (Priority: MEDIUM)

### Task 4.1: Status Distribution Analysis
**Goal:** Understand the data distribution

Generate report:
- Count by status (live/dead/pending)
- Count by decade (1880s, 1890s, ...)
- Count by Nice class
- Top 100 owners by trademark count

**Output:** `analysis/distribution_report.json`

### Task 4.2: Failure Pattern Extraction
**Goal:** Identify why trademarks die

Analyze dead trademarks:
- Group by status_code (abandonment reasons)
- Extract common patterns
- Identify "quick deaths" (< 1 year from filing to death)

**Output:** `analysis/failure_patterns.json`

---

## Phase 5: Docker Compose Setup (Priority: MEDIUM)

### Task 5.1: Create docker-compose.yml
**Goal:** One-command local development setup

```yaml
# docker-compose.yml
services:
  manticore:
    image: manticoresearch/manticore:latest
    ports:
      - "9306:9306"
      - "9308:9308"
    volumes:
      - ./data/indexes:/var/lib/manticore
```

**Success criteria:**
- [ ] `docker-compose up` starts Manticore
- [ ] Data persists between restarts

### Task 5.2: Add API Service (Optional)
**Goal:** Simple HTTP API for searching

Create lightweight Flask/FastAPI service:
- `GET /search?q=NIKE` - Search marks
- `GET /mark/{serial}` - Get single mark
- `GET /health` - Health check

---

## Phase 6: Automation (Priority: LOW)

### Task 6.1: Daily Update Script
**Goal:** Automate daily USPTO data ingestion

Create `scripts/daily_update.sh`:
```bash
#!/bin/bash
cd ~/Projects/ilegalflow-data
source .venv/bin/activate
python scripts/download.py --sample
python scripts/parse.py --input raw/daily --incremental
python scripts/index.py --incremental
```

### Task 6.2: Cron Setup
**Goal:** Schedule daily updates

```bash
# Add to crontab
0 6 * * * /home/alex/Projects/ilegalflow-data/scripts/daily_update.sh >> /var/log/ilegalflow-daily.log 2>&1
```

---

## Completion Checklist

When all phases complete, verify:

- [ ] 13M+ records parsed and indexed
- [ ] Phonetic search working at scale
- [ ] Sample datasets exported
- [ ] Features computed
- [ ] Docker Compose working
- [ ] Documentation updated

Then create a PR or tag: `v1.0.0-full-dataset`

---

## Notes for Agent

1. **Run tasks sequentially** - Phase 1 must complete before Phase 2
2. **Commit frequently** - After each task, commit and push
3. **Test after changes** - Run validation before moving on
4. **Monitor resources** - Full parse uses significant I/O
5. **Check Manticore** - Ensure Docker container stays healthy

If stuck, check:
- `AGENT.md` for environment setup
- `docs/FEASIBILITY-RESULTS.md` for validated benchmarks
- `docs/ARCHITECTURE.md` for design decisions
