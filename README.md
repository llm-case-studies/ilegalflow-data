# iLegalFlow Data

**USPTO Trademark Data Ingestion & Preprocessing Pipeline**

This repository contains scripts, schemas, and tooling for ingesting USPTO trademark data. It produces clean, versioned artifacts that feed the iLegalFlow ecosystem.

## Philosophy

> Data intake exists to understand reality.
> — GPT System0Vision

This repo is a **producer of versioned artifacts**, not a consumer. Downstream systems (extension, landing page, search core) should never parse raw USPTO data directly—they consume outputs from here.

## Repository Structure

```
ilegalflow-data/
├── scripts/           # Download, parse, normalize, index
│   ├── download.py    # Fetch USPTO bulk XML
│   ├── parse.py       # XML → normalized records
│   ├── features.py    # Generate phonetics, n-grams
│   └── index.py       # Load into search engine
├── schemas/           # Data contracts
│   └── marks.schema.json
├── samples/           # Small test datasets (committed)
│   └── sample_100.json
├── config/            # Configuration
│   └── config.yaml
├── releases/          # Output artifacts (gitignored)
│   └── YYYY-MM-DD/
│       ├── marks.parquet
│       ├── status.parquet
│       ├── features.parquet
│       └── MANIFEST.json
├── docs/              # Documentation
│   └── ARCHITECTURE.md
└── README.md
```

## Data Flow

```
USPTO Bulk XML (10-150GB)
        │
        ▼
   [download.py]
        │
        ▼
   Raw XML on disk (external storage)
        │
        ▼
    [parse.py]
        │
        ▼
   Normalized records (parquet/json)
        │
        ▼
   [features.py]
        │
        ▼
   Enriched with phonetics, n-grams, labels
        │
        ▼
    [index.py]
        │
        ▼
   Search engine (Manticore/Tantivy)
```

## Data Storage Strategy

**Git repo contains:** Scripts, schemas, samples, docs (small, portable)

**External storage contains:** Raw USPTO XML, processed artifacts (large, shared via network)

Configure data paths in `config/config.yaml`:
```yaml
data:
  raw_path: /mnt/uspto-data/raw
  output_path: /mnt/uspto-data/releases
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_ORG/ilegalflow-data.git
cd ilegalflow-data

# Configure paths
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your storage paths

# Download sample data
python scripts/download.py --sample

# Parse and normalize
python scripts/parse.py

# Generate features (phonetics, etc.)
python scripts/features.py

# Index into search engine
python scripts/index.py
```

## Output Artifacts

Each release produces:

| File | Description |
|------|-------------|
| `marks.parquet` | Core trademark data (mark_text, classes, serial_no, dates) |
| `status.parquet` | Status labels (live/dead/abandoned, reason codes) |
| `features.parquet` | Computed features (phonetics, n-grams, dominant terms) |
| `MANIFEST.json` | Checksums, record counts, schema version |

## Related Repositories

- `ilegalflow-web` — Landing page, playground, marketing
- `ilegalflow-extension` — Chrome extension (Co-Pilot)
- `ilegalflow-core` — Rust search/scoring engine

## License

TBD
